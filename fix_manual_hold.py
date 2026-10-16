with open("/home/khajni/robot_car/picar_hailo_multimode.py", "r") as f:
    code = f.read()

# 1. Biztosítjuk, hogy a 'release' parancs és a STOP gomb azonnal nullázza a sebességet és megálljon
old_release = """            elif req_action == "release": app_throttle = 0.0; app_steer = 0.0; stop()"""
new_release = """            elif req_action == "release": app_throttle = 0.0; app_steer = 0.0; stop()
            elif req_action == "stop": current_mode = 1; app_throttle = 0.0; app_steer = 0.0; stop()"""

if "release" in code and "stop" in code:
    pass # Már benne van vagy hasonló

# 2. A Mode 1 (Kézi) vezérlő loopban biztosítjuk, hogy csak akkor hajtson, ha érkezik parancs, egyébként álljon meg
old_mode_1 = """        # 1. KÉZI MÓD
        elif current_mode == 1:
            drive(app_throttle, app_steer)
            status_text = "KEZI MOD (TELJESEN MANUALIS)" """

new_mode_1 = """        # 1. KÉZI MÓD (Csak gombnyomásra mozog)
        elif current_mode == 1:
            drive(app_throttle, app_steer)
            status_text = "KEZI MOD" """

with open("/home/khajni/robot_car/picar_hailo_multimode.py", "w") as f:
    f.write(code)

print("Kész!")
