import unittest

from analytics.models import AnalyticsCategory, AnalyticsEvent
from analytics.store import AnalyticsStore


class AnalyticsStoreTest(unittest.TestCase):
    def test_store_is_bounded_and_deduplicates_events(self):
        store = AnalyticsStore(max_events=2)
        first = AnalyticsEvent(
            category=AnalyticsCategory.RUNTIME,
            event_type="ready",
            source="test",
        )
        self.assertTrue(store.add(first, dedupe_key="runtime:ready"))
        self.assertFalse(store.add(first, dedupe_key="runtime:ready"))
        store.add(
            AnalyticsEvent(
                category=AnalyticsCategory.SAFETY,
                event_type="fault",
                source="test",
            ),
            dedupe_key="safety:fault",
        )
        store.add(
            AnalyticsEvent(
                category=AnalyticsCategory.VISION,
                event_type="detection",
                source="test",
            ),
            dedupe_key="vision:1",
        )

        self.assertEqual(store.summary()["total_events"], 2)
        self.assertTrue(store.add(first, dedupe_key="runtime:ready"))

    def test_query_filters_category_confidence_and_time(self):
        store = AnalyticsStore()
        store.add(
            AnalyticsEvent(
                category=AnalyticsCategory.VISION,
                event_type="detection",
                source="test",
                timestamp="2026-07-20T01:00:00+00:00",
                confidence=0.9,
                session_id="play-1",
            )
        )
        store.add(
            AnalyticsEvent(
                category=AnalyticsCategory.RUNTIME,
                event_type="ready",
                source="test",
                timestamp="2026-07-20T00:00:00+00:00",
            )
        )

        events = store.query(
            category="vision",
            session_id="play-1",
            min_confidence=0.8,
            start="2026-07-20T00:30:00Z",
        )

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "detection")

    def test_invalid_query_is_rejected(self):
        store = AnalyticsStore()
        with self.assertRaisesRegex(ValueError, "Invalid ISO-8601"):
            store.query(start="yesterday")
        with self.assertRaisesRegex(ValueError, "limit"):
            store.query(limit=0)


if __name__ == "__main__":
    unittest.main()
