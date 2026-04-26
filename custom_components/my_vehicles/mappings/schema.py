"""Typed loading and validation for adapter mapping YAML files."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - environment fallback
    from . import simple_yaml as yaml

from ..domain.capability_registry import CANONICAL_ACTIONS, CORE_CAPABILITIES


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
    availability: StateMapping | None = None
    availability_not: StateMapping | None = None


@dataclass(frozen=True, slots=True)
class StateMapping:
    """Validated state definition for one canonical capability."""

    entity: str | None = None
    template: str | None = None
    any: tuple[str, ...] = ()
    all: tuple[str, ...] = ()
    unavailable: bool = False
    domain: str | None = None
    metadata: MappingMetadata = field(default_factory=MappingMetadata)

    def source_entities(self) -> tuple[str, ...]:
        """Return all referenced source entities for this mapping."""

        if self.entity is not None:
            return (self.entity,)
        if self.any:
            return self.any
        if self.all:
            return self.all
        return ()

    def mode(self) -> str:
        """Return the primary mapping mode name."""

        if self.entity is not None:
            return "entity"
        if self.template is not None:
            return "template"
        if self.any:
            return "any"
        if self.all:
            return "all"
        if self.unavailable:
            return "unavailable"
        return "empty"


@dataclass(frozen=True, slots=True)
class CapabilityMapping:
    """Canonical capability mapping with required state and optional actions."""

    name: str
    state: StateMapping
    availability: StateMapping | None = None
    availability_not: StateMapping | None = None
    actions: dict[str, ActionMapping] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class VehicleAdapterMapping:
    """Fully validated adapter mapping definition."""

    integration: MappingIntegration
    capabilities: dict[str, CapabilityMapping]

    def capability(self, name: str) -> CapabilityMapping | None:
        """Return one capability mapping by canonical name."""

        return self.capabilities.get(name)


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


async def async_load_adapter_mapping(
    hass: Any, adapter_name: str
) -> VehicleAdapterMapping:
    """Load one co-located mapping file without blocking the event loop."""

    return await hass.async_add_executor_job(load_adapter_mapping, adapter_name)


def _parse_mapping(raw_data: dict[str, Any]) -> VehicleAdapterMapping:
    integration = _parse_integration(raw_data.get("integration"))
    if "metrics" in raw_data:
        raise MappingValidationError("metrics is not supported in the unified schema")
    if "derived" in raw_data:
        raise MappingValidationError("derived is not supported in the unified schema")
    capabilities = _parse_capabilities(raw_data.get("capabilities"))
    return VehicleAdapterMapping(
        integration=integration,
        capabilities=capabilities,
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

    unknown = sorted(set(raw_capabilities) - set(CORE_CAPABILITIES))
    if unknown:
        raise MappingValidationError(
            f"Unknown canonical capabilities: {', '.join(unknown)}"
        )

    missing = [
        capability
        for capability in CORE_CAPABILITIES
        if capability not in raw_capabilities
    ]
    if missing:
        raise MappingValidationError(
            f"Missing canonical capabilities: {', '.join(missing)}"
        )

    capabilities: dict[str, CapabilityMapping] = {}
    for capability_name, raw_mapping in raw_capabilities.items():
        if not isinstance(capability_name, str) or not capability_name:
            raise MappingValidationError("capability names must be non-empty strings")
        if not isinstance(raw_mapping, dict):
            raise MappingValidationError(
                f"capabilities.{capability_name} must be a dictionary"
            )

        if (
            raw_mapping.get("availability") is not None
            and raw_mapping.get("availability_not") is not None
        ):
            raise MappingValidationError(
                f"capabilities.{capability_name} may not define both availability and availability_not"
            )

        raw_state = raw_mapping.get("state")
        if not isinstance(raw_state, dict):
            raise MappingValidationError(
                f"capabilities.{capability_name}.state must be a dictionary"
            )

        actions = _parse_actions(
            raw_mapping.get("actions"),
            context=f"capabilities.{capability_name}.actions",
            capability_name=capability_name,
        )
        state_mapping = _parse_state_mapping(
            raw_state,
            context=f"capabilities.{capability_name}.state",
        )
        availability = _parse_optional_state_mapping(
            raw_mapping.get("availability"),
            context=f"capabilities.{capability_name}.availability",
        )
        availability_not = _parse_optional_state_mapping(
            raw_mapping.get("availability_not"),
            context=f"capabilities.{capability_name}.availability_not",
        )
        capabilities[capability_name] = CapabilityMapping(
            name=capability_name,
            state=state_mapping,
            availability=availability,
            availability_not=availability_not,
            actions=actions,
        )

    return capabilities


def _parse_state_mapping(
    raw_mapping: dict[str, Any],
    *,
    context: str,
) -> StateMapping:
    mode_values = {
        "entity": raw_mapping.get("entity"),
        "template": raw_mapping.get("template"),
        "any": raw_mapping.get("any"),
        "all": raw_mapping.get("all"),
        "unavailable": raw_mapping.get("unavailable"),
    }
    present_modes = [
        key
        for key, value in mode_values.items()
        if value not in (None, [], (), False)
    ]
    if len(present_modes) != 1:
        raise MappingValidationError(
            f"{context} must define exactly one of entity/template/any/all/unavailable"
        )

    entity_value = raw_mapping.get("entity")
    template_value = raw_mapping.get("template")
    raw_any = raw_mapping.get("any")
    raw_all = raw_mapping.get("all")
    unavailable_value = raw_mapping.get("unavailable", False)

    if entity_value is not None and not isinstance(entity_value, str):
        raise MappingValidationError(f"{context}.entity must be a string")
    if template_value is not None and not isinstance(template_value, str):
        raise MappingValidationError(f"{context}.template must be a string")
    if unavailable_value not in (False, True):
        raise MappingValidationError(f"{context}.unavailable must be true when set")
    if unavailable_value is True and present_modes != ["unavailable"]:
        raise MappingValidationError(
            f"{context}.unavailable may not be combined with other state modes"
        )

    any_value = (
        _as_string_tuple(raw_any, context=f"{context}.any")
        if raw_any not in (None, ())
        else ()
    )
    all_value = (
        _as_string_tuple(raw_all, context=f"{context}.all")
        if raw_all not in (None, ())
        else ()
    )
    domain_value = raw_mapping.get("domain")
    if domain_value is not None and not isinstance(domain_value, str):
        raise MappingValidationError(f"{context}.domain must be a string when set")

    metadata = _parse_metadata(raw_mapping, context=context)
    return StateMapping(
        entity=entity_value if isinstance(entity_value, str) else None,
        template=template_value if isinstance(template_value, str) else None,
        any=any_value,
        all=all_value,
        unavailable=unavailable_value is True,
        domain=domain_value if isinstance(domain_value, str) else None,
        metadata=metadata,
    )


def _parse_actions(
    raw_actions: Any,
    *,
    context: str,
    capability_name: str,
) -> dict[str, ActionMapping]:
    if raw_actions is None:
        return {}
    if not isinstance(raw_actions, dict):
        raise MappingValidationError(f"{context} must be a dictionary")

    allowed_verbs = set(CANONICAL_ACTIONS[capability_name])
    parsed: dict[str, ActionMapping] = {}
    for action_name, raw_action in raw_actions.items():
        if not isinstance(action_name, str) or not action_name:
            raise MappingValidationError(f"{context} keys must be non-empty strings")
        if action_name not in allowed_verbs:
            raise MappingValidationError(
                f"{context}.{action_name} is not a valid canonical verb for {capability_name}"
            )
        if not isinstance(raw_action, dict):
            raise MappingValidationError(f"{context}.{action_name} must be a dictionary")

        action = raw_action.get("action")
        if not isinstance(action, str) or not action:
            raise MappingValidationError(
                f"{context}.{action_name}.action must be a non-empty string"
            )
        if "." not in action:
            raise MappingValidationError(
                f"{context}.{action_name}.action must be a fully qualified domain.service"
            )
        action_domain, action_service = action.split(".", 1)
        if not action_domain or not action_service:
            raise MappingValidationError(
                f"{context}.{action_name}.action must be a fully qualified domain.service"
            )
        data = _normalize_placeholder_values(raw_action.get("data", {}))
        target = _normalize_placeholder_values(raw_action.get("target", {}))
        if not isinstance(data, dict):
            raise MappingValidationError(f"{context}.{action_name}.data must be a dictionary")
        if not isinstance(target, dict):
            raise MappingValidationError(
                f"{context}.{action_name}.target must be a dictionary"
            )
        raw_availability = raw_action.get("availability")
        raw_availability_not = raw_action.get("availability_not")
        availability = None
        availability_not = None
        if raw_availability is not None:
            if not isinstance(raw_availability, dict):
                raise MappingValidationError(
                    f"{context}.{action_name}.availability must be a dictionary"
                )
            availability = _parse_state_mapping(
                raw_availability,
                context=f"{context}.{action_name}.availability",
            )
        if raw_availability_not is not None:
            if not isinstance(raw_availability_not, dict):
                raise MappingValidationError(
                    f"{context}.{action_name}.availability_not must be a dictionary"
                )
            availability_not = _parse_state_mapping(
                raw_availability_not,
                context=f"{context}.{action_name}.availability_not",
            )
        if availability is not None and availability_not is not None:
            raise MappingValidationError(
                f"{context}.{action_name} may not define both availability and availability_not"
            )
        parsed[action_name] = ActionMapping(
            action=action,
            data=data,
            target=target,
            availability=availability,
            availability_not=availability_not,
        )

    return parsed


def _parse_optional_state_mapping(raw_mapping: Any, *, context: str) -> StateMapping | None:
    if raw_mapping is None:
        return None
    if not isinstance(raw_mapping, dict):
        raise MappingValidationError(f"{context} must be a dictionary")
    return _parse_state_mapping(raw_mapping, context=context)


def _normalize_placeholder_values(value: Any) -> Any:
    if isinstance(value, dict):
        if len(value) == 1:
            key, nested = next(iter(value.items()))
            if isinstance(key, str) and nested is None and key in {"device", "vehicle"}:
                return "{" + key + "}"
        return {
            key: _normalize_placeholder_values(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_normalize_placeholder_values(item) for item in value]
    return value


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
