# Data Flow

This document describes how information moves through Progress Claw OS.

## Operator Control Flow

```text
Operator
   |
   v
dashboard/
   |
   v
controller/
   |
   v
arduino/
   |
   v
Motors / Claw / Lights / Sensors
```

1. Operator uses the dashboard.
2. Dashboard sends a high-level request such as move, stop, drop, or start session.
3. Controller validates the request.
4. Controller sends a safe command to Arduino.
5. Arduino controls hardware and reports status.

## AI Assist Flow

```text
camera/
   |
   v
ai/
   |
   v
dashboard/
   |
   v
arduino/
```

1. Camera captures a player photo.
2. Dashboard saves the photo and runs OpenCV people detection.
3. Dashboard updates `AI PEOPLE`.
4. Dashboard applies the agreed Crowd Bonus rule when AI mode is active.
5. Dashboard drives the effective grabber power GPIO bits.
6. Arduino applies that hold power when FlySky CH6 controls the grabber.

Future live AI camera services can also post count updates to `/api/ai-count`.

Current AI Crowd Bonus rule:

| AI people count | Grabber hold power |
| --- | --- |
| 0-1 | 60% |
| 2-3 | 70% |
| 4 | 80% |
| 5+ | 90% |

The startup three-trigger grabber pulse remains full power. AI-selected power
applies only to CH6 grabber hold power during play.

## Status Flow

```text
Arduino sensors
      |
      v
controller/
      |
      +--> dashboard/
      +--> system/logs
      +--> maintenance/reports
```

Hardware status should become visible in the dashboard and logs. Faults should also appear in maintenance records.

## Data Storage Flow

```text
camera snapshots -> data/raw/
processed frames  -> data/processed/
AI model files    -> data/models/ or assets/ai-models/
runtime logs      -> data/logs/
service logs      -> system/logs/ or services/logging/
maintenance notes -> maintenance/reports/
```

## Remote Management Flow

```text
Remote laptop/phone
      |
      v
Tailscale network
      |
      v
Raspberry Pi dashboard/services
```

Tailscale should be used for private remote access. Avoid exposing dashboard ports directly to the public internet.
