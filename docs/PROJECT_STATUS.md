# Project Status

Last updated: 2026-07-23

## Current Phase

Progress Claw OS is a working Raspberry Pi claw-machine platform in supervised
prototype/integration status. Phase 5 runtime hardening and protected kiosk
administration are implemented. Phase 6 vision, game-state, recommendation, and
read-only analytics foundations are also implemented.

The project is hardware-facing software. Physical movement, emergency, power,
touchscreen, and network changes require supervised validation before unattended
operation.

## Runtime and Safety

- `main.py` is the production entry point used by `claw-dashboard.service`.
- `RuntimeController` owns the hardware safety boundary.
- Dashboard play, stop, claw-power, and emergency-stop routes submit controller
  command models rather than opening Arduino transport directly.
- The deployed GPIO adapter controls the active-low play gate and grabber power
  selection for the current Arduino firmware.
- Mock transport remains available for hardware-independent automated tests.
- Structured command, Arduino, safety, system, game-state, recommendation, and
  cloud logs are available.

## Dashboard and Protected Administration

- The dashboard provides player registration, camera preview, play timing,
  machine settings, claw-power selection, cloud status, and analytics access.
- Chromium kiosk startup and recovery run independently from the dashboard.
- Short-lived Admin PIN sessions protect maintenance, game stop, kiosk exit and
  restart, Raspberry Pi reboot and shutdown, and Wi-Fi administration.
- Power and Wi-Fi operations use installed root-owned least-privilege helpers
  with exact sudoers action allowlists.
- Live WPA/WPA2 Personal scanning, connection, automatic rollback, and internet
  recovery were validated under supervision on 2026-07-22.
- Full touchscreen validation remains deferred until a data-capable absolute
  touchscreen interface is available and recognized by Linux.

## Phase 6 Intelligence

- Vision Service provides camera, snapshot, frame queue, YOLO detection,
  detection-cache, and health boundaries.
- Game State Engine converts public runtime and detection inputs into
  conservative cached state events.
- Recommendation Engine produces explainable informational recommendations
  without controlling hardware.
- Read-only analytics aggregates bounded runtime, safety, vision, game-state,
  and recommendation events with filters and CSV export.
- AI-generated action execution and autonomous mode are not enabled.

## Cloud

- Supabase integration is optional and outside the machine-control path.
- Explicit diagnostics and isolated live-row lifecycle testing are implemented.
- Dashboard health polling uses cached credential-free status.
- Automatic production synchronization, retention, and final least-privilege
  policies remain deferred.

## Verification Baseline

Latest full automated verification before this documentation update:

```text
166 passed, 1 skipped
```

The skipped test is the explicitly opt-in live Supabase lifecycle test.
Supervised validations also cover real GPIO idle levels, kiosk recovery,
protected reboot and shutdown, Admin Wi-Fi association, rollback, dashboard
recovery, and internet connectivity.

## Remaining Work

1. Complete supervised touchscreen calibration and protected-control validation
   when Linux detects a real touchscreen interface.
2. Review and remove the host's broader pre-existing `NOPASSWD: ALL` rule,
   retaining only reviewed helper permissions.
3. Persist safety-critical runtime state conservatively across dashboard
   restarts, especially emergency-stop and maintenance state.
4. Complete physical motor, limit-switch, claw, play-timing, fault, and
   emergency-stop validation under supervision.
5. Add explicit, opt-in AI action requests through Runtime API and
   `RuntimeController`, including stale-data, confidence, manual-lockout, fault,
   and emergency-stop gates.
6. Add bounded durable analytics, play/session identifiers, outcomes, and
   background collection after approving privacy and retention limits.
7. Consolidate dashboard people counting with the YOLO Vision Service or retain
   OpenCV HOG as a documented fallback.
8. Approve or decline scheduled Supabase synchronization, retention, and final
   least-privilege Row Level Security.
9. Apply the repository data-retention policy and review whether previously
   published human images require a coordinated Git-history rewrite.

## Run and Service

Development/mock command:

```bash
cd /home/araya/Projects/Progress-Claw-OS
CLAW_ARDUINO_MOCK=1 .venv/bin/python main.py
```

Production is managed by:

```text
claw-dashboard.service
progress-claw-kiosk.service
```

Dashboard URL on the Raspberry Pi:

```text
http://localhost:5000/
```
