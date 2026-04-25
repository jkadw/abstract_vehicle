"""Tests for adapter mapping loading and validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from custom_components.vehicle.adapters.mapping import (
    MappingValidationError,
    load_adapter_mapping,
    load_mapping_file,
)


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
