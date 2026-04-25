# Vehicle Mapping Schema

Audience: mapping developers who add or maintain YAML mapping files.

This document defines the minimal v1 schema for YAML-driven adapter mappings in the `my_vehicles` integration.

The goal is to move integration-specific mapping rules out of Python heuristics and into explicit mapping files, while keeping the mapping format simple, Home Assistant-friendly, and easy to validate.

## Purpose

A mapping file defines:

- which source integration the adapter depends on
- how source entities map to canonical vehicle capabilities
- how measurement-like values map to canonical metrics
- how optional derived entities are exposed
- how canonical actions map to Home Assistant service calls

The mapping file does not define:

- canonical state precedence
- advanced unit conversion logic
- asynchronous startup or retry behavior
- Home Assistant registry access details beyond generic discovery by `integration.domain`

Those remain in Python.

## Top-Level Structure

Each mapping file must contain:

- `integration`
- `capabilities`

Optional sections:

- `metrics`
- `derived`

Example shape:

```yaml
integration:
  domain: kia_uvo
  friendly_name: Hyundai / Kia Connect

capabilities:
  lock:
    state: lock.{vehicle}_door_lock
    actions:
      lock:
        action: lock
        data:
          device_id: {device}
      unlock:
        action: unlock
        data:
          device_id: {device}

metrics:
  range:
    state: sensor.{vehicle}_total_driving_range
```

## Integration Metadata

`integration` defines metadata about the upstream Home Assistant integration.

Required fields:

- `domain: str`
- `friendly_name: str`

Rules:

- `domain` must match the upstream Home Assistant integration domain
- `friendly_name` is user-facing only
- v1 supports exactly one upstream integration per mapping file
- generic discovery uses `integration.domain` to find candidate Home Assistant devices

## Capability Definitions

`capabilities` defines how canonical `my_vehicles` capabilities are derived from source entities and actions.

Supported v1 capability names:

- `lock`
- `windows`
- `climate`
- `charging`
- `location`
- `refresh`

Each capability may define:

- `state`
- `actions`

Either section may be omitted.

This preserves state/action separation.

Capability boundary:

- capabilities should represent semantic feature areas
- measurement-like values such as battery level, fuel level, range, and odometer should be modeled in `metrics`
- `location` remains a capability because it represents support for exposing vehicle position, while `latitude` and `longitude` remain metrics

## Capability State Mapping

A capability `state` block defines how to derive canonical state support and raw values.

Supported v1 state forms:

1. Direct source reference
2. Template-derived value
3. Simple aggregation

### Direct Source Reference

```yaml
capabilities:
  location:
    state: device_tracker.{vehicle}_vehicle
```

Rules:

- `state` points to the primary source entity for passthrough mappings
- for direct `state` mappings, default Home Assistant metadata should be inherited automatically when available
- direct `state` mappings are the preferred v1 style

### Template-Derived Value

```yaml
capabilities:
  charging:
    template: "{{ states('sensor.{vehicle}_charging_state') == 'Charging' }}"
```

Rules:

- `template` is an optional escape hatch for simple derived values
- `template` should stay read-only and simple
- templates should not replace structured action or aggregation mappings when a simpler structure exists

### Aggregated State

```yaml
capabilities:
  windows:
    any:
      - binary_sensor.{vehicle}_front_left_window
      - binary_sensor.{vehicle}_front_right_window
      - binary_sensor.{vehicle}_rear_left_window
      - binary_sensor.{vehicle}_rear_right_window
```

Supported v1 aggregation operators:

- `any`
- `all`

Rules:

- `any` means true when any mapped source evaluates true
- `all` means true when all mapped sources evaluate true
- aggregation is intended for simple multi-entity feature state such as windows
- aggregation is preferred over templates when the intent is simple boolean combination

## Capability State Metadata

Capability state blocks may optionally define metadata overrides.

Supported optional fields:

- `device_class`
- `state_class`
- `unit_of_measurement`
- `icon`
- `attributes`

Example:

```yaml
capabilities:
  location:
    state: device_tracker.{vehicle}_vehicle
    attributes:
      - source
      - gps_accuracy
```

Rules:

- default source metadata should always be included automatically for direct `state` mappings, even when not mentioned
- explicit metadata fields override inherited values only when needed
- `attributes` lists additional source attributes to copy through
- `attributes` should normally be omitted unless extra passthrough attributes are needed

## Capability Actions

A capability `actions` block defines which canonical actions are supported and how they call Home Assistant services. The runtime prefixes `integration.domain` automatically, so mapped action names are relative to that domain unless explicitly marked otherwise.

Example:

```yaml
capabilities:
  lock:
    state: lock.{vehicle}_door_lock
    actions:
      lock:
        action: lock
        data:
          device_id: {device}
      unlock:
        action: unlock
        data:
          device_id: {device}
```

Each action definition must contain:

- `action: <service name>`

Optional fields:

- `target`
- `data`

Rules:

- action names must match canonical action names used by the `my_vehicles` integration
- `action` is resolved as `integration.domain + "." + action` by default
- `data` may contain placeholders
- `target` remains optional for cases where Home Assistant target selectors are preferable

## Metrics Section

`metrics` is optional and defines canonical raw metric extraction for measurement-like values that do not belong in `capabilities`.

Example:

```yaml
metrics:
  battery_level:
    state: sensor.{vehicle}_ev_battery_level

  range:
    state: sensor.{vehicle}_total_driving_range
    attributes:
      - source
      - last_reset

  odometer:
    state: sensor.{vehicle}_odometer
```

Supported v1 metric names:

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
