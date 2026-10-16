with open("/home/khajni/robot_car/picar_hailo_multimode.py", "r") as f:
    code = f.read()

# Még kisebb fordulási sebesség (0.28) és rövidebb idő (0.35 mp)
old_turn = """            elif avoid_state == "TURNING":
                # Lágyabb, rövidebb és lassabb fordulás (0.5 mp, 0.35 sebesség)
                if current_time - avoid_state_timer < 0.5:
                    drive(avoid_turn_dir * 0.35, -avoid_turn_dir * 0.35)
                    status_text = f"FINOM FORDULAS ({'JOBBRA' if avoid_turn_dir==1 else 'BALRA'})"
                else:
                    stop()
                    avoid_state = "FORWARD_CLEAR"
                    avoid_state_timer = current_time"""

new_turn = """            elif avoid_state == "TURNING":
                # Nagyon finom, kis szögű korrekció (0.35 mp, 0.28 sebesség)
                if current_time - avoid_state_timer < 0.35:
                    drive(avoid_turn_dir * 0.28, -avoid_turn_dir * 0.28)
                    status_text = f"KICSISZOGU KORREKCIO ({'JOBBRA' if avoid_turn_dir==1 else 'BALRA'})"
                else:
                    stop()
                    avoid_state = "FORWARD_CLEAR"
                    avoid_state_timer = current_time"""

if old_turn in code:
    code = code.replace(old_turn, new_turn)
else:
    # Ha az előző finomítás más szöveggel ment be, cseréljük közvetlenül a TURNING ágat
    import re
    code = re.sub(r'elif avoid_state == "TURNING":.*?(?=elif avoid_state ==|elif current_mode ==)', '''elif avoid_state == "TURNING":
                if current_time - avoid_state_timer < 0.35:
                    drive(avoid_turn_dir * 0.28, -avoid_turn_dir * 0.28)
                    status_text = f"KICSISZOGU KORREKCIO ({'JOBBRA' if avoid_turn_dir==1 else 'BALRA'})"
                else:
                    stop()
                    avoid_state = "FORWARD_CLEAR"
                    avoid_state_timer = current_time
    ''', code, flags=re.DOTALL)

with open("/home/khajni/robot_car/picar_hailo_multimode.py", "w") as f:
    f.write(code)

print("Fordulási szög csökkentve!")
