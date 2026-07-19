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

Latest verification on 2026-07-19: 127 automated tests passed. Supervised
Raspberry Pi validation also confirmed real GPIO idle levels, Chromium kiosk
recovery, and the protected reboot and shutdown workflows through the
least-privilege power helper.

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

## Phase 5 Planned Kiosk Mode

Phase 5 is being implemented incrementally. Step 1 adds an opt-in Chromium kiosk
launcher and an independent systemd service; neither is installed or enabled
automatically. The existing dashboard backend, frontend, API, and runtime service
are unchanged. The kiosk browser runs separately so an operator can exit
fullscreen display mode without stopping machine services.

### Implementation progress

- [x] Step 1: Add the isolated kiosk launcher, service definition, and
  configuration tests.
- [x] Step 2: Add the press-and-hold protected touchscreen administration UI
  preview with inactive system controls.
- [x] Step 3A: Add short-lived backend PIN authentication, failed-attempt rate
  limiting, and Lock/Logout without exposing system commands.
- [x] Step 3B: Add authenticated, press-and-hold safe game-stop and
  maintenance-mode workflows through the existing controller stop path.
- [x] Step 3C1: Add authenticated, press-and-hold kiosk exit without stopping
  the dashboard backend or using privileged process commands.
- [x] Step 3C2: Add authenticated, press-and-hold kiosk restart that replaces
  only the Chromium child process.
- [x] Step 3C3A: Add double-confirmed Raspberry Pi reboot and shutdown safety
  simulation with no operating-system command execution.
- [x] Step 3C3B: Add the opt-in least-privilege Raspberry Pi power helper and
  live executor with exact reboot/poweroff allowlists.
- [x] Step 3C3C: Install the reviewed helper and perform supervised reboot, then
  supervised shutdown validation.
- [ ] Step 4 (deferred 2026-07-19): Perform supervised Raspberry Pi
  touchscreen validation when a USB touch interface is available.

Step 1 files:

- `scripts/kiosk/start_kiosk.sh`
- `system/progress-claw-kiosk.service`
- `tests/unit/test_kiosk_config.py`

The launcher starts only Chromium and never starts, stops, or restarts the
dashboard backend. Its default URL is `http://localhost:5000/`; deployments may
override it with `PROGRESS_CLAW_KIOSK_URL` in the existing environment file.

Step 2 adds a touchscreen administrator modal opened by holding the centered
Steaming Club logo on the start screen for 1.8 seconds. It includes the planned
PIN field and system-action buttons, but they are deliberately disabled. No
admin API, PIN validation, `systemctl`, reboot, shutdown, GPIO, or Arduino
command is connected in this step. This allows the layout and interaction to be
reviewed safely before privileged workflows are implemented.

Step 3A connects only administrator authentication. Configure it locally with
`PROGRESS_CLAW_ADMIN_PIN` (4–8 digits) and a strong random
`PROGRESS_CLAW_SECRET_KEY`; real values must never be committed. Successful
authentication creates a five-minute signed session by default, configurable
with `PROGRESS_CLAW_ADMIN_SESSION_SECONDS`. Five failed attempts from one client
within five minutes temporarily block further login attempts. Lock/Logout clears
the session immediately. All system-action buttons remain disabled, and no
system service, reboot, shutdown, GPIO, or Arduino command is exposed by Step 3A.

Step 3B enables only **Stop current game** and **Enter/Exit maintenance** after
administrator authentication. Both touchscreen actions require a 1.8-second
press-and-hold and an explicit API confirmation token. Entering maintenance
safely stops an active game through the existing controller-owned stop flow,
blocks new dashboard plays, and writes the admin action to the dashboard event
log. Exiting maintenance allows new plays again. Kiosk exit, service restart,
Raspberry Pi reboot, and shutdown remain disabled.

Step 3C1 enables **Exit kiosk** only when the administrator is authenticated and
the machine is not running. A 1.8-second press-and-hold sends an explicit
`EXIT_KIOSK` confirmation to the backend. The backend writes a private exit
request under `$XDG_RUNTIME_DIR/progress-claw/`; the independent launcher sees
the request and terminates only the Chromium process that it started. It does
not use `pkill`, `killall`, `systemctl`, or stop the dashboard/controller. Kiosk
restart, Raspberry Pi reboot, and shutdown remain disabled.

Step 3C2 enables **Restart kiosk** only when the administrator is authenticated
and the machine is not running. The private request channel sends `restart` to
the launcher, which terminates only its current Chromium child and starts a new
Chromium child with the same kiosk URL and flags. The dashboard backend,
controller, and game state remain running. The workflow does not use
`systemctl`, `pkill`, `killall`, reboot, or shutdown. Raspberry Pi reboot and
shutdown remain disabled.

