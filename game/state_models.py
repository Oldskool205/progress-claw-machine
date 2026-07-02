"""Game state data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class GameState(str, Enum):
    IDLE = "IDLE"
    PLAYER_PRESENT = "PLAYER_PRESENT"
    PLAYER_COUNT_CHANGED = "PLAYER_COUNT_CHANGED"
    READY_TO_PLAY = "READY_TO_PLAY"
    PLAYING = "PLAYING"
    GRABBING = "GRABBING"
    PRIZE_DETECTED = "PRIZE_DETECTED"
    PRIZE_CAPTURED = "PRIZE_CAPTURED"
    FAILED_ATTEMPT = "FAILED_ATTEMPT"
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class GameStateEvent:
    state: GameState
    timestamp: str = field(default_factory=utc_timestamp)
    confidence: float = 1.0
    source: str = "game_state_engine"
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "timestamp": self.timestamp,
            "confidence": round(float(self.confidence), 4),
            "source": self.source,
            "details": dict(self.details),
        }
