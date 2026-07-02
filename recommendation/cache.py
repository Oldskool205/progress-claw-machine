"""Thread-safe recommendation cache."""

from __future__ import annotations

import threading
from collections import deque

from recommendation.models import Recommendation, RecommendationType


class RecommendationCache:
    """Store latest recommendation plus a bounded history."""

    def __init__(self, max_history: int = 50) -> None:
        self._lock = threading.Lock()
        self._latest = Recommendation(
            recommendation=RecommendationType.NO_ACTION,
            confidence=1.0,
            reason="No recommendation generated yet",
            source="initial",
        )
        self._history: deque[Recommendation] = deque(
            [self._latest],
            maxlen=max_history,
        )

    def latest(self) -> Recommendation:
        with self._lock:
            return self._latest

    def history(self) -> list[Recommendation]:
        with self._lock:
            return list(self._history)

    def update(self, recommendation: Recommendation) -> Recommendation:
        with self._lock:
            self._latest = recommendation
            self._history.appendleft(recommendation)
        return recommendation

    def latest_dict(self) -> dict:
        return self.latest().to_dict()

    def history_dict(self) -> dict:
        return {
            "recommendations": [
                recommendation.to_dict() for recommendation in self.history()
            ]
        }
