"""Analytics event schema."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4


class AnalyticsCategory(str, Enum):
    RUNTIME = "runtime"
    VISION = "vision"
    GAME_STATE = "game_state"
    RECOMMENDATION = "recommendation"
    SAFETY = "safety"


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class AnalyticsEvent:
    category: AnalyticsCategory
    event_type: str
    source: str
    timestamp: str = field(default_factory=utc_timestamp)
    confidence: Optional[float] = None
    session_id: Optional[str] = None
    details: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: uuid4().hex)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "category": self.category.value,
            "event_type": self.event_type,
            "source": self.source,
            "confidence": (
                None if self.confidence is None else round(float(self.confidence), 4)
            ),
            "session_id": self.session_id,
            "details": dict(self.details),
        }
