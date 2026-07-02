"""Detection data models for Vision Service."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class DetectedObject:
    class_name: str
    confidence: float
    bounding_box: list[float]
    timestamp: float
    tracking_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "class": self.class_name,
            "confidence": round(float(self.confidence), 4),
            "bbox": list(self.bounding_box),
            "timestamp": self.timestamp,
            "tracking_id": self.tracking_id,
        }


@dataclass(frozen=True)
class DetectionResult:
    timestamp: Optional[float] = None
    frame_id: Optional[int] = None
    objects: list[DetectedObject] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "frame_id": self.frame_id,
            "objects": [obj.to_dict() for obj in self.objects],
        }
