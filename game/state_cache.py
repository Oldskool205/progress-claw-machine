"""Thread-safe latest game state and recent event cache."""

from __future__ import annotations

import threading
from collections import deque
from typing import Optional

from game.state_models import GameState, GameStateEvent


class GameStateCache:
    """Store latest state plus a bounded recent event buffer."""

    def __init__(self, max_events: int = 50) -> None:
        self._lock = threading.Lock()
        self._latest = GameStateEvent(
            state=GameState.IDLE,
            confidence=1.0,
            source="initial",
            details={},
        )
        self._events: deque[GameStateEvent] = deque([self._latest], maxlen=max_events)

    def latest(self) -> GameStateEvent:
        with self._lock:
            return self._latest

    def recent_events(self) -> list[GameStateEvent]:
        with self._lock:
            return list(self._events)

    def update(self, event: GameStateEvent) -> GameStateEvent:
        with self._lock:
            self._latest = event
            self._events.appendleft(event)
        return event

    def transition(
        self,
        state: GameState,
        *,
        confidence: float,
        source: str,
        details: Optional[dict] = None,
    ) -> GameStateEvent:
        event = GameStateEvent(
            state=state,
            confidence=confidence,
            source=source,
            details=details or {},
        )
        return self.update(event)

    def latest_dict(self) -> dict:
        return self.latest().to_dict()

    def events_dict(self) -> dict:
        return {"events": [event.to_dict() for event in self.recent_events()]}
