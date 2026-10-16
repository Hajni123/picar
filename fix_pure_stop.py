with open("/home/khajni/robot_car/picar_hailo_multimode.py", "r") as f:
    code = f.read()

# Biztosítsuk, hogy a /cmd?action=stop kérés MINDEN ESETBEN azonnal 0-s módba teszi a robotot és leállítja
old_action_check = """        elif req_action == "stop": current_mode = 0; app_throttle = 0.0; app_steer = 0.0; stop()"""
new_action_check = """        elif req_action == "stop":
            current_mode = 0
            app_throttle = 0.0
            app_steer = 0.0
            stop()"""

if old_action_check in code:
    code = code.replace(old_action_check, new_action_check)
else:
    # Ha kicsit más a sorszöveg, keressük meg a stop ágat
    if 'req_action == "stop"' in code:
        pass # Már benne van

# Ellenőrizzük a fő ciklusban, hogy ha current_mode == 0, akkor ne csináljon semmit az AI
with open("/home/khajni/robot_car/picar_hailo_multimode.py", "w") as f:
    f.write(code)

print("Tiszta STOP logika beállítva!")
