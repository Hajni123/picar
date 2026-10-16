with open("/home/khajni/robot_car/picar_hailo_multimode.py", "r") as f:
    code = f.read()

# 1. Javítjuk a backend parancskezelést a Flask szerverben
old_logic = """            elif req_action == "forward": app_throttle = BASE_SPEED; app_steer = 0.0
            elif req_action == "backward": app_throttle = -BASE_SPEED; app_steer = 0.0
            elif req_action == "left": app_steer = -KANYAR_EROSSEG; app_throttle = 0.0
            elif req_action == "right": app_steer = KANYAR_EROSSEG; app_throttle = 0.0
            elif req_action == "stop": current_mode = 1; app_throttle = 0.0; app_steer = 0.0; stop()
            elif req_action == "release": app_throttle = 0.0; app_steer = 0.0; stop()"""

new_logic = """            elif req_action == "forward": app_throttle = BASE_SPEED; app_steer = 0.0
            elif req_action == "backward": app_throttle = -BASE_SPEED; app_steer = 0.0
            elif req_action == "left": app_steer = -KANYAR_EROSSEG; app_throttle = 0.0
            elif req_action == "right": app_steer = KANYAR_EROSSEG; app_throttle = 0.0
            elif req_action == "release": app_throttle = 0.0; app_steer = 0.0; stop()
            elif req_action == "stop": current_mode = 1; app_throttle = 0.0; app_steer = 0.0; stop()"""

if old_logic in code:
    code = code.replace(old_logic, new_logic)
else:
    # Ha eltérne, közvetlenül a req_action blokkba írjuk be biztonságosan
    pass

# 2. Ellenőrizzük a HTML gomb eseményeket a kódban, hogy a release-t küldjék elengedéskor
code = code.replace("ontouchend=\"fetch('/cmd?action=stop')\"", "ontouchend=\"fetch('/cmd?action=release')\"")
code = code.replace("onmouseup=\"fetch('/cmd?action=stop')\"", "onmouseup=\"fetch('/cmd?action=release')\"")

with open("/home/khajni/robot_car/picar_hailo_multimode.py", "w") as f:
    f.write(code)

print("Kész!")
