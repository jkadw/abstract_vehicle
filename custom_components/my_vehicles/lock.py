"""Lock platform for vehicle lock capability."""

from __future__ import annotations

from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_ENTITIES, DATA_NORMALIZED, DATA_VEHICLES, DOMAIN
from .entity import VehicleBaseEntity
from .services import async_execute_entry_action


class VehicleLockCapabilityEntity(VehicleBaseEntity, LockEntity):
    """Lock entity for the normalized vehicle lock capability."""

    def __init__(self, normalized_data, entry_data) -> None:
        super().__init__(normalized_data, "lock_vehicle", "Lock Vehicle")
        self._entry_data = entry_data

    @property
    def is_locked(self) -> bool | None:
        return self._normalized_data.locked

    async def async_lock(self, **kwargs) -> None:
        _ = kwargs
        await async_execute_entry_action(self._entry_data, "lock_vehicle", "lock")

    async def async_unlock(self, **kwargs) -> None:
        _ = kwargs
        await async_execute_entry_action(self._entry_data, "lock_vehicle", "unlock")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up vehicle lock entities for a config entry."""

    entry_data = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for vehicle_data in entry_data[DATA_VEHICLES]:
        normalized = vehicle_data[DATA_NORMALIZED]

        entity = VehicleLockCapabilityEntity(normalized, vehicle_data)
        vehicle_data[DATA_ENTITIES].append(entity)
        entities.append(entity)

    if entities:
        async_add_entities(entities)
