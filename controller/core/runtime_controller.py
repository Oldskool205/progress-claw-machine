"""Central controller safety boundary."""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import asdict

from controller.adapters.arduino_adapter import ArduinoAdapter, ArduinoResponse
from controller.models import (
    ClawPowerCommand,
    EmergencyStopCommand,
    PlayStartCommand,
    PlayStopCommand,
)
from controller.state import MachineState
from controller.safety.validator import SafetyError, SafetyValidator


LOGGER = logging.getLogger("progress_claw.controller")


class RuntimeController:
    """Owns machine state, safety checks, and all Arduino communication."""

    def __init__(
        self,
        arduino: ArduinoAdapter | None = None,
        validator: SafetyValidator | None = None,
        state: MachineState | None = None,
    ) -> None:
        self.arduino = arduino or ArduinoAdapter.from_env()
        self.validator = validator or SafetyValidator()
        self.state = state or MachineState()
        self._lock = threading.RLock()
        self._play_generation = 0

    @classmethod
    def from_env(cls) -> "RuntimeController":
        state = MachineState(
            play_duration_seconds=int(os.getenv("CLAW_PLAY_DURATION_SECONDS", "60")),
            claw_power_percent=int(os.getenv("CLAW_GRABBER_POWER_PERCENT", "100")),
        )
        return cls(state=state)

    def status(self) -> dict:
        with self._lock:
            self.state.arduino_connected = self.arduino.connected
            self.state.mock_arduino = self.arduino.mock_mode
            return self.state.snapshot()

    def start_play(self, command: PlayStartCommand) -> dict:
        with self._lock:
            self.validator.validate_start(command, self.state)
            self._play_generation += 1
            generation = self._play_generation
            self.state.status = "running"
            self.state.play_mode = "test" if command.test_mode else "play"
            self.state.play_duration_seconds = command.duration_seconds
            now = time.time()
            self.state.play_started_at = now
            self.state.play_ends_at = now + command.duration_seconds
            self._log_command(command)
            power_response = self._send(f"CLAW POWER {self.state.claw_power_percent}")
            start_response = self._send(f"PLAY START {command.duration_seconds}")
            self._record_response(start_response)
            threading.Thread(
                target=self._auto_stop_after_play,
                args=(generation, command.duration_seconds),
                daemon=True,
            ).start()
            return self.state.snapshot(
                extra={
                    "ok": True,
                    "arduino_response": start_response.message,
                    "power_response": power_response.message,
                }
            )

    def stop_play(self, command: PlayStopCommand | None = None) -> dict:
        with self._lock:
            command = command or PlayStopCommand()
            self.validator.validate_stop(command, self.state)
            self._play_generation += 1
            self._log_command(command)
            response = self._send("PLAY STOP")
            self._record_response(response)
            self._mark_stopped("ready")
            return self.state.snapshot(
                extra={"ok": True, "arduino_response": response.message}
            )

    def set_claw_power(self, command: ClawPowerCommand) -> dict:
        with self._lock:
            self.validator.validate_claw_power(command, self.state)
            self.state.claw_power_percent = command.power_percent
            self._log_command(command)
            response = self._send(f"CLAW POWER {command.power_percent}")
            self._record_response(response)
            return self.state.snapshot(
                extra={"ok": True, "arduino_response": response.message}
            )

    def emergency_stop(self, command: EmergencyStopCommand | None = None) -> dict:
        with self._lock:
            command = command or EmergencyStopCommand()
            self._play_generation += 1
            self.state.emergency_stopped = True
            self._log_command(command)
            response = self._send("EMERGENCY STOP")
            self._record_response(response)
            self._mark_stopped("emergency_stopped")
            LOGGER.critical(
                "safety_emergency_stop",
                extra={
                    "event": "safety_emergency_stop",
                    "source": command.source,
                    "reason": command.reason,
                },
            )
            return self.state.snapshot(
                extra={"ok": True, "arduino_response": response.message}
            )

    def clear_emergency_for_tests(self) -> None:
        with self._lock:
            self.state.emergency_stopped = False
            self.state.status = "ready"

    def _auto_stop_after_play(self, generation: int, duration_seconds: int) -> None:
        time.sleep(duration_seconds)
        with self._lock:
            if generation != self._play_generation or self.state.play_mode is None:
                return
            response = self._send("PLAY STOP")
            self._record_response(response)
            self._mark_stopped("ready")

    def _send(self, command: str) -> ArduinoResponse:
        response = self.arduino.send_command(command)
        self.state.arduino_connected = self.arduino.connected
        self.state.mock_arduino = response.mock
        return response

    def _record_response(self, response: ArduinoResponse) -> None:
        if response.ok:
            self.state.last_error = None
            return
        self.state.last_error = response.message
        self.state.status = "fault"
        LOGGER.error(
            "safety_arduino_fault",
            extra={"event": "safety_arduino_fault", "response": response.message},
        )

    def _mark_stopped(self, status: str) -> None:
        self.state.status = status
        self.state.play_mode = None
        self.state.play_started_at = None
        self.state.play_ends_at = None

    def _log_command(self, command: object) -> None:
        payload = asdict(command)
        LOGGER.info(
            "controller_command",
            extra={"event": "controller_command", "command": payload},
        )