Step 3C3A enables reboot and shutdown **simulation** only when the administrator
is authenticated, the machine is idle, and maintenance mode is active. Each
action opens a separate warning modal and requires a three-second press-and-hold
with an action-specific API confirmation. The mock executor records the audit
request and always reports `executed: false`; it contains no subprocess, shell,
systemd, reboot, or poweroff execution path. Connecting real operating-system
power control is deferred to the separately reviewed Step 3C3B.

Step 3C3B adds an opt-in live executor and root helper. The helper accepts
exactly `reboot` or `poweroff` and maps them to fixed absolute `systemctl`
commands; arbitrary arguments and shell execution are unavailable. The
dashboard remains unprivileged and invokes the helper through an exact sudoers
allowlist. Live mode requires explicit local configuration with
`PROGRESS_CLAW_POWER_MODE=live`; the repository default remains `mock`. Adding
the files does not install the helper or execute a power action. Supervised
installation and real-device validation are tracked separately as Step 3C3C.

On the development Raspberry Pi, the helper was installed to
`/usr/local/sbin/progress-claw-power` and its sudoers file parsed successfully.
The installed helper matched the repository copy, and an unsupported action was
rejected without a power operation. This machine already has a pre-existing
`NOPASSWD: ALL` rule for user `araya`; that broader host rule should be removed
in a separately reviewed system-hardening task. Progress Claw still invokes
only the fixed helper allowlist.

Step 3C3C was completed under supervision on 2026-07-19. Before each operation,
the controller reported idle with no emergency stop, GPIO 17 released the
active-low play gate, and GPIOs 22, 23, and 24 were low. The protected admin API
successfully authenticated, entered maintenance mode, verified the machine was
not running, and invoked the exact allowlisted helper action. The reboot stopped
the dashboard and kiosk cleanly and both services recovered automatically. The
subsequent shutdown powered the Pi off cleanly; after power was restored, the
dashboard, kiosk, camera, real GPIO/Arduino transport, and safe output levels all
recovered with no failed systemd units.

Step 4 was started under supervision on 2026-07-19 and then explicitly deferred.
The 1920x1080 Chromium kiosk, dashboard and administrator-panel layouts, PIN
unlock, safety-based button gating, and maintenance-mode workflow were checked
with a mouse. Linux exposed no absolute touchscreen or
`ID_INPUT_TOUCHSCREEN` device; USB enumeration showed only the existing camera,
Arduino serial adapter, and hub, even after the proposed touch cable was
connected. Mouse checks therefore do not count as touchscreen validation. No
kiosk or power action was executed during this attempt. The machine was returned
to Ready with maintenance disabled, no game running, GPIO 17 released, and GPIOs
22, 23, and 24 low. Touch accuracy, calibration, on-screen PIN entry,
press-and-hold targeting, and protected kiosk/power controls remain deferred
until a data-capable USB touch interface is detected.

### Touchscreen operation

- Chromium fullscreen startup at `http://localhost:5000/`.
- Large touch-friendly buttons and readable text.
- No dependence on a keyboard, mouse, hover action, or right-click.
- Protection against accidental zooming, text selection, and page navigation.
- Visible network, Arduino, camera, cloud, and machine status.
- Clear loading, success, warning, and error messages.

### Protected admin controls

- A hidden or PIN-protected admin menu.
- Controls to stop the current game safely, stop or restart machine services,
  restart the kiosk browser, and resume normal operation.
- Maintenance mode that prevents new games from starting.
- A protected **Exit kiosk** control that returns to the normal desktop.
- Protected Raspberry Pi reboot and safe-shutdown controls.
- An emergency-stop control with a clear latched-state warning.
- Confirmation prompts for game stop, service stop, reboot, shutdown, and
  emergency actions.

### Safety requirements

- Stop motors and release hardware outputs before stopping services or shutting
  down the Raspberry Pi.
- Block normal shutdown while hardware is moving; emergency override behavior
  must remain available and fail safe.
- Require a PIN and press-and-hold confirmation for dangerous touchscreen
  actions.
- Keep the physical emergency-stop control independent of the touchscreen.
- Record protected admin actions and shutdown reasons in logs.
- Recover safely after power loss, a browser crash, or an unexpected service
  restart.
- Keep the kiosk browser separate from the dashboard backend service.

### Recovery and normal desktop mode

- `Alt+F4` as the normal keyboard exit method.
- A terminal recovery path using `pkill chromium` if the browser does not close.
- A separately managed kiosk autostart or systemd service that can be disabled
  with `sudo systemctl disable --now progress-claw-kiosk.service` to restore
  normal desktop startup.
- Restarting or stopping the kiosk service must not stop the dashboard backend.
