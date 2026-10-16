with open("/home/khajni/robot_car/picar_hailo_multimode.py", "r") as f:
    code = f.read()

# Cseréljük ki a BACKUP és TURNING időzítéseket hosszabbra és határozottabbra
old_maneuver = """            if avoid_state == "BACKUP":
                if current_time - avoid_state_timer < 0.65:
                    drive(-0.45, -0.45)
                    status_text = "HATRALAS..."
                else:
                    stop()
                    avoid_state = "TURNING"
                    avoid_state_timer = current_time

            elif avoid_state == "TURNING":
                if current_time - avoid_state_timer < 0.50:
                    drive(avoid_turn_dir * 0.42, -avoid_turn_dir * 0.42)
                    status_text = f"KITERO FORDULAS ({'JOBBRA' if avoid_turn_dir==1 else 'BALRA'})"
                else:
                    stop()
                    avoid_state = "FORWARD_CLEAR"
                    avoid_state_timer = current_time"""

new_maneuver = """            if avoid_state == "BACKUP":
                # Hosszabb, határozottabb tolatás (1.1 mp), hogy teljesen elszakadjon a faltól
                if current_time - avoid_state_timer < 1.1:
                    drive(-0.50, -0.50)
                    status_text = "HATRALAS ES ELAKADAS KORREKCIO..."
                else:
                    stop()
                    avoid_state = "TURNING"
                    avoid_state_timer = current_time

            elif avoid_state == "TURNING":
                # Szélesebb, nagyobb szögű fordulás (0.85 mp), hogy ne forduljon vissza ugyanabba a falba
                if current_time - avoid_state_timer < 0.85:
                    drive(avoid_turn_dir * 0.48, -avoid_turn_dir * 0.48)
                    status_text = f"NAGY FORDULAS ({'JOBBRA' if avoid_turn_dir==1 else 'BALRA'})"
                else:
                    stop()
                    avoid_state = "FORWARD_CLEAR"
                    avoid_state_timer = current_time"""

if old_maneuver in code:
    code = code.replace(old_maneuver, new_maneuver)
    with open("/home/khajni/robot_car/picar_hailo_multimode.py", "w") as f:
        f.write(code)
    print("Sikeresen javítva!")
else:
    print("A blokk nem található.")
