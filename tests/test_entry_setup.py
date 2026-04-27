"""Tests for entry setup, reconciliation, and startup behavior."""

from __future__ import annotations

import asyncio
import logging

import pytest

from custom_components.my_vehicles.setup.entry import (
    _normalize_entry_adapter_key,
    _log_vehicle_reconciliation,
    _refresh_vehicle_entry,
    _snapshot_vehicle_ids,
    async_setup_entry,
)
from custom_components.my_vehicles.runtime.base import DiscoveredVehicle
from custom_components.my_vehicles.const import (
    CONF_ADAPTER,
    DATA_DISCOVERY_SNAPSHOTS,
    DATA_VEHICLES,
    DOMAIN,
    EVENT_STATE_CHANGED,
)
from custom_components.my_vehicles.domain.model import VehicleCapabilities
from custom_components.my_vehicles.domain.normalization import normalize_vehicle_data


class _FakeEntry:
    def __init__(self, entry_id: str = "entry-1", data: dict | None = None) -> None:
        self.entry_id = entry_id
        self.data = data or {}
        self.unload_callbacks: list[object] = []

    def async_on_unload(self, callback) -> None:
        self.unload_callbacks.append(callback)


class _FakeBus:
    def __init__(self) -> None:
        self.listeners: list[tuple[str, object]] = []
        self.fired: list[tuple[str, dict[str, object]]] = []

    def async_listen_once(self, event_type: str, callback):
        self.listeners.append((event_type, callback))
        return callback

    def async_fire(self, event_type: str, event_data) -> None:
        self.fired.append((event_type, event_data))


class _FakeConfigEntries:
    def __init__(self) -> None:
        self.forwarded: list[tuple[str, tuple[str, ...]]] = []
        self.reloads: list[str] = []
        self.updated: list[tuple[object, dict]] = []

    async def async_forward_entry_setups(self, entry, platforms) -> None:
        self.forwarded.append((entry.entry_id, tuple(platforms)))

    async def async_reload(self, entry_id: str) -> None:
        self.reloads.append(entry_id)

    def async_update_entry(self, entry, *, data) -> None:
        entry.data = data
        self.updated.append((entry, data))


class _FakeHass:
    def __init__(self, *, is_running: bool) -> None:
        self.data: dict[str, object] = {}
        self.is_running = is_running
        self.bus = _FakeBus()
        self.config_entries = _FakeConfigEntries()
        self.created_tasks: list[object] = []

    def async_create_task(self, coro):
        self.created_tasks.append(coro)
        return coro


class _FakeAdapter:
    def __init__(self, vehicle_id: str, name: str) -> None:
        self._vehicle_id = vehicle_id
        self._name = name
        self.raw_state_calls = 0
        self.raw_metrics_calls = 0
        self.capability_calls = 0

    async def get_raw_state(self) -> dict[str, object]:
        self.raw_state_calls += 1
        return {
            "vehicle_id": self._vehicle_id,
            "name": self._name,
            "manufacturer": "Kia",
            "model": "Unknown",
            "vehicle_type": "ev",
            "status": "parked",
            "available": True,
            "backend_online": True,
            "has_error": False,
            "driving": False,
            "ev_charging": False,
            "ev_plugged_in": False,
            "locked": True,
            "climate_active": False,
        }

    async def get_raw_metrics(self) -> dict[str, object]:
        self.raw_metrics_calls += 1
        return {
            "ev_battery_level": 60.0,
            "driving_range": 200.0,
            "openings": {},
            "source_units": {"distance_unit": "km"},
        }

    async def get_capabilities(self) -> VehicleCapabilities:
        self.capability_calls += 1
        return VehicleCapabilities()

    def source_entity_ids(self) -> tuple[str, ...]:
        return (f"sensor.{self._vehicle_id}_source",)


