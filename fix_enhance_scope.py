with open("/home/khajni/robot_car/picar_hailo_multimode.py", "r") as f:
    code = f.read()

# Biztosítjuk, hogy a route-on belül globálisan legyen kezelve az enhance_enabled
old_target = """            elif req_action == "toggle_enhance":
                enhance_enabled = not enhance_enabled
                status_text = f"ENHANCE: {'BE' if enhance_enabled else 'KI'}" """

new_target = """            elif req_action == "toggle_enhance":
                global enhance_enabled
                enhance_enabled = not enhance_enabled
                status_text = f"ENHANCE: {'BE' if enhance_enabled else 'KI'}" """

if old_target in code:
    code = code.replace(old_target, new_target)
    with open("/home/khajni/robot_car/picar_hailo_multimode.py", "w") as f:
        f.write(code)
    print("Globális hatókör javítva!")
else:
    print("Nem található a pontos blokk, de ellenőrizve.")
