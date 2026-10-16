with open("/home/khajni/robot_car/picar_hailo_multimode.py", "r") as f:
    content = f.read()

# Cseréljük ki a Flask parancskezelést a folyamatos kombinált vezérlésre
if "@app_flask.route('/cmd" in content:
    old_flask_cmds = """@app_flask.route('/cmd', methods=['GET'])
def handle_cmd():
    global incoming_cmd
    action = request.args.get('action')
    if action:
        with cmd_lock:
            incoming_cmd = action
    return "OK\""""

    new_flask_cmds = """@app_flask.route('/cmd', methods=['GET'])
def handle_cmd():
    global incoming_cmd
    action = request.args.get('action')
    if action:
        with cmd_lock:
            incoming_cmd = action
    return "OK"

@app_flask.route('/drive_state', methods=['GET'])
def handle_drive_state():
    global app_throttle, app_steer, current_mode
    fwd = int(request.args.get('fwd', 0))
    rev = int(request.args.get('rev', 0))
    left = int(request.args.get('left', 0))
    right = int(request.args.get('right', 0))
    
    current_mode = 1 # Ha a kézi gombokat nyomják, automatikusan 1-es (kézi) módba vált
    
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
    return "OK\""""

    # Kicseréljük
    # Biztosabb ha a handle_cmd környékét frissítjük
    print("Szerver parancsok frissítése...")

