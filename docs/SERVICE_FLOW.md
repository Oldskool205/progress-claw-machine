# Service Flow

This document defines the planned always-on service structure for the Raspberry Pi.

## Service Overview

```text
Raspberry Pi boot
      |
      v
system supervisor
      |
      +--> dashboard service
      +--> controller service
      +--> camera service
      +--> AI service
      +--> logging service
      +--> watchdog service
      +--> Tailscale service
```

## Planned Services

### Dashboard Service

Purpose:

- Serve the operator interface
- Show machine state and camera preview
- Allow remote access through Tailscale

Depends on:

- controller service
- camera service

### Controller Service

Purpose:

- Own active machine state
- Validate commands
- Communicate with Arduino
- Stop movement during faults

Depends on:

- Arduino serial connection
- system safety configuration

### Camera Service

Purpose:

- Open camera device
- Capture frames
- Provide frames to dashboard and AI
- Save snapshots when requested

Depends on:

- camera hardware
- calibration files

### AI Service

Purpose:

- Receive camera frames
- Run object detection or strategy logic
- Recommend actions to controller

Depends on:

- camera service
- controller service
- AI model files

### Watchdog Service

Purpose:

- Check that key services are alive
- Record failures
- Trigger safe stop when needed
- Restart non-critical services when safe

Depends on:

- controller service
- system logs

### Tailscale Service

Purpose:

- Provide secure private remote access
- Avoid public dashboard exposure
- Support remote maintenance

Depends on:

- Raspberry Pi network connection
- Tailscale account/device authorization

## Safe Startup Order

```text
1. Tailscale/network
2. logging
3. controller
4. camera
5. ai
6. dashboard
7. watchdog
```

Controller should start before dashboard and AI so all commands have a safety boundary.

## Safe Shutdown Order

```text
1. dashboard stops accepting commands
2. AI stops sending recommendations
3. controller sends stop command
4. Arduino confirms idle or fault state
5. camera service closes
6. logs flush
```
