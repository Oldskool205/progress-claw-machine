"""Thread-safe latest detection result storage."""

from __future__ import annotations

import threading
from typing import Optional

from vision.detection_models import DetectedObject, DetectionResult


class DetectionCache:
    """Maintain only the latest detection result."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._latest = DetectionResult()

    def update(
        self,
        timestamp: float,
        frame_id: int,
        objects: list[DetectedObject],
    ) -> DetectionResult:
        result = DetectionResult(
            timestamp=float(timestamp),
            frame_id=int(frame_id),
            objects=list(objects),
        )
        with self._lock:
            self._latest = result
        return result

    def latest(self) -> DetectionResult:
        with self._lock:
            return self._latest

    def clear(self) -> None:
        with self._lock:
            self._latest = DetectionResult()

    def to_dict(self) -> dict[str, object]:
        return self.latest().to_dict()


_SHARED_DETECTION_CACHE = DetectionCache()


def shared_detection_cache() -> DetectionCache:
    return _SHARED_DETECTION_CACHE
