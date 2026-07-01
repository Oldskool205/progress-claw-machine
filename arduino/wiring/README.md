# Arduino Wiring

Pin map for `arduino/sketches/arduino_claw/arduino_claw.ino`.

## Arduino Uno Pin Map

| Arduino pin | Signal | Direction | Connects to | Notes |
| --- | --- | --- | --- | --- |
| D0 / RX | FlySky iBus serial | Input | FlySky receiver iBus signal | Uses `Serial` at 115200 baud. Disconnect this wire before uploading firmware. |
| D1 / TX | USB serial TX | Output | USB serial adapter / host | Leave available for USB serial. |
| D2 | Motor 1 up button | Input pullup | Momentary button to GND | Active-low. Pressed when pin is grounded. |
| D3 | Motor 1 down button | Input pullup | Momentary button to GND | Active-low. Pressed when pin is grounded. |
| D4 | Buzzer | Output | Buzzer driver/input | Arduino toggles this while motors move. |
| D5 | Grabber PWM control | PWM output | Grabber MOSFET gate driver/input | Active-high PWM. Forced to 0 when stopped or timed out. |
| D6 | Motor 1 step | Output | Stepper driver STEP input | Pulsed by firmware. |
| D7 | Motor 1 direction | Output | Stepper driver DIR input | Direction is set before step pulses. |
| D8 | Motor 2 up button | Input pullup | Momentary button to GND | Active-low. Pressed when pin is grounded. |
| D9 | Motor 2 down button | Input pullup | Momentary button to GND | Active-low. Pressed when pin is grounded. |
| D11 | Motor 2 step | Output | Stepper driver STEP input | Pulsed by firmware. |
| D12 | Motor 2 direction | Output | Stepper driver DIR input | Direction is set before step pulses. |
| D13 | Unused | - | - | Previously used for grabber on/off; grabber moved to D5 for PWM. |
| A0 | Dashboard start gate | Input pullup | Raspberry Pi BCM GPIO 17 | Active-low. Dashboard pulls low during test/play. |
| A1 | Grabber power bit 0 | Input | Raspberry Pi BCM GPIO 22 | Effective dashboard power selection, least-significant bit. |
| A2 | Grabber power bit 1 | Input | Raspberry Pi BCM GPIO 23 | Effective dashboard power selection. |
| A3 | Grabber power bit 2 | Input | Raspberry Pi BCM GPIO 24 | Effective dashboard power selection, most-significant bit. |
| GND | Common ground | Power reference | Raspberry Pi GND, drivers, buttons, receiver, buzzer/relay drivers | All control signals need a shared ground. |

## Raspberry Pi Dashboard Connection

```text
Raspberry Pi physical pin 11 (BCM GPIO 17) -> Arduino A0
Raspberry Pi physical pin 6  (GND)         -> Arduino GND
Raspberry Pi physical pin 15 (BCM GPIO 22) -> Arduino A1
Raspberry Pi physical pin 16 (BCM GPIO 23) -> Arduino A2
Raspberry Pi physical pin 18 (BCM GPIO 24) -> Arduino A3
```

The dashboard start gate is active-low. When the dashboard starts a test or
play, GPIO 17 pulls Arduino A0 low. Releasing A0 stops movement and grabber
control immediately. The Arduino firmware also has a 180-second safety timeout.

GPIO 22, 23, and 24 select the effective grabber hold power. The dashboard
drives these pins before enabling A0 and whenever the power setting changes.
The effective power can come from Manual mode or AI Crowd Bonus mode. The three
pins are read by Arduino as a binary level:

| Dashboard power | A3 | A2 | A1 |
| --- | --- | --- | --- |
| 40% | LOW | LOW | LOW |
| 50% | LOW | LOW | HIGH |
| 60% | LOW | HIGH | LOW |
| 70% | LOW | HIGH | HIGH |
| 80% | HIGH | LOW | LOW |
| 90% | HIGH | LOW | HIGH |
| 100% | HIGH | HIGH | LOW |

AI Crowd Bonus mode uses these tiers before converting to the same A1/A2/A3
power bits:

| AI people count | Grabber hold power |
| --- | --- |
| 0-1 | 60% |
| 2-3 | 70% |
| 4 | 80% |
| 5+ | 90% |

The Raspberry Pi uses 3.3 V GPIO. Do not connect a 5 V Arduino output to a
Raspberry Pi GPIO input.

## Button Wiring

All four movement buttons use Arduino `INPUT_PULLUP`.

```text
Arduino input pin -> momentary button -> Arduino GND
```

The input reads `LOW` when pressed and `HIGH` when released. Do not wire these
button inputs to 5 V.

## Stepper Driver Wiring

Motor 1:

```text
Arduino D6 -> Motor 1 driver STEP
Arduino D7 -> Motor 1 driver DIR
Arduino GND -> Motor 1 driver signal GND
```

Motor 2:

```text
Arduino D11 -> Motor 2 driver STEP
Arduino D12 -> Motor 2 driver DIR
Arduino GND -> Motor 2 driver signal GND
```

Use the stepper driver's own motor power supply wiring for motor power. The
Arduino pins are only control signals.

## Grabber Wiring

```text
Arduino D5 -> MOSFET gate resistor -> MOSFET gate
Arduino GND -> MOSFET source/load power GND common
```

At the start of each active play window, firmware pulses D5 on/off three times
at full PWM with one second per toggle. After that, FlySky channel 6 controls
D5 using the dashboard-selected hold power while the dashboard gate remains
active. Stop and timeout force D5 PWM to 0.

The firmware uses `analogWrite()` on D5. Startup grabber pulses use full PWM.
Normal CH6 grabber hold power is selected from the dashboard. Manual mode
supports 40% to 100%; AI Crowd Bonus mode uses the people-count tiers above.

Use a MOSFET/driver stage appropriate for the grabber load. Do not drive a
solenoid, motor, or high-current coil directly from D5.

## FlySky Receiver

```text
FlySky iBus signal -> Arduino D0 / RX
FlySky GND         -> Arduino GND
FlySky VCC         -> Receiver-rated supply
```

The sketch reads FlySky iBus through Arduino `Serial`, so the receiver shares
the Arduino USB serial RX pin. Disconnect the receiver signal wire from D0
before uploading firmware, then reconnect it after upload.

Channel use in firmware:

| FlySky channel | Function |
| --- | --- |
| CH1 | Motor 2 movement |
| CH2 | Motor 1 movement |
| CH3 | Speed control |
| CH5 | Remote movement enable |
| CH6 | Grabber on/off |

## Safety Notes

- The dashboard gate on A0 must be wired and working before running the machine.
- When A0 is not held low, firmware forces step outputs, buzzer, and grabber
  output off and ignores FlySky and physical movement buttons.
- Verify every pin against the real machine wiring before powering motor,
  grabber, relay, or solenoid loads.
