# Dashboard Frontend

Dashboard UI source files live here.

Current operator controls include:

- manual people count
- people target
- game time
- machine enable/disable
- grabber power mode
- manual grabber power selector
- AI people count display/input

`POWER MODE` selects `Manual` or `AI Crowd Bonus`.

In Manual mode, `GRABBER POWER` supports 40%-100% in 10% steps and saves
through `/api/settings` as `grabber_power_percent`.

In AI Crowd Bonus mode, the dashboard shows `AI PEOPLE` and the effective
power calculated by the backend:

| AI people count | Grabber hold power |
| --- | --- |
| 0-1 | 60% |
| 2-3 | 70% |
| 4 | 80% |
| 5+ | 90% |

The backend turns the effective value into Raspberry Pi GPIO selection bits for
Arduino A1/A2/A3.
