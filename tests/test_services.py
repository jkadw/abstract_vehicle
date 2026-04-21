"""Tests for service dispatch."""

from __future__ import annotations

import pytest

from custom_components.vehicle.adapters.base import UnsupportedVehicleActionError
from custom_components.vehicle.adapters.mock import MockVehicleAdapter
from custom_components.vehicle.const import (
    DATA_ADAPTER,
    DATA_ENTITY,
    DATA_NORMALIZED,
    DOMAIN,
    SERVICE_START_CLIMATE,
    SERVICE_UNLOCK,
)
from custom_components.vehicle.model import CapabilitySupport, VehicleCapabilities
from custom_components.vehicle.normalization import normalize_vehicle_data
from custom_components.vehicle.services import _build_service_handler
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


class _ExplodingAdapter(MockVehicleAdapter):
    """Adapter that simulates an unexpected backend failure."""

    async def execute_action(self, action: str, **kwargs):
        _ = action, kwargs
        raise RuntimeError("backend boom")


@pytest.mark.asyncio
async def test_service_dispatch_executes_action_and_refreshes_entity() -> None:
    """A supported service should delegate to the adapter and refresh state."""

    hass = HomeAssistant()
    adapter = MockVehicleAdapter()
    entity = _FakeEntity("sensor.family_ev")
    normalized = normalize_vehicle_data(
        await adapter.get_raw_state(),
        await adapter.get_raw_metrics(),
        await adapter.get_capabilities(),
    )
    hass.data = {
        DOMAIN: {
            "entry-1": {
                DATA_ADAPTER: adapter,
                DATA_NORMALIZED: normalized,
                DATA_ENTITY: entity,
            }
        }
    }

    handler = _build_service_handler(hass, SERVICE_UNLOCK)
    await handler(ServiceCall({"entity_id": "sensor.family_ev"}))

    refreshed_state = await adapter.get_raw_state()
    assert refreshed_state["locked"] is False
    assert entity.updated_data is not None
    assert entity.updated_data.locked is False
    assert entity.write_calls == 1


@pytest.mark.asyncio
async def test_service_dispatch_rejects_missing_capability_support() -> None:
    """Capability-based validation should block unsupported actions."""

    hass = HomeAssistant()
    adapter = MockVehicleAdapter()
    entity = _FakeEntity("sensor.family_ev")
    normalized = normalize_vehicle_data(
        await adapter.get_raw_state(),
        await adapter.get_raw_metrics(),
        VehicleCapabilities(
            lock=CapabilitySupport(state_supported=True, action_supported=True),
            climate=CapabilitySupport(state_supported=True, action_supported=False),
        ),
    )
    hass.data = {
        DOMAIN: {
            "entry-1": {
                DATA_ADAPTER: adapter,
                DATA_NORMALIZED: normalized,
                DATA_ENTITY: entity,
            }
        }
    }

    handler = _build_service_handler(hass, SERVICE_START_CLIMATE)
    with pytest.raises(ServiceValidationError):
        await handler(ServiceCall({"entity_id": "sensor.family_ev"}))


@pytest.mark.asyncio
async def test_service_dispatch_maps_unsupported_adapter_action_to_validation_error() -> None:
    """Unsupported adapter actions should become validation errors."""

    class _UnsupportedClimateAdapter(MockVehicleAdapter):
        async def execute_action(self, action: str, **kwargs):
            if action == "start_climate":
                raise UnsupportedVehicleActionError("climate unavailable")
            return await super().execute_action(action, **kwargs)

    hass = HomeAssistant()
    adapter = _UnsupportedClimateAdapter()
    entity = _FakeEntity("sensor.family_ev")
    normalized = normalize_vehicle_data(
        await adapter.get_raw_state(),
        await adapter.get_raw_metrics(),
        await adapter.get_capabilities(),
    )
    hass.data = {
        DOMAIN: {
            "entry-1": {
                DATA_ADAPTER: adapter,
                DATA_NORMALIZED: normalized,
                DATA_ENTITY: entity,
            }
        }
    }

    handler = _build_service_handler(hass, SERVICE_START_CLIMATE)
    with pytest.raises(ServiceValidationError):
        await handler(ServiceCall({"entity_id": "sensor.family_ev"}))


@pytest.mark.asyncio
async def test_service_dispatch_maps_unexpected_adapter_errors() -> None:
    """Unexpected adapter failures should raise a generic HA error."""

    hass = HomeAssistant()
    adapter = _ExplodingAdapter()
    entity = _FakeEntity("sensor.family_ev")
    normalized = normalize_vehicle_data(
        await adapter.get_raw_state(),
        await adapter.get_raw_metrics(),
        await adapter.get_capabilities(),
    )
    hass.data = {
        DOMAIN: {
            "entry-1": {
                DATA_ADAPTER: adapter,
                DATA_NORMALIZED: normalized,
                DATA_ENTITY: entity,
            }
        }
    }

    handler = _build_service_handler(hass, SERVICE_UNLOCK)
    with pytest.raises(HomeAssistantError):
        await handler(ServiceCall({"entity_id": "sensor.family_ev"}))
