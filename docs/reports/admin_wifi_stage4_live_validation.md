# Admin Wi-Fi Stage 4: Supervised Live Validation

## Outcome

Stage 4 activated the protected live Wi-Fi workflow and completed supervised
association, internet, rollback, dashboard-recovery, and machine-safety checks.

Validation date: 2026-07-22

The administrator entered the Wi-Fi password locally on the Raspberry Pi. No
credential was placed in chat, source control, documentation, environment
configuration, logs, process arguments, or API responses.

## Activation

The local ignored `.env` now selects:

```text
PROGRESS_CLAW_WIFI_MODE=live
PROGRESS_CLAW_WIFI_HELPER=/usr/local/sbin/progress-claw-wifi
```

Only `claw-dashboard.service` was restarted. `wpa_supplicant`, `dhcpcd`, the
kiosk service, and the Raspberry Pi were not restarted.

After activation:

- dashboard health was `ok`
- controller state was `ready`
- Arduino was connected
- machine was idle
- emergency stop was clear
- administrator authentication remained configured
- Wi-Fi mode reported `live`

## Live UI Validation

The protected Admin workflow successfully:

- required administrator PIN authentication
- required maintenance mode before enabling password and connection controls
- displayed real scan results
- allowed network selection
- accepted the password only through the local masked field
- required the three-second hold confirmation
- completed a live association

The selected network associated successfully, the dashboard remained healthy,
and internet verification returned HTTP 204.

## Duplicate-Request Hardening

Monitoring identified four completed requests while the operator waited for
feedback. The requests were serialized and remained safe, but repeated success
rewrote the same managed configuration and backup unnecessarily.

The live validation therefore added and deployed two hardening changes:

- the Connect button is disabled while a request is pending
- an identical already-connected configuration returns successfully without
  rewriting the configuration or rollback backup

The installed helper checksum after this hardening is:

```text
cb6d06a825d941c54a522b35470a255ad1660c5fac6fddbd72e8c94c89ce66e1
```

The installed helper matches the repository copy.

## Controlled Rollback Validation

A controlled failure used a deliberately nonexistent test SSID and non-secret
test password through helper standard input. No real credential was involved.

Observed sequence:

1. The helper installed the temporary managed configuration.
2. Association failed and the helper exited with its expected failure code.
3. The original configuration was restored byte-for-byte.
4. The immediate status check occurred before reassociation completed and
   briefly showed no LAN address or DNS.
5. The first follow-up recovery check showed the original Wi-Fi association,
   `192.168.1.10`, and internet access restored.
6. Dashboard, camera, controller, and Arduino remained healthy throughout.

Configuration checksum before and after rollback:

```text
0cf2d5e4c7cf747fc0eb83f94d90e100478cbbd00e49245aa12c8e9b79792708
```

The root-owned mode-`0600` rollback backup has the same known-good checksum.

The physical failure-and-recovery cycle took about 70 seconds because
individual `wpa_cli` operations waited during reassociation. The dashboard
executor timeout was increased from 45 to 90 seconds so it will not interrupt
that rollback window.

## Final State

- Wi-Fi: connected
- LAN dashboard: `http://192.168.1.10:5000`
- Internet check: HTTP 204
- Dashboard service: active and healthy
- Camera: ready
- Controller: ready
- Arduino: connected
- Game running: no
- Emergency stop: clear
- Maintenance mode: off
- Wi-Fi mode: live
- Managed configuration markers: exactly one matching pair
- Configuration and rollback backup: root-owned mode `0600`

## Automated Verification

Full repository verification after the live hardening changes:

```text
162 passed, 1 skipped in 7.70s
```

The skipped test is the explicitly opt-in live Supabase lifecycle test.

## Supported Network Scope

The activated helper supports WPA/WPA2 Personal PSK networks. Open networks,
WPA3-SAE-only networks, WPA-Enterprise usernames, captive portals, and static
IP configuration remain unsupported.
