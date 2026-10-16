with open("/home/khajni/robot_car/picar_hailo_multimode.py", "r") as f:
    code = f.read()

# Keresem a req_action blokkot és beszúrom a toggle_enhance-t
old_block = """        if req_action:
            if req_action == "mode_1": current_mode = 1; stop()"""

new_block = """        if req_action:
            if req_action == "toggle_enhance": enhance_enabled = not enhance_enabled
            elif req_action == "mode_1": current_mode = 1; stop()"""

if old_block in code and "toggle_enhance" not in code:
    code = code.replace(old_block, new_block)
    with open("/home/khajni/robot_car/picar_hailo_multimode.py", "w") as f:
        f.write(code)
    print("Toggle enhance sikeresen beillesztve!")
else:
    print("Már benne van vagy eltérő a szerkezet.")
