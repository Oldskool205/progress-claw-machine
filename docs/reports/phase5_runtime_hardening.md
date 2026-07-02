# Phase 5 Runtime Hardening and Safe Dashboard Refactor

## Files changed

- `dashboard/backend/app.py`: kept as the Flask entry point, explicit dashboard static/template paths, blueprint registration, startup helpers, and JSON error handlers.
- `dashboard/backend/dashboard_state.py`: shared dashboard state, camera worker, player photo helpers, play helpers, and RuntimeController wiring.
- `dashboard/backend/routes_api.py`: existing controller-backed API routes and legacy dashboard control routes.
- `dashboard/backend/routes_camera.py`: camera stream route.
- `dashboard/backend/routes_player.py`: player photo upload and Pi camera capture routes.
- `dashboard/backend/routes_system.py`: dashboard shell, service worker, and `GET /api/health`.
- `services/logging/structured.py`: structured JSON logging to stdout and separate log files.
- `system/progress-claw.service`: Raspberry Pi systemd service unit.
- `system/README.md`: Raspberry Pi service installation instructions.
- `tests/integration/test_dashboard_runtime_api.py`: health endpoint and API validation coverage.
- `tests/unit/test_arduino_adapter.py`: Arduino mock adapter coverage.
- `controller/*` and `tests/unit/test_runtime_controller.py`: Black formatting only.

## Architecture decisions

- `RuntimeController` remains the only hardware gateway. Dashboard route modules call the controller and do not instantiate or communicate with the Arduino adapter directly.
- `app.py` stays intentionally small and remains the application entry point.
- Route behavior was moved into focused modules without renaming existing routes or changing response payload shapes.
- Shared mutable dashboard state remains centralized in `dashboard_state.py` to avoid duplicate state across blueprints.
- Flask now points explicitly at `dashboard/assets/static` and `dashboard/frontend/templates`, matching the repository layout for the dashboard UI and service worker.
- Structured logs are JSON. Default log files are:
  - `logs/system.log`
  - `logs/command.log`
  - `logs/arduino.log`
  - `logs/safety.log`
- `GET /api/health` returns controller, Arduino, camera, and uptime status without changing any existing endpoint.

## Migration notes

- Install the Raspberry Pi service with the instructions in `system/README.md`.
- The service expects the application at `/opt/progress-claw` and runs `/usr/bin/python3 /opt/progress-claw/main.py`.
- Optional production environment overrides should be placed in `/etc/progress-claw/progress-claw.env`.
- Set `CLAW_LOG_DIR` to move runtime logs outside the repository, for example `/opt/progress-claw/logs`.
- Existing API routes are retained:
  - `/api/status`
  - `/api/play/start`
  - `/api/play/stop`
  - `/api/claw/power`
  - `/api/emergency-stop`
  - `/api/count`
  - `/api/settings`
  - `/api/ai-count`
  - `/api/hacker`
  - `/api/player-photo`
  - `/api/capture-player`
  - `/api/play`
  - `/api/stop`
  - `/api/reset`

## Testing results

- `python3 -m black --check` was run per Python source file after formatting.
- `python3 -m unittest discover -s tests`
  - Result: `Ran 13 tests in 0.085s`
  - Result: `OK`
- Flask test-client smoke checks:
  - `/` returned `200`
  - `/api/health` returned `200`
  - `/api/status` returned `200`
  - `/service-worker.js` returned `200`

## Known limitations

- Camera readiness in `/api/health` is based on whether the camera worker has received at least one frame in the current process.
- Hardware serial behavior is still hardware dependent; automated tests cover the mock adapter path.
- Generated runtime logs are ignored by git and should be collected from the production host when diagnosing live issues.
