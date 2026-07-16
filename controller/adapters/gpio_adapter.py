"""Raspberry Pi GPIO transport for the Arduino dashboard control pins."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Callable

from controller.adapters.arduino_adapter import ArduinoResponse

try:
    from gpiozero import OutputDevice
except ImportError:  # pragma: no cover - depends on deployment image
    OutputDevice = None


LOGGER = logging.getLogger("progress_claw.controller.gpio")


@dataclass
class GpioArduinoAdapter:
    """Translate controller commands into the firmware's four GPIO inputs.

    GPIO 17 is an active-low play gate connected to Arduino A0. GPIOs 22, 23,
    and 24 provide the three-bit claw-power level on Arduino A1-A3.
    """

    start_pin: int = 17
    power_pins: tuple[int, int, int] = (22, 23, 24)
    force_mock: bool = False
    output_device_factory: Callable | None = None
    _start_output: object | None = field(default=None, init=False, repr=False)
    _power_outputs: list[object] = field(default_factory=list, init=False, repr=False)
    _mock_log: list[str] = field(default_factory=list, init=False, repr=False)

    @classmethod
    def from_env(cls) -> "GpioArduinoAdapter":
        pins = tuple(
            int(item.strip())
            for item in os.getenv("CLAW_GRABBER_POWER_GPIOS", "22,23,24").split(",")
            if item.strip()
        )
        if len(pins) != 3:
            raise ValueError("CLAW_GRABBER_POWER_GPIOS must contain exactly 3 pins")
        return cls(
            start_pin=int(os.getenv("CLAW_START_GPIO", "17")),
            power_pins=pins,
            force_mock=os.getenv("CLAW_ARDUINO_MOCK", "").lower()
            in {"1", "true", "yes", "on"},
        )

    @property
    def mock_mode(self) -> bool:
        return self.force_mock or self._start_output is None

    @property
    def connected(self) -> bool:
        self.connect()
        return not self.mock_mode

    @property
    def mock_commands(self) -> tuple[str, ...]:
        return tuple(self._mock_log)

    def connect(self) -> None:
        if self.force_mock or self._start_output is not None:
            return
        factory = self.output_device_factory or OutputDevice
        if factory is None:
            self.force_mock = True
            LOGGER.warning("gpio_library_unavailable", extra={"event": "gpio_library_unavailable"})
            return
        try:
            # active_high=False makes on() pull Arduino A0 low.
            self._start_output = factory(
                self.start_pin, active_high=False, initial_value=False
            )
            self._power_outputs = [
                factory(pin, active_high=True, initial_value=False)
                for pin in self.power_pins
            ]
            LOGGER.info(
                "gpio_connected",
                extra={
                    "event": "gpio_connected",
                    "start_pin": self.start_pin,
                    "power_pins": self.power_pins,
                },
            )
        except Exception as error:  # pragma: no cover - hardware dependent
            self.close()
            self.force_mock = True
            LOGGER.warning(
                "gpio_connect_failed",
                extra={"event": "gpio_connect_failed", "error": str(error)},
            )

    def close(self) -> None:
        outputs = ([self._start_output] if self._start_output is not None else []) + self._power_outputs
        for output in outputs:
            try:
                output.close()
            except Exception:
                pass
        self._start_output = None
        self._power_outputs = []

    def send_command(self, command: str) -> ArduinoResponse:
        command = command.strip()
        if not command:
            return ArduinoResponse(False, "ERR EMPTY_COMMAND", self.mock_mode)
        self.connect()
        if self.mock_mode:
            self._mock_log.append(command)
            return ArduinoResponse(True, f"OK MOCK {command}", True)

        try:
            if command.startswith("CLAW POWER "):
                self._set_power_percent(int(command.rsplit(" ", 1)[1]))
            elif command.startswith("PLAY START "):
                self._start_output.on()
            elif command == "PLAY STOP":
                # 111 on gate release requests the firmware's safe end pulse.
                self._set_power_level(7)
                self._start_output.off()
            elif command == "EMERGENCY STOP":
                # Do not request a pulse during an emergency stop.
                self._set_power_level(0)
                self._start_output.off()
            else:
                return ArduinoResponse(False, f"ERR UNKNOWN_COMMAND {command}", False)
        except Exception as error:  # pragma: no cover - hardware dependent
            LOGGER.error(
                "gpio_command_failed",
                extra={"event": "gpio_command_failed", "command": command, "error": str(error)},
            )
            return ArduinoResponse(False, f"ERR {error}", False)
        return ArduinoResponse(True, f"OK GPIO {command}", False)

    def _set_power_percent(self, percent: int) -> None:
        percent = max(40, min(100, percent))
        level = round((percent - 40) / 10)
        self._set_power_level(max(0, min(6, level)))

    def _set_power_level(self, level: int) -> None:
        for index, output in enumerate(self._power_outputs):
            if level & (1 << index):
                output.on()
            else:
                output.off()
