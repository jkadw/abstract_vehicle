"""Button platform for vehicle actions that do not have state."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_ENTITIES, DATA_NORMALIZED, DOMAIN
from .entity import VehicleBaseEntity
from .services import async_execute_entry_action


class VehicleRefreshButtonEntity(VehicleBaseEntity, ButtonEntity):
    """Button entity for the normalized vehicle refresh action."""

    def __init__(self, normalized_data, entry_data) -> None:
        super().__init__(normalized_data, "refresh", "Refresh")
        self._entry_data = entry_data

    @property
    def icon(self) -> str:
        return "mdi:refresh"

    async def async_press(self) -> None:
        await async_execute_entry_action(self._entry_data, "refresh", "refresh")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up vehicle button entities for a config entry."""

    entry_data = hass.data[DOMAIN][entry.entry_id]
    normalized = entry_data[DATA_NORMALIZED]
    if not normalized.capabilities.refresh.action_supported:
        return

    entity = VehicleRefreshButtonEntity(normalized, entry_data)
    entry_data[DATA_ENTITIES].append(entity)
    async_add_entities([entity])
