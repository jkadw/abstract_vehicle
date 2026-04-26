"""Normalization helpers for converting raw adapter data into the domain model."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .capability_registry import CORE_CAPABILITIES
from .model import (
    CapabilitySupport,
    NormalizedVehicleData,
    SourceUnits,
    VehicleCapabilities,
    VehicleInfo,
    VehicleState,
)

def normalize_vehicle_state(raw_state: Mapping[str, Any]) -> VehicleState:
    """Map raw state signals into the canonical vehicle state."""

    if not raw_state:
        return VehicleState.UNKNOWN

    if raw_state.get("has_error") is True or raw_state.get("status") == "error":
        return VehicleState.ERROR

    if raw_state.get("charging_active") is True or raw_state.get("status") == "charging":
        return VehicleState.CHARGING

    if raw_state.get("backend_online") is False or raw_state.get("status") == "offline":
        return VehicleState.OFFLINE

    if raw_state.get("driving") is True or raw_state.get("status") == "driving":
        return VehicleState.DRIVING

    if raw_state.get("available") is False or raw_state.get("status") == "unavailable":
        return VehicleState.UNAVAILABLE

    if raw_state.get("status") == "parked":
        return VehicleState.PARKED

    return VehicleState.PARKED


def normalize_openings(openings: Mapping[str, Any] | None) -> bool | None:
    """Aggregate raw opening states into a single windows-open flag."""

    if not openings:
        return None

    return any(str(state).lower() == "open" for state in openings.values())


def normalize_source_units(raw_metrics: Mapping[str, Any]) -> SourceUnits:
    """Prepare source unit metadata for future conversions."""

    raw_units = raw_metrics.get("source_units")
    if not isinstance(raw_units, Mapping):
        return SourceUnits()

    return SourceUnits(
        distance_unit=_as_str(raw_units.get("distance_unit")),
        temperature_unit=_as_str(raw_units.get("temperature_unit")),
        power_unit=_as_str(raw_units.get("power_unit")),
        energy_unit=_as_str(raw_units.get("energy_unit")),
    )


def infer_capabilities(
    raw_state: Mapping[str, Any],
    raw_metrics: Mapping[str, Any],
    declared_capabilities: VehicleCapabilities | None = None,
) -> VehicleCapabilities:
    """Return canonical capability support without drifting from declared mapping support."""

    if declared_capabilities is not None:
        return VehicleCapabilities(
            **{
                capability_name: declared_capabilities.get(capability_name)
                for capability_name in CORE_CAPABILITIES
            }
        )

    inferred: dict[str, CapabilitySupport] = {}
    capability_values = build_capability_values(raw_state, raw_metrics)
    for capability_name in CORE_CAPABILITIES:
        inferred[capability_name] = CapabilitySupport(
            state_supported=capability_values.get(capability_name) is not None,
            action_supported=False,
        )

    return VehicleCapabilities(**inferred)


def build_capability_values(
    raw_state: Mapping[str, Any], raw_metrics: Mapping[str, Any]
) -> dict[str, object]:
    """Build canonical capability-state values from raw adapter payloads."""

    latitude = _as_float(raw_metrics.get("latitude"))
    longitude = _as_float(raw_metrics.get("longitude"))
    location_value: object | None = None
    if latitude is not None and longitude is not None:
        location_value = {
            "latitude": latitude,
            "longitude": longitude,
        }

    return {
        "lock_vehicle": _as_bool(raw_state.get("locked")),
        "climate": _as_bool(raw_state.get("climate_active")),
        "charging": _as_bool(raw_state.get("charging_active")),
        "horn": _as_bool(raw_state.get("horn_active")),
        "flash_lights": _as_bool(raw_state.get("flash_lights_active")),
        "hazard_lights": _as_bool(raw_state.get("hazard_lights_active")),
        "location": location_value,
        "ignition": _as_bool(raw_state.get("ignition_on")),
        "driving_range": _as_float(raw_metrics.get("range")),
        "range_warning": _as_boolish(
            raw_state.get("range_warning", raw_metrics.get("range_warning"))
        ),
        "odometer": _as_float(raw_metrics.get("odometer")),
        "tire_pressure": raw_metrics.get("tire_pressure"),
        "warning_messages": raw_state.get("warning_messages"),
        "info_messages": raw_state.get("info_messages"),
        "windows": normalize_openings(_as_mapping(raw_metrics.get("openings"))),
        "doors": _as_boolish(raw_metrics.get("doors_open")),
        "lids": _as_boolish(raw_metrics.get("lids_open")),
        "battery_level": _as_float(raw_metrics.get("battery_level")),
        "refresh": None,
    }


def normalize_vehicle_data(
    raw_state: Mapping[str, Any],
    raw_metrics: Mapping[str, Any],
    capabilities: VehicleCapabilities,
) -> NormalizedVehicleData:
    """Build a canonical vehicle snapshot from raw adapter payloads."""

    source_units = normalize_source_units(raw_metrics)
    capability_values = build_capability_values(raw_state, raw_metrics)
    normalized_capabilities = infer_capabilities(raw_state, raw_metrics, capabilities)
    driving_range = _as_float(capability_values.get("driving_range"))
    odometer = _as_float(capability_values.get("odometer"))
    source_problems = _as_str_mapping(
        raw_state.get("source_problems", raw_metrics.get("source_problems"))
    )

    info = VehicleInfo(
        vehicle_id=_as_str(raw_state.get("vehicle_id")) or "unknown-vehicle",
        name=_as_str(raw_state.get("name")) or "Vehicle",
        manufacturer=_as_str(raw_state.get("manufacturer")) or "Unknown",
        model=_as_str(raw_state.get("model")) or "Unknown",
        vehicle_type=_as_str(raw_state.get("vehicle_type")) or "unknown",
    )

    return NormalizedVehicleData(
        info=info,
        state=normalize_vehicle_state(raw_state),
        capabilities=normalized_capabilities,
        capability_values=capability_values,
        battery_level=_as_float(raw_metrics.get("battery_level")),
        fuel_level=_as_float(raw_metrics.get("fuel_level")),
        driving_range=driving_range,
        range=driving_range,
        locked=_as_bool(raw_state.get("locked")),
        windows_open=normalize_openings(_as_mapping(raw_metrics.get("openings"))),
        climate_active=_as_bool(raw_state.get("climate_active")),
        charging_active=_as_bool(raw_state.get("charging_active")),
        charging_plugged=_as_bool(raw_state.get("charging_plugged")),
        ignition_on=_as_bool(raw_state.get("ignition_on")),
        range_warning=_as_boolish(capability_values.get("range_warning")),
        latitude=_as_float(raw_metrics.get("latitude")),
        longitude=_as_float(raw_metrics.get("longitude")),
        odometer=odometer,
        warning_messages=capability_values.get("warning_messages"),
        info_messages=capability_values.get("info_messages"),
        source_problems=source_problems,
        source_units=source_units,
        display_units=source_units,
    )


def build_vehicle_attributes(data: NormalizedVehicleData) -> dict[str, Any]:
    """Convert normalized vehicle data into HA state attributes."""

    attributes: dict[str, Any] = {
        "manufacturer": data.info.manufacturer,
        "model": data.info.model,
        "vehicle_type": data.info.vehicle_type,
        "battery_level": data.battery_level,
        "driving_range": data.driving_range,
        "range": data.range,
        "locked": data.locked,
        "windows_open": data.windows_open,
        "climate_active": data.climate_active,
        "charging_active": data.charging_active,
        "charging_plugged": data.charging_plugged,
        "ignition_on": data.ignition_on,
        "range_warning": data.range_warning,
        "latitude": data.latitude,
        "longitude": data.longitude,
        "odometer": data.odometer,
        "warning_messages": data.warning_messages,
        "info_messages": data.info_messages,
    }
    if data.source_problems:
        attributes["source_problems"] = dict(data.source_problems)

    for capability_name in CORE_CAPABILITIES:
        support = data.capabilities.get(capability_name)
        attributes[f"{capability_name}_state_supported"] = support.state_supported
        attributes[f"{capability_name}_action_supported"] = support.action_supported

    return attributes


def _as_mapping(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _as_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _as_bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _as_boolish(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "on", "open", "1", "locked", "charging"}:
            return True
        if normalized in {"false", "off", "closed", "0", "unlocked"}:
            return False
    return None


def _as_str_mapping(value: Any) -> dict[str, str]:
    if not isinstance(value, Mapping):
        return {}
    normalized: dict[str, str] = {}
    for key, item in value.items():
        if isinstance(key, str) and isinstance(item, str):
            normalized[key] = item
    return normalized


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None
