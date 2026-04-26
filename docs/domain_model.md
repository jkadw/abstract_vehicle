# Vehicle Domain Model

This document defines the stable domain model for the `my_vehicles`
integration.

## State Model

The integration exposes one aggregate state entity per vehicle:

- `sensor.my_<vehicle>`

Its friendly name is `My <device>`.

When state capabilities are available, the integration may also expose capability-specific entities in standard Home Assistant domains such as:

- `sensor.*`
- `binary_sensor.*`
- `lock.*`
- `device_tracker.*`

Normalized aggregate states:

- `unknown`
- `unavailable`
- `offline`
- `parked`
- `charging`
- `driving`
- `error`

Rules:

- `charging` dominates other states
- `offline` means the source backend or API is not reachable
- `driving` is only used when a reliable signal exists
- `error` is only used for explicit fault conditions
- `parked` is the default fallback when the vehicle is available but not
  otherwise active
- the aggregate `sensor.*` entity is the canonical overview entity for the
  integration
- actions target the `my_vehicles` device, not individual entities

## Capability Model

The mapping model is organized around canonical capabilities, not around a
split between capabilities, metrics, and derived entities.

Every supported source integration is normalized onto the same capability list.
Each mapping file must declare every canonical capability explicitly, even when
unsupported.

Canonical capabilities:

- `lock_vehicle`
- `climate`
- `charging`
- `horn`
- `flash_lights`
- `hazard_lights`
- `location`
- `ignition`
- `driving_range`
- `range_warning`
- `odometer`
- `tire_pressure`
- `warning_messages`
- `info_messages`
- `windows`
- `doors`
- `lids`
- `battery_level`
- `refresh`

Each capability has:

- one required `state` definition in the mapping
- optional `actions`

Capability support is still represented in runtime attributes as:

- `state_supported`
- `action_supported`

The meaning of each capability is fixed here, not in individual mapping files.

Canonical verbs are also fixed per capability in the Python registry. Mapping
files may only use those verbs.

Examples:

- `lock_vehicle`
  Semantics: vehicle door locking state plus `lock` and `unlock` actions when
  available.
- `climate`
  Semantics: cabin climate state plus `start` and `stop` actions when
  available.
- `charging`
  Semantics: EV charging state plus optional `start` and `stop` actions when
  the source integration supports them.
- `horn`
  Semantics: horn trigger action and any corresponding state if a source
  integration exposes one.
- `flash_lights`
  Semantics: headlight flash action and any corresponding state if exposed.
- `hazard_lights`
  Semantics: warning or hazard light state and `turn_on` / `turn_off` actions when
  available.
- `location`
  Semantics: current vehicle position.
- `ignition`
  Semantics: ignition or vehicle-on state.
- `driving_range`
  Semantics: remaining estimated range.
- `range_warning`
  Semantics: low-range warning, often derived from range.
- `odometer`
  Semantics: total distance traveled.
- `tire_pressure`
  Semantics: tire pressure status or measurement exposure.
- `warning_messages`
  Semantics: critical warning indicators.
- `info_messages`
  Semantics: informational vehicle messages.
- `windows`
  Semantics: combined window status plus optional window actions if a source
  integration supports them.
- `doors`
  Semantics: combined door-open status.
- `lids`
  Semantics: hood, trunk, frunk, or similar lid status plus optional actions.
- `battery_level`
  Semantics: traction-battery level where available.
- `refresh`
  Semantics: explicit refresh action exposed by the source integration.

Example mapping shape:

```yaml
capabilities:
  lock_vehicle:
    state:
      entity: lock.{vehicle}_door_lock
    actions:
      lock:
        action: kia_uvo.lock
        data:
          device_id: {device}
      unlock:
        action: kia_uvo.unlock
        data:
          device_id: {device}
  windows:
    state:
      any:
        - binary_sensor.{vehicle}_front_left_window
        - binary_sensor.{vehicle}_front_right_window
  horn:
    state:
      unavailable: true
```

## Attribute Schema

The aggregate vehicle entity exposes normalized attributes describing the
current vehicle snapshot and capability support. The exact runtime payload can
grow, but the stable shape is:

- `manufacturer: str`
- `model: str`
- `vehicle_type: ev|phev|ice|hybrid|unknown`
- `battery_level: float | null`
- `driving_range: float | null`
- `range: float | null`
- `locked: true|false|unknown`
- `windows_open: true|false|unknown`
- `climate_active: true|false|unknown`
- `charging_active: true|false|unknown`
- `charging_plugged: true|false|unknown`
- `ignition_on: true|false|unknown`
- `latitude: float | null`
- `longitude: float | null`
- `odometer: float | null`
- `warning_messages: object | null`
- `info_messages: object | null`
- `source_problems: object | null`

Capability support flags:

- `lock_vehicle_state_supported: bool`
- `lock_vehicle_action_supported: bool`
- `climate_state_supported: bool`
- `climate_action_supported: bool`
- `charging_state_supported: bool`
- `charging_action_supported: bool`
- `horn_state_supported: bool`
- `horn_action_supported: bool`
- `flash_lights_state_supported: bool`
- `flash_lights_action_supported: bool`
- `hazard_lights_state_supported: bool`
- `hazard_lights_action_supported: bool`
- `location_state_supported: bool`
- `location_action_supported: bool`
- `ignition_state_supported: bool`
- `ignition_action_supported: bool`
- `driving_range_state_supported: bool`
- `driving_range_action_supported: bool`
- `range_warning_state_supported: bool`
- `range_warning_action_supported: bool`
- `odometer_state_supported: bool`
- `odometer_action_supported: bool`
- `tire_pressure_state_supported: bool`
- `tire_pressure_action_supported: bool`
- `warning_messages_state_supported: bool`
- `warning_messages_action_supported: bool`
- `info_messages_state_supported: bool`
- `info_messages_action_supported: bool`
- `windows_state_supported: bool`
- `windows_action_supported: bool`
- `doors_state_supported: bool`
- `doors_action_supported: bool`
- `lids_state_supported: bool`
- `lids_action_supported: bool`
- `battery_level_state_supported: bool`
- `battery_level_action_supported: bool`
- `refresh_state_supported: bool`
- `refresh_action_supported: bool`

The schema is stable by name. Unsupported capabilities should still appear in
support flags as `false`.

## Windows Aggregation

All openings are aggregated into one semantic capability result:

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

- mappings may inherit source metadata or override it where needed
- adapters return raw values and source units when available
- normalization converts raw values into configured units
- entities expose normalized values only
- distance-bearing capability entities use normalized display units
- conversion behavior stays centralized rather than being reimplemented per
  mapping

## Service Definitions

Core services:

- `my_vehicles.lock_vehicle`
- `my_vehicles.unlock_vehicle`
- `my_vehicles.start_climate`
- `my_vehicles.stop_climate`
- `my_vehicles.start_charging`
- `my_vehicles.stop_charging`
- `my_vehicles.flash_lights`
- `my_vehicles.honk`
- `my_vehicles.turn_on_hazard_lights`
- `my_vehicles.turn_off_hazard_lights`
- `my_vehicles.refresh`

Rules:

- services must check `action_supported` before execution
- services target the `my_vehicles` device exposed by the integration
- services delegate to adapters rather than encoding source-integration-specific
  behavior in entities
- canonical service verbs should match the canonical action verbs defined by the
  registry
- unsupported services should fail clearly and predictably
