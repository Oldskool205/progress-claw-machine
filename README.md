# Progress Claw OS

Phase 4 runtime skeleton for a layered claw-machine operating system.

Progress Claw OS is a Raspberry Pi backend and dashboard foundation for an Arduino-based claw machine. Phase 4 converts the Phase 3 architecture into a runnable backend skeleton with a controller-owned safety boundary, mock Arduino mode, basic runtime API endpoints, structured logging, and tests.

## Phase 4 Runtime Overview

Progress Claw OS is designed for a Raspberry Pi controlling an Arduino-based claw machine with AI camera support and Tailscale remote management.

```text
Remote Admin
   |
Tailscale
   |
Raspberry Pi
   |-- dashboard/
   |-- ai/
   |-- camera/
   |-- controller/
   |-- system/
   |-- data/
   |-- maintenance/
   |
Controller runtime safety boundary
   |
USB serial command adapter
   |
Arduino
   |
Motors / Claw / Sensors / Coin Input
```

The Raspberry Pi owns services, dashboard, AI, camera processing, logs, and remote access. The Arduino owns low-level hardware control. The controller owns command validation, machine state, and all Arduino communication.

Layer rule:

```text
Dashboard / AI
      |
      v
Controller
      |
      v
Arduino adapter
```

Dashboard and AI code must not access Arduino directly. They submit command models to the controller, and the controller validates safety rules before sending any hardware command.

## Runtime Features

- Controller is the central safety boundary.
- Dashboard runtime endpoints route through `RuntimeController`.
- Arduino communication uses a line-based serial adapter.
- Mock Arduino mode is automatic when hardware is not connected or can be forced with `CLAW_ARDUINO_MOCK=1`.
- Machine state tracks running status, play timing, claw power, Arduino connection, mock mode, emergency stop, and faults.
- Structured JSON logs cover commands, Arduino communication, and safety events.
- Basic unit and integration tests run without Raspberry Pi GPIO or attached Arduino hardware.

## Backend API

- `GET /api/status`
- `POST /api/play/start`
- `POST /api/play/stop`
- `POST /api/claw/power`
- `POST /api/emergency-stop`

Legacy dashboard routes remain available where needed, but hardware-facing work is delegated to the controller.

## Current Hardware Firmware Note

The migrated claw-machine Arduino sketch uses D5 as the active-high PWM output
for the grabber MOSFET. The Raspberry Pi GPIO power bits on Arduino A1/A2/A3
select normal CH6 hold power from 40% to 100%. The reserved A1/A2/A3 code
`111` requests the Arduino to pulse D5 three times at full power after natural
Time Up or the dashboard Stop button while movement remains disabled.

## Run

Install dependencies:

```sh
pip install -r requirements.txt
```

Run with mock Arduino mode:

```sh
CLAW_ARDUINO_MOCK=1 python main.py
```

Run against an attached Arduino:

```sh
CLAW_ARDUINO_DEVICE=/dev/ttyUSB0 python main.py
```

The backend listens on `0.0.0.0:5000` by default. Set `PORT` to change the port.

Useful environment variables:

- `CLAW_ARDUINO_MOCK=1` forces mock Arduino mode.
- `CLAW_ARDUINO_DEVICE=/dev/ttyUSB0` selects a serial device.
- `CLAW_ARDUINO_BAUD=115200` selects the serial baud rate.
- `CLAW_PLAY_DURATION_SECONDS=60` sets the default play duration.
- `CLAW_GRABBER_POWER_PERCENT=100` sets the default claw power.

## Test

```sh
CLAW_ARDUINO_MOCK=1 python -m unittest discover tests
```

The tests use the mock Arduino adapter and do not require attached hardware.

## Documentation

Phase 4 report:

- [docs/reports/phase4_runtime_skeleton.md](docs/reports/phase4_runtime_skeleton.md)

Architecture docs:

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/MODULES.md](docs/MODULES.md)
- [docs/DATA_FLOW.md](docs/DATA_FLOW.md)
- [docs/SERVICE_FLOW.md](docs/SERVICE_FLOW.md)
- [docs/ARDUINO_COMMUNICATION.md](docs/ARDUINO_COMMUNICATION.md)

## Migration Status

The initial safe migration pass has been executed.

- Existing audited dashboard files are already located under `dashboard/`.
- Existing audited script files are already located under `scripts/`.
- No original files were deleted.
- No duplicate copies were created because every audited file was already in its target Progress-Claw-OS module folder.
- Migration details are recorded in [docs/MIGRATION_LOG.md](docs/MIGRATION_LOG.md).

## Project Structure

```text
.
├── controller/      # Control APIs, adapters, protocols, and safety rules
├── ai/              # AI models, vision logic, strategy, and training assets
├── camera/          # Camera capture, calibration, processing, and snapshots
├── dashboard/       # Operator dashboard frontend/backend structure
├── arduino/         # Arduino firmware, sketches, wiring, and protocols
├── system/          # Runtime services, supervisor config, and system logs
├── data/            # Raw data, processed data, models, and logs
├── maintenance/     # Calibration, diagnostics, checklists, and reports
├── assets/          # Images, icons, audio, and AI model assets
├── plugins/         # Future optional feature modules
├── services/        # Long-running services and always-on processes
├── docs/            # Architecture, setup, API, and decision records
├── config/          # Environment, hardware, and interface configuration
├── scripts/         # Development, deployment, and maintenance scripts
├── tests/           # Unit, integration, hardware, and end-to-end tests
├── main.py          # Runtime entry point
├── requirements.txt # Python dependencies
└── README.md
```

## Known Limitations

- The Arduino protocol is still a simple line-based skeleton.
- Emergency stop currently latches in process memory.
- Advanced AI decision making is intentionally not implemented yet.
- Mock mode verifies backend command flow but cannot validate real motors, limit switches, relays, or timing behavior.
