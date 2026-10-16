with open("/home/khajni/robot_car/picar_hailo_multimode.py", "r") as f:
    code = f.read()

# Eltávolítjuk a hibás részeket
code = code.replace("while True:\n    if 'current_mode' in globals() and current_mode == 0:\n        stop()\n        time.sleep(0.02)\n        continue", "while True:")
code = code.replace("while True:\n    if 'current_mode' in globals() and current_mode == 0:\n        stop()\n        time.sleep(0.05)\n        continue", "while True:")

with open("/home/khajni/robot_car/picar_hailo_multimode.py", "w") as f:
    f.write(code)

print("Hurok megtisztítva!")
