with open("/home/khajni/robot_car/picar_hailo_multimode.py", "r") as f:
    code = f.read()

old_block = """        # 3. AKADÁLYKIKERÜLÉS + OPTIKAI ELAKADÁS (STALL) ÉRZÉKELÉS
        elif current_mode == 3:
            # Optikai mozgásmérés a képkockákból előrehaladás közben
            gray_curr = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2GRAY)
            if 'prev_gray_frame' not in globals() or prev_gray_frame is None:
                prev_gray_frame = gray_curr
                forward_start_time = current_time

            if avoid_state == "FORWARD":
                # Kiszámoljuk a különbséget az előző és jelenlegi kép között
                frame_diff = cv2.absdiff(prev_gray_frame, gray_curr)
                motion_score = float(np.mean(frame_diff))

                # Ha előre megyünk, de a kép alig mozdul ( < 1.8 ), és már telt el 0.6 másodperc -> NEKIÜTKÖZTÜNK VALAMINEK!
                is_stalled = (current_time - forward_start_time > 0.6) and (motion_score < 1.8)

                if obstacle_in_front or is_stalled:
                    stop()
                    avoid_turn_dir = 1 if obs_left >= obs_right else -1
                    avoid_state = "BACKUP"
                    avoid_state_timer = current_time
                    status_text = "NEKIÜTKÖZÖTT (ELAKADÁS)! TOLATÁS..." if is_stalled else "AKADALY! HÁTRÁLÁS..."
                else:
                    drive(BASE_SPEED, BASE_SPEED)
                    status_text = f"HALADÁS ELŐRE (Mozgás: {motion_score:.1f})"
            else:
                forward_start_time = current_time

            prev_gray_frame = gray_curr

            if avoid_state == "BACKUP":
                if current_time - avoid_state_timer < 0.85:
                    drive(-0.50, -0.50)
                    status_text = "ELAKADÁS: ERŐS TOLATÁS..."
                else:
                    stop()
                    avoid_state = "TURNING"
                    avoid_state_timer = current_time

            elif avoid_state == "TURNING":
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
                    status_text = "ÚJRATERVEZÉS ÉS ELHALADÁS"
                else:
                    avoid_state = "FORWARD" """

new_block = """        # 3. AKADÁLYKIKERÜLÉS (MEGELŐZŐ + PLUSZ ÜTKÖZÉS-KORREKCIÓ)
        elif current_mode == 3:
            gray_curr = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2GRAY)
            if 'prev_gray_frame' not in globals() or prev_gray_frame is None:
                prev_gray_frame = gray_curr
                forward_start_time = current_time

            if avoid_state == "FORWARD":
                frame_diff = cv2.absdiff(prev_gray_frame, gray_curr)
                motion_score = float(np.mean(frame_diff))
                
                # Elakadás figyelése: ha előre megyünk, de a kép nem mozdul több mint 0.6 mp-ig
                is_stalled = (current_time - forward_start_time > 0.6) and (motion_score < 1.8)

                # 1. Elsődleges: ha látja az akadályt, időben kikerüli
                if obstacle_in_front:
                    stop()
                    avoid_turn_dir = 1 if obs_left >= obs_right else -1
                    avoid_state = "BACKUP"
                    avoid_state_timer = current_time
                    status_text = "AKADÁLY ÉSZLELVE -> Tolatás..."
                # 2. Másodlagos (plusz): ha nem látta, de nekiment és megakadt
                elif is_stalled:
                    stop()
                    avoid_turn_dir = 1 if obs_left >= obs_right else -1
                    avoid_state = "BACKUP"
                    avoid_state_timer = current_time
                    status_text = "ÜTKÖZÉS / ELAKADÁS -> Korrekciós tolatás..."
                else:
                    drive(BASE_SPEED, BASE_SPEED)
                    status_text = "ÚT TISZTA - HALADÁS ELŐRE"
            else:
                forward_start_time = current_time

            prev_gray_frame = gray_curr

            if avoid_state == "BACKUP":
                if current_time - avoid_state_timer < 0.65:
                    drive(-0.45, -0.45)
                    status_text = "HÁTRÁLÁS..."
                else:
                    stop()
                    avoid_state = "TURNING"
                    avoid_state_timer = current_time

            elif avoid_state == "TURNING":
                if current_time - avoid_state_timer < 0.50:
                    drive(avoid_turn_dir * 0.42, -avoid_turn_dir * 0.42)
                    status_text = f"KITÉRŐ FORDULÁS ({'JOBBRA' if avoid_turn_dir==1 else 'BALRA'})"
                else:
                    stop()
                    avoid_state = "FORWARD_CLEAR"
                    avoid_state_timer = current_time

            elif avoid_state == "FORWARD_CLEAR":
                if current_time - avoid_state_timer < 0.55:
                    drive(BASE_SPEED, BASE_SPEED)
                    status_text = "ELHALADÁS"
                else:
                    avoid_state = "FORWARD" """

if old_block.strip() in code:
    code = code.replace(old_block.strip(), new_block.strip())
    with open("/home/khajni/robot_car/picar_hailo_multimode.py", "w") as f:
        f.write(code)
    print("Sikeresen javítva!")
else:
    print("Hiba a blokk keresésekor.")
