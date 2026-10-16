import cv2
import numpy as np
import torch
import pygame

from picamera2 import Picamera2
from gpiozero import PWMOutputDevice
from model import FlashFireCNN


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
TRAIN_LEFT_PWM = 0.20
TRAIN_RIGHT_PWM = 0.27

AUTO_LEFT_PWM = 0.20
AUTO_RIGHT_PWM = 0.27

MIN_PWM = 0.10
MAX_PWM = 0.45

DISPLAY_WIDTH = 320
DISPLAY_HEIGHT = 240

turn_multiplier = 1.0

active = False
frame_count = 0

left_pwm = 0.0
right_pwm = 0.0

raw_left = 0.0
raw_right = 0.0


# Modell
model = FlashFireCNN()

model.load_state_dict(
    torch.load(
        "flashfire_model.pth",
        map_location="cpu",
        weights_only=True
    )
)

model.eval()


# Kamera
camera = Picamera2()

camera_config = camera.create_preview_configuration(
    main={
        "size": (160, 120),
        "format": "RGB888"
    }
)

camera.configure(camera_config)
camera.start()


# Ablak
pygame.init()

screen = pygame.display.set_mode(
    (DISPLAY_WIDTH, DISPLAY_HEIGHT)
)
pygame.display.set_caption("PiCar - Utvonalkovetes")
clock = pygame.time.Clock()

stop()

try:
    while True:
        clock.tick(30)

        # Eseménykezelés
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise KeyboardInterrupt

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    raise KeyboardInterrupt

                if event.key == pygame.K_SPACE:
                    active = not active

                    if not active:
                        stop()
                        left_pwm = 0.0
                        right_pwm = 0.0

                if event.key in (
                    pygame.K_EQUALS,
                    pygame.K_KP_PLUS
                ):
                    turn_multiplier = min(
                        2.0,
                        turn_multiplier + 0.1
                    )

                if event.key in (
                    pygame.K_MINUS,
                    pygame.K_KP_MINUS
                ):
                    turn_multiplier = max(
                        0.5,
                        turn_multiplier - 0.1
                    )

        # Képfelvétel
        frame = camera.capture_array()

        if frame is None:
            stop()
            active = False
            continue

        # Előfeldolgozás
        rgb_frame = frame[..., ::-1].copy()

        image_array = rgb_frame.astype(np.float32) / 255.0
        image_array = np.transpose(image_array, (2, 0, 1))

        input_tensor = torch.from_numpy(
            image_array.copy()
        ).unsqueeze(0)

        # Következtetés
        with torch.no_grad():
            prediction = model(input_tensor).cpu().numpy()[0]

        if (
            prediction.shape != (2,)
            or not np.all(np.isfinite(prediction))
        ):
            stop()
            active = False
            raise RuntimeError("Ervenytelen CNN kimenet")

        # Korrekció
        raw_left = float(prediction[0])
        raw_right = float(prediction[1])

        left_deviation = raw_left - TRAIN_LEFT_PWM
        right_deviation = raw_right - TRAIN_RIGHT_PWM

        target_left_pwm = float(np.clip(
            AUTO_LEFT_PWM + left_deviation * turn_multiplier,
            MIN_PWM,
            MAX_PWM
        ))

        target_right_pwm = float(np.clip(
            AUTO_RIGHT_PWM + right_deviation * turn_multiplier,
            MIN_PWM,
            MAX_PWM
        ))

        steering = left_deviation - right_deviation

        # Motorvezérlés
        if active:
            left_pwm = target_left_pwm
            right_pwm = target_right_pwm

            left_backward.value = 0
            right_backward.value = 0

            left_forward.value = left_pwm
            right_forward.value = right_pwm

        else:
            stop()
            left_pwm = 0.0
            right_pwm = 0.0

        # Visszajelzés
        frame_count += 1

        if frame_count % 3 == 0:
            print(
                f"\rCnn bal: {raw_left:.3f} | "
                f"Jobb: {raw_right:.3f} | "
                f"Kormany: {steering:+.3f} | "
                f"Cel bal: {target_left_pwm:.3f} | "
                f"Jobb: {target_right_pwm:.3f} | "
                f"Motor bal: {left_pwm:.3f} | "
                f"Jobb: {right_pwm:.3f} | "
                f"Aktiv: {active}     ",
                end="",
                flush=True
            )

            # Feliratozás
            display_frame = cv2.resize(
                rgb_frame,
                (DISPLAY_WIDTH, DISPLAY_HEIGHT)
            )

            status = "aktiv" if active else "stop"

            cv2.putText(
                display_frame,
                f"Autopilot: {status}",
                (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 255, 0) if active else (255, 0, 0),
                2
            )

            cv2.putText(
                display_frame,
                f"Cel bal: {target_left_pwm:.2f} "
                f"jobb: {target_right_pwm:.2f}",
                (10, 55),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.48,
                (255, 255, 255),
                1
            )

            cv2.putText(
                display_frame,
                f"Motor bal: {left_pwm:.2f} jobb: {right_pwm:.2f}",
                (10, 80),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.48,
                (255, 255, 255),
                1
            )

            cv2.putText(
                display_frame,
                f"Kormany: {steering:+.3f}",
                (10, 105),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.48,
                (255, 255, 255),
                1
            )

            cv2.putText(
                display_frame,
                f"Szorzo: {turn_multiplier:.1f}",
                (10, 130),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (255, 255, 255),
                1
            )

            cv2.putText(
                display_frame,
                "Space start/stop",
                (10, 220),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (255, 255, 255),
                1
            )

            # Megjelenítés
            surface = pygame.image.frombuffer(
                display_frame.tobytes(),
                (DISPLAY_WIDTH, DISPLAY_HEIGHT),
                "RGB"
            )

            screen.blit(surface, (0, 0))
            pygame.display.flip()

except KeyboardInterrupt:
    pass

finally:
    stop()
    camera.stop()
    pygame.quit()
    print("\nAutopilot leallitva.")
