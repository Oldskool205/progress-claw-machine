import unittest
from types import SimpleNamespace

from cloud.config import SupabaseConfig
from cloud.errors import sanitize_error
from cloud.supabase_client import SupabaseClient
from cloud.sync_service import CloudSyncService


class ObservableQuery:
    def __init__(self, error=None, update_data=None, select_data=None):
        self.error = error
        self.update_data = [{"id": 1}] if update_data is None else update_data
        self.select_data = [] if select_data is None else select_data
        self.operation = None
        self.calls = 0

    def select(self, columns):
        self.operation = "select"
        return self

    def limit(self, count):
        return self

    def update(self, payload):
        self.operation = "update"
        return self

    def insert(self, payload):
        self.operation = "insert"
        return self

    def eq(self, column, value):
        return self

    def execute(self):
        self.calls += 1
        if self.error:
            raise self.error
        data = self.select_data if self.operation == "select" else self.update_data
        return SimpleNamespace(data=data)


class ObservableSdkClient:
    def __init__(self, query):
        self.query = query

    def table(self, table_name):
        return self.query


def service_for(query):
    config = SupabaseConfig(
        url="https://example.supabase.co",
        key="TOP-SECRET-KEY",
        machine_name="CLOUD-DIAGNOSTIC-TEST",
        retry_seconds=0,
    )
    sdk = ObservableSdkClient(query)
    client = SupabaseClient(config, client_factory=lambda url, key: sdk)
    return CloudSyncService(config, client)


class CloudObservabilityTest(unittest.TestCase):
    def test_schema_validation_updates_cached_connection_health(self):
        query = ObservableQuery()
        service = service_for(query)

        result = service.validate_schema()
        health = service.health_snapshot()

        self.assertTrue(result.ok)
        self.assertTrue(health["connected"])
        self.assertIsNotNone(health["last_connection_attempt"])
        self.assertIsNotNone(health["last_successful_connection"])
        self.assertEqual(query.calls, 1)

    def test_schema_failure_reports_missing_column_without_raw_error(self):
        query = ObservableQuery(
            error=RuntimeError("column x_position does not exist; TOP-SECRET-KEY")
        )
        service = service_for(query)

        result = service.validate_schema()
        health = service.health_snapshot()

        self.assertFalse(result.ok)
        self.assertEqual(result.error_category, "schema_mismatch")
        self.assertEqual(result.missing_columns, ("x_position",))
        self.assertNotIn("TOP-SECRET-KEY", str(result))
        self.assertNotIn("TOP-SECRET-KEY", str(health))

    def test_heartbeat_success_and_failure_are_observable(self):
        success_service = service_for(ObservableQuery())
        success = success_service.heartbeat()

        failure_service = service_for(ObservableQuery(error=TimeoutError("secret")))
        failure = failure_service.heartbeat()

        self.assertTrue(success.ok)
        self.assertIsNotNone(success_service.health_snapshot()["last_heartbeat"])
        self.assertFalse(failure.ok)
        self.assertIsNone(failure_service.health_snapshot()["last_heartbeat"])
        self.assertEqual(failure_service.health_snapshot()["last_error"], "timeout")

    def test_error_sanitizer_never_returns_exception_payload(self):
        secret = "TOP-SECRET-KEY"
        category = sanitize_error(RuntimeError(f"unauthorized JWT {secret}"))

        self.assertEqual(category, "invalid_credentials")
        self.assertNotIn(secret, category)

    def test_error_sanitizer_distinguishes_operational_failures(self):
        cases = {
            RuntimeError("relation machine_status does not exist"): "missing_table",
            RuntimeError("row-level security policy rejected row"): "rls_permission_denied",
            ConnectionError("network down"): "network_error",
            TimeoutError("request timeout"): "timeout",
        }

        for error, expected in cases.items():
            with self.subTest(expected=expected):
                self.assertEqual(sanitize_error(error), expected)

    def test_health_snapshot_is_cached_and_makes_no_cloud_query(self):
        query = ObservableQuery()
        service = service_for(query)

        first = service.health_snapshot()
        second = service.health_snapshot()

        self.assertEqual(first, second)
        self.assertEqual(query.calls, 0)

    def test_explicit_fetch_caches_whitelisted_supabase_machine_data(self):
        remote = {
            "id": 1,
            "machine_name": "CLOUD-DIAGNOSTIC-TEST",
            "status": "diagnostic",
            "x_position": 1.0,
            "y_position": 2.0,
            "claw_power": 50,
            "online": False,
            "updated_at": "2026-07-15T09:00:00+00:00",
            "unexpected": "not exposed",
        }
        query = ObservableQuery(select_data=[remote])
        service = service_for(query)

        result = service.fetch_machine_status()
        cached = service.health_snapshot()["supabase_machine_status"]

        self.assertTrue(result.ok)
        self.assertEqual(cached["machine_name"], "CLOUD-DIAGNOSTIC-TEST")
        self.assertFalse(cached["online"])
        self.assertNotIn("unexpected", cached)
        self.assertIsNotNone(service.health_snapshot()["last_supabase_read"])

    def test_explicit_fetch_handles_missing_record_and_cloud_failure(self):
        missing_service = service_for(ObservableQuery(select_data=[]))
        missing = missing_service.fetch_machine_status()

        failed_service = service_for(
            ObservableQuery(error=ConnectionError("offline"))
        )
        failed = failed_service.fetch_machine_status()

        self.assertFalse(missing.ok)
        self.assertEqual(
            missing_service.health_snapshot()["last_error"], "record_not_found"
        )
        self.assertFalse(failed.ok)
        self.assertEqual(
            failed_service.health_snapshot()["last_error"], "network_error"
        )


if __name__ == "__main__":
    unittest.main()
