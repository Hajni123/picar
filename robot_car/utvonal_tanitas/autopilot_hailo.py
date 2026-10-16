import cv2
import numpy as np
import pygame

from picamera2 import Picamera2
from gpiozero import PWMOutputDevice

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

camera = None
pygame_started = False

stop()

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

    screen = pygame.display.set_mode(
        (DISPLAY_WIDTH, DISPLAY_HEIGHT)
    )
    pygame.display.set_caption("PiCar - Hailo Utvonalkovetes")

    clock = pygame.time.Clock()

    # Modell
    hef = HEF("flashfire_model_uj.hef")
    device_params = VDevice.create_params()

    with VDevice(device_params) as device:
        # Hálózat
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

                    if frame.ndim != 3:
                        stop()
                        active = False
                        raise RuntimeError("Hibas kamerakep")

                    if frame.shape[2] == 4:
                        frame = frame[:, :, :3]

                    # Előfeldolgozás
                    rgb_frame = frame[..., ::-1].copy()

                    input_data = {
                        input_info.name: np.expand_dims(
                            rgb_frame,
                            axis=0
                        ).astype(np.uint8)
                    }

                    # Következtetés
                    output_data = pipeline.infer(input_data)

                    prediction = np.asarray(
                        output_data[output_info.name]
                    ).reshape(-1)

                    if (
                        prediction.size != 2
                        or not np.all(np.isfinite(prediction))
                    ):
                        stop()
                        active = False
                        raise RuntimeError(
                            "Ervenytelen Hailo kimenet"
                        )

                    # Korrekció
                    raw_left = float(prediction[0])
                    raw_right = float(prediction[1])

                    left_deviation = raw_left - TRAIN_LEFT_PWM
                    right_deviation = raw_right - TRAIN_RIGHT_PWM

                    target_left_pwm = float(np.clip(
                        AUTO_LEFT_PWM
                        + left_deviation * turn_multiplier,
                        MIN_PWM,
                        MAX_PWM
                    ))

                    target_right_pwm = float(np.clip(
                        AUTO_RIGHT_PWM
                        + right_deviation * turn_multiplier,
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
                        if steering < -0.015:
                            direction = "Balra"
                        elif steering > 0.015:
                            direction = "Jobbra"
                        else:
                            direction = "Egyenes"

                        print(
                            f"\rHailo bal:{raw_left:.3f} "
                            f"jobb:{raw_right:.3f} | "
                            f"Kormany:{steering:+.3f} "
                            f"Irany:{direction} | "
                            f"Cel bal:{target_left_pwm:.3f} "
                            f"jobb:{target_right_pwm:.3f} | "
                            f"Motor bal:{left_pwm:.3f} "
                            f"jobb:{right_pwm:.3f} | "
                            f"Aktiv:{active}     ",
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
                            f"Hailo: {status}",
                            (10, 25),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.55,
                            (0, 255, 0) if active else (255, 0, 0),
                            2
                        )

                        cv2.putText(
                            display_frame,
                            f"Cnn bal:{raw_left:.3f} "
                            f"jobb:{raw_right:.3f}",
                            (10, 55),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.45,
                            (255, 255, 255),
                            1
                        )

                        cv2.putText(
                            display_frame,
                            f"Cel bal:{target_left_pwm:.3f} "
                            f"jobb:{target_right_pwm:.3f}",
                            (10, 80),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.45,
                            (255, 255, 255),
                            1
                        )

                        cv2.putText(
                            display_frame,
                            f"Kormany:{steering:+.3f} {direction}",
                            (10, 105),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.45,
                            (255, 255, 255),
                            1
                        )

                        cv2.putText(
                            display_frame,
                            f"Szorzo:{turn_multiplier:.1f}",
                            (10, 130),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.45,
                            (255, 255, 255),
                            1
                        )

                        cv2.putText(
                            display_frame,
                            "Space start/stop  Esc kilep",
                            (10, 225),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.38,
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

    if camera is not None:
        camera.stop()

    if pygame_started:
        pygame.quit()

    print("\nHailo autopilot leallitva.")
