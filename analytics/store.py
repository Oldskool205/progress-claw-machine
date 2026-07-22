"""Bounded, thread-safe analytics event store."""

from __future__ import annotations

import threading
from collections import Counter, deque
from datetime import datetime, timezone
from typing import Optional

from analytics.models import AnalyticsEvent


def _parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except (TypeError, ValueError) as error:
        raise ValueError(f"Invalid ISO-8601 timestamp: {value}") from error


class AnalyticsStore:
    """Keep a bounded read model; no analytics data reaches hardware control."""

    def __init__(self, max_events: int = 1000) -> None:
        if max_events < 1:
            raise ValueError("max_events must be positive")
        self._lock = threading.Lock()
        self._events: deque[AnalyticsEvent] = deque(maxlen=max_events)
        self._dedupe_keys: set[str] = set()
        self._event_dedupe_keys: deque[Optional[str]] = deque(maxlen=max_events)
        self._max_events = max_events

    def add(self, event: AnalyticsEvent, *, dedupe_key: Optional[str] = None) -> bool:
        with self._lock:
            if dedupe_key and dedupe_key in self._dedupe_keys:
                return False
            if len(self._events) == self._max_events:
                self._dedupe_keys.discard(self._event_dedupe_keys[-1])
            self._events.appendleft(event)
            self._event_dedupe_keys.appendleft(dedupe_key)
            if dedupe_key:
                self._dedupe_keys.add(dedupe_key)
            return True

    def query(
        self,
        *,
        category: Optional[str] = None,
        event_type: Optional[str] = None,
        source: Optional[str] = None,
        session_id: Optional[str] = None,
        min_confidence: Optional[float] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        limit: int = 100,
    ) -> list[AnalyticsEvent]:
        if limit < 1 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
        start_at = _parse_timestamp(start)
        end_at = _parse_timestamp(end)
        if start_at and end_at and start_at > end_at:
            raise ValueError("start must be before end")
        with self._lock:
            snapshot = list(self._events)

        matches = []
        for event in snapshot:
            timestamp = _parse_timestamp(event.timestamp)
            if category and event.category.value != category:
                continue
            if event_type and event.event_type != event_type:
                continue
            if source and event.source != source:
                continue
            if session_id and event.session_id != session_id:
                continue
            if min_confidence is not None and (
                event.confidence is None or event.confidence < min_confidence
            ):
                continue
            if start_at and timestamp and timestamp < start_at:
                continue
            if end_at and timestamp and timestamp > end_at:
                continue
            matches.append(event)
            if len(matches) >= limit:
                break
        return matches

    def summary(self) -> dict:
        with self._lock:
            snapshot = list(self._events)
        categories = Counter(event.category.value for event in snapshot)
        event_types = Counter(event.event_type for event in snapshot)
        confidences = [
            event.confidence for event in snapshot if event.confidence is not None
        ]
        return {
            "total_events": len(snapshot),
            "by_category": dict(sorted(categories.items())),
            "by_event_type": dict(sorted(event_types.items())),
            "average_confidence": (
                None
                if not confidences
                else round(sum(confidences) / len(confidences), 4)
            ),
            "capacity": self._max_events,
            "storage": "memory",
        }
