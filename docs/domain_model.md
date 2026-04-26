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

Each capability has:

- one required `state` definition in the mapping
- optional `actions`

Mapped action verbs may also define an optional `availability` block. This uses
the same shape as a capability `state` mapping and controls whether the
corresponding button/service is currently available without removing the entity.
The alternative `availability_not` form is also supported when a simple negated
source condition is clearer than writing a template.

Capability support is still represented in runtime attributes as:

- `state_supported`
- `action_supported`

The meaning of each capability is fixed here, not in individual mapping files.
Canonical verbs are also fixed per capability in the Python registry. Mapping
files may only use those verbs.

Vehicle type is a property of an individual vehicle, not of a source
integration as a whole. Applicability is therefore documented per capability,
while vehicle-type discovery happens per discovered vehicle.

Canonical capabilities:

- `lock_vehicle`
  Meaning: vehicle locking state and lock control at whole-vehicle level.
  Canonical verbs: `lock`, `unlock`.
  Applicable vehicle types: `ice`, `hev`, `phev`, `ev`.

- `climate`
  Meaning: cabin climate or remote HVAC state and control.
  Canonical verbs: `start`, `stop`.
  Applicable vehicle types: `ice`, `hev`, `phev`, `ev`.

- `hazard_lights`
  Meaning: hazard or warning light control and any corresponding exposed state.
  Canonical verbs: `turn_on`, `turn_off`.
  Applicable vehicle types: `ice`, `hev`, `phev`, `ev`.

- `horn`
  Meaning: horn trigger action and any corresponding exposed state.
  Canonical verbs: `trigger`.
  Applicable vehicle types: `ice`, `hev`, `phev`, `ev`.

- `flash_lights`
  Meaning: headlight flash action and any corresponding exposed state.
  Canonical verbs: `trigger`.
  Applicable vehicle types: `ice`, `hev`, `phev`, `ev`.

- `location`
  Meaning: current vehicle position.
  Canonical verbs: none.
  Applicable vehicle types: `ice`, `hev`, `phev`, `ev`.

- `ignition`
  Meaning: ignition, engine-on, or vehicle-on state.
  Canonical verbs: none.
  Applicable vehicle types: `ice`, `hev`, `phev`, `ev`.

- `odometer`
  Meaning: total traveled distance.
  Canonical verbs: none.
  Applicable vehicle types: `ice`, `hev`, `phev`, `ev`.

- `range_warning`
  Meaning: low-range warning, often derived from another range capability.
  Canonical verbs: none.
  Applicable vehicle types: `ice`, `hev`, `phev`, `ev`.

- `tire_pressure`
  Meaning: tire pressure state, warning, or summarized status.
  Canonical verbs: none.
  Applicable vehicle types: `ice`, `hev`, `phev`, `ev`.

- `warning_messages`
  Meaning: warning indicators or warning message state.
  Canonical verbs: none.
  Applicable vehicle types: `ice`, `hev`, `phev`, `ev`.

- `info_messages`
  Meaning: informational messages or non-warning status messages.
  Canonical verbs: none.
  Applicable vehicle types: `ice`, `hev`, `phev`, `ev`.

- `windows`
  Meaning: aggregated window state and optional whole-vehicle window actions.
  Canonical verbs: `open`, `close`.
  Applicable vehicle types: `ice`, `hev`, `phev`, `ev`.

- `doors`
  Meaning: aggregated open or closed door state.
  Canonical verbs: none.
  Applicable vehicle types: `ice`, `hev`, `phev`, `ev`.

- `lids`
  Meaning: aggregated hood, trunk, frunk, tailgate, or similar lid state.
  Canonical verbs: `open`, `close`.
  Applicable vehicle types: `ice`, `hev`, `phev`, `ev`.

- `fuel_level`
  Meaning: remaining fuel level for liquid-fuel energy storage.
  Canonical verbs: none.
  Applicable vehicle types: `ice`, `hev`, `phev`.

- `fuel_driving_range`
  Meaning: remaining range attributable to fuel.
  Canonical verbs: none.
  Applicable vehicle types: `ice`, `hev`, `phev`.

- `ev_battery_level`
  Meaning: traction-battery state of charge used for electric driving.
  Canonical verbs: none.
  Applicable vehicle types: `ev`, `phev`.

- `ev_driving_range`
  Meaning: remaining electric driving range.
  Canonical verbs: none.
  Applicable vehicle types: `ev`, `phev`.

- `ev_plugged_in`
  Meaning: whether the vehicle is physically connected to external charging.
  Canonical verbs: none.
  Applicable vehicle types: `ev`, `phev`.

- `ev_charging`
  Meaning: whether the vehicle is actively charging from external power.
  Canonical verbs: `start`, `stop`.
  Applicable vehicle types: `ev`, `phev`.

- `driving_range`
  Meaning: agnostic cross-vehicle remaining driving range for dashboards,
  scripts, and automations that should not need to understand the underlying
  energy system.
  Canonical verbs: none.
  Applicable vehicle types: `ice`, `hev`, `phev`, `ev`.
  Notes: this is a convenience capability layered on top of vehicle-type-
  specific range data, not a claim that fuel and EV ranges are semantically
  identical.

