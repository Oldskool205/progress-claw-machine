"""Explicit live Supabase diagnostics for Phase A.1.

Run with ``python3 -m cloud.diagnostics --help``. This module is never invoked
by the normal machine runtime.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
from typing import Optional, Sequence

from cloud.config import SupabaseConfig
from cloud.errors import sanitize_error
from cloud.sync_service import CloudSyncService


DIAGNOSTIC_MACHINE_NAME = "CLOUD-DIAGNOSTIC-TEST"


def diagnostic_service() -> CloudSyncService:
    config = replace(
        SupabaseConfig.from_env(),
        machine_name=DIAGNOSTIC_MACHINE_NAME,
    )
    return CloudSyncService(config=config)


def run_diagnostics(args: argparse.Namespace, service: CloudSyncService) -> int:
    results: list[tuple[str, bool, str]] = []

    if not service.config.configured:
        results.append(("configuration", False, "SUPABASE_URL or SUPABASE_KEY missing"))
        _print_summary(results)
        return 1

    run_all = args.all
    if args.test_connection or run_all:
        schema = service.validate_schema()
        message = schema.message
        if schema.error_category:
            message = f"{message} ({schema.error_category})"
        results.append(("connection and schema", schema.ok, message))

    if args.send_test_status or run_all:
        result = service.sync_game_status(
            status="diagnostic",
            x_position=1.0,
            y_position=2.0,
            claw_power=50,
        )
        results.append(("test status", result.ok, result.message))

    if args.heartbeat or run_all:
        result = service.heartbeat()
        results.append(("heartbeat", result.ok, result.message))

    if args.set_offline or run_all:
        result = service.sync_online_state(False)
        results.append(("set offline", result.ok, result.message))

    if args.cleanup:
        results.append(_cleanup_test_record(service))

    if not results:
        results.append(("diagnostics", False, "No diagnostic action selected"))
    _print_summary(results)
    return 0 if all(ok for _, ok, _ in results) else 1


def _cleanup_test_record(service: CloudSyncService) -> tuple[str, bool, str]:
    if not service.connect():
        return ("cleanup", False, "Cloud connection unavailable")
    try:
        (
            service.client.client.table(service.config.table_name)
            .delete()
            .eq("machine_name", DIAGNOSTIC_MACHINE_NAME)
            .execute()
        )
        return ("cleanup", True, "Diagnostic row removed")
    except Exception as error:
        return ("cleanup", False, f"Cleanup failed ({sanitize_error(error)})")


def _print_summary(results: list[tuple[str, bool, str]]) -> None:
    print("Progress Claw Cloud Diagnostic")
    print(f"Machine: {DIAGNOSTIC_MACHINE_NAME}")
    for name, ok, message in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {message}")
    passed = sum(1 for _, ok, _ in results if ok)
    print(f"Summary: {passed}/{len(results)} checks passed")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run opt-in Supabase diagnostics")
    parser.add_argument("--test-connection", action="store_true")
    parser.add_argument("--send-test-status", action="store_true")
    parser.add_argument("--heartbeat", action="store_true")
    parser.add_argument("--set-offline", action="store_true")
    parser.add_argument("--cleanup", action="store_true")
    parser.add_argument("--all", action="store_true")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return run_diagnostics(args, diagnostic_service())


if __name__ == "__main__":
    raise SystemExit(main())
