import time
import cv2
import numpy as np
from picamera2 import Picamera2
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

print("[1/3] Kamera indítása...")
picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"size": (640, 480), "format": "RGB888"})
picam2.configure(config)
picam2.start()
time.sleep(1.0)

print("[2/3] Hailo modell betöltése...")
hef = HEF("flashfire_model.hef")
params = VDevice.create_params()

with VDevice(params) as target:
    configure_params = ConfigureParams.create_from_hef(hef, interface=HailoStreamInterface.PCIe)
    network_group = target.configure(hef, configure_params)[0]

    input_vstreams_params = InputVStreamParams.make(network_group, format_type=FormatType.UINT8)
    output_vstreams_params = OutputVStreamParams.make(network_group, format_type=FormatType.FLOAT32)

    input_vstream_info = hef.get_input_vstream_infos()[0]
    output_vstream_info = hef.get_output_vstream_infos()[0]

    req_h = input_vstream_info.shape[0]
    req_w = input_vstream_info.shape[1]

    print("[3/3] Teszt indítása (Mozgasd a kamerát tárgyak előtt!). Megállítás: Ctrl+C\n")

    with network_group.activate():
        with InferVStreams(network_group, input_vstreams_params, output_vstreams_params) as infer_pipeline:
            try:
                while True:
                    raw_frame = picam2.capture_array()
                    if raw_frame is None:
                        continue

                    # Bemenet előkészítése
                    resized = cv2.resize(raw_frame, (req_w, req_h))
                    input_data = np.ascontiguousarray(np.expand_dims(resized, axis=0), dtype=np.uint8)

                    # Következtetés
                    infer_results = infer_pipeline.infer({input_vstream_info.name: input_data})
                    pred = infer_results[output_vstream_info.name].flatten()

                    pred_bal = float(pred[0])
                    pred_jobb = float(pred[1]) if len(pred) > 1 else float(pred[0])
                    diff = pred_bal - pred_jobb

                    print(f"\rBal: {pred_bal:8.4f} | Jobb: {pred_jobb:8.4f} | Diff: {diff:+8.4f}", end="", flush=True)
                    time.sleep(0.05)

            except KeyboardInterrupt:
                print("\nTeszt vége.")
            finally:
                picam2.stop()
