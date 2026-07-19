#!/usr/bin/env bash
set -euo pipefail

KIOSK_URL="${PROGRESS_CLAW_KIOSK_URL:-http://localhost:5000/}"
KIOSK_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/progress-claw"
KIOSK_EXIT_FILE="${PROGRESS_CLAW_KIOSK_EXIT_FILE:-$KIOSK_RUNTIME_DIR/kiosk-exit-request}"
KIOSK_PROFILE_DIR="$KIOSK_RUNTIME_DIR/chromium-profile"

if command -v chromium-browser >/dev/null 2>&1; then
  CHROMIUM_BIN="chromium-browser"
elif command -v chromium >/dev/null 2>&1; then
  CHROMIUM_BIN="chromium"
else
  echo "Progress Claw kiosk: Chromium is not installed." >&2
  exit 127
fi

# This launcher intentionally starts only the browser. The dashboard backend is
# managed by its own service and must remain independent from kiosk lifecycle.
mkdir -p "$KIOSK_RUNTIME_DIR"
chmod 700 "$KIOSK_RUNTIME_DIR"
rm -f "$KIOSK_EXIT_FILE"

CHROMIUM_PID=""
KIOSK_MODE=1

start_chromium() {
  chromium_args=(
    --user-data-dir="$KIOSK_PROFILE_DIR" \
    --no-first-run \
    --disable-session-crashed-bubble \
    --disable-infobars \
    --overscroll-history-navigation=0 \
    "$KIOSK_URL"
  )
  if [[ "$KIOSK_MODE" -eq 1 ]]; then
    chromium_args=(--kiosk "${chromium_args[@]}")
  fi
  setsid "$CHROMIUM_BIN" "${chromium_args[@]}" &
  CHROMIUM_PID=$!
}

stop_chromium() {
  if [[ -n "$CHROMIUM_PID" ]] && kill -0 "$CHROMIUM_PID" 2>/dev/null; then
    # Chromium uses several child processes. The isolated session lets us stop
    # only this launcher's complete browser tree before a clean restart.
    kill -TERM -- "-$CHROMIUM_PID"
    wait "$CHROMIUM_PID" || true
  fi
}

shutdown_launcher() {
  stop_chromium
  exit 0
}
trap shutdown_launcher INT TERM

while true; do
  start_chromium
  restart_requested=0
  while kill -0 "$CHROMIUM_PID" 2>/dev/null; do
    if [[ -f "$KIOSK_EXIT_FILE" ]]; then
      kiosk_request="$(<"$KIOSK_EXIT_FILE")"
      rm -f "$KIOSK_EXIT_FILE"
      case "$kiosk_request" in
        exit)
          stop_chromium
          # Keep the dashboard visible in a normal browser window. This lets
          # the operator reopen Administrator and return to fullscreen later.
          KIOSK_MODE=0
          restart_requested=1
          break
          ;;
        restart)
          stop_chromium
          KIOSK_MODE=1
          restart_requested=1
          break
          ;;
      esac
    fi
    sleep 0.5
  done

  if [[ "$restart_requested" -eq 1 ]]; then
    continue
  fi

  # Kiosk mode is persistent: if Chromium closes or crashes on its own, return
  # to the dashboard. Only the explicit `exit` request above stops the launcher.
  wait "$CHROMIUM_PID" || true
  sleep 1
done
