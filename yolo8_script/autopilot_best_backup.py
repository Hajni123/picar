# Korábbi önvezető tesztprogram: kamerakép alapján, szűrt
# motorérték-különbséggel vezérel. CPU-n fut, Hailo nélkül.
# Indítás után automatikusan elindítja a motorokat.
import cv2
import numpy as np
import pygame
import torch

from gpiozero import PWMOutputDevice
from picamera2 import Picamera2

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
ALPHA = 0.30
BASE_SPEED = 0.35

filtered_difference = 0.0
bias_offset = 0.0
calibration_values = []
calibrated = False


# Motorvezérlés
def apply_filtered_motors(raw_left, raw_right):
    global filtered_difference, calibrated, bias_offset

    raw_difference = raw_left - raw_right

    # Kalibrálás
    if not calibrated:
        calibration_values.append(raw_difference)

        if len(calibration_values) >= 12:
            bias_offset = (
                sum(calibration_values)
                / len(calibration_values)
            )
            calibrated = True

            print(
                f"\n[Kalibracio kesz] "
                f"Alapzaj kiszurve: {bias_offset:+.4f}\n"
            )

        left_forward.value = BASE_SPEED
        right_forward.value = BASE_SPEED
        return 0.0, "Kalibracio"

    # Szűrés
    corrected_difference = raw_difference - bias_offset

    filtered_difference = (
        ALPHA * corrected_difference
    ) + (
        (1.0 - ALPHA) * filtered_difference
    )

    absolute_difference = abs(filtered_difference)

    # Kanyarodás
    if absolute_difference > 0.060:
        mode = "Eles kikerules"
        turn = np.sign(filtered_difference) * 0.13
        left_pwm = BASE_SPEED + turn
        right_pwm = BASE_SPEED - turn

    elif absolute_difference > 0.040:
        mode = "Finom rateres"
        turn = np.sign(filtered_difference) * 0.06
        left_pwm = BASE_SPEED + turn
        right_pwm = BASE_SPEED - turn

    else:
        mode = "Egyenes"
        left_pwm = BASE_SPEED
        right_pwm = BASE_SPEED

    # Korlátozás
    left_pwm = max(0.16, min(0.46, left_pwm))
    right_pwm = max(0.16, min(0.46, right_pwm))

    left_backward.value = 0
    right_backward.value = 0

    left_forward.value = left_pwm
    right_forward.value = right_pwm

    return filtered_difference, mode


# Modell
device = torch.device("cpu")
model = FlashFireCNN().to(device)

model.load_state_dict(
    torch.load(
        "flashfire_model.pth",
        map_location=device
    )
)

model.eval()


# Ablak
DISPLAY_WIDTH = 160
DISPLAY_HEIGHT = 120

pygame.init()

screen = pygame.display.set_mode(
    (DISPLAY_WIDTH, DISPLAY_HEIGHT)
)
pygame.display.set_caption("Ai kamera (kek doboz)")


# Kamera
camera = Picamera2()

camera_config = camera.create_preview_configuration(
    main={
        "size": (640, 480),
        "format": "RGB888"
    }
)

camera.configure(camera_config)
camera.start()

print("\n--- Önvezetés aktív (helyes színmegjelenítéssel) ---")
print("Megállítás: Esc az ablakban vagy Ctrl + C a terminálban\n")


try:
    with torch.no_grad():
        while True:
            # Eseménykezelés
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise KeyboardInterrupt

            if pygame.key.get_pressed()[pygame.K_ESCAPE]:
                break

            # Képfelvétel
            raw_frame = camera.capture_array()

            if raw_frame is None:
                continue

            # Előfeldolgozás
            resized_frame = cv2.resize(raw_frame, (120, 160))

            image_array = resized_frame.astype(np.float32) / 255.0
            image_array = np.transpose(image_array, (2, 0, 1))

            input_tensor = torch.tensor(
                image_array
            ).unsqueeze(0).to(device)

            # Következtetés
            prediction = model(input_tensor).numpy()[0]
            raw_left = float(prediction[0])
            raw_right = float(prediction[1])

            # Vezérlés
            filtered_value, mode = apply_filtered_motors(
                raw_left,
                raw_right
            )

            print(
                f"\rBal: {raw_left:.2f} | "
                f"Jobb: {raw_right:.2f} | "
                f"Diff: {filtered_value:+.4f} | "
                f"Mód: {mode:<16}",
                end=""
            )

            # Megjelenítés
            display_frame = cv2.resize(
                raw_frame,
                (DISPLAY_WIDTH, DISPLAY_HEIGHT)
            )

            rgb_frame = cv2.cvtColor(
                display_frame,
                cv2.COLOR_BGR2RGB
            )

            surface = pygame.image.frombuffer(
                rgb_frame.tobytes(),
                (DISPLAY_WIDTH, DISPLAY_HEIGHT),
                "RGB"
            )

            screen.blit(surface, (0, 0))
            pygame.display.flip()

except KeyboardInterrupt:
    print("\nLeállítás...")

finally:
    # Lezárás
    stop()
    camera.stop()
    pygame.quit()
