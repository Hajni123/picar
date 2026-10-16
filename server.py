import cv2
import time
import threading
import numpy as np
from flask import Flask, Response, request
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

# --- 1. MOTOROK KONFIGURÁCIÓJA ---
feher_bal_elore  = PWMOutputDevice(7, frequency=100)
zold_bal_hatra   = PWMOutputDevice(8, frequency=100)
barna_jobb_elore = PWMOutputDevice(25, frequency=100)
sarga_jobb_hatra = PWMOutputDevice(27, frequency=100)

def stop_motors():
    feher_bal_elore.value = 0
    zold_bal_hatra.value = 0
    barna_jobb_elore.value = 0
    sarga_jobb_hatra.value = 0

def drive(bal, jobb):
    zold_bal_hatra.value = 0
    sarga_jobb_hatra.value = 0
    feher_bal_elore.value = max(0.0, min(1.0, bal))
    barna_jobb_elore.value = max(0.0, min(1.0, jobb))

# --- 2. KAMERA ELŐKÉSZÍTÉSE ---
picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"size": (640, 480), "format": "RGB888"})
picam2.configure(config)
picam2.start()
time.sleep(0.5)

# --- 3. PARAMÉTEREK ÉS GLOBÁLIS ÁLLAPOTOK ---
current_mode = "manual"
latest_frame = None
lock = threading.Lock()

CURRENT_SPEED = 0.35
KANYAR_SZORZO = 0.20
MIN_SPEED = 0.22

# --- 4. FLASK WEBSZERVER ---
app = Flask(__name__)

def hailo_worker():
    global current_mode, latest_frame, CURRENT_SPEED
    hef = HEF("flashfire_model.hef")
    params = VDevice.create_params()

    with VDevice(params) as target:
        configure_params = ConfigureParams.create_from_hef(hef, interface=HailoStreamInterface.PCIe)
        network_group = target.configure(hef, configure_params)[0]

        in_params = InputVStreamParams.make(network_group, format_type=FormatType.UINT8)
        out_params = OutputVStreamParams.make(network_group, format_type=FormatType.FLOAT32)

        in_info = hef.get_input_vstream_infos()[0]
        out_info = hef.get_output_vstream_infos()[0]
        req_h, req_w = in_info.shape[0], in_info.shape[1]

        with network_group.activate():
            with InferVStreams(network_group, in_params, out_params) as pipeline:
                while True:
                    frame = picam2.capture_array()
                    with lock:
                        latest_frame = frame.copy()

                    if current_mode == "autopilot":
                        resized = cv2.resize(frame, (req_w, req_h))
                        input_data = np.expand_dims(resized, axis=0).astype(np.uint8)

                        res = pipeline.infer({in_info.name: input_data})
                        out = res[out_info.name][0]

                        val_bal = float(out[0])
                        val_jobb = float(out[1]) if len(out) > 1 else float(out[0])

                        diff = (val_jobb - val_bal) * KANYAR_SZORZO
                        bal_pwm = max(MIN_SPEED, min(1.0, CURRENT_SPEED - diff))
                        jobb_pwm = max(MIN_SPEED, min(1.0, CURRENT_SPEED + diff))

                        drive(bal_pwm, jobb_pwm)
                    time.sleep(0.01)

def generate_stream():
    global latest_frame
    while True:
        if latest_frame is None:
            time.sleep(0.05)
            continue
        with lock:
            frame = latest_frame.copy()

        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate_stream(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/cmd')
def handle_cmd():
    global current_mode, CURRENT_SPEED
    action = request.args.get('action', '')

    # Sebesség beállítás
    if action.startswith("speed_"):
        try:
            percent = int(action.split("_")[1])
            CURRENT_SPEED = max(0.20, min(1.0, percent / 100.0))
            print(f"[SEBESSÉG] Frissítve: {percent}% ({CURRENT_SPEED:.2f})")
        except ValueError:
            pass
        return f"OK: speed set to {CURRENT_SPEED}"

    # Üzemmódok
    if action == "mode_1":
        current_mode = "manual"
        stop_motors()
    elif action == "mode_2":
        current_mode = "autopilot"
    elif action in ["stop", "release"]:
        if current_mode == "manual":
            stop_motors()

    # Kézi parancsok és íves mozgások
    elif current_mode == "manual":
        if action == "forward":
            drive(CURRENT_SPEED, CURRENT_SPEED)
        elif action == "backward":
            feher_bal_elore.value = 0
            barna_jobb_elore.value = 0
            zold_bal_hatra.value = CURRENT_SPEED
            sarga_jobb_hatra.value = CURRENT_SPEED
        elif action == "left":
            feher_bal_elore.value = 0
            barna_jobb_elore.value = CURRENT_SPEED
        elif action == "right":
            feher_bal_elore.value = CURRENT_SPEED
            barna_jobb_elore.value = 0
        elif action == "forward_left":
            drive(CURRENT_SPEED * 0.45, CURRENT_SPEED)
        elif action == "forward_right":
            drive(CURRENT_SPEED, CURRENT_SPEED * 0.45)
        elif action == "backward_left":
            feher_bal_elore.value = 0
            barna_jobb_elore.value = 0
            zold_bal_hatra.value = CURRENT_SPEED * 0.45
            sarga_jobb_hatra.value = CURRENT_SPEED
        elif action == "backward_right":
            feher_bal_elore.value = 0
            barna_jobb_elore.value = 0
            zold_bal_hatra.value = CURRENT_SPEED
            sarga_jobb_hatra.value = CURRENT_SPEED * 0.45

    return f"OK: {action}"

if __name__ == '__main__':
    t = threading.Thread(target=hailo_worker, daemon=True)
    t.start()
    app.run(host='0.0.0.0', port=5000, threaded=True)
