# Progress Claw OS

Phase 2 project framework for a layered claw-machine operating system.

This phase creates the clean folder structure, starter configuration, assets/plugins/services placeholders, and documentation files. Complex runtime logic is intentionally not implemented yet.

## Phase 3 Architecture Overview

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
GPIO safety gate and grabber power lines
   |
Arduino
   |
Motors / Claw / Sensors / Coin Input
```

The Raspberry Pi owns services, dashboard, AI, camera processing, logs, and remote access. The Arduino owns low-level hardware control. The current claw-machine integration uses Raspberry Pi GPIO to gate play and select grabber hold power because FlySky iBus uses the Arduino serial port.

Current hardware control notes:

- Raspberry Pi BCM GPIO 17 -> Arduino A0: active-low dashboard play gate
- Raspberry Pi BCM GPIO 22/23/24 -> Arduino A1/A2/A3: dashboard grabber hold-power selection
- Arduino D5: PWM output to the grabber MOSFET module
- FlySky CH5 enables remote movement; FlySky CH6 controls grabber on/off during play
- Startup grabber pulses stay full power; dashboard-selected grabber power applies to CH6 hold power
- AI Crowd Bonus mode can select CH6 hold power automatically: 0-1 people -> 60%, 2-3 -> 70%, 4 -> 80%, 5+ -> 90%

The controller module remains the planned safety boundary between software decisions and physical movement.

Phase 3 architecture docs:

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

## Architecture

```text
Dashboard / AI
      |
Business Logic
      |
Controller
      |
Hardware: Arduino / GPIO / Camera
```

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
├── main.py          # Placeholder entry point
├── requirements.txt # Python dependencies
└── README.md
```

## Run Placeholder

```sh
python3 main.py
```

## Phase 2 Scope

- Create the project framework.
- Define module boundaries.
- Add README files for each module.
- Add starter config files.
- Add placeholders for assets, plugins, and services.
- Avoid complex implementation code.
