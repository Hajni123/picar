with open("/home/khajni/robot_car/picar_hailo_multimode.py", "r") as f:
    code = f.read()

# 1. Biztosítsuk, hogy a Flask szerverben a /cmd?action=stop AZONNAL átállítsa a current_mode-ot 0-ra globálisan
old_stop_route = """        elif req_action == "stop":
            current_mode = 0
            app_throttle = 0.0
            app_steer = 0.0
            stop()"""

new_stop_route = """        elif req_action == "stop":
            global current_mode
            current_mode = 0
            app_throttle = 0.0
            app_steer = 0.0
            stop()"""

if old_stop_route in code:
    code = code.replace(old_stop_route, new_stop_route)

# 2. A fő ciklus elején ellenőrizzük, hogy ha current_mode == 0, semmi más ne futhasson le
if "if current_mode == 0:" not in code:
    code = code.replace("while True:", "while True:\n    if 'current_mode' in globals() and current_mode == 0:\n        stop()\n        time.sleep(0.05)\n        continue")

with open("/home/khajni/robot_car/picar_hailo_multimode.py", "w") as f:
    f.write(code)

print("Véglegesítve!")
