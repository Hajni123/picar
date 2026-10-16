import time

import numpy as np
import onnxruntime as ort
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
BASE_SPEED = 0.35
ALPHA = 0.30

filtered_difference = 0.0


# Motorvezérlés
def apply_filtered_motors(raw_left, raw_right):
    global filtered_difference

    raw_difference = raw_left - raw_right

    filtered_difference = (
        ALPHA * raw_difference
        + (1.0 - ALPHA) * filtered_difference
    )

    absolute_difference = abs(filtered_difference)

    if absolute_difference > 0.025:
        mode = "Eles kikerules"
        turn = np.sign(filtered_difference) * 0.13
        left_pwm = BASE_SPEED + turn
        right_pwm = BASE_SPEED - turn

    elif absolute_difference > 0.010:
        mode = "Finom rateres"
        turn = np.sign(filtered_difference) * 0.07
        left_pwm = BASE_SPEED + turn
        right_pwm = BASE_SPEED - turn

    else:
        mode = "Egyenes"
        left_pwm = BASE_SPEED
        right_pwm = BASE_SPEED

    left_pwm = max(0.14, min(0.55, left_pwm))
    right_pwm = max(0.14, min(0.55, right_pwm))

    left_backward.value = 0
    right_backward.value = 0

    left_forward.value = left_pwm
    right_forward.value = right_pwm

    return filtered_difference, mode


# Modell
session_options = ort.SessionOptions()
session_options.intra_op_num_threads = 4

session = ort.InferenceSession(
    "flashfire_model.onnx",
    session_options
)

input_name = session.get_inputs()[0].name


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

print("  Leállítás: Ctrl + C")


try:
    while True:
        start_time = time.time()

        # Képfelvétel
        raw_frame = camera.capture_array()

        if raw_frame is None:
            continue

        # Előfeldolgozás
        image_array = (
            raw_frame.astype(np.float32) / 255.0
        ).transpose(2, 0, 1)

        input_tensor = np.expand_dims(
            image_array,
            axis=0
        )

        # Következtetés
        outputs = session.run(
            None,
            {input_name: input_tensor}
        )

        prediction = outputs[0][0]

        raw_left = float(prediction[0])
        raw_right = float(prediction[1])

        # Vezérlés
        filtered_value, mode = apply_filtered_motors(
            raw_left,
            raw_right
        )

        # Visszajelzés
        fps = 1.0 / (time.time() - start_time)

        print(
            f"\rFps: {fps:4.1f} | "
            f"Bal: {raw_left:.2f} | "
            f"Jobb: {raw_right:.2f} | "
            f"Kulonbseg: {filtered_value:+.4f} | "
            f"{mode:<14}",
            end=""
        )

except KeyboardInterrupt:
    print("\nLeállítás...")

finally:
    stop()
    camera.stop()
    print("Robot leállítva.")
