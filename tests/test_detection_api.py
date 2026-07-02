import time
import unittest

import cv2
import numpy as np

from vision.detection_cache import DetectionCache
from vision.detection_service import DetectionService
from vision.detector import DetectorConfig, YoloDetector
from vision.frame_queue import FrameQueue
from vision.stream_service import create_app


def jpeg_frame():
    ok, encoded = cv2.imencode(".jpg", np.zeros((8, 8, 3), dtype=np.uint8))
    if not ok:
        raise RuntimeError("Failed to build test JPEG")
    return encoded.tobytes()


class FakeBox:
    cls = [67]
    conf = [0.87]
    xyxy = [[10, 20, 30, 40]]


class FakeResult:
    names = {67: "cell phone"}
    boxes = [FakeBox()]


class FakeModel:
    def predict(self, image, conf, imgsz, device, verbose):
        return [FakeResult()]


class DetectionApiTest(unittest.TestCase):
    def test_detections_endpoint_returns_latest_cache(self):
        queue = FrameQueue()
        cache = DetectionCache()
        detector = YoloDetector(
            config=DetectorConfig(model_path="fake.pt", inference_interval_seconds=0.0),
            model_factory=lambda _path: FakeModel(),
        )
        service = DetectionService(
            queue,
            detector=detector,
            cache=cache,
            inference_interval_seconds=0.0,
        )
        app = create_app(
            frame_queue=queue,
            detection_cache=cache,
            detection_service=service,
            start_camera=False,
            start_detection=True,
        )

        queue.put(jpeg_frame(), timestamp=123.0)
        deadline = time.time() + 2.0
        payload = None
        while time.time() < deadline:
            response = app.test_client().get("/vision/detections")
            payload = response.get_json()
            if payload["objects"]:
                break
            time.sleep(0.01)
        service.stop()

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(payload["timestamp"])
        self.assertEqual(payload["frame_id"], 1)
        self.assertEqual(payload["objects"][0]["class"], "cell phone")
        self.assertEqual(payload["objects"][0]["bbox"], [10.0, 20.0, 30.0, 40.0])

    def test_detections_endpoint_available_without_detection_thread(self):
        app = create_app(
            frame_queue=FrameQueue(),
            start_camera=False,
            start_detection=False,
        )

        response = app.test_client().get("/vision/detections")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["objects"], [])


if __name__ == "__main__":
    unittest.main()
