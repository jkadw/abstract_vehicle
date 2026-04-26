"""Tests for the generic adapter mapping runtime."""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

from custom_components.my_vehicles.mappings.schema import (
    load_adapter_mapping,
    load_mapping_file,
)
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


def test_mapping_runtime_resolves_optional_action_availability(tmp_path: Path) -> None:
    """Mapped actions may carry an optional state-like availability block."""

    mapping_path = tmp_path / "availability.yaml"
    mapping_path.write_text(
        """
integration:
  domain: kia_uvo
  friendly_name: Hyundai / Kia Connect
capabilities:
  lock_vehicle:
    state:
      unavailable: true
  climate:
    state:
      unavailable: true
  charging:
    state:
      unavailable: true
  horn:
    state:
      unavailable: true
  flash_lights:
    state:
      unavailable: true
  hazard_lights:
    state:
      unavailable: true
  location:
    state:
      unavailable: true
  ignition:
    state:
      unavailable: true
  driving_range:
    state:
      unavailable: true
  range_warning:
    state:
      unavailable: true
  odometer:
    state:
      unavailable: true
  tire_pressure:
    state:
      unavailable: true
  warning_messages:
    state:
      unavailable: true
  info_messages:
    state:
      unavailable: true
  windows:
    state:
      any:
        - binary_sensor.{vehicle}_front_left_window
    actions:
      open:
        action: kia_uvo.set_windows
        availability:
          entity: binary_sensor.{vehicle}_windows_available
        data:
          device_id: {device}
  doors:
    state:
      unavailable: true
  lids:
    state:
      unavailable: true
  battery_level:
    state:
      unavailable: true
  refresh:
    state:
      unavailable: true
""".strip(),
        encoding="utf-8",
    )

    mapping = load_mapping_file(mapping_path)
    hass = _FakeHass(
        {
            "binary_sensor.santa_fe_front_left_window": SimpleNamespace(
                state="off", attributes={}
            ),
            "binary_sensor.santa_fe_windows_available": SimpleNamespace(
                state="off", attributes={}
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

    assert resolved.actions["windows"]["open"].available is False
    assert runtime.is_action_available("windows", "open") is False


def test_mapping_runtime_resolves_optional_action_availability_not(
    tmp_path: Path,
) -> None:
    """Negated availability should avoid templates for simple boolean inversions."""

    mapping_path = tmp_path / "availability_not.yaml"
    mapping_path.write_text(
        """
integration:
  domain: kia_uvo
  friendly_name: Hyundai / Kia Connect
capabilities:
  lock_vehicle:
    state:
      unavailable: true
  climate:
    state:
      unavailable: true
  charging:
    state:
      unavailable: true
  horn:
    state:
      unavailable: true
  flash_lights:
    state:
      unavailable: true
  hazard_lights:
    state:
      unavailable: true
  location:
    state:
      unavailable: true
  ignition:
    state:
      unavailable: true
  driving_range:
    state:
      unavailable: true
  range_warning:
    state:
      unavailable: true
  odometer:
    state:
      unavailable: true
  tire_pressure:
    state:
      unavailable: true
  warning_messages:
    state:
      unavailable: true
  info_messages:
    state:
      unavailable: true
  windows:
    state:
      any:
        - binary_sensor.{vehicle}_front_left_window
    actions:
      open:
        action: kia_uvo.set_windows
        availability_not:
          entity: binary_sensor.{vehicle}_windows_blocked
        data:
          device_id: {device}
  doors:
    state:
      unavailable: true
  lids:
    state:
      unavailable: true
  battery_level:
    state:
      unavailable: true
  refresh:
    state:
      unavailable: true
""".strip(),
        encoding="utf-8",
    )

    mapping = load_mapping_file(mapping_path)
    hass = _FakeHass(
        {
            "binary_sensor.santa_fe_front_left_window": SimpleNamespace(
                state="off", attributes={}
            ),
            "binary_sensor.santa_fe_windows_blocked": SimpleNamespace(
                state="on", attributes={}
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

    assert resolved.actions["windows"]["open"].available is False
    assert runtime.is_action_available("windows", "open") is False


def test_mapping_runtime_source_snapshot_includes_action_availability_entities(
    tmp_path: Path,
) -> None:
    """Availability-only source entities should participate in refresh/diagnostics."""

    mapping_path = tmp_path / "availability_snapshot.yaml"
    mapping_path.write_text(
        """
integration:
  domain: kia_uvo
  friendly_name: Hyundai / Kia Connect
capabilities:
  lock_vehicle:
    state:
      unavailable: true
  climate:
    state:
      unavailable: true
  charging:
    state:
      unavailable: true
  horn:
    state:
      unavailable: true
  flash_lights:
    state:
      unavailable: true
  hazard_lights:
    state:
      unavailable: true
  location:
    state:
      unavailable: true
  ignition:
    state:
      unavailable: true
  driving_range:
    state:
      unavailable: true
  range_warning:
    state:
      unavailable: true
  odometer:
    state:
      unavailable: true
  tire_pressure:
    state:
      unavailable: true
  warning_messages:
    state:
      unavailable: true
  info_messages:
    state:
      unavailable: true
  windows:
    state:
      any:
        - binary_sensor.{vehicle}_front_left_window
    actions:
      open:
        action: kia_uvo.set_windows
        availability:
          entity: binary_sensor.{vehicle}_windows_available
        data:
          entity_id: binary_sensor.{vehicle}_windows_available
          device_id: {device}
  doors:
    state:
      unavailable: true
  lids:
    state:
      unavailable: true
  battery_level:
    state:
      unavailable: true
  refresh:
    state:
      unavailable: true
""".strip(),
        encoding="utf-8",
    )

    mapping = load_mapping_file(mapping_path)
    hass = _FakeHass(
        {
            "binary_sensor.santa_fe_front_left_window": SimpleNamespace(
                state="off", attributes={}
            ),
            "binary_sensor.santa_fe_windows_available": SimpleNamespace(
                state="on", attributes={}
            ),
        }
    )
    runtime = MappingRuntime(
        hass,
        mapping,
        vehicle="santa_fe",
        device="device-123",
    )

    snapshot = runtime.source_entity_snapshot()

    assert "binary_sensor.santa_fe_windows_available" in snapshot
    assert snapshot["binary_sensor.santa_fe_windows_available"]["exists"] is True
    assert len(snapshot) == 2


def test_mapping_runtime_source_snapshot_deduplicates_shared_source_entities(
    tmp_path: Path,
) -> None:
    """One source entity referenced more than once should still appear only once."""

    mapping_path = tmp_path / "dedupe_snapshot.yaml"
    mapping_path.write_text(
        """
integration:
  domain: kia_uvo
  friendly_name: Hyundai / Kia Connect
capabilities:
  lock_vehicle:
    state:
      unavailable: true
  climate:
    state:
      unavailable: true
  charging:
    state:
      unavailable: true
  horn:
    state:
      unavailable: true
  flash_lights:
    state:
      unavailable: true
  hazard_lights:
    state:
      unavailable: true
  location:
    state:
      unavailable: true
  ignition:
    state:
      unavailable: true
  driving_range:
    state:
      unavailable: true
  range_warning:
    state:
      unavailable: true
  odometer:
    state:
      unavailable: true
  tire_pressure:
    state:
      unavailable: true
  warning_messages:
    state:
      unavailable: true
  info_messages:
    state:
      unavailable: true
  windows:
    state:
      entity: binary_sensor.{vehicle}_windows_available
    actions:
      open:
        action: kia_uvo.set_windows
        availability:
          entity: binary_sensor.{vehicle}_windows_available
        data:
          entity_id: binary_sensor.{vehicle}_windows_available
          device_id: {device}
  doors:
    state:
      unavailable: true
  lids:
    state:
      unavailable: true
  battery_level:
    state:
      unavailable: true
  refresh:
    state:
      unavailable: true
""".strip(),
        encoding="utf-8",
    )

    mapping = load_mapping_file(mapping_path)
    hass = _FakeHass(
        {
            "binary_sensor.santa_fe_windows_available": SimpleNamespace(
                state="on", attributes={}
            ),
        }
    )
    runtime = MappingRuntime(
        hass,
        mapping,
        vehicle="santa_fe",
        device="device-123",
    )

    snapshot = runtime.source_entity_snapshot()

    assert list(snapshot) == ["binary_sensor.santa_fe_windows_available"]
