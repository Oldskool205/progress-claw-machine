# Arduino

The Arduino module contains firmware and board-specific integration files.

Current claw-machine firmware:

- reads FlySky iBus on Arduino D0/RX through `Serial`
- uses Arduino A0 as the active-low dashboard play gate
- reads Arduino A1/A2/A3 as dashboard-selected grabber hold-power bits
- drives the grabber MOSFET from Arduino D5 PWM
- keeps startup grabber pulses at full power before the countdown
- applies dashboard-selected effective hold power when FlySky CH6 controls the grabber
- uses the reserved A1/A2/A3 `HIGH/HIGH/HIGH` code to pulse D5 three times at
  Time Up or dashboard Stop while keeping movement disabled

Effective hold power can come from Manual mode or AI Crowd Bonus mode. AI mode
uses the dashboard-provided people-count tiers:

```text
0-1 people -> 60%
2-3 people -> 70%
4 people   -> 80%
5+ people  -> 90%
```

## Subfolders

- `firmware/`: firmware source structure
- `sketches/`: Arduino IDE sketches and experiments
- `protocols/`: serial command formats and board communication notes
- `wiring/`: pin maps, wiring diagrams, and hardware notes

Arduino-specific implementation should stay here so the system can later move to ESP32 or another board with minimal changes elsewhere.

Update `wiring/README.md` whenever any pin assignment or hardware connection
changes.
