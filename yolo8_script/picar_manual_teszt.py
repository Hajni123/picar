# Kameraképes kézi motorvezérlési teszt, objektumfelismerés nélkül.

import subprocess

import cv2
import numpy as np
from gpiozero import PWMOutputDevice


# Motorok
DRIVE_SPEED = 0.45

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
def turn_left(speed=DRIVE_SPEED):
    left_forward.value = 0
    right_backward.value = 0
    left_backward.value = speed
    right_forward.value = speed


# Jobbra
def turn_right(speed=DRIVE_SPEED):
    left_backward.value = 0
    right_forward.value = 0
    left_forward.value = speed
    right_backward.value = speed


stop()


# Ablak
WINDOW_NAME = "PiCar - Kezi vezerles teszt"

cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
cv2.resizeWindow(WINDOW_NAME, 640, 640)

print("--- Kézi vezérlés teszt ---")
print(
    "W / ^ : Előre | S / v : Hátra | "
    "A / < : Balra | D / > : Jobbra | Q : Kilépés"
)

try:
    while True:
        # Képfelvétel
        command = [
            "rpicam-jpeg",
            "-o", "-",
            "-t", "1",
            "--width", "640",
            "--height", "480",
            "-n"
        ]

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )

        if result.returncode != 0:
            stop()
            continue

        image_data = np.frombuffer(
            result.stdout,
            np.uint8
        )

        frame = cv2.imdecode(
            image_data,
            cv2.IMREAD_COLOR
        )

        if frame is None:
            stop()
            continue

        # Megjelenítés
        cv2.putText(
            frame,
            "Iranyitas: wasd vagy nyilak",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )

        cv2.imshow(WINDOW_NAME, frame)

        # Billentyűkezelés
        key = cv2.waitKeyEx(30)

        if key in [ord("w"), ord("W"), 82, 65362, 2490368]:
            move_forward()

        elif key in [ord("s"), ord("S"), 84, 65364, 2621440]:
            move_backward()

        elif key in [ord("a"), ord("A"), 81, 65361, 2424832]:
            turn_left()

        elif key in [ord("d"), ord("D"), 83, 65363, 2555904]:
            turn_right()

        elif key in [ord("q"), ord("Q")]:
            break

        else:
            stop()

finally:
    stop()
    cv2.destroyAllWindows()
