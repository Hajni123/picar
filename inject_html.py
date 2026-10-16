with open("/home/khajni/robot_car/picar_hailo_multimode.py", "r") as f:
    code = f.read()

# Új gombok HTML kódja
new_buttons_html = '''    <div class="btn-modes">
        <button class="btn-mode" onclick="fetch('/cmd?action=mode_1')">1: Kezi</button>
        <button class="btn-mode" onclick="fetch('/cmd?action=mode_2')">2: Kovetes</button>
        <button class="btn-mode" onclick="fetch('/cmd?action=mode_3')">3: Kerules</button>
    </div>
    <div class="btn-modes" style="margin-top: 5px;">
        <button class="btn-mode" style="background:#e67e22; width: 48%;" onclick="fetch('/cmd?action=switch_model')">M: Modell Valtas</button>
        <button class="btn-mode" style="background:#8e44ad; width: 48%;" onclick="fetch('/cmd?action=toggle_enhance')">C: Kepjavitas</button>
    </div>'''

# Ha létezik régi btn-modes blokk, kicseréljük, ha nem, a body elé szúrjuk
import re
if 'class="btn-modes"' in code:
    # Cseréljük az első találatot vagy az összes btn-modes-t
    code = re.sub(r'<div class="btn-modes">.*?</div>(\s*<div class="btn-modes">.*?</div>)?', new_buttons_html, code, flags=re.DOTALL)
else:
    code = code.replace("</body>", new_buttons_html + "\n</body>")

# Biztosítjuk, hogy a toggle_enhance parancsot kezelje a backend
if "toggle_enhance" not in code:
    code = code.replace("elif req_action == \"release\":", "elif req_action == \"toggle_enhance\": enhance_enabled = not enhance_enabled\n            elif req_action == \"release\":")

with open("/home/khajni/robot_car/picar_hailo_multimode.py", "w") as f:
    f.write(code)

print("HTML beillesztve!")
