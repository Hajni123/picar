# A PyTorch- és Hailo-modellek kimenetének és futási idejének
# összehasonlítása élő kameraképen, motorvezérlés nélkül.

import time

import cv2
import numpy as np
import pygame
import torch
from hailo_platform import (
    HEF,
    VDevice,
    HailoStreamInterface,
    InferVStreams,
    ConfigureParams,
    InputVStreamParams,
    OutputVStreamParams,
    FormatType
)
from picamera2 import Picamera2

from model import FlashFireCNN


# Modellek
torch.set_num_threads(2)

model = FlashFireCNN()
model.load_state_dict(
    torch.load(
        "flashfire_model.pth",
        map_location="cpu",
        weights_only=True
    )
)
model.eval()

hef = HEF("flashfire_model_uj.hef")

camera = None
pygame_started = False

try:
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
    pygame_started = True

    screen = pygame.display.set_mode((480, 360))
    pygame.display.set_caption("PyTorch - Hailo osszehasonlitas")

    font = pygame.font.SysFont(None, 26)
    clock = pygame.time.Clock()

    # Hálózat
    device_params = VDevice.create_params()

    with VDevice(device_params) as device:
        configure_params = ConfigureParams.create_from_hef(
            hef,
            interface=HailoStreamInterface.PCIe
        )

        network_group = device.configure(
            hef,
            configure_params
        )[0]

        network_params = network_group.create_params()

        input_params = InputVStreamParams.make(
            network_group,
            format_type=FormatType.UINT8
        )

        output_params = OutputVStreamParams.make(
            network_group,
            format_type=FormatType.FLOAT32
        )

        input_info = hef.get_input_vstream_infos()[0]
        output_info = hef.get_output_vstream_infos()[0]

        # Aktiválás
        with network_group.activate(network_params):
            with InferVStreams(
                network_group,
                input_params,
                output_params
            ) as pipeline:
                while True:
                    clock.tick(30)

                    # Eseménykezelés
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            raise KeyboardInterrupt

                        if event.type == pygame.KEYDOWN:
                            if event.key == pygame.K_ESCAPE:
                                raise KeyboardInterrupt

                    # Képfelvétel
                    frame = camera.capture_array()

                    if frame is None:
                        continue

                    if frame.ndim != 3:
                        raise RuntimeError("Hibas kamerakep")

                    if frame.shape[2] == 4:
                        frame = frame[:, :, :3]

                    # Előfeldolgozás
                    rgb_frame = frame[..., ::-1].copy()

                    image_array = (
                        rgb_frame.astype(np.float32) / 255.0
                    )

                    image_array = np.transpose(
                        image_array,
                        (2, 0, 1)
                    )

                    input_tensor = torch.from_numpy(
                        image_array.copy()
                    ).unsqueeze(0)

                    # PyTorch
                    start_time = time.perf_counter()

                    with torch.no_grad():
                        pytorch_prediction = (
                            model(input_tensor)
                            .cpu()
                            .numpy()
                            .reshape(-1)
                        )

                    pytorch_ms = (
                        time.perf_counter() - start_time
                    ) * 1000.0

                    # Hailo
                    hailo_input = {
                        input_info.name: np.expand_dims(
                            rgb_frame,
                            axis=0
                        ).astype(np.uint8)
                    }

                    start_time = time.perf_counter()

                    output_data = pipeline.infer(hailo_input)

                    hailo_ms = (
                        time.perf_counter() - start_time
                    ) * 1000.0

                    hailo_prediction = np.asarray(
                        output_data[output_info.name]
                    ).reshape(-1)

                    # Ellenőrzés
                    if (
                        pytorch_prediction.size != 2
                        or hailo_prediction.size != 2
                        or not np.all(np.isfinite(pytorch_prediction))
                        or not np.all(np.isfinite(hailo_prediction))
                    ):
                        raise RuntimeError("Ervenytelen modellkimenet")

                    # Összehasonlítás
                    pytorch_left, pytorch_right = map(
                        float,
                        pytorch_prediction
                    )
                    hailo_left, hailo_right = map(
                        float,
                        hailo_prediction
                    )

                    left_difference = hailo_left - pytorch_left
                    right_difference = hailo_right - pytorch_right

                    pytorch_steering = (
                        (pytorch_left - 0.20) - (pytorch_right - 0.27)
                    )

                    hailo_steering = (
                        (hailo_left - 0.20) - (hailo_right - 0.27)
                    )

                    # Visszajelzés
                    print(
                        f"\rPyTorch bal:{pytorch_left:.3f} "
                        f"jobb:{pytorch_right:.3f} "
                        f"| Hailo bal:{hailo_left:.3f} "
                        f"jobb:{hailo_right:.3f} "
                        f"| Elteres bal:{left_difference:+.3f} "
                        f"jobb:{right_difference:+.3f} "
                        f"| T:{pytorch_ms:.1f}ms "
                        f"H:{hailo_ms:.1f}ms       ",
                        end="",
                        flush=True
                    )

                    # Megjelenítés
                    display_frame = cv2.resize(
                        rgb_frame,
                        (480, 360)
                    )

                    surface = pygame.image.frombuffer(
                        display_frame.tobytes(),
                        (480, 360),
                        "RGB"
                    )

                    screen.blit(surface, (0, 0))

                    # Feliratozás
                    lines = [
                        (
                            f"PyTorch B:{pytorch_left:.3f} "
                            f"J:{pytorch_right:.3f}"
                        ),
                        (
                            f"Hailo   B:{hailo_left:.3f} "
                            f"J:{hailo_right:.3f}"
                        ),
                        (
                            f"Elteres B:{left_difference:+.3f} "
                            f"J:{right_difference:+.3f}"
                        ),
                        f"Kormany T:{pytorch_steering:+.3f}",
                        f"Kormany H:{hailo_steering:+.3f}",
                        f"Ido T:{pytorch_ms:.1f}ms H:{hailo_ms:.1f}ms",
                        "Esc: Kilepes - Motorok nem mukodnek"
                    ]

                    overlay = pygame.Surface(
                        (480, 175),
                        pygame.SRCALPHA
                    )
                    overlay.fill((0, 0, 0, 190))
                    screen.blit(overlay, (0, 0))

                    for index, line in enumerate(lines):
                        text_surface = font.render(
                            line,
                            True,
                            (255, 255, 255)
                        )
                        screen.blit(
                            text_surface,
                            (8, 6 + index * 24)
                        )

                    pygame.display.flip()

except KeyboardInterrupt:
    pass


finally:
    if camera is not None:
        camera.stop()

    if pygame_started:
        pygame.quit()

    print("\nOsszehasonlitas leallitva.")
