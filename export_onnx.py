import torch
from model import FlashFireCNN

# Modell betöltése
model = FlashFireCNN()
model.load_state_dict(torch.load("flashfire_model.pth", map_location="cpu"))
model.eval()

# Dummy bemenet (1 kép, 3 csatorna, 120 magasság, 160 szélesség)
dummy_input = torch.randn(1, 3, 120, 160)

# Exportálás a stabil beépített motorral
torch.onnx.export(
    model,
    dummy_input,
    "flashfire_model.onnx",
    export_params=True,
    opset_version=11,
    input_names=['input'],
    output_names=['output'],
    dynamo=False  # Kikapcsolja az onnxscript kényszerítést
)

print("Sikeres exportálás: flashfire_model.onnx készen áll!")
