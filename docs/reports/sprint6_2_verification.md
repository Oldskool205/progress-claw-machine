# Sprint 6.2 Verification

Date: 2026-07-02

## Verification Results

Sprint 6.2 adds a YOLO Detection Service that consumes frames from `FrameQueue`
and publishes the latest result through the Vision API.

Verified constraints:

- `CameraManager` remains the only camera owner.
- YOLO code does not open `VideoCapture`.
- Detection consumes `FrameQueue` frames only.
- Detection does not communicate with Arduino.
- Detection does not communicate with `RuntimeController`.
- Dashboard UI and existing Dashboard APIs were not modified.
- Existing Vision Service health, snapshot, and stream behavior remains present.

## Tests

Compile command:

```bash
python3 -m py_compile main.py vision/*.py dashboard/backend/*.py
```

Result: Passed.

Unit test command:

```bash
python3 -m unittest discover -s tests
```

Result:

```text
Ran 31 tests in 0.801s
OK
```

New test coverage:

- `tests/test_detector.py`
- `tests/test_detection_cache.py`
- `tests/test_detection_api.py`

The detector tests use mocked YOLO model objects and generated in-memory JPEG frames.
They do not require a physical camera.

## Endpoint Verification

Runtime command:

```bash
VISION_PORT=5156 python3 -m vision.stream_service
```

Endpoint checks:

```text
/vision/health 200 application/json {"camera":"disconnected","fps":0.0,"last_error":"Camera failed to open","last_frame_at":null,"resolution":"1280x720","uptime":9}
/vision/snapshot 503 text/html; charset=utf-8 Camera frame unavailable
/vision/detections 200 application/json {"frame_id":null,"objects":[],"timestamp":null}
```

`/vision/snapshot` returned `503` because `/dev/video0` is unavailable in this
environment. This matches existing Sprint 6.1 behavior when no camera frame is present.

## Performance

- Detection runs in a daemon thread.
- Detection reads from latest-only `FrameQueue`.
- Old frames are discarded by design.
- Detection results are stored in latest-only `DetectionCache`.
- The configured inference interval is `0.1` seconds, targeting up to 10 FPS.
- Inference logging includes model load, inference time, estimated FPS, detection count,
  and errors.

## Known Limitations

- The local verification environment does not have `ultralytics` installed, so real
  YOLO model loading logs a graceful load failure here.
- `requirements.txt` now includes `ultralytics` for deployments that run real YOLOv8
  inference.
- Camera endpoint verification was limited by unavailable `/dev/video0`.
- Tracking IDs are reserved as `tracking_id` but not implemented yet.
- Detection history is not retained; only the latest result is cached.
