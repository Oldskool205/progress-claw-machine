import unittest

from vision.frame_queue import FrameQueue
from vision.stream_service import create_app, mjpeg_frames

JPEG_FRAME = b"\xff\xd8snapshot\xff\xd9"


class SnapshotServiceTest(unittest.TestCase):
    def test_snapshot_returns_latest_jpeg(self):
        queue = FrameQueue()
        queue.put(JPEG_FRAME)
        app = create_app(
            frame_queue=queue,
            start_camera=False,
            start_detection=False,
        )

        response = app.test_client().get("/vision/snapshot")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "image/jpeg")
        self.assertEqual(response.data, JPEG_FRAME)

    def test_snapshot_returns_unavailable_without_frame(self):
        app = create_app(
            frame_queue=FrameQueue(),
            start_camera=False,
            start_detection=False,
        )

        response = app.test_client().get("/vision/snapshot")

        self.assertEqual(response.status_code, 503)

    def test_mjpeg_stream_formats_frame(self):
        queue = FrameQueue()
        stream = mjpeg_frames(queue, timeout=0.01)
        queue.put(JPEG_FRAME)

        chunk = next(stream)

        self.assertIn(b"--frame", chunk)
        self.assertIn(b"Content-Type: image/jpeg", chunk)
        self.assertIn(JPEG_FRAME, chunk)


if __name__ == "__main__":
    unittest.main()
