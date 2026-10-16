#!/usr/bin/env python3
# Bója- és nyílfelismerésen alapuló motorvezérlés Hailón.
# A HEF-modell NMS-kimenetét dolgozza fel.

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
MODEL_PATH = Path('/home/khajni/yolo8_script/best.hef')
MOTOR_PINS = (7, 8, 25, 27)
FOCAL_LENGTH_PX = 600.0
REAL_WIDTH_CM = {'boja': 9.0, 'balra_nyil': 11.0, 'jobbra_nyil': 11.0}
CLASS_NAMES = {0: 'balra_nyil', 1: 'boja', 2: 'jobbra_nyil'}
CONFIDENCE_THRESHOLD = 0.50
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
             '--height', '480', '-n'],
            capture_output=True,
            timeout=3
        )
    except (subprocess.TimeoutExpired, OSError):
        return None

    if p.returncode != 0 or not p.stdout:
        return None

    return cv2.imdecode(
        np.frombuffer(p.stdout, np.uint8),
        cv2.IMREAD_COLOR
    )


# Előfeldolgozás
def letterbox(frame, size=320):
    h, w = frame.shape[:2]
    scale = min(size / w, size / h)
    nw = int(round(w * scale))
    nh = int(round(h * scale))

    resized_image = cv2.resize(
        frame,
        (nw, nh),
        interpolation=cv2.INTER_LINEAR
    )

    left = (size - nw) // 2
    top = (size - nh) // 2

    input_image = np.full(
        (size, size, 3),
        114,
        dtype=np.uint8
    )

    input_image[top:top + nh, left:left + nw] = resized_image
    return input_image, scale, left, top


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

        self.network_group = self.device.configure(
            self.hef,
            cfg
        )[0]

        self.network_params = self.network_group.create_params()

        self.input_params = InputVStreamParams.make_from_network_group(
            self.network_group,
            quantized=True,
            format_type=FormatType.UINT8
        )

        self.output_params = OutputVStreamParams.make_from_network_group(
            self.network_group,
            quantized=False,
            format_type=FormatType.FLOAT32
        )

        self.input_name = self.hef.get_input_vstream_infos()[0].name
        self.output_name = self.hef.get_output_vstream_infos()[0].name

        self.pipeline = InferVStreams(
            self.network_group,
            self.input_params,
            self.output_params
        )
        self.pipeline.__enter__()

        self.activation = self.network_group.activate(
            self.network_params
        )
        self.activation.__enter__()

    def infer(self, input_image):
        outputs = self.pipeline.infer({
            self.input_name: np.expand_dims(input_image, 0)
        })
        return outputs[self.output_name]

    def close(self):
        try:
            self.activation.__exit__(None, None, None)
        except Exception:
            pass

        try:
            self.pipeline.__exit__(None, None, None)
        except Exception:
            pass

        try:
            self.device.release()
        except Exception:
            pass


# Kimenetek
def get_class_results(nms_output):
    if not isinstance(nms_output, list):
        raise RuntimeError(
            f'Nem vart NMS kimeneti tipus: {type(nms_output)}'
        )

    if len(nms_output) == 1 and isinstance(
        nms_output[0], (list, tuple)
    ):
        class_results = nms_output[0]
    elif (
        len(nms_output) == len(CLASS_NAMES)
        and all(isinstance(x, np.ndarray) for x in nms_output)
    ):
        class_results = nms_output
    else:
        raise RuntimeError(
            f'Nem vart NMS szerkezet: '
            f'tipus={type(nms_output)}, hossz={len(nms_output)}'
        )

    if len(class_results) != len(CLASS_NAMES):
        raise RuntimeError(
            f'Nem vart osztalyszam az NMS kimeneten: '
            f'{len(class_results)}'
        )

    return class_results


