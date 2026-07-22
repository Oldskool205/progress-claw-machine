import unittest

from flask import Flask

from analytics.api import create_analytics_blueprint
from analytics.service import AnalyticsService
from game.state_cache import GameStateCache
from recommendation.cache import RecommendationCache
from vision.detection_cache import DetectionCache


class AnalyticsApiTest(unittest.TestCase):
    def make_app(self):
        service = AnalyticsService(
            runtime_status_provider=lambda: {
                "status": "ready",
                "running": False,
                "arduino_connected": True,
                "emergency_stopped": False,
                "last_error": None,
            },
            detection_cache=DetectionCache(),
            game_state_cache=GameStateCache(),
            recommendation_cache=RecommendationCache(),
        )
        app = Flask(__name__)
        app.register_blueprint(create_analytics_blueprint(service))
        return app

    def test_events_and_summary_are_read_only(self):
        client = self.make_app().test_client()

        events = client.get("/analytics/events")
        summary = client.get("/analytics/summary")

        self.assertEqual(events.status_code, 200)
        self.assertIn("events", events.get_json())
        self.assertEqual(summary.status_code, 200)
        self.assertEqual(summary.get_json()["storage"], "memory")
        self.assertEqual(client.post("/analytics/events", json={}).status_code, 405)

    def test_filters_validate_input(self):
        client = self.make_app().test_client()

        response = client.get("/analytics/events?limit=not-a-number")
        invalid_confidence = client.get(
            "/analytics/events?min_confidence=1.5"
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.get_json()["ok"])
        self.assertEqual(invalid_confidence.status_code, 400)

    def test_csv_export_has_stable_schema(self):
        response = self.make_app().test_client().get("/analytics/export.csv")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "text/csv")
        self.assertIn("event_id,timestamp,category,event_type", response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
