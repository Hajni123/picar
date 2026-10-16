with open("/home/khajni/robot_car/picar_hailo_multimode.py", "r") as f:
    code = f.read()

# Keressük meg a módok gomb blokkját és írjuk át teljesen ujakra
import re

# Ha létezik már régi gombblokk, cseréljük le
pattern = r'<div class="btn-modes">.*?</div>'
replacement = '''<div class="btn-modes">
        <button class="btn-mode" onclick="fetch('/cmd?action=mode_1')">1: Kezi</button>
        <button class="btn-mode" onclick="fetch('/cmd?action=mode_2')">2: Kovetes</button>
        <button class="btn-mode" onclick="fetch('/cmd?action=mode_3')">3: Kerules</button>
    </div>
    <div class="btn-modes" style="margin-top: 5px;">
        <button class="btn-mode" style="background:#e67e22; width: 48%;" onclick="fetch('/cmd?action=switch_model')">M: Modell Valtas</button>
        <button class="btn-mode" style="background:#8e44ad; width: 48%;" onclick="fetch('/cmd?action=toggle_enhance')">C: Kepjavitas</button>
    </div>'''

# Ha nincs benne a toggle_enhance, adjuk hozzá a Python kezelőhöz is
if "toggle_enhance" not in code:
    code = code.replace("elif req_action == \"release\":", "elif req_action == \"toggle_enhance\": enhance_enabled = not enhance_enabled\n            elif req_action == \"release\":")

# Írjuk vissza
with open("/home/khajni/robot_car/picar_hailo_multimode.py", "w") as f:
    f.write(code)

print("Kész!")
