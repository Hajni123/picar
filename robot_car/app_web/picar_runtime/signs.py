import numpy as np


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

def _first_output(raw_out):
    if isinstance(raw_out, dict):
        if not raw_out:
            return []
        return next(iter(raw_out.values()))
    return raw_out

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
