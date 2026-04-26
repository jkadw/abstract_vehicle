"""Generic HA-backed runtime for evaluation and action execution of adapter mappings."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

try:
    from jinja2 import Environment, StrictUndefined
except ModuleNotFoundError:  # pragma: no cover - environment fallback
    Environment = None
    StrictUndefined = object

from .base import ActionResult, UnsupportedVehicleActionError, VehicleAdapterError
from ..domain.model import CapabilitySupport, VehicleCapabilities
from ..mappings.schema import ActionMapping, StateMapping, VehicleAdapterMapping


@dataclass(frozen=True, slots=True)
class PreparedAction:
    """One canonical action prepared for later execution."""

    canonical_action: str
    service: str
    data: dict[str, Any] = field(default_factory=dict)
    target: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ResolvedMappingRuntime:
    """Resolved read-only view of one mapping against one source vehicle."""

    capability_states: dict[str, Any]
    capabilities: VehicleCapabilities
    actions: dict[str, dict[str, PreparedAction]]
    errors: dict[str, str]


class MappingRuntime:
    """Evaluation runtime for one adapter mapping instance."""

    def __init__(
        self,
        hass: Any,
        mapping: VehicleAdapterMapping,
        *,
        vehicle: str,
        device: str,
    ) -> None:
        self._hass = hass
        self._mapping = mapping
        self._vehicle = vehicle
        self._device = device
        self._template_env = _build_template_environment(self)

    def resolve(self) -> ResolvedMappingRuntime:
        """Resolve one mapping against the current HA state model."""

        capability_states, errors = self._resolve_capability_states()
        capabilities = self._build_capabilities()
        actions = self._prepare_actions()
        return ResolvedMappingRuntime(
            capability_states=capability_states,
            capabilities=capabilities,
            actions=actions,
            errors=errors,
        )

    def get_prepared_action(
        self, capability_name: str, canonical_action: str
    ) -> PreparedAction:
        """Return one prepared action or raise a clear adapter-level error."""

        capability = self._mapping.capability(capability_name)
        if capability is None:
            raise UnsupportedVehicleActionError(
                f"Unknown capability for action execution: {capability_name}"
            )

        action = capability.actions.get(canonical_action)
        if action is None:
            raise UnsupportedVehicleActionError(
                f"Unsupported action '{canonical_action}' for capability '{capability_name}'"
            )

        return self._prepare_action(canonical_action, action)

    async def async_execute_action(
        self, capability_name: str, canonical_action: str
    ) -> ActionResult:
        """Execute one mapped action via Home Assistant services."""

        prepared = self.get_prepared_action(capability_name, canonical_action)
        domain, service = _split_service_name(prepared.service)
        services = getattr(self._hass, "services", None)
        if services is None:
            raise VehicleAdapterError("Home Assistant service registry is unavailable")

        async_call = getattr(services, "async_call", None)
        if async_call is None:
            raise VehicleAdapterError(
                "Home Assistant service registry does not support async calls"
            )

        try:
            await async_call(
                domain,
                service,
                service_data=prepared.data,
                target=prepared.target or None,
                blocking=True,
            )
        except Exception as err:  # pragma: no cover - defensive adapter boundary
            raise VehicleAdapterError(
                f"Failed to execute mapped action '{canonical_action}' via {prepared.service}"
            ) from err

        return ActionResult(
            success=True,
            action=canonical_action,
            message=f"Executed {prepared.service}",
        )

    def state_value(self, entity_id: str) -> str:
        """Return one HA entity state as a string."""

        entity = self._get_state_object(entity_id)
        return "unknown" if entity is None else str(getattr(entity, "state", "unknown"))

    def state_attr(self, entity_id: str, attr_name: str) -> Any:
        """Return one HA entity attribute value."""

        entity = self._get_state_object(entity_id)
        if entity is None:
            return None
        attributes = getattr(entity, "attributes", {}) or {}
        if not isinstance(attributes, dict):
            return None
        return attributes.get(attr_name)

    def source_entity_snapshot(self) -> dict[str, dict[str, Any]]:
        """Return a read-only snapshot of resolved source entities."""

        snapshot: dict[str, dict[str, Any]] = {}
        for entity_id in self._referenced_entity_ids():
            entity = self._get_state_object(entity_id)
            attributes = getattr(entity, "attributes", {}) if entity is not None else {}
            if not isinstance(attributes, dict):
                attributes = {}
            snapshot[entity_id] = {
                "exists": entity is not None,
                "state": None if entity is None else str(getattr(entity, "state", "unknown")),
                "attributes": {
                    key: value
                    for key, value in attributes.items()
                    if key in {"unit_of_measurement", "device_class", "state_class", "icon"}
                },
            }
        return snapshot

    def _resolve_capability_states(self) -> tuple[dict[str, Any], dict[str, str]]:
        capability_states: dict[str, Any] = {}
        errors: dict[str, str] = {}

        for capability_name, capability in self._mapping.capabilities.items():
            missing_entities = self._missing_source_entities(
                capability.state.source_entities()
            )
            if missing_entities:
                errors[capability_name] = (
                    "Missing source entities: " + ", ".join(missing_entities)
                )

            try:
                capability_states[capability_name] = self._resolve_state_mapping(
                    capability.state
                )
            except Exception as err:
                detail = f"{type(err).__name__}: {err}"
                errors[capability_name] = (
                    f"{errors[capability_name]}; {detail}"
                    if capability_name in errors
                    else detail
                )
                capability_states[capability_name] = None

        return capability_states, errors

    def _build_capabilities(self) -> VehicleCapabilities:
        return VehicleCapabilities(
            **{
                capability_name: CapabilitySupport(
                    state_supported=not capability.state.unavailable,
                    action_supported=bool(capability.actions),
                )
                for capability_name, capability in self._mapping.capabilities.items()
            }
        )

    def _prepare_actions(self) -> dict[str, dict[str, PreparedAction]]:
        prepared: dict[str, dict[str, PreparedAction]] = {}
        for capability_name, capability in self._mapping.capabilities.items():
            if not capability.actions:
                continue
            prepared[capability_name] = {}
            for canonical_action, action in capability.actions.items():
                prepared[capability_name][canonical_action] = self._prepare_action(
                    canonical_action,
                    action,
                )
        return prepared

    def _prepare_action(
        self, canonical_action: str, action: ActionMapping
    ) -> PreparedAction:
        return PreparedAction(
            canonical_action=canonical_action,
            service=action.action,
            data=_substitute_placeholders(action.data, self._vehicle, self._device),
            target=_substitute_placeholders(action.target, self._vehicle, self._device),
        )

    def _resolve_state_mapping(self, mapping: StateMapping) -> Any:
        if mapping.unavailable:
            return None
        if mapping.entity is not None:
            entity_id = _substitute_string(mapping.entity, self._vehicle, self._device)
            return self.state_value(entity_id)
        if mapping.template is not None:
            template = _substitute_string(mapping.template, self._vehicle, self._device)
            rendered = self._template_env.from_string(template).render()
            return _coerce_template_value(rendered)
        if mapping.any:
            return any(
                _state_to_bool(
                    self.state_value(
                        _substitute_string(entity_id, self._vehicle, self._device)
                    )
                )
                for entity_id in mapping.any
            )
        if mapping.all:
            return all(
                _state_to_bool(
                    self.state_value(
                        _substitute_string(entity_id, self._vehicle, self._device)
                    )
                )
                for entity_id in mapping.all
            )
        return None

    def _get_state_object(self, entity_id: str) -> Any | None:
        states = getattr(self._hass, "states", None)
        if states is None:
            return None
        getter = getattr(states, "get", None)
        if getter is None:
            return None
        return getter(entity_id)

    def _referenced_entity_ids(self) -> list[str]:
        entity_ids: list[str] = []
        for capability in self._mapping.capabilities.values():
            entity_ids.extend(
                self._resolve_source_entities(capability.state.source_entities())
            )
            for action in capability.actions.values():
                self._collect_entity_ids_from_value(action.data, entity_ids)
                self._collect_entity_ids_from_value(action.target, entity_ids)

        unique_ids: list[str] = []
        for entity_id in entity_ids:
            if entity_id not in unique_ids:
                unique_ids.append(entity_id)
        return unique_ids

    def _resolve_source_entities(self, entity_ids: tuple[str, ...]) -> list[str]:
        return [
            _substitute_string(entity_id, self._vehicle, self._device)
            for entity_id in entity_ids
        ]

    def _missing_source_entities(self, entity_ids: tuple[str, ...]) -> list[str]:
        missing: list[str] = []
        for entity_id in self._resolve_source_entities(entity_ids):
            if self._get_state_object(entity_id) is None:
                missing.append(entity_id)
        return missing

    def _collect_entity_ids_from_value(self, value: Any, entity_ids: list[str]) -> None:
        if isinstance(value, str):
            resolved = _substitute_string(value, self._vehicle, self._device)
            if "." in resolved and " " not in resolved:
                entity_ids.append(resolved)
            return
        if isinstance(value, dict):
            for item in value.values():
                self._collect_entity_ids_from_value(item, entity_ids)
            return
        if isinstance(value, list):
            for item in value:
                self._collect_entity_ids_from_value(item, entity_ids)


def _build_template_environment(runtime: MappingRuntime) -> Environment:
    if Environment is None:
        return _FallbackEnvironment(runtime)
    env = Environment(undefined=StrictUndefined, autoescape=False)
    env.globals["states"] = runtime.state_value
    env.globals["state_attr"] = runtime.state_attr
    env.filters["float"] = _jinja_float
    env.filters["int"] = _jinja_int
    return env


def _jinja_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _jinja_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return int(default)


def _state_to_bool(value: Any) -> bool:
    normalized = str(value).strip().lower()
    return normalized in {"on", "open", "true", "1", "locked", "charging"}


def _substitute_placeholders(value: Any, vehicle: str, device: str) -> Any:
    if isinstance(value, str):
        return _substitute_string(value, vehicle, device)
    if isinstance(value, dict):
        return {
            key: _substitute_placeholders(item, vehicle, device)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_substitute_placeholders(item, vehicle, device) for item in value]
    return value


def _substitute_string(value: str, vehicle: str, device: str) -> str:
    return value.replace("{vehicle}", vehicle).replace("{device}", device)


def _split_service_name(service_name: str) -> tuple[str, str]:
    parts = service_name.split(".", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise VehicleAdapterError(f"Invalid mapped service name: {service_name}")
    return parts[0], parts[1]


def _coerce_template_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    normalized = value.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    return value


class _FallbackEnvironment:
    def __init__(self, runtime: MappingRuntime) -> None:
        self._runtime = runtime

    def from_string(self, template: str):
        return _FallbackTemplate(self._runtime, template)


class _FallbackTemplate:
    def __init__(self, runtime: MappingRuntime, template: str) -> None:
        self._runtime = runtime
        self._template = template

    def render(self) -> str:
        template = self._template.strip()
        if template.startswith("{{") and template.endswith("}}"):
            expression = template[2:-2].strip()
            return str(_evaluate_fallback_expression(self._runtime, expression))
        return template


def _evaluate_fallback_expression(runtime: MappingRuntime, expression: str) -> Any:
    normalized = expression
    normalized = normalized.replace("| float", "__float_filter")
    normalized = normalized.replace("| int", "__int_filter")
    normalized = normalized.replace("states(", "__states(")
    normalized = normalized.replace("state_attr(", "__state_attr(")
    normalized = _rewrite_filter_calls(normalized)

    return eval(  # noqa: S307 - controlled fallback for local template subset
        normalized,
        {"__builtins__": {}},
        {
            "__states": runtime.state_value,
            "__state_attr": runtime.state_attr,
            "__float_filter": _jinja_float,
            "__int_filter": _jinja_int,
        },
    )


def _rewrite_filter_calls(expression: str) -> str:
    for marker in ("__float_filter", "__int_filter"):
        while True:
            index = _find_uncalled_filter_index(expression, marker)
            if index == -1:
                break
            left = expression[:index].rstrip()
            start = _find_filter_operand_start(left)
            operand = left[start:].strip()
            expression = (
                f"{left[:start]}{marker}({operand})"
                f"{expression[index + len(marker):]}"
            )
    return expression


def _find_uncalled_filter_index(expression: str, marker: str) -> int:
    start = 0
    while True:
        index = expression.find(marker, start)
        if index == -1:
            return -1
        suffix = expression[index + len(marker) :].lstrip()
        if not suffix.startswith("("):
            return index
        start = index + len(marker)


def _find_filter_operand_start(text: str) -> int:
    depth = 0
    for index in range(len(text) - 1, -1, -1):
        char = text[index]
        if char == ")":
            depth += 1
        elif char == "(":
            depth -= 1
        elif depth == 0 and char in "<>=!+-*/% ":
            return index + 1
    return 0
