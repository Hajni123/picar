import csv
import os
import time

import cv2
import pygame

from gpiozero import PWMOutputDevice
from picamera2 import Picamera2


# Motorok
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


# Beállítások
LEFT_BASE_PWM = 0.20
RIGHT_BASE_PWM = 0.27
TURN_STRENGTH = 0.12

MIN_PWM = 0.10
MAX_PWM = 0.45

DATA_DIR = "data"
IMAGE_DIR = os.path.join(DATA_DIR, "images")
CSV_PATH = os.path.join(DATA_DIR, "labels.csv")

IMAGE_WIDTH = 160
IMAGE_HEIGHT = 120

os.makedirs(IMAGE_DIR, exist_ok=True)


# Vezérlő
pygame.init()
pygame.joystick.init()

controller = None

if pygame.joystick.get_count() > 0:
    controller = pygame.joystick.Joystick(0)
    controller.init()


# Ablak
screen = pygame.display.set_mode((320, 240))
pygame.display.set_caption("PiCar - Adatgyujtes")

clock = pygame.time.Clock()


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
time.sleep(0.5)


# Adatfájl
csv_file = open(CSV_PATH, "a", newline="")
csv_writer = csv.writer(csv_file)

frame_count = 0
recording = False

stop()

print("\nAdatgyujtes elindult")
print("Space: Rogzites be/ki")
print("Fel: Elore")
print("Le: Hatra")
print("Bal/jobb: Kormanyzas")
print("Esc: Kilepes")


try:
    while True:
        clock.tick(30)

        steering = 0.0
        throttle = 0.0

        # Eseménykezelés
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise KeyboardInterrupt

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    raise KeyboardInterrupt

                if event.key == pygame.K_SPACE:
                    recording = not recording

                    print(
                        "\nRogzites:",
                        "Be" if recording else "Ki"
                    )

        # Billentyűzet
        keys = pygame.key.get_pressed()

        if keys[pygame.K_UP] or keys[pygame.K_w]:
            throttle = 1.0

        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            throttle = -1.0

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            steering = -TURN_STRENGTH

        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            steering = TURN_STRENGTH

        # Vezérlő
        if controller:
            axis_x = controller.get_axis(0)
            axis_y = controller.get_axis(1)

            if abs(axis_x) > 0.20:
                steering = axis_x * TURN_STRENGTH

            if abs(axis_y) > 0.20:
                throttle = -axis_y

        # Motorvezérlés
        if throttle > 0:
            left_pwm = max(
                MIN_PWM,
                min(
                    MAX_PWM,
                    LEFT_BASE_PWM * throttle + steering
                )
            )

            right_pwm = max(
                MIN_PWM,
                min(
                    MAX_PWM,
                    RIGHT_BASE_PWM * throttle - steering
                )
            )

            left_backward.value = 0
            right_backward.value = 0

            left_forward.value = left_pwm
            right_forward.value = right_pwm

        elif throttle < 0:
            left_pwm = 0.0
            right_pwm = 0.0

            left_forward.value = 0
            right_forward.value = 0

            left_backward.value = 0.20
            right_backward.value = 0.20

        else:
            left_pwm = 0.0
            right_pwm = 0.0
            stop()

        # Képfelvétel
        raw_frame = camera.capture_array()

        if raw_frame is not None:
            rgb_frame = raw_frame[..., ::-1].copy()

            # Adatrögzítés
            if recording and throttle > 0:
                image_name = (
                    f"frame_{int(time.time() * 1000)}_"
                    f"{frame_count:05d}.jpg"
                )

                image_path = os.path.join(
                    IMAGE_DIR,
                    image_name
                )

                if cv2.imwrite(image_path, rgb_frame):
                    csv_writer.writerow([
                        os.path.join("images", image_name),
                        f"{left_pwm:.4f}",
                        f"{right_pwm:.4f}"
                    ])

                    csv_file.flush()
                    frame_count += 1

            # Feliratozás
            display_frame = cv2.resize(
                rgb_frame,
                (320, 240)
            )

            status = (
                "Rogzites: Be"
                if recording
                else "Rogzites: Ki"
            )

            cv2.putText(
                display_frame,
                status,
                (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.48,
                (0, 255, 0) if recording else (255, 255, 255),
                1
            )

            cv2.putText(
                display_frame,
                f"Bal: {left_pwm:.2f} Jobb: {right_pwm:.2f}",
                (10, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.48,
                (255, 255, 255),
                1
            )

            cv2.putText(
                display_frame,
                f"Kepek: {frame_count}",
                (10, 75),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.48,
                (255, 255, 255),
                1
            )

            # Megjelenítés
            surface = pygame.image.frombuffer(
                display_frame.tobytes(),
                (320, 240),
                "RGB"
            )

            screen.blit(surface, (0, 0))
            pygame.display.flip()

            # Kiírások
            print(
                f"\rBal: {left_pwm:.2f} | "
                f"Jobb: {right_pwm:.2f} | "
                f"Kormany: {steering:+.2f} | "
                f"Kepek: {frame_count}    ",
                end="",
                flush=True
            )

except KeyboardInterrupt:
    pass

finally:
    stop()
    csv_file.close()
    camera.stop()
    pygame.quit()
    print("\nAdatgyujtes leallitva.")
