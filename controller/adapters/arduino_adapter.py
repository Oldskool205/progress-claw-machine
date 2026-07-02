"""Arduino serial adapter with automatic mock fallback."""

from __future__ import annotations

import glob
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Iterable

try:
    import serial
except ImportError:  # pragma: no cover - exercised when pyserial is absent
    serial = None


LOGGER = logging.getLogger("progress_claw.controller.arduino")


@dataclass
class ArduinoResponse:
    ok: bool
    message: str
    mock: bool


@dataclass
class ArduinoAdapter:
    """Line-based Arduino transport.

    The controller owns this adapter. Dashboard, AI, and plugins should call the
    controller API instead of instantiating this class directly.
    """

    port: str | None = None
    baud_rate: int = 115200
    timeout_seconds: float = 1.0
    force_mock: bool = False
    device_patterns: tuple[str, ...] = (
        "/dev/ttyUSB*",
        "/dev/ttyACM*",
        "/dev/serial/by-id/*",
    )
    _serial: object | None = field(default=None, init=False, repr=False)
    _mock_log: list[str] = field(default_factory=list, init=False, repr=False)

    @classmethod
    def from_env(cls) -> "ArduinoAdapter":
        port = os.getenv("CLAW_ARDUINO_DEVICE") or None
        patterns = tuple(
            item.strip()
            for item in os.getenv(
                "CLAW_ARDUINO_DEVICE_PATTERNS",
                "/dev/ttyUSB*,/dev/ttyACM*,/dev/serial/by-id/*",
            ).split(",")
            if item.strip()
        )
        force_mock = os.getenv("CLAW_ARDUINO_MOCK", "").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        baud_rate = int(os.getenv("CLAW_ARDUINO_BAUD", "115200"))
        return cls(
            port=port,
            baud_rate=baud_rate,
            force_mock=force_mock,
            device_patterns=patterns,
        )

    @property
    def mock_mode(self) -> bool:
        return self.force_mock or self._serial is None

    @property
    def connected(self) -> bool:
        if self.force_mock:
            return False
        if self._serial is not None:
            return True
        return self._discover_port() is not None

    @property
    def mock_commands(self) -> tuple[str, ...]:
        return tuple(self._mock_log)

    def connect(self) -> None:
        if self.force_mock or self._serial is not None:
            return
        if serial is None:
            LOGGER.warning(
                "arduino_serial_unavailable",
                extra={"event": "arduino_serial_unavailable"},
            )
            self.force_mock = True
            return
        port = self.port or self._discover_port()
        if not port:
            LOGGER.warning(
                "arduino_not_connected", extra={"event": "arduino_not_connected"}
            )
            self.force_mock = True
            return
        try:
            self._serial = serial.Serial(
                port, self.baud_rate, timeout=self.timeout_seconds
            )
            time.sleep(0.2)
            LOGGER.info(
                "arduino_connected",
                extra={
                    "event": "arduino_connected",
                    "port": port,
                    "baud_rate": self.baud_rate,
                },
            )
        except Exception as error:  # pragma: no cover - hardware dependent
            self._serial = None
            self.force_mock = True
            LOGGER.warning(
                "arduino_connect_failed",
                extra={
                    "event": "arduino_connect_failed",
                    "port": port,
                    "error": str(error),
                },
            )

    def close(self) -> None:
        if self._serial is None:
            return
        try:
            self._serial.close()
        finally:
            self._serial = None

    def send_command(self, command: str) -> ArduinoResponse:
        command = command.strip()
        if not command:
            return ArduinoResponse(
                ok=False, message="ERR EMPTY_COMMAND", mock=self.mock_mode
            )
        self.connect()
        if self.mock_mode:
            self._mock_log.append(command)
            LOGGER.info(
                "arduino_mock_command",
                extra={"event": "arduino_mock_command", "command": command},
            )
            return ArduinoResponse(ok=True, message=f"OK MOCK {command}", mock=True)

        try:
            payload = f"{command}\n".encode("utf-8")
            self._serial.write(payload)
            self._serial.flush()
            raw_response = (
                self._serial.readline().decode("utf-8", errors="replace").strip()
            )
        except Exception as error:  # pragma: no cover - hardware dependent
            self.close()
            LOGGER.error(
                "arduino_command_failed",
                extra={
                    "event": "arduino_command_failed",
                    "command": command,
                    "error": str(error),
                },
            )
            return ArduinoResponse(ok=False, message=f"ERR {error}", mock=False)

        response = raw_response or "ERR NO_RESPONSE"
        ok = response.startswith("OK")
        LOGGER.info(
            "arduino_command",
            extra={
                "event": "arduino_command",
                "command": command,
                "response": response,
                "ok": ok,
            },
        )
        return ArduinoResponse(ok=ok, message=response, mock=False)

    def _discover_port(self) -> str | None:
        candidates: list[str] = []
        if self.port:
            candidates.append(self.port)
        candidates.extend(_expand_patterns(self.device_patterns))
        return candidates[0] if candidates else None


def _expand_patterns(patterns: Iterable[str]) -> list[str]:
    ports: list[str] = []
    for pattern in patterns:
        if any(character in pattern for character in "*?["):
            ports.extend(sorted(glob.glob(pattern)))
        elif os.path.exists(pattern):
            ports.append(pattern)
    return ports
