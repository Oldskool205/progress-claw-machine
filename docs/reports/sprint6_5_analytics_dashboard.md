# Sprint 6.5 Analytics Dashboard

## Outcome

Sprint 6.5 adds a read-only analytics foundation around the existing public
runtime and intelligence contracts. It does not add a hardware command path.

The machine dashboard now links to `/analytics`, which shows current event
counts and a filterable event table. Operators can filter by category, event
type, confidence, session, and time, or export the filtered view as CSV.

## Event Schema

Every event contains:

- `event_id`: generated event identifier
- `timestamp`: ISO-8601 timestamp
- `category`: `runtime`, `vision`, `game_state`, `recommendation`, or `safety`
- `event_type`: source-specific state or event name
- `source`: the public service contract that produced the observation
- `confidence`: optional normalized confidence
- `session_id`: optional play/session correlation value
- `details`: source-specific structured data

## Data Sources

`AnalyticsService` reads only:

- `RuntimeController.status()`
- the latest `DetectionCache` result
- recent `GameStateCache` events
- recent `RecommendationCache` entries

Runtime fault or emergency state is categorized as a safety event. Vision,
game-state, and recommendation records retain their source confidence. Repeated
polls are deduplicated, and collection is serialized for concurrent Flask
requests.

The analytics package does not import an Arduino adapter, GPIO module, command
model, or controller implementation. All analytics routes are GET-only.

## Storage and Retention

The first analytics slice deliberately uses a bounded, thread-safe in-memory
store. The default capacity is 1,000 events and can be changed with
`CLAW_ANALYTICS_MAX_EVENTS`. Oldest events are evicted first. Data resets when
the dashboard process restarts.

This keeps Raspberry Pi disk growth bounded while the durable storage,
privacy, and retention policy remains undecided. CSV export is operator-driven
and does not change the store.

## API

- `GET /analytics`
- `GET /analytics/events`
- `GET /analytics/summary`
- `GET /analytics/export.csv`

`/analytics/events` and `/analytics/export.csv` accept `category`,
`event_type`, `source`, `session_id`, `min_confidence`, `start`, `end`, and
`limit`. Invalid time, confidence, and limit values return HTTP 400.

## Verification

Verification on 2026-07-20:

```text
136 passed, 1 skipped in 8.92s
```

The skipped test is the explicitly opt-in live Supabase lifecycle test. New
coverage verifies event retention and deduplication, filters, safety-event
classification, API validation, CSV schema, dashboard rendering, and that the
analytics event endpoint rejects POST requests.

## Deferred

- Durable analytics storage across process restarts
- Approved long-term retention and privacy policy
- Background sampling independent of API reads
- Explicit play outcome/session identifiers throughout all upstream services
- Autonomous AI action requests and rejection analytics, which do not yet
  exist in the current informational Recommendation Engine
