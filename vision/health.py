"""Health endpoint helpers for Vision Service."""

from __future__ import annotations

from flask import Blueprint, jsonify

from vision.camera_manager import CameraManager


def create_health_blueprint(camera_manager: CameraManager) -> Blueprint:
    bp = Blueprint("vision_health", __name__)

    @bp.route("/vision/health", methods=["GET"])
    def health():
        return jsonify(camera_manager.health())

    return bp
