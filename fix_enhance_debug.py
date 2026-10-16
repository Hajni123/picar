with open("/home/khajni/robot_car/picar_hailo_multimode.py", "r") as f:
    code = f.read()

# Cseréljük ki a toggle_enhance részt egy biztosabb, nyomtatós változatra
old_toggle = """            elif req_action == "toggle_enhance": enhance_enabled = not enhance_enabled"""
new_toggle = """            elif req_action == "toggle_enhance":
                enhance_enabled = not enhance_enabled
                print(f"--- TELEFONOS C GOMB MEGNYOMVA! Uj statusz: {enhance_enabled} ---")"""

if old_toggle in code:
    code = code.replace(old_toggle, new_toggle)
    with open("/home/khajni/robot_car/picar_hailo_multimode.py", "w") as f:
        f.write(code)
    print("Debug kód beillesztve!")
else:
    print("Nem találom a toggle_enhance sort, ellenőrizd.")
