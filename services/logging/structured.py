"""Structured logging setup."""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in (
            "event",
            "command",
            "response",
            "ok",
            "port",
            "baud_rate",
            "source",
            "reason",
            "error",
        ):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload, sort_keys=True)


class EventFilter(logging.Filter):
    def __init__(
        self,
        *,
        logger_prefix: str | None = None,
        event_prefix: str | None = None,
        event_name: str | None = None,
    ) -> None:
        super().__init__()
        self.logger_prefix = logger_prefix
        self.event_prefix = event_prefix
        self.event_name = event_name

    def filter(self, record: logging.LogRecord) -> bool:
        if self.logger_prefix and record.name.startswith(self.logger_prefix):
            return True
        event = getattr(record, "event", "")
        if self.event_name and event == self.event_name:
            return True
        if self.event_prefix and event.startswith(self.event_prefix):
            return True
        return False


def _json_handler(handler: logging.Handler) -> logging.Handler:
    handler.setFormatter(JsonFormatter())
    handler._progress_claw_json = True
    return handler


def _file_handler(path: str, log_filter: logging.Filter) -> logging.Handler:
    handler = logging.FileHandler(path)
    handler.addFilter(log_filter)
    return _json_handler(handler)


def configure_logging(level: int = logging.INFO) -> None:
    root = logging.getLogger()
    if any(getattr(handler, "_progress_claw_json", False) for handler in root.handlers):
        return
    log_dir = os.getenv("CLAW_LOG_DIR", "logs")
    os.makedirs(log_dir, exist_ok=True)

    root.addHandler(_json_handler(logging.StreamHandler(sys.stdout)))
    root.addHandler(
        _json_handler(logging.FileHandler(os.path.join(log_dir, "system.log")))
    )
    root.addHandler(
        _file_handler(
            os.path.join(log_dir, "command.log"),
            EventFilter(event_name="controller_command"),
        )
    )
    root.addHandler(
        _file_handler(
            os.path.join(log_dir, "arduino.log"),
            EventFilter(logger_prefix="progress_claw.controller.arduino"),
        )
    )
    root.addHandler(
        _file_handler(
            os.path.join(log_dir, "safety.log"),
            EventFilter(event_prefix="safety_"),
        )
    )
    root.setLevel(level)
