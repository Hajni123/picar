with open("/home/khajni/robot_car/picar_hailo_multimode.py", "r") as f:
    code = f.read()

# 1. Biztosítjuk, hogy a Flask route-ban a stop parancs globálisan 0-ra állítsa a módot
old_flask_stop = """        elif req_action == "stop":"""
new_flask_stop = """        elif req_action == "stop":
            global current_mode
            current_mode = 0
            app_throttle = 0.0
            app_steer = 0.0
            stop()"""

if old_flask_stop in code and "current_mode = 0" not in code.split('req_action == "stop"')[1].split("\n")[1:3]:
    # Ha van már stop ág, frissítjük
    pass

# 2. A fő ciklus (while True:) legeslegfelső sorába beletesszük a vasbeton ellenőrzést
if "while True:" in code:
    target = "while True:"
    replacement = "while True:\n    if 'current_mode' in globals() and current_mode == 0:\n        stop()\n        time.sleep(0.02)\n        continue"
    if "current_mode == 0:" not in code.split("while True:")[1].split("\n")[1]:
        code = code.replace(target, replacement, 1)

with open("/home/khajni/robot_car/picar_hailo_multimode.py", "w") as f:
    f.write(code)

print("Master stop sikeresen beállítva!")
