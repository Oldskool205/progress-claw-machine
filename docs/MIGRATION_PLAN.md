# Migration Plan

This migration plan is based on `docs/EXISTING_CODE_AUDIT.md`.

No files should be moved yet. The current audited files are already inside the Progress-Claw-OS structure and are documentation placeholders only.

## Migration Summary

- Current audited scope: `dashboard/` and `scripts/`
- Current executable code found: none
- Current dependencies required: none
- Immediate migration required: none
- Risk level: low

## Existing File Mapping

| Source File | Target Folder | Module | Reason | Risk Level | Required Changes |
|---|---|---|---|---|---|
| `dashboard/README.md` | `dashboard/` | `dashboard` | Already documents the dashboard module and its intended structure. | Low | Keep in place. Update later when dashboard implementation begins. |
| `dashboard/backend/README.md` | `dashboard/backend/` | `dashboard` | Already marks the correct location for future dashboard API/backend code. | Low | Keep in place. Add backend code here in a later phase. |
| `dashboard/frontend/README.md` | `dashboard/frontend/` | `dashboard` | Already marks the correct location for future dashboard UI code. | Low | Keep in place. Add frontend code here in a later phase. |
| `dashboard/components/README.md` | `dashboard/components/` | `dashboard` | Already marks the correct location for reusable dashboard UI components. | Low | Keep in place. Add reusable components here in a later phase. |
| `dashboard/assets/README.md` | `dashboard/assets/` | `dashboard` | Already marks the correct location for dashboard-specific static assets. | Low | Keep in place. Add dashboard images, icons, and static files here later. |
| `scripts/README.md` | `scripts/` | `system` | Already documents the scripts module and its intended structure. | Low | Keep in place. Update later when scripts are implemented. |
| `scripts/dev/README.md` | `scripts/dev/` | `system` | Already marks the correct location for development helper scripts. | Low | Keep in place. Add setup, start, and test helpers here later. |
| `scripts/deploy/README.md` | `scripts/deploy/` | `system` | Already marks the correct location for Raspberry Pi deployment helpers. | Low | Keep in place. Add deployment scripts here later. |
| `scripts/maintenance/README.md` | `scripts/maintenance/` | `maintenance` | Already marks the correct location for maintenance and operator helper scripts. | Low | Keep in place. Add calibration and diagnostic scripts here later. |
| `scripts/tools/README.md` | `scripts/tools/` | `system` | Already marks the correct location for small project utilities. | Low | Keep in place. Add utility scripts here later. |

## Module Migration Rules

### controller

Target folder:

- `controller/`

Move here later:

- Command validation code
- Motion safety logic
- Arduino command interface wrappers
- Machine state coordination

Required changes when migrating:

- Remove direct hardware access from dashboard or AI code.
- Route physical movement requests through controller APIs.

Risk level:

- Medium to high when real hardware movement code is introduced.

### ai

Target folder:

- `ai/`

Move here later:

- Vision models
- Object detection logic
- Strategy logic
- AI training notes and experiments

Required changes when migrating:

- Replace direct motor commands with controller action requests.
- Store large trained model files in `data/models/` or `assets/ai-models/` as appropriate.

Risk level:

- Medium, because AI recommendations must not bypass safety checks.

### camera

Target folder:

- `camera/`

Move here later:

- Camera capture code
- Calibration data
- Frame processing logic
- Snapshot test utilities

Required changes when migrating:

- Separate raw camera capture from AI decision logic.
- Store generated images in `data/raw/`, `data/processed/`, or `data/snapshots/`.

Risk level:

- Medium, because camera device IDs and Raspberry Pi camera setup may differ by machine.

### dashboard

Target folders:

- `dashboard/frontend/`
- `dashboard/backend/`
- `dashboard/components/`
- `dashboard/assets/`

Move here later:

- Existing dashboard web UI
- Dashboard server/API code
- Reusable UI components
- Dashboard-specific images and icons

Required changes when migrating:

- Remove direct Arduino or GPIO access from dashboard code.
- Use controller APIs for commands.
- Use camera service/API for camera preview.
- Keep Tailscale access as a deployment/network concern, not dashboard business logic.

Risk level:

- Medium, because dashboard code may currently mix UI, hardware control, and service startup logic.

### arduino

Target folder:

- `arduino/`

Move here later:

- Arduino sketches
- Firmware source
- Serial protocol notes
- Wiring diagrams and pin maps

Required changes when migrating:

- Document baud rate, command format, and response format.
- Keep firmware separate from Raspberry Pi Python/dashboard code.

