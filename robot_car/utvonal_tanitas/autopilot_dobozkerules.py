# Kamerakép alapján végzett CNN-motorvezérlés PyTorch használatával.

import time

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


# Modell
model = FlashFireCNN()
model.load_state_dict(
    torch.load("flashfire_model.pth", map_location="cpu")
)
model.eval()


# Kamera
IMAGE_WIDTH = 160
IMAGE_HEIGHT = 120

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


# Ablak
pygame.init()

DISPLAY_WIDTH = 320
DISPLAY_HEIGHT = 240

screen = pygame.display.set_mode(
    (DISPLAY_WIDTH, DISPLAY_HEIGHT)
)
pygame.display.set_caption("PiCar - Utvonalkovetes")

frame_count = 0

try:
    while True:
        # Eseménykezelés
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise KeyboardInterrupt

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    raise KeyboardInterrupt

        # Képfelvétel
        raw_frame = camera.capture_array()

        if raw_frame is None:
            continue

        if raw_frame.shape[2] == 4:
            raw_frame = raw_frame[:, :, :3]

        # Előfeldolgozás
        image_array = raw_frame.astype(np.float32) / 255.0
        image_array = np.transpose(image_array, (2, 0, 1))
        image_array = np.ascontiguousarray(image_array)

        input_tensor = torch.from_numpy(
            image_array
        ).unsqueeze(0)

        # Következtetés
        with torch.no_grad():
            output = model(input_tensor)

        # Motorvezérlés
        left_pwm = float(output[0][0])
        right_pwm = float(output[0][1])

        left_pwm = max(0.10, min(0.45, left_pwm))
        right_pwm = max(0.10, min(0.45, right_pwm))

        left_backward.value = 0
        right_backward.value = 0

        left_forward.value = left_pwm
        right_forward.value = right_pwm

        # Megjelenítés
        frame_count += 1

        if frame_count % 4 == 0:
            display_frame = raw_frame[..., ::-1]

            enlarged_frame = np.repeat(
                np.repeat(display_frame, 2, axis=0),
                2,
                axis=1
            )

            enlarged_frame = np.ascontiguousarray(enlarged_frame)

            surface = pygame.image.frombuffer(
                enlarged_frame.tobytes(),
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
