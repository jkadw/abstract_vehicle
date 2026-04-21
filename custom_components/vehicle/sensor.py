"""Sensor platform for the aggregate vehicle entity."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_ENTITY, DATA_NORMALIZED, DOMAIN
from .entity import VehicleEntity


class VehicleSensorEntity(VehicleEntity, SensorEntity):
    """Sensor wrapper for the normalized vehicle entity."""


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the vehicle entity for a config entry."""

    entry_data = hass.data[DOMAIN][entry.entry_id]
    entity = VehicleSensorEntity(entry_data[DATA_NORMALIZED])
    entry_data[DATA_ENTITY] = entity
    async_add_entities([entity])
