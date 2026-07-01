# Dashboard

The dashboard module contains the operator interface for Progress Claw OS.

The current claw-machine dashboard exposes:

- player registration and photo capture
- start/stop play control
- people-count reward tracking
- game-time setting
- manual grabber hold-power selection from 40% to 100%
- AI Crowd Bonus power mode driven by camera people count

The grabber power selector drives Raspberry Pi GPIO 22, 23, and 24, which are
wired to Arduino A1, A2, and A3. Arduino uses those inputs to choose the PWM
hold power on D5 after the full-power startup pulse sequence.

AI Crowd Bonus power tiers:

| AI people count | Grabber hold power |
| --- | --- |
| 0-1 | 60% |
| 2-3 | 70% |
| 4 | 80% |
| 5+ | 90% |

The startup three-trigger grabber pulse sequence remains full power. The
manual or AI-selected power applies to FlySky CH6 grabber hold power during
play.

## Subfolders

- `frontend/`: UI structure and client assets
- `backend/`: dashboard server/API structure
- `components/`: reusable dashboard widgets and controls
- `assets/`: dashboard images, icons, and static files

The long-term architecture should keep hardware details behind controller
interfaces. The current migrated dashboard still owns direct GPIO integration
for the working claw machine.
