"""My Vehicles integration package."""

from __future__ import annotations

from .const import DOMAIN


async def async_setup(hass, config):
    from .setup.entry import async_setup as _async_setup

    return await _async_setup(hass, config)


async def async_setup_entry(hass, entry):
    from .setup.entry import async_setup_entry as _async_setup_entry

    return await _async_setup_entry(hass, entry)


async def async_unload_entry(hass, entry):
    from .setup.entry import async_unload_entry as _async_unload_entry

    return await _async_unload_entry(hass, entry)


__all__ = ["DOMAIN", "async_setup", "async_setup_entry", "async_unload_entry"]
