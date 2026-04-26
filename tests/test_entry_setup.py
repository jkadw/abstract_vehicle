"""Tests for entry setup, reconciliation, and startup behavior."""

from __future__ import annotations

import asyncio
import logging

import pytest

from custom_components.my_vehicles.setup.entry import (
    _log_vehicle_reconciliation,
    _snapshot_vehicle_ids,
    async_setup_entry,
)
from custom_components.my_vehicles.runtime.base import DiscoveredVehicle
from custom_components.my_vehicles.const import (
    CONF_ADAPTER,
    DATA_DISCOVERY_SNAPSHOTS,
    DATA_VEHICLES,
    DOMAIN,
)
from custom_components.my_vehicles.domain.model import VehicleCapabilities


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

    def async_listen_once(self, event_type: str, callback):
        self.listeners.append((event_type, callback))
        return callback


class _FakeConfigEntries:
    def __init__(self) -> None:
        self.forwarded: list[tuple[str, tuple[str, ...]]] = []
        self.reloads: list[str] = []

    async def async_forward_entry_setups(self, entry, platforms) -> None:
        self.forwarded.append((entry.entry_id, tuple(platforms)))

    async def async_reload(self, entry_id: str) -> None:
        self.reloads.append(entry_id)


class _FakeHass:
    def __init__(self, *, is_running: bool) -> None:
        self.data: dict[str, object] = {}
        self.is_running = is_running
        self.bus = _FakeBus()
        self.config_entries = _FakeConfigEntries()


class _FakeAdapter:
    def __init__(self, vehicle_id: str, name: str) -> None:
        self._vehicle_id = vehicle_id
        self._name = name

    async def get_raw_state(self) -> dict[str, object]:
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
            "charging_active": False,
            "charging_plugged": False,
            "locked": True,
            "climate_active": False,
        }

    async def get_raw_metrics(self) -> dict[str, object]:
        return {
            "battery_level": 60.0,
            "range": 200.0,
            "openings": {},
            "source_units": {"distance_unit": "km"},
        }

    async def get_capabilities(self) -> VehicleCapabilities:
        return VehicleCapabilities()


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

    monkeypatch.setattr(vehicle_module, "async_register_services", _noop_register_services)
    monkeypatch.setattr(vehicle_module, "_discover_entry_vehicles", _fake_discover)
    monkeypatch.setattr(
        vehicle_module,
        "create_adapter_from_discovered_vehicle",
        _fake_create,
    )

    result = asyncio.run(async_setup_entry(hass, entry))

    assert result is True
    assert len(hass.data[DOMAIN][entry.entry_id][DATA_VEHICLES]) == 2
    assert hass.data[DOMAIN][DATA_DISCOVERY_SNAPSHOTS][entry.entry_id] == [
        "vehicle-1",
        "vehicle-2",
    ]
    assert len(hass.bus.listeners) == 1
    assert hass.config_entries.forwarded == [
        (
            "entry-1",
            ("sensor", "binary_sensor", "lock", "switch", "device_tracker", "button"),
        )
    ]

    _, callback = hass.bus.listeners[0]
    asyncio.run(callback(object()))

    assert hass.config_entries.reloads == ["entry-1"]


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
