"""Recommendation data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class RecommendationType(str, Enum):
    NO_ACTION = "NO_ACTION"
    WAIT_FOR_PLAYER = "WAIT_FOR_PLAYER"
    READY_TO_START = "READY_TO_START"
    INCREASE_CLAW_POWER = "INCREASE_CLAW_POWER"
    REDUCE_CLAW_POWER = "REDUCE_CLAW_POWER"
    START_DEMO_MODE = "START_DEMO_MODE"
    STOP_DEMO_MODE = "STOP_DEMO_MODE"
    CHECK_CAMERA = "CHECK_CAMERA"
    CHECK_ARDUINO = "CHECK_ARDUINO"
    SYSTEM_DEGRADED = "SYSTEM_DEGRADED"


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Recommendation:
    recommendation: RecommendationType
    confidence: float
    reason: str
    timestamp: str = field(default_factory=utc_timestamp)
    source: str = "RecommendationEngine"
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "recommendation": self.recommendation.value,
            "confidence": round(float(self.confidence), 4),
            "reason": self.reason,
            "timestamp": self.timestamp,
            "source": self.source,
            "details": dict(self.details),
        }
