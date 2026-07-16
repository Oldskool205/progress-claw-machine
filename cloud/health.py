"""Thread-safe, credential-free local cloud observability."""

from __future__ import annotations

import threading
from dataclasses import asdict, dataclass
from typing import Any, Optional


@dataclass
class CloudHealthState:
    enabled: bool
    configured: bool
    connected: bool
    machine_name: str
    sync_interval_seconds: float
    last_connection_attempt: Optional[str] = None
    last_successful_connection: Optional[str] = None
    last_sync_attempt: Optional[str] = None
    last_successful_sync: Optional[str] = None
    last_heartbeat: Optional[str] = None
    last_supabase_read: Optional[str] = None
    last_error: Optional[str] = None
    consecutive_failure_count: int = 0
    retry_count: int = 0
    current_machine_status: Optional[dict[str, Any]] = None
    supabase_machine_status: Optional[dict[str, Any]] = None


class CloudHealthTracker:
    def __init__(self, initial: CloudHealthState) -> None:
        self._state = initial
        self._lock = threading.RLock()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return asdict(self._state)

    def update(self, **changes: Any) -> None:
        with self._lock:
            for name, value in changes.items():
                if hasattr(self._state, name):
                    setattr(self._state, name, value)

    def success(self, **changes: Any) -> None:
        self.update(
            connected=True,
            last_error=None,
            consecutive_failure_count=0,
            **changes,
        )

    def failure(self, category: str, **changes: Any) -> None:
        with self._lock:
            self._state.connected = False
            self._state.last_error = category
            self._state.consecutive_failure_count += 1
            self._state.retry_count += 1
            for name, value in changes.items():
                if hasattr(self._state, name):
                    setattr(self._state, name, value)
