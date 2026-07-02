import os
import unittest

os.environ["CLAW_ARDUINO_MOCK"] = "1"

from dashboard.backend.app import app, runtime_controller


class DashboardRuntimeApiTest(unittest.TestCase):
    def setUp(self):
        runtime_controller.clear_emergency_for_tests()
        if runtime_controller.status()["running"]:
            runtime_controller.stop_play()
        self.client = app.test_client()

    def test_status_exposes_controller_state(self):
        response = self.client.get("/api/status")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIn("controller", payload)
        self.assertTrue(payload["controller"]["mock_arduino"])

    def test_health_endpoint_reports_runtime_dependencies(self):
        response = self.client.get("/api/health")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["status"], "ok")
        self.assertIn("controller", payload)
        self.assertIn("arduino", payload)
        self.assertIn("camera", payload)
        self.assertIsInstance(payload["uptime"], (float, int))

    def test_play_start_and_stop_endpoints_use_controller(self):
        start = self.client.post(
            "/api/play/start", json={"duration_seconds": 10, "test": True}
        )
        self.assertEqual(start.status_code, 200)
        self.assertTrue(start.get_json()["controller"]["running"])

        stop = self.client.post("/api/play/stop", json={"reason": "test"})
        self.assertEqual(stop.status_code, 200)
        self.assertFalse(stop.get_json()["controller"]["running"])

    def test_claw_power_endpoint_validates_payload(self):
        response = self.client.post("/api/claw/power", json={"power_percent": 75})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["controller"]["claw_power_percent"], 75)

        invalid = self.client.post("/api/claw/power", json={"power_percent": 5})
        self.assertEqual(invalid.status_code, 409)

    def test_api_validation_returns_bad_request_for_invalid_payloads(self):
        missing_power = self.client.post("/api/claw/power", json={})
        self.assertEqual(missing_power.status_code, 400)

        invalid_power = self.client.post(
            "/api/claw/power",
            json={"power_percent": "not-a-number"},
        )
        self.assertEqual(invalid_power.status_code, 409)

        missing_ai_count = self.client.post("/api/ai-count", json={})
        self.assertEqual(missing_ai_count.status_code, 400)

    def test_emergency_stop_endpoint_blocks_start(self):
        response = self.client.post("/api/emergency-stop", json={"reason": "test"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["controller"]["emergency_stopped"])

        blocked = self.client.post("/api/play/start", json={"duration_seconds": 10})
        self.assertEqual(blocked.status_code, 409)


if __name__ == "__main__":
    unittest.main()
