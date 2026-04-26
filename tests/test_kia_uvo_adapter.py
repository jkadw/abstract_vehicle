"""Tests for the kia_uvo-backed mapped adapter."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from custom_components.my_vehicles.runtime.loader import _load_adapter_class
from custom_components.my_vehicles.runtime.registry import get_adapter_definition
from custom_components.my_vehicles.runtime.base import UnsupportedVehicleActionError
from custom_components.my_vehicles.domain.normalization import (
    normalize_vehicle_data,
)


class _StateStore(dict):
    def get(self, entity_id: str):
        return super().get(entity_id)


class _ServiceRegistry:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def async_call(
        self,
        domain: str,
        service: str,
        *,
        service_data=None,
        target=None,
        blocking: bool = False,
    ) -> None:
        self.calls.append(
            {
                "domain": domain,
                "service": service,
                "service_data": service_data,
                "target": target,
                "blocking": blocking,
            }
        )


class _FakeHass:
    def __init__(self, states: dict[str, SimpleNamespace]):
        self.states = _StateStore(states)
        self.services = _ServiceRegistry()
        self.is_running = False

    async def async_add_executor_job(self, func, *args):
        return func(*args)


class _Device:
    def __init__(
        self,
        device_id: str,
        *,
        identifiers,
        name: str,
        manufacturer: str,
        model: str = "EV6",
    ) -> None:
        self.id = device_id
        self.identifiers = identifiers
        self.name = name
        self.name_by_user = None
        self.manufacturer = manufacturer
        self.model = model


class _DeviceRegistry:
    def __init__(self, devices: dict[str, _Device]) -> None:
        self.devices = devices


class _EntityEntry:
    def __init__(self, entity_id: str, device_id: str) -> None:
        self.entity_id = entity_id
        self.device_id = device_id


class _EntityRegistry:
    def __init__(self, entities: dict[str, _EntityEntry]) -> None:
        self.entities = entities


def _configured_vehicles() -> list[dict]:
    return [
        {
            "vehicle_id": "kia-1",
            "name": "Kia EV6",
            "manufacturer": "Kia",
            "model": "EV6",
            "vehicle_type": "ev",
            "source_vehicle": "santa_fe",
            "source_device_id": "device-123",
            "available": True,
            "backend_online": True,
            "has_error": False,
            "driving": False,
            "ev_plugged_in": True,
        }
    ]


def _fake_hass() -> _FakeHass:
    return _FakeHass(
        {
            "lock.santa_fe_door_lock": SimpleNamespace(state="locked", attributes={}),
            "binary_sensor.santa_fe_front_left_window": SimpleNamespace(
                state="off", attributes={}
            ),
            "binary_sensor.santa_fe_front_right_window": SimpleNamespace(
                state="on", attributes={}
            ),
            "binary_sensor.santa_fe_rear_left_window": SimpleNamespace(
                state="off", attributes={}
            ),
            "binary_sensor.santa_fe_rear_right_window": SimpleNamespace(
                state="off", attributes={}
            ),
            "device_tracker.santa_fe_location": SimpleNamespace(
                state="home",
                attributes={"latitude": 33.7490, "longitude": -84.3880},
            ),
            "sensor.santa_fe_ev_battery_level": SimpleNamespace(
                state="61.5", attributes={"unit_of_measurement": "%"}
            ),
            "sensor.santa_fe_total_driving_range": SimpleNamespace(
                state="198", attributes={"unit_of_measurement": "mi"}
            ),
            "sensor.santa_fe_odometer": SimpleNamespace(
                state="12450", attributes={"unit_of_measurement": "mi"}
            ),
            "button.santa_fe_santa_fe_force_refresh": SimpleNamespace(
                state="unknown",
                attributes={},
            ),
        }
    )


def _patch_registries(monkeypatch, hass: _FakeHass, identifiers) -> None:
    from custom_components.my_vehicles.runtime import discovery as discovery_module

    device = _Device(
        "device-123",
        identifiers=identifiers,
        name="Kia EV6",
        manufacturer="Kia",
    )
    entities = {
        entity_id: _EntityEntry(entity_id, "device-123")
        for entity_id in hass.states.keys()
    }

    monkeypatch.setattr(
        discovery_module.dr,
        "async_get",
        lambda _hass: _DeviceRegistry({"device-123": device}),
        raising=False,
    )
    monkeypatch.setattr(
        discovery_module.er,
        "async_get",
        lambda _hass: _EntityRegistry(entities),
        raising=False,
    )


def _kia_uvo_adapter_class():
    definition = get_adapter_definition("hyundai_kia_connect_kia_uvo")
    assert definition is not None
    return _load_adapter_class(definition)


def test_kia_uvo_adapter_discovers_vehicle_generically(monkeypatch) -> None:
    """The adapter should discover vehicles via integration.domain and mapping patterns."""

    hass = _fake_hass()
    _patch_registries(monkeypatch, hass, {("kia_uvo", "kia-1")})

    discovered = asyncio.run(_kia_uvo_adapter_class().async_discover_vehicles(hass))

    assert len(discovered) == 1
    assert discovered[0].vehicle_id == "kia-1"
    assert discovered[0].title == "Kia EV6"
    assert discovered[0].payload["model"] == "EV6"
    assert discovered[0].payload["source_vehicle"] == "santa_fe"
    assert discovered[0].payload["source_device_id"] == "device-123"


def test_kia_uvo_adapter_maps_selected_vehicle_via_generic_mapping() -> None:
    """The adapter should build raw data from the generic mapped runtime."""

    adapter = _kia_uvo_adapter_class()(
        hass=_fake_hass(),
        vehicles=_configured_vehicles(),
        vehicle_id="kia-1",
    )

    raw_state = asyncio.run(adapter.get_raw_state())
    raw_metrics = asyncio.run(adapter.get_raw_metrics())
    capabilities = asyncio.run(adapter.get_capabilities())

    assert raw_state["vehicle_id"] == "kia-1"
    assert raw_state["manufacturer"] == "Kia"
    assert raw_state["model"] == "EV6"
    assert raw_state["status"] == "parked"
    assert raw_state["locked"] is True
    assert raw_metrics["ev_battery_level"] == 61.5
    assert raw_metrics["driving_range"] == 198.0
    assert raw_metrics["latitude"] == 33.749
    assert raw_metrics["openings"]["santa_fe_front_right_window"] == "open"
    assert capabilities.lock_vehicle.action_supported is True
    assert capabilities.windows.state_supported is True
    assert capabilities.refresh.action_supported is True


def test_kia_uvo_adapter_relies_on_normalization_for_canonical_outputs() -> None:
    """Mapped raw values should normalize into the unified capability model."""

    adapter = _kia_uvo_adapter_class()(
        hass=_fake_hass(),
        vehicles=_configured_vehicles(),
        vehicle_id="kia-1",
    )
    normalized = normalize_vehicle_data(
        asyncio.run(adapter.get_raw_state()),
        asyncio.run(adapter.get_raw_metrics()),
        asyncio.run(adapter.get_capabilities()),
    )

    assert normalized.state.value == "parked"
    assert normalized.driving_range == 198.0
    assert normalized.odometer == 12450.0
    assert normalized.capabilities.location.state_supported is True
    assert normalized.capabilities.ev_battery_level.state_supported is True


def test_kia_uvo_adapter_executes_supported_actions_via_mapping_runtime() -> None:
    """Mapped actions should execute via HA services rather than OEM-specific code."""

    hass = _fake_hass()
    adapter = _kia_uvo_adapter_class()(
        hass=hass,
        vehicles=_configured_vehicles(),
        vehicle_id="kia-1",
    )

    asyncio.run(adapter.execute_action("unlock"))
    asyncio.run(adapter.execute_action("start_heating"))
    asyncio.run(adapter.execute_action("refresh"))

    assert hass.services.calls == [
        {
            "domain": "kia_uvo",
            "service": "unlock",
            "service_data": {"device_id": "device-123"},
            "target": None,
            "blocking": True,
        },
        {
            "domain": "kia_uvo",
            "service": "start_climate",
            "service_data": {
                "device_id": "device-123",
                "temperature": 23,
                "duration": 10,
                "climate": True,
                "heating": "4",
                "flseat": "7",
                "frseat": "7",
            },
            "target": None,
            "blocking": True,
        },
        {
            "domain": "kia_uvo",
            "service": "force_update",
            "service_data": {"device_id": "device-123"},
            "target": None,
            "blocking": True,
        },
    ]

    with pytest.raises(UnsupportedVehicleActionError):
        asyncio.run(adapter.execute_action("start_climate"))


def test_kia_uvo_adapter_exposes_read_only_diagnostics() -> None:
    """Mapped adapters should expose detailed diagnostics without executing actions."""

    adapter = _kia_uvo_adapter_class()(
        hass=_fake_hass(),
        vehicles=_configured_vehicles(),
        vehicle_id="kia-1",
    )

    diagnostics = asyncio.run(adapter.get_diagnostics())

    assert diagnostics["adapter_type"] == "mapped"
    assert diagnostics["mapping_name"] == "hyundai_kia_connect_kia_uvo"
    assert diagnostics["integration_domain"] == "kia_uvo"
    assert diagnostics["source_vehicle"] == "santa_fe"
    assert diagnostics["raw_state"]["vehicle_id"] == "kia-1"
    assert diagnostics["raw_metrics"]["driving_range"] == 198.0
    assert diagnostics["capabilities"]["refresh"]["action_supported"] is True
    assert diagnostics["actions"]["windows"]["open"]["service"] == "kia_uvo.set_windows"
    assert (
        diagnostics["source_entities"]["lock.santa_fe_door_lock"]["exists"]
        is True
    )
    assert (
        diagnostics["source_entities"]["sensor.santa_fe_total_driving_range"]["attributes"][
            "unit_of_measurement"
        ]
        == "mi"
    )


def test_kia_uvo_discovery_ignores_malformed_identifier_entries(monkeypatch) -> None:
    """Generic discovery should not crash on unexpected identifier shapes."""

    hass = _fake_hass()
    _patch_registries(
        monkeypatch,
        hass,
        {
            ("other_domain", "ignore-me"),
            ("kia_uvo", "vehicle-123"),
            ("kia_uvo", ""),
            ("broken",),
            "not-a-tuple",
        },
    )

    discovered = asyncio.run(_kia_uvo_adapter_class().async_discover_vehicles(hass))

    assert discovered[0].vehicle_id == "vehicle-123"
