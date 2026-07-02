# Phase 6.0 Intelligent Machine Platform Roadmap

Phase 6 turns Progress Claw Machine from a hardened operator-controlled machine
into an intelligent machine platform. This phase is planning first: no Phase 6
runtime code is introduced by this roadmap.

## Phase 6 Vision

Phase 6 adds vision, machine-state reasoning, AI decision support, and analytics
around the existing safe runtime boundary.

The platform should be able to observe the playfield, detect prizes and claw
position, infer game state, recommend or request safe actions, and present useful
operational analytics without allowing any service to bypass the controller.

The core principle remains unchanged from Phase 5:

```text
RuntimeController is the only hardware gateway.
```

Dashboard, AI, camera, analytics, plugins, and future services may call approved
APIs. They must never open Arduino serial connections, send Arduino commands, or
control GPIO hardware directly.

## Current Architecture Summary

Phase 5 established the hardened runtime boundary:

- `RuntimeController` owns active machine state and validates hardware commands.
- Dashboard routes call controller-backed APIs instead of controlling Arduino
  directly.
- The Arduino adapter is behind the controller layer.
- Health, status, play, stop, power, and emergency-stop routes are exposed
  through the dashboard backend API.
- Structured logs record runtime, command, Arduino, and safety events.
- Camera and AI behavior exists in early form, but the long-term Phase 6 design
  must route observations and recommendations through service APIs and the
  controller boundary.

Current safe control path:

```text
Operator
   |
   v
Dashboard API
   |
   v
RuntimeController
   |
   v
Arduino adapter
   |
   v
Claw machine hardware
```

Current service responsibilities:

- Dashboard: operator UI, API entry point, remote monitoring.
- RuntimeController: command validation, safety state, Arduino gateway.
- Arduino: timing-sensitive motor, claw, sensor, and actuator control.
- Camera: frame capture and snapshots.
- AI: early support logic and future decision support.
- Logging/system services: startup, health, logs, and watchdog behavior.

## Target Architecture

Phase 6 adds intelligence as service layers around the controller, not inside the
hardware boundary.

```text
Camera Service
   |
   v
Vision Service
   |
   v
Game State Engine
   |
   v
AI Decision Engine
   |
   v
Runtime API
   |
   v
RuntimeController
   |
   v
Arduino
   |
   v
Hardware
```

Dashboard and analytics consume status, observations, decisions, and history
through APIs:

```text
RuntimeController ----+
Vision Service -------+
Game State Engine ----+--> API layer --> Dashboard
AI Decision Engine ---+
Analytics Store ------+
```

Target service ownership:

- Camera Service captures frames and publishes frame metadata.
- Vision Service detects objects from frames and publishes observations.
- Game State Engine converts observations and runtime status into game state.
- AI Decision Engine recommends actions or requests approved runtime actions.
- Runtime API accepts only high-level, validated requests.
- RuntimeController validates every command before Arduino communication.
- Analytics Dashboard displays current and historical machine intelligence.

## Non-Negotiable Rules

- AI must not talk directly to Arduino.
- Camera service must not control hardware.
- Dashboard must use API only.
- RuntimeController remains the only hardware gateway.
- Services must communicate through explicit APIs or message contracts.
- Emergency stop must override operator, AI, dashboard, plugin, and scheduled
  actions.
- Any autonomous action must be traceable in command and safety logs.
- A failed AI, camera, analytics, or dashboard service must not prevent manual
  safe stop.

## Data Flow Diagrams

### Observation Flow

```text
Camera
  |
  v
Camera Service
  |
  v
Vision Service
  |
  v
Detections / confidence / frame metadata
  |
  v
Game State Engine
```

### Decision Flow

```text
Game State Engine
  |
  v
AI Decision Engine
  |
  v
Recommended action or approved action request
  |
  v
Runtime API
  |
  v
RuntimeController
  |
  v
Arduino
```

### Dashboard Flow

```text
Operator
  |
  v
Dashboard
  |
  v
Dashboard/API backend
  |
  +--> RuntimeController status
  +--> Vision observations
  +--> Game state
  +--> AI decisions
  +--> Analytics summaries
```

### Safety and Stop Flow

```text
Emergency stop / fault / watchdog
  |
  v
RuntimeController
  |
  +--> send stop to Arduino when available
  +--> reject unsafe commands
  +--> publish fault status
  +--> write safety log
```

### Analytics Flow

```text
Runtime events
Vision observations
Game states
AI decisions
Operator actions
Safety events
  |
  v
Analytics store
  |
  v
Analytics Dashboard
```

## Sprint Breakdown

### Sprint 6.1 Vision Service Foundation

Purpose:

Build the service boundary for camera frames and vision observations before
adding object detection complexity.

Scope:

- Define the Vision Service contract.
- Define frame metadata, observation payloads, confidence values, and timestamps.
- Define how the Camera Service provides frames to Vision Service.
- Add planning for calibration, frame retention, and service health checks.
- Confirm Vision Service is read-only with respect to hardware.

Acceptance criteria:

