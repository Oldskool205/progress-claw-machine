import unittest

from flask import Flask

from game.state_cache import GameStateCache
from game.state_models import GameState
from recommendation.api import create_recommendation_blueprint
from recommendation.engine import RecommendationConfig, RecommendationEngine
from vision.detection_cache import DetectionCache


def runtime_status():
    return {
        "status": "ready",
        "running": False,
        "play_mode": None,
        "arduino_connected": True,
        "last_error": None,
    }


class RecommendationApiTest(unittest.TestCase):
    def make_app(self):
        game_cache = GameStateCache()
        game_cache.transition(
            GameState.IDLE,
            confidence=1.0,
            source="test",
            details={},
        )
        engine = RecommendationEngine(
            game_cache,
            DetectionCache(),
            runtime_status_provider=runtime_status,
            config=RecommendationConfig(idle_demo_timeout=60),
        )
        app = Flask(__name__)
        app.register_blueprint(create_recommendation_blueprint(engine))
        return app

    def test_current_endpoint_returns_json_recommendation(self):
        response = self.make_app().test_client().get("/recommendation/current")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIn("recommendation", payload)
        self.assertEqual(payload["source"], "RecommendationEngine")

    def test_history_endpoint_returns_json_history(self):
        response = self.make_app().test_client().get("/recommendation/history")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIn("recommendations", payload)
        self.assertGreaterEqual(len(payload["recommendations"]), 1)


if __name__ == "__main__":
    unittest.main()
