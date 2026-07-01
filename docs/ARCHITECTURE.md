# Progress Claw OS Architecture

Phase 3 defines the system architecture for Progress Claw OS. This document is design-only. Runtime code will be implemented in later phases.

## Target Hardware

- Raspberry Pi as the main computer
- Arduino as the hardware control board
- AI camera or USB camera for vision input
- Tailscale for secure remote management
- Claw machine hardware: motors, claw actuator, coin/credit input, sensors, lights, and optional audio

## High-Level Architecture

```text
Remote Admin
  Tailscale
      |
      v
Raspberry Pi
  |
  |-- dashboard/      Operator UI and remote monitoring
  |-- ai/             Vision and decision support
  |-- camera/         Camera capture and calibration
  |-- controller/     Main control logic and safety rules
  |-- system/         Services, startup, logs, watchdog
  |-- data/           Logs, captures, models, reports
  |-- maintenance/    Calibration and diagnostics
  |
  USB Serial
      |
      v
Arduino
  |
  |-- motors
  |-- claw actuator
  |-- sensors
  |-- coin input
  |-- lights/audio
```

## Layer Rule

```text
Dashboard / AI
      |
      v
Controller
      |
      v
Arduino / Camera / Hardware
```

The dashboard and AI should never directly control Arduino pins. They request actions through the controller layer.

## Main Responsibilities

- Raspberry Pi runs the operating system, dashboard, AI, camera processing, service supervision, logging, and remote access.
- Arduino handles timing-sensitive hardware control such as motors, relays, buttons, coin pulse reading, and emergency stop input.
- Tailscale allows secure remote access without exposing the Raspberry Pi directly to the public internet.

## Safety Principles

- Controller must validate every movement command before sending it to Arduino.
- Arduino should reject unknown commands.
- Emergency stop must override dashboard, AI, and plugin commands.
- Services should restart only safe processes automatically.
- Logs should record commands, faults, startup events, and maintenance actions.
