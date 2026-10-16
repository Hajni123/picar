import time
import numpy as np
import onnxruntime as ort
from picamera2 import Picamera2
from gpiozero import PWMOutputDevice

# --- MOTORVEZÉRLÉS ---
feher_bal_elore  = PWMOutputDevice(7, frequency=100)
zold_bal_hatra   = PWMOutputDevice(8, frequency=100)
barna_jobb_elore = PWMOutputDevice(25, frequency=100)
sarga_jobb_hatra = PWMOutputDevice(27, frequency=100)

def stop():
    feher_bal_elore.value = 0
    zold_bal_hatra.value = 0
    barna_jobb_elore.value = 0
    sarga_jobb_hatra.value = 0

# --- BEVÁLT VEZÉRLÉSI PARAMÉTEREK ---
BASE_SPEED = 0.35
ALPHA = 0.30
filtered_diff = 0.0

def apply_filtered_motors(pred_bal, pred_jobb):
    global filtered_diff

    raw_diff = pred_bal - pred_jobb
    filtered_diff = (ALPHA * raw_diff) + ((1.0 - ALPHA) * filtered_diff)
    abs_diff = abs(filtered_diff)

    # A régi, jól bevált határozott küszöbértékek
    if abs_diff > 0.025:
        mode = "ELES KIKERULES"
        turn = np.sign(filtered_diff) * 0.13
        bal_val  = BASE_SPEED + turn
        jobb_val = BASE_SPEED - turn
    elif abs_diff > 0.010:
        mode = "FINOM RATERES"
        turn = np.sign(filtered_diff) * 0.07
        bal_val  = BASE_SPEED + turn
        jobb_val = BASE_SPEED - turn
    else:
        mode = "EGYENES"
        bal_val  = BASE_SPEED
        jobb_val = BASE_SPEED

    bal_val = max(0.14, min(0.55, bal_val))
    jobb_val = max(0.14, min(0.55, jobb_val))

    zold_bal_hatra.value = 0
    sarga_jobb_hatra.value = 0
    feher_bal_elore.value = bal_val
    barna_jobb_elore.value = jobb_val

    return filtered_diff, mode

# --- ONNX ENGINE BETÖLTÉSE ---
opts = ort.SessionOptions()
opts.intra_op_num_threads = 4
session = ort.InferenceSession("flashfire_model.onnx", opts)
input_name = session.get_inputs()[0].name

# --- KAMERA HARDVERES GYORSÍTÁSSAL ---
WIDTH, HEIGHT = 160, 120
picam2 = Picamera2()
config = picam2.create_preview_configuration(
    main={"size": (WIDTH, HEIGHT), "format": "RGB888"}
)
picam2.configure(config)
picam2.start()
time.sleep(0.5)

print("\n==========================================")
print("  ONNX AUTOPILOT (A BEVÁLT RÉGI LOGIKÁVAL)")
print("  Leállítás: Ctrl + C")
print("==========================================\n")

try:
    while True:
        t_start = time.time()

        raw_frame = picam2.capture_array()
        if raw_frame is None:
            continue

        # Normalizálás és ONNX formátum (1, 3, 120, 160)
        img_data = (raw_frame.astype(np.float32) / 255.0).transpose(2, 0, 1)
        input_tensor = np.expand_dims(img_data, axis=0)

        # ONNX Predikció
        outputs = session.run(None, {input_name: input_tensor})
        pred = outputs[0][0]
        pred_bal = float(pred[0])
        pred_jobb = float(pred[1])

        # A bevált szűrt és zónás irányítás
        filt_val, mode = apply_filtered_motors(pred_bal, pred_jobb)

        fps = 1.0 / (time.time() - t_start)
        print(f"\rFPS: {fps:4.1f} | B: {pred_bal:.2f} | J: {pred_jobb:.2f} | Diff: {filt_val:+.4f} | {mode:<14}", end="")

except KeyboardInterrupt:
    print("\nLeállítás...")
finally:
    stop()
    picam2.stop()
    print("Robot leállítva.")
