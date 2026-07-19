"""Non-privileged Phase 5 power-action simulator."""

from __future__ import annotations

import os
import subprocess
import time


ALLOWED_ACTIONS = {"reboot", "poweroff"}


class MockSystemPowerExecutor:
    """Record a validated request without invoking an operating-system command."""

    mode = "mock"

    def __init__(self) -> None:
        self.last_request = None

    def request(self, action: str) -> dict:
        if action not in ALLOWED_ACTIONS:
            raise ValueError("Unsupported system power action")
        self.last_request = {"action": action, "requested_at": time.time()}
        return {"ok": True, "action": action, "mode": self.mode, "executed": False}


class LiveSystemPowerExecutor:
    """Invoke only the separately installed, sudo-allowlisted power helper."""

    mode = "live"

    def __init__(self, helper_path: str) -> None:
        self.helper_path = helper_path

    def request(self, action: str) -> dict:
        if action not in ALLOWED_ACTIONS:
            raise ValueError("Unsupported system power action")
        subprocess.run(
            ["/usr/bin/sudo", "-n", self.helper_path, action],
            check=True,
            timeout=10,
        )
        return {"ok": True, "action": action, "mode": self.mode, "executed": True}


def create_power_executor():
    mode = os.getenv("PROGRESS_CLAW_POWER_MODE", "mock").strip().lower()
    if mode == "mock":
        return MockSystemPowerExecutor()
    if mode == "live":
        helper_path = os.getenv(
            "PROGRESS_CLAW_POWER_HELPER", "/usr/local/sbin/progress-claw-power"
        )
        return LiveSystemPowerExecutor(helper_path)
    raise ValueError("PROGRESS_CLAW_POWER_MODE must be mock or live")


power_executor = create_power_executor()
