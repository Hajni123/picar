import math
import time

import cv2
import numpy as np

from picamera2 import Picamera2
from hailo_platform import (
    HEF,
    VDevice,
    HailoStreamInterface,
    InferVStreams,
    ConfigureParams,
    InputVStreamParams,
    OutputVStreamParams,
    FormatType,
)


# Beállítások
IMAGE_WIDTH = 640
IMAGE_HEIGHT = 640
CENTER_POINT = (IMAGE_WIDTH // 2, IMAGE_HEIGHT // 2)
PIXELS_PER_METER = 111.0
FOCAL_LENGTH = 520.0
HEF_PATH = "yolov8n.hef"

COCO_CLASSES = [
    "person", "bicycle", "car", "motorcycle", "airplane",
    "bus", "train", "truck", "boat", "traffic light",
    "fire hydrant", "stop sign", "parking meter", "bench",
    "bird", "cat", "dog", "horse", "sheep", "cow",
    "elephant", "bear", "zebra", "giraffe", "backpack",
    "umbrella", "handbag", "tie", "suitcase", "frisbee",
    "skis", "snowboard", "sports ball", "kite", "baseball bat",
    "baseball glove", "skateboard", "surfboard", "tennis racket",
    "bottle", "wine glass", "cup", "fork", "knife", "spoon",
    "bowl", "banana", "apple", "sandwich", "orange", "broccoli",
    "carrot", "hot dog", "pizza", "donut", "cake", "chair",
    "couch", "potted plant", "bed", "dining table", "toilet",
    "tv", "laptop", "mouse", "remote", "keyboard", "cell phone",
    "microwave", "oven", "toaster", "sink", "refrigerator",
    "book", "clock", "vase", "scissors", "teddy bear",
    "hair drier", "toothbrush",
]

REAL_WIDTH_CM = {
    "person": 45.0,
    "cell phone": 7.5,
    "bottle": 7.0,
    "cup": 8.0,
    "laptop": 32.0,
    "chair": 50.0,
    "sports ball": 22.0,
}

DEFAULT_WIDTH_CM = 20.0


# Távolságbecslés
def estimate_distance(real_width_cm, width_pixels):
    if width_pixels <= 0:
        return 0

    return (real_width_cm * FOCAL_LENGTH) / width_pixels


# Videómentés
video_writer = cv2.VideoWriter(
    "output.avi",
    cv2.VideoWriter_fourcc(*"MJPG"),
    30.0,
    (IMAGE_WIDTH, IMAGE_HEIGHT)
)


# Kamera
camera = Picamera2()

camera_config = camera.create_preview_configuration(
    main={
        "size": (IMAGE_WIDTH, IMAGE_HEIGHT),
        "format": "RGB888"
    }
)

camera.configure(camera_config)
camera.start()

print("Hailo-8 rendszer fut... Kilépéshez nyomj 'q'-t!")


# Hálózat
device_params = VDevice.create_params()

with VDevice(device_params) as device:
    hef = HEF(HEF_PATH)

    configure_params = ConfigureParams.create_from_hef(
        hef,
        interface=HailoStreamInterface.PCIe
    )

    network_group = device.configure(
        hef,
        configure_params
    )[0]

    network_group_params = network_group.create_params()

    input_vstream_params = InputVStreamParams.make(
        network_group,
        format_type=FormatType.UINT8
    )

    output_vstream_params = OutputVStreamParams.make(
        network_group,
        format_type=FormatType.FLOAT32
    )

    input_name = hef.get_input_vstream_infos()[0].name

    # Aktiválás
    with network_group.activate(network_group_params):
        with InferVStreams(
            network_group,
            input_vstream_params,
            output_vstream_params
        ) as pipeline:
            previous_time = time.time()

            while True:
                # Képfelvétel
                raw_frame = camera.capture_array()
                frame = raw_frame.copy()
                annotated_frame = frame.copy()

                # Következtetés
                input_data = {
                    input_name: np.expand_dims(
                        raw_frame,
                        axis=0
                    )
                }

                results = pipeline.infer(input_data)

                cv2.circle(
                    annotated_frame,
                    CENTER_POINT,
                    5,
                    (0, 0, 255),
                    -1
                )

                # Felismerések
                detections = []

                for key, class_detections in results.items():
                    if (
                        isinstance(class_detections, list)
                        and len(class_detections) > 0
                    ):
                        batch_results = class_detections[0]

                    elif isinstance(class_detections, np.ndarray):
                        batch_results = (
                            class_detections[0]
                            if class_detections.ndim >= 2
                            else [class_detections]
                        )

                    else:
                        continue

                    for class_id, boxes in enumerate(batch_results):
                        if len(boxes) == 0:
                            continue

                        for box in boxes:
                            if len(box) >= 5:
                                (
                                    y_min,
                                    x_min,
                                    y_max,
                                    x_max,
                                    confidence
                                ) = box[:5]

                                if confidence >= 0.35:
                                    name = (
                                        COCO_CLASSES[class_id]
                                        if class_id < len(COCO_CLASSES)
                                        else f"Id_{class_id}"
                                    )

                                    x1 = max(
                                        0,
                                        int(x_min * IMAGE_WIDTH)
                                    )
                                    y1 = max(
                                        0,
                                        int(y_min * IMAGE_HEIGHT)
                                    )
                                    x2 = min(
                                        IMAGE_WIDTH,
                                        int(x_max * IMAGE_WIDTH)
                                    )
                                    y2 = min(
                                        IMAGE_HEIGHT,
                                        int(y_max * IMAGE_HEIGHT)
                                    )

                                    detections.append(
                                        (
                                            (
                                                x1, y1,
                                                x2, y2,
                                                float(confidence)
                                            ),
                                            name
                                        )
                                    )

                # Jelölések
                for (
                    x1, y1, x2, y2, confidence
                ), name in detections:
                    width_pixels = x2 - x1
                    height_pixels = y2 - y1
                    confidence_percent = int(confidence * 100)

                    cv2.rectangle(
                        annotated_frame,
                        (x1, y1),
                        (x2, y2),
                        (255, 0, 0),
                        2
                    )

                    cv2.putText(
                        annotated_frame,
                        f"{name} {confidence_percent}%",
                        (x1, max(20, y1 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (255, 0, 0),
                        2
                    )

                    # Éldetektálás
                    if width_pixels > 10 and height_pixels > 10:
                        roi = frame[y1:y2, x1:x2]

                        if roi.size > 0:
                            gray_roi = cv2.cvtColor(
                                roi,
                                cv2.COLOR_BGR2GRAY
                            )

                            blurred_roi = cv2.GaussianBlur(
                                gray_roi,
                                (5, 5),
                                0
                            )

                            edges = cv2.Canny(
                                blurred_roi,
                                100,
                                200
                            )

                            black_mask = cv2.multiply(edges, 0)

                            colored_edges = cv2.merge([
                                black_mask,
                                edges,
                                black_mask
                            ])

                            annotated_roi = annotated_frame[
                                y1:y2, x1:x2
                            ]

                            combined_roi = cv2.addWeighted(
                                annotated_roi,
                                1.0,
                                colored_edges,
                                1.0,
                                0
                            )

                            annotated_frame[
                                y1:y2, x1:x2
                            ] = combined_roi

                    # Középpont
                    center_x = (x1 + x2) // 2
                    center_y = (y1 + y2) // 2

                    cv2.circle(
                        annotated_frame,
                        (center_x, center_y),
                        4,
                        (0, 255, 255),
                        -1
                    )

                    cv2.line(
                        annotated_frame,
                        CENTER_POINT,
                        (center_x, center_y),
                        (0, 255, 0),
                        2
                    )

                    # Távolság
                    offset_pixels = math.hypot(
                        center_x - CENTER_POINT[0],
                        center_y - CENTER_POINT[1]
                    )

                    offset_meters = offset_pixels / PIXELS_PER_METER

                    real_width_cm = REAL_WIDTH_CM.get(
                        name,
                        DEFAULT_WIDTH_CM
                    )

                    distance_cm = estimate_distance(
                        real_width_cm,
                        width_pixels
                    )

                    distance_label = (
                        f"Tavolsag: {round(distance_cm, 1)}cm | "
                        f"Eltolodas: {offset_meters:.2f}m"
                    )

                    cv2.putText(
                        annotated_frame,
                        distance_label,
                        (x1, min(IMAGE_HEIGHT - 10, y2 + 20)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (220, 220, 220),
                        2
                    )

                # Képfrissítés
                current_time = time.time()

                fps = (
                    1.0 / (current_time - previous_time)
                    if (current_time - previous_time) > 0
                    else 0
                )

                previous_time = current_time

                cv2.putText(
                    annotated_frame,
                    f"Hailo-8 | Fps: {fps:.1f}",
                    (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 255),
                    2
                )

                # Megjelenítés
                video_writer.write(annotated_frame)
                cv2.imshow("Hailo-8 kamera", annotated_frame)

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break


# Lezárás
video_writer.release()
cv2.destroyAllWindows()
camera.stop()
