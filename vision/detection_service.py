"""Background YOLO detection service and Vision API endpoint."""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

from flask import Blueprint, jsonify

from vision.detection_cache import DetectionCache
from vision.detector import YoloDetector
from vision.frame_queue import FrameQueue

LOGGER = logging.getLogger("progress_claw.vision")


class DetectionService:
    """Consume the newest frame from FrameQueue and update DetectionCache."""

    def __init__(
        self,
        frame_queue: FrameQueue,
        detector: YoloDetector,
        cache: DetectionCache,
        inference_interval_seconds: Optional[float] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.frame_queue = frame_queue
        self.detector = detector
        self.cache = cache
        self.inference_interval_seconds = (
            detector.config.inference_interval_seconds
            if inference_interval_seconds is None
            else float(inference_interval_seconds)
        )
        self.logger = logger or LOGGER
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def start(self) -> None:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop_event.set()
        thread = self._thread
        if thread:
            thread.join(timeout=timeout)

    def _run(self) -> None:
        last_sequence: Optional[int] = None
        last_inference_at = 0.0

        while not self._stop_event.is_set():
            frame = self.frame_queue.wait_for_next(
                last_sequence=last_sequence,
                timeout=0.5,
            )
            if frame is None:
                continue

            latest = self.frame_queue.latest() or frame
            last_sequence = latest.sequence

            elapsed = time.monotonic() - last_inference_at
            if elapsed < self.inference_interval_seconds:
                if self._stop_event.wait(self.inference_interval_seconds - elapsed):
                    return
                latest = self.frame_queue.latest() or latest
                last_sequence = latest.sequence

            try:
                objects = self.detector.detect(latest.data, timestamp=latest.timestamp)
                self.cache.update(
                    timestamp=time.time(),
                    frame_id=latest.sequence,
                    objects=objects,
                )
                last_inference_at = time.monotonic()
            except Exception as error:
                last_inference_at = time.monotonic()
                self.logger.exception(
                    "vision_yolo_inference_error",
                    extra={
                        "event": "vision_yolo_inference_error",
                        "frame_id": latest.sequence,
                        "error": str(error),
                    },
                )


def create_detection_blueprint(cache: DetectionCache) -> Blueprint:
    bp = Blueprint("vision_detection", __name__)

    @bp.route("/vision/detections", methods=["GET"])
    def detections():
        return jsonify(cache.to_dict())

    return bp
