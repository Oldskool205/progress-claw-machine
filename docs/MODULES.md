# Module Responsibilities

This document defines the responsibilities of each main Progress Claw OS module.

## controller/

The controller module is the central decision and safety boundary.

Responsibilities:

- Receive movement and game commands from dashboard, AI, plugins, or services
- Validate command limits before hardware execution
- Manage claw movement state
- Send safe commands to Arduino
- Stop motion during faults or emergency stop
- Expose a stable internal API for other modules

Should not:

- Store large camera datasets
- Render dashboard UI
- Directly train AI models

## ai/

The AI module contains vision-assisted decision logic.

Responsibilities:

- Analyze camera frames
- Detect claw, prize, target zones, or machine state
- Recommend movement commands
- Store model notes and training structure
- Send high-level action requests to controller

Should not:

- Control Arduino directly
- Bypass controller safety checks

## camera/

The camera module owns camera input and calibration.

Responsibilities:

- Capture frames from camera hardware
- Store calibration data
- Prepare images for AI processing
- Save debug snapshots
- Track camera device settings

Should not:

- Decide final movement commands
- Control motors

## dashboard/

The dashboard module is the operator interface.

Responsibilities:

- Show machine status
- Show camera preview
- Start/stop sessions
- Trigger maintenance actions
- Display logs, alerts, and service health
- Support remote use through Tailscale

Should not:

- Talk directly to Arduino pins or serial commands
- Ignore controller safety state

## arduino/

The Arduino module contains firmware and hardware communication notes.

Responsibilities:

- Control motors and actuators
- Read buttons, coin inputs, and sensors
- Execute serial commands from Raspberry Pi
- Report hardware status
- Enforce low-level safety timing

Should not:

- Run dashboard logic
- Run AI logic
- Store long-term logs

## system/

The system module contains Raspberry Pi runtime management.

Responsibilities:

- Define startup behavior
- Manage services
- Configure watchdogs
- Track system logs
- Document Tailscale access
- Keep the OS-level setup repeatable

Should not:

- Contain business-specific claw movement logic

## data/

The data module stores runtime and development data.

Responsibilities:

- Store raw camera captures
- Store processed images
- Store AI model artifacts
- Store logs and reports
- Keep test fixtures organized

Should not:

- Contain application source code
- Store secrets

## maintenance/

The maintenance module supports machine servicing.

Responsibilities:

- Calibration checklists
- Hardware diagnostics
- Service reports
- Repair notes
- Manual test procedures

Should not:

- Replace the controller safety layer
- Store production credentials
