"""Service registration and dispatch for My Vehicles actions."""

from __future__ import annotations

from collections.abc import Iterable
import logging

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import config_validation as cv

from .runtime.base import UnsupportedVehicleActionError
from .domain.capability_registry import button_rule_map
from .const import (
    DATA_ADAPTER,
    DATA_ENTITIES,
    DATA_NORMALIZED,
    DATA_SERVICES_REGISTERED,
    DATA_VEHICLES,
    DOMAIN,
    SERVICE_DIAGNOSTICS,
)
from .domain.normalization import normalize_vehicle_data

LOGGER = logging.getLogger(__name__)

SERVICE_CAPABILITY_ACTIONS: dict[str, tuple[str, ...]] = {}
for _service_name, (_capability_name, _button_rule) in button_rule_map().items():
    SERVICE_CAPABILITY_ACTIONS.setdefault(_capability_name, ())
    SERVICE_CAPABILITY_ACTIONS[_capability_name] = (
        *SERVICE_CAPABILITY_ACTIONS[_capability_name],
        _button_rule.action,
    )

SERVICE_SCHEMAS: dict[str, vol.Schema] = {
    capability_name: vol.Schema(
        {
            vol.Required("device_id"): vol.Any(cv.string, [cv.string]),
            vol.Required("action"): vol.In(action_names),
        }
    )
    for capability_name, action_names in SERVICE_CAPABILITY_ACTIONS.items()
    if capability_name != "refresh"
}
SERVICE_SCHEMAS["refresh"] = vol.Schema(
    {
        vol.Required("device_id"): vol.Any(cv.string, [cv.string]),
    }
)


async def async_register_services(hass: HomeAssistant) -> None:
    """Register domain services once per Home Assistant instance."""

    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get(DATA_SERVICES_REGISTERED):
        return

    for service_name, schema in SERVICE_SCHEMAS.items():
        hass.services.async_register(
            DOMAIN,
            service_name,
            _build_service_handler(hass, service_name),
            schema=schema,
        )
    hass.services.async_register(
        DOMAIN,
        SERVICE_DIAGNOSTICS,
        _build_diagnostics_handler(hass),
        schema=SERVICE_SCHEMAS["refresh"],
    )

    domain_data[DATA_SERVICES_REGISTERED] = True


async def async_unregister_services(hass: HomeAssistant) -> None:
    """Unregister domain services when no entries remain."""

    domain_data = hass.data.get(DOMAIN)
    if not domain_data or not domain_data.get(DATA_SERVICES_REGISTERED):
        return

    for service_name in SERVICE_SCHEMAS:
        hass.services.async_remove(DOMAIN, service_name)
    hass.services.async_remove(DOMAIN, SERVICE_DIAGNOSTICS)

    domain_data.pop(DATA_SERVICES_REGISTERED, None)


async def async_execute_entry_action(
    entry_data: dict[str, object], capability_name: str, action_name: str
) -> None:
    """Execute an action, then rebuild and fan out normalized state."""

    normalized = entry_data[DATA_NORMALIZED]
    support = getattr(normalized.capabilities, capability_name)
    if not support.action_supported:
        raise ServiceValidationError(
            f"Capability '{capability_name}' does not support action '{action_name}'"
        )

    adapter = entry_data[DATA_ADAPTER]
    entities = entry_data.get(DATA_ENTITIES, [])
    availability_check = getattr(adapter, "is_action_available", None)
    if callable(availability_check) and not availability_check(
        capability_name, action_name
    ):
        raise ServiceValidationError(
            f"Action '{action_name}' for capability '{capability_name}' is currently unavailable"
        )

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

    for entity in entities:
        entity.update_normalized_data(updated)
        entity.async_write_ha_state()


def _build_service_handler(hass: HomeAssistant, service_name: str):
    async def _handle_service(call: ServiceCall) -> None:
        target_device_ids = _coerce_device_ids(call.data["device_id"])
        target_entries = _find_target_entries(hass, target_device_ids)

        if not target_entries:
            raise ServiceValidationError(
                f"No vehicle device found for device_id: {', '.join(target_device_ids)}"
            )

        capability_name = service_name
        action_name = (
            "refresh" if capability_name == "refresh" else call.data["action"]
        )

        for entry_data in target_entries:
            await async_execute_entry_action(entry_data, capability_name, action_name)

    return _handle_service


