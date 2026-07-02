"""Thread-safe latest-frame storage for Vision Service."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Frame:
    data: bytes
    timestamp: float
    sequence: int


class FrameQueue:
    """Maintain only the latest frame and notify waiting consumers."""

    def __init__(self) -> None:
        self._condition = threading.Condition()
        self._latest: Optional[Frame] = None
        self._sequence = 0

    def put(self, data: bytes, timestamp: Optional[float] = None) -> Frame:
        if not isinstance(data, bytes):
            raise TypeError("Frame data must be bytes")
        with self._condition:
            self._sequence += 1
            frame = Frame(
                data=data,
                timestamp=time.time() if timestamp is None else float(timestamp),
                sequence=self._sequence,
            )
            self._latest = frame
            self._condition.notify_all()
            return frame

    def latest(self) -> Optional[Frame]:
        with self._condition:
            return self._latest

    def wait_for_next(
        self,
        last_sequence: Optional[int] = None,
        timeout: Optional[float] = None,
    ) -> Optional[Frame]:
        with self._condition:
            self._condition.wait_for(
                lambda: self._latest is not None
                and (last_sequence is None or self._latest.sequence != last_sequence),
                timeout=timeout,
            )
            if self._latest is None:
                return None
            if last_sequence is not None and self._latest.sequence == last_sequence:
                return None
            return self._latest

    def clear(self) -> None:
        with self._condition:
            self._latest = None
            self._condition.notify_all()