Risk level:

- High when connected to real motors, relays, coin inputs, and emergency stop circuits.

### system

Target folders:

- `system/`
- `services/`
- `scripts/dev/`
- `scripts/deploy/`
- `scripts/tools/`

Move here later:

- Raspberry Pi service files
- Startup scripts
- Tailscale setup notes
- Watchdog scripts
- Log collection utilities

Required changes when migrating:

- Convert ad hoc startup commands into repeatable service definitions.
- Keep secrets and device-specific local settings out of the repository.

Risk level:

- Medium, because incorrect service startup can leave hardware in an unsafe state.

### data

Target folders:

- `data/raw/`
- `data/processed/`
- `data/models/`
- `data/logs/`
- `data/snapshots/`

Move here later:

- Test captures
- Runtime logs
- Processed camera frames
- AI model artifacts
- Debug snapshots

Required changes when migrating:

- Do not commit large generated datasets unless they are small fixtures.
- Keep runtime logs out of source control where possible.

Risk level:

- Low to medium, mainly due to storage size and privacy concerns.

### maintenance

Target folders:

- `maintenance/`
- `scripts/maintenance/`

Move here later:

- Calibration scripts
- Diagnostic scripts
- Operator checklists
- Repair reports
- Hardware test procedures

Required changes when migrating:

- Keep maintenance scripts safe to run repeatedly.
- Clearly label scripts that move hardware or require operator supervision.

Risk level:

- Medium to high when scripts interact with real hardware.

## Future External Code Migration Checklist

Use this checklist if older dashboard or claw-machine code is found elsewhere on the Raspberry Pi.

| Existing Code Type | Target Folder | Reason | Risk Level | Required Changes |
|---|---|---|---|---|
| Dashboard web UI | `dashboard/frontend/` | Keeps operator interface code inside the dashboard module. | Medium | Remove hardware calls; call backend/controller APIs instead. |
| Dashboard API/server | `dashboard/backend/` | Keeps dashboard server logic separate from frontend UI. | Medium | Route machine commands through `controller/`. |
| Reusable UI widgets | `dashboard/components/` | Keeps shared dashboard components reusable and organized. | Low | Rename/import paths as needed. |
| Dashboard static assets | `dashboard/assets/` | Keeps dashboard-only images/icons separate from global assets. | Low | Update asset paths in dashboard UI. |
| General images/icons/audio | `assets/` | Keeps shared static assets available to multiple modules. | Low | Update references to new asset paths. |
| AI model files | `data/models/` or `assets/ai-models/` | Keeps AI artifacts separate from code. | Medium | Confirm model size, format, and load path. |
| Camera capture scripts | `camera/capture/` | Keeps camera input code separate from AI and dashboard. | Medium | Replace hardcoded device IDs with config values. |
| Camera calibration files | `camera/calibration/` | Keeps calibration material near camera module. | Medium | Document camera position and calibration date. |
| Arduino sketches | `arduino/sketches/` | Keeps Arduino IDE sketches in the Arduino module. | High | Verify pins, timing limits, and emergency stop behavior. |
| Arduino firmware source | `arduino/firmware/` | Keeps firmware source separate from Raspberry Pi code. | High | Confirm serial protocol compatibility. |
| Wiring notes/pin maps | `arduino/wiring/` | Keeps physical hardware documentation near firmware. | High | Verify against the real machine before operation. |
| Local development scripts | `scripts/dev/` | Keeps developer helpers separate from runtime services. | Low | Make scripts repeatable and documented. |
| Deployment scripts | `scripts/deploy/` | Keeps Raspberry Pi deployment helpers organized. | Medium | Avoid hardcoded secrets and local-only paths. |
| Maintenance scripts | `scripts/maintenance/` | Keeps operator tools with maintenance workflows. | Medium | Add warnings for scripts that move hardware. |
| Utility scripts | `scripts/tools/` | Keeps one-off project utilities organized. | Low | Add usage notes. |
| Systemd service files | `system/services/` or `services/runtime/` | Keeps runtime service definitions organized. | Medium | Define safe startup/shutdown order. |
| Watchdog scripts | `services/watchdog/` | Keeps health checks and recovery logic separate. | Medium | Ensure recovery actions fail safe. |
| Runtime logs | `data/logs/` or `system/logs/` | Keeps generated logs out of source modules. | Low | Do not commit large or sensitive logs. |

## Current Decision

Do not move any files yet.

The current audited files are already in the correct structure. The next migration action should happen only after older external source files are found and reviewed.
