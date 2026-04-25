# Adapter Strategy

This document describes how mappings for existing vehicle-related integrations should fit into the `my_vehicles` integration without changing the shared domain model.

## Mapping Principles

- Adapters must map integration-specific source entities and services into the stable `my_vehicles` domain model.
- Integration-specific naming must stop at the adapter boundary. The rest of the integration should only see canonical fields and capabilities.
- Adapters should prefer the smallest reliable set of signals needed for v1 behavior.
- State support and action support must be modeled separately for every capability.
- When a source exposes multiple low-level signals for one concept, adapters should return the raw pieces and let normalization aggregate them.

Preferred mapping approach:

- mapping files should define explicit source mappings instead of growing Python heuristics
- generic adapter code should resolve those mappings against Home Assistant state, registry, and services
- adapters return raw state and raw metrics in a loose, typed structure
- normalization converts raw values into canonical state, attributes, units, and inferred support
- adapter definitions expose a stable friendly name for the config flow

## Entity Discovery

Adapters should discover source entities by semantic role, not by copying every available entity.

Discovery guidelines:

- discover all source devices for the selected upstream integration
- look for stable identifiers first: VIN-like ids, device ids, unique coordinator keys, or integration device registry metadata
- derive one logical vehicle from each matching source device
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

Current example:

- the `Hyundai-Kia-Connect/kia_uvo` mapping is resolved through the generic mapped-adapter runtime
- generic discovery uses the upstream integration domain plus entity-pattern matching to derive each vehicle token

## Action Mapping

Adapters should translate canonical actions into the existing vehicle-related integration’s Home Assistant service calls.

Canonical v1 actions:

- `lock`
- `unlock`
- `start_climate`
- `stop_climate`

Action mapping rules:

- only expose `action_supported = true` when the adapter can actually execute the action reliably
- keep action names canonical inside the adapter interface
- perform integration-specific argument building inside the adapter or adapter mapping, not in services or entities
- raise a clear adapter-level error for unsupported or failed actions
- refresh raw state after action execution so the normalized snapshot can be rebuilt

If an existing vehicle-related integration uses unusual service names or payloads, the adapter should absorb that complexity and still present the same canonical action surface.

## Handling Missing Features

Existing vehicle-related integrations will vary in completeness. Missing features should degrade cleanly.

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
- Prefer explicit mapping files and small helper methods over large conditional branches.
- Log enough detail to debug mappings, but do not leak integration-specific structures into the domain model.
- Add new integrations by adding mapping-backed adapter definitions whenever generic discovery and runtime behavior are sufficient.
- Only add dedicated Python hooks when the generic mapped-adapter path cannot express the needed behavior cleanly.

Guiding principle:

- adapters are replaceable; the domain model is stable
