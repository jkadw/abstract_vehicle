# My Vehicle

`vehicle` is a Home Assistant custom integration that provides a stable, manufacturer-agnostic vehicle abstraction.

The goal is to keep dashboards, automations, and scripts stable even when the underlying vehicle integration changes. Instead of exposing OEM-specific semantics directly, `vehicle` normalizes raw data behind a small shared domain model.

## Purpose

This project is built around three layers:

- adapters collect raw vehicle data and execute actions
- normalization converts raw values into a canonical model
- the entity layer exposes one aggregate state entity plus capability-specific entities

The current v1 scope focuses on a minimal, stable foundation:

- normalized vehicle state
- structured capabilities with separate state and action support
- centralized normalization and unit conversion hooks
- one aggregate `sensor.*` entity per vehicle with the friendly name `My <device>`
- per-capability entities in standard Home Assistant domains
- a mock adapter for development and tests
- a `Hyundai-Kia-Connect/kia_uvo`-based adapter that discovers vehicles from Home Assistant

## Setup

Current setup is intentionally minimal.

Supported paths today:

1. Add the integration through Home Assistant.
2. Choose an adapter type in the config flow.
3. Select one discovered vehicle from the chosen adapter.

At runtime the integration:

- creates the configured adapter
- reads raw state, raw metrics, and capabilities
- normalizes the data into the shared model
- exposes one aggregate sensor entity for the vehicle state
- creates per-capability entities where state support exists:
  - `sensor.*` for numeric values such as battery, fuel, range, and odometer
  - `binary_sensor.*` for windows, climate, and charging
  - `lock.*` for lock state and lock actions
  - `device_tracker.*` for vehicle location
  - `button.*` for refresh when the adapter supports it

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
- `vehicle.refresh`

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

- adapter discovery is still intentionally simple
- the Hyundai/Kia adapter still contains legacy Python-side mapping logic while YAML-driven mapping support is being introduced
- no direct OEM API clients in this repository
- no UI card
- no per-window control
- only a minimal service surface is implemented
- Home Assistant runtime tests are not executed in this workspace

The `Hyundai / Kia Connect` adapter currently discovers vehicles from the Home Assistant registry and state model rather than talking to the OEM service directly.

## More Detail

Additional docs:

- [Domain Model](./docs/domain_model.md)
- [OEM Adapter Strategy](./docs/oem_adapter_strategy.md)
- [Mapping UX](./docs/mapping_ux.md)
