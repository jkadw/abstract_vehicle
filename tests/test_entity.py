"""Tests for the normalized vehicle entity."""

from __future__ import annotations

import sys
import types

from custom_components.vehicle.model import (
    CapabilitySupport,
    NormalizedVehicleData,
    VehicleCapabilities,
    VehicleInfo,
    VehicleState,
)


if "homeassistant" not in sys.modules:
    homeassistant = types.ModuleType("homeassistant")
    helpers = types.ModuleType("homeassistant.helpers")
    entity_module = types.ModuleType("homeassistant.helpers.entity")
    device_registry_module = types.ModuleType("homeassistant.helpers.device_registry")

    class Entity:  # noqa: D401
        """Minimal Entity stub for unit tests."""

    class DeviceInfo(dict):
        """Simple dict-backed DeviceInfo replacement for tests."""

        def __init__(self, **kwargs):
            super().__init__(**kwargs)

    entity_module.Entity = Entity
    device_registry_module.DeviceInfo = DeviceInfo
    helpers.entity = entity_module
    helpers.device_registry = device_registry_module
    homeassistant.helpers = helpers

    sys.modules["homeassistant"] = homeassistant
    sys.modules["homeassistant.helpers"] = helpers
    sys.modules["homeassistant.helpers.entity"] = entity_module
    sys.modules["homeassistant.helpers.device_registry"] = device_registry_module


from custom_components.vehicle.entity import VehicleEntity


def _normalized_vehicle_data(state: VehicleState) -> NormalizedVehicleData:
    return NormalizedVehicleData(
        info=VehicleInfo(
            vehicle_id="vehicle-123",
            name="Family EV",
            manufacturer="Mock Motors",
            model="Atlas",
            vehicle_type="ev",
        ),
        state=state,
        capabilities=VehicleCapabilities(
            lock=CapabilitySupport(state_supported=True, action_supported=True),
            windows=CapabilitySupport(state_supported=True, action_supported=False),
            climate=CapabilitySupport(state_supported=True, action_supported=True),
        ),
        battery_level=80.0,
        range=260.0,
        locked=True,
        windows_open=False,
        climate_active=False,
        charging_active=state is VehicleState.CHARGING,
        charging_plugged=True,
        latitude=37.77,
        longitude=-122.41,
        odometer=12345.6,
    )


def test_vehicle_entity_uses_normalized_state_and_attributes() -> None:
    """Entity state and attributes should come from the normalized model."""

    entity = VehicleEntity(_normalized_vehicle_data(VehicleState.PARKED))

    assert entity.state == "parked"
    assert entity.available is True
    assert entity.extra_state_attributes["battery_level"] == 80.0
    assert entity.extra_state_attributes["windows_open"] is False
    assert entity.extra_state_attributes["lock_action_supported"] is True


def test_vehicle_entity_marks_unavailable_state_as_unavailable() -> None:
    """Only the normalized unavailable state should affect availability."""

    entity = VehicleEntity(_normalized_vehicle_data(VehicleState.UNAVAILABLE))

    assert entity.state == "unavailable"
    assert entity.available is False


def test_vehicle_entity_device_info_is_stable() -> None:
    """Device info should be derived from normalized vehicle metadata."""

    entity = VehicleEntity(_normalized_vehicle_data(VehicleState.OFFLINE))
    device_info = entity.device_info

    assert device_info["manufacturer"] == "Mock Motors"
    assert device_info["model"] == "Atlas"
    assert device_info["name"] == "Family EV"
    assert ("vehicle", "vehicle-123") in device_info["identifiers"]


def test_vehicle_entity_updates_metadata_when_snapshot_changes() -> None:
    """Refreshing normalized data should update HA-facing identifiers and name."""

    entity = VehicleEntity(_normalized_vehicle_data(VehicleState.PARKED))

    updated = NormalizedVehicleData(
        info=VehicleInfo(
            vehicle_id="vehicle-456",
            name="Updated Vehicle",
            manufacturer="Mock Motors",
            model="Atlas Touring",
            vehicle_type="ev",
        ),
        state=VehicleState.CHARGING,
        capabilities=entity._normalized_data.capabilities,
        battery_level=84.0,
    )

    entity.update_normalized_data(updated)

    assert entity.state == "charging"
    assert entity._attr_unique_id == "vehicle-456"
    assert entity._attr_name == "Updated Vehicle"
