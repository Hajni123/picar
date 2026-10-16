import os
import cv2
import numpy as np

# Add meg a robot kameraképeit tartalmazó mappa elérési útját
IMAGE_DIR = "data"  
OUT_PATH = "calib_data.npy"

images = []
valid_extensions = (".jpg", ".jpeg", ".png")

# Képek összegyűjtése (rekurzívan, ha almappákban vannak)
for root, _, files in os.walk(IMAGE_DIR):
    for file in sorted(files):
        if file.lower().endswith(valid_extensions):
            img_path = os.path.join(root, file)
            img = cv2.imread(img_path)
            if img is not None:
                # RGB konverzió és átméretezés a modell 160x120 méretére
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                resized = cv2.resize(img_rgb, (160, 120))
                images.append(resized)
            if len(images) >= 128:
                break
    if len(images) >= 128:
        break

if len(images) < 16:
    raise ValueError(f"Túl kevés kép található a megadott mappában ({len(images)} db).")

calib_array = np.array(images, dtype=np.uint8)
np.save(OUT_PATH, calib_array)
print(f"[SIKER] {len(images)} kép elmentve kalibrációhoz ide: {OUT_PATH} (Shape: {calib_array.shape})")
