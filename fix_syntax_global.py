with open("/home/khajni/robot_car/picar_hailo_multimode.py", "r") as f:
    code = f.read()

# Javítjuk a rossz helyen lévő global deklarációt a Flask útvonalban
code = code.replace("    current_mode =\n        global current_mode", "    global current_mode")
code = code.replace("    req_action = request.args.get('action')\n    global current_mode", "    global current_mode\n    req_action = request.args.get('action')")

# Ha esetleg rosszul maradt benne a fenti minta, keressük meg a függvény elejét
if "def cmd():" in code or "@app_flask.route('/cmd')" in code:
    # Biztosítsuk, hogy a /cmd alatt a global current_mode az első sor legyen
    old_snippet = """@app_flask.route('/cmd')
def cmd():
    req_action = request.args.get('action')
    global current_mode"""
    
    new_snippet = """@app_flask.route('/cmd')
def cmd():
    global current_mode
    req_action = request.args.get('action')"""
    if old_snippet in code:
        code = code.replace(old_snippet, new_snippet)

with open("/home/khajni/robot_car/picar_hailo_multimode.py", "w") as f:
    f.write(code)

print("Szintaxis javítva!")
