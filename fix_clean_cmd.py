with open("/home/khajni/robot_car/picar_hailo_multimode.py", "r") as f:
    lines = f.readlines()

new_lines = []
skip_next = False
for line in lines:
    # Ha benne van a hibás global current_mode, kihagyjuk
    if "global current_mode" in line:
        continue
    new_lines.append(line)

with open("/home/khajni/robot_car/picar_hailo_multimode.py", "w") as f:
    f.writelines(new_lines)

print("Tisztítva!")
