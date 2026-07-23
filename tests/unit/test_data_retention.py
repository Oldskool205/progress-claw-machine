import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from dashboard.backend import dashboard_state


PROJECT_ROOT = Path(__file__).resolve().parents[2]
AUDIT_SCRIPT = PROJECT_ROOT / "scripts" / "maintenance" / "audit_data_retention.py"


def load_audit_module():
    spec = importlib.util.spec_from_file_location("audit_data_retention", AUDIT_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class DataRetentionAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit_module = load_audit_module()

    def test_audit_counts_expired_files_without_deleting(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data_dir = root / "private"
            data_dir.mkdir()
            recent = data_dir / "recent.jpg"
            expired = data_dir / "expired.jpg"
            ignored = data_dir / ".gitkeep"
            recent.write_bytes(b"recent")
            expired.write_bytes(b"expired-data")
            ignored.touch()
            now = 2_000_000_000.0
            os.utime(recent, (now, now))
            os.utime(expired, (now - 9 * 86400, now - 9 * 86400))
            category = self.audit_module.RetentionCategory("test", "private", 7)

            summary = self.audit_module.summarize_category(
                root, category, now=now
            )

            self.assertEqual(summary.files, 2)
            self.assertEqual(summary.expired_files, 1)
            self.assertEqual(summary.expired_bytes, len(b"expired-data"))
            self.assertTrue(recent.exists())
            self.assertTrue(expired.exists())

    def test_audit_does_not_follow_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data_dir = root / "private"
            data_dir.mkdir()
            target = root / "outside.jpg"
            target.write_bytes(b"private")
            (data_dir / "link.jpg").symlink_to(target)
            category = self.audit_module.RetentionCategory("test", "private", 7)

            summary = self.audit_module.summarize_category(root, category)

            self.assertEqual(summary.files, 0)
            self.assertTrue(target.exists())


class TrainingArchivePrivacyTest(unittest.TestCase):
    def test_archive_is_disabled_without_explicit_opt_in(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(
            dashboard_state, "YOLO_RAW_PHOTO_DIR", directory
        ), patch.object(
            dashboard_state, "YOLO_RAW_PHOTO_ARCHIVE_ENABLED", False
        ):
            result = dashboard_state.archive_yolo_raw_photo(
                b"photo", dashboard_state.datetime.now(), "test", 1
            )

            self.assertIsNone(result)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_opted_in_archive_omits_player_identity(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(
            dashboard_state, "YOLO_RAW_PHOTO_DIR", directory
        ), patch.object(
            dashboard_state, "YOLO_RAW_PHOTO_ARCHIVE_ENABLED", True
        ):
            image_path = dashboard_state.archive_yolo_raw_photo(
                b"photo", dashboard_state.datetime.now(), "test", 1
            )
            metadata_path = Path(image_path).with_suffix(".json")
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

            self.assertNotIn("player_name", metadata)
            self.assertNotIn("player", Path(image_path).name)
            self.assertEqual(metadata["source"], "test")


if __name__ == "__main__":
    unittest.main()
