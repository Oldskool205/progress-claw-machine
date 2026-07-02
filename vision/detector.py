"""YOLOv8 detector wrapper for Vision Service frames."""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional, Union

from vision.camera_manager import _read_simple_yaml
from vision.detection_models import DetectedObject

LOGGER = logging.getLogger("progress_claw.vision")
DEFAULT_MODEL_PATH = "yolov8n.pt"
SUPPORTED_CLASSES = {"person", "teddy bear", "cell phone"}


@dataclass(frozen=True)
class DetectorConfig:
    model_path: str = DEFAULT_MODEL_PATH
    confidence_threshold: float = 0.25
    image_size: int = 640
    device: str = "cpu"
    inference_interval_seconds: float = 0.1


def load_detector_config(
    path: Union[str, os.PathLike[str]] = "config/camera.yaml",
) -> DetectorConfig:
    data = _read_simple_yaml(Path(path))
    return DetectorConfig(
        model_path=str(
            data.get(
                "yolo_model_path",
                data.get("model_path", DEFAULT_MODEL_PATH),
            )
        ),
        confidence_threshold=float(
            data.get(
                "yolo_confidence_threshold",
                data.get("confidence_threshold", 0.25),
            )
        ),
        image_size=int(data.get("yolo_image_size", data.get("image_size", 640))),
        device=str(data.get("yolo_device", data.get("device", "cpu"))),
        inference_interval_seconds=float(
            data.get(
                "yolo_inference_interval_seconds",
                data.get("inference_interval_seconds", 0.1),
            )
        ),
    )


class YoloDetector:
    """Lazy-loading YOLOv8 detector that never opens camera devices."""

    def __init__(
        self,
        config: Optional[DetectorConfig] = None,
        model_factory: Optional[Callable[[str], Any]] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.config = config or load_detector_config()
        self.model_factory = model_factory
        self.logger = logger or LOGGER
        self._model: Optional[Any] = None
        self._load_error: Optional[str] = None

    @property
    def loaded(self) -> bool:
        return self._model is not None

    def detect(
        self,
        frame_data: bytes,
        timestamp: Optional[float] = None,
    ) -> list[DetectedObject]:
        model = self._load_model()
        image = self._decode_frame(frame_data)
        started_at = time.monotonic()
        results = model.predict(
            image,
            conf=self.config.confidence_threshold,
            imgsz=self.config.image_size,
            device=self.config.device,
            verbose=False,
        )
        inference_time = time.monotonic() - started_at
        objects = self._objects_from_results(results, timestamp or time.time())
        fps = 1.0 / inference_time if inference_time > 0 else 0.0
        self.logger.info(
            "vision_yolo_inference",
            extra={
                "event": "vision_yolo_inference",
                "inference_time_ms": round(inference_time * 1000, 2),
                "fps": round(fps, 2),
                "detections": len(objects),
            },
        )
        return objects

    def _load_model(self) -> Any:
        if self._model is not None:
            return self._model
        if self._load_error:
            raise RuntimeError(self._load_error)

        model_path = self.config.model_path
        try:
            if self.model_factory is None:
                from ultralytics import YOLO

                self._model = YOLO(model_path)
            else:
                self._model = self.model_factory(model_path)
        except Exception as error:
            self._load_error = f"YOLO model load failed: {error}"
            self.logger.exception(
                "vision_yolo_model_load_failure",
                extra={
                    "event": "vision_yolo_model_load_failure",
                    "model_path": model_path,
                    "error": str(error),
                },
            )
            raise RuntimeError(self._load_error) from error

        self.logger.info(
            "vision_yolo_model_loaded",
            extra={"event": "vision_yolo_model_loaded", "model_path": model_path},
        )
        return self._model

    def _decode_frame(self, frame_data: bytes) -> Any:
        if not isinstance(frame_data, bytes):
            raise TypeError("Detection frame data must be bytes")

        try:
            import cv2
            import numpy as np
        except ImportError as error:
            raise RuntimeError(
                "opencv-python and numpy are required for detection"
            ) from error

        buffer = np.frombuffer(frame_data, dtype=np.uint8)
        image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
        if image is None:
            raise RuntimeError("Detection frame could not be decoded")
        return image

    def _objects_from_results(
        self,
        results: Any,
        timestamp: float,
    ) -> list[DetectedObject]:
        objects: list[DetectedObject] = []
        for result in results or []:
            names = getattr(result, "names", {}) or getattr(self._model, "names", {})
            boxes = getattr(result, "boxes", None)
            if boxes is None:
                continue

            for box in boxes:
                class_id = int(self._scalar(getattr(box, "cls", 0)))
                confidence = float(self._scalar(getattr(box, "conf", 0.0)))
                class_name = str(names.get(class_id, class_id))
                xyxy = getattr(box, "xyxy", [])
                bounding_box = [float(value) for value in self._sequence(xyxy)[:4]]
                objects.append(
                    DetectedObject(
                        class_name=class_name,
                        confidence=confidence,
                        bounding_box=bounding_box,
                        timestamp=timestamp,
                        tracking_id=None,
                    )
                )
        return objects

    def _scalar(self, value: Any) -> Any:
        if hasattr(value, "item"):
            return value.item()
        values = self._sequence(value)
        if values:
            first = values[0]
            return first.item() if hasattr(first, "item") else first
        return value

    def _sequence(self, value: Any) -> list[Any]:
        if hasattr(value, "tolist"):
            value = value.tolist()
        while (
            isinstance(value, list) and len(value) == 1 and isinstance(value[0], list)
        ):
            value = value[0]
        if isinstance(value, tuple):
            value = list(value)
        if isinstance(value, list):
            return value
        return [value]
