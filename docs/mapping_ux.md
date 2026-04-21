# Mapping UX

This document describes the intended user experience for mapping source entities into the `vehicle` integration.

## User Selection Flow

The user should map one logical vehicle at a time.

Recommended flow:

1. Choose a source integration or adapter type.
2. Select the source vehicle, device, or entity group that represents one real vehicle.
3. Review suggested mappings for the core v1 capabilities.
4. Confirm the mapping and create the vehicle entity.

The UX should stay simple in v1:

- prefer guided selection over free-form configuration
- group mappings by semantic capability, not by raw entity domain
- show only the fields needed for the minimal stable model
- allow incomplete setups when some capabilities are missing

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
- adapters should keep OEM-specific details hidden from the user where possible

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
- no OEM-specific setup screens outside what the adapter needs
- no requirement for full feature parity before setup can complete

Guiding principle:

- users map vehicle concepts, not OEM implementation details
