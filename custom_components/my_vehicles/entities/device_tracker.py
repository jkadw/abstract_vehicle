"""Device tracker platform for vehicle location capability."""

from __future__ import annotations

from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..domain.capability_registry import (
    state_entity_rules_for_domain,
    should_create_entity_rule,
)
from .const import DATA_ENTITIES, DATA_NORMALIZED, DATA_VEHICLES, DOMAIN
from .base import VehicleBaseEntity, capability_source_domains


class VehicleLocationTrackerEntity(VehicleBaseEntity, TrackerEntity):
    """Device tracker for normalized vehicle location."""

    def __init__(self, normalized_data, key: str, name: str, icon: str | None = None) -> None:
        super().__init__(normalized_data, key, name)
        self._icon = icon

    @property
    def latitude(self) -> float | None:
        return self._normalized_data.latitude

    @property
    def longitude(self) -> float | None:
        return self._normalized_data.longitude

    @property
    def source_type(self) -> str:
        return "gps"

    @property
    def icon(self) -> str:
        return self._icon or "mdi:map-marker"


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
        for capability_name, rule in state_entity_rules_for_domain("device_tracker"):
            support = normalized.capabilities.get(capability_name)
            if not should_create_entity_rule(
                rule,
                state_supported=support.state_supported,
                action_supported=support.action_supported,
                source_domains=capability_source_domains(vehicle_data, capability_name),
            ):
                continue
            entity = VehicleLocationTrackerEntity(
                normalized,
                rule.key,
                _title(rule.key),
                icon=rule.icon,
            )
            vehicle_data[DATA_ENTITIES].append(entity)
            entities.append(entity)

    if entities:
        async_add_entities(entities)


def _title(value: str) -> str:
    return value.replace("_", " ").title()