- `refresh`
  Meaning: explicit refresh action exposed by the source integration.
  Canonical verbs: `refresh`.
  Applicable vehicle types: `ice`, `hev`, `phev`, `ev`.

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
- `vehicle_type: ev|phev|hev|ice|unknown`
- `driving_range: float | null`
- `fuel_level: float | null`
- `fuel_driving_range: float | null`
- `ev_battery_level: float | null`
- `ev_driving_range: float | null`
- `ev_plugged_in: true|false|unknown`
- `ev_charging: true|false|unknown`
- `locked: true|false|unknown`
- `windows_open: true|false|unknown`
- `climate_active: true|false|unknown`
- `ignition_on: true|false|unknown`
- `latitude: float | null`
- `longitude: float | null`
- `odometer: float | null`
- `warning_messages: object | null`
- `info_messages: object | null`
- `source_problems: object | null`

`vehicle_type` is always determined per discovered vehicle. It must never be
treated as a fixed property of a whole source integration.

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
- `fuel_level_state_supported: bool`
- `fuel_level_action_supported: bool`
- `fuel_driving_range_state_supported: bool`
- `fuel_driving_range_action_supported: bool`
- `ev_battery_level_state_supported: bool`
- `ev_battery_level_action_supported: bool`
- `ev_driving_range_state_supported: bool`
- `ev_driving_range_action_supported: bool`
- `ev_plugged_in_state_supported: bool`
- `ev_plugged_in_action_supported: bool`
- `ev_charging_state_supported: bool`
- `ev_charging_action_supported: bool`
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
- `refresh_state_supported: bool`
- `refresh_action_supported: bool`

The schema is stable by name. Unsupported capabilities should still appear in
support flags as `false`.

## Aggregation

All openings are aggregated into one semantic capability result:

- `windows_open`
- `doors`
- `lids`

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

The same aggregation principle also applies to other boolean group
capabilities such as `warning_messages`.

## Vehicle Type Discovery

`my_vehicles` targets four canonical vehicle types:

- `ev`
- `hev`
- `phev`
- `ice`

Vehicle type discovery is designed as a per-vehicle normalization step with a
clear precedence order.

Precedence:

1. explicit mapped vehicle-type source
2. inference from resolved capabilities and state
3. `unknown`

### 1. Explicit Mapped Vehicle-Type Source

Preferred rule:

- if a source integration exposes a reliable per-vehicle type field, `my_vehicles`
  should use it

This should be modeled as a vehicle-level input, not as integration metadata.

Examples of acceptable explicit sources:

- a source sensor or attribute that directly identifies the vehicle as EV, PHEV,
  HEV, or ICE
- an integration-specific per-vehicle property already present in Home Assistant

Rules:

- explicit mapped type wins over inference
- explicit mapped type should still be normalized onto the canonical set
  `ev | hev | phev | ice`
- unknown or unsupported source labels should not fail setup; they should fall
  through to inference or finally `unknown`

### 2. Inference From Resolved Capabilities and State

If no explicit mapped type is available, `my_vehicles` should infer vehicle
type from the resolved capability surface of that individual vehicle.

Intended inference rules:

- if EV-only charging concepts exist together with fuel concepts, infer `phev`
- if EV-only charging concepts exist without fuel concepts, infer `ev`
- if fuel concepts exist without EV charging concepts, prefer `ice`
- infer `hev` only when the source provides a reliable HEV-specific signal or
  when later registry rules define a stable way to distinguish HEV from ICE

Relevant capability groups:

- EV charging concepts:
  - `ev_plugged_in`
  - `ev_charging`
- EV energy concepts:
  - `ev_battery_level`
  - `ev_driving_range`
- fuel concepts:
  - `fuel_level`
  - `fuel_driving_range`

Interpretation guidance:

- `ev`:
  EV charging concepts are present and fuel concepts are absent
- `phev`:
  EV charging concepts and fuel concepts are both present
- `ice`:
  fuel concepts are present and EV charging concepts are absent
- `hev`:
  should not be guessed aggressively from weak signals alone

This intentionally biases toward honesty over overclassification. `hev` is the
hardest class to infer reliably without an explicit source signal, so unknown is
better than a wrong type.

### 3. Unknown Behavior

If neither an explicit mapped type nor reliable inference is available:

- set `vehicle_type = unknown`

Rules:

- `unknown` must not block setup
- `unknown` must not prevent generic capabilities such as `lock_vehicle`,
  `location`, `odometer`, `windows`, or `doors`
- `unknown` should only suppress vehicle-type-specific convenience assumptions
- users should still be able to build automations around universal capabilities
  and directly supported energy capabilities

### Design Boundary

Vehicle-type discovery should be split intentionally:

- mapping layer:
  may provide an explicit per-vehicle type source when one exists
- runtime:
  resolves the mapped source value and vehicle-level supported capabilities
- normalization:
  applies precedence, canonicalizes the final value, and exposes
  `vehicle_type`

This keeps the mapping schema small while still allowing reliable explicit
sources to override generic inference.

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
- `my_vehicles.start_heating_climate`
- `my_vehicles.start_cooling_climate`
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
