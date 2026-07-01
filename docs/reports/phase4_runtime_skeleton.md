# Phase 4 Runtime Skeleton

## Files Changed

- `controller/`: added command models, machine state, safety validation, runtime controller, and Arduino adapter.
- `dashboard/backend/app.py`: routed runtime API calls through the controller boundary.
- `services/logging/structured.py`: added JSON structured logging for commands, Arduino communication, and safety events.
- `main.py`: starts the Flask backend runtime.
- `config/config.yaml`: marks Phase 4 runtime settings and Arduino mock fallback.
- `requirements.txt`: adds `pyserial` for USB serial communication.
- `tests/unit/test_runtime_controller.py`: tests controller behavior with mock Arduino.
- `tests/integration/test_dashboard_runtime_api.py`: tests required backend API endpoints with mock Arduino.

## Architecture Decisions

- The controller is the central safety boundary. All Arduino communication is owned by `RuntimeController`.
- Dashboard endpoints create command models and submit them to the controller. They do not instantiate serial or GPIO hardware directly.
- AI-facing updates, such as people count driven claw power, still pass through controller validation before a hardware command is emitted.
- The Arduino adapter uses line-based serial commands and automatically falls back to mock mode when `pyserial` is unavailable, mock mode is requested, or no Arduino port is found.
- Structured logs are emitted as JSON for controller commands, Arduino communication, Arduino faults, and emergency-stop events.

## How to Run

```bash
python main.py
```

The backend listens on `0.0.0.0:5000` by default. Set `PORT` to change the port.

Useful environment variables:

- `CLAW_ARDUINO_MOCK=1` forces mock Arduino mode.
- `CLAW_ARDUINO_DEVICE=/dev/ttyUSB0` selects a serial device.
- `CLAW_ARDUINO_BAUD=115200` selects the serial baud rate.
- `CLAW_PLAY_DURATION_SECONDS=60` sets the default play duration.
- `CLAW_GRABBER_POWER_PERCENT=100` sets the default claw power.

## Backend API

- `GET /api/status`
- `POST /api/play/start`
- `POST /api/play/stop`
- `POST /api/claw/power`
- `POST /api/emergency-stop`

Legacy dashboard routes remain available where needed, but hardware-facing work is delegated to the controller.

## How to Test

```bash
CLAW_ARDUINO_MOCK=1 python -m unittest discover tests
```

The tests use the mock Arduino adapter and do not require Raspberry Pi GPIO or attached hardware.

## Known Limitations

- The Arduino protocol is still a simple line-based skeleton. Firmware responses may need adjustment when hardware firmware is finalized.
- Emergency stop currently latches in process memory. A later phase should add authenticated reset and persistence.
- Advanced AI decision making is intentionally not implemented in Phase 4.
- The mock adapter verifies command flow but cannot validate real motor timing, limit switches, or relay behavior.
