# Layered Architecture

Claw MC uses a layered architecture from the first commit so hardware changes do not force changes in the dashboard, AI, or game logic.

```text
Applications
    |
    |-- Dashboard / AI
    |
Business Logic
    |
Controller
    |
Hardware
    |
    |-- Arduino / GPIO / Camera
```

## 1. Applications

Path: `applications/`, `dashboard/`, `ai/`

This layer contains user-facing apps and decision-making clients.

- Dashboard UI
- AI vision and strategy clients
- Operator tools
- External API clients

Applications request actions. They should not know whether the machine is using Arduino UNO, ESP32, FlySky, GPIO, or another controller.

## 2. Business Logic

Path: `business-logic/`

This layer contains the rules of the claw machine.

- Game state
- Credit/session rules
- Movement limits
- Prize/drop rules
- AI action validation
- Maintenance mode rules

Business logic decides what should happen. It should not directly talk to hardware pins, serial ports, cameras, or remote-control protocols.

## 3. Controller

Path: `controller/`

This layer translates business commands into hardware-safe controller operations.

- Movement commands
- Safety checks
- Command throttling
- Hardware adapter selection
- Camera frame adapter interfaces
- Controller API used by dashboard and AI workflows

Controller code depends on hardware interfaces, not on one specific board.

## 4. Hardware

Path: `hardware/`, `arduino/`, `camera/`

This layer contains device-specific implementation details.

- Arduino UNO
- ESP32
- GPIO
- Camera
- FlySky or other radio controller integrations
- Motor drivers, relays, sensors, and serial protocols

When hardware changes, this should be the main layer that changes.

## Dependency Rule

Dependencies flow downward only:

```text
Applications -> Business Logic -> Controller -> Hardware
```

Lower layers should not import or depend on higher layers.
