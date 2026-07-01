"""Controller safety validation rules."""

from __future__ import annotations

from controller.models import ClawPowerCommand, PlayStartCommand, PlayStopCommand
from controller.state import MachineState


class SafetyError(ValueError):
    """Raised when a command violates a safety rule."""


class SafetyValidator:
    min_play_seconds = 10
    max_play_seconds = 180
    min_claw_power_percent = 40
    max_claw_power_percent = 100

    def validate_start(self, command: PlayStartCommand, state: MachineState) -> None:
        if state.emergency_stopped:
            raise SafetyError("Emergency stop is active")
        if not state.machine_enabled:
            raise SafetyError("Machine is disabled")
        if state.play_mode is not None:
            raise SafetyError("Machine is already running")
        if not self.min_play_seconds <= int(command.duration_seconds) <= self.max_play_seconds:
            raise SafetyError(
                f"Play duration must be {self.min_play_seconds}-{self.max_play_seconds} seconds"
            )

    def validate_stop(self, command: PlayStopCommand, state: MachineState) -> None:
        if state.play_mode is None:
            raise SafetyError("Machine is not running")

    def validate_claw_power(self, command: ClawPowerCommand, state: MachineState) -> None:
        if state.emergency_stopped:
            raise SafetyError("Emergency stop is active")
        if not self.min_claw_power_percent <= int(command.power_percent) <= self.max_claw_power_percent:
            raise SafetyError(
                f"Claw power must be {self.min_claw_power_percent}-{self.max_claw_power_percent}%"
            )
