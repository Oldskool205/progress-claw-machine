import unittest

import cv2
import numpy as np

from vision.detector import DetectorConfig, YoloDetector, load_detector_config


def jpeg_frame():
    ok, encoded = cv2.imencode(".jpg", np.zeros((8, 8, 3), dtype=np.uint8))
    if not ok:
        raise RuntimeError("Failed to build test JPEG")
    return encoded.tobytes()


class FakeBox:
    cls = [0]
    conf = [0.94]
    xyxy = [[100, 120, 250, 500]]


class FakeResult:
    names = {0: "person"}
    boxes = [FakeBox()]


class FakeModel:
    def __init__(self):
        self.calls = 0

    def predict(self, image, conf, imgsz, device, verbose):
        self.calls += 1
        self.last_shape = image.shape
        self.last_conf = conf
        self.last_imgsz = imgsz
        self.last_device = device
        self.last_verbose = verbose
        return [FakeResult()]


class DetectorTest(unittest.TestCase):
    def test_loads_detector_config_from_camera_yaml(self):
        config = load_detector_config("config/camera.yaml")

        self.assertEqual(config.model_path, "yolov8n.pt")
        self.assertEqual(config.image_size, 640)
        self.assertEqual(config.device, "cpu")

    def test_detect_decodes_frame_and_maps_yolo_result(self):
        model = FakeModel()
        detector = YoloDetector(
            config=DetectorConfig(
                model_path="fake.pt",
                confidence_threshold=0.5,
                image_size=320,
                device="cpu",
            ),
            model_factory=lambda _path: model,
        )

        objects = detector.detect(jpeg_frame(), timestamp=123.0)

        self.assertEqual(model.calls, 1)
        self.assertEqual(model.last_conf, 0.5)
        self.assertEqual(model.last_imgsz, 320)
        self.assertEqual(model.last_device, "cpu")
        self.assertEqual(len(objects), 1)
        self.assertEqual(objects[0].class_name, "person")
        self.assertEqual(objects[0].confidence, 0.94)
        self.assertEqual(objects[0].bounding_box, [100.0, 120.0, 250.0, 500.0])
        self.assertEqual(objects[0].timestamp, 123.0)

    def test_invalid_frame_raises_without_opening_camera(self):
        detector = YoloDetector(
            config=DetectorConfig(model_path="fake.pt"),
            model_factory=lambda _path: FakeModel(),
        )

        with self.assertRaises(RuntimeError):
            detector.detect(b"not-a-jpeg", timestamp=123.0)


if __name__ == "__main__":
    unittest.main()
