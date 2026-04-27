"""Tests for registry-driven platform entity generation."""

from __future__ import annotations

import asyncio

from custom_components.my_vehicles.mappings.schema import load_adapter_mapping
from custom_components.my_vehicles.entities.binary_sensor import (
    VehicleBinaryStateEntity,
    async_setup_entry as async_setup_binary_sensors,
)
from custom_components.my_vehicles.entities.button import (
    VehicleActionButtonEntity,
    async_setup_entry as async_setup_buttons,
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
    def __init__(
        self,
        *,
        unavailable_actions: set[tuple[str, str]] | None = None,
        unavailable_capabilities: set[str] | None = None,
    ) -> None:
        self._mapping = load_adapter_mapping("kia_uvo")
        self._unavailable_actions = unavailable_actions or set()
        self._unavailable_capabilities = unavailable_capabilities or set()

    def is_action_available(self, capability_name: str, action: str, **kwargs) -> bool:
        _ = kwargs
        return (capability_name, action) not in self._unavailable_actions

    def is_capability_available(self, capability_name: str, **kwargs) -> bool:
        _ = kwargs
        return capability_name not in self._unavailable_capabilities


def _normalized_vehicle(
    *,
    lock_state_supported: bool,
    lock_action_supported: bool,
    locked: bool | None = None,
    windows_state_supported: bool = False,
    windows_action_supported: bool = False,
    hazard_action_supported: bool = False,
    ev_charging_state_supported: bool = False,
    ev_charging_action_supported: bool = False,
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
            central_locking=CapabilitySupport(
                state_supported=lock_state_supported,
                action_supported=lock_action_supported,
            ),
            windows=CapabilitySupport(
                state_supported=windows_state_supported,
                action_supported=windows_action_supported,
            ),
            hazard_lights=CapabilitySupport(
                state_supported=False,
                action_supported=hazard_action_supported,
            ),
            ev_charging=CapabilitySupport(
                state_supported=ev_charging_state_supported,
                action_supported=ev_charging_action_supported,
            ),
        ),
        locked=locked,
    )


def _vehicle_entry(
    *,
    lock_state_supported: bool,
    lock_action_supported: bool,
    locked: bool | None = None,
    windows_state_supported: bool = False,
    windows_action_supported: bool = False,
    hazard_action_supported: bool = False,
    ev_charging_state_supported: bool = False,
    ev_charging_action_supported: bool = False,
    unavailable_actions: set[tuple[str, str]] | None = None,
    unavailable_capabilities: set[str] | None = None,
) -> dict[str, object]:
    return {
        DATA_ADAPTER: _FakeAdapter(
            unavailable_actions=unavailable_actions,
            unavailable_capabilities=unavailable_capabilities,
        ),
        DATA_NORMALIZED: _normalized_vehicle(
            lock_state_supported=lock_state_supported,
            lock_action_supported=lock_action_supported,
            locked=locked,
            windows_state_supported=windows_state_supported,
            windows_action_supported=windows_action_supported,
            hazard_action_supported=hazard_action_supported,
            ev_charging_state_supported=ev_charging_state_supported,
            ev_charging_action_supported=ev_charging_action_supported,
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


def test_button_platform_creates_window_and_hazard_buttons_from_registry() -> None:
    """Registry-driven action buttons should appear only for mapped canonical verbs."""

    hass = HomeAssistant()
    entry = _FakeEntry()
    vehicle_data = _vehicle_entry(
        lock_state_supported=False,
        lock_action_supported=False,
        windows_state_supported=True,
        windows_action_supported=True,
        hazard_action_supported=True,
        unavailable_actions={("windows", "open")},
    )
    hass.data = {
        DOMAIN: {
            entry.entry_id: {
                DATA_VEHICLES: [vehicle_data],
            }
        }
    }
    added = []

    asyncio.run(async_setup_buttons(hass, entry, added.extend))

    keys = {entity._entity_key for entity in added if isinstance(entity, VehicleActionButtonEntity)}
    icons = {entity._entity_key: entity.icon for entity in added if isinstance(entity, VehicleActionButtonEntity)}

    assert "open_windows" in keys
    assert "close_windows" in keys
    assert "turn_on_hazard_lights" in keys
    assert "turn_off_hazard_lights" not in keys
    assert icons["turn_on_hazard_lights"] == "mdi:hazard-lights"
    open_button = next(entity for entity in added if entity._entity_key == "open_windows")
    assert open_button.available is False


def test_button_availability_updates_when_adapter_availability_changes() -> None:
    """Buttons should stay registered but reflect changing action availability."""

    hass = HomeAssistant()
    entry = _FakeEntry()
    vehicle_data = _vehicle_entry(
        lock_state_supported=False,
        lock_action_supported=False,
        windows_state_supported=True,
        windows_action_supported=True,
        unavailable_actions={("windows", "open")},
    )
    hass.data = {
        DOMAIN: {
            entry.entry_id: {
                DATA_VEHICLES: [vehicle_data],
            }
        }
    }
    added = []

    asyncio.run(async_setup_buttons(hass, entry, added.extend))

    open_button = next(entity for entity in added if entity._entity_key == "open_windows")
    adapter = vehicle_data[DATA_ADAPTER]

    assert open_button.available is False

    adapter._unavailable_actions.clear()

    assert open_button.available is True


def test_switch_availability_reflects_action_availability() -> None:
    """Switch entities should become unavailable only from capability availability."""

    hass = HomeAssistant()
    entry = _FakeEntry()
    vehicle_data = _vehicle_entry(
        lock_state_supported=False,
        lock_action_supported=False,
        ev_charging_state_supported=True,
        ev_charging_action_supported=True,
        unavailable_capabilities={"ev_charging"},
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

    charging_switch = next(entity for entity in added if entity._entity_key == "ev_charging")
    assert charging_switch.available is False

    adapter = vehicle_data[DATA_ADAPTER]
    adapter._unavailable_capabilities.clear()

    assert charging_switch.available is True


def test_switch_stays_available_when_only_one_direction_is_currently_available() -> None:
    """State-dependent verb availability must not disable the whole switch."""

    hass = HomeAssistant()
    entry = _FakeEntry()
    vehicle_data = _vehicle_entry(
        lock_state_supported=False,
        lock_action_supported=False,
        ev_charging_state_supported=True,
        ev_charging_action_supported=True,
        unavailable_actions={("ev_charging", "stop")},
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

    charging_switch = next(entity for entity in added if entity._entity_key == "ev_charging")

    assert charging_switch.available is True
