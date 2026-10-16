import os
import time
import csv
import cv2
import pygame
from picamera2 import Picamera2
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

# --- SEBESSÉG BEÁLLÍTÁSOK ---
BASE_SPEED = 0.26
KANYAR_EROSSEG = 0.16

DATA_DIR = "data"
IMG_DIR = os.path.join(DATA_DIR, "images")
os.makedirs(IMG_DIR, exist_ok=True)
csv_file_path = os.path.join(DATA_DIR, "labels.csv")

# --- KAMERA ÉS ABLAK ---
WIDTH, HEIGHT = 160, 120
pygame.init()
pygame.joystick.init()

joystick = None
if pygame.joystick.get_count() > 0:
    joystick = pygame.joystick.Joystick(0)
    joystick.init()

screen = pygame.display.set_mode((320, 240))
pygame.display.set_caption("Adatgyujtes - Eredeti szinekkel")

picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"size": (WIDTH, HEIGHT), "format": "RGB888"})
picam2.configure(config)
picam2.start()
time.sleep(0.5)

csv_file = open(csv_file_path, "a", newline="")
csv_writer = csv.writer(csv_file)

frame_count = 0
clock = pygame.time.Clock()

print("\n--- ADATGYŰJTÉS INDUL ---")
print("Gáz: [W] / Fel nyíl | Kormányzás: [A]/[D] / Jobb-Bal nyilak | Kilépés: [ESC]\n")

try:
    while True:
        clock.tick(30)
        
        steer = 0.0
        throttle = 0.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise KeyboardInterrupt

        keys = pygame.key.get_pressed()
        if keys[pygame.K_ESCAPE]:
            break

        if keys[pygame.K_UP] or keys[pygame.K_w]:
            throttle = BASE_SPEED
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            throttle = -BASE_SPEED

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            steer = -KANYAR_EROSSEG
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            steer = KANYAR_EROSSEG

        if joystick:
            jx = joystick.get_axis(0)
            jy = joystick.get_axis(1)
            if abs(jx) > 0.20:
                steer = jx * KANYAR_EROSSEG
            if abs(jy) > 0.20:
                throttle = -jy * BASE_SPEED

        if throttle > 0:
            bal_pwm  = max(0.10, min(0.45, throttle + steer))
            jobb_pwm = max(0.10, min(0.45, throttle - steer))

            zold_bal_hatra.value = 0
            sarga_jobb_hatra.value = 0
            feher_bal_elore.value = bal_pwm
            barna_jobb_elore.value = jobb_pwm
        elif throttle < 0:
            bal_pwm = jobb_pwm = 0.0
            feher_bal_elore.value = 0
            barna_jobb_elore.value = 0
            zold_bal_hatra.value = 0.20
            sarga_jobb_hatra.value = 0.20
        else:
            bal_pwm = jobb_pwm = 0.0
            stop()

        raw_frame = picam2.capture_array()
        if raw_frame is not None:
            if raw_frame.shape[2] == 4:
                raw_frame = raw_frame[:, :, :3]

            # A megfordított frame, ami nálad a jó színt adta
            frame_view = raw_frame[..., ::-1]

            if throttle > 0:
                img_name = f"frame_{int(time.time()*1000)}_{frame_count:05d}.jpg"
                img_path = os.path.join(IMG_DIR, img_name)
                cv2.imwrite(img_path, frame_view)
                csv_writer.writerow([os.path.join("images", img_name), f"{bal_pwm:.4f}", f"{jobb_pwm:.4f}"])
                frame_count += 1

            disp_frame = cv2.resize(frame_view, (320, 240))
            disp_surf = pygame.image.frombuffer(disp_frame.tobytes(), (320, 240), "RGB")
            screen.blit(disp_surf, (0, 0))
            pygame.display.flip()

            print(f"\rKép: {frame_count:05d} | B: {bal_pwm:.2f} | J: {jobb_pwm:.2f} | Kormány: {steer:+.2f}", end="")

except KeyboardInterrupt:
    pass
finally:
    stop()
    csv_file.close()
    picam2.stop()
    pygame.quit()
    print("\nAdatgyűjtés befejezve.")
