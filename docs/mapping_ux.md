# Mapping UX

This document describes the intended and current user experience for mapping source entities into the `my_vehicles` integration.

## User Selection Flow

The user should select one source mapping or adapter at a time.

Recommended flow:

1. Choose a source integration or adapter type.
2. Create one `My Vehicles` entry for that source mapping.
3. Let the integration discover all source vehicles or devices that match the selected mapping.

The UX should stay simple in v1:

- prefer guided selection over free-form configuration
- group mappings by semantic capability, not by raw entity domain
- show only the fields needed for the minimal stable model
- allow incomplete setups when some capabilities are missing

Current implementation:

- the config flow shows an adapter dropdown first
- the selected adapter or mapping becomes one config entry
- the integration discovers all matching source devices for that entry
- one config entry owns multiple discovered `My Vehicles` devices when the source integration exposes multiple vehicles

## How Mapping Works

Mappings should be defined by semantic role.

Examples:

- lock state source
- lock action target
- climate state source
- climate action target
- battery level source
- charging status source

Rules:

- users should not need to understand the internal normalized model to complete setup
- one capability may use separate sources for state and action
- one normalized attribute may be derived from multiple raw sources
- adapters should keep source-integration-specific details hidden from the user where possible
- the aggregate `sensor.*` entity remains the primary vehicle overview even when capability entities are also created
- actions should target the vehicle device, not individual capability entities

For aggregated concepts:

- windows should be treated as one mapping group
- the user may map multiple openings into the single `windows_open` concept
- per-window control is out of scope for v1

## Suggested Mapping Behavior

The integration should help users succeed with the smallest amount of manual work.

Preferred behavior:

- auto-suggest likely source entities when a clear match exists
- mark each capability as:
  - mapped
  - partially mapped
  - unsupported
  - missing
- allow users to accept defaults and adjust only where needed
- show capability state support and action support separately

If multiple candidate sources exist:

- prefer the most stable, explicit, machine-readable entity
- show alternatives only when confidence is low or ambiguous
- avoid forcing users to map duplicate concepts unless necessary

## Debugging Support

Mapping issues should be easy to diagnose without reading code.

Useful debugging signals:

- which raw entities were selected for each capability
- which capabilities are state-only, action-only, or unsupported
- current normalized state and attributes
- which device-targeted actions are available for each discovered vehicle
- last adapter refresh result
- last action result or error message

Useful debugging behaviors:

- clear validation errors for missing required mappings
- warnings when multiple candidates conflict
- warnings when a mapped action exists but the state source is missing
- explicit indication when a capability is intentionally unsupported

## v1 Boundaries

To keep the UX minimal and stable in v1:

- no per-window control
- no advanced transformation rules in the UI
- no integration-specific setup screens outside what the adapter needs
- no requirement for full feature parity before setup can complete
- no scenario selection in the config flow

Guiding principle:

- users map vehicle concepts, not implementation details from a specific source integration
