with open("/home/khajni/robot_car/picar_hailo_multimode.py", "r") as f:
    code = f.read()

# Cseréljük ki a HTML_PAGE-t egy stabilabb, telefonbarát verzióra
old_html_start = 'HTML_PAGE = """'
new_html = '''HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>PiCar-X Távirányító</title>
    <style>
        body { font-family: Arial; text-align: center; background: #1a1a1a; color: white; margin: 0; padding: 10px; }
        img { width: 100%; max-height: 55vh; object-fit: contain; border-radius: 8px; }
        .grid { display: grid; grid-template-columns: repeat(3, 90px); gap: 10px; justify-content: center; margin-top: 15px; }
        button { height: 65px; font-size: 16px; font-weight: bold; border-radius: 8px; border: none; background: #333; color: white; touch-action: manipulation; }
        button:active { background: #555; }
        .btn-modes { display: flex; justify-content: center; gap: 6px; margin-top: 15px; flex-wrap: wrap; }
        .btn-mode { height: 45px; padding: 0 10px; background: #007acc; font-size: 14px; }
    </style>
</head>
<body>
    <h3>PiCar-X Élő Kép</h3>
    <img src="/video_feed">
    <div class="btn-modes">
        <button class="btn-mode" onclick="sendCmd('mode_1')">1: Kezi</button>
        <button class="btn-mode" onclick="sendCmd('mode_2')">2: Kovetes</button>
        <button class="btn-mode" onclick="sendCmd('mode_3')">3: Kerules</button>
        <button class="btn-mode" style="background:#e67e22;" onclick="sendCmd('switch_model')">M: Valtas</button>
    </div>
    <div class="grid">
        <div></div>
        <button ontouchstart="sendCmd('forward'); event.preventDefault();" onmousedown="sendCmd('forward')"
                ontouchend="sendCmd('stop'); event.preventDefault();" onmouseup="sendCmd('stop')">ELORE</button>
        <div></div>
        <button ontouchstart="sendCmd('left'); event.preventDefault();" onmousedown="sendCmd('left')"
                ontouchend="sendCmd('stop'); event.preventDefault();" onmouseup="sendCmd('stop')">BALRA</button>
        <button style="background: red;" onclick="sendCmd('stop')">STOP</button>
        <button ontouchstart="sendCmd('right'); event.preventDefault();" onmousedown="sendCmd('right')"
                ontouchend="sendCmd('stop'); event.preventDefault();" onmouseup="sendCmd('stop')">JOBBRA</button>
        <div></div>
        <button ontouchstart="sendCmd('backward'); event.preventDefault();" onmousedown="sendCmd('backward')"
                ontouchend="sendCmd('stop'); event.preventDefault();" onmouseup="sendCmd('stop')">HATRA</button>
        <div></div>
    </div>
    <script>
        function sendCmd(action) {
            fetch('/cmd?action=' + action).catch(function(error) {});
        }
    </script>
</body>
</html>
"""'''

if old_html_start in code:
    # Megkeressük a régi HTML_PAGE végét és kicseréljük
    start_idx = code.find('HTML_PAGE = """')
    end_idx = code.find('"""\n\n@app_flask.route(\'/\')')
    if end_idx == -1:
        end_idx = code.find('"""\n\n@app_flask.route("/")')
    
    if start_idx != -1 and end_idx != -1:
        code = code[:start_idx] + new_html + code[end_idx + 3:]
        with open("/home/khajni/robot_car/picar_hailo_multimode.py", "w") as f:
            f.write(code)
        print("Sikeres HTML frissítés!")
    else:
        print("Nem sikerült pontosan határolni a HTML blokkot.")
else:
    print("A HTML_PAGE nem található.")
