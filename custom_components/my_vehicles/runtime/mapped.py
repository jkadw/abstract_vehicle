"""Generic YAML-mapped adapter implementation."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .base import (
    ActionResult,
    DiscoveredVehicle,
    RawMetricsPayload,
    RawStatePayload,
    UnsupportedVehicleActionError,
    VehicleAdapter,
)
from .discovery import build_vehicle_payload_from_hass, discover_vehicles_for_mapping
from ..mappings.schema import VehicleAdapterMapping, load_adapter_mapping
from .runtime import MappingRuntime


class MappedVehicleAdapter(VehicleAdapter):
    """Generic adapter driven by a mapping file plus optional discovery helper."""

    mapping_name: str = ""
    friendly_name: str = ""
    discovery_helper: Any | None = None

    @classmethod
    def get_friendly_name(cls) -> str:
        """Return a user-facing adapter name."""

        if cls.friendly_name:
            return cls.friendly_name
        if cls.mapping_name:
            try:
                return load_adapter_mapping(cls.mapping_name).integration.friendly_name
            except Exception:
                pass
        return super().get_friendly_name()

    @classmethod
    async def async_discover_vehicles(cls, hass: Any) -> list[DiscoveredVehicle]:
        """Discover vehicles using generic mapping rules by default."""

        helper = cls.discovery_helper
        if helper is not None:
            return await helper.async_discover_vehicles(hass)
        if not cls.mapping_name:
            return []
        return await discover_vehicles_for_mapping(hass, cls.mapping_name)

    def __init__(
        self,
        vehicles: list[dict[str, Any]],
        vehicle_id: str | None = None,
        hass: Any | None = None,
        mapping_name: str | None = None,
        discovery_helper: Any | None = None,
        mapping: VehicleAdapterMapping | None = None,
    ) -> None:
        self._hass = hass
        self._mapping_name = mapping_name or self.mapping_name
        self._discovery_helper = discovery_helper or self.discovery_helper
        if not self._mapping_name:
            raise ValueError("Mapped vehicle adapter requires a mapping_name")

        self._mapping = mapping or load_adapter_mapping(self._mapping_name)
        if not vehicles:
            raise ValueError("Mapped vehicle adapter requires at least one configured vehicle")

        self._vehicles: dict[str, dict[str, Any]] = {}
        for vehicle in vehicles:
            raw_vehicle_id = vehicle.get("vehicle_id") or vehicle.get("id")
            if not isinstance(raw_vehicle_id, str) or not raw_vehicle_id:
                raise ValueError("Each configured mapped vehicle requires a vehicle_id")
            self._vehicles[raw_vehicle_id] = deepcopy(vehicle)

        self._vehicle_id = vehicle_id or next(iter(self._vehicles))
        if self._vehicle_id not in self._vehicles:
            raise ValueError(
                f"Configured mapped vehicle_id not found: {self._vehicle_id}"
            )

        if self._hass is not None and getattr(self._hass, "is_running", False):
            refreshed_vehicle = self._refresh_vehicle_payload()
            if refreshed_vehicle is not None:
                self._vehicles[self._vehicle_id] = self._merge_vehicle_payloads(
                    self._vehicles[self._vehicle_id],
                    refreshed_vehicle,
                )

    async def get_raw_state(self) -> RawStatePayload:
        """Return raw state derived from the generic mapping runtime."""

        vehicle = self._vehicle
        resolved = self._resolve_runtime()
        locked = _coerce_lock_state(resolved.capability_states.get("lock_vehicle"))
        climate_active = _coerce_bool_state(resolved.capability_states.get("climate"))
        charging_active = _coerce_bool_state(
            resolved.capability_states.get("charging")
        ) or self._as_bool(vehicle.get("charging_active"), default=False)
        charging_plugged = self._as_bool(vehicle.get("charging_plugged"))
        available = self._as_bool(vehicle.get("available"), default=True)
        backend_online = self._as_bool(vehicle.get("backend_online"), default=True)
        has_error = self._as_bool(vehicle.get("has_error"), default=False)
        driving = self._as_bool(vehicle.get("driving"), default=False)

        return {
            "vehicle_id": self._vehicle_id,
            "name": self._as_str(vehicle.get("name")) or "Mapped Vehicle",
            "manufacturer": self._as_str(vehicle.get("manufacturer")) or "Unknown",
            "model": self._as_str(vehicle.get("model")) or "Unknown",
            "vehicle_type": self._as_str(vehicle.get("vehicle_type")) or "unknown",
            "status": self._as_str(vehicle.get("status"))
            or self._derive_status(
                available=available,
                backend_online=backend_online,
                has_error=has_error,
                driving=driving,
                charging_active=charging_active is True,
            ),
            "available": available,
            "backend_online": backend_online,
            "has_error": has_error,
            "driving": driving,
            "charging_active": charging_active,
            "charging_plugged": charging_plugged,
            "locked": locked,
            "climate_active": climate_active,
            "ignition_on": _coerce_bool_state(resolved.capability_states.get("ignition")),
            "range_warning": _coerce_bool_state(
                resolved.capability_states.get("range_warning")
            ),
            "warning_messages": resolved.capability_states.get("warning_messages"),
            "info_messages": resolved.capability_states.get("info_messages"),
            "hazard_lights_active": _coerce_bool_state(
                resolved.capability_states.get("hazard_lights")
            ),
            "source_problems": dict(resolved.errors),
        }

    async def get_raw_metrics(self) -> RawMetricsPayload:
        """Return raw metrics derived from the generic mapping runtime."""

        resolved = self._resolve_runtime()
        runtime = self._runtime()
        latitude, longitude = self._resolve_coordinates(runtime)
        return {
            "battery_level": self._as_float(
                resolved.capability_states.get("battery_level")
            ),
            "fuel_level": None,
            "range": self._as_float(resolved.capability_states.get("driving_range")),
            "odometer": self._as_float(resolved.capability_states.get("odometer")),
            "latitude": latitude,
            "longitude": longitude,
            "openings": self._resolve_openings(runtime),
            "doors_open": _coerce_bool_state(resolved.capability_states.get("doors")),
            "lids_open": _coerce_bool_state(resolved.capability_states.get("lids")),
            "tire_pressure": resolved.capability_states.get("tire_pressure"),
            "source_units": self._resolve_source_units(runtime),
            "source_problems": dict(resolved.errors),
        }

    async def get_capabilities(self):
        """Return capability support derived from the generic mapping runtime."""

        return self._resolve_runtime().capabilities

    async def execute_action(self, action: str, **kwargs: Any) -> ActionResult:
        """Execute one canonical action via the mapped runtime."""

        _ = kwargs
        runtime = self._runtime()
        capability_name = self._capability_for_action(runtime, action)
        if capability_name is None:
            raise UnsupportedVehicleActionError(f"Unsupported action: {action}")
        return await runtime.async_execute_action(capability_name, action)

    async def get_diagnostics(self) -> dict[str, Any]:
        """Return read-only mapping diagnostics for the selected source vehicle."""

        runtime = self._runtime()
        resolved = runtime.resolve()
        raw_state = await self.get_raw_state()
        raw_metrics = await self.get_raw_metrics()

        return {
            "adapter_type": "mapped",
            "friendly_name": self.get_friendly_name(),
            "mapping_name": self._mapping_name,
            "integration_domain": self._mapping.integration.domain,
            "vehicle_id": self._vehicle_id,
            "source_vehicle": self._source_vehicle_token(),
            "source_device_id": self._source_device_id(),
            "source_entities": runtime.source_entity_snapshot(),
            "raw_state": dict(raw_state),
            "raw_metrics": dict(raw_metrics),
            "resolved_capability_states": dict(resolved.capability_states),
            "capabilities": {
                capability_name: {
                    "state_supported": support.state_supported,
                    "action_supported": support.action_supported,
                }
                for capability_name, support in resolved.capabilities.items()
            },
            "actions": {
                capability_name: {
                    action_name: {
                        "service": prepared.service,
                        "data": dict(prepared.data),
                        "target": dict(prepared.target),
                    }
                    for action_name, prepared in action_map.items()
                }
                for capability_name, action_map in resolved.actions.items()
            },
            "source_problems": dict(resolved.errors),
        }

    @property
    def _vehicle(self) -> dict[str, Any]:
        return self._vehicles[self._vehicle_id]

    def _runtime(self) -> MappingRuntime:
        if self._hass is None:
            raise ValueError("Mapped vehicle adapter requires hass for runtime resolution")
        return MappingRuntime(
            self._hass,
            self._mapping,
            vehicle=self._source_vehicle_token(),
            device=self._source_device_id(),
        )

    def _resolve_runtime(self):
        return self._runtime().resolve()

    def _source_vehicle_token(self) -> str:
        token = self._as_str(self._vehicle.get("source_vehicle"))
        if not token:
            raise ValueError("Mapped vehicle payload requires source_vehicle")
        return token

    def _source_device_id(self) -> str:
        device_id = self._as_str(self._vehicle.get("source_device_id"))
        if not device_id:
            raise ValueError("Mapped vehicle payload requires source_device_id")
        return device_id

    def _resolve_coordinates(self, runtime: MappingRuntime) -> tuple[float | None, float | None]:
        location_mapping = self._mapping.capability("location")
        if (
            location_mapping is None
            or location_mapping.state.entity is None
        ):
            return None, None

        entity_id = _substitute_string(
            location_mapping.state.entity,
            self._source_vehicle_token(),
            self._source_device_id(),
        )
        latitude = self._as_float(runtime.state_attr(entity_id, "latitude"))
        longitude = self._as_float(runtime.state_attr(entity_id, "longitude"))
        return latitude, longitude

    def _resolve_openings(self, runtime: MappingRuntime) -> dict[str, str]:
        windows_mapping = self._mapping.capability("windows")
        if windows_mapping is None or windows_mapping.state is None:
            return {}

        state_mapping = windows_mapping.state
        entity_ids = state_mapping.any or state_mapping.all
        if not entity_ids:
            return {}

        openings: dict[str, str] = {}
        for entity_pattern in entity_ids:
            entity_id = _substitute_string(
                entity_pattern,
                self._source_vehicle_token(),
                self._source_device_id(),
            )
            object_id = entity_id.split(".", 1)[-1]
            openings[object_id] = (
                "open" if _coerce_bool_state(runtime.state_value(entity_id)) else "closed"
            )
        return openings

    def _resolve_source_units(self, runtime: MappingRuntime) -> dict[str, str]:
        for capability_name in ("driving_range", "odometer"):
            capability_mapping = self._mapping.capability(capability_name)
            if capability_mapping is None or capability_mapping.state.entity is None:
                continue
            entity_id = _substitute_string(
                capability_mapping.state.entity,
                self._source_vehicle_token(),
                self._source_device_id(),
            )
            unit = runtime.state_attr(entity_id, "unit_of_measurement")
            if isinstance(unit, str) and unit:
                return {"distance_unit": unit}
        return {}

    def _refresh_vehicle_payload(self) -> dict[str, Any] | None:
        helper = self._discovery_helper
        if helper is not None:
            refresh = getattr(helper, "build_vehicle_payload_from_hass", None)
            if refresh is None:
                return None
            return refresh(self._hass, self._vehicle_id)
        return build_vehicle_payload_from_hass(
            self._hass,
            self._mapping,
            self._vehicle_id,
        )

    def _capability_for_action(
        self, runtime: MappingRuntime, action: str
    ) -> str | None:
        for capability_name, prepared_actions in runtime.resolve().actions.items():
            if action in prepared_actions:
                return capability_name
        return None

    def _merge_vehicle_payloads(
        self,
        stored_vehicle: dict[str, Any],
        refreshed_vehicle: dict[str, Any],
    ) -> dict[str, Any]:
        merged = deepcopy(stored_vehicle)
        for field_name in (
            "name",
            "manufacturer",
            "model",
            "vehicle_type",
            "source_vehicle",
            "source_device_id",
            "status",
            "available",
            "backend_online",
            "has_error",
            "driving",
            "charging_active",
            "charging_plugged",
        ):
            refreshed_value = refreshed_vehicle.get(field_name)
            if refreshed_value is not None:
                merged[field_name] = refreshed_value

        for list_field in ("source_entity_ids",):
            merged[list_field] = _merge_entity_id_lists(
                stored_vehicle.get(list_field),
                refreshed_vehicle.get(list_field),
            )
        return merged

    def _derive_status(
        self,
        *,
        available: bool,
        backend_online: bool,
        has_error: bool,
        driving: bool,
        charging_active: bool,
    ) -> str:
        if has_error:
            return "error"
        if charging_active:
            return "charging"
        if not backend_online:
            return "offline"
        if driving:
            return "driving"
        if not available:
            return "unavailable"
        return "parked"

    def _as_bool(self, value: Any, default: bool | None = None) -> bool | None:
        if isinstance(value, bool):
            return value
        return default

    def _as_float(self, value: Any) -> float | None:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return None
        return None

    def _as_str(self, value: Any) -> str | None:
        return value if isinstance(value, str) else None


def _coerce_lock_state(value: Any) -> bool | None:
    normalized = str(value).strip().lower()
    if normalized in {"locked", "lock", "true", "on", "1"}:
        return True
    if normalized in {"unlocked", "unlock", "false", "off", "0"}:
        return False
    return value if isinstance(value, bool) else None


def _coerce_bool_state(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"on", "open", "true", "1", "charging", "locked", "home"}:
        return True
    if normalized in {"off", "closed", "false", "0", "unavailable", "unknown"}:
        return False
    return None


def _substitute_string(value: str, vehicle: str, device: str) -> str:
    return value.replace("{vehicle}", vehicle).replace("{device}", device)


def _merge_entity_id_lists(*values: Any) -> list[str]:
    merged: list[str] = []
    for value in values:
        if not isinstance(value, list):
            continue
        for entity_id in value:
            if not isinstance(entity_id, str) or "." not in entity_id:
                continue
            if entity_id not in merged:
                merged.append(entity_id)
    return merged
