"""Camera streaming routes."""

from flask import Blueprint, Response

from dashboard.backend.dashboard_state import camera_stream

bp = Blueprint("camera", __name__)


@bp.route("/camera-stream", methods=["GET"])
def live_camera():
    return Response(
        camera_stream(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
    )
