from io import BytesIO
import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path
import os
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
HELPER_PATH = PROJECT_ROOT / "scripts" / "system" / "progress-claw-wifi"
SUDOERS_PATH = PROJECT_ROOT / "system" / "progress-claw-wifi.sudoers"


def load_helper():
    loader = SourceFileLoader("progress_claw_wifi_helper", str(HELPER_PATH))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class WifiHelperConfigTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.helper = load_helper()

    def test_known_wpa_psk_vector_and_no_plaintext_in_managed_block(self):
        expected = (
            "f42c6fc52df0ebef9ebb4b90b38a5f90"
            "2e83fe1b135a70e23aed762e9710a12e"
        )
        self.assertEqual(self.helper.derive_psk("IEEE", "password"), expected)

        block = self.helper.managed_block("Workshop WiFi", "do-not-store-this")
        self.assertNotIn("do-not-store-this", block)
        self.assertIn("ssid=576f726b73686f702057694669", block)
        self.assertIn(self.helper.BEGIN_MARKER, block)
        self.assertIn(self.helper.END_MARKER, block)

    def test_request_is_bounded_exact_and_safely_validated(self):
        request = BytesIO(b'{"ssid":"Workshop WiFi","password":"safe-password"}')
        self.assertEqual(
            self.helper.read_connect_request(request),
            ("Workshop WiFi", "safe-password"),
        )
        for raw in (
            b'{"ssid":"x","password":"safe-password","path":"/etc/passwd"}',
            b"x" * (self.helper.MAX_INPUT_BYTES + 1),
            b"not-json",
        ):
            with self.subTest(raw=raw[:20]):
                with self.assertRaises(self.helper.HelperError):
                    self.helper.read_connect_request(BytesIO(raw))

    def test_managed_update_preserves_unmanaged_configuration(self):
        original = "ctrl_interface=DIR=/var/run/wpa_supplicant\nnetwork={\n    ssid=aaaa\n}\n"

        first = self.helper.update_managed_block(original, "First", "password-one")
        second = self.helper.update_managed_block(first, "Second", "password-two")

        self.assertIn("ssid=aaaa", second)
        self.assertNotIn("password-one", second)
        self.assertNotIn("password-two", second)
        self.assertEqual(second.count(self.helper.BEGIN_MARKER), 1)
        self.assertIn("ssid=5365636f6e64", second)

    def test_inconsistent_or_duplicate_markers_are_rejected(self):
        for content in (
            self.helper.BEGIN_MARKER,
            self.helper.END_MARKER,
            f"{self.helper.BEGIN_MARKER}\n{self.helper.END_MARKER}\n"
            f"{self.helper.BEGIN_MARKER}\n{self.helper.END_MARKER}",
        ):
            with self.subTest(content=content):
                with self.assertRaises(self.helper.HelperError):
                    self.helper.update_managed_block(content, "WiFi", "password")

    def test_successful_connect_writes_psk_and_keeps_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "wpa_supplicant.conf"
            backup = root / "backup.conf"
            original = b"country=GB\n"
            config.write_bytes(original)
            config.chmod(0o600)
            actions = []

            def runner(action):
                actions.append(action)
                if action == "status":
                    return "wpa_state=COMPLETED\nid_str=progress-claw-admin\n"
                return "OK\n"

            result = self.helper.connect_network(
                "Workshop WiFi",
                "safe-password",
                config_path=config,
                backup_path=backup,
                runner=runner,
                sleeper=lambda _seconds: None,
                attempts=1,
                require_root_owner=False,
            )

            self.assertTrue(result["executed"])
            self.assertEqual(backup.read_bytes(), original)
            self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
            self.assertNotIn("safe-password", config.read_text(encoding="utf-8"))
            self.assertEqual(config.stat().st_mode & 0o777, 0o600)
            self.assertEqual(actions, ["reconfigure", "status"])

    def test_failed_connect_restores_original_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "wpa_supplicant.conf"
            backup = root / "backup.conf"
            original = b"country=GB\nnetwork={}\n"
            config.write_bytes(original)
            config.chmod(0o600)
            actions = []

            def runner(action):
                actions.append(action)
                return "wpa_state=DISCONNECTED\n" if action == "status" else "OK\n"

            with self.assertRaisesRegex(self.helper.HelperError, "timed out"):
                self.helper.connect_network(
                    "Workshop WiFi",
                    "safe-password",
                    config_path=config,
                    backup_path=backup,
                    runner=runner,
                    sleeper=lambda _seconds: None,
                    attempts=1,
                    require_root_owner=False,
                )

            self.assertEqual(config.read_bytes(), original)
            self.assertEqual(actions, ["reconfigure", "status", "reconfigure"])

    def test_identical_connected_configuration_is_not_rewritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "wpa_supplicant.conf"
            backup = root / "backup.conf"
            existing = self.helper.update_managed_block(
                "country=GB\n", "Workshop WiFi", "safe-password"
            ).encode("utf-8")
            config.write_bytes(existing)
            config.chmod(0o600)

            result = self.helper.connect_network(
                "Workshop WiFi",
                "safe-password",
                config_path=config,
                backup_path=backup,
                runner=lambda action: (
                    "wpa_state=COMPLETED\nid_str=progress-claw-admin\n"
                    if action == "status"
                    else "OK\n"
                ),
                sleeper=lambda _seconds: None,
                attempts=1,
                require_root_owner=False,
            )

            self.assertTrue(result["connected"])
            self.assertIn("already connected", result["message"])
            self.assertEqual(config.read_bytes(), existing)
            self.assertFalse(backup.exists())

    def test_symlink_and_unsafe_permissions_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target"
            target.write_text("country=GB\n", encoding="utf-8")
            target.chmod(0o666)
            link = root / "link"
            link.symlink_to(target)

            for path in (target, link):
                with self.subTest(path=path):
                    with self.assertRaises(self.helper.HelperError):
                        self.helper.validate_config_file(
                            path, require_root_owner=False
                        )

    def test_hard_linked_config_and_symlink_lock_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "config"
            config.write_text("country=GB\n", encoding="utf-8")
            config.chmod(0o600)
            hard_link = root / "config-hard-link"
            os.link(config, hard_link)

            with self.assertRaises(self.helper.HelperError):
                self.helper.validate_config_file(
                    config, require_root_owner=False
                )

            lock_target = root / "lock-target"
            lock_target.touch()
            lock_link = root / "lock-link"
            lock_link.symlink_to(lock_target)
            with self.assertRaises(self.helper.HelperError):
                self.helper.acquire_operation_lock(lock_link)

    def test_scan_deduplicates_and_orders_networks(self):
        outputs = {
            "scan": "OK\n",
            "scan_results": (
                "bssid / frequency / signal level / flags / ssid\n"
                "aa\t2412\t-70\t[WPA2-PSK]\tCafe\n"
                "bb\t2412\t-40\t[WPA2-PSK]\tCafe\n"
                "cc\t2412\t-50\t[ESS]\tGuest\n"
            ),
        }

        result = self.helper.scan_payload(lambda action: outputs[action])

        self.assertEqual([item["ssid"] for item in result["networks"]], ["Cafe", "Guest"])
        self.assertEqual(result["networks"][0]["security"], "secured")

    def test_helper_and_sudoers_have_exact_allowlists(self):
        helper = HELPER_PATH.read_text(encoding="utf-8")
        sudoers = SUDOERS_PATH.read_text(encoding="utf-8")

        self.assertIn('sys.argv[1] not in {"status", "scan", "connect"}', helper)
        self.assertIn('[WPA_CLI, "-i", INTERFACE, action]', helper)
        self.assertNotIn("shell=True", helper)
        self.assertNotIn("os.system", helper)
        for action in ("status", "scan", "connect"):
            self.assertIn(f"progress-claw-wifi {action}", sudoers)
        self.assertNotIn("progress-claw-wifi *", sudoers)
        self.assertNotIn("NOPASSWD: ALL", sudoers)


if __name__ == "__main__":
    unittest.main()
