# Sprint 6.3 Game State Engine

## Architecture

Sprint 6.3 adds a rule-based Game State Engine that interprets detection results,
runtime status, and timer/event context into high-level game states.

New package:

- `game/state_engine.py`: rule-based state interpreter.
- `game/state_models.py`: state enum and event model.
- `game/state_cache.py`: latest-state cache plus recent event ring buffer.
- `game/rules.py`: object, runtime, prize-zone, and event rules.
- `game/events.py`: `/game/state` and `/game/events` API blueprint.

The engine does not control Arduino, does not modify RuntimeController behavior, and
does not make AI decisions.

## Data Flow

```text
YOLO Detection Service
  -> DetectionCache
  -> GameStateEngine
  -> GameStateCache
  -> /game/state
  -> /game/events
```

Runtime status is read through the existing RuntimeController public `status()` method.
The engine only reads this status and never sends runtime commands.

## States

Supported states:

- `IDLE`
- `PLAYER_PRESENT`
- `PLAYER_COUNT_CHANGED`
- `READY_TO_PLAY`
- `PLAYING`
- `GRABBING`
- `PRIZE_DETECTED`
- `PRIZE_CAPTURED`
- `FAILED_ATTEMPT`
- `TIMEOUT`
- `ERROR`

Each event uses this shape:

```json
{
  "state": "PLAYER_PRESENT",
  "timestamp": "2026-07-02T00:00:00+00:00",
  "confidence": 0.91,
  "source": "vision",
  "details": {}
}
```

## Transition Rules

Initial rules:

- Runtime fault, last error, or emergency stop -> `ERROR`
- Running runtime status -> `PLAYING`
- Expired play timer -> `TIMEOUT`
- Runtime event containing grab/claw context -> `GRABBING`
- Confident teddy bear inside configured prize zone -> `PRIZE_DETECTED`
- Confident person detection -> `PLAYER_PRESENT`
- Person count change after prior person detection -> `PLAYER_COUNT_CHANGED`
- No person after idle timeout -> `IDLE`
- Missing detection data -> `ERROR`

Future states such as `READY_TO_PLAY`, `PRIZE_CAPTURED`, and `FAILED_ATTEMPT` are
defined in the model for later rules when the surrounding runtime events exist.

## API

`GET /game/state`

Evaluates current inputs and returns the latest state event.

`GET /game/events`

Evaluates current inputs and returns recent state events:

```json
{
  "events": []
}
```

Existing Dashboard and Vision APIs are unchanged.

## Configuration

Config file: `config/game_state.yaml`

```yaml
player_presence_threshold: 1
idle_timeout_seconds: 5
detection_confidence_threshold: 0.5
state_update_interval_ms: 250
timeout_seconds: 60

prize_zone:
  x_min: 0
  y_min: 0
  x_max: 10000
  y_max: 10000
```

## Tests

New tests:

- `tests/test_game_state_engine.py`
- `tests/test_game_state_cache.py`
- `tests/test_game_state_api.py`

Verification run:

```bash
python3 -m py_compile main.py vision/*.py dashboard/backend/*.py game/*.py
python3 -m unittest discover -s tests
```

Result:

```text
Ran 43 tests in 0.839s
OK
```

## Known Limitations

- Dashboard-side Game State Engine currently owns an isolated `DetectionCache`; wiring it
  to a deployed Vision Service detection cache remains future integration work.
- `READY_TO_PLAY`, `PRIZE_CAPTURED`, and `FAILED_ATTEMPT` are modeled but need richer
  runtime or sensor events before reliable rules can be added.
- Prize-zone values are interpreted as bounding-box coordinate ranges.
- No AI decision-making or hardware control is included in this sprint.
