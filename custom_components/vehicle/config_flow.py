"""Config flow for the vehicle integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .adapters import (
    DiscoveredVehicle,
    discover_adapter_vehicles,
    get_available_adapter_options,
)
from .const import (
    ADAPTER_TYPE_MOCK,
    CONF_ADAPTER,
    CONF_VEHICLE_ID,
    CONF_VEHICLES,
    DOMAIN,
)


class VehicleConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow driven by adapter and vehicle discovery."""

    VERSION = 1

    def __init__(self) -> None:
        self._selected_adapter: str | None = None
        self._discovered_vehicles: list[DiscoveredVehicle] = []
        self._adapter_options: dict[str, tuple[str, object]] = {}

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Select the adapter to use."""

        if user_input is not None:
            self._selected_adapter = user_input[CONF_ADAPTER]
            return await self.async_step_vehicle()

        self._adapter_options = await get_available_adapter_options(self.hass)

        schema = vol.Schema(
            {
                vol.Required(CONF_ADAPTER, default=ADAPTER_TYPE_MOCK): vol.In(
                    {
                        adapter_key: adapter_label
                        for adapter_key, (adapter_label, _) in self._adapter_options.items()
                    }
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_vehicle(self, user_input: dict | None = None) -> FlowResult:
        """Select one of the vehicles discoverable by the chosen adapter."""

        if self._selected_adapter is None:
            return await self.async_step_user()

        if not self._adapter_options:
            self._adapter_options = await get_available_adapter_options(self.hass)
        if self._selected_adapter not in self._adapter_options:
            return self.async_abort(reason="adapter_not_available")
        if not self._discovered_vehicles:
            self._discovered_vehicles = await discover_adapter_vehicles(
                self.hass, self._selected_adapter
            )

        if user_input is not None:
            selected_vehicle = next(
                (
                    vehicle
                    for vehicle in self._discovered_vehicles
                    if vehicle.vehicle_id == user_input[CONF_VEHICLE_ID]
                ),
                None,
            )
            if selected_vehicle is None:
                return self.async_abort(reason="vehicle_not_found")

            await self.async_set_unique_id(
                f"{self._selected_adapter}:{selected_vehicle.vehicle_id}"
            )
            self._abort_if_unique_id_configured()

            entry_data = {
                CONF_ADAPTER: self._selected_adapter,
                CONF_VEHICLE_ID: selected_vehicle.vehicle_id,
                CONF_VEHICLES: [selected_vehicle.payload],
            }
            return self.async_create_entry(title=selected_vehicle.title, data=entry_data)

        if not self._discovered_vehicles:
            return self.async_show_form(
                step_id="vehicle",
                errors={"base": "no_vehicles_found"},
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_VEHICLE_ID): vol.In(
                    {
                        vehicle.vehicle_id: vehicle.title
                        for vehicle in self._discovered_vehicles
                    }
                )
            }
        )
        return self.async_show_form(step_id="vehicle", data_schema=schema)
