import time
import unittest

from game.rules import PrizeZone
from game.state_engine import GameStateConfig, GameStateEngine, load_game_state_config
from vision.detection_cache import DetectionCache
from vision.detection_models import DetectedObject


def ready_status():
    return {
        "status": "ready",
        "running": False,
        "play_mode": None,
        "play_started_at": None,
        "play_ends_at": None,
        "emergency_stopped": False,
        "last_error": None,
    }


class GameStateEngineTest(unittest.TestCase):
    def make_engine(self, cache=None, runtime_status=None, config=None):
        return GameStateEngine(
            cache or DetectionCache(),
            runtime_status_provider=lambda: runtime_status or ready_status(),
            config=config
            or GameStateConfig(
                idle_timeout_seconds=0.05,
                detection_confidence_threshold=0.5,
                prize_zone=PrizeZone(0, 0, 100, 100),
                timeout_seconds=1.0,
            ),
        )

    def test_loads_game_state_config(self):
        config = load_game_state_config("config/game_state.yaml")

        self.assertEqual(config.player_presence_threshold, 1)
        self.assertEqual(config.state_update_interval_ms, 250)

    def test_person_detection_produces_player_present(self):
        cache = DetectionCache()
        cache.update(
            timestamp=time.time(),
            frame_id=7,
            objects=[DetectedObject("person", 0.91, [1, 2, 3, 4], time.time())],
        )
        engine = self.make_engine(cache=cache)

        payload = engine.evaluate()

        self.assertEqual(payload["state"], "PLAYER_PRESENT")
        self.assertEqual(payload["source"], "vision")
        self.assertEqual(payload["details"]["player_count"], 1)

    def test_player_count_change_is_reported(self):
        cache = DetectionCache()
        engine = self.make_engine(cache=cache)
        cache.update(
            timestamp=time.time(),
            frame_id=1,
            objects=[DetectedObject("person", 0.9, [1, 1, 2, 2], time.time())],
        )
        engine.evaluate()
        cache.update(
            timestamp=time.time(),
            frame_id=2,
            objects=[
                DetectedObject("person", 0.9, [1, 1, 2, 2], time.time()),
                DetectedObject("person", 0.92, [3, 3, 4, 4], time.time()),
            ],
        )

        payload = engine.evaluate()

        self.assertEqual(payload["state"], "PLAYER_COUNT_CHANGED")
        self.assertEqual(payload["details"]["player_count"], 2)

    def test_runtime_running_produces_playing(self):
        engine = self.make_engine(runtime_status={**ready_status(), "running": True})

        payload = engine.evaluate()

        self.assertEqual(payload["state"], "PLAYING")
        self.assertEqual(payload["source"], "runtime")

    def test_teddy_bear_in_prize_zone_produces_prize_detected(self):
        cache = DetectionCache()
        cache.update(
            timestamp=time.time(),
            frame_id=3,
            objects=[DetectedObject("teddy bear", 0.88, [10, 10, 20, 20], time.time())],
        )
        engine = self.make_engine(cache=cache)

        payload = engine.evaluate()

        self.assertEqual(payload["state"], "PRIZE_DETECTED")
        self.assertEqual(payload["source"], "vision")

    def test_timeout_produces_timeout(self):
        engine = self.make_engine(
            runtime_status={
                **ready_status(),
                "running": True,
                "play_started_at": time.time() - 10,
                "play_ends_at": time.time() - 1,
            }
        )

        payload = engine.evaluate()

        self.assertEqual(payload["state"], "TIMEOUT")

    def test_runtime_error_produces_error(self):
        engine = self.make_engine(
            runtime_status={**ready_status(), "last_error": "fault"}
        )

        payload = engine.evaluate()

        self.assertEqual(payload["state"], "ERROR")
        self.assertEqual(payload["source"], "runtime")


if __name__ == "__main__":
    unittest.main()