def _build_diagnostics_handler(hass: HomeAssistant):
    async def _handle_diagnostics(call: ServiceCall) -> None:
        target_device_ids = _coerce_device_ids(call.data["device_id"])
        target_entries = _find_target_entries(hass, target_device_ids)

        if not target_entries:
            raise ServiceValidationError(
                f"No vehicle device found for device_id: {', '.join(target_device_ids)}"
            )

        for entry_data in target_entries:
            diagnostics = await _collect_entry_diagnostics(entry_data)
            LOGGER.info("My Vehicles diagnostics: %s", diagnostics)

    return _handle_diagnostics


def _coerce_device_ids(device_id: str | list[str]) -> list[str]:
    if isinstance(device_id, str):
        return [device_id]
    return list(device_id)


def _find_target_entries(
    hass: HomeAssistant, device_ids: Iterable[str]
) -> list[dict[str, object]]:
    domain_data = hass.data.get(DOMAIN, {})
    target_ids = set(device_ids)
    matched_entries: list[dict[str, object]] = []
    device_registry = dr.async_get(hass)

    for value in domain_data.values():
        if not isinstance(value, dict):
            continue
        vehicle_entries = value.get(DATA_VEHICLES, [])
        if not isinstance(vehicle_entries, list):
            continue
        for vehicle_entry in vehicle_entries:
            if not isinstance(vehicle_entry, dict):
                continue
            normalized = vehicle_entry.get(DATA_NORMALIZED)
            if normalized is None:
                continue

            device = device_registry.async_get_device(
                identifiers={(DOMAIN, normalized.info.vehicle_id)},
                connections=set(),
            )
            if device is not None and device.id in target_ids:
                matched_entries.append(vehicle_entry)

    return matched_entries


async def _collect_entry_diagnostics(
    entry_data: dict[str, object]
) -> dict[str, object]:
    adapter = entry_data[DATA_ADAPTER]
    normalized = entry_data[DATA_NORMALIZED]

    diagnostics_method = getattr(adapter, "get_diagnostics", None)
    adapter_diagnostics: dict[str, object]
    if callable(diagnostics_method):
        adapter_result = await diagnostics_method()
        adapter_diagnostics = (
            adapter_result if isinstance(adapter_result, dict) else {"adapter": adapter_result}
        )
    else:
        raw_state = await adapter.get_raw_state()
        raw_metrics = await adapter.get_raw_metrics()
        capabilities = await adapter.get_capabilities()
        adapter_diagnostics = {
            "raw_state": dict(raw_state),
            "raw_metrics": dict(raw_metrics),
            "capabilities": _serialize_capabilities(capabilities),
        }

    return {
        "vehicle_id": normalized.info.vehicle_id,
        "vehicle_name": normalized.info.name,
        "state": normalized.state.value,
        "normalized": {
            "fuel_level": normalized.fuel_level,
            "fuel_driving_range": normalized.fuel_driving_range,
            "ev_battery_level": normalized.ev_battery_level,
            "ev_driving_range": normalized.ev_driving_range,
            "ev_plugged_in": normalized.ev_plugged_in,
            "ev_charging": normalized.ev_charging,
            "driving_range": normalized.driving_range,
            "locked": normalized.locked,
            "windows_open": normalized.windows_open,
            "climate_active": normalized.climate_active,
            "latitude": normalized.latitude,
            "longitude": normalized.longitude,
            "odometer": normalized.odometer,
            "capabilities": _serialize_capabilities(normalized.capabilities),
        },
        "adapter": adapter_diagnostics,
    }


def _serialize_capabilities(capabilities) -> dict[str, dict[str, bool]]:
    return {
        capability_name: {
            "state_supported": support.state_supported,
            "action_supported": support.action_supported,
        }
        for capability_name, support in capabilities.items()
    }
