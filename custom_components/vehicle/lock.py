"""Lock platform for vehicle lock capability."""

from __future__ import annotations

from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_ADAPTER, DATA_ENTITIES, DATA_NORMALIZED, DOMAIN
from .entity import VehicleBaseEntity


class VehicleLockCapabilityEntity(VehicleBaseEntity, LockEntity):
    """Lock entity for the normalized vehicle lock capability."""

    def __init__(self, normalized_data, adapter) -> None:
        super().__init__(normalized_data, "lock", "Lock")
        self._adapter = adapter

    @property
    def is_locked(self) -> bool | None:
        return self._normalized_data.locked

    async def async_lock(self, **kwargs) -> None:
        _ = kwargs
        await self._adapter.execute_action("lock")

    async def async_unlock(self, **kwargs) -> None:
        _ = kwargs
        await self._adapter.execute_action("unlock")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up vehicle lock entities for a config entry."""

    entry_data = hass.data[DOMAIN][entry.entry_id]
    normalized = entry_data[DATA_NORMALIZED]
    if not normalized.capabilities.lock.state_supported:
        return

    entity = VehicleLockCapabilityEntity(normalized, entry_data[DATA_ADAPTER])
    entry_data[DATA_ENTITIES].append(entity)
    async_add_entities([entity])
