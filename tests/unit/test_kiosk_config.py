from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = PROJECT_ROOT / "scripts" / "kiosk" / "start_kiosk.sh"
SERVICE = PROJECT_ROOT / "system" / "progress-claw-kiosk.service"


class KioskConfigTest(unittest.TestCase):
    def test_launcher_uses_kiosk_mode_and_default_dashboard_url(self):
        content = LAUNCHER.read_text(encoding="utf-8")

        self.assertIn("--kiosk", content)
        self.assertIn("http://localhost:5000/", content)
        self.assertIn("PROGRESS_CLAW_KIOSK_URL", content)
        self.assertIn('--user-data-dir="$KIOSK_PROFILE_DIR"', content)

    def test_launcher_does_not_start_or_stop_dashboard_backend(self):
        content = LAUNCHER.read_text(encoding="utf-8")

        self.assertNotIn("main.py", content)
        self.assertNotIn("app.py", content)
        self.assertNotIn("systemctl", content)

    def test_launcher_exits_only_its_owned_chromium_process(self):
        content = LAUNCHER.read_text(encoding="utf-8")

        self.assertIn("PROGRESS_CLAW_KIOSK_EXIT_FILE", content)
        self.assertIn('kill -TERM -- "-$CHROMIUM_PID"', content)
        self.assertIn('setsid "$CHROMIUM_BIN"', content)
        self.assertNotIn("pkill", content)
        self.assertNotIn("killall", content)

    def test_exit_keeps_launcher_available_for_later_kiosk_restart(self):
        content = LAUNCHER.read_text(encoding="utf-8")

        self.assertIn("normal browser window", content)
        self.assertIn("KIOSK_MODE=0", content)
        self.assertIn("KIOSK_MODE=1", content)

    def test_launcher_restarts_chromium_without_restarting_backend(self):
        content = LAUNCHER.read_text(encoding="utf-8")

        self.assertIn("start_chromium", content)
        self.assertIn("restart)", content)
        self.assertIn("restart_requested=1", content)
        self.assertIn("Kiosk mode is persistent", content)
        self.assertNotIn("progress-claw.service restart", content)

    def test_service_is_independent_from_dashboard_lifecycle(self):
        content = SERVICE.read_text(encoding="utf-8")

        self.assertIn(
            "ExecStart=/home/araya/Projects/Progress-Claw-OS/scripts/kiosk/start_kiosk.sh",
            content,
        )
        self.assertIn("User=araya", content)
        self.assertNotIn("Requires=claw-dashboard.service", content)
        self.assertNotIn("PartOf=claw-dashboard.service", content)
        self.assertNotIn("ExecStop=", content)


if __name__ == "__main__":
    unittest.main()
