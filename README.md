# Vehicle

`vehicle` is a Home Assistant custom integration that provides a stable, manufacturer-agnostic vehicle abstraction.

The goal is to keep dashboards, automations, and scripts stable even when the underlying vehicle integration changes. Instead of exposing OEM-specific semantics directly, `vehicle` normalizes raw data behind a small shared domain model.

## Purpose

This project is built around three layers:

- adapters collect raw vehicle data and execute actions
- normalization converts raw values into a canonical model
- the entity layer exposes one aggregate Home Assistant entity per vehicle

The current v1 scope focuses on a minimal, stable foundation:

- normalized vehicle state
- structured capabilities with separate state and action support
- centralized normalization and unit conversion hooks
- one aggregate entity per vehicle
- a mock adapter for development and tests
- a `kia_uvo`-based adapter that maps configured vehicles

## Setup

Current setup is intentionally minimal.

Supported paths today:

1. Add the integration through Home Assistant.
2. Choose an adapter type in the config flow.
3. For the mock adapter, select a scenario such as `parked`, `charging`, or `offline`.
4. For `kia_uvo`, provide configured vehicle payloads in the config entry data and select the target `vehicle_id`.

At runtime the integration:

- creates the configured adapter
- reads raw state, raw metrics, and capabilities
- normalizes the data into the shared model
- exposes one aggregate sensor-style vehicle entity

## Examples

Example normalized state values:

- `unknown`
- `unavailable`
- `offline`
- `parked`
- `charging`
- `driving`
- `error`

Example capability structure:

```yaml
capabilities:
  lock:
    state_supported: true
    action_supported: true
  windows:
    state_supported: true
    action_supported: false
  climate:
    state_supported: true
    action_supported: true
```

Example services:

- `vehicle.lock`
- `vehicle.unlock`
- `vehicle.start_climate`
- `vehicle.stop_climate`

Example normalized attributes:

- `battery_level`
- `range`
- `locked`
- `windows_open`
- `climate_active`
- `charging_active`
- `charging_plugged`
- `latitude`
- `longitude`
- `odometer`

## Limitations

This repository is still early-stage and intentionally incomplete.

Current limitations:

- no full OEM discovery flow yet
- no production-ready vehicle mapping UX in the config flow
- no direct OEM API clients in this repository
- no UI card
- no per-window control
- only a minimal service surface is implemented
- Home Assistant runtime tests are not executed in this workspace

The `kia_uvo` adapter now supports configured vehicles at runtime, but entry data still needs to supply those mapped vehicle payloads until a richer mapping/setup flow is added.

## More Detail

Additional docs:

- [Domain Model](./docs/domain_model.md)
- [OEM Adapter Strategy](./docs/oem_adapter_strategy.md)
- [Mapping UX](./docs/mapping_ux.md)
