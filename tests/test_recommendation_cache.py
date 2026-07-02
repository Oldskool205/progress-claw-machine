import unittest

from recommendation.cache import RecommendationCache
from recommendation.models import Recommendation, RecommendationType


class RecommendationCacheTest(unittest.TestCase):
    def test_defaults_to_no_action(self):
        cache = RecommendationCache()

        payload = cache.latest_dict()

        self.assertEqual(payload["recommendation"], "NO_ACTION")
        self.assertEqual(payload["source"], "initial")

    def test_update_replaces_latest_and_records_history(self):
        cache = RecommendationCache(max_history=3)
        recommendation = Recommendation(
            recommendation=RecommendationType.READY_TO_START,
            confidence=0.92,
            reason="Player ready",
        )

        cache.update(recommendation)

        self.assertEqual(cache.latest_dict()["recommendation"], "READY_TO_START")
        self.assertEqual(
            cache.history_dict()["recommendations"][0]["recommendation"],
            "READY_TO_START",
        )

    def test_history_is_bounded(self):
        cache = RecommendationCache(max_history=2)

        cache.update(
            Recommendation(
                RecommendationType.WAIT_FOR_PLAYER,
                0.7,
                "wait",
            )
        )
        cache.update(
            Recommendation(
                RecommendationType.READY_TO_START,
                0.9,
                "ready",
            )
        )
        cache.update(
            Recommendation(
                RecommendationType.START_DEMO_MODE,
                0.8,
                "demo",
            )
        )

        history = cache.history_dict()["recommendations"]
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["recommendation"], "START_DEMO_MODE")
        self.assertEqual(history[1]["recommendation"], "READY_TO_START")


if __name__ == "__main__":
    unittest.main()
