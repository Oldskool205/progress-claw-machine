"""Sanitize cloud failures into safe operator-facing categories."""

from __future__ import annotations

import socket
from typing import Iterable


def sanitize_error(error: BaseException) -> str:
    """Return a stable category without retaining exception details or secrets."""

    name = type(error).__name__.lower()
    message = str(error).lower()
    if isinstance(error, (TimeoutError, socket.timeout)) or "timeout" in name:
        return "timeout"
    if any(token in message for token in ("jwt", "unauthorized", "invalid api key")):
        return "invalid_credentials"
    if any(token in message for token in ("row-level security", "rls", "permission")):
        return "rls_permission_denied"
    if any(token in message for token in ("column", "42703", "schema cache")):
        return "schema_mismatch"
    if any(token in message for token in ("does not exist", "not found", "42p01")):
        return "missing_table"
    if isinstance(error, (ConnectionError, OSError)) or any(
        token in message for token in ("network", "connection", "dns")
    ):
        return "network_error"
    return "cloud_error"


def missing_columns_from_error(
    error: BaseException, expected_columns: Iterable[str]
) -> tuple[str, ...]:
    message = str(error).lower()
    return tuple(column for column in expected_columns if column.lower() in message)
