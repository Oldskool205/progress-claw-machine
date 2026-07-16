import os
import unittest
from unittest.mock import Mock, patch

os.environ["CLAW_ARDUINO_MOCK"] = "1"

from dashboard.backend.app import app
from cloud.config import SupabaseConfig
from cloud.sync_service import CloudSyncService
from cloud.models import SyncResult
from cloud.monitoring_app import app as standalone_cloud_app


class CloudMonitoringTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_health_api_is_cached_and_exposes_no_credentials(self):
        response = self.client.get("/cloud/health")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIn("configured", payload)
        self.assertIn("connected", payload)
        self.assertIn("last_successful_sync", payload)
        serialized = response.get_data(as_text=True).lower()
        self.assertNotIn("supabase_key", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("database_password", serialized)

    def test_status_alias_returns_cloud_health(self):
        response = self.client.get("/cloud/status")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json()["machine_name"], "CLOUD-DIAGNOSTIC-TEST"
        )

    def test_monitoring_page_renders_diagnostic_controls(self):
        response = self.client.get("/cloud")
        page = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Supabase Cloud Monitor", page)
        self.assertIn("Test Connection", page)
        self.assertIn("Send Test Status", page)
        self.assertIn("Send Heartbeat", page)
        self.assertIn("Load Supabase Data", page)
        self.assertIn("Supabase Machine Data", page)
        self.assertIn("CLOUD-DIAGNOSTIC-TEST", page)

    def test_load_supabase_data_action_returns_cached_remote_row(self):
        service = Mock()
        remote = {
            "id": 1,
            "machine_name": "CLOUD-DIAGNOSTIC-TEST",
            "status": "diagnostic",
            "x_position": 1.0,
            "y_position": 2.0,
            "claw_power": 50,
            "online": False,
            "updated_at": "2026-07-15T09:00:00+00:00",
        }
        service.fetch_machine_status.return_value = SyncResult(
            True,
            "Machine status loaded from Supabase",
            data={"machine_status": remote},
        )
        service.health_snapshot.return_value = {
            "supabase_machine_status": remote
        }

        with patch("cloud.routes.cloud_service", service):
            response = self.client.post("/cloud/actions/load-supabase-data")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["ok"])
        self.assertEqual(
            response.get_json()["data"]["machine_status"]["claw_power"], 50
        )
        service.fetch_machine_status.assert_called_once_with()

    def test_cloud_unavailable_does_not_change_local_health(self):
        unavailable = CloudSyncService(SupabaseConfig())
        with patch("cloud.routes.cloud_service", unavailable):
            action = self.client.post("/cloud/actions/test-connection")
        local_health = self.client.get("/api/health")

        self.assertEqual(action.status_code, 200)
        self.assertFalse(action.get_json()["ok"])
        self.assertEqual(local_health.status_code, 200)
        self.assertEqual(local_health.get_json()["status"], "ok")

    def test_standalone_monitor_exposes_no_machine_control_routes(self):
        client = standalone_cloud_app.test_client()

        self.assertEqual(client.get("/").status_code, 302)
        self.assertEqual(client.get("/cloud").status_code, 200)
        self.assertEqual(client.post("/api/play/start", json={}).status_code, 404)


if __name__ == "__main__":
    unittest.main()
