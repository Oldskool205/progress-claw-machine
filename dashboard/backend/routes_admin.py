"""Phase 5 protected administrator routes."""

import subprocess

from flask import Blueprint, jsonify, request

from dashboard.backend import admin_auth
from dashboard.backend import kiosk_control
from dashboard.backend.wifi_control import (
    WifiControlError,
    WifiValidationError,
    wifi_manager,
)
from dashboard.backend.system_power import power_executor
from controller.safety.validator import SafetyError
from dashboard.backend.dashboard_state import (
    add_event,
    dashboard_state,
    lock,
    state,
    stop_play,
)


bp = Blueprint("admin", __name__)


def _status_payload():
    payload = admin_auth.session_status()
    payload.update(
        maintenance_mode=state["maintenance_mode"],
        machine_running=state["play_mode"] is not None,
        power_mode=power_executor.mode,
        wifi_mode=wifi_manager.mode,
    )
    return payload


@bp.route("/api/admin/status", methods=["GET"])
def status():
    return jsonify(_status_payload())


@bp.route("/api/admin/login", methods=["POST"])
def login():
    if not admin_auth.is_configured():
        return jsonify({"ok": False, "error": "Admin authentication is not configured"}), 503

    data = request.get_json(silent=True) or {}
    pin = data.get("pin")
    if not isinstance(pin, str) or not pin.isdigit() or not 4 <= len(pin) <= 8:
        return jsonify({"ok": False, "error": "PIN must contain 4 to 8 digits"}), 400

    client_key = request.remote_addr or "unknown"
    accepted, retry_after = admin_auth.authenticate(pin, client_key)
    if retry_after:
        return jsonify(
            {"ok": False, "error": "Too many attempts", "retry_after": retry_after}
        ), 429
    if not accepted:
        return jsonify({"ok": False, "error": "Incorrect PIN"}), 401
    return jsonify(_status_payload())


@bp.route("/api/admin/logout", methods=["POST"])
def logout():
    admin_auth.logout()
    return jsonify(_status_payload())


@bp.route("/api/admin/stop-game", methods=["POST"])
@admin_auth.require_admin
def stop_current_game():
    data = request.get_json(silent=True) or {}
    if data.get("confirm") != "STOP_CURRENT_GAME":
        return jsonify({"ok": False, "error": "Stop confirmation is required"}), 400
    with lock:
        if state["play_mode"] is None:
            return jsonify({"ok": False, "error": "Machine is not running"}), 409
        try:
            stop_play("Current game stopped by administrator", source="admin")
        except SafetyError as error:
            return jsonify({"ok": False, "error": str(error)}), 409
        add_event("Admin action: current game stopped", "warning")
        return jsonify(dashboard_state(ok=True, admin=_status_payload()))


@bp.route("/api/admin/maintenance", methods=["POST"])
@admin_auth.require_admin
def maintenance():
    data = request.get_json(silent=True) or {}
    enabled = data.get("enabled")
    expected_confirmation = "ENTER_MAINTENANCE" if enabled is True else "EXIT_MAINTENANCE"
    if not isinstance(enabled, bool) or data.get("confirm") != expected_confirmation:
        return jsonify({"ok": False, "error": "Maintenance confirmation is required"}), 400

    with lock:
        if enabled and state["play_mode"] is not None:
            try:
                stop_play("Current game stopped for maintenance", source="admin")
            except SafetyError as error:
                return jsonify({"ok": False, "error": str(error)}), 409
        state["maintenance_mode"] = enabled
        state["machine_status"] = "Maintenance" if enabled else "Ready"
        action = "entered" if enabled else "exited"
        add_event(f"Admin action: maintenance mode {action}", "warning")
        return jsonify(dashboard_state(ok=True, admin=_status_payload()))


@bp.route("/api/admin/exit-kiosk", methods=["POST"])
@admin_auth.require_admin
def exit_kiosk():
    data = request.get_json(silent=True) or {}
    if data.get("confirm") != "EXIT_KIOSK":
        return jsonify({"ok": False, "error": "Kiosk exit confirmation is required"}), 400
    with lock:
        if state["play_mode"] is not None:
            return jsonify({"ok": False, "error": "Stop the current game before exiting kiosk"}), 409
        try:
            kiosk_control.request_exit()
        except OSError:
            return jsonify({"ok": False, "error": "Kiosk exit request could not be created"}), 503
        add_event("Admin action: kiosk exit requested", "warning")
        return jsonify({"ok": True, "message": "Kiosk exit requested"})


