import cv2
import numpy as np

from picamera2 import Picamera2
from hailo_platform import (
    HEF,
    VDevice,
    ConfigureParams,
    HailoStreamInterface,
    InferVStreams,
    InputVStreamParams,
    OutputVStreamParams,
    FormatType,
)


# Beállítások
HEF_PATH = "picar_jelzesek_palya.hef"

CLASS_NAMES = ["balra", "jobbra", "polya"]

CONFIDENCE_THRESHOLD = 0.45
IOU_THRESHOLD = 0.45


# Kamera
camera = Picamera2()

camera_config = camera.create_preview_configuration(
    main={
        "size": (640, 640),
        "format": "RGB888"
    }
)

camera.configure(camera_config)
camera.start()


# Hálózat
hef = HEF(HEF_PATH)

device_params = VDevice.create_params()
device = VDevice(device_params)

configure_params = ConfigureParams.create_from_hef(
    hef,
    interface=HailoStreamInterface.PCIe
)

network_groups = device.configure(
    hef,
    configure_params
)
network_group = network_groups[0]

network_group_params = network_group.create_params()

input_vstream_params = InputVStreamParams.make_from_network_group(
    network_group,
    quantized=False,
    format_type=FormatType.FLOAT32
)

output_vstream_params = OutputVStreamParams.make_from_network_group(
    network_group,
    quantized=False,
    format_type=FormatType.FLOAT32
)

input_info = hef.get_input_vstream_infos()[0]
output_infos = hef.get_output_vstream_infos()

input_name = input_info.name

print("Hailo modell:", HEF_PATH)
print("Bemenet:", input_name)

for output_info in output_infos:
    print("Kimenet:", output_info.name, output_info.shape)


# Aktiváció
def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


# Futtatás
with InferVStreams(
    network_group,
    input_vstream_params,
    output_vstream_params
) as pipeline:
    with network_group.activate(network_group_params):
        while True:
            # Képfelvétel
            frame = camera.capture_array()

            # Előfeldolgozás
            input_image = cv2.resize(frame, (320, 320))
            input_image = input_image.astype(np.float32)

            input_data = {
                input_name: np.expand_dims(
                    input_image,
                    axis=0
                )
            }

            # Következtetés
            results = pipeline.infer(input_data)

            # Kimenetek
            regression_output = None
            classification_output = None

            for name, data in results.items():
                output_array = np.asarray(data)
                output_array = np.squeeze(output_array)

                if output_array.shape == (2100, 64):
                    regression_output = output_array

                elif output_array.shape == (2100, 3):
                    classification_output = output_array

            if (
                regression_output is None
                or classification_output is None
            ):
                print("Nem találom a YOLO kimeneteket.")

                for name, data in results.items():
                    print(name, np.asarray(data).shape)

                break

            # Pontszámok
            if (
                classification_output.min() < 0
                or classification_output.max() > 1
            ):
                scores = sigmoid(classification_output)
            else:
                scores = classification_output

            best_index = np.unravel_index(
                np.argmax(scores),
                scores.shape
            )

            object_index = best_index[0]
            class_id = best_index[1]

            confidence = float(
                scores[object_index, class_id]
            )

            # Feliratozás
            if confidence >= CONFIDENCE_THRESHOLD:
                name = CLASS_NAMES[class_id]

                cv2.putText(
                    frame,
                    f"{name} {confidence:.2f}",
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (220, 220, 220),
                    2
                )

            # Megjelenítés
            cv2.imshow("PiCar - Hailo", frame)

            key = cv2.waitKey(1) & 0xFF

            if key == 27 or key == ord("q"):
                break


# Lezárás
cv2.destroyAllWindows()
camera.stop()
