"""Tests for adapter mapping loading and validation."""

from __future__ import annotations

import asyncio
import importlib
from pathlib import Path

import pytest

import custom_components.my_vehicles.runtime as runtime_package
from custom_components.my_vehicles.runtime.loader import (
    _load_adapter_class,
    get_available_adapter_definitions,
    get_available_adapter_options,
)
from custom_components.my_vehicles.mappings.schema import (
    MappingValidationError,
    load_adapter_mapping,
    load_mapping_file,
)
from custom_components.my_vehicles.runtime.mapped import MappedVehicleAdapter
from custom_components.my_vehicles.runtime import registry as registry_module
from custom_components.my_vehicles.runtime.registry import (
    CUSTOM_ADAPTER_DEFINITIONS,
    get_adapter_definition,
    get_adapter_definitions,
)


_MINIMAL_CANONICAL_CAPABILITIES = """
capabilities:
  lock_vehicle:
    state:
      entity: lock.{vehicle}_door_lock
    actions:
      lock:
        action: kia_uvo.lock
        data:
          device_id: "{device}"
      unlock:
        action: kia_uvo.unlock
        data:
          device_id: "{device}"
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
      entity: device_tracker.{vehicle}_vehicle
  ignition:
    state:
      unavailable: true
  driving_range:
    state:
      entity: sensor.{vehicle}_total_driving_range
  range_warning:
    state:
      domain: binary_sensor
      template: "{{ states('sensor.{vehicle}_total_driving_range') | float < 50 }}"
  odometer:
    state:
      entity: sensor.{vehicle}_odometer
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
        - binary_sensor.{vehicle}_front_right_window
    actions:
      open:
        action: kia_uvo.set_windows
        data:
          device_id: "{device}"
  doors:
    state:
      unavailable: true
  lids:
    state:
      unavailable: true
  battery_level:
    state:
      entity: sensor.{vehicle}_ev_battery_level
  refresh:
    state:
      unavailable: true
    actions:
      refresh:
        action: button.press
        data:
          entity_id: button.{vehicle}_force_refresh
""".strip()


def test_load_adapter_mapping_for_kia_yaml() -> None:
    """The Hyundai/Kia example mapping should load successfully."""

    mapping = load_adapter_mapping("hyundai_kia_connect_kia_uvo")

    assert mapping.integration.domain == "kia_uvo"
    assert mapping.integration.friendly_name == "Hyundai / Kia Connect"
    assert "lock_vehicle" in mapping.capabilities
    assert mapping.capability("lock_vehicle") is not None
    assert mapping.capability("lock_vehicle").actions["lock"].action == "kia_uvo.lock"
    assert mapping.capability("windows").actions["open"].action == "kia_uvo.set_windows"
    assert mapping.capability("windows").state.any == (
        "binary_sensor.{vehicle}_front_left_window",
        "binary_sensor.{vehicle}_front_right_window",
        "binary_sensor.{vehicle}_rear_left_window",
        "binary_sensor.{vehicle}_rear_right_window",
    )
    assert (
        mapping.capability("driving_range").state.entity
        == "sensor.{vehicle}_total_driving_range"
    )
    assert mapping.capability("range_warning").state.domain == "binary_sensor"


