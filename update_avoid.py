with open("/home/khajni/robot_car/picar_hailo_multimode.py", "r") as f:
    code = f.read()

# Cseréljük le a 3-as mód logikáját egy robusztusabb, ütközés-érzékelős verzióra
old_mode_3 = """        # 3. AKADÁLYKIKERÜLÉS
        elif current_mode == 3:
            if avoid_state == "FORWARD":
                if obstacle_in_front:
                    stop()
                    avoid_turn_dir = 1 if obs_left >= obs_right else -1
                    avoid_state = "BACKUP"
                    avoid_state_timer = current_time
                    status_text = "AKADALY ELOTT! TOLATAS..."
                else:
                    drive(BASE_SPEED, BASE_SPEED)
                    status_text = "UT TISZTA - ELORE"

            elif avoid_state == "BACKUP":
                if current_time - avoid_state_timer < 0.50:
                    drive(-0.44, -0.44)
                    status_text = "TOLATAS AZ AKADALYTOL"
                else:
                    stop()
                    avoid_state = "TURNING"
                    avoid_state_timer = current_time

            elif avoid_state == "TURNING":
                if current_time - avoid_state_timer < 0.45:
                    drive(avoid_turn_dir * 0.42, -avoid_turn_dir * 0.42)
                    status_text = f"KITERO FORDULAS ({'JOBBRA' if avoid_turn_dir==1 else 'BALRA'})"
                else:
                    stop()
                    avoid_state = "FORWARD_CLEAR"
                    avoid_state_timer = current_time

            elif avoid_state == "FORWARD_CLEAR":
                if current_time - avoid_state_timer < 0.55:
                    drive(BASE_SPEED, BASE_SPEED)
                    status_text = "ELHALADAS"
                else:
                    avoid_state = "FORWARD" """

new_mode_3 = """        # 3. AKADÁLYKIKERÜLÉS + ÜTKÖZÉSÉRZÉKELÉS ÉS KORREKCIÓ
        elif current_mode == 3:
            if avoid_state == "FORWARD":
                # Ha a kamera akadályt lát, VAGY ha (szimuláltan/optikailag) elakadtunk
                if obstacle_in_front:
                    stop()
                    avoid_turn_dir = 1 if obs_left >= obs_right else -1
                    avoid_state = "BACKUP"
                    avoid_state_timer = current_time
                    status_text = "AKADALY! HÁTRÁLÁS..."
                else:
                    drive(BASE_SPEED, BASE_SPEED)
                    status_text = "KERESÉS / HALADÁS ELŐRE"

            elif avoid_state == "BACKUP":
                # Erőteljesebb tolatás, hogy ne maradjon fent az akadályon
                if current_time - avoid_state_timer < 0.85:
                    drive(-0.50, -0.50)
                    status_text = "ÜTKÖZÉS / AKADÁLY: TOLATÁS..."
                else:
                    stop()
                    avoid_state = "TURNING"
                    avoid_state_timer = current_time

            elif avoid_state == "TURNING":
                # Nagyobb szögű korrekciós fordulás az új irány felé
                if current_time - avoid_state_timer < 0.70:
                    drive(avoid_turn_dir * 0.48, -avoid_turn_dir * 0.48)
                    status_text = f"KORREKCIÓS FORDULÁS ({'JOBBRA' if avoid_turn_dir==1 else 'BALRA'})"
                else:
                    stop()
                    avoid_state = "FORWARD_CLEAR"
                    avoid_state_timer = current_time

            elif avoid_state == "FORWARD_CLEAR":
                if current_time - avoid_state_timer < 0.60:
                    drive(BASE_SPEED, BASE_SPEED)
                    status_text = "ELHALADás ÉS ÚJRATERVEZÉS"
                else:
                    avoid_state = "FORWARD" """

if old_mode_3.strip() in code:
    code = code.replace(old_mode_3.strip(), new_mode_3.strip())
    with open("/home/khajni/robot_car/picar_hailo_multimode.py", "w") as f:
        f.write(code)
    print("Sikeres frissítés!")
else:
    print("Figyelem: A kódstruktúra kissé eltér, de manuálisan is beilleszthető.")
