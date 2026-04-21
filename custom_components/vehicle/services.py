"""Service registration and dispatch for vehicle actions."""

from __future__ import annotations

from collections.abc import Iterable

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .adapters import UnsupportedVehicleActionError
from .const import (
    DATA_ADAPTER,
    DATA_ENTITY,
    DATA_NORMALIZED,
    DATA_SERVICES_REGISTERED,
    DOMAIN,
    SERVICE_LOCK,
    SERVICE_START_CLIMATE,
    SERVICE_STOP_CLIMATE,
    SERVICE_UNLOCK,
)
from .normalization import normalize_vehicle_data


SERVICE_ACTIONS: dict[str, tuple[str, str]] = {
    SERVICE_LOCK: ("lock", "lock"),
    SERVICE_UNLOCK: ("lock", "unlock"),
    SERVICE_START_CLIMATE: ("climate", "start_climate"),
    SERVICE_STOP_CLIMATE: ("climate", "stop_climate"),
}

SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): vol.Any(cv.entity_id, [cv.entity_id]),
    }
)


async def async_register_services(hass: HomeAssistant) -> None:
    """Register domain services once per Home Assistant instance."""

    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get(DATA_SERVICES_REGISTERED):
        return

    for service_name in SERVICE_ACTIONS:
        hass.services.async_register(
            DOMAIN,
            service_name,
            _build_service_handler(hass, service_name),
            schema=SERVICE_SCHEMA,
        )

    domain_data[DATA_SERVICES_REGISTERED] = True


async def async_unregister_services(hass: HomeAssistant) -> None:
    """Unregister domain services when no entries remain."""

    domain_data = hass.data.get(DOMAIN)
    if not domain_data or not domain_data.get(DATA_SERVICES_REGISTERED):
        return

    for service_name in SERVICE_ACTIONS:
        hass.services.async_remove(DOMAIN, service_name)

    domain_data.pop(DATA_SERVICES_REGISTERED, None)


def _build_service_handler(hass: HomeAssistant, service_name: str):
    async def _handle_service(call: ServiceCall) -> None:
        target_entity_ids = _coerce_entity_ids(call.data["entity_id"])
        target_entries = _find_target_entries(hass, target_entity_ids)

        if not target_entries:
            raise ServiceValidationError(
                f"No vehicle entity found for entity_id: {', '.join(target_entity_ids)}"
            )

        capability_name, action_name = SERVICE_ACTIONS[service_name]

        for entry_data in target_entries:
            normalized = entry_data[DATA_NORMALIZED]
            support = getattr(normalized.capabilities, capability_name)
            if not support.action_supported:
                raise ServiceValidationError(
                    f"Capability '{capability_name}' does not support action '{action_name}'"
                )

            adapter = entry_data[DATA_ADAPTER]
            entity = entry_data.get(DATA_ENTITY)

            try:
                await adapter.execute_action(action_name)
            except UnsupportedVehicleActionError as err:
                raise ServiceValidationError(str(err)) from err
            except Exception as err:
                raise HomeAssistantError(
                    f"Failed to execute vehicle action '{action_name}'"
                ) from err

            raw_state = await adapter.get_raw_state()
            raw_metrics = await adapter.get_raw_metrics()
            capabilities = await adapter.get_capabilities()
            updated = normalize_vehicle_data(raw_state, raw_metrics, capabilities)
            entry_data[DATA_NORMALIZED] = updated

            if entity is not None:
                entity.update_normalized_data(updated)
                entity.async_write_ha_state()

    return _handle_service


def _coerce_entity_ids(entity_id: str | list[str]) -> list[str]:
    if isinstance(entity_id, str):
        return [entity_id]
    return list(entity_id)


def _find_target_entries(
    hass: HomeAssistant, entity_ids: Iterable[str]
) -> list[dict[str, object]]:
    domain_data = hass.data.get(DOMAIN, {})
    target_ids = set(entity_ids)
    matched_entries: list[dict[str, object]] = []

    for value in domain_data.values():
        if not isinstance(value, dict):
            continue
        entity = value.get(DATA_ENTITY)
        if entity is None:
            continue
        if getattr(entity, "entity_id", None) in target_ids:
            matched_entries.append(value)

    return matched_entries
