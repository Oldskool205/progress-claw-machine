# AI Strategy

Automated play and decision strategy logic lives here.

Current active strategy rule: AI Crowd Bonus grabber power.

The business rule is intentionally simple and explainable for players and the
marketing team:

```text
More people watching = stronger claw hold power
```

Tier mapping:

| AI people count | Grabber hold power |
| --- | --- |
| 0-1 | 60% |
| 2-3 | 70% |
| 4 | 80% |
| 5+ | 90% |

Operational notes:

- Manual power mode remains available for staff override.
- AI mode caps normal hold power at 90% to protect prize cost.
- The startup three-trigger pulse stays 100% and is not changed by AI mode.
- The selected power applies only to FlySky CH6 grabber hold during play.
