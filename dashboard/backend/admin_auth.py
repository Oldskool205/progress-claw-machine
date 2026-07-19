"""Short-lived administrator authentication without privileged system actions."""

from __future__ import annotations

import hmac
import threading
import time
from collections import defaultdict, deque
from functools import wraps

from flask import current_app, jsonify, session


SESSION_KEY = "progress_claw_admin_expires_at"
MAX_ATTEMPTS = 5
ATTEMPT_WINDOW_SECONDS = 300
SESSION_SECONDS = 300

_attempts = defaultdict(deque)
_attempt_lock = threading.Lock()


def is_configured() -> bool:
    return bool(current_app.config.get("ADMIN_PIN")) and bool(current_app.secret_key)


def authenticated(now: float | None = None) -> bool:
    if not is_configured():
        return False
    current_time = time.time() if now is None else now
    expires_at = float(session.get(SESSION_KEY, 0))
    if expires_at <= current_time:
        session.pop(SESSION_KEY, None)
        return False
    return True


def session_status(now: float | None = None) -> dict:
    current_time = time.time() if now is None else now
    configured = is_configured()
    active = authenticated(current_time)
    expires_at = float(session.get(SESSION_KEY, 0)) if active else 0
    return {
        "ok": True,
        "configured": configured,
        "authenticated": active,
        "expires_in": max(0, int(expires_at - current_time)),
    }


def authenticate(pin: str, client_key: str, now: float | None = None) -> tuple[bool, int]:
    current_time = time.time() if now is None else now
    with _attempt_lock:
        attempts = _attempts[client_key]
        while attempts and attempts[0] <= current_time - ATTEMPT_WINDOW_SECONDS:
            attempts.popleft()
        if len(attempts) >= MAX_ATTEMPTS:
            retry_after = max(1, int(ATTEMPT_WINDOW_SECONDS - (current_time - attempts[0])))
            return False, retry_after

        expected_pin = str(current_app.config.get("ADMIN_PIN", ""))
        if not hmac.compare_digest(pin, expected_pin):
            attempts.append(current_time)
            return False, 0

        attempts.clear()
        session[SESSION_KEY] = current_time + int(
            current_app.config.get("ADMIN_SESSION_SECONDS", SESSION_SECONDS)
        )
        return True, 0


def logout() -> None:
    session.pop(SESSION_KEY, None)


def require_admin(view):
    """Reject protected actions unless the short-lived admin session is active."""

    @wraps(view)
    def protected(*args, **kwargs):
        if not authenticated():
            return jsonify({"ok": False, "error": "Administrator login required"}), 401
        return view(*args, **kwargs)

    return protected


def clear_attempts_for_tests() -> None:
    with _attempt_lock:
        _attempts.clear()
