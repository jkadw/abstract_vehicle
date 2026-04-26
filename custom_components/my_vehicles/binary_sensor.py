"""Binary sensor platform for registry-driven boolean capability entities."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .capability_registry import (
    state_entity_rules_for_domain,
    should_create_entity_rule,
)
from .const import DATA_ENTITIES, DATA_NORMALIZED, DATA_VEHICLES, DOMAIN
from .entity import VehicleBaseEntity, capability_source_domains
from .model import NormalizedVehicleData


class VehicleBinaryStateEntity(VehicleBaseEntity, BinarySensorEntity):
    """Binary sensor for one canonical capability."""

    def __init__(
        self,
        normalized_data: NormalizedVehicleData,
        capability_name: str,
        entity_key: str,
        entity_name: str,
        *,
        icon: str | None = None,
        device_class: str | None = None,
    ) -> None:
        super().__init__(normalized_data, entity_key, entity_name)
        self._capability_name = capability_name
        self._icon = icon
        self._device_class = device_class

    @property
    def is_on(self) -> bool | None:
        if self._capability_name == "lock_vehicle":
            return self._normalized_data.locked
        if self._capability_name == "windows":
            return self._normalized_data.windows_open
        if self._capability_name == "climate":
            return self._normalized_data.climate_active
        if self._capability_name == "charging":
            return self._normalized_data.charging_active
        if self._capability_name == "ignition":
            return self._normalized_data.ignition_on
        if self._capability_name == "range_warning":
            return self._normalized_data.range_warning
        value = self._capability_value(self._capability_name)
        return value if isinstance(value, bool) else None

    @property
    def device_class(self) -> str | None:
        return self._device_class

    @property
    def icon(self) -> str | None:
        return self._icon


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up vehicle binary sensor entities for a config entry."""

    entry_data = hass.data[DOMAIN][entry.entry_id]
    entities: list[BinarySensorEntity] = []

    for vehicle_data in entry_data[DATA_VEHICLES]:
        normalized = vehicle_data[DATA_NORMALIZED]
        vehicle_entities: list[BinarySensorEntity] = []
        for capability_name, rule in state_entity_rules_for_domain("binary_sensor"):
            support = normalized.capabilities.get(capability_name)
            if not should_create_entity_rule(
                rule,
                state_supported=support.state_supported,
                action_supported=support.action_supported,
                source_domains=capability_source_domains(vehicle_data, capability_name),
            ):
                continue
            vehicle_entities.append(
                VehicleBinaryStateEntity(
                    normalized,
                    capability_name,
                    rule.key,
                    _title(rule.key),
                    icon=rule.icon,
                    device_class=rule.device_class,
                )
            )

        vehicle_data[DATA_ENTITIES].extend(vehicle_entities)
        entities.extend(vehicle_entities)

    async_add_entities(entities)


def _title(value: str) -> str:
    return value.replace("_", " ").title()
