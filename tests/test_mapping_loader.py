"""Tests for adapter mapping loading and validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from custom_components.vehicle.adapters.loader import _load_adapter_class
from custom_components.vehicle.adapters.mapping import (
    MappingValidationError,
    load_adapter_mapping,
    load_mapping_file,
)
from custom_components.vehicle.adapters.mapped import MappedVehicleAdapter
from custom_components.vehicle.adapters.registry import get_adapter_definition


def test_load_adapter_mapping_for_kia_yaml() -> None:
    """The Hyundai/Kia example mapping should load successfully."""

    mapping = load_adapter_mapping("hyundai_kia_connect_kia_uvo")

    assert mapping.integration.domain == "kia_uvo"
    assert mapping.integration.friendly_name == "Hyundai / Kia Connect"
    assert "lock" in mapping.capabilities
    assert mapping.capability("lock") is not None
    assert mapping.capability("lock").actions["lock"].action == "lock"
    assert mapping.capability("windows").actions["open"].action == "set_windows"
    assert mapping.capability("windows").state.any == (
        "binary_sensor.{vehicle}_front_left_window",
        "binary_sensor.{vehicle}_front_right_window",
        "binary_sensor.{vehicle}_rear_left_window",
        "binary_sensor.{vehicle}_rear_right_window",
    )
    assert mapping.metric("range").state == "sensor.{vehicle}_total_driving_range"
    assert mapping.derived_entity("range_warning").domain == "binary_sensor"


def test_load_mapping_file_rejects_missing_integration(tmp_path: Path) -> None:
    """A mapping without integration metadata should fail validation."""

    mapping_path = tmp_path / "invalid.yaml"
    mapping_path.write_text(
        """
capabilities:
  lock:
    state: lock.{vehicle}_door_lock
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(MappingValidationError, match="integration"):
        load_mapping_file(mapping_path)


def test_load_mapping_file_rejects_multiple_state_modes(tmp_path: Path) -> None:
    """One mapping block may not declare multiple state modes."""

    mapping_path = tmp_path / "invalid_modes.yaml"
    mapping_path.write_text(
        """
integration:
  domain: kia_uvo
  friendly_name: Hyundai / Kia Connect
capabilities:
  windows:
    state: binary_sensor.{vehicle}_front_left_window
    any:
      - binary_sensor.{vehicle}_front_left_window
      - binary_sensor.{vehicle}_front_right_window
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(MappingValidationError, match="only one of state/template/any/all"):
        load_mapping_file(mapping_path)


def test_load_mapping_file_allows_simple_state_without_any_or_all(tmp_path: Path) -> None:
    """Missing optional any/all fields should not fail simple state mappings."""

    mapping_path = tmp_path / "simple_state.yaml"
    mapping_path.write_text(
        """
integration:
  domain: kia_uvo
  friendly_name: Hyundai / Kia Connect
capabilities:
  lock:
    state: lock.{vehicle}_door_lock
    actions:
      lock:
        action: lock
        data:
          device_id: "{device}"
""".strip(),
        encoding="utf-8",
    )

    mapping = load_mapping_file(mapping_path)

    assert mapping.capability("lock") is not None
    assert mapping.capability("lock").state is not None
    assert mapping.capability("lock").state.state == "lock.{vehicle}_door_lock"


def test_registry_builds_generic_mapped_adapter_class_for_kia() -> None:
    """Mapped adapter definitions should resolve to a configured generic adapter class."""

    definition = get_adapter_definition("kia_uvo")
    assert definition is not None

    adapter_class = _load_adapter_class(definition)

    assert issubclass(adapter_class, MappedVehicleAdapter)
    assert adapter_class.mapping_name == "hyundai_kia_connect_kia_uvo"
    assert adapter_class.get_friendly_name() == "Hyundai / Kia Connect"
