"""Tests for service dispatch."""

from __future__ import annotations

import asyncio

import pytest

from custom_components.my_vehicles.runtime.base import UnsupportedVehicleActionError
from custom_components.my_vehicles.const import (
    DATA_ADAPTER,
    DATA_ENTITIES,
    DATA_NORMALIZED,
    DATA_VEHICLES,
    DOMAIN,
    SERVICE_DIAGNOSTICS,
)
from custom_components.my_vehicles.domain.model import CapabilitySupport, VehicleCapabilities
from custom_components.my_vehicles.domain.normalization import normalize_vehicle_data
from custom_components.my_vehicles import services as services_module
from custom_components.my_vehicles.services import _build_service_handler
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError


class _FakeEntity:
    """Minimal entity stub that records refresh behavior."""

    def __init__(self, entity_id: str) -> None:
        self.entity_id = entity_id
        self.updated_data = None
        self.write_calls = 0

    def update_normalized_data(self, normalized_data) -> None:
        self.updated_data = normalized_data

    def async_write_ha_state(self) -> None:
        self.write_calls += 1


class _ServiceAdapter:
    """Small local adapter for service-dispatch tests."""

    def __init__(self) -> None:
        self._locked = True
        self._climate_active = False

    async def get_raw_state(self) -> dict[str, object]:
        return {
            "vehicle_id": "vehicle-123",
            "name": "Family EV",
            "manufacturer": "Test Motors",
            "model": "Atlas",
            "vehicle_type": "ev",
            "status": "parked",
            "available": True,
            "backend_online": True,
            "has_error": False,
            "driving": False,
            "ev_charging": False,
            "ev_plugged_in": True,
            "locked": self._locked,
            "climate_active": self._climate_active,
        }

    async def get_raw_metrics(self) -> dict[str, object]:
        return {
            "ev_battery_level": 80.0,
            "driving_range": 250.0,
            "openings": {},
            "source_units": {"distance_unit": "km"},
        }

    async def get_capabilities(self) -> VehicleCapabilities:
        return VehicleCapabilities(
            central_locking=CapabilitySupport(state_supported=True, action_supported=True),
            climate=CapabilitySupport(state_supported=True, action_supported=True),
            refresh=CapabilitySupport(state_supported=False, action_supported=True),
        )

    async def execute_action(self, action: str, **kwargs):
        _ = kwargs
        if action == "unlock":
            self._locked = False
            return {"success": True, "action": action}
        if action == "lock":
            self._locked = True
            return {"success": True, "action": action}
        if action in {"start_heating", "start_cooling"}:
            self._climate_active = True
            return {"success": True, "action": action}
        if action == "stop":
            self._climate_active = False
            return {"success": True, "action": action}
        if action == "refresh":
            return {"success": True, "action": action}
        raise UnsupportedVehicleActionError(f"Unsupported action: {action}")


class _ExplodingAdapter(_ServiceAdapter):
    """Adapter that simulates an unexpected backend failure."""

    async def execute_action(self, action: str, **kwargs):
        _ = action, kwargs
        raise RuntimeError("backend boom")


class _UnavailableActionAdapter(_ServiceAdapter):
    """Adapter that reports a mapped action as currently unavailable."""

    def is_action_available(self, capability_name: str, action: str, **kwargs) -> bool:
        _ = kwargs
        return not (capability_name == "climate" and action == "start_heating")


class _FakeDevice:
    def __init__(self, device_id: str) -> None:
        self.id = device_id


class _FakeDeviceRegistry:
    def __init__(self, device_id: str) -> None:
        self._device = _FakeDevice(device_id)

    def async_get_device(self, identifiers=None, connections=None):
        _ = identifiers, connections
        return self._device


def test_service_dispatch_executes_action_and_refreshes_entity() -> None:
    """A supported service should delegate to the adapter and refresh state."""

    hass = HomeAssistant()
    adapter = _ServiceAdapter()
    entity = _FakeEntity("sensor.family_ev")
    device_id = "device-123"
    normalized = normalize_vehicle_data(
        asyncio.run(adapter.get_raw_state()),
        asyncio.run(adapter.get_raw_metrics()),
        asyncio.run(adapter.get_capabilities()),
    )
    hass.data = {
        DOMAIN: {
            "entry-1": {
                DATA_VEHICLES: [
                    {
                        DATA_ADAPTER: adapter,
                        DATA_NORMALIZED: normalized,
                        DATA_ENTITIES: [entity],
                    }
                ],
            }
        }
    }
    services_module.dr.async_get = lambda _hass: _FakeDeviceRegistry(device_id)

    handler = _build_service_handler(hass, "central_locking")
    asyncio.run(handler(ServiceCall({"device_id": device_id, "action": "unlock"})))

    refreshed_state = asyncio.run(adapter.get_raw_state())
    assert refreshed_state["locked"] is False
    assert entity.updated_data is not None
    assert entity.updated_data.locked is False
    assert entity.write_calls == 1


def test_service_dispatch_rejects_missing_capability_support() -> None:
    """Capability-based validation should block unsupported actions."""

    hass = HomeAssistant()
    adapter = _ServiceAdapter()
    entity = _FakeEntity("sensor.family_ev")
    device_id = "device-123"
    normalized = normalize_vehicle_data(
        asyncio.run(adapter.get_raw_state()),
        asyncio.run(adapter.get_raw_metrics()),
        VehicleCapabilities(
            central_locking=CapabilitySupport(state_supported=True, action_supported=True),
            climate=CapabilitySupport(state_supported=True, action_supported=False),
        ),
    )
    hass.data = {
        DOMAIN: {
            "entry-1": {
                DATA_VEHICLES: [
                    {
                        DATA_ADAPTER: adapter,
                        DATA_NORMALIZED: normalized,
                        DATA_ENTITIES: [entity],
                    }
                ],
            }
        }
    }
    services_module.dr.async_get = lambda _hass: _FakeDeviceRegistry(device_id)

    handler = _build_service_handler(hass, "climate")
    with pytest.raises(ServiceValidationError):
        asyncio.run(
            handler(ServiceCall({"device_id": device_id, "action": "start_heating"}))
        )


