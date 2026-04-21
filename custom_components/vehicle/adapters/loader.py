"""Dynamic adapter loading and availability checks."""

from __future__ import annotations

import importlib
from typing import Any

from homeassistant.core import HomeAssistant

from .base import DiscoveredVehicle, VehicleAdapter
from .registry import ADAPTER_DEFINITIONS, AdapterDefinition, get_adapter_definition
from ..const import CONF_VEHICLE_ID, CONF_VEHICLES


def load_adapter_class(definition: AdapterDefinition) -> type[VehicleAdapter]:
    """Import and return the adapter class for a registry definition."""

    module = importlib.import_module(definition.module_path)
    adapter_class = getattr(module, definition.class_name)
    return adapter_class


async def is_adapter_available(
    hass: HomeAssistant, definition: AdapterDefinition
) -> bool:
    """Return whether the adapter should be offered in this HA instance."""

    if definition.always_available:
        return True

    if definition.source_integration is None:
        return True

    if definition.source_integration in hass.config.components:
        return True

    return bool(hass.config_entries.async_entries(definition.source_integration))


async def get_available_adapter_definitions(
    hass: HomeAssistant,
) -> list[AdapterDefinition]:
    """Return registry entries that are usable in the current HA instance."""

    available: list[AdapterDefinition] = []
    for definition in ADAPTER_DEFINITIONS:
        if await is_adapter_available(hass, definition):
            available.append(definition)
    return available


async def get_available_adapter_options(
    hass: HomeAssistant,
) -> dict[str, tuple[str, type[VehicleAdapter]]]:
    """Return config-flow adapter choices keyed by adapter id."""

    options: dict[str, tuple[str, type[VehicleAdapter]]] = {}
    for definition in await get_available_adapter_definitions(hass):
        try:
            adapter_class = load_adapter_class(definition)
        except Exception:
            continue
        options[definition.key] = (
            adapter_class.get_friendly_name() or definition.fallback_label,
            adapter_class,
        )
    return options


async def discover_adapter_vehicles(
    hass: HomeAssistant, adapter_key: str
) -> list[DiscoveredVehicle]:
    """Return vehicles discoverable by the selected adapter."""

    definition = get_adapter_definition(adapter_key)
    if definition is None:
        raise ValueError(f"Unsupported adapter type: {adapter_key}")

    if not await is_adapter_available(hass, definition):
        raise ValueError(f"Adapter not available: {adapter_key}")

    adapter_class = load_adapter_class(definition)
    return await adapter_class.async_discover_vehicles(hass)


def create_adapter_from_entry(
    hass: HomeAssistant,
    adapter_key: str,
    entry_data: dict[str, Any],
) -> VehicleAdapter:
    """Instantiate the selected adapter from config-entry data."""

    definition = get_adapter_definition(adapter_key)
    if definition is None:
        raise ValueError(f"Unsupported adapter type: {adapter_key}")

    adapter_class = load_adapter_class(definition)

    if adapter_key == "mock":
        return adapter_class()

    if adapter_key == "kia_uvo":
        vehicles = entry_data.get(CONF_VEHICLES)
        if not isinstance(vehicles, list):
            raise ValueError("kia_uvo adapter requires configured vehicles")
        vehicle_id = entry_data.get(CONF_VEHICLE_ID)
        if vehicle_id is not None and not isinstance(vehicle_id, str):
            raise ValueError("kia_uvo vehicle_id must be a string when configured")
        return adapter_class(hass=hass, vehicles=vehicles, vehicle_id=vehicle_id)

    raise ValueError(f"Unsupported adapter type: {adapter_key}")
