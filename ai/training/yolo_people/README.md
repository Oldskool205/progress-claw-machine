# YOLO People Training

This folder is for training a YOLO person detector on real claw-machine camera
photos.

## Purpose

Train or fine-tune a detector that counts people in player/crowd photos. The
dashboard uses the detected people count for AI Crowd Bonus grabber power:

| AI people count | Grabber hold power |
| --- | --- |
| 0-1 | 60% |
| 2-3 | 70% |
| 4 | 80% |
| 5+ | 90% |

## Folder Layout

```text
yolo_people/
  raw_photos/          # Original uncropped photos from the real machine
  dataset/
    images/
      train/
      val/
      test/
    labels/
      train/
      val/
      test/
  data.yaml            # YOLO dataset config
  runs/                # Training logs and intermediate outputs
  exports/             # Exported models for deployment
```

## Labeling Rule

The dashboard automatically saves every accepted player photo into
`raw_photos/` for future labeling. Each saved image has a matching metadata
file:

```text
raw_photos/20260701-103000-player-name-1780000000000.jpg
raw_photos/20260701-103000-player-name-1780000000000.json
```

The JSON metadata records the player name, capture source, timestamp, and
current OpenCV AI count. These raw photos are not training labels yet.

Use one class only:

```text
person
```

Each visible person should get one bounding box. Save labels in YOLO text
format beside the matching image split:

```text
dataset/images/train/example001.jpg
dataset/labels/train/example001.txt
```

## Suggested Collection Target

Collect real photos from the actual camera position and lighting:

```text
0 people:    50+ photos
1 person:    50+ photos
2-3 people:  50+ photos
4 people:    50+ photos
5+ people:   50+ photos
```

## Training Command

Example command after installing YOLO tooling:

```sh
yolo detect train data=ai/training/yolo_people/data.yaml model=yolov8n.pt epochs=50 imgsz=640 project=ai/training/yolo_people/runs name=people
```

After training, copy the best model to:

```text
ai/models/yolo_people/best.pt
```
