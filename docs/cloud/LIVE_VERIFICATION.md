# Live Supabase Verification

Phase A.1 live checks are explicit diagnostics. They are not called by the
normal runtime and cannot stop local machine operation.

## Create the table

Open the Supabase project, select **SQL Editor**, and run
[`machine_status.sql`](machine_status.sql). The required columns are `id`,
`machine_name`, `status`, `x_position`, `y_position`, `claw_power`, `online`,
and `updated_at`. Keep the unique constraint on `machine_name`; diagnostics use
the stable name `CLOUD-DIAGNOSTIC-TEST` and update the same row on every run.

Configure Row Level Security policies that permit the server-side key to select,
insert, update, and—only if using cleanup—delete this table. Policy design is
deployment-specific and is intentionally not automated by this migration.

## Configure credentials

Find the project URL and API key in Supabase **Project Settings > API**. Copy the
local template and edit `.env`:

```bash
cp .env.example .env
```

```dotenv
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-server-side-key
```

Use the least-privileged key suitable for the Raspberry Pi. Never use a key in
browser JavaScript, paste it into diagnostic output, or commit `.env`. The
repository `.gitignore` excludes `.env` and `.env.*` while allowing only
`.env.example`.

## Run diagnostics

```bash
python3 -m cloud.diagnostics --test-connection
python3 -m cloud.diagnostics --send-test-status
python3 -m cloud.diagnostics --heartbeat
python3 -m cloud.diagnostics --set-offline
python3 -m cloud.diagnostics --all
python3 -m cloud.diagnostics --cleanup
```

The automated live lifecycle test is also opt-in, so a normal local test run
never writes to Supabase merely because `.env` is present:

```bash
PROGRESS_CLAW_RUN_LIVE_TESTS=1 python3 -m unittest tests.live.cloud_live_test -v
```

`--test-connection` performs a bounded select of all expected columns, so it
validates credentials, table availability, schema, and read permission—not only
SDK construction. `--all` validates the schema, writes one test snapshot, sends
a heartbeat, and leaves that diagnostic row offline. `--cleanup` removes only
the dedicated diagnostic row when delete permission is available.

Expected summary:

```text
Progress Claw Cloud Diagnostic
Machine: CLOUD-DIAGNOSTIC-TEST
[PASS] connection and schema: machine_status schema is accessible
[PASS] test status: Machine status synchronized
[PASS] heartbeat: Machine status synchronized
[PASS] set offline: Machine status synchronized
Summary: 4/4 checks passed
```

View the result in Supabase **Table Editor > machine_status** and filter
`machine_name` for `CLOUD-DIAGNOSTIC-TEST`. API/Postgres activity and policy
failures are available in the Supabase project **Logs** section.

## Common safe error categories

- `not_configured`: URL or key is absent.
- `invalid_credentials`: API key or JWT was rejected.
- `missing_table`: `machine_status` is missing or unavailable.
- `schema_mismatch`: an expected column is missing.
- `rls_permission_denied`: a Row Level Security policy blocked the action.
- `network_error`: DNS, routing, or connection failure.
- `timeout`: the request exceeded its timeout.
- `cloud_error`: another cloud-only failure occurred.

Diagnostics retain categories rather than raw exception payloads. Keys and
tokens are never included in health responses. A failed diagnostic has no effect
on controller, motor, game, vision, or local dashboard health.
