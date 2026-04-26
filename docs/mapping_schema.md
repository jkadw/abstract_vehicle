# Vehicle Mapping Schema

Audience: mapping developers who add or maintain YAML mapping files.

This document defines the current mapping schema for YAML-driven integrations in
`my_vehicles`.

The schema is intentionally strict. A mapping file is not a loose collection of
signals. It is a declaration of how one existing vehicle-related integration
maps onto one canonical `my_vehicles` domain model.

## Purpose

A mapping file defines:

- which source integration the mapping depends on
- how every canonical vehicle capability is represented
- which canonical actions are available for those capabilities
- how `{vehicle}` and `{device}` placeholders are used in resolved entity ids and
  action payloads

The mapping file does not define:

- aggregate vehicle state precedence such as `charging` vs `parked`
- normalization rules outside a capability's own mapped state
- startup sequencing or retry behavior
- Home Assistant registry access details beyond generic discovery by
  `integration.domain`

Those remain in Python.

## Top-Level Structure

Each mapping file must contain:

- `integration`
- `capabilities`

No other top-level modeling sections are used. In particular:

- there is no `metrics`
- there is no `derived`

Everything is modeled as a canonical capability.

Example shape:

```yaml
integration:
  domain: kia_uvo
  friendly_name: Hyundai / Kia Connect

capabilities:
  lock_vehicle:
    state:
      entity: lock.{vehicle}_door_lock
    actions:
      lock:
        action: lock
        data:
          device_id: {device}
      unlock:
        action: unlock
        data:
          device_id: {device}

  driving_range:
    state:
      entity: sensor.{vehicle}_total_driving_range

  range_warning:
    state:
      domain: binary_sensor
      template: "{{ states('sensor.{vehicle}_total_driving_range') | float < 50 }}"
      device_class: problem
```

## Integration Metadata

`integration` defines metadata about the source Home Assistant integration.

Required fields:

- `domain: str`
- `friendly_name: str`

Rules:

- `domain` must match the source Home Assistant integration domain
- `friendly_name` is user-facing only
- one mapping file supports one source integration
- generic discovery uses `integration.domain` to find candidate Home Assistant
  devices

## Canonical Capability Set

Every mapping file must define exactly this set of canonical capabilities:

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

Rules:

- every listed capability must appear in the YAML
- unknown capability names are invalid
- omission is invalid, even when the source integration does not support that
  capability
- unsupported capabilities must still be declared via `state.unavailable: true`

This is intentional. It prevents drift between mapping files and makes support
levels explicit instead of implicit.

## Capability Structure

Each capability must contain:

- `state`

Each capability may contain:

- `actions`

`actions` is optional. If it is absent, the capability is treated as not
actionable by that mapping.

Example:

```yaml
capabilities:
  windows:
    state:
      any:
        - binary_sensor.{vehicle}_front_left_window
        - binary_sensor.{vehicle}_front_right_window
        - binary_sensor.{vehicle}_rear_left_window
        - binary_sensor.{vehicle}_rear_right_window
    actions:
      open:
        action: set_windows
        data:
          device_id: {device}
          flwindow: "0"
          frwindow: "0"
          rrwindow: "0"
          rlwindow: "0"
```

## State Mapping

Every capability must define exactly one `state` mode.

Supported modes:

1. `entity`
2. `any`
3. `all`
4. `template`
5. `unavailable: true`

Exactly one of those modes must be present.

### Direct Entity Reference

```yaml
state:
  entity: sensor.{vehicle}_odometer
```

Rules:

- `entity` points to one source entity
- direct entity mappings are the preferred default
- default Home Assistant metadata should be inherited automatically when
  available

### Aggregation

```yaml
state:
  any:
    - binary_sensor.{vehicle}_front_left_window
    - binary_sensor.{vehicle}_front_right_window
```

Supported aggregation operators:

- `any`
- `all`

Rules:

- `any` is true when any mapped source evaluates true
- `all` is true when all mapped sources evaluate true
- aggregation should be used instead of templates for simple boolean
  combinations

### Template State

```yaml
state:
  domain: binary_sensor
  template: "{{ states('sensor.{vehicle}_total_driving_range') | float < 50 }}"
  device_class: problem
```

Rules:

- `template` is an escape hatch for simple derived state
- templates should stay read-only and simple
- `domain` is required when the runtime cannot infer the resulting entity kind

### Explicit Unavailability

```yaml
state:
  unavailable: true
```

Rules:

- this is the required representation for unsupported canonical capabilities
- it is not valid to omit the capability instead

## State Metadata

State blocks may optionally define metadata overrides:

