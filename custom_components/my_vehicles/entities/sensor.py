"""Sensor platform for aggregate and sensor-domain capability entities."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfLength,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..domain.capability_registry import (
    state_entity_rules_for_domain,
    should_create_entity_rule,
)
from ..const import DATA_ENTITIES, DATA_NORMALIZED, DATA_VEHICLES, DOMAIN
from .base import VehicleBaseEntity, VehicleEntity, capability_source_domains
from ..domain.model import NormalizedVehicleData


class VehicleCapabilitySensorEntity(VehicleBaseEntity, SensorEntity):
    """Sensor entity driven by the capability registry."""

    def __init__(
        self,
        normalized_data: NormalizedVehicleData,
        capability_name: str,
        entity_key: str,
        entity_name: str,
        *,
        device_class: str | None = None,
        state_class: str | None = None,
        icon: str | None = None,
    ) -> None:
        super().__init__(normalized_data, entity_key, entity_name)
        self._capability_name = capability_name
        self._device_class = device_class
        self._state_class = state_class
        self._icon = icon

    @property
    def native_value(self) -> Any:
        if self._capability_name == "battery_level":
            return self._normalized_data.battery_level
        if self._capability_name == "driving_range":
            return self._normalized_data.driving_range
        if self._capability_name == "odometer":
            return self._normalized_data.odometer
        if self._capability_name == "info_messages":
            return self._normalized_data.info_messages
        if self._capability_name == "tire_pressure":
            return self._capability_value(self._capability_name)
        return self._capability_value(self._capability_name)

    @property
    def native_unit_of_measurement(self) -> str | None:
        if self._capability_name == "battery_level":
            return PERCENTAGE
        if self._capability_name in {"driving_range", "odometer"}:
            distance_unit = self._normalized_data.display_units.distance_unit
            if distance_unit == "mi":
                return UnitOfLength.MILES
            return UnitOfLength.KILOMETERS
        return None

    @property
    def device_class(self) -> str | None:
        return self._device_class

    @property
    def state_class(self) -> str | None:
        return self._state_class

    @property
    def icon(self) -> str | None:
        return self._icon


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up vehicle sensor entities for a config entry."""

    entry_data = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = []

    for vehicle_data in entry_data[DATA_VEHICLES]:
        normalized = vehicle_data[DATA_NORMALIZED]
        vehicle_entities: list[SensorEntity] = [VehicleEntity(normalized)]
        for capability_name, rule in state_entity_rules_for_domain("sensor"):
            support = normalized.capabilities.get(capability_name)
            if not should_create_entity_rule(
                rule,
                state_supported=support.state_supported,
                action_supported=support.action_supported,
                source_domains=capability_source_domains(vehicle_data, capability_name),
            ):
                continue
            vehicle_entities.append(
                VehicleCapabilitySensorEntity(
                    normalized,
                    capability_name,
                    rule.key,
                    _title(rule.key),
                    device_class=rule.device_class,
                    state_class=rule.state_class,
                    icon=rule.icon,
                )
            )

        vehicle_data[DATA_ENTITIES].extend(vehicle_entities)
        entities.extend(vehicle_entities)

    async_add_entities(entities)


def _title(value: str) -> str:
    return value.replace("_", " ").title()
