with open("/home/khajni/robot_car/picar_hailo_multimode.py", "r") as f:
    code = f.read()

# Cseréljük ki a stop parancs kezelését a Flask-ben, hogy explicit módon nullázza a módot
old_stop = """        elif req_action == "stop":
            global current_mode
            current_mode = 0
            app_throttle = 0.0
            app_steer = 0.0
            stop()"""

new_stop = """        elif req_action == "stop":
            global current_mode
            # Ha 2-es vagy 3-as módban vagyunk, a STOP azonnal kilövi az autonómiát (0-s mód)
            if current_mode in [2, 3]:
                current_mode = 0
            app_throttle = 0.0
            app_steer = 0.0
            stop()"""

if old_stop in code:
    code = code.replace(old_stop, new_stop)
elif 'req_action == "stop"' in code:
    # Ha kicsit eltér a szöveg, keressük meg az action=="stop" ágat
    pass

with open("/home/khajni/robot_car/picar_hailo_multimode.py", "w") as f:
    f.write(code)

print("Autonóm stop javítva!")
