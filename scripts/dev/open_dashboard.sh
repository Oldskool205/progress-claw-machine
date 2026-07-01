#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/home/araya/claw_dashboard"
URL="http://localhost:5000/"
SERVER_LOG="/tmp/claw_dashboard.log"
BROWSER_LOG="/tmp/claw_dashboard_browser.log"

if ! pgrep -f "python3 app.py" >/dev/null 2>&1; then
  cd "$APP_DIR"
  nohup /usr/bin/python3 app.py >>"$SERVER_LOG" 2>&1 &
  sleep 2
fi

xdg-open "$URL" >>"$BROWSER_LOG" 2>&1 &
exit 0