def test_async_setup_entry_builds_multi_vehicle_state_and_startup_reload(
    monkeypatch,
) -> None:
    """One mapping entry should own multiple vehicles and register a startup reload."""

    from custom_components.my_vehicles.setup import entry as vehicle_module

    hass = _FakeHass(is_running=False)
    hass.data = {
        DOMAIN: {
            DATA_DISCOVERY_SNAPSHOTS: {
                "entry-1": ["removed-vehicle", "vehicle-1"],
            }
        }
    }
    entry = _FakeEntry("entry-1", {CONF_ADAPTER: "kia_uvo"})
    discovered = [
        DiscoveredVehicle(
            vehicle_id="vehicle-1",
            title="Kia EV6",
            payload={"vehicle_id": "vehicle-1"},
        ),
        DiscoveredVehicle(
            vehicle_id="vehicle-2",
            title="Hyundai Kona",
            payload={"vehicle_id": "vehicle-2"},
        ),
    ]

    async def _noop_register_services(_hass) -> None:
        return None

    async def _fake_discover(_hass, _entry):
        return discovered

    async def _fake_create(_hass, adapter_type, discovered_vehicle):
        assert adapter_type == "kia_uvo"
        return _FakeAdapter(discovered_vehicle.vehicle_id, discovered_vehicle.title)

    tracked_state_listeners: list[tuple[tuple[str, ...], object]] = []

    def _fake_track_state_change_event(_hass, entity_ids, action):
        tracked_state_listeners.append((tuple(entity_ids), action))
        return action

    monkeypatch.setattr(vehicle_module, "async_register_services", _noop_register_services)
    monkeypatch.setattr(vehicle_module, "_discover_entry_vehicles", _fake_discover)
    monkeypatch.setattr(
        vehicle_module,
        "create_adapter_from_discovered_vehicle",
        _fake_create,
    )
    monkeypatch.setattr(
        vehicle_module,
        "async_track_state_change_event",
        _fake_track_state_change_event,
    )

    result = asyncio.run(async_setup_entry(hass, entry))

    assert result is True
    assert len(hass.data[DOMAIN][entry.entry_id][DATA_VEHICLES]) == 2
    assert hass.data[DOMAIN][DATA_DISCOVERY_SNAPSHOTS][entry.entry_id] == [
        "vehicle-1",
        "vehicle-2",
    ]
    assert len(hass.bus.listeners) == 1
    assert tracked_state_listeners == [
        (("sensor.vehicle-1_source",), tracked_state_listeners[0][1]),
        (("sensor.vehicle-2_source",), tracked_state_listeners[1][1]),
    ]
    assert hass.config_entries.forwarded == [
        (
            "entry-1",
            ("sensor", "binary_sensor", "lock", "switch", "device_tracker", "button"),
        )
    ]

    _, callback = hass.bus.listeners[0]
    asyncio.run(callback(object()))

    assert hass.config_entries.reloads == ["entry-1"]


def test_normalize_entry_adapter_key_migrates_renamed_kia_mapping() -> None:
    """Existing config entries should be rewritten to the renamed kia_uvo key."""

    hass = _FakeHass(is_running=True)
    entry = _FakeEntry("entry-1", {CONF_ADAPTER: "hyundai_kia_connect_kia_uvo"})

    normalized = asyncio.run(_normalize_entry_adapter_key(hass, entry))

    assert normalized == "kia_uvo"
    assert entry.data[CONF_ADAPTER] == "kia_uvo"
    assert hass.config_entries.updated == [(entry, {CONF_ADAPTER: "kia_uvo"})]


def test_refresh_vehicle_entry_updates_normalized_data_without_actions() -> None:
    """Source-state refresh should rebuild normalized data and fan out entity updates."""

    adapter = _FakeAdapter("vehicle-1", "Kia EV6")

    class _Entity:
        def __init__(self) -> None:
            self.updated = None
            self.write_calls = 0

        def update_normalized_data(self, normalized_data) -> None:
            self.updated = normalized_data

        def async_write_ha_state(self) -> None:
            self.write_calls += 1

    entity = _Entity()
    entry_data = {
        "adapter": adapter,
        "entities": [entity],
        "normalized_data": None,
    }

    asyncio.run(_refresh_vehicle_entry(entry_data))

    assert adapter.raw_state_calls == 1
    assert adapter.raw_metrics_calls == 1
    assert adapter.capability_calls == 1
    assert entry_data["normalized_data"] is not None
    assert entity.updated is entry_data["normalized_data"]
    assert entity.write_calls == 1


