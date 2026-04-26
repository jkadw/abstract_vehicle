"""Tests for the normalization layer."""

from __future__ import annotations

from custom_components.my_vehicles.domain.model import (
    CapabilitySupport,
    VehicleCapabilities,
    VehicleState,
)
from custom_components.my_vehicles.domain.normalization import (
    build_capability_values,
    infer_capabilities,
    normalize_openings,
    normalize_vehicle_data,
    normalize_vehicle_state,
)


def test_normalize_vehicle_state_precedence() -> None:
    """Charging and error precedence should be preserved."""

    assert (
        normalize_vehicle_state(
            {
                "status": "driving",
                "charging_active": True,
                "backend_online": True,
            }
        )
        is VehicleState.CHARGING
    )
    assert (
        normalize_vehicle_state(
            {
                "status": "charging",
                "has_error": True,
            }
        )
        is VehicleState.ERROR
    )
    assert (
        normalize_vehicle_state({"status": "offline", "available": False})
        is VehicleState.OFFLINE
    )
    assert normalize_vehicle_state({}) is VehicleState.UNKNOWN


def test_normalize_openings_aggregates_any_open_window() -> None:
    """Window aggregation should collapse many openings into one flag."""

    assert normalize_openings({"front_left": "closed", "sunroof": "open"}) is True
    assert normalize_openings({"front_left": "closed", "sunroof": "closed"}) is False
    assert normalize_openings(None) is None


def test_infer_capabilities_preserves_actions_and_fills_state_support() -> None:
    """Declared mapping support should remain authoritative."""

    declared = VehicleCapabilities(
        lock_vehicle=CapabilitySupport(state_supported=False, action_supported=True),
        climate=CapabilitySupport(state_supported=False, action_supported=True),
    )

    inferred = infer_capabilities(
        raw_state={
            "locked": True,
            "climate_active": False,
            "charging_plugged": True,
        },
        raw_metrics={
            "battery_level": 80.0,
            "odometer": 1234.5,
            "openings": {"sunroof": "closed"},
            "latitude": 1.0,
            "longitude": 2.0,
        },
        declared_capabilities=declared,
    )

    assert inferred.lock_vehicle.state_supported is False
    assert inferred.lock_vehicle.action_supported is True
    assert inferred.windows.state_supported is False
    assert inferred.windows.action_supported is False
    assert inferred.location.state_supported is False
    assert inferred.battery_level.state_supported is False
    assert inferred.charging.state_supported is False


def test_build_capability_values_maps_canonical_capability_names() -> None:
    """Raw payloads should map onto canonical capability values."""

    capability_values = build_capability_values(
        raw_state={
            "locked": True,
            "climate_active": False,
            "charging_active": True,
            "ignition_on": True,
            "range_warning": False,
        },
        raw_metrics={
            "range": 100.0,
            "odometer": 10.0,
            "battery_level": 90.0,
            "openings": {"front_left": "closed", "sunroof": "open"},
            "latitude": 1.0,
            "longitude": 2.0,
        },
    )

    assert capability_values["lock_vehicle"] is True
    assert capability_values["climate"] is False
    assert capability_values["charging"] is True
    assert capability_values["windows"] is True
    assert capability_values["ignition"] is True
    assert capability_values["driving_range"] == 100.0
    assert capability_values["range_warning"] is False
    assert capability_values["battery_level"] == 90.0
    assert capability_values["location"] == {"latitude": 1.0, "longitude": 2.0}


def test_normalize_vehicle_data_preserves_source_distance_units() -> None:
    """Distance values should remain in source units after the refactor."""

    normalized = normalize_vehicle_data(
        raw_state={
            "vehicle_id": "vehicle-1",
            "name": "Family EV",
            "manufacturer": "Mock Motors",
            "model": "Atlas",
            "vehicle_type": "ev",
            "status": "parked",
            "locked": True,
            "climate_active": False,
            "charging_active": False,
            "charging_plugged": True,
        },
        raw_metrics={
            "range": 100.0,
            "odometer": 10.0,
            "battery_level": 90.0,
            "openings": {"front_left": "closed"},
            "source_units": {"distance_unit": "km"},
        },
        capabilities=VehicleCapabilities(
            lock_vehicle=CapabilitySupport(state_supported=True, action_supported=True),
            windows=CapabilitySupport(state_supported=True, action_supported=False),
            battery_level=CapabilitySupport(state_supported=True, action_supported=False),
            driving_range=CapabilitySupport(state_supported=True, action_supported=False),
            odometer=CapabilitySupport(state_supported=True, action_supported=False),
        ),
    )

    assert normalized.state is VehicleState.PARKED
    assert normalized.driving_range == 100.0
    assert normalized.range == 100.0
    assert normalized.odometer == 10.0
    assert normalized.capabilities.lock_vehicle.action_supported is True
    assert normalized.capabilities.windows.state_supported is True
    assert normalized.capabilities.battery_level.state_supported is True
    assert normalized.display_units.distance_unit == "km"
