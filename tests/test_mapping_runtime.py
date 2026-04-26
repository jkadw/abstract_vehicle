"""Tests for the generic adapter mapping runtime."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from custom_components.my_vehicles.mappings.schema import load_adapter_mapping
from custom_components.my_vehicles.runtime.base import UnsupportedVehicleActionError
from custom_components.my_vehicles.runtime.runtime import MappingRuntime


class _StateStore(dict):
    def get(self, entity_id: str):
        return super().get(entity_id)


class _FakeHass:
    def __init__(self, states: dict[str, SimpleNamespace]):
        self.states = _StateStore(states)
        self.services = _ServiceRegistry()


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


def test_mapping_runtime_resolves_direct_state_aggregation_template_and_actions() -> None:
    """The runtime should resolve the main v1 mapping modes without executing actions."""

    mapping = load_adapter_mapping("hyundai_kia_connect_kia_uvo")
    hass = _FakeHass(
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
                attributes={"latitude": 1.0, "longitude": 2.0},
            ),
            "sensor.santa_fe_ev_battery_level": SimpleNamespace(
                state="76.5", attributes={"unit_of_measurement": "%"}
            ),
            "sensor.santa_fe_total_driving_range": SimpleNamespace(
                state="42", attributes={"unit_of_measurement": "km"}
            ),
            "sensor.santa_fe_odometer": SimpleNamespace(
                state="12001", attributes={"unit_of_measurement": "km"}
            ),
        }
    )

    runtime = MappingRuntime(
        hass,
        mapping,
        vehicle="santa_fe",
        device="device-123",
    )
    resolved = runtime.resolve()

    assert resolved.capability_states["lock_vehicle"] == "locked"
    assert resolved.capability_states["windows"] is True
    assert resolved.capability_states["location"] == "home"
    assert resolved.capability_states["battery_level"] == "76.5"
    assert resolved.capability_states["driving_range"] == "42"
    assert resolved.capability_states["odometer"] == "12001"
    assert resolved.capability_states["range_warning"] is True
    assert resolved.capabilities.lock_vehicle.state_supported is True
    assert resolved.capabilities.windows.state_supported is True
    assert resolved.capabilities.refresh.action_supported is True
    assert resolved.actions["lock_vehicle"]["lock"].service == "kia_uvo.lock"
    assert (
        resolved.actions["lock_vehicle"]["lock"].data["device_id"] == "device-123"
    )
    assert resolved.actions["windows"]["open"].service == "kia_uvo.set_windows"
    assert resolved.actions["windows"]["open"].data["device_id"] == "device-123"
    assert resolved.actions["windows"]["open"].data["flwindow"] == "1"
    assert resolved.actions["refresh"]["refresh"].service == "button.press"
    assert (
        resolved.actions["refresh"]["refresh"].data["entity_id"]
        == "button.santa_fe_santa_fe_force_refresh"
    )


def test_mapping_runtime_executes_mapped_actions_via_ha_services() -> None:
    """Mapped actions should call HA services with substituted placeholders."""

    mapping = load_adapter_mapping("hyundai_kia_connect_kia_uvo")
    hass = _FakeHass({})
    runtime = MappingRuntime(
        hass,
        mapping,
        vehicle="santa_fe",
        device="device-123",
    )

    result = asyncio.run(runtime.async_execute_action("windows", "open"))

    assert result["success"] is True
    assert result["action"] == "open"
    assert hass.services.calls == [
        {
            "domain": "kia_uvo",
            "service": "set_windows",
            "service_data": {
                "device_id": "device-123",
                "flwindow": "1",
                "frwindow": "1",
                "rrwindow": "1",
                "rlwindow": "1",
            },
            "target": None,
            "blocking": True,
        }
    ]


def test_mapping_runtime_rejects_unknown_mapped_actions() -> None:
    """Unsupported mapped actions should fail with a clear adapter-level error."""

    mapping = load_adapter_mapping("hyundai_kia_connect_kia_uvo")
    runtime = MappingRuntime(
        _FakeHass({}),
        mapping,
        vehicle="santa_fe",
        device="device-123",
    )

    try:
        asyncio.run(runtime.async_execute_action("windows", "tilt"))
    except UnsupportedVehicleActionError as err:
        assert "Unsupported action 'tilt'" in str(err)
    else:  # pragma: no cover - explicit failure path for plain asserts
        raise AssertionError("UnsupportedVehicleActionError was not raised")
