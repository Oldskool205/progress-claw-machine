"""Thin, failure-safe wrapper around the official Supabase Python SDK."""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from cloud.config import SupabaseConfig
from cloud.errors import sanitize_error

try:
    from supabase import Client, create_client
except ImportError:  # pragma: no cover - depends on deployment environment
    Client = Any
    create_client = None


LOGGER = logging.getLogger("progress_claw.cloud")


class SupabaseClient:
    def __init__(
        self,
        config: SupabaseConfig,
        client_factory: Optional[Callable[[str, str], Any]] = None,
    ) -> None:
        self.config = config
        self._client_factory = client_factory or create_client
        self._client: Optional[Client] = None
        self.last_error_category: Optional[str] = None

    @property
    def connected(self) -> bool:
        return self._client is not None

    @property
    def client(self) -> Optional[Client]:
        return self._client

    def connect(self) -> bool:
        if self.connected:
            return True
        if not self.config.configured:
            self.last_error_category = "not_configured"
            LOGGER.warning(
                "[Cloud] Disconnected",
                extra={"event": "cloud_disconnected", "reason": "not_configured"},
            )
            return False
        if self._client_factory is None:
            self.last_error_category = "sdk_unavailable"
            LOGGER.warning(
                "[Cloud] Disconnected",
                extra={"event": "cloud_disconnected", "reason": "sdk_unavailable"},
            )
            return False
        try:
            self._client = self._client_factory(self.config.url, self.config.key)
        except Exception as error:
            self._client = None
            self.last_error_category = sanitize_error(error)
            LOGGER.warning(
                "[Cloud] Disconnected",
                extra={
                    "event": "cloud_disconnected",
                    "error_category": self.last_error_category,
                },
            )
            return False
        self.last_error_category = None
        LOGGER.info("[Cloud] Connected", extra={"event": "cloud_connected"})
        return True

    def disconnect(self) -> None:
        self._client = None
        LOGGER.info("[Cloud] Disconnected", extra={"event": "cloud_disconnected"})
