# Cloud Monitoring

Start the existing dashboard normally, then open:

```text
http://localhost:5000/cloud
```

For the standalone diagnostic service used on the Raspberry Pi, open port 5001:

```text
http://raspberry-pi-address:5001/cloud
```

The standalone app registers only Cloud Monitoring routes. The example systemd
unit is `system/progress-claw-cloud-monitor.service`.

The page reports cached local cloud health from `GET /cloud/health` (also
available as `GET /cloud/status`). Browser refreshes do not contact Supabase.

## Displayed state

- Configuration and connection state
- Dedicated diagnostic machine name
- Last diagnostic machine snapshot
- Connection, synchronization, and heartbeat timestamps
- Retry and consecutive-failure counts
- Sanitized error category
- Configured future synchronization interval

Colors mean:

- Green: a diagnostic connection or synchronization succeeded.
- Yellow: configured and waiting.
- Red: the most recent diagnostic action failed.
- Gray: credentials are not configured.

The Test Connection, Send Test Status, and Send Heartbeat buttons make explicit
diagnostic requests. All diagnostic writes use `CLOUD-DIAGNOSTIC-TEST`; they do
not read production machine state and cannot alter game or motor behavior.
Refresh Local Status reads only the in-memory health snapshot.

`Load Supabase Data` explicitly reads the dedicated diagnostic row and displays
the expected database fields in a separate Supabase Machine Data panel. The
result is cached locally. Refresh Local Status redisplays that cache and does not
make another Supabase request.

The API never returns `SUPABASE_KEY`, tokens, database passwords, the project
URL, or raw cloud exception payloads. Observability remains locally available
when Supabase is offline. There is no background periodic synchronization in
Phase A.1; `SUPABASE_SYNC_INTERVAL_SECONDS` is configuration visibility for a
future phase only.

For schema creation, credential setup, live commands, Supabase Table Editor,
logs, and RLS troubleshooting, see [LIVE_VERIFICATION.md](LIVE_VERIFICATION.md).
