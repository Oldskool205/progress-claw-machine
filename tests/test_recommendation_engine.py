import time
import unittest

from game.state_cache import GameStateCache
from game.state_models import GameState
from recommendation.engine import (
    RecommendationConfig,
    RecommendationEngine,
    load_recommendation_config,
)
from vision.detection_cache import DetectionCache


def runtime_status(**overrides):
    status = {
        "status": "ready",
        "running": False,
        "play_mode": None,
        "arduino_connected": True,
        "last_error": None,
    }
    status.update(overrides)
    return status


class RecommendationEngineTest(unittest.TestCase):
    def make_engine(self, state=GameState.IDLE, runtime=None, config=None):
        game_cache = GameStateCache()
        game_cache.transition(
            state,
            confidence=1.0,
            source="test",
            details={},
        )
        detection_cache = DetectionCache()
        detection_cache.update(
            timestamp=time.time(),
            frame_id=1,
            objects=[],
        )
        return RecommendationEngine(
            game_cache,
            detection_cache,
            runtime_status_provider=lambda: runtime or runtime_status(),
            config=config
            or RecommendationConfig(
                player_ready_seconds=0.01,
                idle_demo_timeout=0.01,
                arduino_timeout=0.01,
            ),
        )

    def test_loads_recommendation_config(self):
        config = load_recommendation_config("config/recommendation.yaml")

        self.assertEqual(config.recommendation_interval_ms, 500)
        self.assertEqual(config.player_ready_seconds, 3.0)

    def test_player_present_long_enough_recommends_ready_to_start(self):
        engine = self.make_engine(state=GameState.PLAYER_PRESENT)
        engine.evaluate()
        time.sleep(0.02)

        payload = engine.evaluate()

        self.assertEqual(payload["recommendation"], "READY_TO_START")
        self.assertEqual(payload["source"], "RecommendationEngine")

    def test_idle_long_enough_recommends_demo_mode(self):
        engine = self.make_engine(state=GameState.IDLE)
        engine.evaluate()
        time.sleep(0.02)

        payload = engine.evaluate()

        self.assertEqual(payload["recommendation"], "START_DEMO_MODE")

    def test_game_state_error_recommends_system_degraded(self):
        engine = self.make_engine(state=GameState.ERROR)

        payload = engine.evaluate()

        self.assertEqual(payload["recommendation"], "SYSTEM_DEGRADED")

    def test_vision_unavailable_recommends_check_camera(self):
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

        payload = engine.evaluate()

        self.assertEqual(payload["recommendation"], "CHECK_CAMERA")

    def test_arduino_disconnected_recommends_check_arduino(self):
        engine = self.make_engine(
            state=GameState.PLAYING,
            runtime=runtime_status(arduino_connected=False),
        )
        engine.evaluate()
        time.sleep(0.02)

        payload = engine.evaluate()

        self.assertEqual(payload["recommendation"], "CHECK_ARDUINO")


if __name__ == "__main__":
    unittest.main()
