import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from dashboard.backend import kiosk_control


class KioskControlTest(unittest.TestCase):
    def test_exit_request_is_private_and_contains_only_exit_signal(self):
        with tempfile.TemporaryDirectory() as directory:
            request_path = Path(directory) / "runtime" / "kiosk-exit-request"
            with patch.dict(
                os.environ,
                {"PROGRESS_CLAW_KIOSK_EXIT_FILE": str(request_path)},
                clear=False,
            ):
                result = kiosk_control.request_exit()

            self.assertEqual(result, request_path)
            self.assertEqual(request_path.read_text(encoding="utf-8"), "exit\n")
            self.assertEqual(request_path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(request_path.parent.stat().st_mode & 0o777, 0o700)

    def test_restart_request_uses_same_private_channel(self):
        with tempfile.TemporaryDirectory() as directory:
            request_path = Path(directory) / "runtime" / "kiosk-request"
            with patch.dict(
                os.environ,
                {"PROGRESS_CLAW_KIOSK_EXIT_FILE": str(request_path)},
                clear=False,
            ):
                kiosk_control.request_restart()

            self.assertEqual(request_path.read_text(encoding="utf-8"), "restart\n")

    def test_unknown_kiosk_request_is_rejected(self):
        with self.assertRaises(ValueError):
            kiosk_control.request("shutdown")
