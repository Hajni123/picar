#!/usr/bin/env python3
# Bója- és nyílfelismerésen alapuló motorvezérlés Hailón.
# A nyers modellkimenet dekódolását és az NMS-t a Python-kód végzi.

import subprocess
import threading
import time
from pathlib import Path

import cv2
import numpy as np
from gpiozero import PWMOutputDevice
from ultralytics.utils.plotting import colors
from hailo_platform import (
    HEF, VDevice, ConfigureParams, HailoStreamInterface,
    InferVStreams, InputVStreamParams, OutputVStreamParams, FormatType
)

# Beállítások
MODEL_PATH = Path('/home/khajni/yolo8_script/picar_jelzesek_palya.hef')
MOTOR_PINS = (7, 8, 25, 27)
FOCAL_LENGTH_PX = 600.0
REAL_WIDTH_CM = {'boja': 9.0, 'balra_nyil': 11.0, 'jobbra_nyil': 11.0}
CLASS_NAMES = {0: 'balra_nyil', 1: 'boja', 2: 'jobbra_nyil'}
CONFIDENCE_THRESHOLD = 0.50
NMS_IOU_THRESHOLD = 0.70
CONE_NEAR_CM = 30.0
ARROW_NEAR_CM = 30.0
MAX_FRAME_AGE_S = 1.0
DRIVE_SPEED = 0.28
TURN_SPEED = 0.30
TURN_90_LEFT_S = 0.8
TURN_90_RIGHT_S = 0.8
AVOID_TURN_S = 0.33
AVOID_FORWARD_S = 0.75
AVOID_PASS_S = 1.20
AVOID_RETURN_S = 0.33
CLEAR_S = 0.45

# Motorok
motors = []
motor_lock = threading.RLock()
motor_timer = None
motor_generation = 0


# Leállítás
def stop():
    global motor_timer, motor_generation
    with motor_lock:
        motor_generation += 1
        if motor_timer is not None:
            motor_timer.cancel()
            motor_timer = None
        for pin in motors:
            pin.value = 0


# Motorvezérlés
def drive(left, right, duration=None):
    global motor_timer
    left = float(np.clip(left, -1, 1))
    right = float(np.clip(right, -1, 1))
    with motor_lock:
        stop()
        if duration is not None and duration <= 0:
            return
        motors[0 if left >= 0 else 1].value = abs(left)
        motors[2 if right >= 0 else 3].value = abs(right)
        generation = motor_generation

        def expire():
            with motor_lock:
                if generation == motor_generation:
                    stop()

        motor_timer = threading.Timer(
            0.8 if duration is None else duration,
            expire
        )
        motor_timer.daemon = True
        motor_timer.start()


# Kerülés
def avoid_steps(side):
    direction = 1 if side == 'RIGHT' else -1
    outward = (direction * TURN_SPEED, -direction * TURN_SPEED)
    inward = (-direction * TURN_SPEED, direction * TURN_SPEED)
    forward = (DRIVE_SPEED, DRIVE_SPEED)
    return [
        ('AVOID_OUT', AVOID_TURN_S, outward),
        ('AVOID_OFFSET', AVOID_FORWARD_S, forward),
        ('AVOID_ALIGN', AVOID_RETURN_S, inward),
        ('AVOID_PASS', AVOID_PASS_S, forward),
        ('AVOID_RETURN_TURN', AVOID_RETURN_S, inward),
        ('AVOID_RETURN_DIAGONAL', AVOID_FORWARD_S, forward),
        ('AVOID_RESTORE', AVOID_TURN_S, outward),
    ]


# Képfelvétel
def capture():
    try:
        p = subprocess.run(
            ['rpicam-jpeg', '-o', '-', '-t', '1', '--width', '640',
             '--height', '480', '-n'], capture_output=True, timeout=3)
    except (subprocess.TimeoutExpired, OSError):
        return None
    return (
        cv2.imdecode(np.frombuffer(p.stdout, np.uint8), cv2.IMREAD_COLOR)
        if p.returncode == 0 and p.stdout
        else None
    )


# Előfeldolgozás
def letterbox(frame, size=320):
    h, w = frame.shape[:2]
    scale = min(size / w, size / h)
    nw, nh = int(round(w * scale)), int(round(h * scale))
    resized_image = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_LINEAR)
    left = (size - nw) // 2
    top = (size - nh) // 2
    input_image = np.full((size, size, 3), 114, dtype=np.uint8)
    input_image[top:top + nh, left:left + nw] = resized_image
    return input_image, scale, left, top


