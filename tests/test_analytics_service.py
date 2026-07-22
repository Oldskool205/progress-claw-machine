import time
import unittest

from analytics.service import AnalyticsService
from game.state_cache import GameStateCache
from game.state_models import GameState
from recommendation.cache import RecommendationCache
from recommendation.models import Recommendation, RecommendationType
from vision.detection_cache import DetectionCache
from vision.detection_models import DetectedObject


class AnalyticsServiceTest(unittest.TestCase):
    def make_service(self, runtime_status=None):
        detection = DetectionCache()
        game = GameStateCache()
        recommendation = RecommendationCache()
        service = AnalyticsService(
            runtime_status_provider=lambda: runtime_status
            or {
                "status": "ready",
                "running": False,
                "arduino_connected": True,
                "emergency_stopped": False,
                "last_error": None,
            },
            detection_cache=detection,
            game_state_cache=game,
            recommendation_cache=recommendation,
        )
        return service, detection, game, recommendation

    def test_collects_each_public_service_without_duplicates(self):
        service, detection, game, recommendation = self.make_service()
        now = time.time()
        detection.update(
            timestamp=now,
            frame_id=7,
            objects=[DetectedObject("prize", 0.88, [1, 2, 3, 4], now)],
        )
        game.transition(GameState.PLAYING, confidence=0.9, source="test")
        recommendation.update(
            Recommendation(
                recommendation=RecommendationType.NO_ACTION,
                confidence=0.8,
                reason="Playing safely",
            )
        )

        service.collect()
        first_total = service.store.summary()["total_events"]
        service.collect()

        self.assertEqual(service.store.summary()["total_events"], first_total)
        categories = service.store.summary()["by_category"]
        self.assertGreaterEqual(categories["runtime"], 1)
        self.assertGreaterEqual(categories["vision"], 1)
        self.assertGreaterEqual(categories["game_state"], 1)
        self.assertGreaterEqual(categories["recommendation"], 1)

    def test_faulted_runtime_is_visible_as_safety_event(self):
        service, _, _, _ = self.make_service(
            {
                "status": "fault",
                "running": False,
                "arduino_connected": False,
                "emergency_stopped": False,
                "last_error": "serial unavailable",
            }
        )

        service.collect()

        safety = service.store.query(category="safety")
        self.assertEqual(len(safety), 1)
        self.assertEqual(safety[0].event_type, "runtime_safety_state")


if __name__ == "__main__":
    unittest.main()
