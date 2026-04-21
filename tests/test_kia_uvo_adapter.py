"""Tests for the kia_uvo-backed adapter."""

from __future__ import annotations

import pytest

from custom_components.vehicle.adapters.base import UnsupportedVehicleActionError
from custom_components.vehicle.adapters.kia_uvo import KiaUvoVehicleAdapter
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
            "has_error": False,
            "driving": False,
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
            "openings": {
                "front_left_window": "closed",
                "sunroof": "closed",
            },
            "source_units": {
                "distance_unit": "mi",
                "temperature_unit": "F",
                "power_unit": "kW",
                "energy_unit": "kWh",
            },
            "capabilities": {
                "lock": {"state_supported": True, "action_supported": True},
                "windows": {"state_supported": False, "action_supported": False},
                "climate": {"state_supported": True, "action_supported": True},
                "charging": {"state_supported": True, "action_supported": False},
                "location": {"state_supported": False, "action_supported": False},
                "battery": {"state_supported": True, "action_supported": False},
                "fuel": {"state_supported": False, "action_supported": False},
                "odometer": {"state_supported": True, "action_supported": False},
            },
        },
        {
            "vehicle_id": "hyundai-2",
            "name": "Hyundai Kona",
            "manufacturer": "Hyundai",
            "model": "Kona Electric",
            "vehicle_type": "ev",
            "available": True,
            "backend_online": False,
            "has_error": False,
            "charging_active": False,
            "charging_plugged": False,
            "locked": False,
            "metrics": {
                "battery_level": 44.0,
                "range": 140.0,
                "odometer": 9021.0,
            },
            "source_units": {
                "distance_unit": "mi",
            },
            "capabilities": {
                "lock": {"state_supported": True, "action_supported": True},
                "climate": {"state_supported": True, "action_supported": True},
                "battery": {"state_supported": True, "action_supported": False},
                "charging": {"state_supported": True, "action_supported": False},
                "odometer": {"state_supported": True, "action_supported": False},
            },
        },
    ]


@pytest.mark.asyncio
async def test_kia_uvo_adapter_maps_selected_configured_vehicle() -> None:
    """The adapter should select the configured vehicle from entry data."""

    adapter = KiaUvoVehicleAdapter(vehicles=_configured_vehicles(), vehicle_id="hyundai-2")

    raw_state = await adapter.get_raw_state()
    raw_metrics = await adapter.get_raw_metrics()
    capabilities = await adapter.get_capabilities()

    assert raw_state["vehicle_id"] == "hyundai-2"
    assert raw_state["manufacturer"] == "Hyundai"
    assert raw_state["status"] == "offline"
    assert raw_metrics["battery_level"] == 44.0
    assert capabilities.lock.action_supported is True
    assert capabilities.windows.state_supported is False


@pytest.mark.asyncio
async def test_kia_uvo_adapter_relies_on_normalization_for_capability_inference_and_units() -> None:
    """Raw configured metrics should be normalized centrally."""

    adapter = KiaUvoVehicleAdapter(vehicles=_configured_vehicles(), vehicle_id="kia-1")
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
async def test_kia_uvo_adapter_executes_supported_actions_against_selected_vehicle() -> None:
    """Actions should mutate the configured vehicle payload, not a fixed stub scenario."""

    adapter = KiaUvoVehicleAdapter(vehicles=_configured_vehicles(), vehicle_id="kia-1")

    await adapter.execute_action("unlock")
    await adapter.execute_action("start_climate")
    raw_state = await adapter.get_raw_state()

    assert raw_state["locked"] is False
    assert raw_state["climate_active"] is True
    assert raw_state["vehicle_id"] == "kia-1"

    with pytest.raises(UnsupportedVehicleActionError):
        await adapter.execute_action("open_windows")


def test_kia_uvo_identifier_parsing_ignores_malformed_entries() -> None:
    """Discovery should not crash on unexpected identifier shapes."""

    identifiers = {
        ("other_domain", "ignore-me"),
        ("kia_uvo", "vehicle-123"),
        ("kia_uvo", ""),
        ("broken",),
        "not-a-tuple",
    }

    vehicle_id = KiaUvoVehicleAdapter._vehicle_id_from_identifiers(identifiers)

    assert vehicle_id == "vehicle-123"
