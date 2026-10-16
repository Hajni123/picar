with open("/home/khajni/robot_car/picar_hailo_multimode.py", "r") as f:
    code = f.read()

# Beillesztjük a toggle_enhance kezelést a hálózati parancsok közé
old_target = """            elif req_action == "motor_stop" or req_action == "release": app_throttle = 0.0; app_steer = 0.0; stop()
            elif req_action == "stop": current_mode = 1; app_throttle = 0.0; app_steer = 0.0; stop()"""

new_target = """            elif req_action == "motor_stop" or req_action == "release": app_throttle = 0.0; app_steer = 0.0; stop()
            elif req_action == "stop": current_mode = 1; app_throttle = 0.0; app_steer = 0.0; stop()
            elif req_action == "toggle_enhance":
                enhance_enabled = not enhance_enabled"""

if old_target in code and "toggle_enhance" not in code:
    code = code.replace(old_target, new_target)
    with open("/home/khajni/robot_car/picar_hailo_multimode.py", "w") as f:
        f.write(code)
    print("Sikeresen javítva!")
else:
    print("Már benne van vagy nem található a célpont.")
