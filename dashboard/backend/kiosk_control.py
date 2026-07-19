"""Filesystem signal used to exit only the independently managed kiosk browser."""

from __future__ import annotations

import os
from pathlib import Path


def default_runtime_dir() -> Path:
    base = os.getenv("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}"
    return Path(base) / "progress-claw"


def exit_request_path() -> Path:
    configured = os.getenv("PROGRESS_CLAW_KIOSK_EXIT_FILE")
    return Path(configured) if configured else default_runtime_dir() / "kiosk-exit-request"


def request(action: str) -> Path:
    if action not in {"exit", "restart"}:
        raise ValueError("Unsupported kiosk request")
    request_path = exit_request_path()
    request_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    request_path.parent.chmod(0o700)
    request_path.write_text(f"{action}\n", encoding="utf-8")
    request_path.chmod(0o600)
    return request_path


def request_exit() -> Path:
    return request("exit")


def request_restart() -> Path:
    return request("restart")
