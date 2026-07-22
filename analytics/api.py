"""Read-only Analytics API and dashboard routes."""

from __future__ import annotations

import csv
import json
from io import StringIO

from flask import Blueprint, Response, jsonify, render_template, request

from analytics.service import AnalyticsService


def _query_options() -> dict:
    min_confidence = request.args.get("min_confidence")
    options = {
        "category": request.args.get("category"),
        "event_type": request.args.get("event_type"),
        "source": request.args.get("source"),
        "session_id": request.args.get("session_id"),
        "min_confidence": (
            None if min_confidence in (None, "") else float(min_confidence)
        ),
        "start": request.args.get("start"),
        "end": request.args.get("end"),
        "limit": int(request.args.get("limit", "100")),
    }
    if options["min_confidence"] is not None and not 0 <= options["min_confidence"] <= 1:
        raise ValueError("min_confidence must be between 0 and 1")
    return options


def create_analytics_blueprint(service: AnalyticsService) -> Blueprint:
    bp = Blueprint("analytics", __name__)

    @bp.route("/analytics", methods=["GET"])
    def dashboard():
        return render_template("analytics.html")

    @bp.route("/analytics/events", methods=["GET"])
    def events():
        try:
            service.collect()
            items = service.store.query(**_query_options())
        except (TypeError, ValueError) as error:
            return jsonify({"ok": False, "error": str(error)}), 400
        return jsonify({"events": [item.to_dict() for item in items]})

    @bp.route("/analytics/summary", methods=["GET"])
    def summary():
        service.collect()
        return jsonify(service.store.summary())

    @bp.route("/analytics/export.csv", methods=["GET"])
    def export_csv():
        try:
            service.collect()
            items = service.store.query(**_query_options())
        except (TypeError, ValueError) as error:
            return jsonify({"ok": False, "error": str(error)}), 400
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "event_id",
                "timestamp",
                "category",
                "event_type",
                "source",
                "confidence",
                "session_id",
                "details",
            ]
        )
        for event in items:
            payload = event.to_dict()
            writer.writerow(
                [
                    payload["event_id"],
                    payload["timestamp"],
                    payload["category"],
                    payload["event_type"],
                    payload["source"],
                    payload["confidence"],
                    payload["session_id"],
                    json.dumps(payload["details"], sort_keys=True),
                ]
            )
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=progress-claw-analytics.csv"
            },
        )

    return bp
