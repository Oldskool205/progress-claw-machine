"""Optional Supabase cloud synchronization for Progress Claw OS."""

from cloud.models import MachineStatus, SyncResult
from cloud.sync_service import CloudSyncService

__all__ = ["CloudSyncService", "MachineStatus", "SyncResult"]
