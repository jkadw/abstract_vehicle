"""Device tracker platform for vehicle location capability."""

from __future__ import annotations

from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_ENTITIES, DATA_NORMALIZED, DATA_VEHICLES, DOMAIN
from .entity import VehicleBaseEntity


class VehicleLocationTrackerEntity(VehicleBaseEntity, TrackerEntity):
    """Device tracker for normalized vehicle location."""

    def __init__(self, normalized_data) -> None:
        super().__init__(normalized_data, "location", "Location")

    @property
    def latitude(self) -> float | None:
        return self._normalized_data.latitude

    @property
    def longitude(self) -> float | None:
        return self._normalized_data.longitude

    @property
    def icon(self) -> str:
        return "mdi:map-marker"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up vehicle location entities for a config entry."""

    entry_data = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for vehicle_data in entry_data[DATA_VEHICLES]:
        normalized = vehicle_data[DATA_NORMALIZED]
        if not normalized.capabilities.location.state_supported:
            continue

        entity = VehicleLocationTrackerEntity(normalized)
        vehicle_data[DATA_ENTITIES].append(entity)
        entities.append(entity)

    if entities:
        async_add_entities(entities)
