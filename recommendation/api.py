"""Flask routes for Recommendation Engine."""

from __future__ import annotations

from flask import Blueprint, jsonify

from recommendation.engine import RecommendationEngine


def create_recommendation_blueprint(engine: RecommendationEngine) -> Blueprint:
    bp = Blueprint("recommendation", __name__)

    @bp.route("/recommendation/current", methods=["GET"])
    def current():
        return jsonify(engine.evaluate())

    @bp.route("/recommendation/history", methods=["GET"])
    def history():
        engine.evaluate()
        return jsonify(engine.history())

    return bp
