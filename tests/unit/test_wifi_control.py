import inspect
import json
import os
import unittest
from unittest.mock import patch

from dashboard.backend.wifi_control import (
    LiveWifiManager,
    MockWifiManager,
    WifiControlError,
    WifiValidationError,
    create_wifi_manager,
    validate_credentials,
)


class WifiCredentialValidationTest(unittest.TestCase):
    def test_accepts_wpa_personal_credentials(self):
        self.assertEqual(
            validate_credentials("Workshop WiFi", "safe-password"),
            "Workshop WiFi",
        )

    def test_rejects_missing_or_oversized_network_name(self):
        for ssid in (None, "", "x" * 33, "bad\nnetwork"):
            with self.subTest(ssid=ssid):
                with self.assertRaises(WifiValidationError):
                    validate_credentials(ssid, "safe-password")

    def test_rejects_unsupported_passwords(self):
        for password in (None, "short", "x" * 64, "bad\npassword"):
            with self.subTest(password=password):
                with self.assertRaises(WifiValidationError):
                    validate_credentials("Workshop WiFi", password)


class MockWifiManagerTest(unittest.TestCase):
    def test_connect_is_simulated_and_password_is_not_retained(self):
        manager = MockWifiManager()

        result = manager.connect("Workshop WiFi", "do-not-store-this")

        self.assertFalse(result["executed"])
        self.assertEqual(result["mode"], "mock")
        self.assertEqual(manager.status()["last_requested_ssid"], "Workshop WiFi")
        self.assertNotIn("do-not-store-this", repr(manager.__dict__))

    def test_stage_one_module_has_no_system_execution_path(self):
        source = inspect.getsource(MockWifiManager)

        self.assertNotIn("subprocess.", source)
        self.assertNotIn("os.system", source)


class LiveWifiManagerTest(unittest.TestCase):
    @patch("dashboard.backend.wifi_control.subprocess.run")
    def test_status_uses_exact_noninteractive_helper_command(self, run):
        run.return_value.stdout = json.dumps(
            {
                "ok": True,
                "mode": "live",
                "executed": True,
                "connected": True,
                "current_ssid": "Workshop WiFi",
                "internet": None,
                "message": "Wi-Fi connected",
            }
        )
        manager = LiveWifiManager("/usr/local/sbin/progress-claw-wifi")

        result = manager.status()

        run.assert_called_once_with(
            [
                "/usr/bin/sudo",
                "-n",
                "/usr/local/sbin/progress-claw-wifi",
                "status",
            ],
            input=None,
            capture_output=True,
            text=True,
            check=True,
            timeout=90,
        )
        self.assertTrue(result["connected"])

    @patch("dashboard.backend.wifi_control.subprocess.run")
    def test_connect_passes_password_only_through_standard_input(self, run):
        run.return_value.stdout = json.dumps(
            {
                "ok": True,
                "mode": "live",
                "executed": True,
                "connected": True,
                "ssid": "Workshop WiFi",
                "message": "Wi-Fi connection completed",
            }
        )
        manager = LiveWifiManager("/usr/local/sbin/progress-claw-wifi")

        manager.connect("Workshop WiFi", "do-not-put-in-argv")

        call = run.call_args
        self.assertNotIn("do-not-put-in-argv", repr(call.args[0]))
        self.assertEqual(
            json.loads(call.kwargs["input"])["password"], "do-not-put-in-argv"
        )

    @patch("dashboard.backend.wifi_control.subprocess.run")
    def test_invalid_credentials_are_rejected_before_sudo(self, run):
        manager = LiveWifiManager()

        with self.assertRaises(WifiValidationError):
            manager.connect("Workshop WiFi", "short")
        run.assert_not_called()

    @patch("dashboard.backend.wifi_control.subprocess.run")
    def test_helper_failure_is_redacted(self, run):
        run.side_effect = OSError("sensitive system detail")

        with self.assertRaisesRegex(WifiControlError, "Wi-Fi system helper failed") as caught:
            LiveWifiManager().connect("Workshop WiFi", "do-not-log-this")

        self.assertNotIn("do-not-log-this", str(caught.exception))

    @patch("dashboard.backend.wifi_control.subprocess.run")
    def test_unrecognized_helper_fields_are_not_returned(self, run):
        run.return_value.stdout = json.dumps(
            {
                "ok": True,
                "mode": "live",
                "executed": True,
                "connected": True,
                "current_ssid": "Workshop WiFi",
                "internet": None,
                "message": "Wi-Fi connected",
                "password": "must-not-escape",
            }
        )

        result = LiveWifiManager().status()

        self.assertNotIn("password", result)
        self.assertNotIn("must-not-escape", repr(result))

    def test_manager_defaults_to_mock_and_rejects_unknown_mode(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsInstance(create_wifi_manager(), MockWifiManager)
        with patch.dict(os.environ, {"PROGRESS_CLAW_WIFI_MODE": "unknown"}):
            with self.assertRaises(ValueError):
                create_wifi_manager()


if __name__ == "__main__":
    unittest.main()
