"""Switch platform for registry-driven actionable capability entities."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..domain.capability_registry import (
    CANONICAL_ACTIONS,
    control_entity_rules_for_domain,
    should_create_entity_rule,
)
from .const import DATA_ENTITIES, DATA_NORMALIZED, DATA_VEHICLES, DOMAIN
from .base import VehicleBaseEntity, capability_source_domains
from .services import async_execute_entry_action


class VehicleCapabilitySwitchEntity(VehicleBaseEntity, SwitchEntity):
    """Switch entity for one actionable canonical capability."""

    def __init__(
        self,
        normalized_data,
        entry_data,
        *,
        capability_name: str,
        key: str,
        name: str,
        icon: str | None = None,
        invert_state: bool = False,
    ) -> None:
        super().__init__(normalized_data, key, name)
        self._entry_data = entry_data
        self._capability_name = capability_name
        self._icon = icon
        self._invert_state = invert_state

    @property
    def is_on(self) -> bool | None:
        if self._capability_name == "lock_vehicle":
            if self._normalized_data.locked is None:
                return None
            return (
                not self._normalized_data.locked
                if self._invert_state
                else self._normalized_data.locked
            )
        if self._capability_name == "climate":
            return self._normalized_data.climate_active
        if self._capability_name == "charging":
            return self._normalized_data.charging_active
        if self._capability_name == "hazard_lights":
            value = self._capability_value(self._capability_name)
            return value if isinstance(value, bool) else None
        if self._capability_name == "windows":
            return self._normalized_data.windows_open
        if self._capability_name == "lids":
            value = self._capability_value(self._capability_name)
            return value if isinstance(value, bool) else None
        value = self._capability_value(self._capability_name)
        return value if isinstance(value, bool) else None

    @property
    def icon(self) -> str | None:
        return self._icon

    async def async_turn_on(self, **kwargs) -> None:
        _ = kwargs
        positive_action, _ = _switch_actions_for_capability(self._capability_name)
        await async_execute_entry_action(
            self._entry_data, self._capability_name, positive_action
        )

    async def async_turn_off(self, **kwargs) -> None:
        _ = kwargs
        _, negative_action = _switch_actions_for_capability(self._capability_name)
        await async_execute_entry_action(
            self._entry_data, self._capability_name, negative_action
        )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switch entities for a config entry."""

    entry_data = hass.data[DOMAIN][entry.entry_id]
    entities: list[SwitchEntity] = []

    for vehicle_data in entry_data[DATA_VEHICLES]:
        normalized = vehicle_data[DATA_NORMALIZED]
        vehicle_entities: list[SwitchEntity] = []
        for capability_name, rule in control_entity_rules_for_domain("switch"):
            support = normalized.capabilities.get(capability_name)
            source_domains = capability_source_domains(vehicle_data, capability_name)
            if not support.state_supported:
                continue
            if not should_create_entity_rule(
                rule,
                state_supported=support.state_supported,
                action_supported=support.action_supported,
                source_domains=source_domains,
            ):
                continue
            if len(CANONICAL_ACTIONS.get(capability_name, ())) < 2:
                continue
            vehicle_entities.append(
                VehicleCapabilitySwitchEntity(
                    normalized,
                    vehicle_data,
                    capability_name=capability_name,
                    key=rule.key,
                    name=_title(rule.key),
                    icon=rule.icon,
                    invert_state=capability_name == "lock_vehicle"
                    and "lock" in source_domains,
                )
            )

        vehicle_data[DATA_ENTITIES].extend(vehicle_entities)
        entities.extend(vehicle_entities)

    if entities:
        async_add_entities(entities)


def _switch_actions_for_capability(capability_name: str) -> tuple[str, str]:
    actions = CANONICAL_ACTIONS[capability_name]
    if len(actions) < 2:
        raise ValueError(f"Capability does not support switch actions: {capability_name}")
    return actions[0], actions[1]


def _title(value: str) -> str:
    return value.replace("_", " ").title()
