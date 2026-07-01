# Existing Code Audit

Audit scope:

- `dashboard/`
- `scripts/`

Audit date: 2026-06-28

## Summary

No executable dashboard code or script code currently exists in the audited folders.

The current `dashboard/` and `scripts/` folders contain only README placeholder files that define the intended project structure. There are no Python, JavaScript, shell, HTML, CSS, Arduino, service, or configuration implementation files in these two areas yet.

## Files Found

| File | What It Does | Module | Required Dependencies | Migration Recommendation |
|---|---|---|---|---|
| `dashboard/README.md` | Describes the dashboard module and its intended subfolders: frontend, backend, components, and assets. | `dashboard` | None. Markdown only. | Already in the correct Progress-Claw-OS location. Keep as module documentation. |
| `dashboard/backend/README.md` | Placeholder for future dashboard backend and API source files. | `dashboard` | None. Markdown only. | Keep here. Future dashboard API/server code should be added under `dashboard/backend/`. |
| `dashboard/frontend/README.md` | Placeholder for future dashboard UI source files. | `dashboard` | None. Markdown only. | Keep here. Future web UI code should be added under `dashboard/frontend/`. |
| `dashboard/components/README.md` | Placeholder for reusable dashboard widgets and controls. | `dashboard` | None. Markdown only. | Keep here. Future reusable UI components should be added under `dashboard/components/`. |
| `dashboard/assets/README.md` | Placeholder for dashboard-specific static assets. | `dashboard` | None. Markdown only. | Keep here. Dashboard-only images, icons, and static files should be added under `dashboard/assets/`. |
| `scripts/README.md` | Describes script module purpose and subfolders: dev, deploy, maintenance, and tools. | `system` | None. Markdown only. | Already in the correct Progress-Claw-OS location. Keep as script documentation. |
| `scripts/dev/README.md` | Placeholder for local development helper scripts. | `system` | None. Markdown only. | Keep here. Future local setup/start/test helpers should be added under `scripts/dev/`. |
| `scripts/deploy/README.md` | Placeholder for deployment helper scripts. | `system` | None. Markdown only. | Keep here. Future Raspberry Pi deployment scripts should be added under `scripts/deploy/`. |
| `scripts/maintenance/README.md` | Placeholder for operator and maintenance helper scripts. | `maintenance` | None. Markdown only. | Keep here. Future calibration, diagnostics, and service helper scripts should be added under `scripts/maintenance/`. |
| `scripts/tools/README.md` | Placeholder for small project utility scripts. | `system` | None. Markdown only. | Keep here. Future one-off project utility scripts should be added under `scripts/tools/`. |

## Module Mapping

### dashboard

Files:

- `dashboard/README.md`
- `dashboard/backend/README.md`
- `dashboard/frontend/README.md`
- `dashboard/components/README.md`
- `dashboard/assets/README.md`

Current status:

- Documentation placeholders only.
- No dashboard backend code exists yet.
- No dashboard frontend code exists yet.
- No API routes, UI components, static assets, or build configuration exist yet.

Expected future contents:

- Backend API for machine state, command requests, camera status, and service health.
- Frontend UI for operator control, live status, camera preview, maintenance controls, and remote management.
- Reusable dashboard components.
- Dashboard-specific static assets.

### system

Files:

- `scripts/README.md`
- `scripts/dev/README.md`
- `scripts/deploy/README.md`
- `scripts/tools/README.md`

Current status:

- Documentation placeholders only.
- No development, deployment, service, or utility scripts exist yet.

Expected future contents:

- Raspberry Pi setup scripts.
- Local development helpers.
- Service installation helpers.
- Tailscale verification helpers.
- Log collection utilities.

### maintenance

Files:

- `scripts/maintenance/README.md`

Current status:

- Documentation placeholder only.
- No maintenance scripts exist yet.

Expected future contents:

- Calibration helpers.
- Diagnostic scripts.
- Arduino connection checks.
- Camera test capture helpers.
- Maintenance report helpers.

## Dependencies Required

Current required dependencies:

- None for the audited files.

Reason:

- All existing files in `dashboard/` and `scripts/` are Markdown README files.
- No executable code or package manifest was found in these folders.

Likely future dependencies:

- Dashboard backend: Python web framework or Node.js server framework.
- Dashboard frontend: HTML/CSS/JavaScript or a frontend framework.
- Scripts: Bash and Python standard library.
- Raspberry Pi services: systemd.
- Remote management: Tailscale.
- Camera integration: OpenCV or camera-specific libraries.
- Arduino communication: Python serial library such as `pyserial`.

These future dependencies should not be added until implementation begins.

## What Should Be Migrated Into Progress-Claw-OS

Nothing from the audited `dashboard/` and `scripts/` folders needs to be migrated right now because the audited content is already inside the Progress-Claw-OS structure.

If older code exists elsewhere on the Raspberry Pi, it should be migrated as follows:

| Existing Code Type | Target Location |
|---|---|
| Dashboard web UI | `dashboard/frontend/` |
| Dashboard API/server code | `dashboard/backend/` |
| Reusable dashboard UI widgets | `dashboard/components/` |
| Dashboard images/icons/static files | `dashboard/assets/` |
| Local development scripts | `scripts/dev/` |
| Deployment scripts | `scripts/deploy/` |
| Maintenance/calibration scripts | `scripts/maintenance/` |
| Small utilities | `scripts/tools/` |
| Service startup files | `system/services/` |
| Logs generated by scripts | `data/logs/` or `system/logs/` |

## Recommended Next Step

Before Phase 4 implementation, search the Raspberry Pi for any existing dashboard or claw-machine scripts outside this project, then migrate them into the target folders listed above.

Do not add dependencies or runtime code until the migration source files are identified.
