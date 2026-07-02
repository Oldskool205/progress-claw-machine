import threading
import unittest

from vision.frame_queue import FrameQueue


class FrameQueueTest(unittest.TestCase):
    def test_keeps_latest_frame_only(self):
        queue = FrameQueue()

        first = queue.put(b"first", timestamp=1.0)
        second = queue.put(b"second", timestamp=2.0)

        self.assertEqual(first.sequence, 1)
        self.assertEqual(second.sequence, 2)
        self.assertEqual(queue.latest().data, b"second")

    def test_wait_for_next_returns_new_frame(self):
        queue = FrameQueue()
        first = queue.put(b"first")
        observed = []

        def wait_for_frame():
            observed.append(queue.wait_for_next(first.sequence, timeout=1.0))

        thread = threading.Thread(target=wait_for_frame)
        thread.start()
        queue.put(b"second")
        thread.join(timeout=2.0)

        self.assertEqual(observed[0].data, b"second")

    def test_rejects_non_bytes_frame_data(self):
        queue = FrameQueue()

        with self.assertRaises(TypeError):
            queue.put("not-bytes")


if __name__ == "__main__":
    unittest.main()
