import time
import cv2
import numpy as np
import torch
import pygame
from picamera2 import Picamera2
from model import FlashFireCNN
from gpiozero import PWMOutputDevice

feher_bal_elore  = PWMOutputDevice(7, frequency=100)
zold_bal_hatra   = PWMOutputDevice(8, frequency=100)
barna_jobb_elore = PWMOutputDevice(25, frequency=100)
sarga_jobb_hatra = PWMOutputDevice(27, frequency=100)

def stop():
    feher_bal_elore.value = 0
    zold_bal_hatra.value = 0
    barna_jobb_elore.value = 0
    sarga_jobb_hatra.value = 0

filtered_diff = 0.0
ALPHA = 0.30
base_speed = 0.35

def apply_filtered_motors(pred_bal, pred_jobb):
    global filtered_diff

    raw_diff = pred_bal - pred_jobb
    filtered_diff = (ALPHA * raw_diff) + ((1.0 - ALPHA) * filtered_diff)
    abs_diff = abs(filtered_diff)

    if abs_diff > 0.025:
        mode = "ELES KIKERULES"
        turn = np.sign(filtered_diff) * 0.13
        bal_val  = base_speed + turn
        jobb_val = base_speed - turn
    elif abs_diff > 0.010:
        mode = "FINOM RATERES"
        turn = np.sign(filtered_diff) * 0.07
        bal_val  = base_speed + turn
        jobb_val = base_speed - turn
    else:
        mode = "EGYENES"
        bal_val  = base_speed
        jobb_val = base_speed

    bal_val = max(0.14, min(0.48, bal_val))
    jobb_val = max(0.14, min(0.48, jobb_val))

    zold_bal_hatra.value = 0
    sarga_jobb_hatra.value = 0
    feher_bal_elore.value = bal_val
    barna_jobb_elore.value = jobb_val

    return filtered_diff, mode

# Modell betöltése
device = torch.device("cpu")
model = FlashFireCNN().to(device)
model.load_state_dict(torch.load("flashfire_model.pth", map_location=device))
model.eval()

# Kis felbontású kijelző ablak inicializálása (160x120)
DISP_W, DISP_H = 160, 120
pygame.init()
screen = pygame.display.set_mode((DISP_W, DISP_H))
pygame.display.set_caption("AI Kamera (Valos Kek)")

picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"size": (640, 480), "format": "RGB888"})
picam2.configure(config)
picam2.start()

# Kamera fényerő stabilizálási idő
time.sleep(0.5)

print("\n--- ÖNVEZETÉS AKTÍV (ÉRZÉKENY KANYARODÁS) ---")
print("Megállítás: ESC az ablakban vagy Ctrl + C a terminálban\n")

try:
    with torch.no_grad():
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise KeyboardInterrupt
            if pygame.key.get_pressed()[pygame.K_ESCAPE]:
                break

            raw_frame = picam2.capture_array()
            if raw_frame is None:
                continue

            # Modell bemenet előkészítése
            resized = cv2.resize(raw_frame, (120, 160))
            tensor_img = resized.astype(np.float32) / 255.0
            tensor_img = np.transpose(tensor_img, (2, 0, 1))
            input_tensor = torch.tensor(tensor_img).unsqueeze(0).to(device)

            pred = model(input_tensor).numpy()[0]
            pred_bal = float(pred[0])
            pred_jobb = float(pred[1])

            filt_val, mode = apply_filtered_motors(pred_bal, pred_jobb)
            print(f"\rBal: {pred_bal:.2f} | Jobb: {pred_jobb:.2f} | Diff: {filt_val:+.4f} | Mód: {mode:<16}", end="")

            # Kijelző frissítése valós színekkel
            display_img = cv2.resize(raw_frame, (DISP_W, DISP_H))
            disp_rgb = cv2.cvtColor(display_img, cv2.COLOR_BGR2RGB)
            surface = pygame.image.frombuffer(disp_rgb.tobytes(), (DISP_W, DISP_H), "RGB")
            screen.blit(surface, (0, 0))
            pygame.display.flip()

except KeyboardInterrupt:
    print("\nLeállítás...")
finally:
    stop()
    picam2.stop()
    pygame.quit()
