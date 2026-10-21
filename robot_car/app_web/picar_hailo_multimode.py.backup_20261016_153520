#!/usr/bin/env python3
# Hailo-alapú objektumfelismerés és példányszegmentálás 
import os
import sys
import time
import argparse
import threading
from pathlib import Path
import cv2
import numpy as np
import pygame
from gpiozero import PWMOutputDevice
from flask import Flask, Response, request, render_template_string

os.environ["QT_QPA_PLATFORM"] = "xcb"

HAILO_APPS_DIR = Path("/home/khajni/hailo-apps")
OD_DIR = HAILO_APPS_DIR / "hailo_apps/python/standalone_apps/object_detection"
SEG_DIR = (
    HAILO_APPS_DIR / "hailo_apps/python/standalone_apps/instance_segmentation"
)

for p in [str(HAILO_APPS_DIR), str(OD_DIR), str(SEG_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from hailo_apps.python.core.common.toolbox import (
    InputContext,
    VisualizationSettings,
    init_input_source,
)

# Beállítások
BASE_SPEED = 0.40
TURN_STRENGTH = 0.30
REVERSE_SPEED = 0.44

# Távolságbecslés
FOCAL_LENGTH = 520.0
KNOWN_REAL_WIDTHS = {
    "person": 45.0,
    "cell phone": 7.5,
    "bottle": 7.0,
    "cup": 8.0,
    "laptop": 32.0,
    "chair": 50.0,
    "sports ball": 22.0,
}
DEFAULT_WIDTH = 20.0


def calculate_optical_distance(real_w_cm, width_px):
    if width_px <= 0:
        return 0
    return (real_w_cm * FOCAL_LENGTH) / width_px


left_forward = PWMOutputDevice(7, frequency=100)
left_backward = PWMOutputDevice(8, frequency=100)
right_forward = PWMOutputDevice(25, frequency=100)
right_backward = PWMOutputDevice(27, frequency=100)


def stop():
    left_forward.value = 0
    left_backward.value = 0
    right_forward.value = 0
    right_backward.value = 0


def drive(left, right):
    left = float(np.clip(left, -1.0, 1.0))
    right = float(np.clip(right, -1.0, 1.0))
    if left >= 0:
        left_backward.value = 0
        left_forward.value = left
    else:
        left_forward.value = 0
        left_backward.value = abs(left)

    if right >= 0:
        right_backward.value = 0
        right_forward.value = right
    else:
        right_forward.value = 0
        right_backward.value = abs(right)


stop()

WIDTH, HEIGHT = 640, 360
running = True
enhance_enabled = False

MODE_NAMES = {
    1: "KEZI (WASD / TELEFON)",
    2: "AUTOMATA CELKOVETES",
    3: "AKADALY + FAL KIKERULES",
    0: "ALLJ (VESZFEK)",
}

avoid_state = "FORWARD"
avoid_state_timer = 0.0
avoid_turn_dir = 1
last_target_time = 0.0
last_drive_cmd = (0.0, 0.0)

prev_target_pos = None
last_motion_time = 0.0

# Képjavítás
clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
sharpen_kernel = np.array(
    [[0, -0.6, 0], [-0.6, 3.4, -0.6], [0, -0.6, 0]], dtype=np.float32
)


def enhance_frame(frame):
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l_enhanced = clahe.apply(l)
    lab_enhanced = cv2.merge((l_enhanced, a, b))
    enhanced_bgr = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)
    return cv2.filter2D(enhanced_bgr, -1, sharpen_kernel)


def detect_wall_or_couch(frame):
    h, w = frame.shape[:2]
    roi = frame[int(h * 0.60) :, :]
    gray = (
        cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) == 3 else roi
    )
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 40, 120)

    mid = edges[:, int(w * 0.20) : int(w * 0.80)]
    edge_ratio = float(np.count_nonzero(mid)) / float(mid.size)
    mean_val, std_val = cv2.meanStdDev(gray)
    brightness = float(mean_val[0][0])
    contrast = float(std_val[0][0])

    # Felületvizsgálat
    is_white_surface = brightness > 185 and contrast < 25
    return (edge_ratio > 0.08) or (brightness < 30) or is_white_surface


