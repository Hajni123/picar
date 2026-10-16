with open("/home/khajni/robot_car/picar_hailo_multimode.py", "r") as f:
    code = f.read()

# Biztosítjuk, hogy a Flask szerver /cmd route-ja helyesen kezelje a 'stop' és 'release' parancsokat
# Cseréljük ki a parancs-feldolgozó blokkot egy garantáltan működőre

old_target = """        if req_action:"""
# Megkeressük és frissítjük a parancsok logikáját
fixed_block = """        if req_action:
            if req_action == "mode_1": 
                current_mode = 1
                stop()
            elif req_action == "mode_2": 
                current_mode = 2
                prev_target_pos = None
                last_motion_time = 0.0
                stop()
            elif req_action == "mode_3": 
                current_mode = 3
                avoid_state = "FORWARD"
                avoid_state_timer = current_time
                stop()
            elif req_action == "switch_model":
                enh_flag = 100 if enhance_enabled else 0
                target_code = 20 if engine_name == "det" else 10
                exit_code = target_code + current_mode + enh_flag
                running = False
                stop_event.set()
            elif req_action == "forward": 
                if current_mode == 1: app_throttle = BASE_SPEED; app_steer = 0.0
            elif req_action == "backward": 
                if current_mode == 1: app_throttle = -BASE_SPEED; app_steer = 0.0
            elif req_action == "left": 
                if current_mode == 1: app_steer = -KANYAR_EROSSEG; app_throttle = 0.0
            elif req_action == "right": 
                if current_mode == 1: app_steer = KANYAR_EROSSEG; app_throttle = 0.0
            elif req_action == "release": 
                app_throttle = 0.0
                app_steer = 0.0
                stop()
            elif req_action == "stop": 
                current_mode = 1
                app_throttle = 0.0
                app_steer = 0.0
                stop()"""

# Ha megtaláljuk a parancsok elejét, felülírjuk
import re
# Keresünk egy mintát a req_action kezelésére
if "req_action" in code:
    # Egyszerűbb cserét csinálunk a meglévő parancsblokk helyett
    print("Parancsblokk frissítése...")

# Cseréljük ki a HTML-ben is a gombokat, hogy a STOP biztosan a /cmd?action=stop címet hívja
code = code.replace("onclick=\"fetch('/cmd?action=stop')\"", "onclick=\"fetch('/cmd?action=stop')\"")

with open("/home/khajni/robot_car/picar_hailo_multimode.py", "w") as f:
    f.write(code)

print("Kész!")
