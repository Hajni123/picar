import csv
import os

import cv2
import numpy as np
import torch
import torch.nn as nn

from torch.utils.data import (
    DataLoader,
    Dataset,
    Subset,
    WeightedRandomSampler,
)

from model import FlashFireCNN


# Beállítások
CSV_PATH = "data/labels.csv"
MODEL_PATH = "flashfire_model.pth"

EPOCHS = 25
BATCH_SIZE = 32
LEARNING_RATE = 0.0005
TRAIN_RATIO = 0.80

TURN_THRESHOLD = 0.05
TURN_WEIGHT = 4.0
STRAIGHT_WEIGHT = 1.0

torch.manual_seed(42)
np.random.seed(42)


# Adatkészlet
class RobotDataset(Dataset):
    def __init__(self, csv_path):
        self.samples = []
        base_dir = os.path.dirname(csv_path)

        # Beolvasás
        with open(csv_path, "r", newline="") as csv_file:
            csv_reader = csv.reader(csv_file)

            for row in csv_reader:
                if len(row) < 3:
                    continue

                try:
                    left_pwm = float(row[1])
                    right_pwm = float(row[2])
                except ValueError:
                    continue

                if (
                    not np.isfinite(left_pwm)
                    or not np.isfinite(right_pwm)
                ):
                    continue

                image_path = os.path.join(base_dir, row[0])

                if os.path.isfile(image_path):
                    self.samples.append(
                        (image_path, left_pwm, right_pwm)
                    )

        print(f"Betöltött képek: {len(self.samples)}")

    def __len__(self):
        return len(self.samples)

    # Előfeldolgozás
    def __getitem__(self, index):
        image_path, left_pwm, right_pwm = self.samples[index]

        bgr_image = cv2.imread(image_path)

        if bgr_image is None:
            raise RuntimeError(
                f"Nem olvasható kép: {image_path}"
            )

        rgb_image = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)
        rgb_image = cv2.resize(rgb_image, (160, 120))

        image_array = rgb_image.astype(np.float32) / 255.0
        image_array = np.transpose(image_array, (2, 0, 1))

        input_tensor = torch.from_numpy(
            image_array.copy()
        )

        label_tensor = torch.tensor(
            [left_pwm, right_pwm],
            dtype=torch.float32
        )

        return input_tensor, label_tensor


# Ellenőrzés
if not os.path.isfile(CSV_PATH):
    raise SystemExit(
        f"Hiba: Nem található {CSV_PATH}"
    )

dataset = RobotDataset(CSV_PATH)

if len(dataset) < 10:
    raise SystemExit("Hiba: Túl kevés tanítókép!")


# Felosztás
train_size = int(len(dataset) * TRAIN_RATIO)

train_indices = list(range(train_size))
val_indices = list(range(train_size, len(dataset)))

train_dataset = Subset(dataset, train_indices)
val_dataset = Subset(dataset, val_indices)


# Súlyozás
sample_weights = []
straight_count = 0
turn_count = 0

for index in train_indices:
    _, left_pwm, right_pwm = dataset.samples[index]

    if abs(left_pwm - right_pwm) > TURN_THRESHOLD:
        sample_weights.append(TURN_WEIGHT)
        turn_count += 1
    else:
        sample_weights.append(STRAIGHT_WEIGHT)
        straight_count += 1

sampler = WeightedRandomSampler(
    weights=sample_weights,
    num_samples=len(train_dataset),
    replacement=True
)


# Adatbetöltés
train_loader = DataLoader(
    train_dataset,
    batch_size=BATCH_SIZE,
    sampler=sampler
)

val_loader = DataLoader(
    val_dataset,
    batch_size=BATCH_SIZE,
    shuffle=False
)

print(f"Tanítóképek: {len(train_dataset)}")
print(f"Ellenőrző képek: {len(val_dataset)}")
print(f"Egyenes tanítóképek: {straight_count}")
print(f"Kanyarodási tanítóképek: {turn_count}")
print(f"Kanyar súlyozás: {TURN_WEIGHT}x")


# Modell
device = torch.device("cpu")

model = FlashFireCNN().to(device)

criterion = nn.MSELoss()

optimizer = torch.optim.Adam(
    model.parameters(),
    lr=LEARNING_RATE
)

best_val_loss = float("inf")
best_epoch = 0

print(f"\nTanítás indul: {EPOCHS} epoch")


# Tanítás
for epoch in range(EPOCHS):
    model.train()
    train_loss_sum = 0.0

    for images, labels in train_loader:
        images = images.to(device)
        labels = labels.to(device)

        optimizer.zero_grad()

        outputs = model(images)

        if outputs.shape != labels.shape:
            raise RuntimeError(
                f"Hibás kimeneti méret: {outputs.shape}, "
                f"elvárt: {labels.shape}"
            )

        loss = criterion(outputs, labels)

        loss.backward()
        optimizer.step()

        train_loss_sum += loss.item() * images.size(0)

    train_loss = train_loss_sum / len(train_dataset)

    # Kiértékelés
    model.eval()
    val_loss_sum = 0.0

    with torch.no_grad():
        for images, labels in val_loader:
            images = images.to(device)
            labels = labels.to(device)

            outputs = model(images)

            loss = criterion(outputs, labels)

            val_loss_sum += loss.item() * images.size(0)

    val_loss = val_loss_sum / len(val_dataset)

    print(
        f"Epoch {epoch + 1:02d}/{EPOCHS} | "
        f"Train Loss: {train_loss:.6f} | "
        f"Val Loss: {val_loss:.6f}"
    )

    # Mentés
    if val_loss < best_val_loss:
        best_val_loss = val_loss
        best_epoch = epoch + 1

        torch.save(
            model.state_dict(),
            MODEL_PATH
        )


# Eredmények
print("\nTanítás befejezve!")
print(f"Legjobb epoch: {best_epoch}")
print(f"Legjobb Val Loss: {best_val_loss:.6f}")
print(f"Mentett modell: {MODEL_PATH}")
