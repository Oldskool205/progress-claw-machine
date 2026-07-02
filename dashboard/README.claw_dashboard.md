# Claw Control Dashboard

A local dashboard that converts a people count into claw-machine play credits.
It preserves the Arduino's FlySky iBus remote control and starts a play using a
separate Raspberry Pi GPIO signal.

## Verified compatible versions

The dashboard and Arduino sketch in this directory are a matched pair:

```text
Dashboard: /home/araya/Projects/Progress-Claw-OS/dashboard/backend/app.py
Arduino:   /home/araya/Projects/Progress-Claw-OS/arduino/sketches/arduino_claw/arduino_claw.ino
Original:  /home/araya/Claw M/C/Claw mc/remotewithdraw_copy_20260621122459/
```

The bundled Arduino sketch keeps the original FlySky movement behavior and adds
the Progress Claw OS dashboard gate, D5 MOSFET PWM grabber output, and
dashboard-selected grabber power.

## Run

```bash
cd /home/araya/Projects/Progress-Claw-OS/dashboard/backend
python3 app.py
```

Open `http://localhost:5000`.

## Connect Arduino

Use either synchronized copy of the remote-control firmware:

```bash
/home/araya/Projects/Progress-Claw-OS/arduino/sketches/arduino_claw/
```

Wire the start signal:

```text
Raspberry Pi physical pin 11 (BCM GPIO 17) -> Arduino A0
Raspberry Pi physical pin 6  (GND)         -> Arduino GND
Raspberry Pi physical pin 15 (BCM GPIO 22) -> Arduino A1
Raspberry Pi physical pin 16 (BCM GPIO 23) -> Arduino A2
Raspberry Pi physical pin 18 (BCM GPIO 24) -> Arduino A3
```

The GPIO signal is active-low. The dashboard holds it low during a test or play
after the 3-second ready message, and releases it when Stop is pressed or the
configured game-time window finishes. The Arduino also enforces a 180-second
safety timeout.
GPIO 22, 23, and 24 select the effective grabber hold power shown in the
dashboard. Effective power can come from Manual mode or AI Crowd Bonus mode.
The dashboard is the safety gate for the machine: movement and grabber hold
control remain disabled until the visible countdown begins. While stopped, the
Arduino forces both step outputs and the buzzer off and ignores all FlySky and
physical movement-button commands. FlySky movement is available only during the
dashboard play window; channel 6 cannot bypass the dashboard gate.

Wire the grabber MOSFET/driver control input to Arduino PWM pin D5. At the
start of each active play window, the Arduino pulses D5 on/off three times at
full power, then FlySky channel 6 turns D5 on/off using the dashboard-selected
hold power. Natural Time Up and the dashboard Stop button both request three
full-power D5 pulses while movement remains disabled. Reset, hacker mode, and
machine-disable stops still force D5 PWM to 0 immediately.

AI Crowd Bonus mode maps camera people count to hold power:

| AI people count | Grabber hold power |
| --- | --- |
| 0-1 | 60% |
| 2-3 | 70% |
| 4 | 80% |
| 5+ | 90% |

After a player photo is taken, the dashboard runs OpenCV people detection on
that photo and updates the `AI PEOPLE` value. If `POWER MODE` is `AI Crowd
Bonus`, the grabber hold power is updated from the table above before play.

The Raspberry Pi uses 3.3 V GPIO. Never connect a 5 V Arduino output to a
Raspberry Pi GPIO input.

## Play sequence

1. Register the player's name and take a player photo. The name is permanently
   stamped onto the saved JPEG and stored in the player list.
2. Press Start.
3. The dashboard says and displays `ARE YOU READY!` for 3 seconds.
4. GPIO 17 pulls Arduino A0 low and the Arduino pulses the grabber output
   on/off three times, with 1 second per toggle.
5. After the grabber pulse sequence finishes, the configured game-time
   countdown begins.
6. The browser beeps once per second during the countdown.
7. Natural completion displays and says `TIME UP!`, then requests three
   full-power grabber pulses.
8. Pressing Stop releases the play gate, plays the stop sound, displays
   `CLAW MACHINE STOPPED`, and requests three full-power grabber pulses.
9. Movement remains disabled during the end/Stop pulse sequence.
10. A new player photo is required for the next start.

## Upload firmware

The board configuration is:

```text
Port: /dev/ttyUSB0
FQBN: arduino:avr:uno
```

Disconnect the FlySky receiver wire from Arduino pin 0 before uploading, then
reconnect it after the upload finishes.

The dashboard checks the Arduino USB serial device on every status refresh. By
default it looks for `/dev/ttyUSB0`, `/dev/ttyUSB*`, `/dev/ttyACM*`, and
`/dev/serial/by-id/*`. Set `CLAW_ARDUINO_DEVICE=/path/to/device` before
starting `app.py` if your board should use a specific serial path.
