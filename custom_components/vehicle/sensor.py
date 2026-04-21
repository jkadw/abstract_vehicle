"""Sensor platform for vehicle state and numeric capabilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfLength,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_ENTITIES, DATA_NORMALIZED, DOMAIN
from .entity import VehicleBaseEntity, VehicleEntity
from .model import NormalizedVehicleData


@dataclass(frozen=True, slots=True)
class SensorSpec:
    key: str
    name: str
    field: str
    unit: str | None = None
    icon: str | None = None
    device_class: SensorDeviceClass | None = None


SENSOR_SPECS: tuple[SensorSpec, ...] = (
    SensorSpec(
        "battery_level",
        "Battery",
        "battery_level",
        PERCENTAGE,
        "mdi:battery",
        SensorDeviceClass.BATTERY,
    ),
    SensorSpec("fuel_level", "Fuel", "fuel_level", PERCENTAGE, "mdi:gas-station"),
    SensorSpec("range", "Range", "range", None, "mdi:map-marker-distance"),
    SensorSpec("odometer", "Odometer", "odometer", None, "mdi:counter"),
)


class VehicleValueSensorEntity(VehicleBaseEntity, SensorEntity):
    """Sensor for a numeric normalized vehicle field."""

    def __init__(self, normalized_data: NormalizedVehicleData, spec: SensorSpec) -> None:
        super().__init__(normalized_data, spec.key, spec.name)
        self._spec = spec

    @property
    def native_value(self) -> Any:
        return getattr(self._normalized_data, self._spec.field)

    @property
    def native_unit_of_measurement(self) -> str | None:
        if self._spec.key in {"range", "odometer"}:
            distance_unit = self._normalized_data.display_units.distance_unit
            if distance_unit == "mi":
                return UnitOfLength.MILES
            return UnitOfLength.KILOMETERS
        return self._spec.unit

    @property
    def device_class(self) -> SensorDeviceClass | None:
        return self._spec.device_class

    @property
    def icon(self) -> str | None:
        return self._spec.icon


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up vehicle sensor entities for a config entry."""

    entry_data = hass.data[DOMAIN][entry.entry_id]
    normalized = entry_data[DATA_NORMALIZED]
    entities: list[SensorEntity] = [VehicleEntity(normalized)]

    if normalized.capabilities.battery.state_supported:
        entities.append(VehicleValueSensorEntity(normalized, SENSOR_SPECS[0]))
    if normalized.capabilities.fuel.state_supported:
        entities.append(VehicleValueSensorEntity(normalized, SENSOR_SPECS[1]))
    if normalized.range is not None:
        entities.append(VehicleValueSensorEntity(normalized, SENSOR_SPECS[2]))
    if normalized.capabilities.odometer.state_supported:
        entities.append(VehicleValueSensorEntity(normalized, SENSOR_SPECS[3]))

    entry_data[DATA_ENTITIES].extend(entities)
    async_add_entities(entities)
