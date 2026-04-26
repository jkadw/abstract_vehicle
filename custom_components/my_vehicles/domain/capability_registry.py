"""Structured canonical capability registry for My Vehicles."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class EntityGenerationRule:
    """One HA entity variant that may be generated for a capability."""

    domain: str
    key: str
    device_class: str | None = None
    state_class: str | None = None
    icon: str | None = None
    create_always: bool = False
    create_when_state_supported: bool = False
    create_when_action_supported: bool = False
    create_when_source_domain: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ButtonGenerationRule:
    """One button exposed for a canonical action verb."""

    action: str
    key: str
    icon: str | None = None
    create_when_action_supported: bool = True


@dataclass(frozen=True, slots=True)
class CapabilityUiPolicy:
    """Entity-generation policy for one canonical capability."""

    state_entities: tuple[EntityGenerationRule, ...] = ()
    control_entities: tuple[EntityGenerationRule, ...] = ()
    buttons: tuple[ButtonGenerationRule, ...] = ()


@dataclass(frozen=True, slots=True)
class CapabilityDefinition:
    """Canonical capability definition plus action verbs and UI policy."""

    name: str
    action_verbs: tuple[str, ...] = ()
    applicable_vehicle_types: tuple[str, ...] = ("ice", "hev", "phev", "ev")
    ui: CapabilityUiPolicy = field(default_factory=CapabilityUiPolicy)


CAPABILITY_REGISTRY: dict[str, CapabilityDefinition] = {
    "lock_vehicle": CapabilityDefinition(
        name="lock_vehicle",
        action_verbs=("lock", "unlock"),
        applicable_vehicle_types=("ice", "hev", "phev", "ev"),
        ui=CapabilityUiPolicy(
            state_entities=(
                EntityGenerationRule(
                    domain="lock",
                    key="lock_vehicle",
                    icon="mdi:lock",
                    create_always=True,
                ),
                EntityGenerationRule(
                    domain="binary_sensor",
                    key="vehicle_locked",
                    device_class="lock",
                    icon="mdi:lock",
                    create_when_state_supported=True,
                ),
            ),
            buttons=(
                ButtonGenerationRule(
                    action="lock",
                    key="lock_vehicle",
                    icon="mdi:lock",
                ),
                ButtonGenerationRule(
                    action="unlock",
                    key="unlock_vehicle",
                    icon="mdi:lock-open-variant",
                ),
            ),
        ),
    ),
    "climate": CapabilityDefinition(
        name="climate",
        action_verbs=("start_heating", "start_cooling", "stop"),
        applicable_vehicle_types=("ice", "hev", "phev", "ev"),
        ui=CapabilityUiPolicy(
            state_entities=(
                EntityGenerationRule(
                    domain="binary_sensor",
                    key="climate_active",
                    device_class="running",
                    icon="mdi:fan",
                    create_when_state_supported=True,
                ),
            ),
            buttons=(
                ButtonGenerationRule(
                    action="start_heating",
                    key="start_heating_climate",
                    icon="mdi:radiator",
                ),
                ButtonGenerationRule(
                    action="start_cooling",
                    key="start_cooling_climate",
                    icon="mdi:snowflake",
                ),
                ButtonGenerationRule(action="stop", key="stop_climate", icon="mdi:fan-off"),
            ),
        ),
    ),
    "fuel_level": CapabilityDefinition(
        name="fuel_level",
        applicable_vehicle_types=("ice", "hev", "phev"),
        ui=CapabilityUiPolicy(
            state_entities=(
                EntityGenerationRule(
                    domain="sensor",
                    key="fuel_level",
                    icon="mdi:gas-station",
                    create_when_state_supported=True,
                ),
            ),
        ),
    ),
    "fuel_driving_range": CapabilityDefinition(
        name="fuel_driving_range",
        applicable_vehicle_types=("ice", "hev", "phev"),
        ui=CapabilityUiPolicy(
            state_entities=(
                EntityGenerationRule(
                    domain="sensor",
                    key="fuel_driving_range",
                    device_class="distance",
                    icon="mdi:map-marker-distance",
                    create_when_state_supported=True,
                ),
            ),
        ),
    ),
    "ev_battery_level": CapabilityDefinition(
        name="ev_battery_level",
        applicable_vehicle_types=("ev", "phev"),
        ui=CapabilityUiPolicy(
            state_entities=(
                EntityGenerationRule(
                    domain="sensor",
                    key="ev_battery_level",
                    device_class="battery",
                    icon="mdi:battery",
                    create_when_state_supported=True,
                ),
            ),
        ),
    ),
    "ev_driving_range": CapabilityDefinition(
        name="ev_driving_range",
        applicable_vehicle_types=("ev", "phev"),
        ui=CapabilityUiPolicy(
            state_entities=(
                EntityGenerationRule(
                    domain="sensor",
                    key="ev_driving_range",
                    device_class="distance",
                    icon="mdi:map-marker-distance",
                    create_when_state_supported=True,
                ),
            ),
        ),
    ),
    "ev_plugged_in": CapabilityDefinition(
        name="ev_plugged_in",
        applicable_vehicle_types=("ev", "phev"),
        ui=CapabilityUiPolicy(
            state_entities=(
                EntityGenerationRule(
                    domain="binary_sensor",
                    key="ev_plugged_in",
                    device_class="plug",
                    icon="mdi:power-plug",
                    create_when_state_supported=True,
                ),
            ),
        ),
    ),
    "ev_charging": CapabilityDefinition(
        name="ev_charging",
        action_verbs=("start", "stop"),
        applicable_vehicle_types=("ev", "phev"),
        ui=CapabilityUiPolicy(
            state_entities=(
                EntityGenerationRule(
                    domain="binary_sensor",
                    key="ev_charging",
                    device_class="battery_charging",
                    icon="mdi:ev-station",
                    create_when_state_supported=True,
                ),
            ),
            control_entities=(
                EntityGenerationRule(
                    domain="switch",
                    key="ev_charging",
                    icon="mdi:ev-station",
                    create_when_action_supported=True,
                    create_when_source_domain=("switch",),
                ),
            ),
            buttons=(
                ButtonGenerationRule(action="start", key="start_charging", icon="mdi:play"),
                ButtonGenerationRule(action="stop", key="stop_charging", icon="mdi:stop"),
            ),
        ),
    ),
    "horn": CapabilityDefinition(
        name="horn",
        action_verbs=("trigger",),
        applicable_vehicle_types=("ice", "hev", "phev", "ev"),
        ui=CapabilityUiPolicy(
            state_entities=(
                EntityGenerationRule(
                    domain="binary_sensor",
                    key="horn_active",
                    icon="mdi:bullhorn",
                    create_when_state_supported=True,
                ),
            ),
            buttons=(
                ButtonGenerationRule(action="trigger", key="horn", icon="mdi:bullhorn"),
            ),
        ),
    ),
    "flash_lights": CapabilityDefinition(
        name="flash_lights",
        action_verbs=("trigger",),
        applicable_vehicle_types=("ice", "hev", "phev", "ev"),
        ui=CapabilityUiPolicy(
            state_entities=(
                EntityGenerationRule(
                    domain="binary_sensor",
                    key="lights_flashing",
                    icon="mdi:car-light-high",
                    create_when_state_supported=True,
                ),
            ),
            buttons=(
                ButtonGenerationRule(
                    action="trigger",
                    key="flash_lights",
                    icon="mdi:car-light-high",
                ),
            ),
        ),
    ),
    "hazard_lights": CapabilityDefinition(
        name="hazard_lights",
        action_verbs=("turn_on", "turn_off"),
        applicable_vehicle_types=("ice", "hev", "phev", "ev"),
        ui=CapabilityUiPolicy(
            state_entities=(
                EntityGenerationRule(
                    domain="binary_sensor",
                    key="hazard_lights",
                    device_class="problem",
                    icon="mdi:hazard-lights",
                    create_when_state_supported=True,
                ),
            ),
            control_entities=(
                EntityGenerationRule(
                    domain="switch",
                    key="hazard_lights",
                    icon="mdi:hazard-lights",
                    create_when_action_supported=True,
                    create_when_source_domain=("switch",),
                ),
            ),
            buttons=(
                ButtonGenerationRule(
                    action="turn_on",
                    key="turn_on_hazard_lights",
                    icon="mdi:hazard-lights",
                ),
                ButtonGenerationRule(
                    action="turn_off",
                    key="turn_off_hazard_lights",
                    icon="mdi:hazard-lights",
                ),
            ),
        ),
    ),
    "location": CapabilityDefinition(
        name="location",
        applicable_vehicle_types=("ice", "hev", "phev", "ev"),
        ui=CapabilityUiPolicy(
            state_entities=(
                EntityGenerationRule(
                    domain="device_tracker",
                    key="location",
                    icon="mdi:map-marker",
                    create_when_state_supported=True,
                ),
            ),
        ),
    ),
    "ignition": CapabilityDefinition(
        name="ignition",
        applicable_vehicle_types=("ice", "hev", "phev", "ev"),
        ui=CapabilityUiPolicy(
            state_entities=(
                EntityGenerationRule(
                    domain="binary_sensor",
                    key="ignition",
                    device_class="power",
                    icon="mdi:power",
                    create_when_state_supported=True,
                ),
            ),
        ),
    ),
    "driving_range": CapabilityDefinition(
        name="driving_range",
        applicable_vehicle_types=("ice", "hev", "phev", "ev"),
        ui=CapabilityUiPolicy(
            state_entities=(
                EntityGenerationRule(
                    domain="sensor",
                    key="driving_range",
                    device_class="distance",
                    icon="mdi:map-marker-distance",
                    create_when_state_supported=True,
                ),
            ),
        ),
    ),
    "range_warning": CapabilityDefinition(
        name="range_warning",
        applicable_vehicle_types=("ice", "hev", "phev", "ev"),
        ui=CapabilityUiPolicy(
            state_entities=(
                EntityGenerationRule(
                    domain="binary_sensor",
                    key="range_warning",
                    device_class="problem",
                    icon="mdi:alert",
                    create_when_state_supported=True,
                ),
            ),
        ),
    ),
    "odometer": CapabilityDefinition(
        name="odometer",
        applicable_vehicle_types=("ice", "hev", "phev", "ev"),
        ui=CapabilityUiPolicy(
            state_entities=(
                EntityGenerationRule(
                    domain="sensor",
                    key="odometer",
                    device_class="distance",
                    state_class="total_increasing",
                    icon="mdi:counter",
                    create_when_state_supported=True,
                ),
            ),
        ),
    ),
    "tire_pressure": CapabilityDefinition(
        name="tire_pressure",
        applicable_vehicle_types=("ice", "hev", "phev", "ev"),
        ui=CapabilityUiPolicy(
            state_entities=(
                EntityGenerationRule(
                    domain="binary_sensor",
                    key="tire_pressure",
                    device_class="problem",
                    icon="mdi:car-tire-alert",
                    create_when_state_supported=True,
                ),
            ),
        ),
    ),
    "warning_messages": CapabilityDefinition(
        name="warning_messages",
        applicable_vehicle_types=("ice", "hev", "phev", "ev"),
        ui=CapabilityUiPolicy(
            state_entities=(
                EntityGenerationRule(
                    domain="binary_sensor",
                    key="warning_messages",
                    device_class="problem",
                    icon="mdi:alert-circle",
                    create_when_state_supported=True,
                ),
            ),
        ),
    ),
    "info_messages": CapabilityDefinition(
        name="info_messages",
        applicable_vehicle_types=("ice", "hev", "phev", "ev"),
        ui=CapabilityUiPolicy(
            state_entities=(
                EntityGenerationRule(
                    domain="sensor",
                    key="info_messages",
                    icon="mdi:message-text",
                    create_when_state_supported=True,
                ),
            ),
        ),
    ),
    "windows": CapabilityDefinition(
        name="windows",
        action_verbs=("open", "close"),
        applicable_vehicle_types=("ice", "hev", "phev", "ev"),
        ui=CapabilityUiPolicy(
            state_entities=(
                EntityGenerationRule(
                    domain="binary_sensor",
                    key="windows",
                    device_class="window",
                    icon="mdi:car-door",
                    create_when_state_supported=True,
                ),
            ),
            control_entities=(
                EntityGenerationRule(
                    domain="switch",
                    key="windows",
                    icon="mdi:car-door",
                    create_when_action_supported=True,
                    create_when_source_domain=("switch",),
                ),
            ),
            buttons=(
                ButtonGenerationRule(
                    action="open",
                    key="open_windows",
                    icon="mdi:car-door",
                ),
                ButtonGenerationRule(
                    action="close",
                    key="close_windows",
                    icon="mdi:car-door-lock",
                ),
            ),
        ),
    ),
    "doors": CapabilityDefinition(
        name="doors",
        applicable_vehicle_types=("ice", "hev", "phev", "ev"),
        ui=CapabilityUiPolicy(
            state_entities=(
                EntityGenerationRule(
                    domain="binary_sensor",
                    key="doors",
                    device_class="door",
                    icon="mdi:car-door",
                    create_when_state_supported=True,
                ),
            ),
        ),
    ),
    "lids": CapabilityDefinition(
        name="lids",
        action_verbs=("open", "close"),
        applicable_vehicle_types=("ice", "hev", "phev", "ev"),
        ui=CapabilityUiPolicy(
            state_entities=(
                EntityGenerationRule(
                    domain="binary_sensor",
                    key="lids",
                    device_class="opening",
                    icon="mdi:car-back",
                    create_when_state_supported=True,
                ),
            ),
            control_entities=(
                EntityGenerationRule(
                    domain="switch",
                    key="lids",
                    icon="mdi:car-back",
                    create_when_action_supported=True,
                    create_when_source_domain=("switch",),
                ),
            ),
        ),
    ),
    "refresh": CapabilityDefinition(
        name="refresh",
        action_verbs=("refresh",),
        applicable_vehicle_types=("ice", "hev", "phev", "ev"),
        ui=CapabilityUiPolicy(
            buttons=(
                ButtonGenerationRule(
                    action="refresh",
                    key="refresh",
                    icon="mdi:refresh",
                ),
            ),
        ),
    ),
}

CORE_CAPABILITIES: tuple[str, ...] = tuple(CAPABILITY_REGISTRY)
CANONICAL_ACTIONS: dict[str, tuple[str, ...]] = {
    name: definition.action_verbs
    for name, definition in CAPABILITY_REGISTRY.items()
}
CAPABILITY_SUPPORT_ATTRIBUTE_SCHEMA: tuple[str, ...] = tuple(
    attr_name
    for capability_name in CORE_CAPABILITIES
    for attr_name in (
        f"{capability_name}_state_supported",
        f"{capability_name}_action_supported",
    )
)
DOCUMENTED_ATTRIBUTE_SCHEMA: tuple[str, ...] = (
    "manufacturer",
    "model",
    "vehicle_type",
    "fuel_level",
    "fuel_driving_range",
    "ev_battery_level",
    "ev_driving_range",
    "ev_plugged_in",
    "ev_charging",
    "driving_range",
    "locked",
    "windows_open",
    "climate_active",
    "latitude",
    "longitude",
    "odometer",
    *CAPABILITY_SUPPORT_ATTRIBUTE_SCHEMA,
)


def get_capability_definition(name: str) -> CapabilityDefinition:
    """Return the canonical definition for one capability."""

    return CAPABILITY_REGISTRY[name]


def state_entity_rules_for_domain(domain: str) -> tuple[tuple[str, EntityGenerationRule], ...]:
    """Return state-entity rules for one HA domain."""

    return tuple(
        (capability_name, rule)
        for capability_name, definition in CAPABILITY_REGISTRY.items()
        for rule in definition.ui.state_entities
        if rule.domain == domain
    )


def control_entity_rules_for_domain(domain: str) -> tuple[tuple[str, EntityGenerationRule], ...]:
    """Return control-entity rules for one HA domain."""

    return tuple(
        (capability_name, rule)
        for capability_name, definition in CAPABILITY_REGISTRY.items()
        for rule in definition.ui.control_entities
        if rule.domain == domain
    )


def button_rules() -> tuple[tuple[str, ButtonGenerationRule], ...]:
    """Return all button rules keyed by canonical capability."""

    return tuple(
        (capability_name, rule)
        for capability_name, definition in CAPABILITY_REGISTRY.items()
        for rule in definition.ui.buttons
    )


def button_rule_map() -> dict[str, tuple[str, ButtonGenerationRule]]:
    """Return button rules keyed by their exposed key/service name."""

    return {
        rule.key: (capability_name, rule)
        for capability_name, rule in button_rules()
    }


def should_create_entity_rule(
    rule: EntityGenerationRule,
    *,
    state_supported: bool,
    action_supported: bool,
    source_domains: set[str] | None = None,
) -> bool:
    """Return whether one registry entity rule should create an entity."""

    if rule.create_always:
        return True
    if rule.create_when_state_supported and state_supported:
        return True
    if rule.create_when_action_supported and action_supported:
        return True
    if rule.create_when_source_domain and source_domains:
        return bool(set(rule.create_when_source_domain) & source_domains)
    return False