def test_refresh_vehicle_entry_emits_capability_state_changed_events() -> None:
    """Refreshes should emit generic state events for changed capability values."""

    hass = _FakeHass(is_running=True)
    adapter = _FakeAdapter("vehicle-1", "Kia EV6")

    class _Entity:
        def update_normalized_data(self, normalized_data) -> None:
            _ = normalized_data

        def async_write_ha_state(self) -> None:
            return None

    previous = normalize_vehicle_data(
        {
            "vehicle_id": "vehicle-1",
            "name": "Kia EV6",
            "manufacturer": "Kia",
            "model": "Unknown",
            "vehicle_type": "ev",
            "status": "parked",
            "available": True,
            "backend_online": True,
            "has_error": False,
            "driving": False,
            "ev_charging": False,
            "ev_plugged_in": False,
            "locked": False,
            "climate_active": False,
        },
        {
            "ev_battery_level": 60.0,
            "driving_range": 200.0,
            "openings": {},
            "source_units": {"distance_unit": "km"},
        },
        asyncio.run(adapter.get_capabilities()),
    )
    entry_data = {
        "adapter": adapter,
        "entities": [_Entity()],
        "normalized_data": previous,
    }

    from custom_components.my_vehicles import events as events_module

    class _NoDeviceRegistry:
        def async_get_device(self, identifiers=None, connections=None):
            _ = identifiers, connections
            return None

    events_module.dr.async_get = lambda _hass: _NoDeviceRegistry()
    asyncio.run(_refresh_vehicle_entry(entry_data, hass=hass))

    assert hass.bus.fired == [
        (
            EVENT_STATE_CHANGED,
            {
                "device_id": None,
                "vehicle_id": "vehicle-1",
                "capability": "central_locking",
                "old_value": False,
                "new_value": True,
            },
        )
    ]


def test_snapshot_vehicle_ids_ignores_invalid_entries() -> None:
    """Vehicle snapshots should only include valid normalized vehicle ids."""

    class _Info:
        def __init__(self, vehicle_id: str) -> None:
            self.vehicle_id = vehicle_id

    class _Normalized:
        def __init__(self, vehicle_id: str) -> None:
            self.info = _Info(vehicle_id)

    snapshot = _snapshot_vehicle_ids(
        [
            {"normalized_data": _Normalized("vehicle-1")},
            {"normalized_data": _Normalized("vehicle-2")},
            {"normalized_data": _Normalized("")},
            {"normalized_data": object()},
            object(),
        ]
    )

    assert snapshot == {"vehicle-1", "vehicle-2"}


def test_log_vehicle_reconciliation_reports_changes(caplog) -> None:
    """Reconciliation logging should describe added, removed, and kept vehicles."""

    entry = _FakeEntry("entry-1")

    with caplog.at_level(logging.INFO):
        _log_vehicle_reconciliation(
            entry,
            "kia_uvo",
            {"vehicle-1", "removed-vehicle"},
            {"vehicle-1", "vehicle-2"},
        )

    assert "added=['vehicle-2']" in caplog.text
    assert "removed=['removed-vehicle']" in caplog.text
    assert "kept=['vehicle-1']" in caplog.text


def test_log_vehicle_reconciliation_reports_unchanged_entries(caplog) -> None:
    """Unchanged reconciliation should stay on the debug path."""

    entry = _FakeEntry("entry-1")

    with caplog.at_level(logging.DEBUG):
        _log_vehicle_reconciliation(
            entry,
            "kia_uvo",
            {"vehicle-1"},
            {"vehicle-1"},
        )

    assert "is unchanged" in caplog.text
    assert "vehicle-1" in caplog.text
