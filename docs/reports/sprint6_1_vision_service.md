# Sprint 6.1 Vision Service Foundation

## Summary

Sprint 6.1 creates an independent Vision Service foundation for Progress Claw
OS. The service owns camera access, latest-frame storage, health reporting,
snapshot delivery, and MJPEG streaming.

This sprint does not implement YOLO, object detection, AI decisions, dashboard
UI changes, RuntimeController changes, or Arduino communication changes.

## Architecture

The Vision Service is isolated from hardware control.

```text
Dashboard
   |
   v
Vision API
   |
   v
Vision Service
   |
   v
Camera
```

Control architecture remains unchanged:

```text
Dashboard
   |
   v
REST API
   |
   v
RuntimeController
   |
   v
Arduino
```

Safety boundaries:

- Camera code never controls Arduino.
- Vision Service never calls RuntimeController.
- Dashboard image access is through Vision API endpoints.
- AI services will consume Vision Service outputs in Sprint 6.2.

## Components

- `vision/camera_manager.py`: opens the camera, configures resolution/FPS,
  detects disconnects, reconnects, monitors FPS, encodes JPEG frames, and
  releases camera resources on shutdown.
- `vision/frame_queue.py`: thread-safe latest-frame queue with no unbounded
  buffering.
- `vision/stream_service.py`: independent Flask app, MJPEG streaming endpoint,
  app factory, and Vision Service logging setup.
- `vision/snapshot_service.py`: JPEG snapshot endpoint.
- `vision/health.py`: health endpoint.
- `config/camera.yaml`: camera configuration.

## Data Flow

```text
Camera
  |
  v
CameraManager
  |
  v
FrameQueue latest frame
  |
  +--> GET /vision/snapshot
  |
  +--> GET /vision/stream
  |
  +--> future Sprint 6.2 AI/YOLO consumer
```

The frame queue stores only the newest JPEG frame. Slow viewers do not build up
memory because each viewer waits for the next available frame sequence.

## API

### `GET /vision/health`

Returns camera service health.

Example:

```json
{
  "camera": "connected",
  "fps": 30,
  "resolution": "1280x720",
  "uptime": 1234,
  "last_frame_at": 1782990000.0,
  "last_error": null
}
```

`camera` is `connected` or `disconnected`.

### `GET /vision/snapshot`

Returns the latest camera frame as `image/jpeg`.

If no frame is available, the endpoint returns `503`.

### `GET /vision/stream`

Returns an MJPEG stream with MIME type:

```text
multipart/x-mixed-replace; boundary=frame
```

Multiple dashboard viewers are supported because each response gets its own
generator and reads from the shared latest-frame queue.

## Configuration

Camera settings live in `config/camera.yaml`.

```yaml
resolution: 1280x720
fps: 30
device_id: 0
rotation: 0
mirror: false
reconnect_delay_seconds: 2
```

Fields:

- `resolution`: width and height as `WIDTHxHEIGHT`.
- `fps`: requested capture FPS.
- `device_id`: OpenCV camera device index or path.
- `rotation`: optional frame rotation in degrees: `0`, `90`, `180`, or `270`.
- `mirror`: horizontal mirror toggle.
- `reconnect_delay_seconds`: delay before reconnect attempts.

The service also supports:

- `CLAW_CAMERA_CONFIG`: alternate camera config path.
- `CLAW_LOG_DIR`: alternate log directory.
- `VISION_HOST`: Flask bind host for standalone service.
- `VISION_PORT`: Flask port for standalone service.

Run standalone:

```text
python3 -m vision.stream_service
```

Default port is `5100`.

## Logging

Vision Service logs to `vision.log` in `CLAW_LOG_DIR` or `logs/` by default.

Logged events include:

- camera opened
- camera connected
- camera disconnected
- reconnect attempts
- FPS changes
- camera errors
- camera release errors

## Tests

New test coverage:

- `tests/test_camera_manager.py`
  - config loading
  - reconnect after disconnect
  - clean shutdown releases capture
- `tests/test_frame_queue.py`
  - latest-frame-only behavior
  - blocking wait for next frame
  - non-bytes rejection
- `tests/test_snapshot.py`
  - snapshot JPEG response
  - snapshot unavailable response
  - MJPEG frame formatting
- `tests/test_health.py`
  - health endpoint payload

All tests use mock cameras or preloaded frames. No physical camera is required.

Verification command:

```text
CLAW_LOG_DIR=/tmp/progress-claw-test-logs \
PYTHONPYCACHEPREFIX=/tmp/progress-claw-pycache \
CLAW_ARDUINO_MOCK=1 \
python3 -m unittest discover -s tests
```

Result:

```text
Ran 23 tests
OK
```

## Known Limitations

- This sprint does not integrate YOLO or any object detection.
- This sprint does not change the dashboard UI to consume `/vision/*`
  endpoints.
- FPS is observed from the capture loop and may differ from the requested camera
  FPS depending on hardware and driver behavior.
- OpenCV camera support depends on Raspberry Pi camera drivers and device
  availability.
- The Vision Service is independent; production deployment should add a systemd
  unit in a later service-packaging sprint.
