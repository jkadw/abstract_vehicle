# My Vehicles

`my_vehicles` is a Home Assistant custom integration that provides a stable vehicle abstraction on top of existing vehicle-related integrations.

The goal is to keep dashboards, automations, and scripts stable even when the underlying source integration changes. Instead of exposing integration-specific semantics directly, `my_vehicles` normalizes raw data behind a small shared domain model.

## For Users

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
- YAML-driven mapped adapters that discover vehicles from Home Assistant devices and entities

## Setup

Current setup is intentionally minimal.

Supported paths today:

1. Add the integration through Home Assistant.
2. Choose a source mapping in the config flow.
3. The integration discovers all matching source vehicles for that mapping.

At runtime the integration:

- creates the configured mapping-backed adapter
- discovers source vehicles for the selected upstream integration
- reads raw state, raw metrics, and capabilities for each discovered vehicle
- normalizes the data into the shared model
- exposes one aggregate sensor entity for each discovered vehicle state
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

- `my_vehicles.lock`
- `my_vehicles.unlock`
- `my_vehicles.start_climate`
- `my_vehicles.stop_climate`
- `my_vehicles.refresh`

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

- generic discovery is still intentionally simple
- startup reconciliation and add/remove sync are not complete yet
- no direct vehicle-cloud API clients in this repository
- no UI card
- no per-window control
- only a minimal service surface is implemented
- Home Assistant runtime tests are not executed in this workspace

The current mapped-adapter path discovers vehicles from the Home Assistant registry and state model rather than talking to external vehicle services directly.

## For Mapping Developers

Adding a new mapping YAML is the normal way to add support for another existing vehicle-related integration.

Current model:

- add one YAML mapping file under `custom_components/my_vehicles/adapters/`
- the filename becomes the adapter key
- `integration.domain` determines availability
- `integration.friendly_name` is shown in the config flow
- no Python registration is needed for normal mapping-backed integrations

Only rare cases should need custom Python, and those should stay behind the explicit custom-adapter extension point in the adapter registry layer.

## More Detail

Additional docs:

- [Domain Model](./docs/domain_model.md)
- [Adapter Strategy](./docs/oem_adapter_strategy.md)
- [Mapping UX](./docs/mapping_ux.md)
