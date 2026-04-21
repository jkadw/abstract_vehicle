"""Compatibility tests for the Kia/Hyundai adapter alias."""

from __future__ import annotations

import pytest

from custom_components.vehicle.adapters.base import UnsupportedVehicleActionError
from custom_components.vehicle.adapters.kia_hyundai import KiaHyundaiVehicleAdapter
from custom_components.vehicle.normalization import (
    NormalizationConfig,
    normalize_vehicle_data,
)


def _configured_vehicles() -> list[dict]:
    return [
        {
            "vehicle_id": "kia-1",
            "name": "Kia EV6",
            "manufacturer": "Kia",
            "model": "EV6",
            "vehicle_type": "ev",
            "available": True,
            "backend_online": True,
            "charging_active": True,
            "charging_plugged": True,
            "locked": True,
            "climate_active": False,
            "metrics": {
                "battery_level": 61.5,
                "range": 198.0,
                "odometer": 12450.0,
                "latitude": 33.7490,
                "longitude": -84.3880,
            },
            "source_units": {
                "distance_unit": "mi",
            },
            "capabilities": {
                "lock": {"state_supported": True, "action_supported": True},
                "climate": {"state_supported": True, "action_supported": True},
                "charging": {"state_supported": True, "action_supported": False},
                "battery": {"state_supported": True, "action_supported": False},
                "odometer": {"state_supported": True, "action_supported": False},
            },
        }
    ]


@pytest.mark.asyncio
async def test_kia_hyundai_adapter_exposes_minimal_capabilities() -> None:
    """The reference adapter should intentionally keep a small capability surface."""

    adapter = KiaHyundaiVehicleAdapter(vehicles=_configured_vehicles())
    capabilities = await adapter.get_capabilities()

    assert capabilities.lock.state_supported is True
    assert capabilities.lock.action_supported is True
    assert capabilities.climate.state_supported is True
    assert capabilities.climate.action_supported is True
    assert capabilities.battery.state_supported is True
    assert capabilities.charging.state_supported is True
    assert capabilities.windows.state_supported is False
    assert capabilities.windows.action_supported is False


@pytest.mark.asyncio
async def test_kia_hyundai_adapter_relies_on_normalization_for_distance_units() -> None:
    """The adapter should return raw source units and let normalization convert them."""

    adapter = KiaHyundaiVehicleAdapter(vehicles=_configured_vehicles())

    normalized = normalize_vehicle_data(
        await adapter.get_raw_state(),
        await adapter.get_raw_metrics(),
        await adapter.get_capabilities(),
        config=NormalizationConfig(distance_unit="km"),
    )

    assert normalized.state.value == "charging"
    assert normalized.range == 318.65
    assert normalized.odometer == 20036.463
    assert normalized.capabilities.location.state_supported is True


@pytest.mark.asyncio
async def test_kia_hyundai_adapter_supports_only_lock_actions() -> None:
    """The minimal action set should still include lock and climate control."""

    adapter = KiaHyundaiVehicleAdapter(vehicles=_configured_vehicles())

    await adapter.execute_action("unlock")
    await adapter.execute_action("start_climate")
    raw_state = await adapter.get_raw_state()
    assert raw_state["locked"] is False
    assert raw_state["climate_active"] is True

    with pytest.raises(UnsupportedVehicleActionError):
        await adapter.execute_action("open_windows")
