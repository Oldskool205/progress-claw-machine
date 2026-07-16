"""Diagnostic-only cloud monitoring routes."""

from __future__ import annotations

from dataclasses import asdict, replace

from flask import Blueprint, jsonify, render_template

from cloud.config import SupabaseConfig
from cloud.diagnostics import DIAGNOSTIC_MACHINE_NAME
from cloud.sync_service import CloudSyncService


bp = Blueprint("cloud_monitoring", __name__)
cloud_service = CloudSyncService(
    replace(SupabaseConfig.from_env(), machine_name=DIAGNOSTIC_MACHINE_NAME)
)


def _result_payload(action: str, ok: bool, message: str, **extra):
    return {
        "ok": ok,
        "action": action,
        "message": message,
        "health": cloud_service.health_snapshot(),
        **extra,
    }


@bp.route("/cloud", methods=["GET"])
def monitoring_page():
    return render_template("cloud.html")


@bp.route("/cloud/health", methods=["GET"])
@bp.route("/cloud/status", methods=["GET"])
def cloud_health():
    return jsonify(cloud_service.health_snapshot())


@bp.route("/cloud/actions/test-connection", methods=["POST"])
def test_connection():
    result = cloud_service.validate_schema()
    return jsonify(
        _result_payload(
            "test_connection",
            result.ok,
            result.message,
            schema=asdict(result),
        )
    )


@bp.route("/cloud/actions/send-test-status", methods=["POST"])
def send_test_status():
    result = cloud_service.sync_game_status("diagnostic", 1.0, 2.0, 50)
    return jsonify(
        _result_payload("send_test_status", result.ok, result.message)
    )


@bp.route("/cloud/actions/heartbeat", methods=["POST"])
def send_heartbeat():
    result = cloud_service.heartbeat()
    return jsonify(_result_payload("heartbeat", result.ok, result.message))


@bp.route("/cloud/actions/load-supabase-data", methods=["POST"])
def load_supabase_data():
    result = cloud_service.fetch_machine_status()
    return jsonify(
        _result_payload(
            "load_supabase_data",
            result.ok,
            result.message,
            data=result.data,
        )
    )
