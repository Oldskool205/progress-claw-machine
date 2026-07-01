"""Machine state owned by the controller."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class MachineState:
    status: str = "ready"
    machine_enabled: bool = True
    emergency_stopped: bool = False
    play_mode: str | None = None
    play_duration_seconds: int = 60
    play_started_at: float | None = None
    play_ends_at: float | None = None
    claw_power_percent: int = 100
    arduino_connected: bool = False
    mock_arduino: bool = True
    last_error: str | None = None

    def snapshot(self, extra: dict | None = None) -> dict:
        payload = asdict(self)
        payload["running"] = self.play_mode is not None
        if extra:
            payload.update(extra)
        return payload
