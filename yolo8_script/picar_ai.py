# Kézi motorvezérlés és kamerás YOLO-objektumfelismerés.
# A képfeldolgozás, Hailo nélkül.
# Közelítő távolságot számít és megjeleníti az objektumokat.

import math
import subprocess
import threading
import time

import cv2
import numpy as np
from gpiozero import PWMOutputDevice
from ultralytics import YOLO


# Motorok
DRIVE_SPEED = 0.38
TURN_SPEED = 0.30

left_forward = PWMOutputDevice(7, frequency=100)
left_backward = PWMOutputDevice(8, frequency=100)
right_forward = PWMOutputDevice(25, frequency=100)
right_backward = PWMOutputDevice(27, frequency=100)


# Leállítás
def stop():
    left_forward.value = 0
    left_backward.value = 0
    right_forward.value = 0
    right_backward.value = 0


# Előremenet
def move_forward(speed=DRIVE_SPEED):
    left_backward.value = 0
    right_backward.value = 0
    left_forward.value = speed
    right_forward.value = speed


# Hátramenet
def move_backward(speed=DRIVE_SPEED):
    left_forward.value = 0
    right_forward.value = 0
    left_backward.value = speed
    right_backward.value = speed


# Balra
def turn_left(speed=TURN_SPEED):
    left_forward.value = 0
    right_backward.value = 0
    left_backward.value = speed
    right_forward.value = speed


# Jobbra
def turn_right(speed=TURN_SPEED):
    left_backward.value = 0
    right_forward.value = 0
    left_forward.value = speed
    right_backward.value = speed


stop()


# Beállítások
IMAGE_WIDTH = 640
IMAGE_HEIGHT = 480
CENTER_POINT = (IMAGE_WIDTH // 2, IMAGE_HEIGHT // 2)
PIXELS_PER_METER = 111.0
FOCAL_LENGTH = 520.0

latest_frame = None
running = True
lock = threading.Lock()


# Kameraszál
def run_ai_camera():
    global latest_frame, running

    print("600 osztályos YOLO modell betöltése...")
    model = YOLO("yolov8n-oiv7.pt")
    print("Ai és kamera készen áll.")

    while running:
        # Képfelvétel
        command = [
            "rpicam-jpeg",
            "-o", "-",
            "-t", "1",
            "--width", str(IMAGE_WIDTH),
            "--height", str(IMAGE_HEIGHT),
            "-n"
        ]

        capture_result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )

        if capture_result.returncode != 0:
            continue

        image_data = np.frombuffer(
            capture_result.stdout,
            np.uint8
        )

        frame = cv2.imdecode(
            image_data,
            cv2.IMREAD_COLOR
        )

        if frame is None:
            continue

        cv2.circle(
            frame,
            CENTER_POINT,
            5,
            (0, 0, 255),
            -1
        )

        # Felismerés
        results = model(
            frame,
            conf=0.10,
            verbose=False
        )

        for result in results:
            boxes = result.boxes

            for box in boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                class_id = int(box.cls[0])
                name = model.names[class_id]
                confidence = float(box.conf[0])

                # Távolság
                width_pixels = max(1, x2 - x1)
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2

                distance_cm = (
                    15.0 * FOCAL_LENGTH
                ) / width_pixels

                offset_pixels = math.sqrt(
                    (center_x - CENTER_POINT[0]) ** 2
                    + (center_y - CENTER_POINT[1]) ** 2
                )

                offset_meters = offset_pixels / PIXELS_PER_METER

                # Jelölések
                cv2.rectangle(
                    frame,
                    (x1, y1),
                    (x2, y2),
                    (0, 255, 0),
                    2
                )

                cv2.line(
                    frame,
                    CENTER_POINT,
                    (center_x, center_y),
                    (0, 255, 0),
                    1
                )

                label = (
                    f"{name} ({int(confidence * 100)}%): "
                    f"~{int(distance_cm)}cm | "
                    f"{offset_meters:.2f}m"
                )

                cv2.putText(
                    frame,
                    label,
                    (x1, max(20, y1 - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (220, 220, 220),
                    2
                )

        # Feliratozás
        cv2.putText(
            frame,
            "Reszponziv kettos-szal vezérlés",
            (10, 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2
        )

        # Képátadás
        with lock:
            latest_frame = frame


# Szálindítás
camera_thread = threading.Thread(
    target=run_ai_camera,
    daemon=True
)
camera_thread.start()


# Ablak
WINDOW_NAME = "PiCar - Reszponziv ai navigacio"

cv2.namedWindow(
    WINDOW_NAME,
    cv2.WINDOW_NORMAL
)
cv2.resizeWindow(
    WINDOW_NAME,
    IMAGE_WIDTH,
    IMAGE_HEIGHT
)

print("--- Rendszer készen áll ---")
print(
    "Lenyomva tartva halad | "
    "Felengedve azonnal megáll | "
    "Q: Kilépés\n"
)


# Időzítés
KEY_TIMEOUT = 0.08
last_key_time = 0

try:
    while True:
        # Megjelenítés
        with lock:
            if latest_frame is not None:
                cv2.imshow(
                    WINDOW_NAME,
                    latest_frame
                )

        # Billentyűkezelés
        key = cv2.waitKeyEx(10)
        current_time = time.time()

        if key in [
            ord("w"), ord("W"),
            82, 65362, 2490368
        ]:
            move_forward()
            last_key_time = current_time

        elif key in [
            ord("s"), ord("S"),
            84, 65364, 2621440
        ]:
            move_backward()
            last_key_time = current_time

        elif key in [
            ord("a"), ord("A"),
            81, 65361, 2424832
        ]:
            turn_left()
            last_key_time = current_time

        elif key in [
            ord("d"), ord("D"),
            83, 65363, 2555904
        ]:
            turn_right()
            last_key_time = current_time

        elif key == ord(" "):
            stop()

        elif key in [ord("q"), ord("Q")]:
            break

        # Megállítás
        if current_time - last_key_time > KEY_TIMEOUT:
            stop()

finally:
    running = False
    stop()
    cv2.destroyAllWindows()
