with open("/home/khajni/robot_car/picar_hailo_multimode.py", "r") as f:
    code = f.read()

# Cseréljük ki az érzékelési paramétereket gyorsabbá és biztosabbá
old_part = """                # Elakadás figyelése: ha előre megyünk, de a kép nem mozdul több mint 0.6 mp-ig
                is_stalled = (current_time - forward_start_time > 0.6) and (motion_score < 1.8)"""

new_part = """                # Érzékenyebb elakadás figyelése: elég 0.35 mp és magasabb mozgás-küszöb (< 3.5)
                is_stalled = (current_time - forward_start_time > 0.35) and (motion_score < 3.5)"""

if old_part in code:
    code = code.replace(old_part, new_part)
    with open("/home/khajni/robot_car/picar_hailo_multimode.py", "w") as f:
        f.write(code)
    print("Sikeresen felgyorsítva!")
else:
    print("Nem találom a pontos sort.")
