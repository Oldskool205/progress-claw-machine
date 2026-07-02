"""Rule-based Recommendation Engine."""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

from game.state_cache import GameStateCache
from game.state_models import GameState
from recommendation.cache import RecommendationCache
from recommendation.models import Recommendation, RecommendationType
from recommendation.rules import (
    disconnected_arduino,
    is_system_degraded,
    is_vision_unavailable,
    recommendation_reason,
)
from vision.detection_cache import DetectionCache

LOGGER = logging.getLogger("progress_claw.recommendation")


@dataclass(frozen=True)
class RecommendationConfig:
    player_ready_seconds: float = 3.0
    idle_demo_timeout: float = 30.0
    camera_timeout: float = 5.0
    arduino_timeout: float = 5.0
    recommendation_interval_ms: int = 500


def _coerce_scalar(value: str) -> Any:
    lowered = value.strip().lower()
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
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.split("#", 1)[0].strip()
        if not stripped or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        data[key.strip()] = _coerce_scalar(value)
    return data


def load_recommendation_config(
    path: str | os.PathLike[str] = "config/recommendation.yaml",
) -> RecommendationConfig:
    data = _read_simple_yaml(Path(path))
    return RecommendationConfig(
        player_ready_seconds=float(data.get("player_ready_seconds", 3.0)),
        idle_demo_timeout=float(data.get("idle_demo_timeout", 30.0)),
        camera_timeout=float(data.get("camera_timeout", 5.0)),
        arduino_timeout=float(data.get("arduino_timeout", 5.0)),
        recommendation_interval_ms=int(data.get("recommendation_interval_ms", 500)),
    )


def configure_recommendation_logging() -> None:
    log_dir = os.getenv("CLAW_LOG_DIR", "logs")
    os.makedirs(log_dir, exist_ok=True)
    root = logging.getLogger()
    if any(
        getattr(handler, "_progress_claw_recommendation_log", False)
        for handler in root.handlers
    ):
        return
    handler = logging.FileHandler(os.path.join(log_dir, "recommendation.log"))
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    handler.addFilter(
        lambda record: record.name.startswith("progress_claw.recommendation")
    )
    handler._progress_claw_recommendation_log = True
    root.addHandler(handler)


class RecommendationEngine:
    """Generate informational gameplay recommendations from read-only inputs."""

    def __init__(
        self,
        game_state_cache: GameStateCache,
        detection_cache: DetectionCache,
        runtime_status_provider: Callable[[], dict[str, Any]],
        recommendation_cache: Optional[RecommendationCache] = None,
        config: Optional[RecommendationConfig] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        configure_recommendation_logging()
        self.game_state_cache = game_state_cache
        self.detection_cache = detection_cache
        self.runtime_status_provider = runtime_status_provider
        self.recommendation_cache = recommendation_cache or RecommendationCache()
        self.config = config or load_recommendation_config()
        self.logger = logger or LOGGER
        self._player_present_since: Optional[float] = None
        self._idle_since: Optional[float] = None
        self._arduino_disconnected_since: Optional[float] = None

    def evaluate(self) -> dict[str, Any]:
        try:
            game_state = self.game_state_cache.latest().to_dict()
            detection = self.detection_cache.latest()
            runtime_status = self.runtime_status_provider()
            recommendation = self._select_recommendation(
                game_state=game_state,
                detection=detection,
                runtime_status=runtime_status,
                now=time.time(),
            )
            previous = self.recommendation_cache.latest().recommendation
            self.recommendation_cache.update(recommendation)
            if recommendation.recommendation != previous:
                self.logger.info(
                    "recommendation_generated",
                    extra={
                        "event": "recommendation_generated",
                        "source": recommendation.source,
                        "response": recommendation.to_dict(),
                    },
                )
            return recommendation.to_dict()
        except Exception as error:
            self.logger.exception(
                "recommendation_error",
                extra={"event": "recommendation_error", "error": str(error)},
            )
            recommendation = Recommendation(
                recommendation=RecommendationType.SYSTEM_DEGRADED,
                confidence=1.0,
                reason=f"Recommendation error: {error}",
                details={"error": str(error)},
            )
            return self.recommendation_cache.update(recommendation).to_dict()

    def history(self) -> dict[str, Any]:
        return self.recommendation_cache.history_dict()

    def _select_recommendation(
        self,
        *,
        game_state: dict[str, Any],
        detection: Any,
        runtime_status: dict[str, Any],
        now: float,
    ) -> Recommendation:
        state = game_state.get("state")
        self._track_durations(state, runtime_status, now)

        if is_system_degraded(game_state, runtime_status):
            return self._build(
                RecommendationType.SYSTEM_DEGRADED,
                confidence=0.95,
                details={"game_state": state, "runtime_status": runtime_status},
            )

        if is_vision_unavailable(game_state, detection):
            return self._build(
                RecommendationType.CHECK_CAMERA,
                confidence=0.9,
                details={"game_state": state},
            )

        if self._arduino_disconnected_since is not None:
            elapsed = now - self._arduino_disconnected_since
            if elapsed >= self.config.arduino_timeout:
                return self._build(
                    RecommendationType.CHECK_ARDUINO,
                    confidence=0.9,
                    details={"disconnected_seconds": round(elapsed, 3)},
                )

        if state == GameState.PLAYER_PRESENT.value:
            present_for = now - (self._player_present_since or now)
            if present_for >= self.config.player_ready_seconds:
                return self._build(
                    RecommendationType.READY_TO_START,
                    confidence=0.92,
                    details={"player_present_seconds": round(present_for, 3)},
                )
            return self._build(
                RecommendationType.WAIT_FOR_PLAYER,
                confidence=0.7,
                details={"player_present_seconds": round(present_for, 3)},
            )

        if state == GameState.IDLE.value:
            idle_for = now - (self._idle_since or now)
            if idle_for >= self.config.idle_demo_timeout:
                return self._build(
                    RecommendationType.START_DEMO_MODE,
                    confidence=0.8,
                    details={"idle_seconds": round(idle_for, 3)},
                )
            return self._build(
                RecommendationType.WAIT_FOR_PLAYER,
                confidence=0.75,
                details={"idle_seconds": round(idle_for, 3)},
            )

        if state == GameState.PLAYING.value:
            return self._build(
                RecommendationType.NO_ACTION,
                confidence=0.8,
                details={"game_state": state},
            )

        return self._build(
            RecommendationType.NO_ACTION,
            confidence=0.6,
            details={"game_state": state},
        )

    def _track_durations(
        self,
        state: str,
        runtime_status: dict[str, Any],
        now: float,
    ) -> None:
        if state == GameState.PLAYER_PRESENT.value:
            if self._player_present_since is None:
                self._player_present_since = now
        else:
            self._player_present_since = None

        if state == GameState.IDLE.value:
            if self._idle_since is None:
                self._idle_since = now
        else:
            self._idle_since = None

        if disconnected_arduino(runtime_status):
            if self._arduino_disconnected_since is None:
                self._arduino_disconnected_since = now
        else:
            self._arduino_disconnected_since = None

    def _build(
        self,
        recommendation_type: RecommendationType,
        *,
        confidence: float,
        details: Optional[dict[str, Any]] = None,
    ) -> Recommendation:
        return Recommendation(
            recommendation=recommendation_type,
            confidence=confidence,
            reason=recommendation_reason(recommendation_type),
            details=details or {},
        )
