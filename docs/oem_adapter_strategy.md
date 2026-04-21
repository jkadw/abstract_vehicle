# OEM Adapter Strategy

This document describes how OEM-specific adapters should fit into the `vehicle` integration without changing the shared domain model.

## Mapping Principles

- Adapters must map OEM-specific source entities and services into the stable `vehicle` domain model.
- OEM naming must stop at the adapter boundary. The rest of the integration should only see canonical fields and capabilities.
- Adapters should prefer the smallest reliable set of signals needed for v1 behavior.
- State support and action support must be modeled separately for every capability.
- When a source exposes multiple low-level signals for one concept, adapters should return the raw pieces and let normalization aggregate them.

Preferred mapping approach:

- adapter reads raw Home Assistant entities or integration state
- adapter returns raw state and raw metrics in a loose, typed structure
- normalization converts raw values into canonical state, attributes, units, and inferred support

## Entity Discovery

Adapters should discover source entities by semantic role, not by copying every available entity.

Discovery guidelines:

- identify one logical vehicle at a time
- look for stable identifiers first: VIN-like ids, device ids, unique coordinator keys, or integration device registry metadata
- collect only the entities needed for v1 capabilities:
  - lock
  - windows
  - climate
  - charging
  - location
  - battery
  - fuel
  - odometer
- prefer entities that are stable and machine-readable over display-oriented sensors

Selection rules:

- prefer explicit binary or state entities over parsing labels
- prefer one authoritative source per concept
- avoid duplicating the same concept from multiple entities unless one is a fallback
- treat missing entities as unsupported capability state, not as adapter failure

## Action Mapping

Adapters should translate canonical actions into the OEM integration’s existing Home Assistant service calls.

Canonical v1 actions:

- `lock`
- `unlock`
- `start_climate`
- `stop_climate`

Action mapping rules:

- only expose `action_supported = true` when the adapter can actually execute the action reliably
- keep action names canonical inside the adapter interface
- perform OEM-specific argument building inside the adapter, not in services or entities
- raise a clear adapter-level error for unsupported or failed actions
- refresh raw state after action execution so the normalized snapshot can be rebuilt

If an OEM integration uses unusual service names or payloads, the adapter should absorb that complexity and still present the same canonical action surface.

## Handling Missing Features

OEM integrations will vary in completeness. Missing features should degrade cleanly.

Rules:

- if a capability is not present, return `state_supported = false` and `action_supported = false`
- if state is partially available but no action exists, keep `state_supported = true` and `action_supported = false`
- if action exists but reliable state is not available, keep `action_supported = true` and `state_supported = false`
- missing optional fields should become `None` or `unknown`, not adapter errors
- explicit backend/API outage should map toward `offline`
- only use `error` for real fault conditions, not ordinary absence of data

Examples:

- no window sensors: windows capability unsupported
- window sensors but no controls: windows state-only capability
- lock action exposed but no lock state entity: action-only lock capability
- no battery entity on ICE vehicle: battery unsupported, fuel may still be supported

## Implementation Notes

- Keep adapters async-first and non-blocking.
- Prefer simple mapping tables or helper methods over large conditional branches.
- Log enough detail to debug mappings, but do not leak OEM-specific structures into the domain model.
- Add new OEM adapters by implementing the shared adapter interface, not by changing entity or normalization behavior for one manufacturer.

Guiding principle:

- adapters are replaceable; the domain model is stable
