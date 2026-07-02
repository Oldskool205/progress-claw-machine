"""Rule-based Game State Engine."""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

from game.rules import (
    PrizeZone,
    contains_grab_event,
    count_players,
    object_confidence,
    prize_objects,
    runtime_state,
)
from game.state_cache import GameStateCache
from game.state_models import GameState
from vision.detection_cache import DetectionCache

LOGGER = logging.getLogger("progress_claw.game_state")


@dataclass(frozen=True)
class GameStateConfig:
    player_presence_threshold: int = 1
    idle_timeout_seconds: float = 5.0
    detection_confidence_threshold: float = 0.5
    prize_zone: PrizeZone = PrizeZone()
    state_update_interval_ms: int = 250
    timeout_seconds: float = 60.0


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


def _read_game_yaml(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current_section: Optional[str] = None
    if not path.exists():
        return data
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        stripped = raw_line.split("#", 1)[0].rstrip()
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        if not raw_line.startswith(" ") and not raw_line.startswith("\t"):
            current_section = None
            if value.strip():
                data[key.strip()] = _coerce_scalar(value)
            else:
                current_section = key.strip()
                data[current_section] = {}
            continue
        if current_section:
            data[current_section][key.strip()] = _coerce_scalar(value)
    return data


def load_game_state_config(
    path: str | os.PathLike[str] = "config/game_state.yaml",
) -> GameStateConfig:
    data = _read_game_yaml(Path(path))
    zone_data = data.get("prize_zone", {})
    return GameStateConfig(
        player_presence_threshold=int(data.get("player_presence_threshold", 1)),
        idle_timeout_seconds=float(data.get("idle_timeout_seconds", 5.0)),
        detection_confidence_threshold=float(
            data.get("detection_confidence_threshold", 0.5)
        ),
        prize_zone=PrizeZone(
            x_min=float(zone_data.get("x_min", 0.0)),
            y_min=float(zone_data.get("y_min", 0.0)),
            x_max=float(zone_data.get("x_max", 10000.0)),
            y_max=float(zone_data.get("y_max", 10000.0)),
        ),
        state_update_interval_ms=int(data.get("state_update_interval_ms", 250)),
        timeout_seconds=float(data.get("timeout_seconds", 60.0)),
    )


def configure_game_state_logging() -> None:
    log_dir = os.getenv("CLAW_LOG_DIR", "logs")
    os.makedirs(log_dir, exist_ok=True)
    root = logging.getLogger()
    if any(
        getattr(handler, "_progress_claw_game_state_log", False)
        for handler in root.handlers
    ):
        return
    handler = logging.FileHandler(os.path.join(log_dir, "game_state.log"))
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    handler.addFilter(lambda record: record.name.startswith("progress_claw.game_state"))
    handler._progress_claw_game_state_log = True
    root.addHandler(handler)


class GameStateEngine:
    """Convert detection results and runtime status into high-level game state."""

    def __init__(
        self,
        detection_cache: DetectionCache,
        runtime_status_provider: Callable[[], dict[str, Any]],
        state_cache: Optional[GameStateCache] = None,
        config: Optional[GameStateConfig] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        configure_game_state_logging()
        self.detection_cache = detection_cache
        self.runtime_status_provider = runtime_status_provider
        self.state_cache = state_cache or GameStateCache()
        self.config = config or load_game_state_config()
        self.logger = logger or LOGGER
        self._last_person_seen_at: Optional[float] = None
        self._last_player_count = 0

    def evaluate(self, runtime_events: Optional[list[Any]] = None) -> dict[str, Any]:
        runtime_events = runtime_events or []
        try:
            runtime_status = self.runtime_status_provider()
            detection = self.detection_cache.latest()
            objects = list(detection.objects)
            now = time.time()
            state, confidence, source, details = self._select_state(
                runtime_status=runtime_status,
                detection_timestamp=detection.timestamp,
                frame_id=detection.frame_id,
                objects=objects,
                now=now,
                runtime_events=runtime_events,
            )
            previous_state = self.state_cache.latest().state
            event = self.state_cache.transition(
                state,
                confidence=confidence,
                source=source,
                details=details,
            )
            if event.state != previous_state:
                self.logger.info(
                    "game_state_transition",
                    extra={
                        "event": "game_state_transition",
                        "source": source,
                        "response": event.to_dict(),
                    },
                )
            return event.to_dict()
        except Exception as error:
            self.logger.exception(
                "game_state_error",
                extra={"event": "game_state_error", "error": str(error)},
            )
            event = self.state_cache.transition(
                GameState.ERROR,
                confidence=1.0,
                source="game_state_engine",
                details={"error": str(error)},
            )
            return event.to_dict()

    def events(self) -> dict[str, Any]:
        return self.state_cache.events_dict()

    def _select_state(
        self,
        *,
        runtime_status: dict[str, Any],
        detection_timestamp: Optional[float],
        frame_id: Optional[int],
        objects: list[Any],
        now: float,
        runtime_events: list[Any],
    ) -> tuple[GameState, float, str, dict[str, Any]]:
        runtime_result = runtime_state(runtime_status)
        if runtime_result == GameState.ERROR:
            return (
                GameState.ERROR,
                1.0,
                "runtime",
                {"runtime_status": runtime_status},
            )

        if self._is_timeout(runtime_status, now):
            return (
                GameState.TIMEOUT,
                1.0,
                "timer",
                {"runtime_status": runtime_status},
            )

        if contains_grab_event(runtime_events):
            return (
                GameState.GRABBING,
                1.0,
                "runtime_event",
                {"events": runtime_events},
            )

        threshold = self.config.detection_confidence_threshold
        prizes = prize_objects(objects, threshold, self.config.prize_zone)
        if prizes:
            return (
                GameState.PRIZE_DETECTED,
                max(object_confidence(obj) for obj in prizes),
                "vision",
                {"frame_id": frame_id, "objects": len(prizes)},
            )

        if runtime_result == GameState.PLAYING:
            return (
                GameState.PLAYING,
                1.0,
                "runtime",
                {"runtime_status": runtime_status},
            )

        player_count = count_players(objects, threshold)
        if player_count:
            self._last_person_seen_at = now
            previous_count = self._last_player_count
            self._last_player_count = player_count
            if previous_count > 0 and player_count != previous_count:
                return (
                    GameState.PLAYER_COUNT_CHANGED,
                    1.0,
                    "vision",
                    {"player_count": player_count, "frame_id": frame_id},
                )
            if player_count >= self.config.player_presence_threshold:
                return (
                    GameState.PLAYER_PRESENT,
                    1.0,
                    "vision",
                    {"player_count": player_count, "frame_id": frame_id},
                )

        if self._last_person_seen_at is not None:
            idle_elapsed = now - self._last_person_seen_at
            if idle_elapsed < self.config.idle_timeout_seconds:
                return (
                    GameState.PLAYER_PRESENT,
                    0.5,
                    "timer",
                    {"last_seen_seconds": round(idle_elapsed, 3)},
                )

        self._last_player_count = 0
        if detection_timestamp is None:
            return (
                GameState.ERROR,
                0.75,
                "vision",
                {"reason": "detection_unavailable"},
            )
        return GameState.IDLE, 1.0, "timer", {"frame_id": frame_id}

    def _is_timeout(self, runtime_status: dict[str, Any], now: float) -> bool:
        play_ends_at = runtime_status.get("play_ends_at")
        if (
            play_ends_at
            and runtime_status.get("running")
            and now >= float(play_ends_at)
        ):
            return True
        play_started_at = runtime_status.get("play_started_at")
        if play_started_at and runtime_status.get("running"):
            return now - float(play_started_at) >= self.config.timeout_seconds
        return False