@bp.route("/api/admin/restart-kiosk", methods=["POST"])
@admin_auth.require_admin
def restart_kiosk():
    data = request.get_json(silent=True) or {}
    if data.get("confirm") != "RESTART_KIOSK":
        return jsonify({"ok": False, "error": "Kiosk restart confirmation is required"}), 400
    with lock:
        if state["play_mode"] is not None:
            return jsonify({"ok": False, "error": "Stop the current game before restarting kiosk"}), 409
        try:
            kiosk_control.request_restart()
        except OSError:
            return jsonify({"ok": False, "error": "Kiosk restart request could not be created"}), 503
        add_event("Admin action: kiosk restart requested", "warning")
        return jsonify({"ok": True, "message": "Kiosk restart requested"})


@bp.route("/api/admin/power/<action>", methods=["POST"])
@admin_auth.require_admin
def request_power_action(action):
    if action not in {"reboot", "poweroff"}:
        return jsonify({"ok": False, "error": "Unsupported system power action"}), 404
    data = request.get_json(silent=True) or {}
    expected_confirmation = "REBOOT_RASPBERRY_PI" if action == "reboot" else "SHUTDOWN_RASPBERRY_PI"
    if data.get("confirm") != expected_confirmation:
        return jsonify({"ok": False, "error": "System power confirmation is required"}), 400

    with lock:
        if state["play_mode"] is not None:
            return jsonify({"ok": False, "error": "Stop the current game first"}), 409
        if not state["maintenance_mode"]:
            return jsonify({"ok": False, "error": "Enter maintenance mode first"}), 409
        try:
            result = power_executor.request(action)
        except (OSError, subprocess.SubprocessError):
            return jsonify({"ok": False, "error": "System power helper failed"}), 503
        label = "reboot" if action == "reboot" else "shutdown"
        operation = "executed" if result["executed"] else "simulated"
        add_event(f"Admin action: Raspberry Pi {label} {operation}", "warning")
        message = (
            f"Raspberry Pi {label} command accepted"
            if result["executed"]
            else f"Raspberry Pi {label} simulation recorded; no system command executed"
        )
        return jsonify(
            {
                **result,
                "message": message,
            }
        )


@bp.route("/api/admin/wifi/status", methods=["GET"])
@admin_auth.require_admin
def wifi_status():
    try:
        return jsonify(wifi_manager.status())
    except WifiControlError:
        return jsonify({"ok": False, "error": "Wi-Fi status is unavailable"}), 503


@bp.route("/api/admin/wifi/networks", methods=["GET"])
@admin_auth.require_admin
def wifi_networks():
    try:
        return jsonify(wifi_manager.scan())
    except WifiControlError:
        return jsonify({"ok": False, "error": "Wi-Fi scan is unavailable"}), 503


@bp.route("/api/admin/wifi/connect", methods=["POST"])
@admin_auth.require_admin
def wifi_connect():
    data = request.get_json(silent=True) or {}
    if data.get("confirm") != "CONNECT_WIFI":
        return jsonify({"ok": False, "error": "Wi-Fi confirmation is required"}), 400

    with lock:
        if state["play_mode"] is not None:
            return jsonify({"ok": False, "error": "Stop the current game first"}), 409
        if not state["maintenance_mode"]:
            return jsonify({"ok": False, "error": "Enter maintenance mode first"}), 409
        try:
            result = wifi_manager.connect(data.get("ssid"), data.get("password"))
        except WifiValidationError as error:
            return jsonify({"ok": False, "error": str(error)}), 400
        except WifiControlError:
            return jsonify({"ok": False, "error": "Wi-Fi connection failed"}), 503
        operation = "completed" if result.get("executed") else "simulated"
        add_event(f"Admin action: Wi-Fi connection request {operation}", "warning")
        return jsonify(result)
