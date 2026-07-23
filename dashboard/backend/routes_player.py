"""Player photo capture routes."""

import base64
import binascii
import os
import time
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request

from controller.safety.validator import SafetyError
from dashboard.backend import dashboard_state as shared
from dashboard.backend.dashboard_state import *

bp = Blueprint("player", __name__)


@bp.route("/api/player-photo", methods=["POST"])
def player_photo():
    data = request.get_json(silent=True) or {}
    player_name = clean_player_name(data.get("name"))
    if player_name is None:
        return (
            jsonify({"ok": False, "error": "Enter a player name (1-40 characters)"}),
            400,
        )

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

    os.makedirs(os.path.dirname(shared.PLAYER_PHOTO_PATH), exist_ok=True)
    os.makedirs(shared.PLAYER_HISTORY_DIR, exist_ok=True)
    captured_at = datetime.now()
    player_id = int(time.time() * 1000)
    history_filename = f"player-{player_id}.jpg"
    history_path = os.path.join(shared.PLAYER_HISTORY_DIR, history_filename)
    temporary_path = f"{shared.PLAYER_PHOTO_PATH}.browser"
    people_count = count_people_in_photo(image)
    try:
        archive_yolo_raw_photo(image, captured_at, "browser", people_count)
        labeled_image = label_player_photo(image, player_name)
        with open(temporary_path, "wb") as photo_file:
            photo_file.write(labeled_image)
        os.replace(temporary_path, shared.PLAYER_PHOTO_PATH)
        with open(history_path, "wb") as history_file:
            history_file.write(labeled_image)
    except Exception as error:
        current_app.logger.error("Browser player photo save failed: %s", error)
        return jsonify({"ok": False, "error": "Player photo could not be saved"}), 500

    with lock:
        state["player_photo_ready"] = True
        state["player_photo_version"] = player_id
        state["current_player_name"] = player_name
        if people_count is not None:
            set_ai_people_count(people_count)
            try:
                apply_grabber_power_outputs()
            except SafetyError as error:
                return controller_error_response(error)
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


@bp.route("/api/capture-player", methods=["POST"])
def capture_player():
    data = request.get_json(silent=True) or {}
    player_name = clean_player_name(data.get("name"))
    if player_name is None:
        return (
            jsonify({"ok": False, "error": "Enter a player name (1-40 characters)"}),
            400,
        )

    with camera_condition:
        camera_condition.wait_for(lambda: shared.camera_frame is not None, timeout=3)
        frame = shared.camera_frame
    if frame is None:
        return jsonify({"ok": False, "error": "Pi camera is not ready"}), 503

    os.makedirs(os.path.dirname(shared.PLAYER_PHOTO_PATH), exist_ok=True)
    os.makedirs(shared.PLAYER_HISTORY_DIR, exist_ok=True)
    captured_at = datetime.now()
    player_id = int(time.time() * 1000)
    history_filename = f"player-{player_id}.jpg"
    history_path = os.path.join(shared.PLAYER_HISTORY_DIR, history_filename)
    temporary_path = f"{shared.PLAYER_PHOTO_PATH}.capture"
    people_count = count_people_in_photo(frame)
    try:
        archive_yolo_raw_photo(frame, captured_at, "camera", people_count)
        labeled_frame = label_player_photo(frame, player_name)
        with open(temporary_path, "wb") as photo_file:
            photo_file.write(labeled_frame)
        os.replace(temporary_path, shared.PLAYER_PHOTO_PATH)
        with open(history_path, "wb") as history_file:
            history_file.write(labeled_frame)
    except Exception as error:
        current_app.logger.error("Player photo save failed: %s", error)
        return jsonify({"ok": False, "error": "Player photo could not be saved"}), 500

    with lock:
        state["player_photo_ready"] = True
        state["player_photo_version"] = player_id
        state["current_player_name"] = player_name
        if people_count is not None:
            set_ai_people_count(people_count)
            try:
                apply_grabber_power_outputs()
            except SafetyError as error:
                return controller_error_response(error)
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
