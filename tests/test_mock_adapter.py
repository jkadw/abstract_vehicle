"""Tests for the mock vehicle adapter."""

from __future__ import annotations

import pytest

from custom_components.vehicle.adapters.base import UnsupportedVehicleActionError
from custom_components.vehicle.adapters.mock import MockVehicleAdapter


@pytest.mark.asyncio
async def test_mock_adapter_default_fixture_is_parked(
    mock_vehicle_adapter: MockVehicleAdapter,
) -> None:
    """The shared fixture should expose the default parked scenario."""

    raw_state = await mock_vehicle_adapter.get_raw_state()
    raw_metrics = await mock_vehicle_adapter.get_raw_metrics()
    capabilities = await mock_vehicle_adapter.get_capabilities()

    assert raw_state["status"] == "parked"
    assert raw_state["locked"] is True
    assert raw_state["climate_active"] is False
    assert raw_metrics["battery_level"] == 72.5
    assert raw_metrics["openings"]["sunroof"] == "closed"
    assert capabilities.lock.action_supported is True
    assert capabilities.windows.action_supported is False
    assert capabilities.climate.action_supported is True
    assert capabilities.refresh.action_supported is True


@pytest.mark.asyncio
async def test_mock_adapter_supports_charging_and_offline_scenarios() -> None:
    """The fake backend should cover multiple high-level scenarios."""

    charging_adapter = MockVehicleAdapter(initial_state="charging")
    offline_adapter = MockVehicleAdapter(initial_state="offline")

    charging_state = await charging_adapter.get_raw_state()
    offline_state = await offline_adapter.get_raw_state()

    assert charging_state["status"] == "charging"
    assert charging_state["charging_active"] is True
    assert offline_state["status"] == "offline"
    assert offline_state["backend_online"] is False


@pytest.mark.asyncio
async def test_mock_adapter_actions_update_internal_state(
    mock_vehicle_adapter: MockVehicleAdapter,
) -> None:
    """Supported actions should transition the in-memory state."""

    await mock_vehicle_adapter.execute_action("unlock")
    unlocked_state = await mock_vehicle_adapter.get_raw_state()
    assert unlocked_state["locked"] is False

    await mock_vehicle_adapter.execute_action("start_climate")
    climate_state = await mock_vehicle_adapter.get_raw_state()
    assert climate_state["climate_active"] is True

    refresh_result = await mock_vehicle_adapter.execute_action("refresh")
    assert refresh_result["action"] == "refresh"


@pytest.mark.asyncio
async def test_mock_adapter_rejects_unsupported_actions(
    mock_vehicle_adapter: MockVehicleAdapter,
) -> None:
    """Unsupported actions should raise a domain-specific error."""

    with pytest.raises(UnsupportedVehicleActionError):
        await mock_vehicle_adapter.execute_action("open_windows")
