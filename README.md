# My Vehicles

`my_vehicles` is a Home Assistant custom integration that provides a stable vehicle abstraction on top of existing vehicle-related integrations.

The goal is to keep dashboards, automations, and scripts stable even when the underlying source integration changes. Instead of exposing integration-specific semantics directly, `my_vehicles` normalizes raw data behind a small shared domain model.

## Why This Exists

`my_vehicles` sits on top of one of your existing vehicle-related Home Assistant integrations and presents a more stable, integration-independent view of the vehicle.

In practice that means:

- one consistent aggregate entity per vehicle
- capability-specific entities where supported
- a small, stable action surface
- less coupling between your automations and the quirks of one source integration

## Installation

HACS-style installation:

1. Add this repository to HACS as a custom repository, or install it from HACS if it is already published there.
2. Install `My Vehicles`.
3. Restart Home Assistant.
4. Go to `Settings -> Devices & Services -> Add Integration`.
5. Add `My Vehicles`.

## Setup

Current setup is intentionally minimal:

1. Choose the source mapping that matches an existing vehicle-related integration you already use.
2. `my_vehicles` discovers all matching source vehicles for that mapping.
3. One `my_vehicles` config entry manages all discovered vehicles for that selected source mapping.

At runtime the integration:

- loads the selected mapping and generic runtime
- discovers source vehicles for the selected upstream integration
- reads raw state, raw metrics, and capabilities for each discovered vehicle
- normalizes the data into the shared model
- exposes one aggregate sensor entity for each discovered vehicle state
- creates per-capability entities where state support exists:
  - `sensor.*` for numeric values such as battery level, driving range, and odometer
  - `binary_sensor.*` for boolean capabilities such as windows, charging, doors, lids, and warning messages
  - `lock.*` for `lock_vehicle`
  - `device_tracker.*` for vehicle location
  - `button.*` for mapped actions when the specific canonical verb is available

## What You Get

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
  lock_vehicle:
    state_supported: true
    action_supported: true
  windows:
    state_supported: true
    action_supported: true
  climate:
    state_supported: true
    action_supported: true
```

Example services:

- `my_vehicles.lock_vehicle`
- `my_vehicles.unlock_vehicle`
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

Current limitations:

- generic discovery is still intentionally simple
- startup reconciliation and add/remove sync are not complete yet
- no direct vehicle-cloud API clients in this repository
- no UI card
- no per-window control
- only a minimal service surface is implemented
- Home Assistant runtime tests are not executed in this workspace

The current mapped-adapter path discovers vehicles from the Home Assistant registry and state model rather than talking to external vehicle services directly.

## Documentation By Audience

For mapping developers:

- [Mapping Schema](./docs/mapping_schema.md)

For backend developers:

- [Backend Architecture](./docs/backend_architecture.md)
- [Domain Model](./docs/domain_model.md)

For maintainers and machine-readable project guidance:

- [PROJECT.md](./PROJECT.md)
- [PROMPTS.md](./PROMPTS.md)
