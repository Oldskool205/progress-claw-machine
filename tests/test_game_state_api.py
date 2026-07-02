import time
import unittest

from flask import Flask

from game.events import create_game_state_blueprint
from game.state_engine import GameStateConfig, GameStateEngine
from vision.detection_cache import DetectionCache
from vision.detection_models import DetectedObject


def runtime_status():
    return {
        "status": "ready",
        "running": False,
        "play_mode": None,
        "play_started_at": None,
        "play_ends_at": None,
        "emergency_stopped": False,
        "last_error": None,
    }


class GameStateApiTest(unittest.TestCase):
    def make_app(self):
        cache = DetectionCache()
        cache.update(
            timestamp=time.time(),
            frame_id=10,
            objects=[DetectedObject("person", 0.95, [1, 1, 2, 2], time.time())],
        )
        engine = GameStateEngine(
            cache,
            runtime_status_provider=runtime_status,
            config=GameStateConfig(idle_timeout_seconds=1.0),
        )
        app = Flask(__name__)
        app.register_blueprint(create_game_state_blueprint(engine))
        return app

    def test_game_state_endpoint_returns_latest_state(self):
        app = self.make_app()

        response = app.test_client().get("/game/state")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["state"], "PLAYER_PRESENT")
        self.assertEqual(payload["source"], "vision")

    def test_game_events_endpoint_returns_recent_events(self):
        app = self.make_app()

        response = app.test_client().get("/game/events")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIn("events", payload)
        self.assertGreaterEqual(len(payload["events"]), 1)


if __name__ == "__main__":
    unittest.main()
