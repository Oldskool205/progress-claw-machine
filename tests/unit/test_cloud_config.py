import os
import unittest
from unittest.mock import mock_open, patch

from cloud.config import SupabaseConfig


class SupabaseConfigTest(unittest.TestCase):
    def test_loads_required_and_optional_environment_values(self):
        environment = {
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_KEY": "test-key",
            "CLAW_MACHINE_NAME": "Test Claw",
            "SUPABASE_RETRY_SECONDS": "12.5",
        }
        with patch.dict(os.environ, environment, clear=True):
            config = SupabaseConfig.from_env()

        self.assertTrue(config.configured)
        self.assertEqual(config.url, environment["SUPABASE_URL"])
        self.assertEqual(config.key, environment["SUPABASE_KEY"])
        self.assertEqual(config.machine_name, "Test Claw")
        self.assertEqual(config.retry_seconds, 12.5)

    def test_missing_credentials_leave_cloud_disabled(self):
        with patch.dict(os.environ, {}, clear=True), patch(
            "cloud.config.load_dotenv"
        ):
            config = SupabaseConfig.from_env()

        self.assertFalse(config.configured)

    def test_fallback_loads_local_env_without_python_dotenv(self):
        env_contents = (
            "SUPABASE_URL=https://example.supabase.co\n"
            "SUPABASE_KEY=test-secret\n"
            "CLAW_MACHINE_NAME=Fallback Claw\n"
        )
        with patch.dict(os.environ, {}, clear=True), patch(
            "cloud.config.load_dotenv", None
        ), patch("builtins.open", mock_open(read_data=env_contents)):
            config = SupabaseConfig.from_env()

        self.assertTrue(config.configured)
        self.assertEqual(config.machine_name, "Fallback Claw")

    def test_invalid_optional_values_fall_back_to_safe_defaults(self):
        environment = {
            "CLAW_MACHINE_NAME": "  ",
            "SUPABASE_MACHINE_STATUS_TABLE": "",
            "SUPABASE_RETRY_SECONDS": "not-a-number",
        }
        with patch.dict(os.environ, environment, clear=True):
            config = SupabaseConfig.from_env()

        self.assertEqual(config.machine_name, "Progress Claw Machine")
        self.assertEqual(config.table_name, "machine_status")
        self.assertEqual(config.retry_seconds, 30.0)

    def test_negative_retry_delay_is_clamped_to_zero(self):
        with patch.dict(
            os.environ, {"SUPABASE_RETRY_SECONDS": "-1"}, clear=True
        ):
            config = SupabaseConfig.from_env()

        self.assertEqual(config.retry_seconds, 0.0)


if __name__ == "__main__":
    unittest.main()
