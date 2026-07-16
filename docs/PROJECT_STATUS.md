# Project Status

Last updated: 2026-07-16

## Current Phase

Progress Claw OS has moved beyond the original Phase 2 scaffold. The repository
now contains a working local dashboard, matched Arduino firmware, camera capture
support, and an early YOLO people-count training pipeline.

The project is still in prototype/integration status. It should be treated as
hardware-facing software that requires supervised testing on the actual machine
before unattended operation.

## Implemented

- Flask dashboard backend in `dashboard/backend/app.py`.
- Browser dashboard UI in `dashboard/frontend/templates/index.html`.
- Static dashboard assets and player photo history under `dashboard/assets/`.
- Raspberry Pi GPIO dashboard play gate on BCM GPIO 17 to Arduino A0.
- Raspberry Pi GPIO grabber hold-power selection on BCM GPIO 22/23/24 to
  Arduino A1/A2/A3.
- Matched Arduino sketch in `arduino/sketches/arduino_claw/arduino_claw.ino`.
- FlySky iBus movement retained on Arduino during dashboard-approved play
  windows.
- Dashboard-required player registration/photo before starting a play.
- Direct dashboard control screen with no app-shell cache blocking current UI.
- Test Start control that can send the dashboard play gate without a player
  photo.
- Player photo stamping, history, and raw photo capture for AI training.
- USB camera and Pi camera MJPEG streaming path.
- OpenCV HOG people-count fallback for captured photos.
- AI Crowd Bonus grabber power mapping:
  - 0-1 people: 60%
  - 2-3 people: 70%
  - 4 people: 80%
  - 5+ people: 90%
- YOLO people dataset structure, raw photos, labeled sample images, training
  outputs, and deployment model location under `ai/models/yolo_people/best.pt`.
- Runtime dependencies listed in `requirements.txt`.
- Optional failure-safe Supabase machine-status synchronization under `cloud/`.
- Diagnostic-only cloud monitoring at `/cloud` and cached health at
  `/cloud/health`.
- Dashboard header Supabase status badge linked to the Phase A cloud monitor.
- Simplified operator dashboard focused on player registration and machine
  control, without Hacker Mode, reward metrics, player history, or activity
  panels.
- Explicit cloud CLI diagnostics and an opt-in live lifecycle test using the
  isolated `CLOUD-DIAGNOSTIC-TEST` row.
- Automated unit and integration coverage for controller, vision, game state,
  recommendations, dashboard runtime, and cloud monitoring behavior.

## Hardware Integration Notes

- Dashboard play control is active-low: the Raspberry Pi holds Arduino A0 low
  during a play window and releases it to stop.
- Arduino D5 drives the grabber MOSFET/driver PWM control input.
- Manual mode and AI Crowd Bonus mode both update the effective grabber hold
  power shown on the dashboard and sent over GPIO 22/23/24.
- Startup, natural Time Up, and dashboard Stop request full-power grabber pulse
  sequences.
- Movement and grabber hold remain disabled when the dashboard gate is closed.
- The Arduino enforces a 180-second dashboard play safety timeout.
- The Raspberry Pi uses 3.3 V GPIO; do not connect 5 V Arduino outputs to
  Raspberry Pi GPIO inputs.

## Known Gaps

- `main.py` is still a placeholder and does not start the runtime system.
- Controller, service supervisor, deployment, maintenance, and API modules are
  mostly documentation placeholders.
- Dashboard hardware access currently lives directly in the dashboard backend;
  the planned controller safety boundary has not been extracted yet.
- Runtime state is in memory and resets when the dashboard process restarts.
- Player photos, raw AI captures, training runs, caches, and model artifacts are
  present in the repository tree and need a retention/source-control policy.
- Automated tests use mock GPIO/Arduino and Supabase clients; physical hardware
  safety flows still require supervised Raspberry Pi and Arduino testing.
- AI detection in the dashboard uses OpenCV HOG; the trained YOLO model is
  present but is not yet wired into the dashboard runtime path.
- Dashboard styling and frontend code are currently contained in a single HTML
  template.

## Immediate Next Steps

1. Decide whether `dashboard/backend/app.py` remains the temporary runtime entry
   point or whether `main.py` should start the dashboard and future services.
2. Move hardware command decisions behind a controller API so dashboard and AI
   code cannot directly bypass safety rules.
3. Extend automated dashboard coverage to settings validation, hacker mode
   lockout, and photo validation.
4. Add `.gitignore` rules or data-management documentation for generated player
   photos, raw captures, YOLO caches, training runs, and model files.
5. Wire the trained YOLO people model into the dashboard or document why OpenCV
   HOG remains the active runtime detector.
6. Create deployment/service instructions for running the dashboard reliably on
   the Raspberry Pi.
7. Keep cloud synchronization opt-in until production scheduling, retention,
   and least-privilege Supabase policies are approved.

## Current Run Command

```bash
cd /home/araya/Projects/Progress-Claw-OS/dashboard/backend
python3 app.py
```

Then open:

```text
http://localhost:5000
```
