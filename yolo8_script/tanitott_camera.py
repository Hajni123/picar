# A saját betanított YOLO-modell kamerás tesztje.
# Hailo és motorvezérlés nélkül.

import subprocess

import cv2
import numpy as np
from ultralytics import YOLO
from ultralytics.utils.plotting import colors


# Modell
MODEL_PATH = "/home/khajni/yolo8_script/runs/jelzesek_v1/weights/best.pt"
model = YOLO(MODEL_PATH)

print("Saját betanított modell indul. Kilépés: q")


while True:
    # Képfelvétel
    command = [
        "rpicam-jpeg", "-o", "-", "-t", "1",
        "--width", "640", "--height", "640", "-n"
    ]

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL
    )

    if result.returncode != 0:
        continue

    image_data = np.frombuffer(result.stdout, np.uint8)
    frame = cv2.imdecode(image_data, cv2.IMREAD_COLOR)

    if frame is None:
        continue

    # Felismerés
    results = model(
        frame,
        conf=0.25,
        imgsz=320,
        verbose=False
    )

    annotated_frame = frame.copy()

    # Jelölések
    for box in results[0].boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
        class_id = int(box.cls[0])
        confidence = float(box.conf[0])
        name = model.names[class_id]
        label = f"{name} {confidence * 100:.0f}%"

        color = colors(class_id, bgr=True)

        cv2.rectangle(
            annotated_frame,
            (x1, y1),
            (x2, y2),
            color,
            2
        )

        cv2.putText(
            annotated_frame,
            label,
            (x1, max(y1 - 8, 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            2
        )

    # Időmérés
    inference_time = results[0].speed["inference"]

    fps = (
        1000 / inference_time
        if inference_time > 0
        else 0
    )

    # Megjelenítés
    cv2.putText(
        annotated_frame,
        f"Sajat ai | Fps: {fps:.1f}",
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 0),
        2
    )

    cv2.imshow("Sajat model kamera", annotated_frame)

    # Billentyűkezelés
    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):
        break


cv2.destroyAllWindows()
