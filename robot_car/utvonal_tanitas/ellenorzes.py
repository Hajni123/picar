# A balra kanyarodáshoz rögzített tanítóképek ellenőrzése.

import csv
import os
import random

import cv2


# Útvonalak
CSV_PATH = "data/labels.csv"
DATA_DIR = "data"

left_turn_images = []


# Beolvasás
with open(CSV_PATH, newline="") as csv_file:
    csv_reader = csv.reader(csv_file)

    for row in csv_reader:
        if len(row) < 3:
            continue

        try:
            left_pwm = float(row[1])
            right_pwm = float(row[2])
        except ValueError:
            continue

        # Kiválasztás
        if right_pwm - left_pwm > 0.05:
            image_path = os.path.join(DATA_DIR, row[0])

            if os.path.isfile(image_path):
                left_turn_images.append(
                    (image_path, left_pwm, right_pwm)
                )

print("Balra kanyarodási képek:", len(left_turn_images))


# Mintavétel
random.seed(42)
samples = random.sample(
    left_turn_images,
    min(20, len(left_turn_images))
)


# Képfeldolgozás
for index, (image_path, left_pwm, right_pwm) in enumerate(samples):
    image = cv2.imread(image_path)

    if image is None:
        continue

    image = cv2.resize(image, (640, 480))

    # Kiírások
    cv2.putText(
        image,
        f"Bal: {left_pwm:.2f}  Jobb: {right_pwm:.2f}",
        (15, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 0),
        2
    )

    cv2.putText(
        image,
        f"Kep: {index + 1}/{len(samples)}",
        (15, 70),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2
    )

    # Megjelenítés
    cv2.imshow("Balra kanyarodasi tanitokepek", image)

    # Billentyűkezelés
    key = cv2.waitKey(0)

    if key == 27 or key == ord("q"):
        break

cv2.destroyAllWindows()
