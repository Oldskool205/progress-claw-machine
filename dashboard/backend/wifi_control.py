"""Wi-Fi control boundary for protected dashboard administration.

Mock mode remains the default. Live mode can invoke only the separately
installed and sudo-allowlisted helper; it never runs networking tools directly.
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from typing import Any


class WifiValidationError(ValueError):
    """Raised when submitted Wi-Fi credentials are not safe or supported."""


class WifiControlError(RuntimeError):
    """Raised when the isolated system helper cannot complete an operation."""


def validate_credentials(ssid: Any, password: Any) -> str:
    if not isinstance(ssid, str) or not ssid:
        raise WifiValidationError("Network name is required")
    if any(ord(character) < 32 or ord(character) == 127 for character in ssid):
        raise WifiValidationError("Network name contains unsupported characters")
    if len(ssid.encode("utf-8")) > 32:
        raise WifiValidationError("Network name must be at most 32 bytes")

    if not isinstance(password, str):
        raise WifiValidationError("Wi-Fi password is required")
    password_bytes = password.encode("utf-8")
    if not 8 <= len(password_bytes) <= 63:
        raise WifiValidationError("Wi-Fi password must be 8 to 63 bytes")
    if any(ord(character) < 32 or ord(character) == 127 for character in password):
        raise WifiValidationError("Wi-Fi password contains unsupported characters")
    return ssid


class MockWifiManager:
    """Simulate requests in memory without retaining submitted passwords."""

    mode = "mock"

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._last_requested_ssid: str | None = None
        self._last_requested_at: float | None = None

    def status(self) -> dict[str, Any]:
        with self._lock:
            last_requested_ssid = self._last_requested_ssid
            last_requested_at = self._last_requested_at
        return {
            "ok": True,
            "mode": self.mode,
            "stage": 1,
            "executed": False,
            "connected": None,
            "current_ssid": None,
            "internet": None,
            "last_requested_ssid": last_requested_ssid,
            "last_requested_at": last_requested_at,
            "message": "Simulation mode; live Wi-Fi access is not installed",
        }

    def scan(self) -> dict[str, Any]:
        return {
            "ok": True,
            "mode": self.mode,
            "stage": 1,
            "executed": False,
            "networks": [],
            "message": "Simulation mode; enter a network name manually",
        }

    def connect(self, ssid: str, password: str) -> dict[str, Any]:
        clean_ssid = validate_credentials(ssid, password)
        with self._lock:
            self._last_requested_ssid = clean_ssid
            self._last_requested_at = time.time()
        return {
            "ok": True,
            "mode": self.mode,
            "stage": 1,
            "executed": False,
            "ssid": clean_ssid,
            "message": "Wi-Fi request validated and simulated; network unchanged",
        }


class LiveWifiManager:
    """Invoke only the separately installed, sudo-allowlisted Wi-Fi helper."""

    mode = "live"

    def __init__(
        self,
        helper_path: str = "/usr/local/sbin/progress-claw-wifi",
        timeout_seconds: int = 90,
    ) -> None:
        self.helper_path = helper_path
        self.timeout_seconds = timeout_seconds

    def _request(self, action: str, payload: dict[str, str] | None = None) -> dict:
        if action not in {"status", "scan", "connect"}:
            raise ValueError("Unsupported Wi-Fi helper action")
        command = ["/usr/bin/sudo", "-n", self.helper_path, action]
        request_body = None if payload is None else json.dumps(payload)
        try:
            completed = subprocess.run(
                command,
                input=request_body,
                capture_output=True,
                text=True,
                check=True,
                timeout=self.timeout_seconds,
            )
            response = json.loads(completed.stdout)
        except (
            OSError,
            subprocess.SubprocessError,
            json.JSONDecodeError,
        ) as error:
            raise WifiControlError("Wi-Fi system helper failed") from error
        if (
            not isinstance(response, dict)
            or response.get("ok") is not True
            or response.get("mode") != "live"
        ):
            raise WifiControlError("Wi-Fi system helper returned an invalid response")
        return self._sanitize_response(action, response)

    @staticmethod
    def _safe_ssid(value: Any) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str) or not value:
            raise WifiControlError("Wi-Fi system helper returned an invalid response")
        if len(value.encode("utf-8")) > 32 or any(
            ord(character) < 32 or ord(character) == 127 for character in value
        ):
            raise WifiControlError("Wi-Fi system helper returned an invalid response")
        return value

    def _sanitize_response(self, action: str, response: dict) -> dict:
        message = response.get("message")
        if (
            not isinstance(message, str)
            or len(message) > 160
            or any(ord(character) < 32 or ord(character) == 127 for character in message)
        ):
            raise WifiControlError("Wi-Fi system helper returned an invalid response")
        result = {
            "ok": True,
            "mode": "live",
            "executed": response.get("executed") is True,
            "message": message,
        }
        if action in {"scan", "connect"} and not result["executed"]:
            raise WifiControlError("Wi-Fi system helper returned an invalid response")
        if action == "scan":
            networks = response.get("networks")
            if not isinstance(networks, list) or len(networks) > 100:
                raise WifiControlError("Wi-Fi system helper returned an invalid response")
            clean_networks = []
            for network in networks:
                if not isinstance(network, dict):
                    raise WifiControlError(
                        "Wi-Fi system helper returned an invalid response"
                    )
                signal = network.get("signal")
                security = network.get("security")
                if type(signal) is not int or not -200 <= signal <= 0:
                    raise WifiControlError(
                        "Wi-Fi system helper returned an invalid response"
                    )
                if security not in {"secured", "open"}:
                    raise WifiControlError(
                        "Wi-Fi system helper returned an invalid response"
                    )
                clean_ssid = self._safe_ssid(network.get("ssid"))
                if clean_ssid is None:
                    raise WifiControlError(
                        "Wi-Fi system helper returned an invalid response"
                    )
                clean_networks.append(
                    {
                        "ssid": clean_ssid,
                        "signal": signal,
                        "security": security,
                    }
                )
            result["networks"] = clean_networks
        else:
            connected = response.get("connected")
            if connected is not None and not isinstance(connected, bool):
                raise WifiControlError("Wi-Fi system helper returned an invalid response")
            result["connected"] = connected
            ssid_key = "ssid" if action == "connect" else "current_ssid"
            result[ssid_key] = self._safe_ssid(response.get(ssid_key))
            if (connected is True or action == "connect") and result[ssid_key] is None:
                raise WifiControlError("Wi-Fi system helper returned an invalid response")
            if action == "connect" and connected is not True:
                raise WifiControlError("Wi-Fi system helper returned an invalid response")
            if action == "status":
                internet = response.get("internet")
                if internet is not None and not isinstance(internet, bool):
                    raise WifiControlError(
                        "Wi-Fi system helper returned an invalid response"
                    )
                result["internet"] = internet
        return result

    def status(self) -> dict[str, Any]:
        return self._request("status")

    def scan(self) -> dict[str, Any]:
        return self._request("scan")

    def connect(self, ssid: str, password: str) -> dict[str, Any]:
        clean_ssid = validate_credentials(ssid, password)
        result = self._request(
            "connect", {"ssid": clean_ssid, "password": password}
        )
        if result["ssid"] != clean_ssid:
            raise WifiControlError("Wi-Fi system helper returned an invalid response")
        return result


def create_wifi_manager():
    mode = os.getenv("PROGRESS_CLAW_WIFI_MODE", "mock").strip().lower()
    if mode == "mock":
        return MockWifiManager()
    if mode == "live":
        helper_path = os.getenv(
            "PROGRESS_CLAW_WIFI_HELPER", "/usr/local/sbin/progress-claw-wifi"
        )
        return LiveWifiManager(helper_path=helper_path)
    raise ValueError("PROGRESS_CLAW_WIFI_MODE must be mock or live")


wifi_manager = create_wifi_manager()
