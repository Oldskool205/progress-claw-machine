"""Shared dashboard runtime state and helpers."""

from __future__ import annotations

import base64
import binascii
import json
import logging
import os
import subprocess
import threading
import time
from collections import deque
from datetime import datetime
from io import BytesIO

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from flask import jsonify

from controller import RuntimeController
from controller.models import ClawPowerCommand, PlayStartCommand, PlayStopCommand
from controller.safety.validator import SafetyError

try:
    import cv2
except ImportError:
    cv2 = None

LOGGER = logging.getLogger("progress_claw.dashboard")
APP_LOGGER = LOGGER
STARTED_AT = time.time()


def initialize_paths(app):
    global PLAYER_PHOTO_PATH, PLAYER_HISTORY_DIR
    PLAYER_PHOTO_PATH = os.path.join(app.static_folder, "images", "current-player.jpg")
    PLAYER_HISTORY_DIR = os.path.join(app.static_folder, "images", "players")


def set_app_logger(logger):
    global APP_LOGGER
    APP_LOGGER = logger


lock = threading.Lock()
runtime_controller = RuntimeController.from_env()
PLAYER_PHOTO_PATH = None
PLAYER_HISTORY_DIR = None
YOLO_RAW_PHOTO_DIR = os.getenv(
    "CLAW_YOLO_RAW_PHOTO_DIR",
    "/home/araya/Projects/Progress-Claw-OS/ai/training/yolo_people/raw_photos",
)
YOLO_RAW_PHOTO_ARCHIVE_ENABLED = os.getenv(
    "CLAW_YOLO_ARCHIVE_PLAYER_PHOTOS", "0"
).strip().lower() in {"1", "true", "yes", "on"}

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
GRABBER_START_DURATION_SECONDS = int(os.getenv("CLAW_GRABBER_START_SECONDS", "1"))
USB_CAMERA_DEVICE = os.getenv("CLAW_USB_CAMERA_DEVICE", "/dev/video0")
PLAYER_NAME_FONT = "/usr/share/fonts/truetype/lato/Lato-Heavy.ttf"

state = {
    "people": 0,
    "target": 10,
    "credits": 0,
    "plays_today": 0,
    "machine_enabled": True,
    "maintenance_mode": False,
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
    controller_status = runtime_controller.status()
    state["arduino_connected"] = controller_status["arduino_connected"]
    state["machine_enabled"] = controller_status["machine_enabled"]
    state["grabber_power_percent"] = controller_status["claw_power_percent"]
    if state["play_mode"] is not None and not controller_status["running"]:
        state["play_mode"] = None
        state["countdown_starts_at"] = None
        state["play_ends_at"] = None
        state["player_photo_ready"] = False
        add_event("Claw machine play window completed", "success")
    if controller_status["emergency_stopped"]:
        state["machine_status"] = "Emergency stopped"
    elif controller_status["running"]:
        state["machine_status"] = "Running"
    elif controller_status["status"] == "fault":
        state["machine_status"] = "Fault"
    elif state["maintenance_mode"]:
        state["machine_status"] = "Maintenance"
    elif state["play_mode"] is None:
        state["machine_status"] = "Ready"
    return {
        **state,
        "events": list(events),
        "controller": controller_status,
        **extra,
    }


def controller_error_response(error, status_code=409):
    add_event(str(error), "warning")
    return jsonify(dashboard_state(ok=False, error=str(error))), status_code


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


def save_yolo_raw_photo(frame, captured_at, source, people_count):
    os.makedirs(YOLO_RAW_PHOTO_DIR, exist_ok=True)
    timestamp = captured_at.strftime("%Y%m%d-%H%M%S")
    base_name = f"{timestamp}-capture-{int(time.time() * 1000)}"
    image_path = os.path.join(YOLO_RAW_PHOTO_DIR, f"{base_name}.jpg")
    metadata_path = os.path.join(YOLO_RAW_PHOTO_DIR, f"{base_name}.json")

    with open(image_path, "wb") as photo_file:
        photo_file.write(frame)

    metadata = {
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


def archive_yolo_raw_photo(frame, captured_at, source, people_count):
    """Archive an anonymized training capture only after explicit local opt-in."""

    if not YOLO_RAW_PHOTO_ARCHIVE_ENABLED:
        return None
    return save_yolo_raw_photo(frame, captured_at, source, people_count)


def grabber_power_level(percent):
    percent = max(
        MIN_GRABBER_POWER_PERCENT,
        min(MAX_GRABBER_POWER_PERCENT, int(percent)),
    )
    level = round((percent - MIN_GRABBER_POWER_PERCENT) / GRABBER_POWER_STEP_PERCENT)
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
    if log_event:
        add_event("Grabber power is managed by controller runtime", "info")
    return True


def apply_grabber_power_outputs():
    percent = refresh_effective_grabber_power()
    runtime_controller.set_claw_power(ClawPowerCommand(power_percent=percent))
    return True


def initialize_start_output(log_event=True):
    controller_status = runtime_controller.status()
    state["arduino_connected"] = controller_status["arduino_connected"]
    if log_event:
        add_event("Arduino access is managed by controller runtime", "info")
    return True


def refresh_arduino_connection():
    controller_status = runtime_controller.status()
    state["arduino_connected"] = controller_status["arduino_connected"]
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


def trigger_play(duration, test_mode=False):
    return runtime_controller.start_play(
        PlayStartCommand(
            duration_seconds=duration,
            source="dashboard",
            test_mode=test_mode,
            startup_seconds=READY_DURATION_SECONDS + GRABBER_START_DURATION_SECONDS,
        )
    )


def release_start_output():
    if runtime_controller.status()["running"]:
        runtime_controller.stop_play(PlayStopCommand(source="dashboard"))


def stop_play(message, source="dashboard"):
    global play_generation
    play_generation += 1
    if runtime_controller.status()["running"]:
        runtime_controller.stop_play(
            PlayStopCommand(source=source, reason=message)
        )
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
                APP_LOGGER.warning("%s stream stopped", camera_name)
            except OSError as error:
                APP_LOGGER.error("%s stream failed: %s", camera_name, error)
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
            b"Cache-Control: no-cache\r\n\r\n" + frame + b"\r\n"
        )
