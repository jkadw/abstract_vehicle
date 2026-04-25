"""Dynamic adapter loading and availability checks."""

from __future__ import annotations

import importlib
from typing import Any

from homeassistant.core import HomeAssistant

from .base import DiscoveredVehicle, VehicleAdapter
from .mapped import MappedVehicleAdapter
from .registry import ADAPTER_DEFINITIONS, AdapterDefinition, get_adapter_definition
from ..const import CONF_VEHICLE_ID, CONF_VEHICLES


def _load_adapter_class(definition: AdapterDefinition) -> type[VehicleAdapter]:
    """Import and return the adapter class for a registry definition."""

    module = importlib.import_module(definition.module_path)
    adapter_class = getattr(module, definition.class_name)
    if definition.mapping_name and issubclass(adapter_class, MappedVehicleAdapter):
        return _build_mapped_adapter_class(definition, adapter_class)
    return adapter_class


def _build_mapped_adapter_class(
    definition: AdapterDefinition,
    adapter_class: type[MappedVehicleAdapter],
) -> type[MappedVehicleAdapter]:
    """Create a concrete mapped-adapter class from registry metadata."""

    class_name = f"{definition.key.title().replace('_', '')}MappedVehicleAdapter"
    return type(
        class_name,
        (adapter_class,),
        {
            "mapping_name": definition.mapping_name,
            "friendly_name": definition.fallback_label,
        },
    )


async def load_adapter_class(
    hass: HomeAssistant, definition: AdapterDefinition
) -> type[VehicleAdapter]:
    """Import and return the adapter class without blocking the event loop."""

    return await hass.async_add_executor_job(_load_adapter_class, definition)


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
            adapter_class = await load_adapter_class(hass, definition)
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

    adapter_class = await load_adapter_class(hass, definition)
    return await adapter_class.async_discover_vehicles(hass)


async def create_adapter_from_entry(
    hass: HomeAssistant,
    adapter_key: str,
    entry_data: dict[str, Any],
) -> VehicleAdapter:
    """Instantiate the selected adapter from config-entry data."""

    definition = get_adapter_definition(adapter_key)
    if definition is None:
        raise ValueError(f"Unsupported adapter type: {adapter_key}")

    adapter_class = await load_adapter_class(hass, definition)

    if adapter_key == "mock":
        return adapter_class()

    if definition.mapping_name is not None:
        vehicles = entry_data.get(CONF_VEHICLES)
        if not isinstance(vehicles, list):
            raise ValueError(
                f"{adapter_key} adapter requires configured vehicles"
            )
        vehicle_id = entry_data.get(CONF_VEHICLE_ID)
        if vehicle_id is not None and not isinstance(vehicle_id, str):
            raise ValueError(
                f"{adapter_key} vehicle_id must be a string when configured"
            )
        return adapter_class(hass=hass, vehicles=vehicles, vehicle_id=vehicle_id)

    raise ValueError(f"Unsupported adapter type: {adapter_key}")


async def create_adapter_from_discovered_vehicle(
    hass: HomeAssistant,
    adapter_key: str,
    discovered_vehicle: DiscoveredVehicle,
) -> VehicleAdapter:
    """Instantiate one adapter from one discovered vehicle payload."""

    return await create_adapter_from_entry(
        hass,
        adapter_key,
        {
            CONF_VEHICLE_ID: discovered_vehicle.vehicle_id,
            CONF_VEHICLES: [discovered_vehicle.payload],
        },
    )