def test_load_mapping_file_rejects_missing_integration(tmp_path: Path) -> None:
    """A mapping without integration metadata should fail validation."""

    mapping_path = tmp_path / "invalid.yaml"
    mapping_path.write_text(
        _MINIMAL_CANONICAL_CAPABILITIES,
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
"""
        + _MINIMAL_CANONICAL_CAPABILITIES.replace(
            """  windows:
    state:
      any:
        - binary_sensor.{vehicle}_front_left_window
        - binary_sensor.{vehicle}_front_right_window""",
            """  windows:
    state:
      entity: binary_sensor.{vehicle}_front_left_window
      any:
        - binary_sensor.{vehicle}_front_left_window
        - binary_sensor.{vehicle}_front_right_window""",
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        MappingValidationError,
        match="exactly one of entity/template/any/all/unavailable",
    ):
        load_mapping_file(mapping_path)


def test_load_mapping_file_requires_full_canonical_capability_set(tmp_path: Path) -> None:
    """Mappings must list every canonical capability explicitly."""

    mapping_path = tmp_path / "missing_caps.yaml"
    mapping_path.write_text(
        """
integration:
  domain: kia_uvo
  friendly_name: Hyundai / Kia Connect
capabilities:
  lock_vehicle:
    state:
      entity: lock.{vehicle}_door_lock
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(MappingValidationError, match="Missing canonical capabilities"):
        load_mapping_file(mapping_path)


def test_load_mapping_file_rejects_unknown_capability_name(tmp_path: Path) -> None:
    """Mappings may not invent capability names outside the registry."""

    mapping_path = tmp_path / "unknown_capability.yaml"
    mapping_path.write_text(
        """
integration:
  domain: kia_uvo
  friendly_name: Hyundai / Kia Connect
""".strip()
        + "\n"
        + _MINIMAL_CANONICAL_CAPABILITIES.replace(
            "capabilities:\n",
            "capabilities:\n  unknown_capability:\n    state:\n      unavailable: true\n",
            1,
        ),
        encoding="utf-8",
    )

    with pytest.raises(MappingValidationError, match="Unknown canonical capabilities"):
        load_mapping_file(mapping_path)


def test_load_mapping_file_rejects_old_metrics_section(tmp_path: Path) -> None:
    """Old top-level metrics are no longer supported."""

    mapping_path = tmp_path / "old_metrics.yaml"
    mapping_path.write_text(
        f"""
integration:
  domain: kia_uvo
  friendly_name: Hyundai / Kia Connect
{_MINIMAL_CANONICAL_CAPABILITIES}
metrics:
  range:
    state: sensor.{{vehicle}}_total_driving_range
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(MappingValidationError, match="metrics is not supported"):
        load_mapping_file(mapping_path)


def test_load_mapping_file_rejects_old_derived_section(tmp_path: Path) -> None:
    """Old top-level derived entities are no longer supported."""

    mapping_path = tmp_path / "old_derived.yaml"
    mapping_path.write_text(
        """
integration:
  domain: kia_uvo
  friendly_name: Hyundai / Kia Connect
""".strip()
        + "\n"
        + _MINIMAL_CANONICAL_CAPABILITIES
        + """
derived:
  range_warning:
    domain: binary_sensor
    template: "{{ states('sensor.{vehicle}_total_driving_range') | float < 50 }}"
""",
        encoding="utf-8",
    )

    with pytest.raises(MappingValidationError, match="derived is not supported"):
        load_mapping_file(mapping_path)


def test_load_mapping_file_rejects_invalid_action_verb(tmp_path: Path) -> None:
    """Action verbs must match the canonical verbs for that capability."""

    mapping_path = tmp_path / "bad_action_verb.yaml"
    mapping_path.write_text(
        """
integration:
  domain: kia_uvo
  friendly_name: Hyundai / Kia Connect
"""
        + _MINIMAL_CANONICAL_CAPABILITIES.replace(
            """    actions:
      open:
        action: kia_uvo.set_windows""",
            """    actions:
      lock:
        action: kia_uvo.set_windows""",
            1,
        ),
        encoding="utf-8",
    )

    with pytest.raises(MappingValidationError, match="not a valid canonical verb"):
        load_mapping_file(mapping_path)


def test_load_mapping_file_requires_fully_qualified_action(tmp_path: Path) -> None:
    """Actions must now be explicit domain.service strings."""

    mapping_path = tmp_path / "short_action.yaml"
    mapping_path.write_text(
        f"""
integration:
  domain: kia_uvo
  friendly_name: Hyundai / Kia Connect
{_MINIMAL_CANONICAL_CAPABILITIES.replace("kia_uvo.lock", "lock")}
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(MappingValidationError, match="fully qualified domain.service"):
        load_mapping_file(mapping_path)


def test_load_mapping_file_parses_action_availability_block(tmp_path: Path) -> None:
    """Action mappings may optionally define availability with state-like syntax."""

    mapping_path = tmp_path / "action_availability.yaml"
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
          device_id: "{device}"
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

    assert (
        mapping.capability("windows").actions["open"].availability is not None
    )
    assert (
        mapping.capability("windows").actions["open"].availability.entity
        == "binary_sensor.{vehicle}_windows_available"
    )


def test_load_mapping_file_parses_action_availability_not_block(tmp_path: Path) -> None:
    """Action mappings may optionally define negated availability."""

    mapping_path = tmp_path / "action_availability_not.yaml"
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
          device_id: "{device}"
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

    assert (
        mapping.capability("windows").actions["open"].availability_not is not None
    )
    assert (
        mapping.capability("windows").actions["open"].availability_not.entity
        == "binary_sensor.{vehicle}_windows_blocked"
    )


def test_load_mapping_file_rejects_both_availability_forms(tmp_path: Path) -> None:
    """One verb may not define both availability forms at once."""

    mapping_path = tmp_path / "bad_action_availability.yaml"
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
        availability_not:
          entity: binary_sensor.{vehicle}_windows_blocked
        data:
          device_id: "{device}"
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

    with pytest.raises(MappingValidationError, match="may not define both"):
        load_mapping_file(mapping_path)


def test_load_mapping_file_parses_nested_state_block(tmp_path: Path) -> None:
    """Simple nested entity state mappings should load cleanly."""

    mapping_path = tmp_path / "simple_state.yaml"
    mapping_path.write_text(
        f"""
integration:
  domain: kia_uvo
  friendly_name: Hyundai / Kia Connect
{_MINIMAL_CANONICAL_CAPABILITIES}
""".strip(),
        encoding="utf-8",
    )

    mapping = load_mapping_file(mapping_path)

    assert mapping.capability("lock_vehicle") is not None
    assert (
        mapping.capability("lock_vehicle").state.entity
        == "lock.{vehicle}_door_lock"
    )


def test_runtime_package_exports_config_flow_dependencies() -> None:
    """The runtime package must re-export helpers used by config_flow."""

    assert runtime_package.get_available_adapter_options is get_available_adapter_options
    assert runtime_package.get_available_adapter_definitions is get_available_adapter_definitions


def test_config_flow_module_imports_cleanly() -> None:
    """Importing the config flow should not fail due to broken package exports."""

    module = importlib.import_module("custom_components.my_vehicles.config_flow")

    assert module is not None
    assert getattr(module, "VehicleConfigFlow", None) is not None


def test_registry_discovers_adapter_definition_from_mapping_yaml() -> None:
    """Adapter definitions should be discovered directly from mapping files."""

    definitions = get_adapter_definitions()

    assert any(
        definition.key == "hyundai_kia_connect_kia_uvo" for definition in definitions
    )

    definition = get_adapter_definition("hyundai_kia_connect_kia_uvo")
    assert definition is not None
    assert definition.kind == "mapping"
    assert definition.mapping_name == "hyundai_kia_connect_kia_uvo"
    assert definition.source_integration == "kia_uvo"
    assert definition.fallback_label == "Hyundai / Kia Connect"


def test_registry_has_explicit_custom_adapter_extension_point() -> None:
    """Non-mapping adapters should remain behind an explicit extension hook."""

    assert CUSTOM_ADAPTER_DEFINITIONS == ()


def test_registry_builds_generic_mapped_adapter_class_for_discovered_mapping() -> None:
    """Discovered mapping definitions should resolve to a configured generic adapter class."""

    definition = get_adapter_definition("hyundai_kia_connect_kia_uvo")
    assert definition is not None

    adapter_class = _load_adapter_class(definition)

    assert issubclass(adapter_class, MappedVehicleAdapter)
    assert adapter_class.mapping_name == "hyundai_kia_connect_kia_uvo"
    assert adapter_class.get_friendly_name() == "Hyundai / Kia Connect"


def test_registry_does_not_support_integration_domain_alias_lookup() -> None:
    """Adapter definitions should now resolve only by mapping filename key."""

    definition = get_adapter_definition("kia_uvo")

    assert definition is None


def test_registry_discovers_additional_mapping_yaml_without_python_changes(
    tmp_path: Path, monkeypatch
) -> None:
    """A new mapping YAML should become an adapter with no registry edits."""

    extra_mapping = tmp_path / "example_oem.yaml"
    extra_mapping.write_text(
        f"""
integration:
  domain: example_oem
  friendly_name: Example OEM
{_MINIMAL_CANONICAL_CAPABILITIES.replace("kia_uvo", "example_oem").replace("Hyundai / Kia Connect", "Example OEM")}
""".strip(),
        encoding="utf-8",
    )

    monkeypatch.setattr(registry_module, "_mapping_directory", lambda: tmp_path)

    definitions = get_adapter_definitions()

    assert len(definitions) == 1
    assert definitions[0].key == "example_oem"
    assert definitions[0].fallback_label == "Example OEM"
    assert definitions[0].source_integration == "example_oem"


class _FakeConfig:
    def __init__(self, components: set[str] | None = None) -> None:
        self.components = components or set()


class _FakeConfigEntries:
    def __init__(self, entries_by_domain: dict[str, list[object]] | None = None) -> None:
        self._entries_by_domain = entries_by_domain or {}

    def async_entries(self, domain: str) -> list[object]:
        return list(self._entries_by_domain.get(domain, []))


class _FakeHass:
    def __init__(
        self,
        *,
        components: set[str] | None = None,
        entries_by_domain: dict[str, list[object]] | None = None,
    ) -> None:
        self.config = _FakeConfig(components)
        self.config_entries = _FakeConfigEntries(entries_by_domain)

    async def async_add_executor_job(self, func, *args):
        return func(*args)


def test_available_adapter_definitions_are_filtered_by_installed_integrations(
    tmp_path: Path, monkeypatch
) -> None:
    """Only mappings whose upstream integration is installed should be offered."""

    (tmp_path / "example_oem.yaml").write_text(
        f"""
integration:
  domain: example_oem
  friendly_name: Example OEM
{_MINIMAL_CANONICAL_CAPABILITIES.replace("kia_uvo", "example_oem").replace("Hyundai / Kia Connect", "Example OEM")}
""".strip(),
        encoding="utf-8",
    )
    (tmp_path / "other_oem.yaml").write_text(
        f"""
integration:
  domain: other_oem
  friendly_name: Other OEM
{_MINIMAL_CANONICAL_CAPABILITIES.replace("kia_uvo", "other_oem").replace("Hyundai / Kia Connect", "Other OEM")}
""".strip(),
        encoding="utf-8",
    )

    monkeypatch.setattr(registry_module, "_mapping_directory", lambda: tmp_path)
    hass = _FakeHass(components={"example_oem"})

    definitions = asyncio.run(get_available_adapter_definitions(hass))

    assert [definition.key for definition in definitions] == ["example_oem"]


def test_available_adapter_options_use_mapping_metadata_labels(
    tmp_path: Path, monkeypatch
) -> None:
    """Config-flow options should come from YAML keys and friendly names."""

    (tmp_path / "example_oem.yaml").write_text(
        f"""
integration:
  domain: example_oem
  friendly_name: Example OEM
{_MINIMAL_CANONICAL_CAPABILITIES.replace("kia_uvo", "example_oem").replace("Hyundai / Kia Connect", "Example OEM")}
""".strip(),
        encoding="utf-8",
    )

    monkeypatch.setattr(registry_module, "_mapping_directory", lambda: tmp_path)
    hass = _FakeHass(entries_by_domain={"example_oem": [object()]})

    options = asyncio.run(get_available_adapter_options(hass))

    assert options == {"example_oem": "Example OEM"}
