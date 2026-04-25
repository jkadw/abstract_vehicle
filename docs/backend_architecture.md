# Backend Architecture

This document is for backend developers working on the Python implementation of `my_vehicles`.

It explains how the integration is structured, where responsibilities belong, and which extension points are intentional.

## Core Layers

The integration is built in four layers:

- mapping files define how an existing vehicle-related integration is interpreted
- adapter runtime resolves those mappings against Home Assistant devices, entities, and services
- normalization converts raw adapter output into the canonical domain model
- entity and service layers expose the Home Assistant-facing behavior

The intended dependency direction is:

`mapping -> adapter runtime -> normalization -> entities/services`

Not the other way around.

## Design Principles

- Keep the domain model stable even if source integrations differ.
- Keep mapping-specific semantics out of entities and services.
- Separate `state_supported` from `action_supported`.
- Keep unit conversion centralized in normalization.
- Prefer YAML-backed integrations over custom Python registration.
- Treat custom Python hooks as exceptions, not the default.

## Adapter Model

The default adapter model is mapping-driven.

Normal path:

- add one YAML mapping file under `custom_components/my_vehicles/adapters/`
- the filename becomes the adapter key
- `integration.domain` controls availability
- `integration.friendly_name` is shown in the config flow
- the generic mapped-adapter runtime handles discovery, state resolution, action preparation, and action execution

Python registration should not be required for normal mapping-backed integrations.

## Discovery Model

One `my_vehicles` config entry represents one selected source mapping.

That entry:

- discovers all matching Home Assistant devices for `integration.domain`
- derives one logical vehicle per matching source device
- resolves the `{vehicle}` token from the source device’s entities
- creates one internal vehicle record per discovered source vehicle

This is intentionally different from a one-entry-per-vehicle design.

## Runtime Responsibilities

The generic runtime is responsible for:

- loading validated mapping files
- resolving `state`, `template`, `any`, and `all`
- deriving capability support
- preparing and executing mapped actions
- collecting read-only diagnostics

The runtime should not:

- implement canonical state precedence
- perform user-facing entity decisions
- contain source-integration-specific heuristics unless there is no better generic path

## Normalization Responsibilities

Normalization owns:

- canonical vehicle state derivation
- unit conversion
- windows aggregation into `windows_open`
- normalized attribute construction
- normalized capability exposure

If a value can be represented as generic raw input plus a stable normalization rule, it belongs here rather than in adapter code.

## Entity and Service Responsibilities

Entities should stay thin.

They should:

- expose normalized values
- expose the aggregate attributes only on the main state entity
- use normalized metadata for device info
- avoid interpreting source-integration semantics

Services should:

- target `my_vehicles` devices
- validate `action_supported`
- delegate execution to adapters
- refresh normalized state after successful actions

## Extension Points

Intended extension points:

- new mapping YAML files
- generic discovery improvements
- generic runtime improvements
- normalization improvements

Narrow extension point for exceptional cases:

- custom adapter definitions in the registry layer when a source integration cannot be expressed cleanly through mappings plus the generic runtime

That path should stay rare and explicit.

## Related Docs

- [Domain Model](./domain_model.md)
- [Mapping Schema](./mapping_schema.md)
