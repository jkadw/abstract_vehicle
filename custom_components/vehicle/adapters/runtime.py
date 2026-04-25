"""Generic HA-backed runtime for evaluation and action execution of adapter mappings."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from jinja2 import Environment, StrictUndefined

from .base import ActionResult, UnsupportedVehicleActionError, VehicleAdapterError
from ..model import CapabilitySupport, VehicleCapabilities
from .mapping import (
    ActionMapping,
    StateMapping,
    VehicleAdapterMapping,
)


@dataclass(frozen=True, slots=True)
class PreparedAction:
    """One canonical action prepared for later execution."""

    canonical_action: str
    service: str
    data: dict[str, Any] = field(default_factory=dict)
    target: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ResolvedDerivedEntity:
    """Resolved value for one derived entity definition."""

    name: str
    value: Any
    domain: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ResolvedMappingRuntime:
    """Resolved read-only view of one mapping against one source vehicle."""

    capability_states: dict[str, Any]
    metrics: dict[str, Any]
    derived: dict[str, ResolvedDerivedEntity]
    capabilities: VehicleCapabilities
    actions: dict[str, dict[str, PreparedAction]]


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

        capability_states = self._resolve_capability_states()
        metrics = self._resolve_metrics()
        derived = self._resolve_derived()
        capabilities = self._build_capabilities(capability_states)
        actions = self._prepare_actions()
        return ResolvedMappingRuntime(
            capability_states=capability_states,
            metrics=metrics,
            derived=derived,
            capabilities=capabilities,
            actions=actions,
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

    def _resolve_capability_states(self) -> dict[str, Any]:
        resolved: dict[str, Any] = {}
        for capability_name, capability in self._mapping.capabilities.items():
            if capability.state is None:
                continue
            resolved[capability_name] = self._resolve_state_mapping(capability.state)
        return resolved

    def _resolve_metrics(self) -> dict[str, Any]:
        resolved: dict[str, Any] = {}
        for metric_name, metric in self._mapping.metrics.items():
            resolved[metric_name] = self._resolve_state_mapping(metric)
        return resolved

    def _resolve_derived(self) -> dict[str, ResolvedDerivedEntity]:
        resolved: dict[str, ResolvedDerivedEntity] = {}
        for name, derived in self._mapping.derived.items():
            resolved[name] = ResolvedDerivedEntity(
                name=name,
                value=self._resolve_state_mapping(derived),
                domain=derived.domain,
                metadata=_metadata_dict(derived),
            )
        return resolved

    def _build_capabilities(
        self, capability_states: dict[str, Any]
    ) -> VehicleCapabilities:
        supports: dict[str, CapabilitySupport] = {}
        for capability_name in (
            "lock",
            "windows",
            "climate",
            "charging",
            "location",
            "battery",
            "fuel",
            "odometer",
            "refresh",
        ):
            mapping = self._mapping.capability(capability_name)
            if mapping is None:
                supports[capability_name] = CapabilitySupport()
                continue

            state_supported = False
            if mapping.state is not None:
                state_supported = capability_states.get(capability_name) is not None
            action_supported = bool(mapping.actions)
            supports[capability_name] = CapabilitySupport(
                state_supported=state_supported,
                action_supported=action_supported,
            )
        return VehicleCapabilities(**supports)

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
            service=f"{self._mapping.integration.domain}.{action.action}",
            data=_substitute_placeholders(action.data, self._vehicle, self._device),
            target=_substitute_placeholders(action.target, self._vehicle, self._device),
        )

    def _resolve_state_mapping(self, mapping: StateMapping) -> Any:
        if mapping.state is not None:
            entity_id = _substitute_string(mapping.state, self._vehicle, self._device)
            return self.state_value(entity_id)
        if mapping.template is not None:
            template = _substitute_string(mapping.template, self._vehicle, self._device)
            return self._template_env.from_string(template).render()
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


def _build_template_environment(runtime: MappingRuntime) -> Environment:
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


def _metadata_dict(mapping: StateMapping) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    if mapping.domain is not None:
        metadata["domain"] = mapping.domain
    if mapping.metadata.device_class is not None:
        metadata["device_class"] = mapping.metadata.device_class
    if mapping.metadata.state_class is not None:
        metadata["state_class"] = mapping.metadata.state_class
    if mapping.metadata.unit_of_measurement is not None:
        metadata["unit_of_measurement"] = mapping.metadata.unit_of_measurement
    if mapping.metadata.icon is not None:
        metadata["icon"] = mapping.metadata.icon
    if mapping.metadata.attributes:
        metadata["attributes"] = list(mapping.metadata.attributes)
    return metadata


def _split_service_name(service_name: str) -> tuple[str, str]:
    parts = service_name.split(".", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise VehicleAdapterError(f"Invalid mapped service name: {service_name}")
    return parts[0], parts[1]
