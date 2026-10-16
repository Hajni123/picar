with open("/home/khajni/robot_car/picar_hailo_multimode.py", "r") as f:
    code = f.read()

# Cseréljük ki a /cmd útvonal kezelését a Pythonban, hogy a 'stop' biztosan Mode 1-be tegyen és megállítson
target_code = """        if req_action:
            if req_action == "mode_1": current_mode = 1; stop()
            elif req_action == "mode_2": current_mode = 2; prev_target_pos = None; last_motion_time = 0.0; stop()
            elif req_action == "mode_3": current_mode = 3; avoid_state = "FORWARD"; avoid_state_timer = current_time; stop()
            elif req_action == "switch_model":
                enh_flag = 100 if enhance_enabled else 0
                target_code = 20 if engine_name == "det" else 10
                exit_code = target_code + current_mode + enh_flag
                running = False
                stop_event.set()
            elif req_action == "forward": app_throttle = BASE_SPEED; app_steer = 0.0
            elif req_action == "backward": app_throttle = -BASE_SPEED; app_steer = 0.0
            elif req_action == "left": app_steer = -KANYAR_EROSSEG; app_throttle = 0.0
            elif req_action == "right": app_steer = KANYAR_EROSSEG; app_throttle = 0.0
            elif req_action == "stop": current_mode = 1; app_throttle = 0.0; app_steer = 0.0; stop()
            elif req_action == "release": app_throttle = 0.0; app_steer = 0.0; stop()"""

# Megkeressük a req_action blokk kezdetét és frissítjük
import re
code = re.sub(r'if req_action:.*?(?=\s+try:)', target_code + '\n\n        ', code, flags=re.DOTALL)

with open("/home/khajni/robot_car/picar_hailo_multimode.py", "w") as f:
    f.write(code)

print("Kész a kényszerített STOP javítás!")