# Felismerés
def detections(model, frame):
    input_image, scale, pad_x, pad_y = letterbox(frame, 320)

    input_image = cv2.cvtColor(
        input_image,
        cv2.COLOR_BGR2RGB
    )

    nms_output = model.infer(input_image)
    class_results = get_class_results(nms_output)

    frame_h, frame_w = frame.shape[:2]
    detected_objects = []

    for class_id, class_detections in enumerate(class_results):
        name = CLASS_NAMES.get(class_id)
        if name is None:
            continue

        detections_array = np.asarray(
            class_detections,
            dtype=np.float32
        )

        if detections_array.size == 0:
            continue

        detections_array = detections_array.reshape(-1, 5)

        for det in detections_array:
            y_min, x_min, y_max, x_max, score = map(
                float,
                det
            )

            if score < CONFIDENCE_THRESHOLD:
                continue

            x_min = float(np.clip(x_min, 0.0, 1.0))
            y_min = float(np.clip(y_min, 0.0, 1.0))
            x_max = float(np.clip(x_max, 0.0, 1.0))
            y_max = float(np.clip(y_max, 0.0, 1.0))

            x1_320 = x_min * 320.0
            y1_320 = y_min * 320.0
            x2_320 = x_max * 320.0
            y2_320 = y_max * 320.0

            x1 = (x1_320 - pad_x) / scale
            y1 = (y1_320 - pad_y) / scale
            x2 = (x2_320 - pad_x) / scale
            y2 = (y2_320 - pad_y) / scale

            x1 = int(np.clip(round(x1), 0, frame_w - 1))
            y1 = int(np.clip(round(y1), 0, frame_h - 1))
            x2 = int(np.clip(round(x2), 0, frame_w - 1))
            y2 = int(np.clip(round(y2), 0, frame_h - 1))

            if x2 <= x1 or y2 <= y1:
                continue

            width_pixels = max(1.0, float(x2 - x1))
            distance_cm = (
                REAL_WIDTH_CM[name]
                * FOCAL_LENGTH_PX
                / width_pixels
            )

            detected_objects.append((
                name,
                distance_cm,
                (x1 + x2) / 2.0,
                score,
                (x1, y1, x2, y2)
            ))

    return detected_objects


# Indítás
def main():
    global motors

    if not MODEL_PATH.is_file():
        raise SystemExit(f'Model missing: {MODEL_PATH}')

    model = HailoModel(MODEL_PATH)

    motors = [
        PWMOutputDevice(
            pin,
            frequency=100,
            initial_value=0
        )
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

            cones = [
                d for d in detected_objects
                if d[0] == 'boja'
            ]

            arrows = [
                d for d in detected_objects
                if d[0] in ('balra_nyil', 'jobbra_nyil')
            ]

            cone = min(
                cones,
                key=lambda d: d[1],
                default=None
            )

            arrow = min(
                arrows,
                key=lambda d: d[1],
                default=None
            )

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

            left = 0.0
            right = 0.0

            if state == 'FORWARD':
                if (
                    cone
                    and cone_enabled
                    and cone[1] <= CONE_NEAR_CM
                ):
                    current_side = next_side
                    cone_enabled = False
                    avoidance_steps = avoid_steps(current_side)
                    avoidance_index = 0
                    state, duration, _ = avoidance_steps[avoidance_index]
                    deadline = current_time + duration

                elif (
                    arrow
                    and arrow_enabled
                    and arrow[1] <= ARROW_NEAR_CM
                ):
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
                    left = DRIVE_SPEED
                    right = DRIVE_SPEED

            if state.startswith('AVOID_'):
                if current_time >= deadline:
                    stop()
                    avoidance_index += 1

                    if avoidance_index == len(avoidance_steps):
                        next_side = (
                            'LEFT'
                            if current_side == 'RIGHT'
                            else 'RIGHT'
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
                        state = 'CLEAR'
                        deadline = current_time + CLEAR_S

                else:
                    if state == 'ARROW_LEFT':
                        left = -TURN_SPEED
                        right = TURN_SPEED
                    else:
                        left = TURN_SPEED
                        right = -TURN_SPEED

            if state == 'CLEAR':
                if current_time >= deadline:
                    state = 'FORWARD'
                else:
                    left = DRIVE_SPEED
                    right = DRIVE_SPEED

            if motion_enabled:
                timed = (
                    state.startswith('AVOID_')
                    or state in (
                        'ARROW_LEFT',
                        'ARROW_RIGHT',
                        'CLEAR'
                    )
                )

                duration = (
                    max(
                        0.0,
                        deadline - time.monotonic()
                    )
                    if timed
                    else None
                )

                drive(left, right, duration)
            else:
                stop()

            for (
                name,
                distance_cm,
                cx,
                score,
                (x1, y1, x2, y2)
            ) in detected_objects:
                class_id = next(
                    i
                    for i, label in model.names.items()
                    if label == name
                )

                color = colors(
                    class_id,
                    bgr=True
                )

                cv2.rectangle(
                    frame,
                    (x1, y1),
                    (x2, y2),
                    color,
                    2
                )

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

            cv2.putText(
                frame,
                status_text,
                (8, 28),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 0, 0),
                4
            )

            cv2.putText(
                frame,
                status_text,
                (8, 28),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2
            )

            cv2.imshow(
                'PiCar palya - Space stop, q kilep',
                frame
            )

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
                key in (
                    ord('b'),
                    ord('B'),
                    ord('j'),
                    ord('J')
                )
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
                    -TURN_SPEED
                    if state == 'ARROW_LEFT'
                    else TURN_SPEED,
                    TURN_SPEED
                    if state == 'ARROW_LEFT'
                    else -TURN_SPEED,
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
