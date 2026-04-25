"""Config flow for the vehicle integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .adapters import get_available_adapter_options
from .const import (
    CONF_ADAPTER,
    DOMAIN,
)


class VehicleConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow driven by discovered mapping files."""

    VERSION = 1

    def __init__(self) -> None:
        self._selected_adapter: str | None = None
        self._adapter_options: dict[str, str] = {}

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Select the adapter to use."""

        if not self._adapter_options:
            self._adapter_options = await get_available_adapter_options(self.hass)

        if user_input is not None:
            self._selected_adapter = user_input[CONF_ADAPTER]
            if self._selected_adapter not in self._adapter_options:
                return self.async_abort(reason="adapter_not_available")

            await self.async_set_unique_id(self._selected_adapter)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=self._adapter_options[self._selected_adapter],
                data={CONF_ADAPTER: self._selected_adapter},
            )

        if not self._adapter_options:
            return self.async_abort(reason="no_adapters_available")

        default_adapter = next(iter(self._adapter_options))
        schema = vol.Schema(
            {
                vol.Required(CONF_ADAPTER, default=default_adapter): vol.In(
                    self._adapter_options
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)
