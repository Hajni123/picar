with open("/home/khajni/robot_car/picar_hailo_multimode.py", "r") as f:
    code = f.read()

# Megkeressük a HTML_PAGE elejét és végéig cseréljük
import re

new_html_block = '''HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>PiCar-X Távirányító</title>
    <style>
        body { font-family: Arial; text-align: center; background: #1a1a1a; color: white; margin: 0; padding: 5px; overflow: hidden; }
        img { width: 100%; max-height: 50vh; object-fit: contain; border-radius: 6px; }
        .grid { display: grid; grid-template-columns: repeat(3, 90px); gap: 8px; justify-content: center; margin-top: 10px; }
        button { height: 65px; font-size: 15px; font-weight: bold; border-radius: 8px; border: none; background: #333; color: white; touch-action: manipulation; }
        button:active { background: #007acc; }
        .btn-stop { background: #d9534f !important; }
        .btn-modes { display: flex; justify-content: center; gap: 6px; margin-top: 8px; }
        .btn-mode { height: 40px; padding: 0 10px; background: #0275d8; font-size: 13px; }
    </style>
</head>
<body>
    <img src="/video_feed">
    <div class="btn-modes">
        <button class="btn-mode" onclick="fetch('/cmd?action=mode_1')">1: Kezi</button>
        <button class="btn-mode" onclick="fetch('/cmd?action=mode_2')">2: Kovetes</button>
        <button class="btn-mode" onclick="fetch('/cmd?action=mode_3')">3: Kerules</button>
        <button class="btn-mode" style="background:#f0ad4e;" onclick="fetch('/cmd?action=switch_model')">M: Valtas</button>
    </div>
    <div class="grid">
        <div></div>
        <button ontouchstart="sendState('fwd', 1)" ontouchend="sendState('fwd', 0)" onmousedown="sendState('fwd', 1)" onmouseup="sendState('fwd', 0)">ELORE</button>
        <div></div>
        <button ontouchstart="sendState('left', 1)" ontouchend="sendState('left', 0)" onmousedown="sendState('left', 1)" onmouseup="sendState('left', 0)">BALRA</button>
        <button class="btn-stop" onclick="fetch('/cmd?action=stop')">STOP</button>
        <button ontouchstart="sendState('right', 1)" ontouchend="sendState('right', 0)" onmousedown="sendState('right', 1)" onmouseup="sendState('right', 0)">JOBBRA</button>
        <div></div>
        <button ontouchstart="sendState('rev', 1)" ontouchend="sendState('rev', 0)" onmousedown="sendState('rev', 1)" onmouseup="sendState('rev', 0)">HATRA</button>
        <div></div>
    </div>

    <script>
        let state = { fwd: 0, rev: 0, left: 0, right: 0 };
        function sendState(dir, val) {
            state[dir] = val;
            let query = `/drive_state?fwd=${state.fwd}&rev=${state.rev}&left=${state.left}&right=${state.right}`;
            fetch(query).catch(e => {});
        }
        window.addEventListener('mouseup', () => { state = {fwd:0, rev:0, left:0, right:0}; fetch('/cmd?action=stop'); });
        window.addEventListener('touchend', () => { state = {fwd:0, rev:0, left:0, right:0}; fetch('/cmd?action=stop'); });
    </script>
</body>
</html>
"""'''

# Kicseréljük a HTML_PAGE részt
code = re.sub(r'HTML_PAGE = \""".*?\"\"\"', new_html_block, code, flags=re.DOTALL)

# Biztosítjuk, hogy a /drive_state route létezzen a Flask-ban
if "/drive_state" not in code:
    route_code = '''
@app_flask.route('/drive_state', methods=['GET'])
def handle_drive_state():
    global app_throttle, app_steer, current_mode
    fwd = int(request.args.get('fwd', 0))
    rev = int(request.args.get('rev', 0))
    left = int(request.args.get('left', 0))
    right = int(request.args.get('right', 0))
    current_mode = 1
    throttle = 0.0
    if fwd: throttle = BASE_SPEED
    elif rev: throttle = -REVERSE_SPEED
    steer = 0.0
    if left: steer = -KANYAR_EROSSEG
    elif right: steer = KANYAR_EROSSEG
    with cmd_lock:
        global web_throttle, web_steer
        web_throttle = throttle
        web_steer = steer
    return "OK"
'''
    code = code.replace("app_flask.run(", route_code + "\napp_flask.run(")

with open("/home/khajni/robot_car/picar_hailo_multimode.py", "w") as f:
    f.write(code)

print("HTML és szerver sikeresen javítva!")
