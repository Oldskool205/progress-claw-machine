# Architecture

## Runtime

The intended runtime is a Paper Minecraft server running Java 21.

## Module Boundaries

- `claw-core` owns shared services, command registration, configuration loading, persistence adapters, and common utilities.
- `claw-lobby` depends on core behavior and owns player-facing lobby systems.
- `claw-gameplay` depends on core behavior and owns gameplay mechanics.

## Repository Boundaries

- `server/` contains runtime configuration and content.
- `assets/` contains resource pack and brand assets.
- `infra/` contains local and deployment infrastructure.
- `scripts/` contains repeatable developer tasks.
