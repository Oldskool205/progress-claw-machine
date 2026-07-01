# AI

The AI module contains machine vision, decision-making, and automated play
logic.

Current AI-related behavior is the Crowd Bonus grabber-power rule. After a
player photo is taken, the dashboard runs an OpenCV people detector on that
photo, updates `AI PEOPLE`, and converts that count into the effective grabber
hold power when AI Crowd Bonus mode is active.

```text
AI camera people count -> dashboard -> grabber power GPIO bits -> Arduino
```

Current Crowd Bonus tiers:

| AI people count | Grabber hold power |
| --- | --- |
| 0-1 | 60% |
| 2-3 | 70% |
| 4 | 80% |
| 5+ | 90% |

The startup three-trigger grabber pulse remains full power. AI-selected power
applies only to FlySky CH6 grabber hold power during the play window.

The dashboard also accepts future live AI count updates at:

```text
POST /api/ai-count
{"people": 4}
```

## Subfolders

- `models/`: trained model files and model metadata
- `vision/`: object detection, frame analysis, and tracking logic
- `strategy/`: decision-making rules for automated claw movement
- `training/`: datasets, experiments, and training notes

AI should request high-level actions through the controller/business layers
instead of controlling hardware directly. For the current migrated dashboard,
the AI count is sent to the dashboard API and the dashboard owns the GPIO power
selection.
