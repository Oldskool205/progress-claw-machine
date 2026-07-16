import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from cloud.config import SupabaseConfig
from cloud.models import MachineStatus
from cloud.supabase_client import SupabaseClient
from cloud.sync_service import CloudSyncService


class FakeQuery:
    def __init__(self, update_data=None, insert_data=None, error=None):
        self.update_data = update_data
        self.insert_data = insert_data
        self.error = error
        self.updated_payload = None
        self.inserted_payload = None
        self.filter = None
        self.operation = None

    def update(self, payload):
        self.operation = "update"
        self.updated_payload = payload
        return self

    def insert(self, payload):
        self.operation = "insert"
        self.inserted_payload = payload
        return self

    def eq(self, column, value):
        self.filter = (column, value)
        return self

    def execute(self):
        if self.error:
            raise self.error
        data = self.update_data if self.operation == "update" else self.insert_data
        return SimpleNamespace(data=data)


class FakeSdkClient:
    def __init__(self, query):
        self.query = query
        self.table_name = None

    def table(self, table_name):
        self.table_name = table_name
        return self.query


class CloudSyncServiceTest(unittest.TestCase):
    def setUp(self):
        self.config = SupabaseConfig(
            url="https://example.supabase.co",
            key="test-key",
            machine_name="Test Claw",
            retry_seconds=30,
        )

    def service_with_query(self, query, clock=lambda: 100.0):
        sdk_client = FakeSdkClient(query)
        client = SupabaseClient(
            self.config, client_factory=lambda url, key: sdk_client
        )
        return CloudSyncService(self.config, client, clock=clock), sdk_client

    def test_connect_uses_configured_supabase_client(self):
        factory = Mock(return_value=FakeSdkClient(FakeQuery()))
        client = SupabaseClient(self.config, client_factory=factory)
        service = CloudSyncService(self.config, client)

        self.assertTrue(service.connect())
        factory.assert_called_once_with(self.config.url, self.config.key)

    def test_sync_updates_existing_machine_row(self):
        query = FakeQuery(update_data=[{"id": 1}])
        service, sdk_client = self.service_with_query(query)
        machine_status = MachineStatus(
            machine_name="Test Claw",
            status="ready",
            x_position=12.0,
            y_position=8.0,
            claw_power=70,
            online=True,
        )

        result = service.update_machine_status(machine_status)

        self.assertTrue(result.ok)
        self.assertEqual(sdk_client.table_name, "machine_status")
        self.assertEqual(query.filter, ("machine_name", "Test Claw"))
        self.assertEqual(query.updated_payload, machine_status.to_dict())
        self.assertIsNone(query.inserted_payload)

    def test_sync_inserts_machine_when_update_finds_no_row(self):
        query = FakeQuery(update_data=[], insert_data=[{"id": 1}])
        service, _ = self.service_with_query(query)

        result = service.sync_game_status("running", 2.0, 3.0, 80)

        self.assertTrue(result.ok)
        self.assertEqual(query.inserted_payload["status"], "running")
        self.assertEqual(query.inserted_payload["claw_power"], 80)

    def test_cloud_failure_returns_without_raising_and_schedules_retry(self):
        query = FakeQuery(error=ConnectionError("offline"))
        service, _ = self.service_with_query(query)

        result = service.sync_game_status("ready")

        self.assertFalse(result.ok)
        self.assertTrue(result.retrying)
        self.assertFalse(service.client.connected)

    def test_unconfigured_cloud_does_not_attempt_connection(self):
        factory = Mock()
        config = SupabaseConfig(retry_seconds=30)
        client = SupabaseClient(config, client_factory=factory)
        service = CloudSyncService(config, client, clock=lambda: 100.0)

        result = service.sync_game_status("ready")

        self.assertFalse(result.ok)
        self.assertTrue(result.retrying)
        factory.assert_not_called()

    def test_retry_delay_prevents_repeated_connection_attempts(self):
        now = [100.0]
        factory = Mock(side_effect=ConnectionError("offline"))
        client = SupabaseClient(self.config, client_factory=factory)
        service = CloudSyncService(self.config, client, clock=lambda: now[0])

        self.assertFalse(service.connect())
        self.assertFalse(service.connect())
        self.assertEqual(factory.call_count, 1)
        now[0] = 131.0
        self.assertFalse(service.connect())
        self.assertEqual(factory.call_count, 2)

    def test_heartbeat_and_offline_sync_preserve_latest_machine_values(self):
        query = FakeQuery(update_data=[{"id": 1}])
        service, _ = self.service_with_query(query)
        service.sync_game_status("running", 4.0, 5.0, 90)

        heartbeat = service.heartbeat()
        offline = service.sync_online_state(False)

        self.assertTrue(heartbeat.ok)
        self.assertTrue(offline.ok)
        self.assertEqual(query.updated_payload["status"], "running")
        self.assertEqual(query.updated_payload["x_position"], 4.0)
        self.assertFalse(query.updated_payload["online"])


if __name__ == "__main__":
    unittest.main()
