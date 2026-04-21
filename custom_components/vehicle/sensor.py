"""Sensor platform for vehicle state and numeric capabilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfLength,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_ENTITIES, DATA_NORMALIZED, DOMAIN
from .entity import VehicleBaseEntity
from .model import NormalizedVehicleData


@dataclass(frozen=True, slots=True)
class SensorSpec:
    key: str
    name: str
    field: str
    unit: str | None = None


SENSOR_SPECS: tuple[SensorSpec, ...] = (
    SensorSpec("state", "State", "state"),
    SensorSpec("battery_level", "Battery", "battery_level", PERCENTAGE),
    SensorSpec("fuel_level", "Fuel", "fuel_level", PERCENTAGE),
    SensorSpec("range", "Range", "range", None),
    SensorSpec("odometer", "Odometer", "odometer", None),
)


class VehicleStateSensorEntity(VehicleBaseEntity, SensorEntity):
    """Sensor for the normalized aggregate vehicle state."""

    def __init__(self, normalized_data: NormalizedVehicleData) -> None:
        super().__init__(normalized_data, "state", "State")

    @property
    def native_value(self) -> str:
        return self._normalized_data.state.value


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
            distance_unit = self._normalized_data.source_units.distance_unit
            if distance_unit == "mi":
                return UnitOfLength.MILES
            return UnitOfLength.KILOMETERS
        return self._spec.unit


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up vehicle sensor entities for a config entry."""

    entry_data = hass.data[DOMAIN][entry.entry_id]
    normalized = entry_data[DATA_NORMALIZED]
    entities: list[SensorEntity] = [VehicleStateSensorEntity(normalized)]

    if normalized.capabilities.battery.state_supported:
        entities.append(VehicleValueSensorEntity(normalized, SENSOR_SPECS[1]))
    if normalized.capabilities.fuel.state_supported:
        entities.append(VehicleValueSensorEntity(normalized, SENSOR_SPECS[2]))
    if normalized.range is not None:
        entities.append(VehicleValueSensorEntity(normalized, SENSOR_SPECS[3]))
    if normalized.capabilities.odometer.state_supported:
        entities.append(VehicleValueSensorEntity(normalized, SENSOR_SPECS[4]))

    entry_data[DATA_ENTITIES].extend(entities)
    async_add_entities(entities)
