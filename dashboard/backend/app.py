#!/usr/bin/env python3
"""Local claw-machine dashboard application entry point."""

from __future__ import annotations

import os
import threading
from pathlib import Path

from flask import Flask, jsonify

from dashboard.backend import dashboard_state
from services.logging.structured import configure_logging


configure_logging()
_DASHBOARD_ROOT = Path(__file__).resolve().parents[1]
app = Flask(
    __name__,
    static_folder=str(_DASHBOARD_ROOT / "assets" / "static"),
    template_folder=str(_DASHBOARD_ROOT / "frontend" / "templates"),
)
dashboard_state.initialize_paths(app)
dashboard_state.set_app_logger(app.logger)

from dashboard.backend.routes_api import bp as api_bp
from dashboard.backend.routes_camera import bp as camera_bp
from dashboard.backend.routes_player import bp as player_bp
from dashboard.backend.routes_system import bp as system_bp

app.register_blueprint(system_bp)
app.register_blueprint(camera_bp)
app.register_blueprint(api_bp)
app.register_blueprint(player_bp)
runtime_controller = dashboard_state.runtime_controller


@app.errorhandler(ValueError)
def handle_value_error(error):
    app.logger.warning(
        "dashboard_invalid_request",
        extra={"event": "dashboard_invalid_request", "error": str(error)},
    )
    return jsonify({"ok": False, "error": str(error)}), 400


@app.errorhandler(Exception)
def handle_unexpected_error(error):
    app.logger.exception(
        "dashboard_unexpected_exception",
        extra={"event": "dashboard_unexpected_exception", "error": str(error)},
    )
    return jsonify({"ok": False, "error": "Unexpected server error"}), 500


def start_background_workers():
    dashboard_state.add_event("Dashboard started")
    dashboard_state.initialize_start_output()
    threading.Thread(target=dashboard_state.camera_worker, daemon=True).start()


if __name__ == "__main__":
    start_background_workers()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
