"""Environment configuration for the optional cloud integration."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency may not be installed yet
    load_dotenv = None


@dataclass(frozen=True)
class SupabaseConfig:
    url: str = ""
    key: str = ""
    machine_name: str = "Progress Claw Machine"
    table_name: str = "machine_status"
    retry_seconds: float = 30.0
    sync_interval_seconds: float = 60.0

    @classmethod
    def from_env(cls) -> "SupabaseConfig":
        if load_dotenv is not None:
            load_dotenv()
        else:
            _load_env_fallback()
        machine_name = os.getenv(
            "CLAW_MACHINE_NAME", "Progress Claw Machine"
        ).strip()
        table_name = os.getenv(
            "SUPABASE_MACHINE_STATUS_TABLE", "machine_status"
        ).strip()
        return cls(
            url=os.getenv("SUPABASE_URL", "").strip(),
            key=os.getenv("SUPABASE_KEY", "").strip(),
            machine_name=machine_name or "Progress Claw Machine",
            table_name=table_name or "machine_status",
            retry_seconds=_retry_seconds_from_env(),
            sync_interval_seconds=_positive_seconds_from_env(
                "SUPABASE_SYNC_INTERVAL_SECONDS", 60.0
            ),
        )

    @property
    def configured(self) -> bool:
        return bool(self.url and self.key)


def _retry_seconds_from_env() -> float:
    raw_value = os.getenv("SUPABASE_RETRY_SECONDS", "30").strip()
    try:
        retry_seconds = float(raw_value)
    except ValueError:
        return 30.0
    if not math.isfinite(retry_seconds):
        return 30.0
    return max(0.0, retry_seconds)


def _positive_seconds_from_env(name: str, default: float) -> float:
    raw_value = os.getenv(name, str(default)).strip()
    try:
        seconds = float(raw_value)
    except ValueError:
        return default
    if not math.isfinite(seconds) or seconds <= 0:
        return default
    return seconds


def _load_env_fallback(path: str = ".env") -> None:
    """Load simple KEY=VALUE entries when python-dotenv is unavailable."""

    try:
        with open(path, encoding="utf-8") as env_file:
            for raw_line in env_file:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                name, value = line.split("=", 1)
                name = name.strip()
                if not name or not name.replace("_", "").isalnum():
                    continue
                value = value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                    value = value[1:-1]
                os.environ.setdefault(name, value)
    except OSError:
        return
