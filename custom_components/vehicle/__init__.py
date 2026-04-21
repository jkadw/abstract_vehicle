"""Vehicle integration package."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .adapters import (
    HyundaiKiaConnectKiaUvoVehicleAdapter,
    MockVehicleAdapter,
    VehicleAdapter,
)
from .const import (
    ADAPTER_TYPE_KIA_UVO,
    ADAPTER_TYPE_MOCK,
    CONF_ADAPTER,
    CONF_VEHICLE_ID,
    CONF_VEHICLES,
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

    adapter_type = entry.data.get(CONF_ADAPTER, ADAPTER_TYPE_MOCK)
    if adapter_type == ADAPTER_TYPE_MOCK:
        return MockVehicleAdapter()
    if adapter_type == ADAPTER_TYPE_KIA_UVO:
        vehicles = entry.data.get(CONF_VEHICLES)
        if not isinstance(vehicles, list):
            raise ValueError("kia_uvo adapter requires configured vehicles")
        vehicle_id = entry.data.get(CONF_VEHICLE_ID)
        if vehicle_id is not None and not isinstance(vehicle_id, str):
            raise ValueError("kia_uvo vehicle_id must be a string when configured")
        return HyundaiKiaConnectKiaUvoVehicleAdapter(
            hass=hass, vehicles=vehicles, vehicle_id=vehicle_id
        )

    raise ValueError(f"Unsupported adapter type: {adapter_type}")


__all__ = ["DOMAIN"]
