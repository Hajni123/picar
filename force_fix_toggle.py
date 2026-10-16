with open("/home/khajni/robot_car/picar_hailo_multimode.py", "r") as f:
    code = f.read()

target = 'elif req_action == "mode_3": current_mode = 3; avoid_state = "FORWARD"; avoid_state_timer = current_time; stop()'
addition = '\n            elif req_action == "toggle_enhance": enhance_enabled = not enhance_enabled'

if target in code and "toggle_enhance" not in code:
    code = code.replace(target, target + addition)
    with open("/home/khajni/robot_car/picar_hailo_multimode.py", "w") as f:
        f.write(code)
    print("Sikeresen hozzáadva!")
else:
    # Ha esetleg már benne van vagy más formátumú
    if "toggle_enhance" not in code:
        code = code.replace("if req_action:", "if req_action:\n            if req_action == \"toggle_enhance\": enhance_enabled = not enhance_enabled")
        with open("/home/khajni/robot_car/picar_hailo_multimode.py", "w") as f:
            f.write(code)
        print("Alternatív módon hozzáadva!")
    else:
        print("Már benne van a kódban.")
