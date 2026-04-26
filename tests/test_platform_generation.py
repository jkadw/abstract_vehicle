"""Tests for registry-driven platform entity generation."""

from __future__ import annotations

import asyncio

from custom_components.my_vehicles.mappings.schema import load_adapter_mapping
from custom_components.my_vehicles.entities.binary_sensor import (
    VehicleBinaryStateEntity,
    async_setup_entry as async_setup_binary_sensors,
)
from custom_components.my_vehicles.const import (
    DATA_ADAPTER,
    DATA_ENTITIES,
    DATA_NORMALIZED,
    DATA_VEHICLES,
    DOMAIN,
)
from custom_components.my_vehicles.entities.lock import (
    VehicleLockCapabilityEntity,
    async_setup_entry as async_setup_locks,
)
from custom_components.my_vehicles.domain.model import (
    CapabilitySupport,
    NormalizedVehicleData,
    VehicleCapabilities,
    VehicleInfo,
    VehicleState,
)
from custom_components.my_vehicles.entities.switch import (
    async_setup_entry as async_setup_switches,
)
from homeassistant.core import HomeAssistant


class _FakeEntry:
    def __init__(self, entry_id: str = "entry-1") -> None:
        self.entry_id = entry_id


class _FakeAdapter:
    def __init__(self) -> None:
        self._mapping = load_adapter_mapping("hyundai_kia_connect_kia_uvo")


def _normalized_vehicle(
    *,
    lock_state_supported: bool,
    lock_action_supported: bool,
    locked: bool | None = None,
) -> NormalizedVehicleData:
    return NormalizedVehicleData(
        info=VehicleInfo(
            vehicle_id="vehicle-123",
            name="Family EV",
            manufacturer="Test Motors",
            model="Atlas",
            vehicle_type="ev",
        ),
        state=VehicleState.PARKED,
        capabilities=VehicleCapabilities(
            lock_vehicle=CapabilitySupport(
                state_supported=lock_state_supported,
                action_supported=lock_action_supported,
            ),
        ),
        locked=locked,
    )


def _vehicle_entry(
    *,
    lock_state_supported: bool,
    lock_action_supported: bool,
    locked: bool | None = None,
) -> dict[str, object]:
    return {
        DATA_ADAPTER: _FakeAdapter(),
        DATA_NORMALIZED: _normalized_vehicle(
            lock_state_supported=lock_state_supported,
            lock_action_supported=lock_action_supported,
            locked=locked,
        ),
        DATA_ENTITIES: [],
    }


def test_lock_platform_creates_lock_entity_without_state_support() -> None:
    """The lock exception should always create a lock-domain entity."""

    hass = HomeAssistant()
    entry = _FakeEntry()
    vehicle_data = _vehicle_entry(
        lock_state_supported=False,
        lock_action_supported=False,
        locked=None,
    )
    hass.data = {
        DOMAIN: {
            entry.entry_id: {
                DATA_VEHICLES: [vehicle_data],
            }
        }
    }
    added = []

    asyncio.run(async_setup_locks(hass, entry, added.extend))

    assert len(added) == 1
    assert isinstance(added[0], VehicleLockCapabilityEntity)
    assert added[0].is_locked is None
    assert vehicle_data[DATA_ENTITIES] == added


def test_binary_sensor_platform_creates_vehicle_locked_when_state_supported() -> None:
    """Binary-sensor-like lock state should create the canonical boolean entity."""

    hass = HomeAssistant()
    entry = _FakeEntry()
    vehicle_data = _vehicle_entry(
        lock_state_supported=True,
        lock_action_supported=False,
        locked=True,
    )
    hass.data = {
        DOMAIN: {
            entry.entry_id: {
                DATA_VEHICLES: [vehicle_data],
            }
        }
    }
    added = []

    asyncio.run(async_setup_binary_sensors(hass, entry, added.extend))

    assert len(added) == 1
    assert isinstance(added[0], VehicleBinaryStateEntity)
    assert added[0]._entity_key == "vehicle_locked"
    assert added[0].is_on is False


def test_switch_platform_does_not_create_lock_switch_when_actions_are_available() -> None:
    """The lock-domain exception should not also expose a switch entity."""

    hass = HomeAssistant()
    entry = _FakeEntry()
    vehicle_data = _vehicle_entry(
        lock_state_supported=False,
        lock_action_supported=True,
        locked=False,
    )
    hass.data = {
        DOMAIN: {
            entry.entry_id: {
                DATA_VEHICLES: [vehicle_data],
            }
        }
    }
    added = []

    asyncio.run(async_setup_switches(hass, entry, added.extend))

    assert added == []
