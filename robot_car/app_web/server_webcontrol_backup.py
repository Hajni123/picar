# Korábbi webes motorvezérlés és Hailo-alapú CNN-útvonalkövetés.

import threading
import time

import cv2
import numpy as np
from flask import Flask, Response, request
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


# Motorvezérlés
def drive(left, right):
    left_backward.value = 0
    right_backward.value = 0
    left_forward.value = max(0.0, min(1.0, left))
    right_forward.value = max(0.0, min(1.0, right))


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
time.sleep(0.5)


# Beállítások
TURN_GAIN = 0.20
MIN_SPEED = 0.22

current_speed = 0.35
current_mode = "manual"
latest_frame = None
last_manual_action = None
lock = threading.Lock()


# Szerver
app = Flask(__name__)


# Következtetés
def hailo_worker():
    global current_mode, latest_frame, current_speed

    hef = HEF("flashfire_model.hef")
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
        input_height = input_info.shape[0]
        input_width = input_info.shape[1]

        with network_group.activate():
            with InferVStreams(
                network_group,
                input_params,
                output_params
            ) as pipeline:
                while True:
                    # Képfelvétel
                    frame = camera.capture_array()

                    with lock:
                        latest_frame = frame.copy()

                    # Útvonalkövetés
                    if current_mode == "autopilot":
                        resized_frame = cv2.resize(
                            frame,
                            (input_width, input_height)
                        )
                        input_data = np.expand_dims(
                            resized_frame,
                            axis=0
                        ).astype(np.uint8)

                        results = pipeline.infer({
                            input_info.name: input_data
                        })
                        output = results[output_info.name][0]

                        left_prediction = float(output[0])
                        right_prediction = (
                            float(output[1])
                            if len(output) > 1
                            else float(output[0])
                        )

                        difference = (
                            right_prediction - left_prediction
                        ) * TURN_GAIN

                        left_pwm = max(
                            MIN_SPEED,
                            min(1.0, current_speed - difference)
                        )
                        right_pwm = max(
                            MIN_SPEED,
                            min(1.0, current_speed + difference)
                        )

                        drive(left_pwm, right_pwm)

                    time.sleep(0.01)


# Képküldés
def generate_stream():
    global latest_frame

    while True:
        if latest_frame is None:
            time.sleep(0.05)
            continue

        with lock:
            frame = latest_frame.copy()

        success, jpeg_buffer = cv2.imencode(".jpg", frame)

        if not success:
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n"
            + jpeg_buffer.tobytes()
            + b"\r\n"
        )


# Videó
@app.route("/video_feed")
def video_feed():
    return Response(
        generate_stream(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


# Parancskezelés
@app.route("/cmd")
def handle_cmd():
    global current_mode, current_speed, last_manual_action

    action = request.args.get("action", "")

    # Sebesség
    if action.startswith("speed_"):
        try:
            percent = int(action.split("_")[1])
            current_speed = max(
                0.20,
                min(1.0, percent / 100.0)
            )
            print(
                f"Sebesség frissítve: {percent}% "
                f"({current_speed:.2f})"
            )

            if current_mode == "manual":
                if last_manual_action == "forward":
                    drive(current_speed, current_speed)

                elif last_manual_action == "backward":
                    left_forward.value = 0
                    right_forward.value = 0
                    left_backward.value = current_speed
                    right_backward.value = current_speed

                elif last_manual_action == "left":
                    left_forward.value = 0
                    right_forward.value = current_speed
                    left_backward.value = 0
                    right_backward.value = 0

                elif last_manual_action == "right":
                    left_forward.value = current_speed
                    right_forward.value = 0
                    left_backward.value = 0
                    right_backward.value = 0

        except ValueError:
            pass

        return f"OK: speed set to {current_speed}"

    # Üzemmódok
    if action == "mode_1":
        current_mode = "manual"
        last_manual_action = None
        stop()

    elif action == "mode_2":
        current_mode = "autopilot"
        last_manual_action = None

    elif action in ["stop", "release"]:
        last_manual_action = None

        if current_mode == "manual":
            stop()

    # Irányítás
    elif current_mode == "manual":
        last_manual_action = action

        if action == "forward":
            drive(current_speed, current_speed)

        elif action == "backward":
            left_forward.value = 0
            right_forward.value = 0
            left_backward.value = current_speed
            right_backward.value = current_speed

        elif action == "left":
            left_forward.value = 0
            right_forward.value = current_speed
            left_backward.value = 0
            right_backward.value = 0

        elif action == "right":
            left_forward.value = current_speed
            right_forward.value = 0
            left_backward.value = 0
            right_backward.value = 0

    return f"OK: {action}"


# Indítás
if __name__ == "__main__":
    worker_thread = threading.Thread(
        target=hailo_worker,
        daemon=True
    )
    worker_thread.start()

    app.run(
        host="0.0.0.0",
        port=5000,
        threaded=True
    )
