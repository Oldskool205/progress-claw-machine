# Arduino Communication

This document defines the practical communication design between Raspberry Pi and Arduino.

## Current Claw Machine Connection

The working claw-machine firmware keeps FlySky iBus on Arduino D0/RX through
`Serial`, so the dashboard does not send live USB serial commands to Arduino.
Instead, the Raspberry Pi uses GPIO control lines:

```text
Raspberry Pi GPIO 17  -> Arduino A0  active-low play gate
Raspberry Pi GPIO 22  -> Arduino A1  grabber power bit 0
Raspberry Pi GPIO 23  -> Arduino A2  grabber power bit 1
Raspberry Pi GPIO 24  -> Arduino A3  grabber power bit 2
Arduino D5            -> grabber MOSFET PWM input
FlySky iBus           -> Arduino D0/RX
```

The dashboard writes an effective `grabber_power_percent`. In Manual mode this
comes from the operator selector. In AI Crowd Bonus mode it comes from camera
people-count tiers:

| AI people count | Grabber hold power |
| --- | --- |
| 0-1 | 60% |
| 2-3 | 70% |
| 4 | 80% |
| 5+ | 90% |

Arduino reads A1/A2/A3 as a binary level and converts that level to D5 PWM hold
power. The startup grabber pulse sequence still uses full PWM.

The A1/A2/A3 level `111` is reserved and is not used for normal hold power.
When the dashboard reaches natural Time Up or the operator presses Stop, it
sets A1/A2/A3 to `111` and releases A0. Arduino treats that as a request to
pulse D5 on/off three times at full PWM while all movement remains disabled.
Reset, hacker mode, machine-disable, and firmware safety timeout paths do not
send the reserved code and force D5 PWM to 0 immediately.

## Planned Serial Connection

```text
Raspberry Pi USB
      |
      v
Arduino serial port
      |
      v
Motor drivers / sensors / claw actuator
```

Recommended default:

- Transport: USB serial
- Baud rate: `115200`
- Command format: line-based text commands during early phases
- Response format: line-based status or error messages

This is the planned future controller protocol. It is not the active
claw-machine control path while FlySky iBus is using Arduino `Serial`.

## Command Direction

```text
Raspberry Pi controller/  --->  Arduino firmware
Raspberry Pi controller/  <---  Arduino status/events
```

Only the controller module should send commands to Arduino.

## Example Command Set

These are design examples, not final firmware code.

```text
PING
STOP
MOVE X POSITIVE 300
MOVE X NEGATIVE 300
MOVE Y POSITIVE 300
MOVE Y NEGATIVE 300
MOVE Z DOWN 500
MOVE Z UP 500
CLAW OPEN
CLAW CLOSE
STATUS
RESET_FAULT
```

## Example Responses

```text
OK PONG
OK STOPPED
OK MOVING X POSITIVE 300
OK STATUS IDLE
ERR UNKNOWN_COMMAND
ERR LIMIT_REACHED
ERR EMERGENCY_STOP
ERR BUSY
```

## Safety Rules

- Arduino should stop motors if no valid command is received within a timeout.
- Arduino should reject unknown commands.
- Arduino should enforce maximum movement duration.
- Emergency stop input should override serial commands.
- Controller should send `STOP` before shutdown.
- Controller should treat missing Arduino response as a fault.

## Serial Message Flow

```text
controller/
   |
   |  MOVE X POSITIVE 300
   v
arduino/
   |
   |  OK MOVING X POSITIVE 300
   v
controller/
   |
   v
dashboard status update
```

## Fault Handling Flow

```text
Arduino fault detected
      |
      v
ERR EMERGENCY_STOP
      |
      v
controller enters fault state
      |
      +--> dashboard alert
      +--> data/logs entry
      +--> maintenance report
```

## Future Upgrade Path

The early system can use simple text commands. Later phases can upgrade to:

- JSON serial messages
- checksum-protected packets
- binary protocol
- ESP32 over USB, Wi-Fi, or Bluetooth
- separate safety microcontroller
