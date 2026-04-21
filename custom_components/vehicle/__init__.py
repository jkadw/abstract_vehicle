"""Vehicle integration package."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .adapters import (
    VehicleAdapter,
    create_adapter_from_entry,
)
from .const import (
    CONF_ADAPTER,
    DATA_ADAPTER,
    DATA_ENTITIES,
    DATA_NORMALIZED,
    DATA_SERVICES_REGISTERED,
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

    adapter = _create_adapter(hass, entry)
    raw_state = await adapter.get_raw_state()
    raw_metrics = await adapter.get_raw_metrics()
    capabilities = await adapter.get_capabilities()
    normalized_data = normalize_vehicle_data(raw_state, raw_metrics, capabilities)

    hass.data[DOMAIN][entry.entry_id] = {
        DATA_ADAPTER: adapter,
        DATA_ENTITIES: [],
        DATA_NORMALIZED: normalized_data,
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


def _create_adapter(hass: HomeAssistant, entry: ConfigEntry) -> VehicleAdapter:
    """Create the configured adapter instance."""

    adapter_type = entry.data.get(CONF_ADAPTER, "mock")
    if not isinstance(adapter_type, str):
        raise ValueError("Configured adapter type must be a string")
    return create_adapter_from_entry(hass, adapter_type, dict(entry.data))


__all__ = ["DOMAIN"]
