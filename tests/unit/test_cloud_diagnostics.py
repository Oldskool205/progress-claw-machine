import argparse
import io
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace

from cloud.diagnostics import DIAGNOSTIC_MACHINE_NAME, run_diagnostics
from cloud.models import SchemaResult, SyncResult


def arguments(**changes):
    values = {
        "test_connection": False,
        "send_test_status": False,
        "heartbeat": False,
        "set_offline": False,
        "cleanup": False,
        "all": False,
    }
    values.update(changes)
    return argparse.Namespace(**values)


class FakeDiagnosticService:
    def __init__(self, configured=True, success=True):
        self.config = SimpleNamespace(configured=configured)
        self.success = success
        self.calls = []

    def validate_schema(self):
        self.calls.append("schema")
        return SchemaResult(
            self.success,
            "schema ok" if self.success else "schema failed",
            error_category=None if self.success else "network_error",
        )

    def sync_game_status(self, status, x_position, y_position, claw_power):
        self.calls.append((status, x_position, y_position, claw_power))
        return SyncResult(self.success, "status result")

    def heartbeat(self):
        self.calls.append("heartbeat")
        return SyncResult(self.success, "heartbeat result")

    def sync_online_state(self, online):
        self.calls.append(("online", online))
        return SyncResult(self.success, "offline result")


class CloudDiagnosticsTest(unittest.TestCase):
    def run_with_output(self, args, service):
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = run_diagnostics(args, service)
        return exit_code, output.getvalue()

    def test_missing_configuration_fails_without_cloud_call(self):
        service = FakeDiagnosticService(configured=False)

        exit_code, output = self.run_with_output(arguments(all=True), service)

        self.assertEqual(exit_code, 1)
        self.assertEqual(service.calls, [])
        self.assertIn("SUPABASE_URL or SUPABASE_KEY missing", output)

    def test_successful_connection_reports_pass(self):
        service = FakeDiagnosticService()

        exit_code, output = self.run_with_output(
            arguments(test_connection=True), service
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(service.calls, ["schema"])
        self.assertIn("[PASS] connection and schema", output)

    def test_connection_failure_reports_sanitized_category(self):
        service = FakeDiagnosticService(success=False)

        exit_code, output = self.run_with_output(
            arguments(test_connection=True), service
        )

        self.assertEqual(exit_code, 1)
        self.assertIn("network_error", output)

    def test_all_uses_only_dedicated_test_snapshot(self):
        service = FakeDiagnosticService()

        exit_code, output = self.run_with_output(arguments(all=True), service)

        self.assertEqual(exit_code, 0)
        self.assertIn(("diagnostic", 1.0, 2.0, 50), service.calls)
        self.assertIn(("online", False), service.calls)
        self.assertIn(DIAGNOSTIC_MACHINE_NAME, output)


if __name__ == "__main__":
    unittest.main()
