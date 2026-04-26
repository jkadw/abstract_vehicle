"""My Vehicles integration package."""

from __future__ import annotations

from .const import DOMAIN
from .setup.entry import async_setup, async_setup_entry, async_unload_entry

__all__ = ["DOMAIN", "async_setup", "async_setup_entry", "async_unload_entry"]
