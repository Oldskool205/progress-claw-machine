"""Controller-backed dashboard API routes."""

from flask import Blueprint, jsonify, request

from controller.models import (
    ClawPowerCommand,
    EmergencyStopCommand,
    PlayStartCommand,
    PlayStopCommand,
)
from controller.safety.validator import SafetyError
from dashboard.backend.dashboard_state import *

bp = Blueprint("api", __name__)


@bp.route("/api/status", methods=["GET"])
def status():
    with lock:
        refresh_arduino_connection()
        return jsonify(dashboard_state())


@bp.route("/api/play/start", methods=["POST"])
def api_play_start():
    data = request.get_json(silent=True) or {}
    duration = play_duration_seconds(
        data.get("duration_seconds", state["play_duration"])
    )
    command = PlayStartCommand(
        duration_seconds=duration,
        source=data.get("source", "dashboard"),
        test_mode=bool(data.get("test", False)),
    )
    with lock:
        try:
            result = runtime_controller.start_play(command)
        except SafetyError as error:
            return controller_error_response(error)
        state["play_mode"] = "test" if command.test_mode else "play"
        state["play_duration"] = duration
        state["countdown_starts_at"] = time.time()
        state["play_ends_at"] = result["play_ends_at"]
        state["machine_status"] = "Running"
        add_event("Controller play started", "success")
        return jsonify(dashboard_state(ok=True))


@bp.route("/api/play/stop", methods=["POST"])
def api_play_stop():
    data = request.get_json(silent=True) or {}
    with lock:
        try:
            runtime_controller.stop_play(
                PlayStopCommand(
                    source=data.get("source", "dashboard"),
                    reason=data.get("reason", "operator_stop"),
                )
            )
        except SafetyError as error:
            return controller_error_response(error)
        state["play_mode"] = None
        state["countdown_starts_at"] = None
        state["play_ends_at"] = None
        state["machine_status"] = "Ready"
        add_event("Controller play stopped", "warning")
        return jsonify(dashboard_state(ok=True))


@bp.route("/api/claw/power", methods=["POST"])
def api_claw_power():
    data = request.get_json(silent=True) or {}
    if "power_percent" not in data:
        return jsonify({"ok": False, "error": "Missing power_percent"}), 400
    with lock:
        try:
            result = runtime_controller.set_claw_power(
                ClawPowerCommand(
                    power_percent=int(data["power_percent"]),
                    source=data.get("source", "dashboard"),
                )
            )
        except (SafetyError, ValueError) as error:
            return controller_error_response(error)
        state["manual_grabber_power_percent"] = result["claw_power_percent"]
        state["grabber_power_percent"] = result["claw_power_percent"]
        add_event(f"Claw power set to {result['claw_power_percent']}%")
        return jsonify(dashboard_state(ok=True))


@bp.route("/api/emergency-stop", methods=["POST"])
def api_emergency_stop():
    data = request.get_json(silent=True) or {}
    with lock:
        runtime_controller.emergency_stop(
            EmergencyStopCommand(
                source=data.get("source", "dashboard"),
                reason=data.get("reason", "emergency_stop"),
            )
        )
        state["play_mode"] = None
        state["countdown_starts_at"] = None
        state["play_ends_at"] = None
        state["machine_status"] = "Emergency stopped"
        add_event("Emergency stop activated", "warning")
        return jsonify(dashboard_state(ok=True))


@bp.route("/api/count", methods=["POST"])
def update_count():
    data = request.get_json(silent=True) or {}
    with lock:
        if "value" in data:
            set_people(data["value"])
        else:
            set_people(state["people"] + int(data.get("change", 1)))
        add_event(f"People count updated to {state['people']}")
        return jsonify(dashboard_state())


@bp.route("/api/settings", methods=["POST"])
def settings():
    data = request.get_json(silent=True) or {}
    with lock:
        if "target" in data:
            state["target"] = max(1, min(999, int(data["target"])))
        if "play_duration" in data:
            state["play_duration"] = play_duration_seconds(data["play_duration"])
        if "grabber_power_percent" in data:
            state["manual_grabber_power_percent"] = grabber_power_percent(
                data["grabber_power_percent"]
            )
            refresh_effective_grabber_power()
            try:
                apply_grabber_power_outputs()
            except SafetyError as error:
                return controller_error_response(error)
        if "grabber_power_mode" in data:
            try:
                set_grabber_power_mode(data["grabber_power_mode"])
            except ValueError as error:
                return jsonify({"ok": False, "error": str(error)}), 400
            try:
                apply_grabber_power_outputs()
            except SafetyError as error:
                return controller_error_response(error)
        if "ai_people_count" in data:
            set_ai_people_count(data["ai_people_count"])
            try:
                apply_grabber_power_outputs()
            except SafetyError as error:
                return controller_error_response(error)
        if "machine_enabled" in data:
            state["machine_enabled"] = bool(data["machine_enabled"])
            if not state["machine_enabled"] and state["play_mode"] is not None:
                stop_play("Machine disabled from dashboard")
        add_event("Settings updated")
        return jsonify(dashboard_state())


@bp.route("/api/ai-count", methods=["POST"])
def ai_count():
    data = request.get_json(silent=True) or {}
    with lock:
        if "people" not in data:
            return jsonify({"ok": False, "error": "Missing people count"}), 400
        set_ai_people_count(data["people"])
        try:
            apply_grabber_power_outputs()
        except SafetyError as error:
            return controller_error_response(error)
        add_event(
            "AI count updated: "
            f"{state['ai_people_count']} people -> "
            f"{state['ai_grabber_power_percent']}% grabber power"
        )
        return jsonify(dashboard_state(ok=True))


@bp.route("/api/play", methods=["POST"])
def play():
    data = request.get_json(silent=True) or {}
    test_mode = bool(data.get("test"))

    with lock:
        refresh_arduino_connection()
        if not state["machine_enabled"]:
            return jsonify({"ok": False, "error": "Machine is disabled"}), 409
        if state["play_mode"] is not None:
            return jsonify({"ok": False, "error": "Machine is already running"}), 409
        if not state["player_photo_ready"]:
            return (
                jsonify({"ok": False, "error": "Take a player photo before starting"}),
                409,
            )
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
        state["play_ends_at"] = state["countdown_starts_at"] + play_duration
        if state["arduino_connected"]:
            state["machine_status"] = "Getting ready"
        else:
            state["machine_status"] = "Test simulation" if test_mode else "Simulation"
        try:
            sent = trigger_play(play_duration)
        except SafetyError as error:
            state["play_mode"] = None
            state["countdown_starts_at"] = None
            state["play_ends_at"] = None
            return controller_error_response(error)
        label = "Test play" if test_mode else "Play"
        add_event(
            f"{label} activated" + ("" if sent else " (simulation mode)"),
            "success",
        )
        return jsonify(dashboard_state(ok=True, start_signal_sent=sent))


@bp.route("/api/stop", methods=["POST"])
def stop():
    with lock:
        if state["play_mode"] is None:
            return jsonify({"ok": False, "error": "Machine is not running"}), 409
        try:
            stop_play("Machine stopped from dashboard")
        except SafetyError as error:
            return controller_error_response(error)
        return jsonify(dashboard_state(ok=True))


@bp.route("/api/reset", methods=["POST"])
def reset():
    with lock:
        stop_play("Machine stopped for dashboard reset")
        state["people"] = 0
        state["credits"] = 0
        state["plays_today"] = 0
        state["last_play"] = None
        state["player_photo_ready"] = False
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
