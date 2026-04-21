"""Config flow for the vehicle integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import (
    ADAPTER_TYPE_MOCK,
    CONF_ADAPTER,
    CONF_SCENARIO,
    DEFAULT_ENTRY_TITLE,
    DEFAULT_MOCK_SCENARIO,
    DOMAIN,
    MOCK_SCENARIOS,
)


class VehicleConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Minimal config flow that supports the mock adapter."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Handle the initial step."""

        if user_input is not None:
            title = (
                f"{DEFAULT_ENTRY_TITLE} ({user_input[CONF_SCENARIO]})"
                if user_input[CONF_ADAPTER] == ADAPTER_TYPE_MOCK
                else DEFAULT_ENTRY_TITLE
            )
            return self.async_create_entry(title=title, data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_ADAPTER, default=ADAPTER_TYPE_MOCK): vol.In(
                    (ADAPTER_TYPE_MOCK,)
                ),
                vol.Required(CONF_SCENARIO, default=DEFAULT_MOCK_SCENARIO): vol.In(
                    MOCK_SCENARIOS
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)
