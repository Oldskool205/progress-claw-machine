#!/usr/bin/env python3
"""Local claw-machine dashboard with Raspberry Pi GPIO start control."""

import os
import base64
import binascii
import glob
import json
from io import BytesIO
import subprocess
import threading
import time
from collections import deque
from datetime import datetime

from flask import Flask, Response, jsonify, render_template, request, send_from_directory
import numpy as np
from PIL import Image, ImageDraw, ImageFont

try:
    import cv2
except ImportError:
    cv2 = None

try:
    from gpiozero import OutputDevice
except ImportError:
    OutputDevice = None


app = Flask(__name__)
lock = threading.Lock()
PLAYER_PHOTO_PATH = os.path.join(app.static_folder, "images", "current-player.jpg")
PLAYER_HISTORY_DIR = os.path.join(app.static_folder, "images", "players")
YOLO_RAW_PHOTO_DIR = os.getenv(
    "CLAW_YOLO_RAW_PHOTO_DIR",
    "/home/araya/Projects/Progress-Claw-OS/ai/training/yolo_people/raw_photos",
)

START_GPIO_PIN = int(os.getenv("CLAW_START_GPIO", "17"))
GRABBER_POWER_GPIO_PINS = tuple(
    int(pin.strip())
    for pin in os.getenv("CLAW_GRABBER_POWER_GPIOS", "22,23,24").split(",")
    if pin.strip()
)
MIN_PLAY_DURATION_SECONDS = 10
MAX_PLAY_DURATION_SECONDS = 180
MIN_GRABBER_POWER_PERCENT = 40
MAX_GRABBER_POWER_PERCENT = 100
GRABBER_POWER_STEP_PERCENT = 10
GRABBER_POWER_MODES = ("manual", "ai")
DEFAULT_GRABBER_POWER_MODE = os.getenv("CLAW_GRABBER_POWER_MODE", "manual")
PLAY_DURATION_SECONDS = max(
    MIN_PLAY_DURATION_SECONDS,
    min(MAX_PLAY_DURATION_SECONDS, int(os.getenv("CLAW_PLAY_DURATION_SECONDS", "60"))),
)
GRABBER_POWER_PERCENT = max(
    MIN_GRABBER_POWER_PERCENT,
    min(MAX_GRABBER_POWER_PERCENT, int(os.getenv("CLAW_GRABBER_POWER_PERCENT", "100"))),
)
READY_DURATION_SECONDS = int(os.getenv("CLAW_READY_DURATION_SECONDS", "3"))
GRABBER_START_DURATION_SECONDS = int(os.getenv("CLAW_GRABBER_START_SECONDS", "6"))
USB_CAMERA_DEVICE = os.getenv("CLAW_USB_CAMERA_DEVICE", "/dev/video0")
ARDUINO_DEVICE = os.getenv("CLAW_ARDUINO_DEVICE", "/dev/ttyUSB0")
HACKER_UNLOCK_PASSWORD = os.getenv("CLAW_HACKER_PASSWORD", "1234")
ARDUINO_DEVICE_PATTERNS = (
    ARDUINO_DEVICE,
    "/dev/ttyUSB*",
    "/dev/ttyACM*",
    "/dev/serial/by-id/*",
)
PLAYER_NAME_FONT = "/usr/share/fonts/truetype/lato/Lato-Heavy.ttf"

state = {
    "people": 0,
    "target": 10,
    "credits": 0,
    "plays_today": 0,
    "machine_enabled": True,
    "hacker_mode": False,
    "arduino_connected": False,
    "machine_status": "Ready",
    "play_mode": None,
    "countdown_starts_at": None,
    "play_ends_at": None,
    "play_duration": PLAY_DURATION_SECONDS,
    "grabber_power_percent": GRABBER_POWER_PERCENT,
    "manual_grabber_power_percent": GRABBER_POWER_PERCENT,
    "grabber_power_mode": (
        DEFAULT_GRABBER_POWER_MODE
        if DEFAULT_GRABBER_POWER_MODE in GRABBER_POWER_MODES
        else "manual"
    ),
    "ai_people_count": 0,
    "ai_grabber_power_percent": 60,
    "ready_duration": READY_DURATION_SECONDS,
    "grabber_start_duration": GRABBER_START_DURATION_SECONDS,
    "player_photo_ready": False,
    "player_photo_version": 0,
    "current_player_name": None,
    "players": [],
    "last_play": None,
}
events = deque(maxlen=30)
start_output = None
grabber_power_outputs = []
play_generation = 0
camera_frame = None
camera_condition = threading.Condition()


