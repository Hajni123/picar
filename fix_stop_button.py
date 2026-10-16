with open("/home/khajni/robot_car/picar_hailo_multimode.py", "r") as f:
    code = f.read()

# 1. Javítjuk a HTML-t: a gomb elengedés külön 'release' parancsot küld, a STOP pedig marad 'stop'
old_html = """        <button onmousedown="fetch('/cmd?action=forward')" onmouseup="fetch('/cmd?action=stop')"
                ontouchstart="fetch('/cmd?action=forward')" ontouchend="fetch('/cmd?action=stop')">ELŐRE</button>
        <div></div>
        <button onmousedown="fetch('/cmd?action=left')" onmouseup="fetch('/cmd?action=stop')"
                ontouchstart="fetch('/cmd?action=left')" ontouchend="fetch('/cmd?action=stop')">BALRA</button>
        <button style="background: red;" onclick="fetch('/cmd?action=stop')">STOP</button>
        <button onmousedown="fetch('/cmd?action=right')" onmouseup="fetch('/cmd?action=stop')"
                ontouchstart="fetch('/cmd?action=right')" ontouchend="fetch('/cmd?action=stop')">JOBBRA</button>
        <div></div>
        <button onmousedown="fetch('/cmd?action=backward')" onmouseup="fetch('/cmd?action=stop')"
                ontouchstart="fetch('/cmd?action=backward')" ontouchend="fetch('/cmd?action=stop')">HÁTRA</button>"""

new_html = """        <button onmousedown="fetch('/cmd?action=forward')" onmouseup="fetch('/cmd?action=release')"
                ontouchstart="fetch('/cmd?action=forward')" ontouchend="fetch('/cmd?action=release')">ELORE</button>
        <div></div>
        <button onmousedown="fetch('/cmd?action=left')" onmouseup="fetch('/cmd?action=release')"
                ontouchstart="fetch('/cmd?action=left')" ontouchend="fetch('/cmd?action=release')">BALRA</button>
        <button style="background: red;" onclick="fetch('/cmd?action=stop')">STOP</button>
        <button onmousedown="fetch('/cmd?action=right')" onmouseup="fetch('/cmd?action=release')"
                ontouchstart="fetch('/cmd?action=right')" ontouchend="fetch('/cmd?action=release')">JOBBRA</button>
        <div></div>
        <button onmousedown="fetch('/cmd?action=backward')" onmouseup="fetch('/cmd?action=release')"
                ontouchstart="fetch('/cmd?action=backward')" ontouchend="fetch('/cmd?action=release')">HATRA</button>"""

if old_html in code:
    code = code.replace(old_html, new_html)

# 2. Python backend parancskezelés frissítése
old_cmd_block = """            elif req_action == "stop": current_mode = 0; app_throttle = 0.0; app_steer = 0.0; stop()"""

new_cmd_block = """            elif req_action == "release": app_throttle = 0.0; app_steer = 0.0; stop()
            elif req_action == "stop": current_mode = 1; app_throttle = 0.0; app_steer = 0.0; stop()"""

if old_cmd_block in code:
    code = code.replace(old_cmd_block, new_cmd_block)

with open("/home/khajni/robot_car/picar_hailo_multimode.py", "w") as f:
    f.write(code)

print("Sikeres STOP gomb javítás!")
