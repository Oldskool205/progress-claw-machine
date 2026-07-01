# AI Vision

Vision and object detection logic lives here.

Current implemented vision output for the dashboard is a people count from the
player photo. The dashboard uses OpenCV HOG person detection after
`/api/player-photo` or `/api/capture-player` saves the photo.

The people count updates `AI PEOPLE` in the dashboard. If `POWER MODE` is set
to `AI Crowd Bonus`, it also updates the effective grabber hold power.

Every accepted player photo is also copied to:

```text
ai/training/yolo_people/raw_photos/
```

This folder is the collection source for future YOLO labeling/training. A JSON
metadata file is saved beside each image.

Future live people counters can send updated counts to the dashboard:

```text
POST /api/ai-count
{"people": 4}
```

The dashboard maps this count to grabber hold power when `POWER MODE` is set
to `AI Crowd Bonus`.

| AI people count | Grabber hold power |
| --- | --- |
| 0-1 | 60% |
| 2-3 | 70% |
| 4 | 80% |
| 5+ | 90% |

Implementation guidance for the next detector upgrade:

- Smooth people count over a short time window before posting updates.
- Avoid rapid power changes from a single bad frame.
- Clamp negative or invalid counts to 0 before sending.
- Send only the count; do not drive GPIO or Arduino pins from AI vision code.
