from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
HELPER = PROJECT_ROOT / "scripts" / "system" / "progress-claw-power"
SUDOERS = PROJECT_ROOT / "system" / "progress-claw-power.sudoers"


class PowerHelperConfigTest(unittest.TestCase):
    def test_helper_has_exact_action_and_command_allowlists(self):
        content = HELPER.read_text(encoding="utf-8")

        self.assertIn('"reboot": ["/usr/bin/systemctl", "reboot"]', content)
        self.assertIn('"poweroff": ["/usr/bin/systemctl", "poweroff"]', content)
        self.assertNotIn("shell=True", content)
        self.assertNotIn("os.system", content)

    def test_sudoers_allows_only_exact_helper_actions(self):
        content = SUDOERS.read_text(encoding="utf-8")

        self.assertIn("/usr/local/sbin/progress-claw-power reboot", content)
        self.assertIn("/usr/local/sbin/progress-claw-power poweroff", content)
        self.assertNotIn("ALL=(ALL) NOPASSWD: ALL", content)


if __name__ == "__main__":
    unittest.main()
