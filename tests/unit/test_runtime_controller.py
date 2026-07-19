import unittest
from unittest.mock import patch

from controller.adapters.arduino_adapter import ArduinoAdapter, ArduinoResponse
from controller.core.runtime_controller import RuntimeController
from controller.models import (
    ClawPowerCommand,
    EmergencyStopCommand,
    PlayStartCommand,
    PlayStopCommand,
)
from controller.safety.validator import SafetyError


class RuntimeControllerTest(unittest.TestCase):
    def make_controller(self):
        return RuntimeController(arduino=ArduinoAdapter(force_mock=True))

    def test_start_play_uses_mock_arduino_and_updates_state(self):
        controller = self.make_controller()

        result = controller.start_play(
            PlayStartCommand(duration_seconds=10, source="test")
        )

        self.assertTrue(result["ok"])
        self.assertTrue(result["running"])
        self.assertEqual(result["status"], "running")
        self.assertIn("CLAW POWER 100", controller.arduino.mock_commands)
        self.assertIn("PLAY START 10", controller.arduino.mock_commands)

    def test_stop_play_sends_stop_and_returns_ready(self):
        controller = self.make_controller()
        controller.start_play(PlayStartCommand(duration_seconds=10, source="test"))

        result = controller.stop_play(PlayStopCommand(source="test"))

        self.assertTrue(result["ok"])
        self.assertFalse(result["running"])
        self.assertEqual(result["status"], "ready")
        self.assertIn("PLAY STOP", controller.arduino.mock_commands)

    def test_startup_time_is_included_before_automatic_stop(self):
        controller = self.make_controller()

        with patch("controller.core.runtime_controller.time.time", return_value=1000), patch(
            "controller.core.runtime_controller.threading.Thread"
        ) as thread:
            result = controller.start_play(
                PlayStartCommand(duration_seconds=60, startup_seconds=9, source="test")
            )

        self.assertEqual(result["play_ends_at"], 1069)
        thread.assert_called_once()
        self.assertEqual(thread.call_args.kwargs["args"][1], 69)

    def test_rejects_unsafe_play_duration(self):
        controller = self.make_controller()

        with self.assertRaises(SafetyError):
            controller.start_play(PlayStartCommand(duration_seconds=3, source="test"))

    def test_hardware_failure_does_not_report_a_running_game(self):
        class FailingArduino(ArduinoAdapter):
            @property
            def connected(self):
                return True

            @property
            def mock_mode(self):
                return False

            def send_command(self, command):
                return ArduinoResponse(False, "ERR cannot set state of pin GPIO17", False)

        controller = RuntimeController(arduino=FailingArduino())

        with self.assertRaisesRegex(SafetyError, "cannot set state of pin GPIO17"):
            controller.start_play(PlayStartCommand(duration_seconds=10, source="test"))

        status = controller.status()
        self.assertFalse(status["running"])
        self.assertEqual(status["status"], "fault")

    def test_claw_power_validation_and_command(self):
        controller = self.make_controller()

        result = controller.set_claw_power(
            ClawPowerCommand(power_percent=70, source="test")
        )

        self.assertEqual(result["claw_power_percent"], 70)
        self.assertIn("CLAW POWER 70", controller.arduino.mock_commands)

        with self.assertRaises(SafetyError):
            controller.set_claw_power(ClawPowerCommand(power_percent=10, source="test"))

    def test_emergency_stop_blocks_later_commands(self):
        controller = self.make_controller()

        result = controller.emergency_stop(EmergencyStopCommand(source="test"))

        self.assertTrue(result["emergency_stopped"])
        self.assertEqual(result["status"], "emergency_stopped")
        self.assertIn("EMERGENCY STOP", controller.arduino.mock_commands)
        with self.assertRaises(SafetyError):
            controller.start_play(PlayStartCommand(duration_seconds=10, source="test"))


if __name__ == "__main__":
    unittest.main()
