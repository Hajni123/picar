with open("/home/khajni/robot_car/picar_hailo_multimode.py", "r") as f:
    lines = f.readlines()

new_lines = []
skip = False
for i, line in enumerate(lines):
    # Kereszttartomány tisztítása a req_action körül
    if 'if req_action:' in line:
        new_lines.append("        if req_action:\n")
        new_lines.append('            if req_action == "mode_1": current_mode = 1; stop()\n')
        new_lines.append('            elif req_action == "mode_2": current_mode = 2; prev_target_pos = None; last_motion_time = 0.0; stop()\n')
        new_lines.append('            elif req_action == "mode_3": current_mode = 3; avoid_state = "FORWARD"; avoid_state_timer = current_time; stop()\n')
        new_lines.append('            elif req_action == "switch_model":\n')
        new_lines.append('                enh_flag = 100 if enhance_enabled else 0\n')
        new_lines.append('                target_code = 20 if engine_name == "det" else 10\n')
        new_lines.append('                exit_code = target_code + current_mode + enh_flag\n')
        new_lines.append('                running = False\n')
        new_lines.append('                stop_event.set()\n')
        new_lines.append('            elif req_action == "forward": app_throttle = BASE_SPEED; app_steer = 0.0\n')
        new_lines.append('            elif req_action == "backward": app_throttle = -BASE_SPEED; app_steer = 0.0\n')
        new_lines.append('            elif req_action == "left": app_steer = -KANYAR_EROSSEG; app_throttle = 0.0\n')
        new_lines.append('            elif req_action == "right": app_steer = KANYAR_EROSSEG; app_throttle = 0.0\n')
        new_lines.append('            elif req_action == "stop": current_mode = 1; app_throttle = 0.0; app_steer = 0.0; stop()\n')
        new_lines.append('            elif req_action == "release": app_throttle = 0.0; app_steer = 0.0; stop()\n')
        # Átugorjuk a régi hibás sorokat amíg el nem érjük a try:-t
        skip = True
    elif skip and 'try:' in line:
        skip = False
        new_lines.append(line)
    elif not skip:
        new_lines.append(line)

with open("/home/khajni/robot_car/picar_hailo_multimode.py", "w") as f:
    f.writelines(new_lines)

print("Behúzás javítva!")
