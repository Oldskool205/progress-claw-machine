import threading
import unittest

from vision.detection_cache import DetectionCache
from vision.detection_models import DetectedObject


class DetectionCacheTest(unittest.TestCase):
    def test_latest_result_defaults_to_empty(self):
        cache = DetectionCache()

        payload = cache.to_dict()

        self.assertIsNone(payload["timestamp"])
        self.assertIsNone(payload["frame_id"])
        self.assertEqual(payload["objects"], [])

    def test_update_replaces_latest_detection(self):
        cache = DetectionCache()
        first = DetectedObject("person", 0.9, [1, 2, 3, 4], 100.0)
        second = DetectedObject("cell phone", 0.8, [5, 6, 7, 8], 101.0)

        cache.update(timestamp=100.0, frame_id=1, objects=[first])
        cache.update(timestamp=101.0, frame_id=2, objects=[second])

        payload = cache.to_dict()
        self.assertEqual(payload["frame_id"], 2)
        self.assertEqual(len(payload["objects"]), 1)
        self.assertEqual(payload["objects"][0]["class"], "cell phone")

    def test_updates_are_thread_safe(self):
        cache = DetectionCache()

        def update(frame_id):
            obj = DetectedObject("person", 0.5, [0, 0, 1, 1], float(frame_id))
            cache.update(timestamp=float(frame_id), frame_id=frame_id, objects=[obj])

        threads = [
            threading.Thread(target=update, args=(frame_id,)) for frame_id in range(20)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertIn(cache.latest().frame_id, range(20))


if __name__ == "__main__":
    unittest.main()
