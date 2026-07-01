# Camera

The camera module contains camera setup, capture, calibration, and image-processing structure.

Current AI camera role:

- provide live preview to the dashboard
- capture the player photo used for AI Crowd Bonus people counting
- support future live people counting for AI Crowd Bonus power mode

Current implementation counts people after `/api/capture-player` or
`/api/player-photo` saves the player photo. The dashboard runs OpenCV HOG person
detection on the captured JPEG and updates `AI PEOPLE`.

The same original captured JPEG is copied to the YOLO collection folder:

```text
ai/training/yolo_people/raw_photos/
```

Use those collected photos for later labeling and training.

Future live people-count pipelines should report only the count to the
dashboard:

```text
POST /api/ai-count
{"people": 4}
```

The dashboard then decides grabber hold power from the agreed business tiers.
Camera code should not control Arduino pins, Raspberry Pi GPIO, or grabber
power directly.

## Subfolders

- `capture/`: camera input and frame capture code
- `calibration/`: lens, angle, position, and color calibration files
- `processing/`: frame processing and image preparation logic
- `snapshots/`: saved images for debugging and tests

Camera-specific code should stay isolated so the camera hardware can be changed later.