- A documented Vision Service API or message contract exists.
- Frame and observation schemas are documented.
- Service health and failure modes are documented.
- The plan states that Vision Service cannot call Arduino or hardware control
  APIs.
- Tests from Phase 5 still pass after documentation or scaffolding changes.

### Sprint 6.2 YOLO Detection Service

Purpose:

Add object detection for prizes, claw position, playfield regions, and optional
player-facing events using a YOLO-based model service.

Scope:

- Select model loading and inference boundaries.
- Define detection classes, confidence thresholds, and output schema.
- Define how annotated frames and raw detections are stored.
- Define fallback behavior when model files are missing or inference fails.
- Keep detections advisory; they do not move hardware.

Acceptance criteria:

- Detection classes and output payloads are documented.
- Confidence threshold handling is documented.
- Failure behavior returns degraded observations instead of unsafe commands.
- No detection code opens Arduino serial, GPIO, or controller internals directly.
- Logs identify model version, inference errors, and detection summary.

### Sprint 6.3 Game State Engine

Purpose:

Convert runtime status and vision observations into a structured game-state model
that downstream services can use consistently.

Scope:

- Define game states such as idle, credit-ready, aiming, dropping, claw-returning,
  win-check, fault, and emergency-stop.
- Define transitions and required inputs from RuntimeController and Vision
  Service.
- Define stale-data handling when frames, detections, or runtime status age out.
- Define confidence scoring for inferred state.
- Publish game state through API for dashboard, AI, and analytics.

Acceptance criteria:

- Game-state enum and transition rules are documented.
- Inputs from runtime status and vision observations are documented.
- Stale or conflicting inputs result in conservative state, not autonomous
  movement.
- Fault and emergency-stop states cannot be overridden by AI decisions.
- Dashboard can consume game state through API only.

### Sprint 6.4 AI Decision Engine

Purpose:

Use game state, detections, and runtime status to recommend actions or submit
safe high-level action requests.

Scope:

- Define decision inputs, outputs, and confidence scoring.
- Separate recommendations from action requests.
- Define autonomous-mode gates, operator approvals, and safety lockouts.
- Route all action requests through Runtime API and RuntimeController.
- Log decisions, rejected requests, confidence, and source state.

Acceptance criteria:

- AI decision payloads distinguish recommendation, requested action, confidence,
  and reason.
- AI cannot import or instantiate Arduino adapters.
- AI cannot bypass Runtime API or RuntimeController.
- RuntimeController can reject every AI request using the same validation rules
  as dashboard requests.
- Emergency stop, fault, manual lockout, or stale game state blocks autonomous
  actions.

### Sprint 6.5 Analytics Dashboard

Purpose:

Expose operational insight from runtime events, detections, game states, AI
decisions, safety events, and play outcomes.

Scope:

- Define analytics event schema and storage boundaries.
- Add dashboard views for machine health, play outcomes, detection quality, AI
  decisions, and safety events.
- Provide filters by time, event type, confidence, and session.
- Keep analytics read-only for hardware control.
- Include exportable reports for maintenance and tuning.

Acceptance criteria:

- Analytics data sources and event schema are documented.
- Dashboard reads analytics and runtime status through API only.
- Analytics views do not issue Arduino commands or direct hardware calls.
- Safety events and rejected AI requests are visible.
- Existing runtime API behavior remains compatible with Phase 5 tests.

## Risks and Safety Rules

### Key Risks

- AI action requests could become unsafe if they bypass controller validation.
- Camera or model latency could produce stale game-state decisions.
- False detections could cause poor strategy or unsafe autonomous requests.
- Dashboard convenience shortcuts could accidentally reintroduce direct hardware
  control.
- Analytics data growth could affect Raspberry Pi disk space.
- Service restart loops could produce repeated requests unless commands are
  idempotent and state-aware.
- Hardware faults may make visual state disagree with controller state.

### Safety Rules

- RuntimeController is the source of truth for command permission.
- RuntimeController status has priority over AI inference.
- Emergency stop and fault states block all movement requests.
- Stale vision, stale game state, or low confidence blocks autonomous action.
- Autonomous mode must be explicit and visible in dashboard state.
- Every AI-generated action request must include source state, confidence, and
  reason in logs.
- Camera, vision, game-state, analytics, and dashboard services must fail closed:
  failure removes intelligence features, not basic safety controls.
- Manual stop and emergency stop must remain available when AI, camera, or
  analytics services are down.

## Phase 6 Completion Criteria

Phase 6 is complete when the platform can observe, infer, recommend, act through
the RuntimeController boundary, and report analytics without weakening Phase 5
runtime hardening.

Minimum completion requirements:

- All Phase 6 services obey the controller boundary.
- RuntimeController remains the only Arduino gateway.
- Dashboard, AI, camera, and analytics use documented APIs only.
- Vision detections and game state are observable through dashboard/API.
- AI decisions are logged, explainable, and rejectable.
- Analytics shows runtime, vision, game-state, AI, and safety history.
- Phase 5 tests remain healthy throughout Phase 6.
