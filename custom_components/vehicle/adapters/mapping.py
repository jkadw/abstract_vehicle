"""Typed loading and validation for adapter mapping YAML files."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class MappingValidationError(ValueError):
    """Raised when a mapping file is structurally invalid."""


_METADATA_KEYS = {
    "device_class",
    "state_class",
    "unit_of_measurement",
    "icon",
    "attributes",
}


@dataclass(frozen=True, slots=True)
class MappingIntegration:
    """Top-level upstream integration metadata."""

    domain: str
    friendly_name: str


@dataclass(frozen=True, slots=True)
class MappingMetadata:
    """Optional HA-facing metadata overrides for one mapped output."""

    device_class: str | None = None
    state_class: str | None = None
    unit_of_measurement: str | None = None
    icon: str | None = None
    attributes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ActionMapping:
    """One canonical action mapped to an upstream action and payload."""

    action: str
    data: dict[str, Any] = field(default_factory=dict)
    target: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class StateMapping:
    """Shared shape for capability, metric, and derived value mappings."""

    state: str | None = None
    template: str | None = None
    any: tuple[str, ...] = ()
    all: tuple[str, ...] = ()
    domain: str | None = None
    metadata: MappingMetadata = field(default_factory=MappingMetadata)

    def source_entities(self) -> tuple[str, ...]:
        """Return all referenced source entities for this mapping."""

        if self.state is not None:
            return (self.state,)
        if self.any:
            return self.any
        if self.all:
            return self.all
        return ()

    def mode(self) -> str:
        """Return the primary mapping mode name."""

        if self.state is not None:
            return "state"
        if self.template is not None:
            return "template"
        if self.any:
            return "any"
        if self.all:
            return "all"
        return "empty"


@dataclass(frozen=True, slots=True)
class CapabilityMapping:
    """Canonical capability mapping with optional state and actions."""

    name: str
    state: StateMapping | None = None
    actions: dict[str, ActionMapping] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class VehicleAdapterMapping:
    """Fully validated adapter mapping definition."""

    integration: MappingIntegration
    capabilities: dict[str, CapabilityMapping]
    metrics: dict[str, StateMapping] = field(default_factory=dict)
    derived: dict[str, StateMapping] = field(default_factory=dict)

    def capability(self, name: str) -> CapabilityMapping | None:
        """Return one capability mapping by canonical name."""

        return self.capabilities.get(name)

    def metric(self, name: str) -> StateMapping | None:
        """Return one metric mapping by canonical name."""

        return self.metrics.get(name)

    def derived_entity(self, name: str) -> StateMapping | None:
        """Return one derived entity mapping by name."""

        return self.derived.get(name)


def load_mapping_file(path: str | Path) -> VehicleAdapterMapping:
    """Load and validate one adapter mapping YAML file."""

    mapping_path = Path(path)
    if not mapping_path.exists():
        raise MappingValidationError(f"Mapping file not found: {mapping_path}")

    try:
        raw_data = yaml.safe_load(mapping_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as err:
        raise MappingValidationError(f"Invalid YAML in {mapping_path}") from err

    if not isinstance(raw_data, dict):
        raise MappingValidationError("Mapping root must be a dictionary")

    return _parse_mapping(raw_data)


def load_adapter_mapping(adapter_name: str) -> VehicleAdapterMapping:
    """Load a mapping file co-located with the adapter package."""

    mapping_path = Path(__file__).resolve().parent / f"{adapter_name}.yaml"
    return load_mapping_file(mapping_path)


def _parse_mapping(raw_data: dict[str, Any]) -> VehicleAdapterMapping:
    integration = _parse_integration(raw_data.get("integration"))
    capabilities = _parse_capabilities(raw_data.get("capabilities"))
    metrics = _parse_named_state_mappings(raw_data.get("metrics"), "metrics")
    derived = _parse_named_state_mappings(raw_data.get("derived"), "derived")
    return VehicleAdapterMapping(
        integration=integration,
        capabilities=capabilities,
        metrics=metrics,
        derived=derived,
    )


def _parse_integration(raw_integration: Any) -> MappingIntegration:
    if not isinstance(raw_integration, dict):
        raise MappingValidationError("integration must be a dictionary")

    domain = raw_integration.get("domain")
    friendly_name = raw_integration.get("friendly_name")
    if not isinstance(domain, str) or not domain:
        raise MappingValidationError("integration.domain must be a non-empty string")
    if not isinstance(friendly_name, str) or not friendly_name:
        raise MappingValidationError(
            "integration.friendly_name must be a non-empty string"
        )
    return MappingIntegration(domain=domain, friendly_name=friendly_name)


def _parse_capabilities(raw_capabilities: Any) -> dict[str, CapabilityMapping]:
    if not isinstance(raw_capabilities, dict) or not raw_capabilities:
        raise MappingValidationError("capabilities must be a non-empty dictionary")

    capabilities: dict[str, CapabilityMapping] = {}
    for capability_name, raw_mapping in raw_capabilities.items():
        if not isinstance(capability_name, str) or not capability_name:
            raise MappingValidationError("capability names must be non-empty strings")
        if not isinstance(raw_mapping, dict):
            raise MappingValidationError(
                f"capabilities.{capability_name} must be a dictionary"
            )

        actions = _parse_actions(
            raw_mapping.get("actions"),
            context=f"capabilities.{capability_name}.actions",
        )
        state_mapping = _parse_state_mapping(
            raw_mapping,
            context=f"capabilities.{capability_name}",
            require_domain=False,
        )
        if state_mapping is None and not actions:
            raise MappingValidationError(
                f"capabilities.{capability_name} must define state/template/any/all or actions"
            )
        capabilities[capability_name] = CapabilityMapping(
            name=capability_name,
            state=state_mapping,
            actions=actions,
        )

    return capabilities


def _parse_named_state_mappings(
    raw_section: Any, section_name: str
) -> dict[str, StateMapping]:
    if raw_section is None:
        return {}
    if not isinstance(raw_section, dict):
        raise MappingValidationError(f"{section_name} must be a dictionary")

    parsed: dict[str, StateMapping] = {}
    for name, raw_mapping in raw_section.items():
        if not isinstance(name, str) or not name:
            raise MappingValidationError(
                f"{section_name} keys must be non-empty strings"
            )
        if not isinstance(raw_mapping, dict):
            raise MappingValidationError(f"{section_name}.{name} must be a dictionary")
        mapping = _parse_state_mapping(
            raw_mapping,
            context=f"{section_name}.{name}",
            require_domain=section_name == "derived",
        )
        if mapping is None:
            raise MappingValidationError(
                f"{section_name}.{name} must define state/template/any/all"
            )
        parsed[name] = mapping

    return parsed


def _parse_state_mapping(
    raw_mapping: dict[str, Any],
    *,
    context: str,
    require_domain: bool,
) -> StateMapping | None:
    mode_values = {
        "state": raw_mapping.get("state"),
        "template": raw_mapping.get("template"),
        "any": raw_mapping.get("any"),
        "all": raw_mapping.get("all"),
    }
    present_modes = [
        key
        for key, value in mode_values.items()
        if value not in (None, [], ())
    ]
    if not present_modes:
        return None
    if len(present_modes) > 1:
        raise MappingValidationError(
            f"{context} must define only one of state/template/any/all"
        )

    state_value = raw_mapping.get("state")
    template_value = raw_mapping.get("template")
    any_value = _as_string_tuple(raw_mapping.get("any"), context=f"{context}.any")
    all_value = _as_string_tuple(raw_mapping.get("all"), context=f"{context}.all")
    domain_value = raw_mapping.get("domain")
    if domain_value is not None and not isinstance(domain_value, str):
        raise MappingValidationError(f"{context}.domain must be a string when set")
    if require_domain and not isinstance(domain_value, str):
        raise MappingValidationError(f"{context}.domain is required")

    if state_value is not None and not isinstance(state_value, str):
        raise MappingValidationError(f"{context}.state must be a string")
    if template_value is not None and not isinstance(template_value, str):
        raise MappingValidationError(f"{context}.template must be a string")

    metadata = _parse_metadata(raw_mapping, context=context)
    return StateMapping(
        state=state_value if isinstance(state_value, str) else None,
        template=template_value if isinstance(template_value, str) else None,
        any=any_value,
        all=all_value,
        domain=domain_value if isinstance(domain_value, str) else None,
        metadata=metadata,
    )


def _parse_actions(raw_actions: Any, *, context: str) -> dict[str, ActionMapping]:
    if raw_actions is None:
        return {}
    if not isinstance(raw_actions, dict):
        raise MappingValidationError(f"{context} must be a dictionary")

    parsed: dict[str, ActionMapping] = {}
    for action_name, raw_action in raw_actions.items():
        if not isinstance(action_name, str) or not action_name:
            raise MappingValidationError(f"{context} keys must be non-empty strings")
        if not isinstance(raw_action, dict):
            raise MappingValidationError(f"{context}.{action_name} must be a dictionary")

        action = raw_action.get("action")
        if not isinstance(action, str) or not action:
            raise MappingValidationError(
                f"{context}.{action_name}.action must be a non-empty string"
            )
        data = raw_action.get("data", {})
        target = raw_action.get("target", {})
        if not isinstance(data, dict):
            raise MappingValidationError(f"{context}.{action_name}.data must be a dictionary")
        if not isinstance(target, dict):
            raise MappingValidationError(
                f"{context}.{action_name}.target must be a dictionary"
            )
        parsed[action_name] = ActionMapping(action=action, data=data, target=target)

    return parsed


def _parse_metadata(raw_mapping: dict[str, Any], *, context: str) -> MappingMetadata:
    attributes = raw_mapping.get("attributes", ())
    if attributes in (None, ()):
        parsed_attributes: tuple[str, ...] = ()
    else:
        parsed_attributes = _as_string_tuple(
            attributes, context=f"{context}.attributes"
        )

    for key in _METADATA_KEYS - {"attributes"}:
        value = raw_mapping.get(key)
        if value is not None and not isinstance(value, str):
            raise MappingValidationError(f"{context}.{key} must be a string when set")

    return MappingMetadata(
        device_class=raw_mapping.get("device_class"),
        state_class=raw_mapping.get("state_class"),
        unit_of_measurement=raw_mapping.get("unit_of_measurement"),
        icon=raw_mapping.get("icon"),
        attributes=parsed_attributes,
    )


def _as_string_tuple(value: Any, *, context: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise MappingValidationError(f"{context} must be a list of strings")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item:
            raise MappingValidationError(f"{context} must contain non-empty strings")
        items.append(item)
    return tuple(items)
