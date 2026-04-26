"""Binary sensor platform for registry-driven boolean capability entities."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..domain.capability_registry import (
    state_entity_rules_for_domain,
    should_create_entity_rule,
)
from ..const import DATA_ADAPTER, DATA_ENTITIES, DATA_NORMALIZED, DATA_VEHICLES, DOMAIN
from .base import VehicleBaseEntity, capability_source_domains
from ..domain.model import NormalizedVehicleData


class VehicleBinaryStateEntity(VehicleBaseEntity, BinarySensorEntity):
    """Binary sensor for one canonical capability."""

    def __init__(
        self,
        normalized_data: NormalizedVehicleData,
        entry_data: dict[str, object],
        capability_name: str,
        entity_key: str,
        entity_name: str,
        *,
        icon: str | None = None,
        device_class: str | None = None,
        invert_state: bool = False,
    ) -> None:
        super().__init__(normalized_data, entity_key, entity_name)
        self._entry_data = entry_data
        self._capability_name = capability_name
        self._icon = icon
        self._device_class = device_class
        self._invert_state = invert_state

    @property
    def is_on(self) -> bool | None:
        if self._capability_name == "lock_vehicle":
            if self._normalized_data.locked is None:
                return None
            return (
                not self._normalized_data.locked
                if self._invert_state
                else self._normalized_data.locked
            )
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

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        adapter = self._entry_data.get(DATA_ADAPTER)
        mapping = getattr(adapter, "_mapping", None)
        if mapping is None:
            return None

        capability = mapping.capability(self._capability_name)
        if capability is None:
            return None

        source_patterns = capability.state.any or capability.state.all
        if not source_patterns:
            return None

        vehicle_token = _callable_value(adapter, "_source_vehicle_token")
        device_id = _callable_value(adapter, "_source_device_id")
        if not vehicle_token or not device_id or self.hass is None:
            return None

        on_entities: list[dict[str, str]] = []
        off_entities: list[dict[str, str]] = []
        for pattern in source_patterns:
            entity_id = (
                pattern.replace("{vehicle}", vehicle_token).replace("{device}", device_id)
            )
            state_obj = self.hass.states.get(entity_id)
            if state_obj is None:
                continue

            state_value = str(getattr(state_obj, "state", "unknown"))
            payload = _short_source_name(entity_id, vehicle_token)
            classified = _classify_state(state_value)
            if classified is True:
                on_entities.append(payload)
            elif classified is False:
                off_entities.append(payload)

        return {
            "state_on": on_entities,
            "state_off": off_entities,
        }


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
            source_domains = capability_source_domains(vehicle_data, capability_name)
            if not should_create_entity_rule(
                rule,
                state_supported=support.state_supported,
                action_supported=support.action_supported,
                source_domains=source_domains,
            ):
                continue
            vehicle_entities.append(
                VehicleBinaryStateEntity(
                    normalized,
                    vehicle_data,
                    capability_name,
                    rule.key,
                    _title(rule.key),
                    icon=rule.icon,
                    device_class=rule.device_class,
                    invert_state=capability_name == "lock_vehicle"
                    and "lock" in source_domains,
                )
            )

        vehicle_data[DATA_ENTITIES].extend(vehicle_entities)
        entities.extend(vehicle_entities)

    async_add_entities(entities)


def _title(value: str) -> str:
    return value.replace("_", " ").title()


def _callable_value(adapter: object, attr_name: str) -> str | None:
    value = getattr(adapter, attr_name, None)
    if value is None:
        return None
    if callable(value):
        try:
            result = value()
        except Exception:
            return None
        return result if isinstance(result, str) and result else None
    return value if isinstance(value, str) and value else None


def _classify_state(value: str) -> bool | None:
    normalized = value.strip().lower()
    if normalized in {"on", "open", "true", "1", "locked", "charging", "home"}:
        return True
    if normalized in {"off", "closed", "false", "0", "unlocked", "not_home"}:
        return False
    return None


def _short_source_name(entity_id: str, vehicle_token: str) -> str:
    object_id = entity_id.split(".", 1)[-1]
    prefix = f"{vehicle_token}_"
    if object_id.startswith(prefix):
        object_id = object_id[len(prefix) :]
    return object_id
