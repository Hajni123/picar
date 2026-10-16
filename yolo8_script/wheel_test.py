# A két hajtómotor előre- és hátramenetének külön és együttes tesztelése.

import time

from gpiozero import PWMOutputDevice


# Motorok
left_forward = PWMOutputDevice(7, frequency=100)
left_backward = PWMOutputDevice(8, frequency=100)
right_forward = PWMOutputDevice(25, frequency=100)
right_backward = PWMOutputDevice(27, frequency=100)


# Leállítás
def stop():
    left_forward.value = 0
    left_backward.value = 0
    right_forward.value = 0
    right_backward.value = 0


print("Kerékteszt indul")
stop()
time.sleep(1)

try:
    # Baloldal
    print("\n[1/4] Bal elore (GPIO 7 - Feher)...")
    left_forward.value = 0.6
    time.sleep(2)
    stop()
    time.sleep(0.5)

    print("[2/4] Bal hatra (GPIO 8 - Zold)...")
    left_backward.value = 0.6
    time.sleep(2)
    stop()
    time.sleep(0.5)

    # Jobboldal
    print("\n[3/4] Jobb elore (GPIO 25 - Barna)...")
    right_forward.value = 0.6
    time.sleep(2)
    stop()
    time.sleep(0.5)

    print("[4/4] Jobb hatra (GPIO 27 - Sarga)...")
    right_backward.value = 0.6
    time.sleep(2)
    stop()
    time.sleep(0.5)

    # Szinkron
    print("\n[Szinkron] Mindketto elore egyszerre...")
    left_forward.value = 0.6
    right_forward.value = 0.6
    time.sleep(2)
    stop()
    time.sleep(0.5)

    print("[Szinkron] Mindketto hatra egyszerre...")
    left_backward.value = 0.6
    right_backward.value = 0.6
    time.sleep(2)
    stop()

    print("\nTeszt vege")

except KeyboardInterrupt:
    print("\nMegszakitva!")

finally:
    stop()
