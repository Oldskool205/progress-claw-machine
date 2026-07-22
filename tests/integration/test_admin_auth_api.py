import os
import unittest
from unittest.mock import patch

os.environ["CLAW_ARDUINO_MOCK"] = "1"

from dashboard.backend import admin_auth
from dashboard.backend.app import app
from dashboard.backend.dashboard_state import state


class AdminAuthApiTest(unittest.TestCase):
    def setUp(self):
        self.original_secret_key = app.secret_key
        self.original_pin = app.config.get("ADMIN_PIN")
        self.original_session_seconds = app.config.get("ADMIN_SESSION_SECONDS")
        self.original_maintenance_mode = state["maintenance_mode"]
        self.original_play_mode = state["play_mode"]
        app.config.update(TESTING=True, ADMIN_PIN="2468", ADMIN_SESSION_SECONDS=300)
        app.secret_key = "test-only-secret-key"
        admin_auth.clear_attempts_for_tests()
        self.client = app.test_client()

    def tearDown(self):
        admin_auth.clear_attempts_for_tests()
        app.secret_key = self.original_secret_key
        app.config["ADMIN_PIN"] = self.original_pin
        app.config["ADMIN_SESSION_SECONDS"] = self.original_session_seconds
        state["maintenance_mode"] = self.original_maintenance_mode
        state["play_mode"] = self.original_play_mode

    def test_login_creates_short_lived_session_and_logout_clears_it(self):
        initial = self.client.get("/api/admin/status").get_json()
        self.assertTrue(initial["configured"])
        self.assertFalse(initial["authenticated"])
        self.assertIn(initial["power_mode"], {"mock", "live"})

        login = self.client.post("/api/admin/login", json={"pin": "2468"})
        self.assertEqual(login.status_code, 200)
        self.assertTrue(login.get_json()["authenticated"])
        self.assertLessEqual(login.get_json()["expires_in"], 300)

        logout = self.client.post("/api/admin/logout", json={})
        self.assertEqual(logout.status_code, 200)
        self.assertFalse(logout.get_json()["authenticated"])

    def test_login_rejects_invalid_pin_without_echoing_it(self):
        response = self.client.post("/api/admin/login", json={"pin": "1111"})

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()["error"], "Incorrect PIN")
        self.assertNotIn("1111", response.get_data(as_text=True))

    def test_login_validates_pin_format(self):
        for pin in (None, "12", "abcd", "123456789"):
            response = self.client.post("/api/admin/login", json={"pin": pin})
            self.assertEqual(response.status_code, 400)

    def test_login_rate_limits_repeated_failures(self):
        for _ in range(admin_auth.MAX_ATTEMPTS):
            response = self.client.post("/api/admin/login", json={"pin": "1111"})
            self.assertEqual(response.status_code, 401)

        limited = self.client.post("/api/admin/login", json={"pin": "2468"})
        self.assertEqual(limited.status_code, 429)
        self.assertGreater(limited.get_json()["retry_after"], 0)

    def test_authentication_is_unavailable_without_pin_or_secret(self):
        app.config["ADMIN_PIN"] = None
        status = self.client.get("/api/admin/status")
        self.assertEqual(status.status_code, 200)
        self.assertFalse(status.get_json()["configured"])
        response = self.client.post("/api/admin/login", json={"pin": "2468"})
        self.assertEqual(response.status_code, 503)

        app.config["ADMIN_PIN"] = "2468"
        app.secret_key = None
        status = self.client.get("/api/admin/status")
        self.assertEqual(status.status_code, 200)
        self.assertFalse(status.get_json()["configured"])
        response = self.client.post("/api/admin/login", json={"pin": "2468"})
        self.assertEqual(response.status_code, 503)

    def test_admin_routes_expose_no_system_actions(self):
        for path in (
            "/api/admin/restart",
            "/api/admin/reboot",
            "/api/admin/shutdown",
        ):
            self.assertEqual(self.client.post(path, json={}).status_code, 404)

    def test_exit_kiosk_requires_auth_confirmation_and_idle_machine(self):
        unauthorized = self.client.post(
            "/api/admin/exit-kiosk", json={"confirm": "EXIT_KIOSK"}
        )
        self.assertEqual(unauthorized.status_code, 401)

        self.client.post("/api/admin/login", json={"pin": "2468"})
        unconfirmed = self.client.post("/api/admin/exit-kiosk", json={})
        self.assertEqual(unconfirmed.status_code, 400)

        state["play_mode"] = "test"
        running = self.client.post(
            "/api/admin/exit-kiosk", json={"confirm": "EXIT_KIOSK"}
        )
        self.assertEqual(running.status_code, 409)

        state["play_mode"] = None
        with patch("dashboard.backend.routes_admin.kiosk_control.request_exit") as request_exit:
            response = self.client.post(
                "/api/admin/exit-kiosk", json={"confirm": "EXIT_KIOSK"}
            )
        self.assertEqual(response.status_code, 200)
        request_exit.assert_called_once_with()

    def test_restart_kiosk_requires_auth_confirmation_and_idle_machine(self):
        unauthorized = self.client.post(
            "/api/admin/restart-kiosk", json={"confirm": "RESTART_KIOSK"}
        )
        self.assertEqual(unauthorized.status_code, 401)

        self.client.post("/api/admin/login", json={"pin": "2468"})
        unconfirmed = self.client.post("/api/admin/restart-kiosk", json={})
        self.assertEqual(unconfirmed.status_code, 400)

        state["play_mode"] = "test"
        running = self.client.post(
            "/api/admin/restart-kiosk", json={"confirm": "RESTART_KIOSK"}
        )
        self.assertEqual(running.status_code, 409)

        state["play_mode"] = None
        with patch("dashboard.backend.routes_admin.kiosk_control.request_restart") as request_restart:
            response = self.client.post(
                "/api/admin/restart-kiosk", json={"confirm": "RESTART_KIOSK"}
            )
        self.assertEqual(response.status_code, 200)
        request_restart.assert_called_once_with()

    def test_power_simulation_requires_auth_idle_machine_and_maintenance(self):
        unauthorized = self.client.post(
            "/api/admin/power/reboot", json={"confirm": "REBOOT_RASPBERRY_PI"}
        )
        self.assertEqual(unauthorized.status_code, 401)

        self.client.post("/api/admin/login", json={"pin": "2468"})
        unconfirmed = self.client.post("/api/admin/power/reboot", json={})
        self.assertEqual(unconfirmed.status_code, 400)

        no_maintenance = self.client.post(
            "/api/admin/power/reboot", json={"confirm": "REBOOT_RASPBERRY_PI"}
        )
        self.assertEqual(no_maintenance.status_code, 409)

        state["maintenance_mode"] = True
        state["play_mode"] = "test"
        running = self.client.post(
            "/api/admin/power/reboot", json={"confirm": "REBOOT_RASPBERRY_PI"}
        )
        self.assertEqual(running.status_code, 409)

        state["play_mode"] = None
        for action, confirmation in (
            ("reboot", "REBOOT_RASPBERRY_PI"),
            ("poweroff", "SHUTDOWN_RASPBERRY_PI"),
        ):
            response = self.client.post(
                f"/api/admin/power/{action}", json={"confirm": confirmation}
            )
            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            self.assertEqual(payload["mode"], "mock")
            self.assertFalse(payload["executed"])

    def test_unknown_power_action_is_not_available(self):
        self.client.post("/api/admin/login", json={"pin": "2468"})
        response = self.client.post(
            "/api/admin/power/shell", json={"confirm": "ANYTHING"}
        )
        self.assertEqual(response.status_code, 404)

    def test_wifi_status_and_scan_require_admin_authentication(self):
        for path in ("/api/admin/wifi/status", "/api/admin/wifi/networks"):
            self.assertEqual(self.client.get(path).status_code, 401)

        self.client.post("/api/admin/login", json={"pin": "2468"})

        status = self.client.get("/api/admin/wifi/status")
        networks = self.client.get("/api/admin/wifi/networks")
        self.assertEqual(status.status_code, 200)
        self.assertEqual(status.get_json()["mode"], "mock")
        self.assertFalse(status.get_json()["executed"])
        self.assertEqual(networks.status_code, 200)
        self.assertEqual(networks.get_json()["networks"], [])

    def test_wifi_connect_requires_auth_confirmation_idle_and_maintenance(self):
        credentials = {
            "ssid": "Workshop WiFi",
            "password": "safe-password",
            "confirm": "CONNECT_WIFI",
        }
        self.assertEqual(
            self.client.post("/api/admin/wifi/connect", json=credentials).status_code,
            401,
        )

        self.client.post("/api/admin/login", json={"pin": "2468"})
        self.assertEqual(
            self.client.post(
                "/api/admin/wifi/connect",
                json={"ssid": "Workshop WiFi", "password": "safe-password"},
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.post("/api/admin/wifi/connect", json=credentials).status_code,
            409,
        )

        state["maintenance_mode"] = True
        state["play_mode"] = "test"
        self.assertEqual(
            self.client.post("/api/admin/wifi/connect", json=credentials).status_code,
            409,
        )

        state["play_mode"] = None
        response = self.client.post("/api/admin/wifi/connect", json=credentials)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.get_json()["executed"])
        self.assertNotIn("safe-password", response.get_data(as_text=True))

    def test_wifi_connect_validates_credentials_without_echoing_password(self):
        self.client.post("/api/admin/login", json={"pin": "2468"})
        state["maintenance_mode"] = True

        response = self.client.post(
            "/api/admin/wifi/connect",
            json={
                "ssid": "Workshop WiFi",
                "password": "short",
                "confirm": "CONNECT_WIFI",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertNotIn("short", response.get_data(as_text=True))

    def test_wifi_helper_failures_return_redacted_service_errors(self):
        from dashboard.backend.wifi_control import WifiControlError

        self.client.post("/api/admin/login", json={"pin": "2468"})
        with patch(
            "dashboard.backend.routes_admin.wifi_manager.status",
            side_effect=WifiControlError("private detail"),
        ):
            status = self.client.get("/api/admin/wifi/status")
        with patch(
            "dashboard.backend.routes_admin.wifi_manager.scan",
            side_effect=WifiControlError("private detail"),
        ):
            scan = self.client.get("/api/admin/wifi/networks")

        self.assertEqual(status.status_code, 503)
        self.assertEqual(scan.status_code, 503)
        self.assertNotIn("private detail", status.get_data(as_text=True))
        self.assertNotIn("private detail", scan.get_data(as_text=True))

    def test_maintenance_requires_authenticated_session_and_confirmation(self):
        unauthorized = self.client.post(
            "/api/admin/maintenance",
            json={"enabled": True, "confirm": "ENTER_MAINTENANCE"},
        )
        self.assertEqual(unauthorized.status_code, 401)

        self.client.post("/api/admin/login", json={"pin": "2468"})
        unconfirmed = self.client.post(
            "/api/admin/maintenance", json={"enabled": True}
        )
        self.assertEqual(unconfirmed.status_code, 400)

        enabled = self.client.post(
            "/api/admin/maintenance",
            json={"enabled": True, "confirm": "ENTER_MAINTENANCE"},
        )
        self.assertEqual(enabled.status_code, 200)
        self.assertTrue(enabled.get_json()["maintenance_mode"])
        self.assertTrue(enabled.get_json()["admin"]["maintenance_mode"])

        blocked_dashboard_play = self.client.post("/api/play", json={"test": True})
        blocked_runtime_play = self.client.post(
            "/api/play/start", json={"duration_seconds": 10, "test": True}
        )
        self.assertEqual(blocked_dashboard_play.status_code, 409)
        self.assertEqual(blocked_runtime_play.status_code, 409)

        disabled = self.client.post(
            "/api/admin/maintenance",
            json={"enabled": False, "confirm": "EXIT_MAINTENANCE"},
        )
        self.assertEqual(disabled.status_code, 200)
        self.assertFalse(disabled.get_json()["maintenance_mode"])

    def test_entering_maintenance_stops_running_game_through_safe_flow(self):
        self.client.post("/api/admin/login", json={"pin": "2468"})
        state["play_mode"] = "test"

        with patch("dashboard.backend.routes_admin.stop_play") as stop:
            response = self.client.post(
                "/api/admin/maintenance",
                json={"enabled": True, "confirm": "ENTER_MAINTENANCE"},
            )

        self.assertEqual(response.status_code, 200)
        stop.assert_called_once_with(
            "Current game stopped for maintenance", source="admin"
        )
        self.assertTrue(state["maintenance_mode"])

    def test_stop_game_requires_running_game_and_uses_safe_stop_flow(self):
        self.client.post("/api/admin/login", json={"pin": "2468"})
        idle = self.client.post(
            "/api/admin/stop-game", json={"confirm": "STOP_CURRENT_GAME"}
        )
        self.assertEqual(idle.status_code, 409)

        state["play_mode"] = "test"
        with patch("dashboard.backend.routes_admin.stop_play") as stop:
            response = self.client.post(
                "/api/admin/stop-game", json={"confirm": "STOP_CURRENT_GAME"}
            )

        self.assertEqual(response.status_code, 200)
        stop.assert_called_once_with(
            "Current game stopped by administrator", source="admin"
        )


if __name__ == "__main__":
    unittest.main()
