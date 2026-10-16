# A motorvezérlő sárga kábeléhez kapcsolódó GPIO keresésére szolgáló tesztprogram.

import time

from gpiozero import OutputDevice


# Beállítások
PINS = [
    2, 3, 4, 14, 15, 17, 18, 27, 22,
    23, 24, 10, 9, 11, 25, 8, 7, 5,
    6, 12, 13, 16, 19, 20, 21, 26
]

print("Sárga kábel keresés")


# Keresés
for pin in PINS:
    try:
        print(
            f"Tesztelés: GPIO {pin} ... ",
            end="",
            flush=True
        )

        output = OutputDevice(pin)
        output.on()
        time.sleep(1.2)
        output.off()
        output.close()

        print("Kikapcsolva")
        time.sleep(0.3)

    except Exception as error:
        print(f"Kihagyva ({error})")


print("\nKeresés véget ért")
