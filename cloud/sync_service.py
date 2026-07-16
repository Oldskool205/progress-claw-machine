"""Non-blocking, failure-safe machine status synchronization."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import replace
from typing import Callable, Optional

from cloud.config import SupabaseConfig
from cloud.errors import missing_columns_from_error, sanitize_error
from cloud.health import CloudHealthState, CloudHealthTracker
from cloud.models import (
    EXPECTED_MACHINE_STATUS_COLUMNS,
    MachineStatus,
    SchemaResult,
    SyncResult,
    utc_timestamp,
)
from cloud.supabase_client import SupabaseClient


LOGGER = logging.getLogger("progress_claw.cloud")


class CloudSyncService:
    """Synchronize snapshots without becoming a machine runtime dependency."""

    def __init__(
        self,
        config: Optional[SupabaseConfig] = None,
        client: Optional[SupabaseClient] = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.config = config or SupabaseConfig.from_env()
        self.client = client or SupabaseClient(self.config)
        self._clock = clock
        self._retry_after = 0.0
        self._last_status: Optional[MachineStatus] = None
        self._lock = threading.RLock()
        self.health = CloudHealthTracker(
            CloudHealthState(
                enabled=True,
                configured=self.config.configured,
                connected=False,
                machine_name=self.config.machine_name,
                sync_interval_seconds=self.config.sync_interval_seconds,
            )
        )

    def connect(self) -> bool:
        with self._lock:
            if self.client.connected:
                return True
            if self._clock() < self._retry_after:
                return False
            self.health.update(last_connection_attempt=utc_timestamp())
            if self.client.connect():
                self._retry_after = 0.0
                self.health.success(last_successful_connection=utc_timestamp())
                return True
            self._schedule_retry(self.client.last_error_category or "cloud_error")
            return False

    def validate_schema(self) -> SchemaResult:
        """Perform an explicit table/column query only when diagnostics request it."""

        if not self.connect():
            category = self.health.snapshot()["last_error"] or "cloud_unavailable"
            return SchemaResult(
                False,
                "Cloud connection unavailable",
                error_category=category,
            )
        try:
            columns = ",".join(EXPECTED_MACHINE_STATUS_COLUMNS)
            (
                self.client.client.table(self.config.table_name)
                .select(columns)
                .limit(1)
                .execute()
            )
            self.health.success(last_successful_connection=utc_timestamp())
            return SchemaResult(True, "machine_status schema is accessible")
        except Exception as error:
            category = sanitize_error(error)
            missing_columns = missing_columns_from_error(
                error, EXPECTED_MACHINE_STATUS_COLUMNS
            )
            self.client.disconnect()
            self._schedule_retry(category)
            return SchemaResult(
                False,
                "machine_status schema validation failed",
                missing_columns=missing_columns,
                error_category=category,
            )

    def update_machine_status(self, machine_status: MachineStatus) -> SyncResult:
        with self._lock:
            self._last_status = machine_status
            self.health.update(
                last_sync_attempt=utc_timestamp(),
                current_machine_status=machine_status.to_dict(),
            )
            if not self.connect():
                return SyncResult(False, "Cloud unavailable; local operation continues", True)
            try:
                table = self.client.client.table(self.config.table_name)
                response = (
                    table.update(machine_status.to_dict())
                    .eq("machine_name", machine_status.machine_name)
                    .execute()
                )
                if not getattr(response, "data", None):
                    response = table.insert(machine_status.to_dict()).execute()
                self._retry_after = 0.0
                self.health.success(last_successful_sync=utc_timestamp())
                LOGGER.info(
                    "[Cloud] Sync Success",
                    extra={
                        "event": "cloud_sync_success",
                        "machine_name": machine_status.machine_name,
                    },
                )
                return SyncResult(
                    True,
                    "Machine status synchronized",
                    data={"machine_name": machine_status.machine_name},
                )
            except Exception as error:
                self.client.disconnect()
                self._schedule_retry(sanitize_error(error))
                return SyncResult(False, "Cloud sync failed; local operation continues", True)

    def fetch_machine_status(self) -> SyncResult:
        """Explicitly read one configured machine row for diagnostics."""

        with self._lock:
            if not self.connect():
                return SyncResult(
                    False,
                    "Cloud unavailable; local operation continues",
                    True,
                )
            try:
                columns = ",".join(EXPECTED_MACHINE_STATUS_COLUMNS)
                response = (
                    self.client.client.table(self.config.table_name)
                    .select(columns)
                    .eq("machine_name", self.config.machine_name)
                    .limit(1)
                    .execute()
                )
                rows = getattr(response, "data", None) or []
                read_at = utc_timestamp()
                if not rows:
                    self.health.update(
                        connected=True,
                        last_supabase_read=read_at,
                        last_error="record_not_found",
                        supabase_machine_status=None,
                    )
                    return SyncResult(False, "Machine record not found")
                source = rows[0]
                machine_status = {
                    column: source.get(column)
                    for column in EXPECTED_MACHINE_STATUS_COLUMNS
                }
                self.health.success(
                    last_supabase_read=read_at,
                    supabase_machine_status=machine_status,
                )
                return SyncResult(
                    True,
                    "Machine status loaded from Supabase",
                    data={"machine_status": machine_status},
                )
            except Exception as error:
                self.client.disconnect()
                self._schedule_retry(sanitize_error(error))
                return SyncResult(
                    False,
                    "Cloud read failed; local operation continues",
                    True,
                )

    def heartbeat(self) -> SyncResult:
        with self._lock:
            status = self._current_status(online=True)
            result = self.update_machine_status(
                replace(status, online=True, updated_at=utc_timestamp())
            )
            if result.ok:
                self.health.update(last_heartbeat=utc_timestamp())
            return result

    def sync_game_status(
        self,
        status: str,
        x_position: float = 0.0,
        y_position: float = 0.0,
        claw_power: int = 0,
    ) -> SyncResult:
        machine_status = MachineStatus(
            machine_name=self.config.machine_name,
            status=status,
            x_position=x_position,
            y_position=y_position,
            claw_power=claw_power,
            online=True,
        )
        return self.update_machine_status(machine_status)

    def sync_online_state(self, online: bool) -> SyncResult:
        with self._lock:
            status = self._current_status(online=online)
            return self.update_machine_status(
                replace(status, online=online, updated_at=utc_timestamp())
            )

    def _current_status(self, online: bool) -> MachineStatus:
        if self._last_status is not None:
            return self._last_status
        return MachineStatus(
            machine_name=self.config.machine_name,
            status="unknown",
            online=online,
        )

    def health_snapshot(self) -> dict:
        return self.health.snapshot()

    def _schedule_retry(self, error_category: Optional[str] = None) -> None:
        self._retry_after = self._clock() + max(0.0, self.config.retry_seconds)
        category = error_category or "cloud_unavailable"
        self.health.failure(category)
        LOGGER.warning(
            "[Cloud] Retrying",
            extra={
                "event": "cloud_retrying",
                "retry_seconds": self.config.retry_seconds,
                "error_category": category,
            },
        )


_default_service: Optional[CloudSyncService] = None


def _service() -> CloudSyncService:
    global _default_service
    if _default_service is None:
        _default_service = CloudSyncService()
    return _default_service


def connect() -> bool:
    return _service().connect()


def update_machine_status(machine_status: MachineStatus) -> SyncResult:
    return _service().update_machine_status(machine_status)


def heartbeat() -> SyncResult:
    return _service().heartbeat()


def sync_game_status(
    status: str,
    x_position: float = 0.0,
    y_position: float = 0.0,
    claw_power: int = 0,
) -> SyncResult:
    return _service().sync_game_status(status, x_position, y_position, claw_power)


def sync_online_state(online: bool) -> SyncResult:
    return _service().sync_online_state(online)
