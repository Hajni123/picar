# Kalibrációs képadatok előkészítése a Hailo-modell átalakításához.

import os

import cv2
import numpy as np


# Beállítások
IMAGE_DIR = "data/images"
MAX_IMAGES = 200


# Fájllista
image_files = sorted(
    filename for filename in os.listdir(IMAGE_DIR)
    if filename.lower().endswith(".jpg")
)

if not image_files:
    raise RuntimeError("Nem találhatók tanítóképek")


# Mintavétel
indices = np.linspace(
    0,
    len(image_files) - 1,
    min(MAX_IMAGES, len(image_files)),
    dtype=int
)

images = []


# Előfeldolgozás
for index in indices:
    image_path = os.path.join(IMAGE_DIR, image_files[index])
    image = cv2.imread(image_path)

    if image is None:
        continue

    image = cv2.resize(image, (160, 120))
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    images.append(image)

if not images:
    raise RuntimeError("Nem sikerült képeket beolvasni")


# Mentés
calibration_data = np.stack(images).astype(np.uint8)

np.save("calib_data.npy", calibration_data)


# Visszajelzés
print("Kalibrációs képek:", len(calibration_data))
print("Alak:", calibration_data.shape)
print("Típus:", calibration_data.dtype)
print("Minimum:", calibration_data.min())
print("Maximum:", calibration_data.max())
print("Kész: calib_data.npy")
