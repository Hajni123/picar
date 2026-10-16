import os
import subprocess
import time


print("Sorozatfelvétel indítása")
print("3 másodpercenként készül egy kép.")
print("Forgasd/mozgasd a tárgyat a kamera előtt!\n")


# Beállítások
MAX_IMAGES = 60
image_count = 1


try:
    # Sorozatfelvétel
    while image_count <= MAX_IMAGES:
        filename = f"kep_{image_count:04d}.jpg"

        command = (
            f"rpicam-still -o {filename} "
            "--immediate --timeout 1 --width 640 --height 480"
        )

        subprocess.run(
            command,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        # Ellenőrzés
        if os.path.exists(filename):
            print(f"[{image_count}/{MAX_IMAGES}] Mentve: {filename}")
            image_count += 1
            time.sleep(3)
        else:
            print("A kamera nem adott képet, próbálkozás újra...")
            time.sleep(1)

    print("\n A fotózás sikeresen befejeződött!")

except KeyboardInterrupt:
    print("\n A fotózást megszakítottad.")
