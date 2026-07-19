import os
import unittest
from unittest.mock import patch

os.environ["CLAW_ARDUINO_MOCK"] = "1"

from controller.safety.validator import SafetyError
from dashboard.backend.app import app, runtime_controller
from dashboard.backend.dashboard_state import dashboard_state, state


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

    def test_dashboard_shows_cloud_status_without_hacker_mode(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        self.assertIn("Supabase", page)
        self.assertIn('href="/cloud"', page)
        self.assertNotIn("Hacker", page)
        self.assertEqual(self.client.post("/api/hacker", json={}).status_code, 404)

    def test_dashboard_admin_preview_has_no_active_system_actions(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        self.assertIn('id="adminTrigger"', page)
        self.assertIn('id="dashboardLogo"', page)
        self.assertIn("returnToStartScreen", page)
        self.assertIn('displayPhase = "stopped"', page)
        self.assertIn('showTimeUp(current.play_ends_at)', page)
        self.assertIn('speak("Time up")', page)
        self.assertIn("GRABBER_START_DISPLAY_SECONDS = 1", page)
        self.assertIn("READY_DISPLAY_SECONDS = 2", page)
        self.assertIn("PREPARING_DISPLAY_SECONDS = 1", page)
        self.assertNotIn('displayText = "• • •"', page)
        self.assertIn("setCountdownDisplay(displayPhase, displayText)", page)
        self.assertIn('displayPhase = "countdown-preview"', page)
        self.assertIn("displayText = remaining", page)
        self.assertIn("playStartPending = true", page)
        self.assertIn('setCountdownDisplay("preparing", "PREPARING…")', page)
        self.assertIn("startupVisualStartedAt = Date.now() / 1000", page)
        self.assertNotIn("message-enter", page)
        self.assertIn("STARTUP_DISPLAY_TOTAL_SECONDS", page)
        self.assertIn("Date.now() / 1000 - startupVisualStartedAt", page)
        self.assertIn("TIME_UP_DISPLAY_MS = 3000", page)
        self.assertIn('"TRY AGAIN!"', page)
        self.assertIn("TRY_AGAIN_DISPLAY_MS = 3000", page)
        self.assertIn('"REGISTER PLAYER"', page)
        self.assertIn('id="adminModal"', page)
        self.assertIn("Checking administrator authentication", page)
        self.assertIn(
            "Press and hold the Steaming Club logo for administrator menu", page
        )
        self.assertEqual(page.count('type="button" data-admin-action'), 6)
        self.assertIn("/api/admin/status", page)
        self.assertIn("/api/admin/login", page)
        self.assertIn("/api/admin/logout", page)
        self.assertIn("/api/admin/maintenance", page)
        self.assertIn("/api/admin/stop-game", page)
        self.assertIn("/api/admin/exit-kiosk", page)
        self.assertIn("/api/admin/restart-kiosk", page)
        self.assertIn("/api/admin/power/${action}", page)
        self.assertNotIn("/api/admin/shutdown", page)
        self.assertNotIn("/api/admin/reboot", page)
        self.assertNotIn("systemctl", page)
        self.assertNotIn("shutdown -", page)

    def test_service_worker_is_available_without_browser_caching(self):
        response = self.client.get("/service-worker.js")
        self.addCleanup(response.close)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/javascript")
        self.assertIn("no-cache", response.headers["Cache-Control"])

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

    def test_dashboard_play_failure_does_not_consume_credit_or_player(self):
        original_state = {
            key: state[key]
            for key in (
                "credits",
                "plays_today",
                "last_play",
                "player_photo_ready",
                "current_player_name",
                "players",
                "play_mode",
                "countdown_starts_at",
                "play_ends_at",
            )
        }
        self.addCleanup(state.update, original_state)
        state.update(
            credits=1,
            plays_today=4,
            last_play="12:34:56",
            player_photo_ready=True,
            current_player_name="Test Player",
            players=[{"name": "Test Player", "status": "Ready"}],
            play_mode=None,
            countdown_starts_at=None,
            play_ends_at=None,
        )

        with patch(
            "dashboard.backend.routes_api.trigger_play",
            side_effect=SafetyError("Machine could not start play: GPIO failure"),
        ):
            response = self.client.post("/api/play", json={})

        self.assertEqual(response.status_code, 409)
        self.assertEqual(state["credits"], 1)
        self.assertEqual(state["plays_today"], 4)
        self.assertEqual(state["last_play"], "12:34:56")
        self.assertTrue(state["player_photo_ready"])
        self.assertEqual(state["current_player_name"], "Test Player")
        self.assertEqual(state["players"][0]["status"], "Ready")
        self.assertIsNone(state["play_mode"])

    def test_dashboard_countdown_end_matches_controller_stop_time(self):
        original_state = dict(state)
        self.addCleanup(state.update, original_state)
        self.addCleanup(state.clear)
        state.update(
            credits=1,
            player_photo_ready=True,
            current_player_name="Timer Test",
            players=[{"name": "Timer Test", "status": "Ready"}],
            play_mode=None,
            play_duration=10,
        )

        response = self.client.post("/api/play", json={"test": True})

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(
            payload["play_ends_at"], payload["controller"]["play_ends_at"]
        )
        self.assertEqual(payload["play_ends_at"] - payload["countdown_starts_at"], 10)
        self.assertEqual(payload["ready_duration"], 3)
        self.assertEqual(payload["grabber_start_duration"], 1)

    def test_natural_controller_completion_clears_dashboard_play_state(self):
        original_state = dict(state)
        self.addCleanup(state.update, original_state)
        self.addCleanup(state.clear)
        state.update(
            play_mode="test",
            countdown_starts_at=100,
            play_ends_at=110,
            player_photo_ready=False,
        )
        controller_status = runtime_controller.status()
        controller_status.update(running=False, play_mode=None, play_ends_at=None)

        with patch.object(runtime_controller, "status", return_value=controller_status):
            payload = dashboard_state()

        self.assertIsNone(payload["play_mode"])
        self.assertIsNone(payload["countdown_starts_at"])
        self.assertIsNone(payload["play_ends_at"])

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
