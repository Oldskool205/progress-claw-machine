# Dashboard Backend

Dashboard backend and API source files live here.

Current backend responsibilities:

- serve the Flask dashboard
- track people count, credits, players, and play windows
- drive Raspberry Pi GPIO 17 as the active-low Arduino play gate
- drive Raspberry Pi GPIO 22/23/24 as the grabber hold-power selector
- compute effective grabber power from Manual or AI Crowd Bonus mode
- count people in player photos with OpenCV HOG detection

Grabber power fields:

- `grabber_power_mode`: `manual` or `ai`
- `manual_grabber_power_percent`: operator-selected manual power
- `ai_people_count`: people count provided by the AI camera pipeline
- `ai_grabber_power_percent`: power calculated from the AI count
- `grabber_power_percent`: effective power currently sent to Arduino

Manual values are clamped to 40%-100% in 10% steps. The default is 100% and can
be changed with `CLAW_GRABBER_POWER_PERCENT`. The default mode is `manual` and
can be changed with `CLAW_GRABBER_POWER_MODE`.

AI Crowd Bonus tiers:

| AI people count | Effective grabber power |
| --- | --- |
| 0-1 | 60% |
| 2-3 | 70% |
| 4 | 80% |
| 5+ | 90% |

The future AI camera service can post count updates to `/api/ai-count`:

```json
{"people": 4}
```

Photo-based counting is already wired into:

- `/api/player-photo`: browser-captured photo upload
- `/api/capture-player`: Pi/USB camera frame capture

After a player photo is accepted, the backend updates `ai_people_count`.
If `grabber_power_mode` is `ai`, the effective `grabber_power_percent` changes
immediately from the tier table above.

Default GPIO mapping:

```text
BCM GPIO 17 -> Arduino A0 play gate
BCM GPIO 22 -> Arduino A1 grabber power bit 0
BCM GPIO 23 -> Arduino A2 grabber power bit 1
BCM GPIO 24 -> Arduino A3 grabber power bit 2
```

Override the three power GPIOs with `CLAW_GRABBER_POWER_GPIOS=22,23,24` if the
wiring changes.
