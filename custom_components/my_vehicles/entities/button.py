"""Button platform for registry-driven vehicle actions."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..domain.capability_registry import button_rules
from ..const import DATA_ADAPTER, DATA_ENTITIES, DATA_NORMALIZED, DATA_VEHICLES, DOMAIN
from .base import VehicleBaseEntity
from ..services import async_execute_entry_action


class VehicleActionButtonEntity(VehicleBaseEntity, ButtonEntity):
    """Button entity for one canonical action."""

    def __init__(
        self,
        normalized_data,
        entry_data,
        *,
        capability_name: str,
        action_name: str,
        key: str,
        name: str,
        icon: str | None = None,
    ) -> None:
        super().__init__(normalized_data, key, name)
        self._entry_data = entry_data
        self._capability_name = capability_name
        self._action_name = action_name
        self._icon = icon
        self._attr_icon = icon

    @property
    def icon(self) -> str | None:
        return self._icon

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        adapter = self._entry_data.get(DATA_ADAPTER)
        checker = getattr(adapter, "is_action_available", None)
        if callable(checker):
            return bool(checker(self._capability_name, self._action_name))
        return True

    async def async_press(self) -> None:
        await async_execute_entry_action(
            self._entry_data, self._capability_name, self._action_name
        )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up vehicle button entities for a config entry."""

    entry_data = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for vehicle_data in entry_data[DATA_VEHICLES]:
        normalized = vehicle_data[DATA_NORMALIZED]
        adapter = vehicle_data.get(DATA_ADAPTER)
        mapping = getattr(adapter, "_mapping", None)
        for capability_name, rule in button_rules():
            if mapping is not None:
                capability = mapping.capability(capability_name)
                if capability is None or rule.action not in capability.actions:
                    continue
            entity = VehicleActionButtonEntity(
                normalized,
                vehicle_data,
                capability_name=capability_name,
                action_name=rule.action,
                key=rule.key,
                name=_title(rule.key),
                icon=rule.icon,
            )
            vehicle_data[DATA_ENTITIES].append(entity)
            entities.append(entity)

    if entities:
        async_add_entities(entities)


def _title(value: str) -> str:
    return value.replace("_", " ").title()
