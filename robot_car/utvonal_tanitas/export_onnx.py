# A betanított PyTorch-modell ONNX-formátumba alakítása és ellenőrzése.

import numpy as np
import onnx
import onnxruntime as ort
import torch

from model import FlashFireCNN


# Modell
model = FlashFireCNN()

model.load_state_dict(
    torch.load(
        "flashfire_model.pth",
        map_location="cpu",
        weights_only=True
    )
)

model.eval()


# Tesztbemenet
dummy_input = torch.randn(1, 3, 120, 160)


# Exportálás
torch.onnx.export(
    model,
    dummy_input,
    "flashfire_model.onnx",
    export_params=True,
    opset_version=11,
    input_names=["input"],
    output_names=["output"],
    dynamo=False
)


# Ellenőrzés
onnx_model = onnx.load("flashfire_model.onnx")
onnx.checker.check_model(onnx_model)


# Betöltés
session = ort.InferenceSession(
    "flashfire_model.onnx",
    providers=["CPUExecutionProvider"]
)


# Következtetés
with torch.no_grad():
    pytorch_output = model(dummy_input).numpy()

onnx_output = session.run(
    ["output"],
    {"input": dummy_input.numpy()}
)[0]


# Összehasonlítás
max_difference = np.max(
    np.abs(pytorch_output - onnx_output)
)

print("ONNX export sikeres")
print("PyTorch kimenet:", pytorch_output)
print("ONNX kimenet:", onnx_output)
print("Maximalis elteres:", max_difference)

if not np.allclose(
    pytorch_output,
    onnx_output,
    rtol=1e-4,
    atol=1e-5
):
    raise RuntimeError(
        "Az ONNX kimenet elter a PyTorch kimenettol"
    )

print("A ket modell kimenete egyezik")
