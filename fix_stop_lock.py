with open("/home/khajni/robot_car/picar_hailo_multimode.py", "r") as f:
    code = f.read()

# Biztosítsuk, hogy 0-s módban a robot fixenálljon és ne csináljon semmit
old_mode_0 = """        # 0. VÉSZFÉK VAGY IDLE"""
new_mode_0 = """        # 0. VÉSZFÉK (TELJES LETILTÁS)
        elif current_mode == 0:
            stop()
            status_text = "VESZFEK - LEÁLLITVA"
            continue"""

if "elif current_mode == 0:" not in code:
    # Ha nincs még benne külön 0-s mód kezelő, beszúrjuk a ciklus elejére
    code = code.replace("while True:", "while True:\n            current_time = time.time()\n            if current_mode == 0:\n                stop()\n                continue")

with open("/home/khajni/robot_car/picar_hailo_multimode.py", "w") as f:
    f.write(code)

print("STOP lezárva!")