def dashboard_state(**extra):
    return {**state, "events": list(events), **extra}


def reject_when_hacker_mode():
    if state["hacker_mode"]:
        return jsonify({"ok": False, "error": "Hacker mode is active"}), 423
    return None


def add_event(message, kind="info"):
    events.appendleft(
        {
            "message": message,
            "kind": kind,
            "time": datetime.now().strftime("%H:%M:%S"),
        }
    )


def award_credits(previous_people):
    previous_milestones = previous_people // state["target"]
    current_milestones = state["people"] // state["target"]
    earned = max(0, current_milestones - previous_milestones)
    if earned:
        state["credits"] += earned
        add_event(f"{earned} play credit earned", "success")


def set_people(value):
    value = max(0, int(value))
    previous = state["people"]
    state["people"] = value
    award_credits(previous)


def clean_player_name(value):
    if not isinstance(value, str):
        return None
    name = " ".join(value.strip().split())
    if not 1 <= len(name) <= 40:
        return None
    return name


def label_player_photo(frame, player_name):
    with Image.open(BytesIO(frame)) as source:
        image = source.convert("RGB")
    draw = ImageDraw.Draw(image)
    font_size = max(22, image.width // 18)
    try:
        font = ImageFont.truetype(PLAYER_NAME_FONT, font_size)
    except OSError:
        font = ImageFont.load_default()
    label = player_name
    padding = max(12, image.width // 50)
    bounds = draw.textbbox((0, 0), label, font=font)
    text_height = bounds[3] - bounds[1]
    box_top = image.height - text_height - padding * 2
    draw.rectangle(
        (0, box_top, image.width, image.height),
        fill=(5, 8, 18, 210),
    )
    draw.text(
        (padding, box_top + padding - bounds[1]),
        label,
        font=font,
        fill=(255, 255, 255),
        stroke_width=1,
        stroke_fill=(0, 0, 0),
    )
    output = BytesIO()
    image.save(output, format="JPEG", quality=92)
    return output.getvalue()


def count_people_in_photo(frame):
    if cv2 is None:
        return None

    image_array = np.frombuffer(frame, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    if image is None:
        return None

    height, width = image.shape[:2]
    scale = min(1.0, 960 / max(width, height))
    if scale < 1.0:
        image = cv2.resize(image, (int(width * scale), int(height * scale)))

    hog = cv2.HOGDescriptor()
    hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
    boxes, weights = hog.detectMultiScale(image, 0, (8, 8), (8, 8), 1.05, 2)

    return sum(1 for weight in weights if float(weight) >= 0.35)


def save_yolo_raw_photo(frame, player_name, captured_at, source, people_count):
    os.makedirs(YOLO_RAW_PHOTO_DIR, exist_ok=True)
    timestamp = captured_at.strftime("%Y%m%d-%H%M%S")
    safe_name = "".join(
        character.lower() if character.isalnum() else "-"
        for character in player_name
    ).strip("-")
    safe_name = safe_name or "player"
    base_name = f"{timestamp}-{safe_name}-{int(time.time() * 1000)}"
    image_path = os.path.join(YOLO_RAW_PHOTO_DIR, f"{base_name}.jpg")
    metadata_path = os.path.join(YOLO_RAW_PHOTO_DIR, f"{base_name}.json")

    with open(image_path, "wb") as photo_file:
        photo_file.write(frame)

    metadata = {
        "player_name": player_name,
        "captured_at": captured_at.isoformat(),
        "source": source,
        "ai_people_count": people_count,
        "label_class": "person",
        "label_status": "unlabeled",
        "notes": "Copy image into dataset/images split and create YOLO labels before training.",
    }
    with open(metadata_path, "w", encoding="utf-8") as metadata_file:
        json.dump(metadata, metadata_file, indent=2)

    return image_path


def arduino_device_available():
    for pattern in ARDUINO_DEVICE_PATTERNS:
        if glob.glob(pattern):
            return True
    return False


def grabber_power_level(percent):
    percent = max(
        MIN_GRABBER_POWER_PERCENT,
        min(MAX_GRABBER_POWER_PERCENT, int(percent)),
    )
    level = round(
        (percent - MIN_GRABBER_POWER_PERCENT) / GRABBER_POWER_STEP_PERCENT
    )
    return max(0, min(6, level))


def grabber_power_percent(value):
    level = grabber_power_level(value)
    return MIN_GRABBER_POWER_PERCENT + (level * GRABBER_POWER_STEP_PERCENT)


def ai_grabber_power_percent(people_count):
    people_count = max(0, int(people_count))
    if people_count <= 1:
        return 60
    if people_count <= 3:
        return 70
    if people_count == 4:
        return 80
    return 90


def refresh_effective_grabber_power():
    state["ai_grabber_power_percent"] = ai_grabber_power_percent(
        state["ai_people_count"]
    )
    if state["grabber_power_mode"] == "ai":
        state["grabber_power_percent"] = state["ai_grabber_power_percent"]
    else:
        state["grabber_power_percent"] = state["manual_grabber_power_percent"]
    return state["grabber_power_percent"]


def set_grabber_power_mode(value):
    if value not in GRABBER_POWER_MODES:
        raise ValueError("Grabber power mode must be manual or ai")
    state["grabber_power_mode"] = value
    refresh_effective_grabber_power()


def set_ai_people_count(value):
    state["ai_people_count"] = max(0, min(99, int(value)))
    refresh_effective_grabber_power()


def initialize_grabber_power_outputs(log_event=True):
    global grabber_power_outputs
    if len(GRABBER_POWER_GPIO_PINS) != 3:
        if log_event:
            add_event("Grabber power GPIO setting must contain 3 pins", "warning")
        grabber_power_outputs = []
        return False
    if OutputDevice is None:
        return False
    try:
        grabber_power_outputs = [
            OutputDevice(pin, active_high=True, initial_value=False)
            for pin in GRABBER_POWER_GPIO_PINS
        ]
        apply_grabber_power_outputs()
        if log_event:
            add_event(
                "Grabber power control ready on GPIO "
                + ",".join(str(pin) for pin in GRABBER_POWER_GPIO_PINS),
                "success",
            )
        return True
    except Exception as error:
        grabber_power_outputs = []
        if log_event:
            add_event(f"Grabber power GPIO unavailable: {error}", "warning")
        return False


def apply_grabber_power_outputs():
    if len(grabber_power_outputs) != 3:
        return False
    level = grabber_power_level(refresh_effective_grabber_power())
    for index, output in enumerate(grabber_power_outputs):
        if level & (1 << index):
            output.on()
        else:
            output.off()
    return True


def initialize_start_output(log_event=True):
    global start_output
    if OutputDevice is None:
        if log_event:
            add_event("GPIO library is unavailable", "warning")
        return False
    try:
        # Active-low: idle is 3.3 V and a play request briefly pulls the line low.
        start_output = OutputDevice(
            START_GPIO_PIN,
            active_high=False,
            initial_value=False,
        )
        if not grabber_power_outputs:
            initialize_grabber_power_outputs(log_event=log_event)
        state["arduino_connected"] = arduino_device_available()
        if log_event:
            if state["arduino_connected"]:
                add_event(
                    f"Arduino start control ready on GPIO {START_GPIO_PIN}",
                    "success",
                )
            else:
                add_event("Arduino USB device is disconnected", "warning")
        return True
    except Exception as error:
        start_output = None
        state["arduino_connected"] = False
        if log_event:
            add_event(f"GPIO start control unavailable: {error}", "warning")
        return False


def refresh_arduino_connection():
    if start_output is None and not initialize_start_output(log_event=False):
        return False
    if not grabber_power_outputs:
        initialize_grabber_power_outputs(log_event=False)
    state["arduino_connected"] = arduino_device_available()
    return state["arduino_connected"]


def play_duration_seconds(value):
    return max(MIN_PLAY_DURATION_SECONDS, min(MAX_PLAY_DURATION_SECONDS, int(value)))


def run_play_window(generation, duration):
    global play_generation
    time.sleep(READY_DURATION_SECONDS)
    with lock:
        if generation != play_generation or state["play_mode"] is None:
            return
        try:
            apply_grabber_power_outputs()
            if start_output is not None:
                start_output.on()
        except Exception as error:
            state["arduino_connected"] = False
            add_event(f"GPIO start signal failed: {error}", "warning")

    time.sleep(GRABBER_START_DURATION_SECONDS + duration)
    with lock:
        if generation != play_generation:
            return
        release_start_output()
        state["machine_status"] = "Ready"
        state["play_mode"] = None
        state["countdown_starts_at"] = None
        state["play_ends_at"] = None
        state["player_photo_ready"] = False
        add_event("Claw machine play window completed", "success")


def trigger_play(duration):
    global play_generation
    play_generation += 1
    generation = play_generation
    threading.Thread(
        target=run_play_window,
        args=(generation, duration),
        daemon=True,
    ).start()
    return state["arduino_connected"] and start_output is not None


def release_start_output():
    if start_output is None:
        return
    try:
        start_output.off()
    except Exception as error:
        state["arduino_connected"] = False
        add_event(f"GPIO stop signal failed: {error}", "warning")


def stop_play(message):
    global play_generation
    play_generation += 1
    release_start_output()
    state["machine_status"] = "Ready"
    state["play_mode"] = None
    state["countdown_starts_at"] = None
    state["play_ends_at"] = None
    add_event(message, "warning")


def camera_commands():
    if os.path.exists(USB_CAMERA_DEVICE):
        yield (
            "USB camera",
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "v4l2",
                "-input_format",
                "mjpeg",
                "-framerate",
                "15",
                "-video_size",
                "640x480",
                "-i",
                USB_CAMERA_DEVICE,
                "-an",
                "-c:v",
                "copy",
                "-f",
                "mjpeg",
                "-",
            ],
        )

    yield (
        "Pi camera",
        [
            "libcamera-vid",
            "--nopreview",
            "--timeout",
            "0",
            "--width",
            "640",
            "--height",
            "480",
            "--framerate",
            "15",
            "--codec",
            "mjpeg",
            "--flush",
            "--output",
            "-",
        ],
    )


def camera_worker():
    global camera_frame
    while True:
        for camera_name, command in camera_commands():
            process = None
            try:
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    bufsize=0,
                )
                buffer = bytearray()
                while True:
                    chunk = process.stdout.read(32768)
                    if not chunk:
                        break
                    buffer.extend(chunk)
                    while True:
                        start = buffer.find(b"\xff\xd8")
                        end = buffer.find(b"\xff\xd9", start + 2)
                        if start < 0 or end < 0:
                            if len(buffer) > 4 * 1024 * 1024:
                                del buffer[:-2]
                            break
                        frame = bytes(buffer[start : end + 2])
                        del buffer[: end + 2]
                        with camera_condition:
                            camera_frame = frame
                            camera_condition.notify_all()
                app.logger.warning("%s stream stopped", camera_name)
            except OSError as error:
                app.logger.error("%s stream failed: %s", camera_name, error)
            finally:
                if process and process.poll() is None:
                    process.terminate()
        time.sleep(2)


def camera_stream():
    previous_frame = None
    while True:
        with camera_condition:
            camera_condition.wait_for(
                lambda: camera_frame is not None and camera_frame is not previous_frame,
                timeout=5,
            )
            frame = camera_frame
        if frame is None or frame is previous_frame:
            continue
        previous_frame = frame
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n"
            b"Cache-Control: no-cache\r\n\r\n"
            + frame
            + b"\r\n"
        )


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/service-worker.js", methods=["GET"])
def service_worker():
    return send_from_directory(
        app.static_folder,
        "service-worker.js",
        mimetype="application/javascript",
        cache_timeout=0,
    )


