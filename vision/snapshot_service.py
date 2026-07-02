"""Snapshot endpoint helpers for Vision Service."""

from __future__ import annotations

from flask import Blueprint, Response

from vision.frame_queue import FrameQueue


def create_snapshot_blueprint(frame_queue: FrameQueue) -> Blueprint:
    bp = Blueprint("vision_snapshot", __name__)

    @bp.route("/vision/snapshot", methods=["GET"])
    def snapshot() -> Response:
        frame = frame_queue.latest()
        if frame is None:
            return Response("Camera frame unavailable\n", status=503)
        return Response(
            frame.data,
            mimetype="image/jpeg",
            headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
        )

    return bp
