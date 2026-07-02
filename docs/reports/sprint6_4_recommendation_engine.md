# Sprint 6.4 Recommendation Engine

## Architecture

Sprint 6.4 adds an independent Recommendation Engine that reads:

- latest Game State
- latest Vision Detection Cache result
- RuntimeController status via its public `status()` method

The engine writes only recommendations to `RecommendationCache`. It does not control
Arduino, does not modify RuntimeController, does not change machine state, and does not
execute recommendations.

New package:

- `recommendation/models.py`
- `recommendation/cache.py`
- `recommendation/rules.py`
- `recommendation/engine.py`
- `recommendation/api.py`

## Rule Engine

Initial rules are deterministic and priority ordered:

- degraded game/runtime status -> `SYSTEM_DEGRADED`
- unavailable detection/vision data -> `CHECK_CAMERA`
- Arduino disconnected beyond timeout -> `CHECK_ARDUINO`
- player present beyond configured ready window -> `READY_TO_START`
- player present but not ready long enough -> `WAIT_FOR_PLAYER`
- idle beyond demo timeout -> `START_DEMO_MODE`
- idle before demo timeout -> `WAIT_FOR_PLAYER`
- playing or unmatched state -> `NO_ACTION`

## Recommendation Types

Supported types:

- `NO_ACTION`
- `WAIT_FOR_PLAYER`
- `READY_TO_START`
- `INCREASE_CLAW_POWER`
- `REDUCE_CLAW_POWER`
- `START_DEMO_MODE`
- `STOP_DEMO_MODE`
- `CHECK_CAMERA`
- `CHECK_ARDUINO`
- `SYSTEM_DEGRADED`

## Configuration

Config file: `config/recommendation.yaml`

```yaml
player_ready_seconds: 3
idle_demo_timeout: 30
camera_timeout: 5
arduino_timeout: 5
recommendation_interval_ms: 500
```

## API

`GET /recommendation/current`

Returns the latest evaluated recommendation as JSON.

`GET /recommendation/history`

Returns recent recommendation history as JSON.

## Tests

New tests:

- `tests/test_recommendation_engine.py`
- `tests/test_recommendation_cache.py`
- `tests/test_recommendation_api.py`

Mock inputs are used for game state, detection cache, and runtime status. No camera or
Arduino hardware is required.

## Known Limitations

- Recommendations are informational only and are not executed.
- `INCREASE_CLAW_POWER`, `REDUCE_CLAW_POWER`, and demo stop recommendations are modeled
  for future gameplay telemetry but are not emitted by the initial conservative rules.
- The engine evaluates on API reads; no background recommendation scheduler is added in
  this sprint.