@app.route("/camera-stream", methods=["GET"])
def live_camera():
    return Response(
        camera_stream(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
    )


@app.route("/api/status", methods=["GET"])
def status():
    with lock:
        refresh_arduino_connection()
        return jsonify(dashboard_state())


@app.route("/api/count", methods=["POST"])
def update_count():
    data = request.get_json(silent=True) or {}
    with lock:
        locked_response = reject_when_hacker_mode()
        if locked_response:
            return locked_response
        if "value" in data:
            set_people(data["value"])
        else:
            set_people(state["people"] + int(data.get("change", 1)))
        add_event(f"People count updated to {state['people']}")
        return jsonify(dashboard_state())


@app.route("/api/settings", methods=["POST"])
def settings():
    data = request.get_json(silent=True) or {}
    with lock:
        locked_response = reject_when_hacker_mode()
        if locked_response:
            return locked_response
        if "target" in data:
            state["target"] = max(1, min(999, int(data["target"])))
        if "play_duration" in data:
            state["play_duration"] = play_duration_seconds(data["play_duration"])
        if "grabber_power_percent" in data:
            state["manual_grabber_power_percent"] = grabber_power_percent(
                data["grabber_power_percent"]
            )
            refresh_effective_grabber_power()
            apply_grabber_power_outputs()
        if "grabber_power_mode" in data:
            try:
                set_grabber_power_mode(data["grabber_power_mode"])
            except ValueError as error:
                return jsonify({"ok": False, "error": str(error)}), 400
            apply_grabber_power_outputs()
        if "ai_people_count" in data:
            set_ai_people_count(data["ai_people_count"])
            apply_grabber_power_outputs()
        if "machine_enabled" in data:
            state["machine_enabled"] = bool(data["machine_enabled"])
            if not state["machine_enabled"] and state["play_mode"] is not None:
                stop_play("Machine disabled from dashboard")
        add_event("Settings updated")
        return jsonify(dashboard_state())


@app.route("/api/ai-count", methods=["POST"])
def ai_count():
    data = request.get_json(silent=True) or {}
    with lock:
        locked_response = reject_when_hacker_mode()
        if locked_response:
            return locked_response
        if "people" not in data:
            return jsonify({"ok": False, "error": "Missing people count"}), 400
        set_ai_people_count(data["people"])
        apply_grabber_power_outputs()
        add_event(
            "AI count updated: "
            f"{state['ai_people_count']} people -> "
            f"{state['ai_grabber_power_percent']}% grabber power"
        )
        return jsonify(dashboard_state(ok=True))


@app.route("/api/hacker", methods=["POST"])
def hacker():
    data = request.get_json(silent=True) or {}
    with lock:
        if state["hacker_mode"] and data.get("password") != HACKER_UNLOCK_PASSWORD:
            add_event("Incorrect hacker unlock password", "warning")
            return jsonify({"ok": False, "error": "Wrong password"}), 403
        state["hacker_mode"] = not state["hacker_mode"]
        if state["hacker_mode"] and state["play_mode"] is not None:
            stop_play("Machine stopped because hacker mode was enabled")
        add_event(
            "Hacker mode enabled" if state["hacker_mode"] else "Hacker mode disabled",
            "success" if state["hacker_mode"] else "warning",
        )
        return jsonify(dashboard_state(ok=True))


@app.route("/api/player-photo", methods=["POST"])
def player_photo():
    data = request.get_json(silent=True) or {}
    player_name = clean_player_name(data.get("name"))
    if player_name is None:
        return jsonify(
            {"ok": False, "error": "Enter a player name (1-40 characters)"}
        ), 400

    with lock:
        locked_response = reject_when_hacker_mode()
        if locked_response:
            return locked_response

    encoded = data.get("image", "")
    if not isinstance(encoded, str) or "," not in encoded:
        return jsonify({"ok": False, "error": "Invalid player photo"}), 400

    header, encoded = encoded.split(",", 1)
    if header != "data:image/jpeg;base64":
        return jsonify({"ok": False, "error": "Use a JPEG photo"}), 400

    try:
        image = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        return jsonify({"ok": False, "error": "Invalid player photo data"}), 400

    if not image or len(image) > 3 * 1024 * 1024:
        return jsonify({"ok": False, "error": "Photo must be smaller than 3 MB"}), 400

    os.makedirs(os.path.dirname(PLAYER_PHOTO_PATH), exist_ok=True)
    os.makedirs(PLAYER_HISTORY_DIR, exist_ok=True)
    captured_at = datetime.now()
    player_id = int(time.time() * 1000)
    history_filename = f"player-{player_id}.jpg"
    history_path = os.path.join(PLAYER_HISTORY_DIR, history_filename)
    temporary_path = f"{PLAYER_PHOTO_PATH}.browser"
    people_count = count_people_in_photo(image)
    try:
        save_yolo_raw_photo(image, player_name, captured_at, "browser", people_count)
        labeled_image = label_player_photo(image, player_name)
        with open(temporary_path, "wb") as photo_file:
            photo_file.write(labeled_image)
        os.replace(temporary_path, PLAYER_PHOTO_PATH)
        with open(history_path, "wb") as history_file:
            history_file.write(labeled_image)
    except Exception as error:
        app.logger.error("Browser player photo save failed: %s", error)
        return jsonify({"ok": False, "error": "Player photo could not be saved"}), 500

    with lock:
        locked_response = reject_when_hacker_mode()
        if locked_response:
            return locked_response
        state["player_photo_ready"] = True
        state["player_photo_version"] = player_id
        state["current_player_name"] = player_name
        if people_count is not None:
            set_ai_people_count(people_count)
            apply_grabber_power_outputs()
        state["players"].insert(
            0,
            {
                "id": player_id,
                "name": player_name,
                "photo": f"/static/images/players/{history_filename}",
                "time": captured_at.strftime("%H:%M:%S"),
                "status": (
                    f"Ready · AI {people_count} people"
                    if people_count is not None
                    else "Ready"
                ),
            },
        )
        del state["players"][12:]
        if people_count is not None:
            add_event(
                f"Player registered: {player_name}; AI counted {people_count} people",
                "success",
            )
        else:
            add_event(f"Player registered: {player_name}", "success")
        return jsonify(dashboard_state(ok=True))


@app.route("/api/capture-player", methods=["POST"])
def capture_player():
    data = request.get_json(silent=True) or {}
    player_name = clean_player_name(data.get("name"))
    if player_name is None:
        return jsonify(
            {"ok": False, "error": "Enter a player name (1-40 characters)"}
        ), 400

    with lock:
        locked_response = reject_when_hacker_mode()
        if locked_response:
            return locked_response

    with camera_condition:
        camera_condition.wait_for(lambda: camera_frame is not None, timeout=3)
        frame = camera_frame
    if frame is None:
        return jsonify({"ok": False, "error": "Pi camera is not ready"}), 503

    os.makedirs(os.path.dirname(PLAYER_PHOTO_PATH), exist_ok=True)
    os.makedirs(PLAYER_HISTORY_DIR, exist_ok=True)
    captured_at = datetime.now()
    player_id = int(time.time() * 1000)
    history_filename = f"player-{player_id}.jpg"
    history_path = os.path.join(PLAYER_HISTORY_DIR, history_filename)
    temporary_path = f"{PLAYER_PHOTO_PATH}.capture"
    people_count = count_people_in_photo(frame)
    try:
        save_yolo_raw_photo(frame, player_name, captured_at, "camera", people_count)
        labeled_frame = label_player_photo(frame, player_name)
        with open(temporary_path, "wb") as photo_file:
            photo_file.write(labeled_frame)
        os.replace(temporary_path, PLAYER_PHOTO_PATH)
        with open(history_path, "wb") as history_file:
            history_file.write(labeled_frame)
    except Exception as error:
        app.logger.error("Player photo save failed: %s", error)
        return jsonify({"ok": False, "error": "Player photo could not be saved"}), 500

    with lock:
        locked_response = reject_when_hacker_mode()
        if locked_response:
            return locked_response
        state["player_photo_ready"] = True
        state["player_photo_version"] = player_id
        state["current_player_name"] = player_name
        if people_count is not None:
            set_ai_people_count(people_count)
            apply_grabber_power_outputs()
        state["players"].insert(
            0,
            {
                "id": player_id,
                "name": player_name,
                "photo": f"/static/images/players/{history_filename}",
                "time": captured_at.strftime("%H:%M:%S"),
                "status": (
                    f"Ready · AI {people_count} people"
                    if people_count is not None
                    else "Ready"
                ),
            },
        )
        del state["players"][12:]
        if people_count is not None:
            add_event(
                f"Player registered: {player_name}; AI counted {people_count} people",
                "success",
            )
        else:
            add_event(f"Player registered: {player_name}", "success")
        return jsonify(dashboard_state(ok=True))


@app.route("/api/play", methods=["POST"])
def play():
    data = request.get_json(silent=True) or {}
    test_mode = bool(data.get("test"))

    with lock:
        locked_response = reject_when_hacker_mode()
        if locked_response:
            return locked_response
        refresh_arduino_connection()
        if not state["machine_enabled"]:
            return jsonify({"ok": False, "error": "Machine is disabled"}), 409
        if state["play_mode"] is not None:
            return jsonify({"ok": False, "error": "Machine is already running"}), 409
        if not state["player_photo_ready"]:
            return jsonify({"ok": False, "error": "Take a player photo before starting"}), 409
        if not test_mode and state["credits"] < 1:
            return jsonify({"ok": False, "error": "No play credit available"}), 409

        if state["players"]:
            state["players"][0]["status"] = "Tested" if test_mode else "Played"
        if not test_mode:
            state["credits"] -= 1
        state["player_photo_ready"] = False
        state["current_player_name"] = None
        if not test_mode:
            state["plays_today"] += 1
            state["last_play"] = datetime.now().strftime("%H:%M:%S")
        state["play_mode"] = "test" if test_mode else "play"
        play_duration = play_duration_seconds(state["play_duration"])
        state["play_duration"] = play_duration
        state["countdown_starts_at"] = (
            time.time() + READY_DURATION_SECONDS + GRABBER_START_DURATION_SECONDS
        )
        state["play_ends_at"] = (
            state["countdown_starts_at"] + play_duration
        )
        if state["arduino_connected"]:
            state["machine_status"] = "Getting ready"
        else:
            state["machine_status"] = "Test simulation" if test_mode else "Simulation"
        sent = trigger_play(play_duration)
        label = "Test play" if test_mode else "Play"
        add_event(
            f"{label} activated" + ("" if sent else " (simulation mode)"),
            "success",
        )
        return jsonify(dashboard_state(ok=True, start_signal_sent=sent))


@app.route("/api/stop", methods=["POST"])
def stop():
    with lock:
        locked_response = reject_when_hacker_mode()
        if locked_response:
            return locked_response
        if state["play_mode"] is None:
            return jsonify({"ok": False, "error": "Machine is not running"}), 409
        stop_play("Machine stopped from dashboard")
        return jsonify(dashboard_state(ok=True))


@app.route("/api/reset", methods=["POST"])
def reset():
    with lock:
        locked_response = reject_when_hacker_mode()
        if locked_response:
            return locked_response
        stop_play("Machine stopped for dashboard reset")
        state["people"] = 0
        state["credits"] = 0
        state["plays_today"] = 0
        state["last_play"] = None
        state["player_photo_ready"] = False
        state["hacker_mode"] = False
        state["player_photo_version"] = 0
        state["current_player_name"] = None
        state["players"].clear()
        if os.path.isdir(PLAYER_HISTORY_DIR):
            for filename in os.listdir(PLAYER_HISTORY_DIR):
                if filename.startswith("player-") and filename.endswith(".jpg"):
                    try:
                        os.remove(os.path.join(PLAYER_HISTORY_DIR, filename))
                    except OSError:
                        pass
        events.clear()
        add_event("Dashboard reset", "warning")
        return jsonify(dashboard_state())


if __name__ == "__main__":
    add_event("Dashboard started")
    initialize_start_output()
    threading.Thread(target=camera_worker, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
