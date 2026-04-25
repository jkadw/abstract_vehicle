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
    ui: CapabilityUiPolicy = field(default_factory=CapabilityUiPolicy)


CAPABILITY_REGISTRY: dict[str, CapabilityDefinition] = {
    "lock_vehicle": CapabilityDefinition(
        name="lock_vehicle",
        action_verbs=("lock", "unlock"),
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
            control_entities=(
                EntityGenerationRule(
                    domain="switch",
                    key="lock_vehicle",
                    icon="mdi:lock",
                    create_when_action_supported=True,
                    create_when_source_domain=("switch",),
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
        action_verbs=("start", "stop"),
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
            control_entities=(
                EntityGenerationRule(
                    domain="switch",
                    key="climate",
                    icon="mdi:fan",
                    create_when_action_supported=True,
                    create_when_source_domain=("switch", "climate"),
                ),
            ),
            buttons=(
                ButtonGenerationRule(action="start", key="start_climate", icon="mdi:fan-plus"),
                ButtonGenerationRule(action="stop", key="stop_climate", icon="mdi:fan-off"),
            ),
        ),
    ),
    "charging": CapabilityDefinition(
        name="charging",
        action_verbs=("start", "stop"),
        ui=CapabilityUiPolicy(
            state_entities=(
                EntityGenerationRule(
                    domain="binary_sensor",
                    key="charging",
                    device_class="battery_charging",
                    icon="mdi:ev-station",
                    create_when_state_supported=True,
                ),
            ),
            control_entities=(
                EntityGenerationRule(
                    domain="switch",
                    key="charging",
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
    "warning_lights": CapabilityDefinition(
        name="warning_lights",
        action_verbs=("on", "off"),
        ui=CapabilityUiPolicy(
            state_entities=(
                EntityGenerationRule(
                    domain="binary_sensor",
                    key="warning_lights",
                    device_class="problem",
                    icon="mdi:car-hazard-lights",
                    create_when_state_supported=True,
                ),
            ),
            control_entities=(
                EntityGenerationRule(
                    domain="switch",
                    key="warning_lights",
                    icon="mdi:car-hazard-lights",
                    create_when_action_supported=True,
                    create_when_source_domain=("switch",),
                ),
            ),
            buttons=(
                ButtonGenerationRule(action="on", key="warning_lights_on", icon="mdi:car-hazard-lights"),
                ButtonGenerationRule(action="off", key="warning_lights_off", icon="mdi:car-hazard-lights"),
            ),
        ),
    ),
    "location": CapabilityDefinition(
        name="location",
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
        ui=CapabilityUiPolicy(
            state_entities=(
                EntityGenerationRule(
                    domain="sensor",
                    key="tire_pressure",
                    icon="mdi:car-tire-alert",
                    create_when_state_supported=True,
                ),
            ),
        ),
    ),
    "critical_warnings": CapabilityDefinition(
        name="critical_warnings",
        ui=CapabilityUiPolicy(
            state_entities=(
                EntityGenerationRule(
                    domain="binary_sensor",
                    key="critical_warnings",
                    device_class="problem",
                    icon="mdi:alert-circle",
                    create_when_state_supported=True,
                ),
            ),
        ),
    ),
    "info_messages": CapabilityDefinition(
        name="info_messages",
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
        ui=CapabilityUiPolicy(
            state_entities=(
                EntityGenerationRule(
                    domain="binary_sensor",
                    key="windows_open",
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
        ),
    ),
    "doors": CapabilityDefinition(
        name="doors",
        ui=CapabilityUiPolicy(
            state_entities=(
                EntityGenerationRule(
                    domain="binary_sensor",
                    key="doors_open",
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
        ui=CapabilityUiPolicy(
            state_entities=(
                EntityGenerationRule(
                    domain="binary_sensor",
                    key="lids_open",
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
    "battery_level": CapabilityDefinition(
        name="battery_level",
        ui=CapabilityUiPolicy(
            state_entities=(
                EntityGenerationRule(
                    domain="sensor",
                    key="battery_level",
                    device_class="battery",
                    icon="mdi:battery",
                    create_when_state_supported=True,
                ),
            ),
        ),
    ),
    "refresh": CapabilityDefinition(
        name="refresh",
        action_verbs=("refresh",),
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
    "battery_level",
    "fuel_level",
    "range",
    "locked",
    "windows_open",
    "climate_active",
    "charging_active",
    "charging_plugged",
    "latitude",
    "longitude",
    "odometer",
    *CAPABILITY_SUPPORT_ATTRIBUTE_SCHEMA,
)


def get_capability_definition(name: str) -> CapabilityDefinition:
    """Return the canonical definition for one capability."""

    return CAPABILITY_REGISTRY[name]