# Aktiváció
def softmax(x):
    x = x - np.max(x, axis=-1, keepdims=True)
    e = np.exp(x)
    return e / np.sum(e, axis=-1, keepdims=True)

# Rácspontok
anchors = []
strides = []
for stride in (8, 16, 32):
    n = 320 // stride
    for y in range(n):
        for x in range(n):
            anchors.append((x + 0.5, y + 0.5))
            strides.append(stride)
anchors = np.asarray(anchors, dtype=np.float32)
strides = np.asarray(strides, dtype=np.float32)


# Modell
class HailoModel:
    def __init__(self, path):
        self.names = CLASS_NAMES
        self.hef = HEF(str(path))
        self.device = VDevice(VDevice.create_params())
        cfg = ConfigureParams.create_from_hef(
            self.hef,
            interface=HailoStreamInterface.PCIe
        )
        self.network_group = self.device.configure(self.hef, cfg)[0]
        self.network_params = self.network_group.create_params()
        self.input_params = InputVStreamParams.make_from_network_group(
            self.network_group, quantized=True, format_type=FormatType.UINT8
        )
        self.output_params = OutputVStreamParams.make_from_network_group(
            self.network_group, quantized=False, format_type=FormatType.FLOAT32
        )
        self.input_name = self.hef.get_input_vstream_infos()[0].name
        self.pipeline = InferVStreams(
            self.network_group,
            self.input_params,
            self.output_params
        )
        self.pipeline.__enter__()
        self.activation = self.network_group.activate(self.network_params)
        self.activation.__enter__()

    def infer(self, input_image):
        return self.pipeline.infer({
            self.input_name: np.expand_dims(input_image, 0)
        })

    def close(self):
        try:
            self.activation.__exit__(None, None, None)
        except Exception:
            pass
        try:
            self.pipeline.__exit__(None, None, None)
        except Exception:
            pass


# Felismerés
def detections(model, frame):
    input_image, scale, pad_x, pad_y = letterbox(frame, 320)
    input_image = cv2.cvtColor(input_image, cv2.COLOR_BGR2RGB)
    outputs = model.infer(input_image)

    reg = None
    cls = None
    for value in outputs.values():
        a = np.squeeze(np.asarray(value))
        if a.shape == (2100, 64):
            reg = a.astype(np.float32)
        elif a.shape == (2100, 3):
            cls = a.astype(np.float32)

    if reg is None or cls is None:
        shapes = [
            tuple(np.squeeze(np.asarray(v)).shape)
            for v in outputs.values()
        ]
        raise RuntimeError(f'Nem vart Hailo kimenet: {shapes}')

    reg = reg.T.reshape(4, 16, 2100)
    reg = reg - np.max(reg, axis=1, keepdims=True)
    prob = np.exp(reg)
    prob /= np.sum(prob, axis=1, keepdims=True)
    bins = np.arange(16, dtype=np.float32).reshape(1, 16, 1)
    d = np.sum(prob * bins, axis=1).T

    class_ids = np.argmax(cls, axis=1)
    scores = np.max(cls, axis=1)

    raw_boxes = []
    raw_scores = []
    raw_classes = []

    for i in np.where(scores >= CONFIDENCE_THRESHOLD)[0]:
        ax, ay = anchors[i]
        stride = strides[i]
        left_distance, top_distance, right_distance, bottom_distance = d[i]
        x1 = (ax - left_distance) * stride
        y1 = (ay - top_distance) * stride
        x2 = (ax + right_distance) * stride
        y2 = (ay + bottom_distance) * stride

        x1 = (x1 - pad_x) / scale
        x2 = (x2 - pad_x) / scale
        y1 = (y1 - pad_y) / scale
        y2 = (y2 - pad_y) / scale

        h, w = frame.shape[:2]
        x1 = float(np.clip(x1, 0, w - 1))
        x2 = float(np.clip(x2, 0, w - 1))
        y1 = float(np.clip(y1, 0, h - 1))
        y2 = float(np.clip(y2, 0, h - 1))

        if x2 <= x1 or y2 <= y1:
            continue

        raw_boxes.append((x1, y1, x2, y2))
        raw_scores.append(float(scores[i]))
        raw_classes.append(int(class_ids[i]))

    detected_objects = []
    for class_id, name in CLASS_NAMES.items():
        ids = [i for i, c in enumerate(raw_classes) if c == class_id]
        if not ids:
            continue

        boxes_xywh = []
        scores_c = []
        for i in ids:
            x1, y1, x2, y2 = raw_boxes[i]
            boxes_xywh.append([x1, y1, x2 - x1, y2 - y1])
            scores_c.append(raw_scores[i])

        keep = cv2.dnn.NMSBoxes(
            boxes_xywh,
            scores_c,
            CONFIDENCE_THRESHOLD,
            NMS_IOU_THRESHOLD
        )
        if len(keep) == 0:
            continue

        for k in np.asarray(keep).reshape(-1):
            i = ids[int(k)]
            x1, y1, x2, y2 = raw_boxes[i]
            width_pixels = max(1.0, x2 - x1)
            distance_cm = REAL_WIDTH_CM[name] * FOCAL_LENGTH_PX / width_pixels
            detected_objects.append((
                name,
                distance_cm,
                (x1 + x2) / 2,
                raw_scores[i],
                (int(x1), int(y1), int(x2), int(y2))
            ))

    return detected_objects


