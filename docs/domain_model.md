# Vehicle Domain Model

This document defines the stable v1 domain model for the `vehicle` integration.

## State Model

The integration exposes one aggregate entity per vehicle:

- `vehicle.my_vehicle`

Normalized states:

- `unknown`
- `unavailable`
- `offline`
- `parked`
- `charging`
- `driving`
- `error`

Rules:

- `charging` dominates other states.
- `offline` means the source backend or API is not reachable.
- `driving` is only used when a reliable signal exists.
- `error` is only used for explicit fault conditions.
- `parked` is the default fallback when the vehicle is available but not otherwise active.

## Capability Model

Capabilities are structured, not simple booleans.

Each capability exposes:

- `state_supported`
- `action_supported`

Core capabilities in v1:

- `lock`
- `windows`
- `climate`
- `charging`
- `location`
- `battery`
- `fuel`
- `odometer`

Example:

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

## Attribute Schema

Core attributes:

- `manufacturer: str`
- `model: str`
- `vehicle_type: ev|phev|ice|hybrid|unknown`
- `battery_level: float | null`
- `fuel_level: float | null`
- `range: float | null`
- `locked: true|false|unknown`
- `windows_open: true|false|unknown`
- `climate_active: true|false|unknown`
- `charging_active: true|false|unknown`
- `charging_plugged: true|false|unknown`
- `latitude: float | null`
- `longitude: float | null`
- `odometer: float | null`

Capability support flags:

- `lock_state_supported: bool`
- `lock_action_supported: bool`
- `windows_state_supported: bool`
- `windows_action_supported: bool`
- `climate_state_supported: bool`
- `climate_action_supported: bool`
- `charging_state_supported: bool`
- `charging_action_supported: bool`
- `location_state_supported: bool`
- `location_action_supported: bool`
- `battery_state_supported: bool`
- `battery_action_supported: bool`
- `fuel_state_supported: bool`
- `fuel_action_supported: bool`
- `odometer_state_supported: bool`
- `odometer_action_supported: bool`

The schema is stable by name. Validation can remain lightweight in v1.

## Windows Aggregation

All openings are aggregated into one semantic attribute:

- `windows_open`

Aggregation rules:

- Includes side windows and sunroof when available.
- The normalized value is `true` if any opening is open.
- The normalized value is `false` if all known openings are closed.
- The normalized value is `unknown` when no opening state is available.

Definition:

```text
windows_open = any(opening == "open")
```

This supports 1:n aggregation without exposing per-window controls in v1.

## Unit Configuration

Units are configured at the integration level.

Supported configuration:

- `distance_unit: km | mi`
- `temperature_unit: C | F`
- `power_unit: kW`
- `energy_unit: kWh`

Rules:

- Adapters return raw values and source units when available.
- Normalization converts raw values into configured units.
- Entities expose normalized values only.
- v1 keeps conversion behavior minimal and centralized.

## Service Definitions

Core services:

- `vehicle.lock`
- `vehicle.unlock`
- `vehicle.start_climate`
- `vehicle.stop_climate`

Optional capability-based services:

- `vehicle.start_charging`
- `vehicle.stop_charging`
- `vehicle.set_charge_limit`
- `vehicle.open_windows`
- `vehicle.close_windows`
- `vehicle.honk`
- `vehicle.flash_lights`
- `vehicle.remote_start`

Rules:

- Services must check `action_supported` before execution.
- Services delegate to adapters rather than encoding OEM behavior in entities.
- Unsupported services should fail clearly and predictably.
