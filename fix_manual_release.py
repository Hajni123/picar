with open("/home/khajni/robot_car/picar_hailo_multimode.py", "r") as f:
    code = f.read()

# 1. Cseréljük ki a HTML-ben a gombok elengedését motor_stop-ra
code = code.replace("sendCmd('stop')", "sendCmd('motor_stop')")
# Visszaállítjuk a piros STOP gombot igazi stop-ra
code = code.replace("background: red;\" onclick=\"sendCmd('motor_stop')", "background: red;\" onclick=\"sendCmd('stop'")

# 2. Python oldalon kezeljük külön a motor_stop-ot és a stop-ot
old_handler = """        elif req_action == "stop": current_mode = 0; app_throttle = 0.0; app_steer = 0.0; stop()"""
new_handler = """        elif req_action == "motor_stop": app_throttle = 0.0; app_steer = 0.0; stop()
        elif req_action == "stop": current_mode = 0; app_throttle = 0.0; app_steer = 0.0; stop()"""

if old_handler in code:
    code = code.replace(old_handler, new_handler)

with open("/home/khajni/robot_car/picar_hailo_multimode.py", "w") as f:
    f.write(code)

print("Javítva!")
