"""Normalization helpers for converting raw adapter data into the domain model."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping
from typing import Any

from .const import CORE_CAPABILITIES
from .model import (
    CapabilitySupport,
    NormalizedVehicleData,
    SourceUnits,
    VehicleCapabilities,
    VehicleInfo,
    VehicleState,
)


@dataclass(frozen=True, slots=True)
class NormalizationConfig:
    """Integration-level unit preferences for normalization."""

    distance_unit: str = "km"
    temperature_unit: str = "C"
    power_unit: str = "kW"
    energy_unit: str = "kWh"


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
    """Infer state support from raw payloads while preserving declared actions."""

    declared = declared_capabilities or VehicleCapabilities()

    inferred: dict[str, CapabilitySupport] = {}
    for capability_name in CORE_CAPABILITIES:
        declared_support = getattr(declared, capability_name)
        inferred_state = declared_support.state_supported or _infer_state_supported(
            capability_name, raw_state, raw_metrics
        )
        inferred[capability_name] = CapabilitySupport(
            state_supported=inferred_state,
            action_supported=declared_support.action_supported,
        )

    return VehicleCapabilities(**inferred)


def normalize_vehicle_data(
    raw_state: Mapping[str, Any],
    raw_metrics: Mapping[str, Any],
    capabilities: VehicleCapabilities,
    config: NormalizationConfig | None = None,
) -> NormalizedVehicleData:
    """Build a canonical vehicle snapshot from raw adapter payloads."""

    normalization_config = config or NormalizationConfig()
    source_units = normalize_source_units(raw_metrics)
    normalized_capabilities = infer_capabilities(raw_state, raw_metrics, capabilities)

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
        battery_level=_as_float(raw_metrics.get("battery_level")),
        fuel_level=_as_float(raw_metrics.get("fuel_level")),
        range=_normalize_distance(
            raw_metrics.get("range"),
            source_units.distance_unit,
            normalization_config.distance_unit,
        ),
        locked=_as_bool(raw_state.get("locked")),
        windows_open=normalize_openings(_as_mapping(raw_metrics.get("openings"))),
        climate_active=_as_bool(raw_state.get("climate_active")),
        charging_active=_as_bool(raw_state.get("charging_active")),
        charging_plugged=_as_bool(raw_state.get("charging_plugged")),
        latitude=_as_float(raw_metrics.get("latitude")),
        longitude=_as_float(raw_metrics.get("longitude")),
        odometer=_normalize_distance(
            raw_metrics.get("odometer"),
            source_units.distance_unit,
            normalization_config.distance_unit,
        ),
        source_units=source_units,
    )


def build_vehicle_attributes(data: NormalizedVehicleData) -> dict[str, Any]:
    """Convert normalized vehicle data into HA state attributes."""

    attributes: dict[str, Any] = {
        "manufacturer": data.info.manufacturer,
        "model": data.info.model,
        "vehicle_type": data.info.vehicle_type,
        "battery_level": data.battery_level,
        "fuel_level": data.fuel_level,
        "range": data.range,
        "locked": data.locked,
        "windows_open": data.windows_open,
        "climate_active": data.climate_active,
        "charging_active": data.charging_active,
        "charging_plugged": data.charging_plugged,
        "latitude": data.latitude,
        "longitude": data.longitude,
        "odometer": data.odometer,
    }

    for capability_name in (
        "lock",
        "windows",
        "climate",
        "charging",
        "location",
        "battery",
        "fuel",
        "odometer",
    ):
        support = getattr(data.capabilities, capability_name)
        attributes[f"{capability_name}_state_supported"] = support.state_supported
        attributes[f"{capability_name}_action_supported"] = support.action_supported

    return attributes


def _normalize_distance(
    value: Any, source_unit: str | None, target_unit: str
) -> float | None:
    """Normalize distance-based values into the configured unit."""

    numeric_value = _as_float(value)
    if numeric_value is None:
        return None

    normalized_source = _normalize_distance_unit(source_unit)
    normalized_target = _normalize_distance_unit(target_unit)
    if normalized_source is None or normalized_source == normalized_target:
        return numeric_value
    if normalized_source == "km" and normalized_target == "mi":
        return round(numeric_value * 0.621371, 3)
    if normalized_source == "mi" and normalized_target == "km":
        return round(numeric_value / 0.621371, 3)
    return numeric_value


def _infer_state_supported(
    capability_name: str, raw_state: Mapping[str, Any], raw_metrics: Mapping[str, Any]
) -> bool:
    if capability_name == "lock":
        return isinstance(raw_state.get("locked"), bool)
    if capability_name == "windows":
        return isinstance(raw_metrics.get("openings"), Mapping)
    if capability_name == "climate":
        return isinstance(raw_state.get("climate_active"), bool)
    if capability_name == "charging":
        return any(
            isinstance(raw_state.get(key), bool)
            for key in ("charging_active", "charging_plugged")
        )
    if capability_name == "location":
        return _as_float(raw_metrics.get("latitude")) is not None and _as_float(
            raw_metrics.get("longitude")
        ) is not None
    if capability_name == "battery":
        return _as_float(raw_metrics.get("battery_level")) is not None
    if capability_name == "fuel":
        return _as_float(raw_metrics.get("fuel_level")) is not None
    if capability_name == "odometer":
        return _as_float(raw_metrics.get("odometer")) is not None
    return False


def _normalize_distance_unit(unit: str | None) -> str | None:
    if unit is None:
        return None
    normalized = unit.lower()
    if normalized in {"km", "kilometer", "kilometers"}:
        return "km"
    if normalized in {"mi", "mile", "miles"}:
        return "mi"
    return None


def _as_mapping(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _as_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _as_bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None
