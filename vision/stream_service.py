"""Independent Flask app and MJPEG stream endpoint for Vision Service."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from flask import Blueprint, Flask, Response

from services.logging.structured import configure_logging
from vision.camera_manager import CameraManager, load_camera_config
from vision.detection_cache import DetectionCache
from vision.detection_service import DetectionService, create_detection_blueprint
from vision.detector import YoloDetector, load_detector_config
from vision.frame_queue import FrameQueue
from vision.health import create_health_blueprint
from vision.snapshot_service import create_snapshot_blueprint

LOGGER = logging.getLogger("progress_claw.vision")


def configure_vision_logging() -> None:
    configure_logging()
    log_dir = os.getenv("CLAW_LOG_DIR", "logs")
    os.makedirs(log_dir, exist_ok=True)
    root = logging.getLogger()
    vision_log_path = os.path.join(log_dir, "vision.log")
    if any(
        getattr(handler, "_progress_claw_vision_log", False)
        for handler in root.handlers
    ):
        return
    handler = logging.FileHandler(vision_log_path)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    handler._progress_claw_vision_log = True
    handler.addFilter(lambda record: record.name.startswith("progress_claw.vision"))
    root.addHandler(handler)


def mjpeg_frames(frame_queue: FrameQueue, timeout: float = 5.0):
    last_sequence = None
    while True:
        frame = frame_queue.wait_for_next(last_sequence=last_sequence, timeout=timeout)
        if frame is None:
            continue
        last_sequence = frame.sequence
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n"
            b"Cache-Control: no-cache\r\n\r\n" + frame.data + b"\r\n"
        )


def create_stream_blueprint(frame_queue: FrameQueue) -> Blueprint:
    bp = Blueprint("vision_stream", __name__)

    @bp.route("/vision/stream", methods=["GET"])
    def stream() -> Response:
        return Response(
            mjpeg_frames(frame_queue),
            mimetype="multipart/x-mixed-replace; boundary=frame",
            headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
        )

    return bp


def create_app(
    camera_manager: Optional[CameraManager] = None,
    frame_queue: Optional[FrameQueue] = None,
    detection_cache: Optional[DetectionCache] = None,
    detection_service: Optional[DetectionService] = None,
    start_detection: bool = True,
    start_camera: bool = True,
) -> Flask:
    configure_vision_logging()
    queue = frame_queue or FrameQueue()
    manager = camera_manager or CameraManager(
        queue,
        config=load_camera_config(
            Path(os.getenv("CLAW_CAMERA_CONFIG", "config/camera.yaml"))
        ),
    )
    cache = detection_cache or DetectionCache()
    detector_service = detection_service or DetectionService(
        queue,
        detector=YoloDetector(
            config=load_detector_config(
                Path(os.getenv("CLAW_CAMERA_CONFIG", "config/camera.yaml"))
            ),
        ),
        cache=cache,
    )

    app = Flask(__name__)
    app.config["VISION_FRAME_QUEUE"] = queue
    app.config["VISION_CAMERA_MANAGER"] = manager
    app.config["VISION_DETECTION_CACHE"] = cache
    app.config["VISION_DETECTION_SERVICE"] = detector_service
    app.register_blueprint(create_health_blueprint(manager))
    app.register_blueprint(create_snapshot_blueprint(queue))
    app.register_blueprint(create_stream_blueprint(queue))
    app.register_blueprint(create_detection_blueprint(cache))

    if start_camera:
        manager.start()
    if start_detection:
        detector_service.start()

    @app.teardown_appcontext
    def _shutdown(_error=None):
        if os.getenv("CLAW_VISION_STOP_ON_TEARDOWN", "0") == "1":
            manager.stop()
            detector_service.stop()

    return app


if __name__ == "__main__":
    vision_app = create_app(start_camera=True)
    vision_app.run(
        host=os.getenv("VISION_HOST", "0.0.0.0"),
        port=int(os.getenv("VISION_PORT", "5100")),
        debug=False,
    )
