import unittest

from game.state_cache import GameStateCache
from game.state_models import GameState


class GameStateCacheTest(unittest.TestCase):
    def test_defaults_to_idle(self):
        cache = GameStateCache()

        latest = cache.latest_dict()

        self.assertEqual(latest["state"], "IDLE")
        self.assertEqual(latest["source"], "initial")

    def test_transition_updates_latest_and_events(self):
        cache = GameStateCache(max_events=3)

        cache.transition(
            GameState.PLAYER_PRESENT,
            confidence=0.91,
            source="vision",
            details={"player_count": 1},
        )

        latest = cache.latest_dict()
        events = cache.events_dict()["events"]
        self.assertEqual(latest["state"], "PLAYER_PRESENT")
        self.assertEqual(latest["confidence"], 0.91)
        self.assertEqual(events[0]["state"], "PLAYER_PRESENT")

    def test_event_buffer_is_bounded(self):
        cache = GameStateCache(max_events=2)

        cache.transition(GameState.PLAYER_PRESENT, confidence=1.0, source="vision")
        cache.transition(GameState.PLAYING, confidence=1.0, source="runtime")
        cache.transition(GameState.TIMEOUT, confidence=1.0, source="timer")

        events = cache.events_dict()["events"]
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["state"], "TIMEOUT")
        self.assertEqual(events[1]["state"], "PLAYING")


if __name__ == "__main__":
    unittest.main()
