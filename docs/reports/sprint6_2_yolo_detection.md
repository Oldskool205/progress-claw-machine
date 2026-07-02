# Sprint 6.2 YOLO Detection Service

## Architecture

Sprint 6.2 adds an independent YOLO Detection Service inside the Vision Service boundary.
The camera remains owned only by `CameraManager`.

The new components are:

- `vision/detector.py`: lazy YOLOv8 model wrapper.
- `vision/detection_service.py`: background worker that consumes `FrameQueue`.
- `vision/detection_cache.py`: thread-safe latest-result cache.
- `vision/detection_models.py`: detection result data models.

The detector does not open `VideoCapture`, does not talk to Arduino, and does not use
`RuntimeController`.

## Data Flow

```text
CameraManager
  -> FrameQueue
  -> DetectionService
  -> YoloDetector
  -> DetectionCache
  -> GET /vision/detections
```

`FrameQueue` stores only the latest frame. `DetectionService` always re-reads the latest
available frame before inference, so stale frames are naturally discarded.

## Configuration

YOLO configuration is read from `config/camera.yaml`:

```yaml
yolo_model_path: yolov8n.pt
yolo_confidence_threshold: 0.25
yolo_image_size: 640
yolo_device: cpu
yolo_inference_interval_seconds: 0.1
```

The default interval targets up to 10 FPS inference without blocking camera capture or
Vision API requests.

## Vision API

`GET /vision/detections` returns the latest cached detection result:

```json
{
  "timestamp": 123.0,
  "frame_id": 1,
  "objects": [
    {
      "class": "person",
      "confidence": 0.94,
      "bbox": [100.0, 120.0, 250.0, 500.0],
      "timestamp": 123.0,
      "tracking_id": null
    }
  ]
}
```

If no detections have run yet, the endpoint returns an empty result with `objects: []`.

## Performance

- Inference runs in a daemon thread.
- Vision API requests are not blocked by inference.
- Camera capture is not blocked by inference.
- `FrameQueue` and `DetectionCache` each keep only the latest data.
- Inference time, estimated FPS, and detection count are logged to `vision.log`.

## Error Handling

The service catches and logs:

- camera unavailable
- model load failure
- invalid model path
- corrupted frame
- unexpected inference exception

Vision Service continues running if YOLO fails. The detection endpoint continues to
return the last successful cached result or an empty result if inference has not
succeeded yet.

## Known Limitations

- This development environment does not currently have the `ultralytics` package
  installed, so real YOLO loading cannot complete here until dependencies are installed.
- Tracking is reserved in the response as `tracking_id` but not implemented in Sprint 6.2.
- Only latest-frame detection is implemented; no detection history is retained.

## Future Extension

- Add object tracking IDs.
- Add model warmup and performance telemetry endpoints.
- Add configurable class filtering while keeping all YOLO classes available.
- Add hardware-specific tuning for Raspberry Pi acceleration.
