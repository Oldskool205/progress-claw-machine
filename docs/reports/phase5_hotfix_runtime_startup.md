# Phase 5 Hotfix Runtime Startup

## Summary

This hotfix verifies the Phase 5 dashboard refactor startup path and keeps
`main.py` aligned with the refactored Flask entry point.

## Files changed

- `docs/reports/phase5_hotfix_runtime_startup.md`

## Runtime startup decision

`main.py` imports only:

```python
from dashboard.backend.app import app, start_background_workers
```

It calls `start_background_workers()` before `app.run()`. This ensures the
controller startup and camera worker initialization use the same code path as
the dashboard entry point after the Phase 5 refactor.

`main.py` does not import `add_event`, `camera_worker`, or
`initialize_start_output` directly.

## Service verification

`system/progress-claw.service` remains compatible with the runtime entry point:

```ini
ExecStart=/usr/bin/python3 /opt/progress-claw/main.py
```

No service command change was required.

## Formatting

All Python source files were checked with Black. The systemd service file was
reviewed and remains in normal multiline unit-file format.

## Tests

Commands run:

```bash
python3 -m py_compile main.py dashboard/backend/app.py dashboard/backend/dashboard_state.py
python3 -m unittest discover -s tests
```

Results:

- Python compile check passed.
- Unit test discovery passed: `Ran 13 tests ... OK`.

## Known limitations

- This hotfix does not change dashboard behavior or route responses.
- Camera availability still depends on the production host camera stack
  producing frames after the background worker starts.
