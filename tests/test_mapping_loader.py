"""Tests for adapter mapping loading and validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from custom_components.my_vehicles.adapters.loader import (
    _load_adapter_class,
    get_available_adapter_definitions,
    get_available_adapter_options,
)
from custom_components.my_vehicles.adapters.mapping import (
    MappingValidationError,
    load_adapter_mapping,
    load_mapping_file,
)
from custom_components.my_vehicles.adapters.mapped import MappedVehicleAdapter
from custom_components.my_vehicles.adapters import registry as registry_module
from custom_components.my_vehicles.adapters.registry import (
    CUSTOM_ADAPTER_DEFINITIONS,
    get_adapter_definition,
    get_adapter_definitions,
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
        """
integration:
  domain: example_oem
  friendly_name: Example OEM
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


@pytest.mark.asyncio
async def test_available_adapter_definitions_are_filtered_by_installed_integrations(
    tmp_path: Path, monkeypatch
) -> None:
    """Only mappings whose upstream integration is installed should be offered."""

    (tmp_path / "example_oem.yaml").write_text(
        """
integration:
  domain: example_oem
  friendly_name: Example OEM
capabilities:
  lock:
    state: lock.{vehicle}_door_lock
""".strip(),
        encoding="utf-8",
    )
    (tmp_path / "other_oem.yaml").write_text(
        """
integration:
  domain: other_oem
  friendly_name: Other OEM
capabilities:
  lock:
    state: lock.{vehicle}_door_lock
""".strip(),
        encoding="utf-8",
    )

    monkeypatch.setattr(registry_module, "_mapping_directory", lambda: tmp_path)
    hass = _FakeHass(components={"example_oem"})

    definitions = await get_available_adapter_definitions(hass)

    assert [definition.key for definition in definitions] == ["example_oem"]


@pytest.mark.asyncio
async def test_available_adapter_options_use_mapping_metadata_labels(
    tmp_path: Path, monkeypatch
) -> None:
    """Config-flow options should come from YAML keys and friendly names."""

    (tmp_path / "example_oem.yaml").write_text(
        """
integration:
  domain: example_oem
  friendly_name: Example OEM
capabilities:
  lock:
    state: lock.{vehicle}_door_lock
""".strip(),
        encoding="utf-8",
    )

    monkeypatch.setattr(registry_module, "_mapping_directory", lambda: tmp_path)
    hass = _FakeHass(entries_by_domain={"example_oem": [object()]})

    options = await get_available_adapter_options(hass)

    assert options == {"example_oem": "Example OEM"}
