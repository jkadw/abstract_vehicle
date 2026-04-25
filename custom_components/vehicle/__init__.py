"""Vehicle integration package."""

from __future__ import annotations

from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant

from .adapters import create_adapter_from_discovered_vehicle, discover_adapter_vehicles
from .const import (
    ADAPTER_TYPE_MOCK,
    CONF_ADAPTER,
    DATA_ADAPTER,
    DATA_ENTITIES,
    DATA_NORMALIZED,
    DATA_SERVICES_REGISTERED,
    DATA_VEHICLES,
    DOMAIN,
    PLATFORMS,
)
from .normalization import normalize_vehicle_data
from .services import async_register_services, async_unregister_services


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the vehicle integration."""

    hass.data.setdefault(DOMAIN, {})
    await async_register_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a vehicle config entry."""

    hass.data.setdefault(DOMAIN, {})

    adapter_type = entry.data.get(CONF_ADAPTER, ADAPTER_TYPE_MOCK)
    if not hass.is_running and adapter_type != ADAPTER_TYPE_MOCK:
        async def _async_reload_on_started(event: Event) -> None:
            _ = event
            await hass.config_entries.async_reload(entry.entry_id)

        entry.async_on_unload(
            hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_STARTED,
                _async_reload_on_started,
            )
        )

    discovered_vehicles = await _discover_entry_vehicles(hass, entry)
    vehicle_entries = []
    for discovered_vehicle in discovered_vehicles:
        vehicle_adapter = await create_adapter_from_discovered_vehicle(
            hass,
            adapter_type,
            discovered_vehicle,
        )
        raw_state = await vehicle_adapter.get_raw_state()
        raw_metrics = await vehicle_adapter.get_raw_metrics()
        capabilities = await vehicle_adapter.get_capabilities()
        normalized_data = normalize_vehicle_data(raw_state, raw_metrics, capabilities)
        vehicle_entries.append(
            {
                DATA_ADAPTER: vehicle_adapter,
                DATA_ENTITIES: [],
                DATA_NORMALIZED: normalized_data,
            }
        )

    hass.data[DOMAIN][entry.entry_id] = {
        DATA_ADAPTER: adapter_type,
        DATA_VEHICLES: vehicle_entries,
    }

    await async_register_services(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a vehicle config entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if all(not isinstance(value, dict) for value in hass.data[DOMAIN].values()):
            await async_unregister_services(hass)
    return unload_ok


async def _discover_entry_vehicles(
    hass: HomeAssistant, entry: ConfigEntry
) -> list:
    """Discover all source vehicles for the selected adapter entry."""

    adapter_type = entry.data.get(CONF_ADAPTER, "mock")
    if not isinstance(adapter_type, str):
        raise ValueError("Configured adapter type must be a string")
    return await discover_adapter_vehicles(hass, adapter_type)


__all__ = ["DOMAIN"]
