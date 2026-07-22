# Admin Wi-Fi Stage 2: Security Review

## Outcome

Stage 2 defines and tests the privileged Wi-Fi boundary without installing or
activating it. The dashboard remains in `PROGRESS_CLAW_WIFI_MODE=mock`.

No file was copied to `/usr/local/sbin` or `/etc/sudoers.d`, no live scan was
performed, and no networking service or connection was changed.

Reviewed repository templates:

- `scripts/system/progress-claw-wifi`
- `system/progress-claw-wifi.sudoers`
- `dashboard/backend/wifi_control.py`

## Platform Decision

This Raspberry Pi currently runs `wpa_supplicant` and `dhcpcd` on `wlan0`.
NetworkManager is installed but disabled. The helper therefore targets the
active stack and does not enable or introduce a second network manager.

The first live version supports WPA/WPA2 Personal PSK networks only. Open
networks, WPA3-SAE-only networks, WPA-Enterprise usernames, captive portals,
and static-IP configuration remain unsupported.

## Privilege Boundary

The unprivileged dashboard can request only these exact commands:

```text
sudo -n /usr/local/sbin/progress-claw-wifi status
sudo -n /usr/local/sbin/progress-claw-wifi scan
sudo -n /usr/local/sbin/progress-claw-wifi connect
```

The sudoers template lists each complete action separately. There is no shell,
wildcard action, arbitrary executable, arbitrary path, or arbitrary command
argument. The repository sudoers template parses successfully with `visudo
-cf`; installation and ownership checks are deferred to Stage 3.

The helper itself accepts exactly `status`, `scan`, or `connect`. Its internal
`wpa_cli` action allowlist is fixed to `status`, `scan`, `scan_results`, and
`reconfigure`, using the fixed `/sbin/wpa_cli` executable and `wlan0`
interface. `shell=True` and `os.system` are not used.

## Credential Handling

- The password is sent to the helper through standard input as bounded JSON.
- It never appears in the process argument list or sudo command log.
- Input is limited to 512 bytes and must contain exactly `ssid` and `password`.
- Both dashboard and root-helper boundaries validate lengths and control
  characters.
- The helper derives a 256-bit WPA PSK with the standard 4096-round
  PBKDF2-HMAC-SHA1 construction.
- Only the derived PSK and hex-encoded SSID are written to the managed block.
- Helper errors and dashboard service errors are generic and credential-free.
- Dashboard responses use an explicit allowlist, so unexpected helper fields
  cannot echo a password to the browser.

Existing unmanaged `wpa_supplicant` content is preserved. If it already
contains plaintext credentials, the helper does not rewrite or expose them.

## Configuration Safety and Rollback

The helper manages one clearly marked network block in the fixed file:

```text
/etc/wpa_supplicant/wpa_supplicant.conf
```

Before modifying it, the helper requires a root-owned, non-symlinked,
single-link regular file that is not group- or world-writable and is no larger
than 1 MiB. Inconsistent or duplicate managed markers fail closed.

The previous configuration is copied to the fixed root-only backup path:

```text
/var/lib/progress-claw/wifi/wpa_supplicant.conf.backup
```

Backup and configuration writes use same-directory temporary files, mode
`0600`, file `fsync`, atomic replacement, and directory `fsync`. A fixed,
non-following root-owned lock prevents concurrent helper operations.

After reconfiguration, the helper waits for `wpa_state=COMPLETED` and the
managed `id_str`. If association fails, times out, is interrupted, or an
internal command fails, it restores the original bytes and requests another
reconfiguration. The dashboard timeout is longer than the normal helper
connection window.

## Safety Gates Retained

A live request would still require:

- configured administrator PIN and secret key
- active short-lived administrator session
- exact `CONNECT_WIFI` confirmation
- three-second touchscreen hold
- idle machine
- maintenance mode

The request remains serialized under the existing dashboard administration
lock.

## Threat Review

| Threat | Control |
|---|---|
| Command injection | Fixed executable, interface, and action allowlists; no shell |
| Password visible in `ps` | Password travels only through standard input |
| Password returned to browser | Explicit response schema strips unknown fields |
| Path traversal | Helper accepts no paths from the request |
| Symlink/hard-link attack | Config and lock file type/link checks; `O_NOFOLLOW` lock |
| Partial configuration write | Atomic replacement with file and directory sync |
| Failed network strands machine | Original configuration restored and reloaded |
| Concurrent changes | Non-blocking root-owned operation lock |
| Oversized/malformed request | 512-byte cap, exact JSON keys, duplicate validation |
| Dashboard compromise expands to shell | Sudoers permits only three exact helper actions |

## Stage 3 Preconditions

Before installation, Stage 3 must stop and report rather than repair silently
if any preflight fails:

1. Confirm `/etc/wpa_supplicant/wpa_supplicant.conf` is the active configuration.
2. Confirm actual host ownership and permissions outside the development
   sandbox.
3. Confirm `/sbin/wpa_cli`, `wlan0`, `wpa_supplicant`, and `dhcpcd` are present.
4. Install the helper as `root:root` mode `0755`.
5. Create the backup directory as `root:root` mode `0700`.
6. Install the sudoers file as `root:root` mode `0440` and run `visudo -cf`.
7. Test only non-mutating helper status in Stage 3.
8. Keep `PROGRESS_CLAW_WIFI_MODE=mock` until installation checks pass.

Live scanning, connection, rollback, internet verification, and recovery remain
reserved for the separately approved supervised Stage 4.

## Verification

Full repository verification on 2026-07-22:

```text
161 passed, 1 skipped in 7.43s
```

The skipped test is the explicitly opt-in live Supabase lifecycle test. The
repository helper has mode `0755`, and the sudoers template parsed successfully
with `visudo -cf`. The development sandbox reported its expected mapped-owner
warning for `/etc/sudo.conf`; actual host ownership remains an explicit Stage 3
preflight check.