# Szerver
app_flask = Flask(__name__)
latest_jpeg = None
incoming_cmd = None
cmd_lock = threading.Lock()

HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>PiCar-X Távirányító</title>
    <style>
        body { font-family: Arial; text-align: center; background: #1a1a1a; color: white; margin: 0; padding: 10px; }
        img { width: 100%; max-height: 50vh; object-fit: contain; border-radius: 8px; }
        .grid { display: grid; grid-template-columns: repeat(3, 90px); gap: 10px; justify-content: center; margin-top: 10px; }
        button { height: 65px; font-size: 16px; font-weight: bold; border-radius: 8px; border: none; background: #333; color: white; touch-action: manipulation; }
        button:active { background: #555; }
        .btn-modes { display: flex; justify-content: center; gap: 6px; margin-top: 10px; flex-wrap: wrap; }
        .btn-mode { height: 40px; padding: 0 10px; background: #007acc; font-size: 14px; }
        .speed-box { margin: 10px auto; background: #2a2a2a; padding: 8px; border-radius: 8px; width: 85%; max-width: 320px; }
    </style>
</head>
<body>
    <h3>PiCar-X Élő Kép</h3>
    <img src="/video_feed">
    
    <div class="speed-box">
        <label style="font-size: 14px;">Sebesség: <span id="speedVal">40</span>%</label><br>
        <input type="range" id="speedSlider" min="20" max="100" value="40" style="width: 100%; margin-top: 5px;" 
               oninput="document.getElementById('speedVal').innerText=this.value; sendCmd('speed_' + this.value)">
    </div>

    <div class="btn-modes">
        <button class="btn-mode" onclick="sendCmd('mode_1')">1: Kezi</button>
        <button class="btn-mode" onclick="sendCmd('mode_2')">2: Kovetes</button>
        <button class="btn-mode" onclick="sendCmd('mode_3')">3: Kerules</button>
    </div>
    <div class="btn-modes" style="margin-top: 5px;">
        <button class="btn-mode" style="background:#e67e22; width: 48%;" onclick="sendCmd('switch_model')">M: Modell valtas</button>
        <button class="btn-mode" style="background:#8e44ad; width: 48%;" onclick="sendCmd('toggle_enhance')">C: Kepjavitas</button>
    </div>
    <div class="grid">
        <div></div>
        <button ontouchstart="sendCmd('forward'); event.preventDefault();" onmousedown="sendCmd('forward')"
                ontouchend="sendCmd('motor_stop'); event.preventDefault();" onmouseup="sendCmd('motor_stop')">Elore</button>
        <div></div>
        <button ontouchstart="sendCmd('left'); event.preventDefault();" onmousedown="sendCmd('left')"
                ontouchend="sendCmd('motor_stop'); event.preventDefault();" onmouseup="sendCmd('motor_stop')">Balra</button>
        <button style="background: red;" onclick="sendCmd('stop')">Stop</button>
        <button ontouchstart="sendCmd('right'); event.preventDefault();" onmousedown="sendCmd('right')"
                ontouchend="sendCmd('motor_stop'); event.preventDefault();" onmouseup="sendCmd('motor_stop')">Jobbra</button>
        <div></div>
        <button ontouchstart="sendCmd('backward'); event.preventDefault();" onmousedown="sendCmd('backward')"
                ontouchend="sendCmd('motor_stop'); event.preventDefault();" onmouseup="sendCmd('motor_stop')">Hatra</button>
        <div></div>
    </div>
    <script>
        function sendCmd(action) {
            fetch('/cmd?action=' + action).catch(function(error) {});
        }
    </script>
</body>
</html>
"""


@app_flask.route("/")
def index():
    return render_template_string(HTML_PAGE)


@app_flask.route("/video_feed")
def video_feed():
    def gen():
        global latest_jpeg
        while True:
            if latest_jpeg is not None:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + latest_jpeg + b"\r\n"
                )
            time.sleep(0.04)

    return Response(
        gen(), mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app_flask.route("/cmd", methods=["GET"])
def handle_cmd():
    global incoming_cmd
    action = request.args.get("action")
    if action:
        with cmd_lock:
            incoming_cmd = action
    return "OK"


def start_flask():
    import logging

    log = logging.getLogger("werkzeug")
    log.setLevel(logging.ERROR)
    app_flask.run(host="0.0.0.0", port=5000, threaded=True, debug=False)


def custom_visualize(
    input_context,
    visualization_settings,
    output_queue,
    post_process_callback_fn,
    fps_tracker,
    stop_event,
    engine_name,
    start_mode=1,
    start_enhance=False,
):
    global running, enhance_enabled
    global avoid_state, avoid_state_timer, avoid_turn_dir
    global last_target_time, last_drive_cmd, prev_target_pos, last_motion_time
    global latest_jpeg, incoming_cmd, BASE_SPEED

    current_mode = start_mode
    enhance_enabled = start_enhance

    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    titles = {"det": "YOLOv6 Dobozok", "seg": "YOLOv5 Szegmentacio"}
    pygame.display.set_caption(
        f"PiCar - {titles.get(engine_name, engine_name)} | [M]: DET<->SEG"
    )
    clock = pygame.time.Clock()

    import hailo_apps.python.standalone_apps.object_detection.object_detection as od

    labels = od.get_labels(
        str(HAILO_APPS_DIR / "resources/json/coco_eighty.json")
    )
    exit_code = 0

    app_throttle, app_steer = 0.0, 0.0

    while not stop_event.is_set() and running:
        clock.tick(30)
        current_time = time.time()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                exit_code = 0
                stop_event.set()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    current_mode = 1
                    stop()
                elif event.key == pygame.K_2:
                    current_mode = 2
                    prev_target_pos = None
                    last_motion_time = 0.0
                    stop()
                elif event.key == pygame.K_3:
                    current_mode = 3
                    avoid_state = "FORWARD"
                    avoid_state_timer = current_time
                    stop()
                elif event.key == pygame.K_SPACE:
                    current_mode = 0
                    stop()
                elif event.key == pygame.K_c:
                    enhance_enabled = not enhance_enabled
                elif event.key == pygame.K_m or event.key == pygame.K_TAB:
                    enh_flag = 100 if enhance_enabled else 0
                    target_code = 20 if engine_name == "det" else 10
                    exit_code = target_code + current_mode + enh_flag
                    running = False
                    stop_event.set()
                elif event.key == pygame.K_ESCAPE:
                    exit_code = 0
                    running = False
                    stop_event.set()

        req_action = None
        with cmd_lock:
            if incoming_cmd is not None:
                req_action = incoming_cmd
                incoming_cmd = None

        if req_action:
            if req_action.startswith("speed_"):
                try:
                    val = int(req_action.split("_")[1])
                    BASE_SPEED = max(0.1, min(1.0, val / 100.0))
                    print(f"Sebesség módosítva: {val}% ({BASE_SPEED})")
                except ValueError:
                    pass
            elif req_action == "toggle_enhance":
                enhance_enabled = not enhance_enabled
                print(
                    f"Telefonrol valtva: enhance_enabled = {enhance_enabled}"
                )
            elif req_action == "mode_1":
                current_mode = 1
                stop()
            elif req_action == "mode_2":
                current_mode = 2
                prev_target_pos = None
                last_motion_time = 0.0
                stop()
            elif req_action == "mode_3":
                current_mode = 3
                avoid_state = "FORWARD"
                avoid_state_timer = current_time
                stop()
            elif req_action == "switch_model":
                enh_flag = 100 if enhance_enabled else 0
                target_code = 20 if engine_name == "det" else 10
                exit_code = target_code + current_mode + enh_flag
                running = False
                stop_event.set()
            elif req_action == "forward":
                app_throttle = BASE_SPEED
                app_steer = 0.0
            elif req_action == "backward":
                app_throttle = -BASE_SPEED
                app_steer = 0.0
            elif req_action == "left":
                app_steer = -TURN_STRENGTH
                app_throttle = 0.0
            elif req_action == "right":
                app_steer = TURN_STRENGTH
                app_throttle = 0.0
            elif req_action == "motor_stop" or req_action == "release":
                app_throttle = 0.0
                app_steer = 0.0
                stop()
            elif req_action == "stop":
                current_mode = 1
                app_throttle = 0.0
                app_steer = 0.0
                stop()

        try:
            item = output_queue.get(timeout=0.1)
        except Exception:
            continue

        if item is None:
            break

        input_frame, raw_out = item

        if enhance_enabled:
            input_frame = enhance_frame(input_frame)

        annotated_frame = post_process_callback_fn(input_frame.copy(), raw_out)
        if (
            annotated_frame.shape[1] != WIDTH
            or annotated_frame.shape[0] != HEIGHT
        ):
            annotated_frame = cv2.resize(annotated_frame, (WIDTH, HEIGHT))

        target_person = None
        max_height = 0
        obstacle_in_front = False
        obs_left = 0
        obs_right = 0
        status_text = ""

        detections = []
        if isinstance(raw_out, dict):
            for key, val in raw_out.items():
                if isinstance(val, np.ndarray) and val.ndim >= 2:
                    detections = val[0] if val.ndim == 3 else val
                    break
        elif isinstance(raw_out, list) and len(raw_out) > 0:
            detections = (
                raw_out[0]
                if isinstance(raw_out[0], (list, np.ndarray))
                else raw_out
            )
        elif isinstance(raw_out, np.ndarray):
            detections = raw_out[0] if raw_out.ndim == 3 else raw_out

        for det in detections:
            try:
                if len(det) >= 6:
                    ymin, xmin, ymax, xmax, score, cls_id = det[:6]
                elif len(det) == 5:
                    ymin, xmin, ymax, xmax, score = det[:5]
                    cls_id = 0
                else:
                    continue

                if float(score) < 0.28:
                    continue

                cls_id = int(cls_id)
                label = (
                    labels[cls_id]
                    if labels and cls_id < len(labels)
                    else str(cls_id)
                )

                if xmax <= 1.0 and ymax <= 1.0:
                    x1, y1 = int(xmin * WIDTH), int(ymin * HEIGHT)
                    x2, y2 = int(xmax * WIDTH), int(ymax * HEIGHT)
                else:
                    x1, y1 = int(xmin), int(ymin)
                    x2, y2 = int(xmax), int(ymax)

                box_h = y2 - y1
                box_w = x2 - x1
                cx = (x1 + x2) // 2

                # Távolság
                real_w = KNOWN_REAL_WIDTHS.get(label, DEFAULT_WIDTH)
                optical_cm = calculate_optical_distance(real_w, box_w)

                dist_lbl = f"Tavolsag: {int(optical_cm)} cm"
                cv2.putText(
                    annotated_frame,
                    dist_lbl,
                    (x1, max(20, y1 - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (220, 220, 220),
                    2,
                )

                if (label == "person" or cls_id == 0) and box_h > max_height:
                    max_height = box_h
                    target_person = (cx, y2, box_h, score)

                if (
                    label != "person"
                    and y2 > (HEIGHT * 0.52)
                    and box_w > 35
                    and box_h > 35
                ):
                    if (WIDTH * 0.22) < cx < (WIDTH * 0.78):
                        obstacle_in_front = True
                    elif cx <= (WIDTH * 0.22):
                        obs_left += 1
                    else:
                        obs_right += 1
            except Exception:
                continue

        if current_mode == 3 and not obstacle_in_front:
            if detect_wall_or_couch(annotated_frame):
                obstacle_in_front = True

        if current_mode == 1:
            keys = pygame.key.get_pressed()
            throttle, steer = app_throttle, app_steer
            if keys[pygame.K_w] or keys[pygame.K_UP]:
                throttle = BASE_SPEED
            elif keys[pygame.K_s] or keys[pygame.K_DOWN]:
                throttle = -BASE_SPEED
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                steer = -TURN_STRENGTH
            elif keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                steer = TURN_STRENGTH

            if throttle > 0:
                drive(throttle + steer, throttle - steer)
            elif throttle < 0:
                drive(throttle - steer, throttle + steer)
            elif steer != 0:
                drive(steer, -steer)
            elif app_throttle == 0 and app_steer == 0:
                stop()
            status_text = "KEZI WASD / APP"

        elif current_mode == 2:
            if target_person is not None:
                last_target_time = current_time
                cx, y2, box_h, score = target_person
                error_x = (cx - (WIDTH // 2)) / (WIDTH // 2)
                steer = error_x * 0.35
                dist_ratio = y2 / HEIGHT

                is_moving = False
                if prev_target_pos is not None:
                    p_cx, p_y2 = prev_target_pos
                    delta_dist = np.hypot(cx - p_cx, y2 - p_y2)
                    if delta_dist > 8.0:
                        is_moving = True
                        last_motion_time = current_time
                else:
                    last_motion_time = current_time
                    is_moving = True

                prev_target_pos = (cx, y2)
                recently_moved = (current_time - last_motion_time) < 0.45

                if dist_ratio > 0.95:
                    status_text = f"TOLATAS! ({int(dist_ratio * 100)}%)"
                    cmd = (-REVERSE_SPEED, -REVERSE_SPEED)
                elif dist_ratio >= 0.78 and not recently_moved:
                    status_text = (
                        f"MEGALLVA (EMBER ALL) - {int(dist_ratio * 100)}%"
                    )
                    cmd = (
                        (steer, -steer) if abs(error_x) > 0.16 else (0.0, 0.0)
                    )
                elif dist_ratio < 0.88 and (
                    recently_moved or dist_ratio < 0.78
                ):
                    status_text = (
                        f"KOVETES (MOZOGSZ: {int(dist_ratio * 100)}%)"
                    )
                    cmd = (BASE_SPEED + steer, BASE_SPEED - steer)
                else:
                    status_text = f"TARTAS ({int(dist_ratio * 100)}%)"
                    cmd = (
                        (steer, -steer) if abs(error_x) > 0.14 else (0.0, 0.0)
                    )

                last_drive_cmd = cmd
                drive(*cmd)
            else:
                prev_target_pos = None
                if current_time - last_target_time < 0.35:
                    status_text = "KOVETES (simitas)..."
                    drive(*last_drive_cmd)
                else:
                    status_text = "KERESES..."
                    stop()

        elif current_mode == 3:
            gray_curr = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2GRAY)
            if "prev_gray_frame" not in globals() or prev_gray_frame is None:
                prev_gray_frame = gray_curr
                forward_start_time = current_time

            if avoid_state == "FORWARD":
                frame_diff = cv2.absdiff(prev_gray_frame, gray_curr)
                motion_score = float(np.mean(frame_diff))

                is_stalled = (current_time - forward_start_time > 0.35) and (
                    motion_score < 3.5
                )

                if obstacle_in_front:
                    stop()
                    avoid_turn_dir = 1 if obs_left >= obs_right else -1
                    avoid_state = "BACKUP"
                    avoid_state_timer = current_time
                    status_text = "AKADALY ESZLELVE -> Tolatas..."
                elif is_stalled:
                    stop()
                    avoid_turn_dir = 1 if obs_left >= obs_right else -1
                    avoid_state = "BACKUP"
                    avoid_state_timer = current_time
                    status_text = "UTKOZES / ELAKADAS -> Korrekcios tolatas..."
                else:
                    drive(BASE_SPEED, BASE_SPEED)
                    status_text = "UT TISZTA - HALADAS ELORE"
            else:
                forward_start_time = current_time

            prev_gray_frame = gray_curr

            if avoid_state == "BACKUP":
                if current_time - avoid_state_timer < 1.1:
                    drive(-0.50, -0.50)
                    status_text = "HATRALAS ES ELAKADAS KORREKCIO..."
                else:
                    stop()
                    avoid_state = "TURNING"
                    avoid_state_timer = current_time

            elif avoid_state == "TURNING":
                if current_time - avoid_state_timer < 0.35:
                    drive(avoid_turn_dir * 0.28, -avoid_turn_dir * 0.28)
                    status_text = (
                        f"KICSISZOGU KORREKCIO "
                        f"({'JOBBRA' if avoid_turn_dir == 1 else 'BALRA'})"
                    )
                else:
                    stop()
                    avoid_state = "FORWARD_CLEAR"
                    avoid_state_timer = current_time
            elif avoid_state == "FORWARD_CLEAR":
                if current_time - avoid_state_timer < 0.55:
                    drive(BASE_SPEED, BASE_SPEED)
                    status_text = "ELHALADAS"
                else:
                    avoid_state = "FORWARD"
        elif current_mode == 0:
            stop()
            status_text = "ALLJ (VESZFEK - SPACE)"

        display_frame = annotated_frame.copy()
        _, jpeg_buff = cv2.imencode(
            ".jpg",
            cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB),
            [cv2.IMWRITE_JPEG_QUALITY, 65],
        )
        latest_jpeg = jpeg_buff.tobytes()

        surf = pygame.image.frombuffer(
            display_frame.tobytes(), (WIDTH, HEIGHT), "RGB"
        )
        screen.blit(surf, (0, 0))
        pygame.display.flip()

    stop()
    pygame.quit()
    sys.exit(exit_code)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", choices=["det", "seg"], default="det")
    parser.add_argument("--mode", type=int, default=1)
    parser.add_argument("--enhance", action="store_true")
    args = parser.parse_args()

    t = threading.Thread(target=start_flask, daemon=True)
    t.start()

    input_ctx = InputContext(
        input_src="rpi",
        batch_size=1,
        resolution=(WIDTH, HEIGHT),
        frame_rate=30,
        video_unpaced=False,
    )
    input_ctx = init_input_source(input_ctx)

    vis_settings = VisualizationSettings(
        output_dir=None,
        save_stream_output=False,
        output_resolution=None,
        no_display=False,
    )

    labels = str(HAILO_APPS_DIR / "resources/json/coco_eighty.json")

    try:
        if args.engine == "det":
            import hailo_apps.python.standalone_apps.object_detection.object_detection as od

            if not hasattr(od.logger, "success"):
                od.logger.success = od.logger.info
            od.visualize = lambda ic, vs, oq, pp, ft, se: custom_visualize(
                ic,
                vs,
                oq,
                pp,
                ft,
                se,
                engine_name="det",
                start_mode=args.mode,
                start_enhance=args.enhance,
            )
            hef = str(HAILO_APPS_DIR / "resources/models/hailo8/yolov6n.hef")
            od.run_inference_pipeline(
                net=hef,
                labels=labels,
                input_context=input_ctx,
                visualization_settings=vis_settings,
                enable_tracking=False,
                show_fps=False,
                time_to_run=None,
            )

        elif args.engine == "seg":
            import hailo_apps.python.standalone_apps.instance_segmentation.instance_segmentation as iseg

            if not hasattr(iseg.logger, "success"):
                iseg.logger.success = iseg.logger.info
            iseg.visualize = lambda ic, vs, oq, pp, ft, se: custom_visualize(
                ic,
                vs,
                oq,
                pp,
                ft,
                se,
                engine_name="seg",
                start_mode=args.mode,
                start_enhance=args.enhance,
            )
            hef = str(
                HAILO_APPS_DIR
                / "resources/models/hailo8/yolov5m_seg_with_nms.hef"
            )
            iseg.run_inference_pipeline(
                net=hef,
                labels=labels,
                model_type="yolov5_seg",
                input_context=input_ctx,
                visualization_settings=vis_settings,
                enable_tracking=False,
                show_fps=False,
                time_to_run=None,
            )
    finally:
        stop()


if __name__ == "__main__":
    main()
