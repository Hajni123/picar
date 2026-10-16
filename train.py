import os
import glob
import csv
import cv2
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from model import FlashFireCNN

# --- CÍMKEFÁJL (labels.csv) KERESÉSE ---
data_dirs = sorted(glob.glob("data/*"))
csv_candidates = [
    "data/labels.csv",
    "labels.csv"
]
if data_dirs:
    csv_candidates.insert(0, os.path.join(data_dirs[-1], "labels.csv"))

csv_path = None
for p in csv_candidates:
    if os.path.exists(p):
        csv_path = p
        break

if not csv_path:
    print("HIBA: Nem található labels.csv fájl!")
    exit()

print(f"Használt címkefájl: {csv_path}")

# --- ADATHALMAZ BETÖLTÉSE ---
class RobotDataset(Dataset):
    def __init__(self, csv_file):
        self.samples = []
        base_dir = os.path.dirname(csv_file)
        
        with open(csv_file, 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 3:
                    rel_img_path = row[0]
                    bal_pwm = float(row[1])
                    jobb_pwm = float(row[2])
                    
                    possible_paths = [
                        rel_img_path,
                        os.path.join("data", rel_img_path),
                        os.path.join(base_dir, rel_img_path),
                        os.path.join(base_dir, "images", os.path.basename(rel_img_path)),
                        os.path.join("data", "images", os.path.basename(rel_img_path))
                    ]
                    
                    actual_path = None
                    for path in possible_paths:
                        if os.path.exists(path):
                            actual_path = path
                            break
                            
                    if actual_path:
                        self.samples.append((actual_path, bal_pwm, jobb_pwm))

        print(f"Sikeresen betöltve: {len(self.samples)} képkocka.")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        img_path, bal_pwm, jobb_pwm = self.samples[idx]
        bgr = cv2.imread(img_path)
        
        if bgr is None:
            rgb = np.zeros((120, 160, 3), dtype=np.uint8)
        else:
            # BGR -> RGB konverzió (megszünteti a kék elszíneződést)
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            rgb = cv2.resize(rgb, (160, 120))
            
        # Normalizálás és PyTorch tensor méretformátum (C, H, W)
        tensor_img = rgb.astype(np.float32) / 255.0
        tensor_img = np.transpose(tensor_img, (2, 0, 1))

        label = np.array([bal_pwm, jobb_pwm], dtype=np.float32)
        return torch.tensor(tensor_img), torch.tensor(label)

dataset = RobotDataset(csv_path)
if len(dataset) == 0:
    print("HIBA: Üres az adathalmaz vagy nem találhatók a képek!")
    exit()

dataloader = DataLoader(dataset, batch_size=32, shuffle=True)

# --- BETANÍTÁS ---
device = torch.device("cpu")
model = FlashFireCNN().to(device)
criterion = nn.MSELoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.0005)

EPOCHS = 25
print(f"\n--- MODELL BETANÍTÁSA ({EPOCHS} Epoch) ---")

model.train()
for epoch in range(EPOCHS):
    total_loss = 0.0
    for images, labels in dataloader:
        images = images.to(device)
        labels = labels.to(device)

        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        total_loss += loss.item() * images.size(0)

    epoch_loss = total_loss / len(dataset)
    print(f"Epoch {epoch+1:02d}/{EPOCHS} -> Loss: {epoch_loss:.6f}")

torch.save(model.state_dict(), "flashfire_model.pth")
print("\nSikeres mentés: flashfire_model.pth kész!")