def test_service_dispatch_maps_unsupported_adapter_action_to_validation_error() -> None:
    """Unsupported adapter actions should become validation errors."""

    class _UnsupportedClimateAdapter(_ServiceAdapter):
        async def execute_action(self, action: str, **kwargs):
            if action == "start_heating":
                raise UnsupportedVehicleActionError("climate unavailable")
            return await super().execute_action(action, **kwargs)

    hass = HomeAssistant()
    adapter = _UnsupportedClimateAdapter()
    entity = _FakeEntity("sensor.family_ev")
    device_id = "device-123"
    normalized = normalize_vehicle_data(
        asyncio.run(adapter.get_raw_state()),
        asyncio.run(adapter.get_raw_metrics()),
        asyncio.run(adapter.get_capabilities()),
    )
    hass.data = {
        DOMAIN: {
            "entry-1": {
                DATA_VEHICLES: [
                    {
                        DATA_ADAPTER: adapter,
                        DATA_NORMALIZED: normalized,
                        DATA_ENTITIES: [entity],
                    }
                ],
            }
        }
    }
    services_module.dr.async_get = lambda _hass: _FakeDeviceRegistry(device_id)

    handler = _build_service_handler(hass, "climate")
    with pytest.raises(ServiceValidationError):
        asyncio.run(
            handler(ServiceCall({"device_id": device_id, "action": "start_heating"}))
        )


def test_service_dispatch_maps_unexpected_adapter_errors() -> None:
    """Unexpected adapter failures should raise a generic HA error."""

    hass = HomeAssistant()
    adapter = _ExplodingAdapter()
    entity = _FakeEntity("sensor.family_ev")
    device_id = "device-123"
    normalized = normalize_vehicle_data(
        asyncio.run(adapter.get_raw_state()),
        asyncio.run(adapter.get_raw_metrics()),
        asyncio.run(adapter.get_capabilities()),
    )
    hass.data = {
        DOMAIN: {
            "entry-1": {
                DATA_VEHICLES: [
                    {
                        DATA_ADAPTER: adapter,
                        DATA_NORMALIZED: normalized,
                        DATA_ENTITIES: [entity],
                    }
                ],
            }
        }
    }
    services_module.dr.async_get = lambda _hass: _FakeDeviceRegistry(device_id)

    handler = _build_service_handler(hass, "central_locking")
    with pytest.raises(HomeAssistantError):
        asyncio.run(handler(ServiceCall({"device_id": device_id, "action": "unlock"})))


def test_diagnostics_service_is_read_only_and_logs_results(caplog) -> None:
    """Diagnostics should inspect the vehicle without mutating state or entities."""

    hass = HomeAssistant()
    adapter = _ServiceAdapter()
    entity = _FakeEntity("sensor.family_ev")
    device_id = "device-123"
    normalized = normalize_vehicle_data(
        asyncio.run(adapter.get_raw_state()),
        asyncio.run(adapter.get_raw_metrics()),
        asyncio.run(adapter.get_capabilities()),
    )
    hass.data = {
        DOMAIN: {
            "entry-1": {
                DATA_VEHICLES: [
                    {
                        DATA_ADAPTER: adapter,
                        DATA_NORMALIZED: normalized,
                        DATA_ENTITIES: [entity],
                    }
                ],
            }
        }
    }
    services_module.dr.async_get = lambda _hass: _FakeDeviceRegistry(device_id)

    handler = services_module._build_diagnostics_handler(hass)
    with caplog.at_level("INFO"):
        asyncio.run(handler(ServiceCall({"device_id": device_id})))

    refreshed_state = asyncio.run(adapter.get_raw_state())
    assert refreshed_state["locked"] is True
    assert entity.updated_data is None
    assert entity.write_calls == 0
    assert "My Vehicles diagnostics:" in caplog.text
    assert "vehicle-123" in caplog.text


def test_service_dispatch_rejects_currently_unavailable_action() -> None:
    """Per-verb action availability should be enforced for service calls too."""

    hass = HomeAssistant()
    adapter = _UnavailableActionAdapter()
    entity = _FakeEntity("sensor.family_ev")
    device_id = "device-123"
    normalized = normalize_vehicle_data(
        asyncio.run(adapter.get_raw_state()),
        asyncio.run(adapter.get_raw_metrics()),
        asyncio.run(adapter.get_capabilities()),
    )
    hass.data = {
        DOMAIN: {
            "entry-1": {
                DATA_VEHICLES: [
                    {
                        DATA_ADAPTER: adapter,
                        DATA_NORMALIZED: normalized,
                        DATA_ENTITIES: [entity],
                    }
                ],
            }
        }
    }
    services_module.dr.async_get = lambda _hass: _FakeDeviceRegistry(device_id)

    handler = _build_service_handler(hass, "climate")
    with pytest.raises(ServiceValidationError, match="currently unavailable"):
        asyncio.run(
            handler(ServiceCall({"device_id": device_id, "action": "start_heating"}))
        )
