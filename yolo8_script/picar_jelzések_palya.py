#!/usr/bin/env python3

import os
import sys
import time
import threading
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "xcb"

import cv2
import numpy as np
import pygame
from gpiozero import PWMOutputDevice
from ultralytics.utils.plotting import colors

# Útvonalak
HAILO_APPS_DIR = Path("/home/khajni/hailo-apps")
OBJECT_DETECTION_DIR = (
    HAILO_APPS_DIR / "hailo_apps/python/standalone_apps/object_detection"
)

for p in (str(HAILO_APPS_DIR), str(OBJECT_DETECTION_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from hailo_apps.python.core.common.toolbox import (
    InputContext,
    VisualizationSettings,
    init_input_source,
)

from hailo_apps.python.standalone_apps.object_detection import (
    object_detection as od,
)

# Beállítások
MODEL_PATH = Path("/home/khajni/yolo8_script/best.hef")

IMAGE_WIDTH = 640
IMAGE_HEIGHT = 360
FRAME_RATE = 30

CLASS_NAMES = {
    0: "balra_nyil",
    1: "boja",
    2: "jobbra_nyil",
}

REAL_WIDTH_CM = {
    "boja": 9.0,
    "balra_nyil": 11.0,
    "jobbra_nyil": 11.0,
}

FOCAL_LENGTH_PX = 600.0

CONFIDENCE_THRESHOLD = 0.50

CONE_NEAR_CM = 20.0
ARROW_NEAR_CM = 50.0

# Motorok
MOTOR_PINS = (7, 8, 25, 27)

SPEED = 0.28
LEFT_STRAIGHT_SPEED = 0.26
RIGHT_STRAIGHT_SPEED = 0.28
TURN_SPEED = 0.30

TURN_90_LEFT_S = 0.60
TURN_90_RIGHT_S = 0.60
ARROW_STOP_S = 0.15

TURN_45_S = 0.33
TURN_50_S = 0.37
TURN_60_S = 0.44
TURN_60_RIGHT_S = 0.16
TURN_30_RIGHT_S = 0.18
TURN_80_S = 0.59
TURN_10_S = 0.07
TURN_20_S = 0.15
TURN_30_S = 0.22
TURN_40_S = 0.29

AVOID_SIDE_S = 1.45
AVOID_SIDE_RIGHT_S = 0.90
AVOID_PASS_S = 1.75
AVOID_PASS_RIGHT_S = 1.40
AVOID_RETURN_S = 2.80
AVOID_RETURN_RIGHT_S = 1.80

CLEAR_S = 0.45

motors = []


# Leállítás
def stop():
    for pin in motors:
        pin.value = 0.0


# Motorvezérlés
def _set_motor(forward_output, backward_output, value):
    value = float(np.clip(value, -1.0, 1.0))

    if value > 0:
        forward_output.value = value
        backward_output.value = 0.0
    elif value < 0:
        forward_output.value = 0.0
        backward_output.value = -value
    else:
        forward_output.value = 0.0
        backward_output.value = 0.0


def drive(left, right):
    _set_motor(motors[0], motors[1], left)
    _set_motor(motors[2], motors[3], right)


# Kerülés
def avoid_steps(side):
    if side == "RIGHT":
        return [
            ("AVOID_RIGHT_45_1", TURN_45_S,
             (TURN_SPEED, -TURN_SPEED)),

            ("AVOID_OUT_FORWARD", AVOID_SIDE_RIGHT_S,
             (LEFT_STRAIGHT_SPEED, RIGHT_STRAIGHT_SPEED)),

            ("AVOID_LEFT_50_1", TURN_50_S,
             (-TURN_SPEED, TURN_SPEED)),

            ("AVOID_PASS", AVOID_PASS_RIGHT_S,
             (LEFT_STRAIGHT_SPEED, RIGHT_STRAIGHT_SPEED)),

            ("AVOID_LEFT_50_2", TURN_50_S,
             (-TURN_SPEED, TURN_SPEED)),

            ("AVOID_RETURN_FORWARD", AVOID_RETURN_RIGHT_S,
             (LEFT_STRAIGHT_SPEED, RIGHT_STRAIGHT_SPEED)),

            ("AVOID_RIGHT_10_FINAL", TURN_10_S,
             (TURN_SPEED, -TURN_SPEED)),

        ]

    return [
        ("AVOID_LEFT_45_1", TURN_45_S,
         (-TURN_SPEED, TURN_SPEED)),

        ("AVOID_OUT_FORWARD", AVOID_SIDE_S,
         (LEFT_STRAIGHT_SPEED, RIGHT_STRAIGHT_SPEED)),

        ("AVOID_RIGHT_30_1", TURN_30_RIGHT_S,
         (TURN_SPEED, -TURN_SPEED)),

        ("AVOID_PASS", AVOID_PASS_S,
         (LEFT_STRAIGHT_SPEED, RIGHT_STRAIGHT_SPEED)),

        ("AVOID_RIGHT_30_2", TURN_30_RIGHT_S,
         (TURN_SPEED, -TURN_SPEED)),

        ("AVOID_RETURN_FORWARD", AVOID_RETURN_S,
         (LEFT_STRAIGHT_SPEED, RIGHT_STRAIGHT_SPEED)),

        ("AVOID_LEFT_60_FINAL", TURN_60_S,
         (-TURN_SPEED, TURN_SPEED)),

    ]


# Kimenet
def _first_output(raw_out):
    if isinstance(raw_out, dict):
        if not raw_out:
            return []
        return next(iter(raw_out.values()))
    return raw_out


# Feldolgozás
def _unwrap_classwise_nms(raw_out):
    """
    A Hailo NMS BY CLASS kimenetét 3 osztály listájára hozza.

    Várt osztályonkénti elem:
        [ymin, xmin, ymax, xmax, score]
    """

    data = _first_output(raw_out)

    if isinstance(data, (list, tuple)):
        if (
            len(data) == 1
            and isinstance(data[0], (list, tuple))
            and len(data[0]) == len(CLASS_NAMES)
        ):
            data = data[0]

        if len(data) == len(CLASS_NAMES):
            return list(data)

    if isinstance(data, np.ndarray):

        if data.dtype == object:
            items = list(data.reshape(-1))
            if len(items) == 1 and isinstance(items[0], (list, tuple)):
                items = list(items[0])
            if len(items) == len(CLASS_NAMES):
                return items

        arr = np.squeeze(data)

        if arr.ndim == 3 and arr.shape[0] == len(CLASS_NAMES):
            return [arr[i] for i in range(len(CLASS_NAMES))]

    raise RuntimeError(
        "Nem vart Hailo NMS kimenet. "
        f"Tipus: {type(data)}, "
        f"alak: {getattr(data, 'shape', None)}"
    )


# Koordináták
def _nms_box_to_frame(det, frame_w, frame_h):
    """
    A Hailo NMS normalizált, négyzetes letterbox koordinátáit
    visszaviszi az eredeti kameraképre.
    """

    y_min, x_min, y_max, x_max, score = map(float, det[:5])

    x_min = float(np.clip(x_min, 0.0, 1.0))
    y_min = float(np.clip(y_min, 0.0, 1.0))
    x_max = float(np.clip(x_max, 0.0, 1.0))
    y_max = float(np.clip(y_max, 0.0, 1.0))

    square = float(max(frame_w, frame_h))

    pad_x = (square - frame_w) / 2.0
    pad_y = (square - frame_h) / 2.0

    x1 = x_min * square - pad_x
    y1 = y_min * square - pad_y
    x2 = x_max * square - pad_x
    y2 = y_max * square - pad_y

    x1 = int(np.clip(round(x1), 0, frame_w - 1))
    y1 = int(np.clip(round(y1), 0, frame_h - 1))
    x2 = int(np.clip(round(x2), 0, frame_w - 1))
    y2 = int(np.clip(round(y2), 0, frame_h - 1))

    return x1, y1, x2, y2, score


# Felismerések
def detections_from_hailo(raw_out, frame_w, frame_h):
    class_results = _unwrap_classwise_nms(raw_out)

    detections = []

    for class_id, class_detections in enumerate(class_results):
        name = CLASS_NAMES[class_id]

        arr = np.asarray(class_detections, dtype=np.float32)

        if arr.size == 0:
            continue

        arr = arr.reshape(-1, 5)

        for det in arr:
            x1, y1, x2, y2, score = _nms_box_to_frame(
                det,
                frame_w,
                frame_h,
            )

            if score < CONFIDENCE_THRESHOLD:
                continue

            if x2 <= x1 or y2 <= y1:
                continue

            width_pixels = max(1.0, float(x2 - x1))

            distance_cm = (
                REAL_WIDTH_CM[name]
                * FOCAL_LENGTH_PX
                / width_pixels
            )

            detections.append(
                (
                    name,
                    distance_cm,
                    (x1 + x2) / 2.0,
                    score,
                    (x1, y1, x2, y2),
                )
            )

    return detections


# Megjelenítés
def custom_visualize(
    input_context,
    visualization_settings,
    output_queue,
    post_process_callback_fn,
    fps_tracker,
    stop_event,
):
    global motors

    pygame.init()
    screen = pygame.display.set_mode((IMAGE_WIDTH, IMAGE_HEIGHT))
    pygame.display.set_caption(
        "PiCar palya - M indul | Space stop | Q kilep"
    )
    clock = pygame.time.Clock()

    motion_enabled = False
    test_turn = False

    state = "PAUSED"
    deadline = 0.0

    next_side = "RIGHT"
    current_side = next_side

    avoidance_active = False
    avoidance_status = ""
    avoidance_abort = threading.Event()

    cone_enabled = True
    arrow_enabled = True

    cone_absent_since = None
    arrow_absent_since = None

    running = True

    print("M = mozgas inditasa")
    print("Space = megallas")
    print("B = egyszeri bal 90 fokos teszt")
    print("J = egyszeri jobb 90 fokos teszt")
    print("Q = kilepes")

    def sleep_abortable(seconds):
        """Pontos időzítés a kamera/inferencia sebességétől függetlenül."""
        end_t = time.monotonic() + float(seconds)
        while time.monotonic() < end_t:
            if avoidance_abort.is_set():
                return False
            time.sleep(min(0.01, max(0.0, end_t - time.monotonic())))
        return not avoidance_abort.is_set()

    def run_cone_maneuver(side):
        nonlocal avoidance_active
        nonlocal avoidance_status
        nonlocal next_side
        nonlocal cone_enabled
        nonlocal cone_absent_since
        nonlocal state

        avoidance_status = (
            "Kerul jobbrol"
            if side == "RIGHT"
            else "Kerul balrol"
        )

        try:

            stop()
            if not sleep_abortable(0.12):
                return

            for (
                step_name, duration, (left_command, right_command)
            ) in avoid_steps(side):
                if avoidance_abort.is_set():
                    return

                drive(left_command, right_command)

                if not sleep_abortable(duration):
                    return

                stop()

                if not sleep_abortable(0.08):
                    return

            next_side = (
                "LEFT"
                if side == "RIGHT"
                else "RIGHT"
            )

            cone_enabled = False
            cone_absent_since = None
            state = "FORWARD"

            if motion_enabled and not avoidance_abort.is_set():
                drive(LEFT_STRAIGHT_SPEED, RIGHT_STRAIGHT_SPEED)

        finally:
            if avoidance_abort.is_set():
                stop()

            avoidance_status = ""
            avoidance_active = False

    try:
        while (
            not stop_event.is_set()
            and running
        ):
            clock.tick(FRAME_RATE)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    stop_event.set()
                    break

                if event.type != pygame.KEYDOWN:
                    continue

                if event.key == pygame.K_q:
                    running = False
                    stop_event.set()
                    break

                if event.key == pygame.K_SPACE:
                    avoidance_abort.set()
                    stop()
                    motion_enabled = False
                    test_turn = False
                    state = "PAUSED"
                    continue

                if event.key == pygame.K_m and not motion_enabled:
                    avoidance_abort.clear()
                    motion_enabled = True
                    test_turn = False
                    state = "FORWARD"

                    cone_enabled = True
                    arrow_enabled = True
                    cone_absent_since = None
                    arrow_absent_since = None
                    continue

                if event.key == pygame.K_b and not motion_enabled:
                    motion_enabled = True
                    test_turn = True
                    state = "ARROW_LEFT"
                    deadline = time.monotonic() + TURN_90_LEFT_S
                    continue

                if event.key == pygame.K_j and not motion_enabled:
                    motion_enabled = True
                    test_turn = True
                    state = "ARROW_RIGHT"
                    deadline = time.monotonic() + TURN_90_RIGHT_S
                    continue

            if not running:
                break

            try:
                item = output_queue.get(timeout=0.15)
            except Exception:
                continue

            if item is None:
                break

            input_frame, raw_out = item

            if input_frame.ndim == 3 and input_frame.shape[2] == 3:
                frame = cv2.cvtColor(
                    input_frame,
                    cv2.COLOR_RGB2BGR,
                )
            else:
                frame = input_frame.copy()

            if (
                frame.shape[1] != IMAGE_WIDTH
                or frame.shape[0] != IMAGE_HEIGHT
            ):
                frame = cv2.resize(
                    frame,
                    (IMAGE_WIDTH, IMAGE_HEIGHT),
                )

            detections = detections_from_hailo(
                raw_out,
                IMAGE_WIDTH,
                IMAGE_HEIGHT,
            )

            current_time = time.monotonic()

            cones = [
                d
                for d in detections
                if d[0] == "boja"
            ]

            arrows = [
                d
                for d in detections
                if d[0] in (
                    "balra_nyil",
                    "jobbra_nyil",
                )
            ]

            cone = min(
                cones,
                key=lambda d: d[1],
                default=None,
            )

            arrow = min(
                arrows,
                key=lambda d: d[1],
                default=None,
            )

            if cone is None:
                if cone_absent_since is None:
                    cone_absent_since = current_time

                if (
                    state == "FORWARD"
                    and current_time - cone_absent_since >= 1.0
                ):
                    cone_enabled = True
            else:
                cone_absent_since = None

            if arrow is None:
                if arrow_absent_since is None:
                    arrow_absent_since = current_time

                if current_time - arrow_absent_since >= 1.0:
                    arrow_enabled = True
            else:
                arrow_absent_since = None

            left = 0.0
            right = 0.0

            if state == "FORWARD":
                if (
                    arrow is not None
                    and arrow_enabled
                    and arrow[1] <= ARROW_NEAR_CM
                ):
                    stop()
                    arrow_enabled = False

                    if arrow[0] == "balra_nyil":
                        state = "ARROW_STOP_LEFT"
                    else:
                        state = "ARROW_STOP_RIGHT"

                    deadline = current_time + ARROW_STOP_S

                elif (
                    cone is not None
                    and cone_enabled
                    and cone[1] <= CONE_NEAR_CM
                    and not avoidance_active
                ):
                    stop()

                    current_side = next_side
                    cone_enabled = False
                    state = "CONE_MANEUVER"

                    avoidance_abort.clear()
                    avoidance_active = True

                    threading.Thread(
                        target=run_cone_maneuver,
                        args=(current_side,),
                        daemon=True,
                    ).start()

                else:
                    left = LEFT_STRAIGHT_SPEED
                    right = RIGHT_STRAIGHT_SPEED

            if state == "ARROW_STOP_LEFT":
                left = 0.0
                right = 0.0

                if current_time >= deadline:
                    state = "ARROW_LEFT"
                    deadline = current_time + TURN_90_LEFT_S

            elif state == "ARROW_STOP_RIGHT":
                left = 0.0
                right = 0.0

                if current_time >= deadline:
                    state = "ARROW_RIGHT"
                    deadline = current_time + TURN_90_RIGHT_S

            if state == "ARROW_LEFT":
                if current_time >= deadline:
                    stop()

                    if test_turn:
                        test_turn = False
                        motion_enabled = False
                        state = "PAUSED"
                    else:
                        state = "CLEAR"
                        deadline = current_time + CLEAR_S
                else:
                    left = -TURN_SPEED
                    right = TURN_SPEED

            elif state == "ARROW_RIGHT":
                if current_time >= deadline:
                    stop()

                    if test_turn:
                        test_turn = False
                        motion_enabled = False
                        state = "PAUSED"
                    else:
                        state = "CLEAR"
                        deadline = current_time + CLEAR_S
                else:
                    left = TURN_SPEED
                    right = -TURN_SPEED

            if state == "CLEAR":
                if current_time >= deadline:
                    state = "FORWARD"
                    left = LEFT_STRAIGHT_SPEED
                    right = RIGHT_STRAIGHT_SPEED
                else:
                    left = LEFT_STRAIGHT_SPEED
                    right = RIGHT_STRAIGHT_SPEED

            if motion_enabled:
                if not avoidance_active:
                    drive(left, right)
            else:
                avoidance_abort.set()
                stop()

            for (
                name,
                distance,
                cx,
                score,
                (x1, y1, x2, y2),
            ) in detections:
                class_id = next(
                    i
                    for i, label in CLASS_NAMES.items()
                    if label == name
                )

                color = colors(
                    class_id,
                    bgr=True,
                )

                cv2.rectangle(
                    frame,
                    (x1, y1),
                    (x2, y2),
                    color,
                    2,
                )

                cv2.putText(
                    frame,
                    f"{name} {score * 100:.0f}% ~{distance:.0f}cm",
                    (
                        x1,
                        max(20, y1 - 7),
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (220, 220, 220),
                    2,
                )

            if (
                not motion_enabled
                or state == "PAUSED"
            ):
                status_text = "All"

            elif avoidance_active:
                status_text = avoidance_status

            elif state in (
                "ARROW_STOP_LEFT",
                "ARROW_LEFT",
            ):
                status_text = "Fordul balra"

            elif state in (
                "ARROW_STOP_RIGHT",
                "ARROW_RIGHT",
            ):
                status_text = "Fordul jobbra"

            else:
                status_text = "Elore"

            cv2.putText(
                frame,
                status_text,
                (8, 28),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 0, 0),
                4,
            )

            cv2.putText(
                frame,
                status_text,
                (8, 28),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2,
            )

            rgb_frame = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB,
            )

            surface = pygame.image.frombuffer(
                rgb_frame.tobytes(),
                (IMAGE_WIDTH, IMAGE_HEIGHT),
                "RGB",
            )

            screen.blit(
                surface,
                (0, 0),
            )

            pygame.display.flip()

    finally:
        avoidance_abort.set()
        stop()
        pygame.quit()


# Indítás
def main():
    global motors

    if not MODEL_PATH.is_file():
        raise SystemExit(
            f"Model missing: {MODEL_PATH}"
        )

    motors = [
        PWMOutputDevice(
            pin,
            frequency=100,
            initial_value=0,
        )
        for pin in MOTOR_PINS
    ]

    input_ctx = InputContext(
        input_src="rpi",
        batch_size=1,
        resolution=(IMAGE_WIDTH, IMAGE_HEIGHT),
        frame_rate=FRAME_RATE,
        video_unpaced=False,
    )

    input_ctx = init_input_source(
        input_ctx
    )

    vis_settings = VisualizationSettings(
        output_dir=None,
        save_stream_output=False,
        output_resolution=None,
        no_display=False,
    )

    labels = str(
        HAILO_APPS_DIR
        / "resources/json/coco_eighty.json"
    )

    if not hasattr(od.logger, "success"):
        od.logger.success = od.logger.info

    od.visualize = custom_visualize

    try:
        od.run_inference_pipeline(
            net=str(MODEL_PATH),
            labels=labels,
            input_context=input_ctx,
            visualization_settings=vis_settings,
            enable_tracking=False,
            show_fps=False,
            time_to_run=None,
        )

    finally:
        stop()

        for pin in motors:
            pin.close()


if __name__ == "__main__":
    main()