- `domain`
- `device_class`
- `state_class`
- `unit_of_measurement`
- `icon`
- `attributes`

Example:

```yaml
state:
  entity: sensor.{vehicle}_total_driving_range
  unit_of_measurement: km
  device_class: distance
  attributes:
    - source
```

Rules:

- source metadata should be inherited automatically for direct `entity` mappings
- explicit values override inherited metadata
- `attributes` lists extra source attributes to copy through
- metadata should only be added when needed

## Actions

`actions` maps canonical verbs to source-integration service calls.

Example:

```yaml
actions:
  refresh:
    action: button.press
    data:
      entity_id: button.{vehicle}_force_refresh
```

Each action definition must contain:

- `action: <domain.service>`

Optional fields:

- `target`
- `data`

Rules:

- action keys must match the canonical verbs registered in Python for that
  capability
- `action` must be fully qualified and unambiguous, for example `kia_uvo.lock`
  or `button.press`
- `{device}` is available for runtime device-id substitution
- `{vehicle}` is available for resolved per-vehicle entity-id substitution

## Placeholder Rules

Supported placeholders:

- `{vehicle}` for the resolved source-vehicle token inside entity ids
- `{device}` for the target Home Assistant device id in action payloads

Rules:

- `{vehicle}` is resolved per discovered source device
- `{device}` is resolved at action-execution time
- no additional placeholders are assumed unless the runtime explicitly adds them

## Validation Rules

The loader should reject mappings when any of the following are true:

- `integration` is missing
- `capabilities` is missing
- a canonical capability is missing
- an unknown capability is present
- a capability has no `state`
- a `state` block defines zero or multiple modes
- `unavailable` is present but not `true`
- `actions` contains verbs that are not canonical for that capability
- an action definition is missing `action`

There is no backward compatibility with the older split model. Files using
top-level `metrics` or `derived`, or older capability names, should fail
validation.

- `range`
- `odometer`
- `battery_level`
- `fuel_level`
- `latitude`
- `longitude`

Rules:

- metric names must map to known raw metric slots used by the adapter runtime
- direct `state` mappings are the preferred style for metrics
- `template` may be used when a metric must be derived
- default source metadata should always be included automatically for direct `state` mappings
- explicit metadata fields override inherited values only when needed

Recommended split:

- use `capabilities` for semantic feature areas such as `lock`, `charging`, `location`, and `refresh`
- use `metrics` for measurable values such as `battery_level`, `fuel_level`, `range`, and `odometer`

## Derived Section

`derived` is optional and defines computed entities that are useful to expose but are not canonical capabilities or raw metrics.

Example:

```yaml
derived:
  range_warning:
    domain: binary_sensor
    template: "{{ states('sensor.{vehicle}_total_driving_range') | float < 50 }}"
```

Supported v1 derived domains:

- `sensor`
- `binary_sensor`

Rules:

- `derived` entities must define either `state` or `template`
- `domain` is required when the derived entity type cannot be inferred
- derived entities may override metadata explicitly
- derived entities should stay read-only

## Template Rules

Templates are optional and should be used only when direct `state:` mappings are not enough.

Rules:

- templates should stay simple and read-only
- templates should not replace structured action mappings
- templates should not replace simple aggregation when `any` or `all` is sufficient
- templates are mainly for light transformations and computed values
- default metadata inheritance does not apply automatically to pure template-only entities unless a source `state` is also defined

## Placeholder Substitution

Entity patterns and action data may use placeholders.

Supported v1 placeholders:

- `{device}`
- `{vehicle}`

Example:

```yaml
actions:
  lock:
    action: lock
    data:
      device_id: {device}
```

Rules:

- `{device}`
- `{device}` resolves to the selected Home Assistant device id used for actions
- `{vehicle}` resolves to the discovered source vehicle token derived from that device's entity ids
- placeholders that cannot be resolved must fail clearly

v1 boundary:

- no arbitrary expressions beyond the supported template field
- no nested templates
- no loops or conditionals outside Jinja itself

## Validation Rules

A mapping file is valid only if:

- `integration.domain` exists
- `integration.friendly_name` exists
- `capabilities` is a mapping
- every mapping block uses a supported shape
- every mapped action name is valid and non-empty
- every placeholder is syntactically valid

Runtime validation should fail early and clearly with file/section context.

## Boundaries

To keep v1 stable, the schema intentionally does not support:

- arbitrary Python expressions
- integration-specific parser code inside YAML
- deep nested condition trees
- UI-driven mapping generation
- per-window control semantics
- multi-integration fallback chains
- full unit conversion rules in YAML

Guiding principle:

- the YAML defines explicit mapping intent
- the Python runtime resolves and executes it safely
