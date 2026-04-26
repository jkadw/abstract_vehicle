# My Vehicles

`my_vehicles` is a Home Assistant custom integration that builds a stable vehicle layer on top of your existing vehicle-related integrations.

Instead of tying dashboards and automations directly to one source integration, `My Vehicles` normalizes vehicle state, capability entities, and actions behind a smaller shared model.

## Why Use It

`My Vehicles` is useful when you want:

- one consistent aggregate entity per vehicle
- stable capability entities such as lock, charging, windows, lids, and location
- a predictable action surface in the `my_vehicles` domain
- less automation churn when a source integration names things differently

## Installation

HACS-style installation:

1. Add this repository to HACS as a custom repository, or install it from HACS if it is already published there.
2. Install `My Vehicles`.
3. Restart Home Assistant.
4. Go to `Settings -> Devices & Services -> Add Integration`.
5. Add `My Vehicles`.

## Setup

Setup is mapping-driven:

1. Choose the source mapping that matches one of your installed vehicle-related integrations.
2. `my_vehicles` discovers all matching source vehicles for that mapping.
3. One `my_vehicles` config entry then manages all discovered vehicles for that selected source integration.

At runtime the integration:

- loads the selected mapping from `custom_components/my_vehicles/mappings/`
- discovers matching Home Assistant devices for the mapped source integration
- resolves canonical capabilities and actions through the generic runtime
- normalizes the data into one shared vehicle model
- creates one aggregate `sensor` entity per discovered vehicle
- creates capability-specific entities where the mapping supports them

## What You Get

### Aggregate State

Each discovered vehicle gets one main aggregate entity:

- `sensor.my_<vehicle>`

The normalized aggregate state is one of:

- `unknown`
- `unavailable`
- `offline`
- `parked`
- `charging`
- `driving`
- `error`

### Capability Entities

Depending on mapping support, `My Vehicles` can create:

- `lock.*` for `central_locking`
- `binary_sensor.*` for boolean-like capabilities such as `windows`, `doors`, `lids`, `charging`, `ignition`, `warning_messages`, and `tire_pressure`
- `sensor.*` for values such as `battery_level`, `driving_range`, and `odometer`
- `device_tracker.*` for `location`
- `button.*` for mapped actions when the specific canonical verb is available

### Services

Core device-targeted services live in the `my_vehicles` domain. Common examples are:

- `my_vehicles.central_locking`
- `my_vehicles.climate`
- `my_vehicles.ev_charging`
- `my_vehicles.vehicle_alert`
- `my_vehicles.hazard_lights`
- `my_vehicles.windows`
- `my_vehicles.refresh`
- `my_vehicles.diagnostics`

The exact available actions depend on the selected mapping and the verbs it exposes for each capability.
Most capability services take an `action` parameter such as `lock`, `start_heating`, or `turn_on`. `my_vehicles.refresh` stays parameterless.

### Aggregate Attributes

The main aggregate entity exposes normalized attributes such as:

- `battery_level`
- `driving_range`
- `locked`
- `windows_open`
- `climate_active`
- `charging_active`
- `charging_plugged`
- `latitude`
- `longitude`
- `odometer`
- `source_problems`

## Current Scope

Current scope and limitations:

- the integration works through Home Assistant entities and services from an existing source integration; it is not a direct vehicle-cloud client
- generic discovery is intentionally simple and mapping-driven
- there is no custom Lovelace card in this repository
- there is no per-window position control yet
- advanced capability domains such as `cover` or native `climate` entities are future work

## Documentation By Audience

For mapping developers:

- [Mapping Schema](./docs/mapping_schema.md)

For backend developers:

- [Backend Architecture](./docs/backend_architecture.md)
- [Domain Model](./docs/domain_model.md)

For maintainers and machine-readable project guidance:

- [PROJECT.md](./PROJECT.md)
- [PROMPTS.md](./PROMPTS.md)
