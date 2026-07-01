# Controller

The controller module is responsible for turning system decisions into safe machine actions.

## Subfolders

- `core/`: controller-level coordination and shared controller concepts
- `api/`: public controller interfaces used by other modules
- `adapters/`: adapters between controller logic and hardware implementations
- `safety/`: emergency stop, motion limits, timing limits, and fault handling
- `protocols/`: command formats and communication contracts

This module should hide hardware-specific details from the dashboard and AI layers.
