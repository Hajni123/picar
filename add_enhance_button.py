with open("/home/khajni/robot_car/picar_hailo_multimode.py", "r") as f:
    code = f.read()

# 1. Hozzáadjuk a gombot a HTML módok sávjához
old_modes_html = """        <div class="btn-modes">
        <button class="btn-mode" onclick="fetch('/cmd?action=mode_1')">1: Kézi</button>
        <button class="btn-mode" onclick="fetch('/cmd?action=mode_2')">2: Követés</button>
        <button class="btn-mode" onclick="fetch('/cmd?action=mode_3')">3: Kerülés</button>
        <button class="btn-mode" style="background:#e67e22;" onclick="fetch('/cmd?action=switch_model')">M: Váltás</button>
    </div>"""

new_modes_html = """        <div class="btn-modes">
        <button class="btn-mode" onclick="fetch('/cmd?action=mode_1')">1: Kézi</button>
        <button class="btn-mode" onclick="fetch('/cmd?action=mode_2')">2: Követés</button>
        <button class="btn-mode" onclick="fetch('/cmd?action=mode_3')">3: Kerülés</button>
    </div>
    <div class="btn-modes" style="margin-top: 5px;">
        <button class="btn-mode" style="background:#e67e22; width: 48%;" onclick="fetch('/cmd?action=switch_model')">M: Modell Váltás</button>
        <button class="btn-mode" style="background:#8e44ad; width: 48%;" onclick="fetch('/cmd?action=toggle_enhance')">C: Képjavítás</button>
    </div>"""

if old_modes_html in code:
    code = code.replace(old_modes_html, new_modes_html)

# 2. Kezeljük a toggle_enhance parancsot a Python oldalon
old_action_handler = """            elif req_action == "release": app_throttle = 0.0; app_steer = 0.0; stop()"""
new_action_handler = """            elif req_action == "release": app_throttle = 0.0; app_steer = 0.0; stop()
            elif req_action == "toggle_enhance": enhance_enabled = not enhance_enabled"""

if old_action_handler in code:
    code = code.replace(old_action_handler, new_action_handler)

with open("/home/khajni/robot_car/picar_hailo_multimode.py", "w") as f:
    f.write(code)

print("Képjavító gomb hozzáadva!")
