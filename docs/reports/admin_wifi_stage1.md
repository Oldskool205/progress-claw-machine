# Admin Wi-Fi Stage 1: Safe Development

## Outcome

Stage 1 adds a protected Wi-Fi setup preview to the existing touchscreen
administrator panel. It is simulation-only and cannot inspect or change the
Raspberry Pi network.

The host was checked before implementation. It currently uses `wpa_supplicant`
and `dhcpcd`; NetworkManager is installed but disabled. No networking service,
system configuration, or active connection was changed during Stage 1.

## Administrator Workflow

After PIN authentication, the administrator panel displays Wi-Fi settings with:

- current Stage 1 mode and status
- simulated network scan
- network name (SSID) input
- masked password input with a show/hide control
- a three-second press-and-hold connection simulation

Scanning deliberately returns no live networks. The operator can enter an SSID
to exercise validation, but the resulting request always reports
`executed: false` and `mode: mock`.

The connection control is enabled only when:

- the administrator session is authenticated
- the machine is idle
- maintenance mode is active

## API Contract

All Stage 1 Wi-Fi routes require the short-lived administrator session:

- `GET /api/admin/wifi/status`
- `GET /api/admin/wifi/networks`
- `POST /api/admin/wifi/connect`

The connection route also requires the exact `CONNECT_WIFI` confirmation.

## Credential Safety

Stage 1 accepts only WPA-personal-style credentials:

- SSID: 1–32 UTF-8 bytes with no control characters
- password: 8–63 UTF-8 bytes with no control characters

Open networks, captive portals, and WPA-Enterprise username authentication are
not supported.

Submitted passwords are not written to application state, logs, events, or API
responses. The password field is cleared when a request begins, when the admin
panel closes, and when the administrator logs out. The mock manager retains
only the requested SSID and timestamp for simulation feedback.

## Safety Boundary

`dashboard/backend/wifi_control.py` contains no subprocess or system-command
execution path. Stage 1 does not include:

- `wpa_cli`, `wpa_supplicant`, `nmcli`, or `dhcpcd` calls
- writes under `/etc`
- a privileged helper or sudoers rule
- network scanning or reassociation
- service restarts
- live internet connectivity checks

Those capabilities remain deferred to the separately approved security-review,
installation, and supervised-test stages.

## Test Coverage

Automated coverage verifies:

- SSID and password validation
- password non-retention
- absence of a system-execution path
- administrator authentication
- explicit confirmation
- idle-machine and maintenance-mode gates
- simulated status and scan behavior
- password redaction from responses
- presence of the protected touchscreen controls

Full repository verification on 2026-07-22:

```text
144 passed, 1 skipped in 4.56s
```

The skipped test is the explicitly opt-in live Supabase lifecycle test.
