"""Camera lifecycle management for Vision Service."""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional, Union

from vision.frame_queue import FrameQueue

LOGGER = logging.getLogger("progress_claw.vision")
DEFAULT_CONFIG_PATH = Path("config/camera.yaml")


@dataclass(frozen=True)
class CameraConfig:
    device_id: Union[int, str] = 0
    width: int = 1280
    height: int = 720
    fps: int = 30
    rotation: int = 0
    mirror: bool = False
    reconnect_delay_seconds: float = 2.0

    @property
    def resolution(self) -> str:
        return f"{self.width}x{self.height}"


class OpenCVCapture:
    def __init__(self, config: CameraConfig) -> None:
        try:
            import cv2
        except ImportError as error:
            raise RuntimeError(
                "opencv-python is required for camera capture"
            ) from error

        self._cv2 = cv2
        self._capture = cv2.VideoCapture(config.device_id)
        self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, config.width)
        self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, config.height)
        self._capture.set(cv2.CAP_PROP_FPS, config.fps)

    def is_opened(self) -> bool:
        return bool(self._capture.isOpened())

    def read(self) -> tuple[bool, Any]:
        return self._capture.read()

    def release(self) -> None:
        self._capture.release()


def _coerce_scalar(value: str) -> Any:
    lowered = value.strip().lower()
    if lowered in {"true", "yes", "on"}:
        return True
    if lowered in {"false", "no", "off"}:
        return False
    try:
        if "." in lowered:
            return float(lowered)
        return int(lowered)
    except ValueError:
        return value.strip().strip("\"'")


def _read_simple_yaml(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = {}
    if not path.exists():
        return data
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.split("#", 1)[0].strip()
        if not stripped or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        data[key.strip()] = _coerce_scalar(value)
    return data


def load_camera_config(
    path: Union[str, os.PathLike[str]] = DEFAULT_CONFIG_PATH,
) -> CameraConfig:
    data = _read_simple_yaml(Path(path))
    resolution = data.get("resolution")
    width = data.get("width")
    height = data.get("height")
    if isinstance(resolution, str) and "x" in resolution:
        left, right = resolution.lower().split("x", 1)
        width = int(left)
        height = int(right)

    return CameraConfig(
        device_id=data.get("device_id", 0),
        width=int(width or 1280),
        height=int(height or 720),
        fps=int(data.get("fps", 30)),
        rotation=int(data.get("rotation", 0)),
        mirror=bool(data.get("mirror", False)),
        reconnect_delay_seconds=float(data.get("reconnect_delay_seconds", 2.0)),
    )


class CameraManager:
    """Open, monitor, reconnect, and cleanly stop a camera capture loop."""

    def __init__(
        self,
        frame_queue: FrameQueue,
        config: Optional[CameraConfig] = None,
        capture_factory: Optional[Callable[[CameraConfig], Any]] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.frame_queue = frame_queue
        self.config = config or load_camera_config()
        self.capture_factory = capture_factory or OpenCVCapture
        self.logger = logger or LOGGER
        self.started_at = time.time()
        self._status = "disconnected"
        self._fps = 0.0
        self._last_frame_at: Optional[float] = None
        self._last_error: Optional[str] = None
        self._capture: Optional[Any] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
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
        self._release_capture()

    def health(self) -> dict[str, Any]:
        with self._lock:
            return {
                "camera": self._status,
                "fps": round(self._fps, 2),
                "resolution": self.config.resolution,
                "uptime": int(time.time() - self.started_at),
                "last_frame_at": self._last_frame_at,
                "last_error": self._last_error,
            }

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._open_capture()
                self._read_loop()
            except Exception as error:
                self._mark_disconnected(str(error))
                self.logger.exception(
                    "vision_camera_error",
                    extra={"event": "vision_camera_error", "error": str(error)},
                )
            finally:
                self._release_capture()

            if not self._stop_event.wait(self.config.reconnect_delay_seconds):
                self.logger.info(
                    "vision_camera_reconnect",
                    extra={"event": "vision_camera_reconnect"},
                )

    def _open_capture(self) -> None:
        self._capture = self.capture_factory(self.config)
        if not self._capture.is_opened():
            raise RuntimeError("Camera failed to open")
        with self._lock:
            previous = self._status
            self._status = "connected"
            self._last_error = None
        self.logger.info(
            "vision_camera_opened",
            extra={
                "event": "vision_camera_opened",
                "source": str(self.config.device_id),
            },
        )
        if previous == "disconnected":
            self.logger.info(
                "vision_camera_connected",
                extra={"event": "vision_camera_connected"},
            )

    def _read_loop(self) -> None:
        frame_count = 0
        window_started_at = time.monotonic()
        last_logged_fps: Optional[int] = None

        while not self._stop_event.is_set():
            ok, frame = self._capture.read()
            if not ok or frame is None:
                self._mark_disconnected("Camera read failed")
                self.logger.warning(
                    "vision_camera_disconnected",
                    extra={"event": "vision_camera_disconnected"},
                )
                return

            encoded = self._encode_frame(frame)
            captured_at = time.time()
            self.frame_queue.put(encoded, captured_at)
            frame_count += 1

            elapsed = time.monotonic() - window_started_at
            if elapsed >= 1.0:
                fps = frame_count / elapsed
                with self._lock:
                    self._fps = fps
                    self._last_frame_at = captured_at
                rounded_fps = int(round(fps))
                if rounded_fps != last_logged_fps:
                    self.logger.info(
                        "vision_camera_fps_changed",
                        extra={
                            "event": "vision_camera_fps_changed",
                            "response": {"fps": round(fps, 2)},
                        },
                    )
                    last_logged_fps = rounded_fps
                frame_count = 0
                window_started_at = time.monotonic()
            else:
                with self._lock:
                    self._last_frame_at = captured_at

    def _encode_frame(self, frame: Any) -> bytes:
        if isinstance(frame, bytes):
            return frame

        try:
            import cv2
        except ImportError as error:
            raise RuntimeError("opencv-python is required to encode frames") from error

        processed = frame
        if self.config.rotation:
            processed = self._rotate_frame(cv2, processed)
        if self.config.mirror:
            processed = cv2.flip(processed, 1)
        ok, encoded = cv2.imencode(".jpg", processed)
        if not ok:
            raise RuntimeError("Failed to encode camera frame")
        return encoded.tobytes()

    def _rotate_frame(self, cv2: Any, frame: Any) -> Any:
        rotation = self.config.rotation % 360
        if rotation == 90:
            return cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        if rotation == 180:
            return cv2.rotate(frame, cv2.ROTATE_180)
        if rotation == 270:
            return cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
        return frame

    def _mark_disconnected(self, error: Optional[str] = None) -> None:
        with self._lock:
            self._status = "disconnected"
            self._fps = 0.0
            self._last_error = error

    def _release_capture(self) -> None:
        capture = self._capture
        self._capture = None
        if capture is not None:
            try:
                capture.release()
            except Exception as error:
                self.logger.warning(
                    "vision_camera_release_error",
                    extra={"event": "vision_camera_release_error", "error": str(error)},
                )
