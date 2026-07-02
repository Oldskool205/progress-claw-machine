"""Rule helpers for game state interpretation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from game.state_models import GameState

PRIZE_CLASSES = {"teddy bear"}
PLAYER_CLASSES = {"person"}


@dataclass(frozen=True)
class PrizeZone:
    x_min: float = 0.0
    y_min: float = 0.0
    x_max: float = 10000.0
    y_max: float = 10000.0

    def contains(self, bbox: Iterable[float]) -> bool:
        values = list(bbox)
        if len(values) < 4:
            return False
        center_x = (float(values[0]) + float(values[2])) / 2.0
        center_y = (float(values[1]) + float(values[3])) / 2.0
        return (
            self.x_min <= center_x <= self.x_max
            and self.y_min <= center_y <= self.y_max
        )


def object_class(obj: Any) -> str:
    if isinstance(obj, dict):
        return str(obj.get("class", ""))
    return str(getattr(obj, "class_name", getattr(obj, "class", "")))


def object_confidence(obj: Any) -> float:
    if isinstance(obj, dict):
        return float(obj.get("confidence", 0.0))
    return float(getattr(obj, "confidence", 0.0))


def object_bbox(obj: Any) -> list[float]:
    if isinstance(obj, dict):
        return list(obj.get("bbox", obj.get("bounding_box", [])))
    return list(getattr(obj, "bounding_box", []))


def confident_objects(objects: Iterable[Any], threshold: float) -> list[Any]:
    return [obj for obj in objects if object_confidence(obj) >= threshold]


def count_players(objects: Iterable[Any], threshold: float) -> int:
    return sum(
        1
        for obj in confident_objects(objects, threshold)
        if object_class(obj) in PLAYER_CLASSES
    )


def prize_objects(
    objects: Iterable[Any],
    threshold: float,
    prize_zone: PrizeZone,
) -> list[Any]:
    return [
        obj
        for obj in confident_objects(objects, threshold)
        if object_class(obj) in PRIZE_CLASSES and prize_zone.contains(object_bbox(obj))
    ]


def runtime_state(runtime_status: dict[str, Any]) -> GameState | None:
    if runtime_status.get("last_error") or runtime_status.get("status") == "fault":
        return GameState.ERROR
    if runtime_status.get("emergency_stopped"):
        return GameState.ERROR
    if runtime_status.get("running") or runtime_status.get("play_mode") is not None:
        return GameState.PLAYING
    return None


def contains_grab_event(events: Iterable[Any]) -> bool:
    for event in events:
        text = str(event).lower()
        if "grab" in text or "claw" in text:
            return True
    return False
