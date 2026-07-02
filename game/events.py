"""Flask routes for Game State Engine API."""

from __future__ import annotations

from flask import Blueprint, jsonify

from game.state_engine import GameStateEngine


def create_game_state_blueprint(engine: GameStateEngine) -> Blueprint:
    bp = Blueprint("game_state", __name__)

    @bp.route("/game/state", methods=["GET"])
    def game_state():
        return jsonify(engine.evaluate())

    @bp.route("/game/events", methods=["GET"])
    def game_events():
        engine.evaluate()
        return jsonify(engine.events())

    return bp
