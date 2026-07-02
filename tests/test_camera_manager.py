import logging
import time
import unittest

from vision.camera_manager import CameraConfig, CameraManager, load_camera_config
from vision.frame_queue import FrameQueue

JPEG_FRAME = b"\xff\xd8mock-jpeg\xff\xd9"


class ScriptedCapture:
    def __init__(self, reads, opened=True, delay=0.0):
        self.reads = list(reads)
        self.opened = opened
        self.delay = delay
        self.released = False

    def is_opened(self):
        return self.opened

    def read(self):
        if self.delay:
            time.sleep(self.delay)
        if not self.reads:
            return True, JPEG_FRAME
        return self.reads.pop(0)

    def release(self):
        self.released = True


class CameraManagerTest(unittest.TestCase):
    def test_loads_camera_config(self):
        config = load_camera_config("config/camera.yaml")

        self.assertEqual(config.resolution, "1280x720")
        self.assertEqual(config.fps, 30)

    def test_reconnects_after_disconnect(self):
        queue = FrameQueue()
        captures = [
            ScriptedCapture([(True, JPEG_FRAME), (False, None)]),
            ScriptedCapture([(True, b"\xff\xd8reconnected\xff\xd9")], delay=0.01),
        ]

        def factory(_config):
            return captures.pop(0)

        manager = CameraManager(
            queue,
            config=CameraConfig(reconnect_delay_seconds=0.01),
            capture_factory=factory,
            logger=logging.getLogger("progress_claw.vision.test"),
        )

        manager.start()
        reconnected_frame = queue.wait_for_next(last_sequence=1, timeout=1.0)
        manager.stop()

        self.assertIsNotNone(reconnected_frame)
        self.assertEqual(reconnected_frame.data, b"\xff\xd8reconnected\xff\xd9")

    def test_clean_shutdown_releases_capture(self):
        queue = FrameQueue()
        capture = ScriptedCapture([(True, JPEG_FRAME)], delay=0.01)
        manager = CameraManager(
            queue,
            config=CameraConfig(reconnect_delay_seconds=0.01),
            capture_factory=lambda _config: capture,
            logger=logging.getLogger("progress_claw.vision.test"),
        )

        manager.start()
        self.assertIsNotNone(queue.wait_for_next(timeout=1.0))
        manager.stop()

        self.assertTrue(capture.released)


if __name__ == "__main__":
    unittest.main()
