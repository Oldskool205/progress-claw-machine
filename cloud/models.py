"""Data contracts owned by the cloud integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


EXPECTED_MACHINE_STATUS_COLUMNS = (
    "id",
    "machine_name",
    "status",
    "x_position",
    "y_position",
    "claw_power",
    "online",
    "updated_at",
)


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class MachineStatus:
    machine_name: str
    status: str
    x_position: float = 0.0
    y_position: float = 0.0
    claw_power: int = 0
    online: bool = True
    updated_at: str = field(default_factory=utc_timestamp)

    def to_dict(self) -> dict[str, Any]:
        return {
            "machine_name": self.machine_name,
            "status": self.status,
            "x_position": self.x_position,
            "y_position": self.y_position,
            "claw_power": self.claw_power,
            "online": self.online,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class SyncResult:
    ok: bool
    message: str
    retrying: bool = False
    data: Optional[dict[str, Any]] = None


@dataclass(frozen=True)
class SchemaResult:
    ok: bool
    message: str
    missing_columns: tuple[str, ...] = ()
    error_category: Optional[str] = None
