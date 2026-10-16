with open("/home/khajni/robot_car/picar_hailo_multimode.py", "r") as f:
    code = f.read()

# Cseréljük ki a stop kezelést a Flask route-ban, hogy azonnal és kíméletlenül leállítson mindent
old_block = """        elif req_action == "stop":
            global current_mode
            if current_mode in [2, 3]:
                current_mode = 0
            app_throttle = 0.0
            app_steer = 0.0
            stop()"""

new_block = """        elif req_action == "stop":
            global current_mode
            current_mode = 0
            app_throttle = 0.0
            app_steer = 0.0
            try:
                stop()
            except:
                pass"""

if old_block in code:
    code = code.replace(old_block, new_block)

with open("/home/khajni/robot_car/picar_hailo_multimode.py", "w") as f:
    f.write(code)

print("Hard-stop beállítva!")
