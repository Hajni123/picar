import time
import numpy as np
from picamera2 import Picamera2
from hailo_platform import HEF, VDevice, HailoStreamInterface, InferVStreams, ConfigureParams, InputVStreamParams, OutputVStreamParams, FormatType
from gpiozero import PWMOutputDevice

# ==========================================
# 1. MOTORVEZÉRLÉS KONFIGURÁCIÓ
# ==========================================
feher_bal_elore  = PWMOutputDevice(7, frequency=100)
zold_bal_hatra   = PWMOutputDevice(8, frequency=100)
barna_jobb_elore = PWMOutputDevice(25, frequency=100)
sarga_jobb_hatra = PWMOutputDevice(27, frequency=100)

def stop_motors():
    feher_bal_elore.value = 0
    zold_bal_hatra.value = 0
    barna_jobb_elore.value = 0
    sarga_jobb_hatra.value = 0

# ==========================================
# 2. FOLYTONOS VONALKÖVETŐ VEZÉRLÉS
# ==========================================
BASE_SPEED = 0.28       # Stabil alapsebesség
KP = 5.0                # Kormányzási érzékenység (erősítés)
ALPHA = 0.25            # Mozgóátlag szűrő a rángatás kisimítására
filtered_diff = 0.0

def apply_motor_control(pred_bal, pred_jobb):
    global filtered_diff

    # Különbség képzése és simítása
    raw_diff = pred_bal - pred_jobb
    filtered_diff = (ALPHA * raw_diff) + ((1.0 - ALPHA) * filtered_diff)

    # Folytonos kormányszög korrekció (Nincs hirtelen kerékleállítás!)
    steering_correction = filtered_diff * KP

    # Bal és jobb kerekek finom differenciálása
    bal_val  = BASE_SPEED + steering_correction
    jobb_val = BASE_SPEED - steering_correction

    # Biztonsági határok: a kerekek sosem állnak meg (min 0.16), de nem pörögnek túl (max 0.45)
    bal_val  = max(0.16, min(0.45, bal_val))
    jobb_val = max(0.16, min(0.45, jobb_val))

    # Motorok kimeneteinek beállítása
    zold_bal_hatra.value = 0
    sarga_jobb_hatra.value = 0
    feher_bal_elore.value = bal_val
    barna_jobb_elore.value = jobb_val

    return filtered_diff, bal_val, jobb_val

# ==========================================
# 3. KAMERA INICIALIZÁLÁSA
# ==========================================
WIDTH, HEIGHT = 160, 120
picam2 = Picamera2()
config = picam2.create_preview_configuration(
    main={"size": (WIDTH, HEIGHT), "format": "RGB888"}
)
picam2.configure(config)
picam2.start()
time.sleep(0.5)

# ==========================================
# 4. HAILO-8 NPU INFERENCIA
# ==========================================
hef = HEF("flashfire_model.hef")

params = VDevice.create_params()
with VDevice(params) as target:
    configure_params = ConfigureParams.create_from_hef(hef, interface=HailoStreamInterface.PCIe)
    network_group = target.configure(hef, configure_params)[0]
    network_group_params = network_group.create_params()
    
    input_vstreams_params = InputVStreamParams.make(network_group, format_type=FormatType.UINT8)
    output_vstreams_params = OutputVStreamParams.make(network_group, format_type=FormatType.FLOAT32)

    input_vstream_info = hef.get_input_vstream_infos()[0]
    output_vstream_info = hef.get_output_vstream_infos()[0]

    print("\n==========================================")
    print("  HAILO AUTOPILOT - FOLYTONOS SÁVKÖVETÉS")
    print("  Leállítás: Ctrl + C")
    print("==========================================\n")

    try:
        with network_group.activate(network_group_params):
            with InferVStreams(network_group, input_vstreams_params, output_vstreams_params) as infer_pipeline:
                while True:
                    t_start = time.time()

                    frame = picam2.capture_array()
                    if frame is None:
                        continue

                    if frame.shape[2] == 4:
                        frame = frame[:, :, :3]

                    input_data = {input_vstream_info.name: np.expand_dims(frame, axis=0).astype(np.uint8)}

                    output_data = infer_pipeline.infer(input_data)
                    pred = output_data[output_vstream_info.name][0]

                    pred_bal = float(pred[0])
                    pred_jobb = float(pred[1])

                    f_diff, b_out, j_out = apply_motor_control(pred_bal, pred_jobb)

                    fps = 1.0 / (time.time() - t_start)
                    print(f"\rFPS: {fps:4.1f} | Diff: {f_diff:+.4f} | PWM: [B:{b_out:.2f} J:{j_out:.2f}] | Out:[{pred_bal:.3f}, {pred_jobb:.3f}]", end="")

    except KeyboardInterrupt:
        print("\nLeállítás...")
    finally:
        stop_motors()
        picam2.stop()
        print("Robot leállítva.")
