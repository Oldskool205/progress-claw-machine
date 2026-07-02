# System

The system module contains runtime and operating-system-level structure.

## Subfolders

- `runtime/`: runtime process definitions and startup notes
- `services/`: service definitions and background workers
- `supervisor/`: watchdog or process supervisor configuration
- `logs/`: system-level logs

This module is for running and supervising Progress Claw OS.

## Raspberry Pi systemd install

The production service unit is `system/progress-claw.service`.

Install on a Raspberry Pi:

```bash
sudo mkdir -p /opt/progress-claw /etc/progress-claw
sudo rsync -a --delete ./ /opt/progress-claw/
sudo cp system/progress-claw.service /etc/systemd/system/progress-claw.service
sudo systemctl daemon-reload
sudo systemctl enable progress-claw.service
sudo systemctl start progress-claw.service
```

Optional runtime settings can be placed in
`/etc/progress-claw/progress-claw.env`, for example:

```bash
CLAW_ARDUINO_DEVICE=/dev/ttyACM0
CLAW_USB_CAMERA_DEVICE=/dev/video0
CLAW_LOG_DIR=/opt/progress-claw/logs
PORT=5000
```

Check service and log output:

```bash
systemctl status progress-claw.service
journalctl -u progress-claw.service -f
```
