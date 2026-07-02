import unittest

from vision.camera_manager import CameraConfig, CameraManager
from vision.frame_queue import FrameQueue
from vision.stream_service import create_app


class HealthServiceTest(unittest.TestCase):
    def test_health_endpoint_returns_camera_status(self):
        manager = CameraManager(
            FrameQueue(),
            config=CameraConfig(width=1280, height=720, fps=30),
        )
        app = create_app(camera_manager=manager, start_camera=False)

        response = app.test_client().get("/vision/health")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["camera"], "disconnected")
        self.assertEqual(payload["fps"], 0.0)
        self.assertEqual(payload["resolution"], "1280x720")
        self.assertIsInstance(payload["uptime"], int)


if __name__ == "__main__":
    unittest.main()
