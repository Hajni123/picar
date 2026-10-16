import time
import cv2
import numpy as np
import torch
import pygame
from picamera2 import Picamera2
from model import FlashFireCNN
from gpiozero import PWMOutputDevice

# --- MOTORVEZÉRLÉS ---
feher_bal_elore  = PWMOutputDevice(7, frequency=100)
zold_bal_hatra   = PWMOutputDevice(8, frequency=100)
barna_jobb_elore = PWMOutputDevice(25, frequency=100)
sarga_jobb_hatra = PWMOutputDevice(27, frequency=100)

def stop():
    feher_bal_elore.value = 0
    zold_bal_hatra.value = 0
    barna_jobb_elore.value = 0
    sarga_jobb_hatra.value = 0

# --- MODELL BETÖLTÉSE ---
device = torch.device("cpu")
model = FlashFireCNN().to(device)
model.load_state_dict(torch.load("flashfire_model.pth", map_location=device))
model.eval()

# --- FINOMHANGOLT VEZÉRLÉSI PARAMÉTEREK ---
SEBESSEG = 0.26        # Minimálisan visszavett sebesség a sodródás ellen (korábban: 0.32)
KANYAR_SZORZO = 2.4   # Élesebb és azonnali reakció a második akadályra (korábban: 1.8)

# --- KAMERA ÉS ÉLŐKÉP ---
WIDTH, HEIGHT = 640, 480
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("AI Autopilot - Finomhangolt")

picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"size": (WIDTH, HEIGHT), "format": "RGB888"})
picam2.configure(config)
picam2.start()
time.sleep(0.5)

print("\n--- ÖNVEZETÉS AKTÍV (FINOMHANGOLT KANYARODÁS) ---")
print("Megállítás: ESC vagy Ctrl + C\n")

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

            # 1. Méretezés a neurális háló méretére
            resized = cv2.resize(raw_frame, (160, 120))
            tensor_img = resized.astype(np.float32) / 255.0
            tensor_img = np.transpose(tensor_img, (2, 0, 1))
            input_tensor = torch.from_numpy(tensor_img).unsqueeze(0).to(device)

            # 2. Modell kimenet
            pred = model(input_tensor).numpy()[0]
            val_bal = float(pred[0])
            val_jobb = float(pred[1])

            # 3. Kormányzás számítása
            kulonbseg = (val_jobb - val_bal) * KANYAR_SZORZO

            # Élesebb kanyar esetén a belső kerék akár teljesen megállhat (0.00)
            bal_pwm  = max(0.00, min(0.55, SEBESSEG - kulonbseg))
            jobb_pwm = max(0.00, min(0.55, SEBESSEG + kulonbseg))

            # 4. Motorok vezérlése
            zold_bal_hatra.value = 0
            sarga_jobb_hatra.value = 0
            feher_bal_elore.value = bal_pwm
            barna_jobb_elore.value = jobb_pwm

            # 5. Élőkép megjelenítése
            real_frame = raw_frame[..., ::-1]
            disp_surf = pygame.image.frombuffer(real_frame.tobytes(), (WIDTH, HEIGHT), "RGB")
            screen.blit(disp_surf, (0, 0))
            pygame.display.flip()

            print(f"\rKormany: {kulonbseg:+.3f} | Bal: {bal_pwm:.2f} | Jobb: {jobb_pwm:.2f}", end="")

except KeyboardInterrupt:
    print("\nLeállítás...")
finally:
    stop()
    picam2.stop()
    pygame.quit()
