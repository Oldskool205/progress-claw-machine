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
- The current Arduino firmware is controlled through the Raspberry Pi GPIO play
  gate and claw-power pins; an optional serial adapter remains available for
  future firmware.
- Mock Arduino mode is automatic when GPIO is unavailable or can be forced with
  `CLAW_ARDUINO_MOCK=1`.
- Machine state tracks running status, play timing, claw power, Arduino connection, mock mode, emergency stop, and faults.
- Structured JSON logs cover commands, Arduino communication, and safety events.
- Basic unit and integration tests run without Raspberry Pi GPIO or attached Arduino hardware.

## Phase A Supabase Cloud Integration

The optional `cloud/` module synchronizes a small machine-status snapshot to
Supabase without placing cloud connectivity in the machine control path. Phase A
is additive and does not modify game logic, the Vision Service, the Game State
Engine, controller safety behavior, or existing REST APIs.

Initially synchronized fields:

- Machine name
- Current status
- X and Y positions
- Claw power
- Online state
- UTC update timestamp

Game history and AI detections are not synchronized in Phase A. Cloud
synchronization is opt-in and is not started automatically by the runtime. If
Supabase is unavailable, local play continues normally while the cloud service
logs a warning and throttles later connection attempts.

Configure Supabase by copying the environment template:

```sh
cp .env.example .env
```

Then provide the required values in `.env`:

```dotenv
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-server-side-key
```

Optional cloud settings are `CLAW_MACHINE_NAME`,
`SUPABASE_MACHINE_STATUS_TABLE`, `SUPABASE_RETRY_SECONDS`, and
`SUPABASE_SYNC_INTERVAL_SECONDS`. The `.env` file is ignored by Git and must
not be committed.

Example manual synchronization:

```python
from cloud.sync_service import CloudSyncService

cloud = CloudSyncService()
cloud.connect()
cloud.sync_game_status(
    status="ready",
    x_position=0.0,
    y_position=0.0,
    claw_power=70,
)
cloud.heartbeat()
```

See [docs/cloud/SUPABASE_SETUP.md](docs/cloud/SUPABASE_SETUP.md) for table SQL,
configuration, Row Level Security guidance, logging, and troubleshooting.

### Phase A.1 diagnostics and monitoring

Run explicit live diagnostics with the dedicated
`CLOUD-DIAGNOSTIC-TEST` row:

```sh
.venv/bin/python -m cloud.diagnostics --test-connection
.venv/bin/python -m cloud.diagnostics --all
```

`--test-connection` performs a read-only connection and schema check. `--all`
also writes, updates, and marks offline only the dedicated diagnostic row. It
never reads production game state or invokes controller commands.

When the dashboard is running, `/cloud` provides diagnostic monitoring and
`/cloud/health` provides credential-free cached health JSON. Browser health
polls do not contact Supabase; only explicit diagnostic actions do. The
standalone diagnostic service can be installed from
`system/progress-claw-cloud-monitor.service` and listens on port 5001. See
[LIVE_VERIFICATION.md](docs/cloud/LIVE_VERIFICATION.md) and
[CLOUD_MONITORING.md](docs/cloud/CLOUD_MONITORING.md).

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
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Run with mock Arduino mode:

```sh
CLAW_ARDUINO_MOCK=1 .venv/bin/python main.py
```

Run on the Raspberry Pi with the current GPIO-connected Arduino firmware:

```sh
.venv/bin/python main.py
```

The backend listens on `0.0.0.0:5000` by default. Set `PORT` to change the port.

Useful environment variables:

- `CLAW_ARDUINO_MOCK=1` forces mock Arduino mode.
- `CLAW_ARDUINO_TRANSPORT=gpio` selects the firmware-compatible Raspberry Pi
  GPIO transport (default). Use `serial` only with firmware that implements the
  controller's line-based command protocol.
- `CLAW_START_GPIO=17` selects the active-low Arduino A0 play-gate output.
- `CLAW_GRABBER_POWER_GPIOS=22,23,24` selects the Arduino A1-A3 power outputs.
- `CLAW_ARDUINO_DEVICE=/dev/ttyUSB0` selects a serial device.
- `CLAW_ARDUINO_BAUD=115200` selects the serial baud rate.
- `CLAW_PLAY_DURATION_SECONDS=60` sets the default play duration.
- `CLAW_GRABBER_POWER_PERCENT=100` sets the default claw power.
- `SUPABASE_URL` selects the Supabase project URL.
- `SUPABASE_KEY` provides the server-side Supabase API key.
- `CLAW_MACHINE_NAME` sets the stable cloud machine name.
- `SUPABASE_RETRY_SECONDS=30` controls cloud retry throttling.
- `SUPABASE_SYNC_INTERVAL_SECONDS=60` records the planned synchronization
  interval; Phase A.1 does not start a background synchronization loop.

## Test

```sh
CLAW_ARDUINO_MOCK=1 .venv/bin/python -m pytest -q
```

The local suite uses mock Arduino and Supabase clients and does not require
attached hardware or cloud access. A configured `.env` does not make the normal
suite write to Supabase. Run the real diagnostic-row lifecycle only when
explicitly requested:

```sh
PROGRESS_CLAW_RUN_LIVE_TESTS=1 \
  .venv/bin/python -m unittest tests.live.cloud_live_test -v
```

Latest verification on 2026-07-16: 90 tests passed and the opt-in live test was
skipped. The read-only Supabase connection/schema diagnostic also passed.

## Documentation

Phase 4 report:

- [docs/reports/phase4_runtime_skeleton.md](docs/reports/phase4_runtime_skeleton.md)

Architecture docs:

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/MODULES.md](docs/MODULES.md)
- [docs/DATA_FLOW.md](docs/DATA_FLOW.md)
- [docs/SERVICE_FLOW.md](docs/SERVICE_FLOW.md)
- [docs/ARDUINO_COMMUNICATION.md](docs/ARDUINO_COMMUNICATION.md)
- [docs/cloud/SUPABASE_SETUP.md](docs/cloud/SUPABASE_SETUP.md)
- [docs/cloud/LIVE_VERIFICATION.md](docs/cloud/LIVE_VERIFICATION.md)
- [docs/cloud/CLOUD_MONITORING.md](docs/cloud/CLOUD_MONITORING.md)

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
├── cloud/           # Optional Supabase status synchronization
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
- Phase A.1 cloud synchronization remains operator-triggered; automatic
  production scheduling and retention policy are not implemented yet.
