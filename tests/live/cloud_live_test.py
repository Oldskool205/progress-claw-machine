"""Optional real Supabase check.

Run explicitly with:
    PROGRESS_CLAW_RUN_LIVE_TESTS=1 python3 -m unittest tests.live.cloud_live_test -v
"""

import os
import unittest

from cloud.config import SupabaseConfig
from cloud.diagnostics import _cleanup_test_record, diagnostic_service


_LIVE_CONFIG = SupabaseConfig.from_env()
_LIVE_TESTS_ENABLED = os.getenv("PROGRESS_CLAW_RUN_LIVE_TESTS") == "1"


@unittest.skipUnless(
    _LIVE_TESTS_ENABLED and _LIVE_CONFIG.configured,
    "live Supabase tests require PROGRESS_CLAW_RUN_LIVE_TESTS=1 and credentials",
)
class LiveCloudTest(unittest.TestCase):
    def test_dedicated_diagnostic_record_lifecycle(self):
        service = diagnostic_service()
        self.assertTrue(service.validate_schema().ok)
        self.assertTrue(service.sync_game_status("diagnostic", 1.0, 2.0, 50).ok)
        self.assertTrue(service.heartbeat().ok)
        self.assertTrue(service.sync_online_state(False).ok)
        cleanup_name, cleanup_ok, cleanup_message = _cleanup_test_record(service)
        self.assertEqual(cleanup_name, "cleanup")
        self.assertTrue(cleanup_ok, cleanup_message)


if __name__ == "__main__":
    unittest.main()
