# Admin Wi-Fi Stage 3: Installation

## Outcome

Stage 3 installed the reviewed Wi-Fi helper and exact-action sudoers rule after
all host preflight checks passed. The dashboard remains in mock mode, and no
live scan, connection attempt, network restart, or Wi-Fi switch was performed.

Installation date: 2026-07-22

## Host Preflight

The approved host-level checks confirmed:

- `wpa_supplicant` is active and enabled.
- `dhcpcd` is active and enabled.
- NetworkManager is inactive and disabled.
- `wlan0` exists and is up.
- The active process uses
  `/etc/wpa_supplicant/wpa_supplicant.conf` for `wlan0`.
- The configuration is a root-owned, mode-`0600`, single-link regular file.
- `/sbin/wpa_cli`, `/usr/bin/sudo`, and `/usr/sbin/visudo` are present and
  root-owned.
- `claw-dashboard.service` runs as user and group `araya`.
- The repository sudoers template parsed successfully.
- `PROGRESS_CLAW_WIFI_MODE` was unset and therefore defaulted to `mock`.
- No previous Progress Claw Wi-Fi helper or sudoers file existed at the target
  paths.

## Installed Files

| Path | Owner | Mode | Purpose |
|---|---|---:|---|
| `/usr/local/sbin/progress-claw-wifi` | `root:root` | `0755` | Fixed-action privileged helper |
| `/etc/sudoers.d/progress-claw-wifi` | `root:root` | `0440` | Exact `status`, `scan`, and `connect` allowlist |
| `/var/lib/progress-claw/wifi` | `root:root` | `0700` | Future root-only rollback backup directory |

The installed helper SHA-256 matched the reviewed repository helper:

```text
68147055122ff85569504cb3ab8fcb6a0cab2edc776ae5df55782a4036a059bd
```

The installed sudoers SHA-256 matched the reviewed repository template:

```text
03efb1cc9080d01034ac25d411fe68f0bb177755618994c3c065f5c6f2aa5ed6
```

The installed sudoers file parsed successfully with `visudo -cf` before and
after its final placement.

## Non-Mutating Status Validation

The dashboard service user successfully invoked exactly:

```text
sudo -n /usr/local/sbin/progress-claw-wifi status
```

The helper reported an active Wi-Fi association. It did not test internet
reachability because that belongs to the supervised live stage.

The active Wi-Fi configuration was hashed immediately before and after the
status call. Both hashes were identical:

```text
1be47b9547d5c16960e762432696e132f1c3bd40f6379cb68d83ca894ee2b6e0
```

No rollback backup was created by the status operation, confirming that this
read-only path did not enter the configuration-change flow.

## Runtime State

- The project `.env` still does not set `PROGRESS_CLAW_WIFI_MODE`.
- The dashboard therefore remains in default `mock` mode.
- The dashboard and kiosk services were not restarted.
- The currently running dashboard does not invoke the installed helper.
- No network scan or connection action was called.
- `wpa_supplicant`, `dhcpcd`, and `wlan0` were not restarted or reconfigured.

## Next Approval Boundary

Stage 4 is the only stage authorized to enable live mode and perform supervised
scanning, association, rollback, internet verification, and dashboard recovery.
Before Stage 4, the operator must provide a test network SSID and WPA/WPA2
Personal password locally through the protected Admin UI. Credentials must not
be added to documentation, source control, chat, or shell command arguments.

## Regression Verification

Full repository verification after installation:

```text
161 passed, 1 skipped in 4.61s
```

The skipped test is the explicitly opt-in live Supabase lifecycle test.
