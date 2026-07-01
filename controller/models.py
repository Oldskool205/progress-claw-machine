"""Command models accepted by the controller."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlayStartCommand:
    duration_seconds: int
    source: str = "dashboard"
    test_mode: bool = False


@dataclass(frozen=True)
class PlayStopCommand:
    source: str = "dashboard"
    reason: str = "operator_stop"


@dataclass(frozen=True)
class ClawPowerCommand:
    power_percent: int
    source: str = "dashboard"


@dataclass(frozen=True)
class EmergencyStopCommand:
    source: str = "dashboard"
    reason: str = "emergency_stop"
