"""System and shell dashboard routes."""

import time

from flask import Blueprint, current_app, jsonify, render_template, send_from_directory

from dashboard.backend import dashboard_state

bp = Blueprint("system", __name__)


def health_payload():
    controller_status = dashboard_state.runtime_controller.status()
    return {
        "status": "ok",
        "controller": controller_status["status"],
        "arduino": (
            "mock"
            if controller_status["mock_arduino"]
            else (
                "connected"
                if controller_status["arduino_connected"]
                else "disconnected"
            )
        ),
        "camera": (
            "ready" if dashboard_state.camera_frame is not None else "unavailable"
        ),
        "uptime": round(time.time() - dashboard_state.STARTED_AT, 3),
    }


@bp.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@bp.route("/service-worker.js", methods=["GET"])
def service_worker():
    return send_from_directory(
        current_app.static_folder,
        "service-worker.js",
        mimetype="application/javascript",
        max_age=0,
    )


@bp.route("/api/health", methods=["GET"])
def health():
    return jsonify(health_payload())
