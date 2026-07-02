"""Rule helpers for Recommendation Engine."""

from __future__ import annotations

from typing import Any

from game.state_models import GameState
from recommendation.models import RecommendationType


def state_value(game_state: Any) -> str:
    if isinstance(game_state, dict):
        return str(game_state.get("state", ""))
    state = getattr(game_state, "state", "")
    return state.value if hasattr(state, "value") else str(state)


def is_vision_unavailable(game_state: dict[str, Any], detection: Any) -> bool:
    details = game_state.get("details", {}) if isinstance(game_state, dict) else {}
    if details.get("reason") == "detection_unavailable":
        return True
    return getattr(detection, "timestamp", None) is None


def is_system_degraded(
    game_state: dict[str, Any], runtime_status: dict[str, Any]
) -> bool:
    state = state_value(game_state)
    if state == GameState.ERROR.value:
        return True
    if runtime_status.get("status") == "fault":
        return True
    return bool(runtime_status.get("last_error"))


def disconnected_arduino(runtime_status: dict[str, Any]) -> bool:
    return not bool(runtime_status.get("arduino_connected", True))


def recommendation_reason(recommendation: RecommendationType) -> str:
    return {
        RecommendationType.NO_ACTION: "No higher-priority recommendation is available",
        RecommendationType.WAIT_FOR_PLAYER: "Waiting for a player",
        RecommendationType.READY_TO_START: "Player detected for configured ready window",
        RecommendationType.START_DEMO_MODE: "Machine has been idle beyond demo timeout",
        RecommendationType.STOP_DEMO_MODE: "Player is present while demo mode can stop",
        RecommendationType.CHECK_CAMERA: "Vision or detection data is unavailable",
        RecommendationType.CHECK_ARDUINO: "Arduino is disconnected",
        RecommendationType.SYSTEM_DEGRADED: "Runtime or game state reports degraded status",
        RecommendationType.INCREASE_CLAW_POWER: "Gameplay signal suggests claw power may be low",
        RecommendationType.REDUCE_CLAW_POWER: "Gameplay signal suggests claw power may be high",
    }[recommendation]
