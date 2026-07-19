import unittest
from unittest.mock import patch

from dashboard.backend.system_power import LiveSystemPowerExecutor, MockSystemPowerExecutor


class MockSystemPowerExecutorTest(unittest.TestCase):
    def test_allowed_actions_are_recorded_but_never_executed(self):
        executor = MockSystemPowerExecutor()

        for action in ("reboot", "poweroff"):
            result = executor.request(action)
            self.assertTrue(result["ok"])
            self.assertEqual(result["mode"], "mock")
            self.assertFalse(result["executed"])
            self.assertEqual(executor.last_request["action"], action)

    def test_unknown_action_is_rejected(self):
        executor = MockSystemPowerExecutor()

        with self.assertRaises(ValueError):
            executor.request("shell")

    @patch("dashboard.backend.system_power.subprocess.run")
    def test_live_executor_uses_fixed_noninteractive_helper_command(self, run):
        executor = LiveSystemPowerExecutor("/usr/local/sbin/progress-claw-power")

        result = executor.request("reboot")

        run.assert_called_once_with(
            [
                "/usr/bin/sudo",
                "-n",
                "/usr/local/sbin/progress-claw-power",
                "reboot",
            ],
            check=True,
            timeout=10,
        )
        self.assertTrue(result["executed"])

    @patch("dashboard.backend.system_power.subprocess.run")
    def test_live_executor_rejects_unknown_action_before_subprocess(self, run):
        executor = LiveSystemPowerExecutor("/usr/local/sbin/progress-claw-power")

        with self.assertRaises(ValueError):
            executor.request("shell")
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
