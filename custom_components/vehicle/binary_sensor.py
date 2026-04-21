"""Binary sensor platform for vehicle boolean state capabilities."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_ENTITIES, DATA_NORMALIZED, DOMAIN
from .entity import VehicleBaseEntity
from .model import NormalizedVehicleData


@dataclass(frozen=True, slots=True)
class BinarySpec:
    key: str
    name: str
    field: str


BINARY_SPECS: tuple[BinarySpec, ...] = (
    BinarySpec("windows", "Windows", "windows_open"),
    BinarySpec("climate", "Climate", "climate_active"),
    BinarySpec("charging", "Charging", "charging_active"),
)


class VehicleBinaryStateEntity(VehicleBaseEntity, BinarySensorEntity):
    """Binary sensor for a boolean normalized vehicle field."""

    def __init__(self, normalized_data: NormalizedVehicleData, spec: BinarySpec) -> None:
        super().__init__(normalized_data, spec.key, spec.name)
        self._spec = spec

    @property
    def is_on(self) -> bool | None:
        return getattr(self._normalized_data, self._spec.field)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up vehicle binary sensor entities for a config entry."""

    entry_data = hass.data[DOMAIN][entry.entry_id]
    normalized = entry_data[DATA_NORMALIZED]
    entities: list[BinarySensorEntity] = []

    if normalized.capabilities.windows.state_supported:
        entities.append(VehicleBinaryStateEntity(normalized, BINARY_SPECS[0]))
    if normalized.capabilities.climate.state_supported:
        entities.append(VehicleBinaryStateEntity(normalized, BINARY_SPECS[1]))
    if normalized.capabilities.charging.state_supported:
        entities.append(VehicleBinaryStateEntity(normalized, BINARY_SPECS[2]))

    entry_data[DATA_ENTITIES].extend(entities)
    async_add_entities(entities)
