with open("/home/khajni/robot_car/picar_hailo_multimode.py", "r") as f:
    code = f.read()

# Biztosítjuk, hogy a toggle_enhance meghívja ugyanazt a logikát, mint a billentyűzetes 'c' leütés
old_handler = """            elif req_action == "toggle_enhance": enhance_enabled = not enhance_enabled"""
new_handler = """            elif req_action == "toggle_enhance":
                enhance_enabled = not enhance_enabled
                status_text = f"ENHANCE: {'BE' if enhance_enabled else 'KI'}" """

if old_handler in code:
    code = code.replace(old_handler, new_handler)
elif "toggle_enhance" not in code:
    code = code.replace("elif req_action == \"release\":", "elif req_action == \"toggle_enhance\":\n                enhance_enabled = not enhance_enabled\n            elif req_action == \"release\":")

with open("/home/khajni/robot_car/picar_hailo_multimode.py", "w") as f:
    f.write(code)

print("Backend javítva!")