# Indítás
def main():
    global motors
    if not MODEL_PATH.is_file():
        raise SystemExit(f'Model missing: {MODEL_PATH}')
    model = HailoModel(MODEL_PATH)
    motors = [
        PWMOutputDevice(pin, frequency=100, initial_value=0)
        for pin in MOTOR_PINS
    ]
    motion_enabled = False
    test_turn = False
    state = 'PAUSED'
    deadline = 0.0
    next_side = 'RIGHT'
    current_side = next_side
    avoidance_steps = []
    avoidance_index = 0
    cone_enabled = True
    arrow_enabled = True
    cone_absent_since = None
    arrow_absent_since = None
    last_frame_time = time.monotonic()
    print(
        'B = egyszeri bal fordulat; J = egyszeri jobb fordulat; utana megall.'
    )
    print(
        'Motorok állnak. M = mozgás indítása; '
        'szóköz = megállítás; q = kilépés.'
    )
    print('A távolság és az időzített fordulat helyszíni kalibrációt igényel.')
    try:
        while True:
            frame = capture()
            current_time = time.monotonic()
            if frame is None:
                stop()
                motion_enabled = False
                if current_time - last_frame_time > MAX_FRAME_AGE_S:
                    state = 'PAUSED'
                continue
            last_frame_time = current_time
            detected_objects = detections(model, frame)
            current_time = time.monotonic()
            cones = [d for d in detected_objects if d[0] == 'boja']
            arrows = [
                d for d in detected_objects
                if d[0] in ('balra_nyil', 'jobbra_nyil')
            ]
            cone = min(cones, key=lambda d: d[1], default=None)
            arrow = min(arrows, key=lambda d: d[1], default=None)

            if cone is None:
                cone_absent_since = (
                    current_time
                    if cone_absent_since is None
                    else cone_absent_since
                )
                if (
                    state == 'FORWARD'
                    and current_time - cone_absent_since > 1.0
                ):
                    cone_enabled = True
            else:
                cone_absent_since = None
            if arrow is None:
                arrow_absent_since = (
                    current_time
                    if arrow_absent_since is None
                    else arrow_absent_since
                )
                if current_time - arrow_absent_since > 1.0:
                    arrow_enabled = True
            else:
                arrow_absent_since = None
            left = right = 0.0
            if state == 'FORWARD':

                if cone and cone_enabled and cone[1] <= CONE_NEAR_CM:
                    current_side = next_side
                    cone_enabled = False
                    avoidance_steps = avoid_steps(current_side)
                    avoidance_index = 0
                    state, duration, _ = avoidance_steps[avoidance_index]
                    deadline = current_time + duration
                elif arrow and arrow_enabled and arrow[1] <= ARROW_NEAR_CM:
                    arrow_enabled = False
                    state = (
                        'ARROW_LEFT'
                        if arrow[0] == 'balra_nyil'
                        else 'ARROW_RIGHT'
                    )
                    deadline = current_time + (
                        TURN_90_LEFT_S
                        if state == 'ARROW_LEFT'
                        else TURN_90_RIGHT_S
                    )
                else:
                    left = right = DRIVE_SPEED
            if state.startswith('AVOID_'):
                if current_time >= deadline:
                    stop()
                    avoidance_index += 1
                    if avoidance_index == len(avoidance_steps):
                        next_side = (
                            'LEFT' if current_side == 'RIGHT' else 'RIGHT'
                        )
                        cone_enabled = False
                        cone_absent_since = None
                        state = 'FORWARD'
                        avoidance_steps = []
                    else:
                        state, duration, _ = avoidance_steps[avoidance_index]
                        deadline = current_time + duration
                if state.startswith('AVOID_'):
                    left, right = avoidance_steps[avoidance_index][2]
            if state in ('ARROW_LEFT', 'ARROW_RIGHT'):
                if current_time >= deadline:
                    stop()
                    if test_turn:
                        motion_enabled = False
                        test_turn = False
                        state = 'PAUSED'
                    else:
                        state, deadline = 'CLEAR', current_time + CLEAR_S
                else:
                    left, right = (
                        (-TURN_SPEED, TURN_SPEED)
                        if state == 'ARROW_LEFT'
                        else (TURN_SPEED, -TURN_SPEED)
                    )
            if state == 'CLEAR':
                if current_time >= deadline:
                    state = 'FORWARD'
                else:
                    left = right = DRIVE_SPEED
            if motion_enabled:
                timed = state.startswith('AVOID_') or state in (
                    'ARROW_LEFT', 'ARROW_RIGHT', 'CLEAR'
                )
                drive(
                    left,
                    right,
                    max(0.0, deadline - time.monotonic()) if timed else None
                )
            else:
                stop()
            for (
                name, distance_cm, cx, score, (x1, y1, x2, y2)
            ) in detected_objects:
                class_id = next(
                    i for i, label in model.names.items() if label == name
                )
                color = colors(class_id, bgr=True)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(
                    frame,
                    f'{name} {score * 100:.0f}% ~{distance_cm:.0f}cm',
                    (x1, max(20, y1 - 7)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (220, 220, 220),
                    2
                )
            if not motion_enabled or state == 'PAUSED':
                status_text = 'All'
            elif state.startswith('AVOID_'):
                status_text = (
                    'Kerul jobbrol'
                    if current_side == 'RIGHT'
                    else 'Kerul balrol'
                )
            elif state == 'ARROW_LEFT':
                status_text = 'Fordul balra'
            elif state == 'ARROW_RIGHT':
                status_text = 'Fordul jobbra'
            else:
                status_text = 'Elore'
            cv2.putText(frame, status_text, (8, 28),
                        cv2.FONT_HERSHEY_SIMPLEX, .65, (0, 0, 0), 4)
            cv2.putText(frame, status_text, (8, 28),
                        cv2.FONT_HERSHEY_SIMPLEX, .65, (255, 255, 255), 2)
            cv2.imshow('PiCar palya - Space stop, q kilep', frame)
            key = cv2.waitKey(1) & 0xff
            if key == ord('q'):
                break
            if key in (ord('m'), ord('M')) and not motion_enabled:
                motion_enabled = True
                test_turn = False
                avoidance_steps = []
                state = 'FORWARD'
                cone_enabled = True
                arrow_enabled = True
                cone_absent_since = None
                arrow_absent_since = None
            if (
                key in (ord('b'), ord('B'), ord('j'), ord('J'))
                and not motion_enabled
            ):
                test_turn = True
                motion_enabled = True
                state = (
                    'ARROW_LEFT'
                    if key in (ord('b'), ord('B'))
                    else 'ARROW_RIGHT'
                )
                duration = (
                    TURN_90_LEFT_S
                    if state == 'ARROW_LEFT'
                    else TURN_90_RIGHT_S
                )
                deadline = time.monotonic() + duration
                drive(
                    -TURN_SPEED if state == 'ARROW_LEFT' else TURN_SPEED,
                    TURN_SPEED if state == 'ARROW_LEFT' else -TURN_SPEED,
                    duration
                )
            if key == 32:
                state = 'PAUSED'
                stop()
                motion_enabled = False
    finally:
        stop()
        for pin in motors:
            pin.close()
        model.close()
        cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
