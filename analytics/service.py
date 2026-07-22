"""Collect read-only snapshots from existing service contracts."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from typing import Any, Callable

from analytics.models import AnalyticsCategory, AnalyticsEvent
from analytics.store import AnalyticsStore


def _epoch_to_iso(value: float) -> str:
    return datetime.fromtimestamp(value, timezone.utc).isoformat()


class AnalyticsService:
    """Aggregate public runtime state and caches without issuing commands."""

    def __init__(
        self,
        *,
        runtime_status_provider: Callable[[], dict[str, Any]],
        detection_cache: Any,
        game_state_cache: Any,
        recommendation_cache: Any,
        store: AnalyticsStore | None = None,
    ) -> None:
        self.runtime_status_provider = runtime_status_provider
        self.detection_cache = detection_cache
        self.game_state_cache = game_state_cache
        self.recommendation_cache = recommendation_cache
        self.store = store or AnalyticsStore()
        self._last_runtime_fingerprint: str | None = None
        self._collect_lock = threading.Lock()

    def collect(self) -> None:
        with self._collect_lock:
            self._collect_runtime()
            self._collect_detection()
            self._collect_game_states()
            self._collect_recommendations()

    def _collect_runtime(self) -> None:
        status = self.runtime_status_provider()
        relevant = {
            key: status.get(key)
            for key in (
                "status",
                "running",
                "play_mode",
                "arduino_connected",
                "mock_arduino",
                "emergency_stopped",
                "machine_enabled",
                "last_error",
            )
        }
        fingerprint = json.dumps(relevant, sort_keys=True, default=str)
        if fingerprint == self._last_runtime_fingerprint:
            return
        self._last_runtime_fingerprint = fingerprint
        unsafe = bool(relevant["emergency_stopped"] or relevant["last_error"])
        category = AnalyticsCategory.SAFETY if unsafe else AnalyticsCategory.RUNTIME
        event_type = "runtime_safety_state" if unsafe else "runtime_status"
        self.store.add(
            AnalyticsEvent(
                category=category,
                event_type=event_type,
                source="RuntimeController.status",
                details=relevant,
            )
        )

    def _collect_detection(self) -> None:
        detection = self.detection_cache.latest()
        if detection.timestamp is None:
            return
        objects = [item.to_dict() for item in detection.objects]
        confidence = (
            max((item.confidence for item in detection.objects), default=None)
        )
        self.store.add(
            AnalyticsEvent(
                category=AnalyticsCategory.VISION,
                event_type="detection_result",
                source="VisionService",
                timestamp=_epoch_to_iso(detection.timestamp),
                confidence=confidence,
                details={"frame_id": detection.frame_id, "objects": objects},
            ),
            dedupe_key=f"vision:{detection.frame_id}:{detection.timestamp}",
        )

    def _collect_game_states(self) -> None:
        for item in reversed(self.game_state_cache.recent_events()):
            payload = item.to_dict()
            self.store.add(
                AnalyticsEvent(
                    category=AnalyticsCategory.GAME_STATE,
                    event_type=payload["state"],
                    source=payload["source"],
                    timestamp=payload["timestamp"],
                    confidence=payload["confidence"],
                    session_id=payload["details"].get("session_id"),
                    details=payload["details"],
                ),
                dedupe_key=f"game:{payload['timestamp']}:{payload['state']}",
            )

    def _collect_recommendations(self) -> None:
        for item in reversed(self.recommendation_cache.history()):
            payload = item.to_dict()
            self.store.add(
                AnalyticsEvent(
                    category=AnalyticsCategory.RECOMMENDATION,
                    event_type=payload["recommendation"],
                    source=payload["source"],
                    timestamp=payload["timestamp"],
                    confidence=payload["confidence"],
                    session_id=payload["details"].get("session_id"),
                    details={"reason": payload["reason"], **payload["details"]},
                ),
                dedupe_key=(
                    f"recommendation:{payload['timestamp']}:"
                    f"{payload['recommendation']}"
                ),
            )
