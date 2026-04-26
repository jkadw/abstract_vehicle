"""Canonical vehicle domain model for the integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterator

from .capability_registry import (
    CANONICAL_ACTIONS,
    CORE_CAPABILITIES,
    DOCUMENTED_ATTRIBUTE_SCHEMA,
)
from ..const import NORMALIZED_STATES


class VehicleState(str, Enum):
    """Normalized high-level vehicle states."""

    UNKNOWN = NORMALIZED_STATES[0]
    UNAVAILABLE = NORMALIZED_STATES[1]
    OFFLINE = NORMALIZED_STATES[2]
    PARKED = NORMALIZED_STATES[3]
    CHARGING = NORMALIZED_STATES[4]
    DRIVING = NORMALIZED_STATES[5]
    ERROR = NORMALIZED_STATES[6]


@dataclass(frozen=True, slots=True)
class CapabilitySupport:
    """Structured support flags for a single capability."""

    state_supported: bool = False
    action_supported: bool = False


@dataclass(frozen=True, slots=True)
class VehicleCapabilities:
    """Capability support matrix keyed by canonical capability name."""

    _supports: dict[str, CapabilitySupport] = field(init=False, repr=False)

    def __init__(self, **supports: CapabilitySupport) -> None:
        unknown = sorted(set(supports) - set(CORE_CAPABILITIES))
        if unknown:
            raise ValueError(
                f"Unknown canonical capabilities: {', '.join(unknown)}"
            )
        normalized = {
            capability_name: supports.get(capability_name, CapabilitySupport())
            for capability_name in CORE_CAPABILITIES
        }
        object.__setattr__(self, "_supports", normalized)

    def __getattr__(self, name: str) -> CapabilitySupport:
        try:
            return self._supports[name]
        except KeyError as err:
            raise AttributeError(name) from err

    def get(self, name: str) -> CapabilitySupport:
        return self._supports.get(name, CapabilitySupport())

    def items(self) -> Iterator[tuple[str, CapabilitySupport]]:
        return iter(self._supports.items())

    def as_dict(self) -> dict[str, CapabilitySupport]:
        return dict(self._supports)


DOCUMENTED_CAPABILITY_SCHEMA = CORE_CAPABILITIES


@dataclass(frozen=True, slots=True)
class VehicleInfo:
    """Stable metadata that identifies a vehicle."""

    vehicle_id: str
    name: str
    manufacturer: str
    model: str
    vehicle_type: str = "unknown"


@dataclass(frozen=True, slots=True)
class SourceUnits:
    """Raw source units for future normalization hooks."""

    distance_unit: str | None = None
    temperature_unit: str | None = None
    power_unit: str | None = None
    energy_unit: str | None = None


@dataclass(frozen=True, slots=True)
class NormalizedVehicleData:
    """Normalized canonical vehicle snapshot."""

    info: VehicleInfo
    state: VehicleState
    capabilities: VehicleCapabilities
    capability_values: dict[str, object] = field(default_factory=dict)
    battery_level: float | None = None
    fuel_level: float | None = None
    driving_range: float | None = None
    range: float | None = None
    locked: bool | None = None
    windows_open: bool | None = None
    climate_active: bool | None = None
    charging_active: bool | None = None
    charging_plugged: bool | None = None
    ignition_on: bool | None = None
    range_warning: bool | None = None
    latitude: float | None = None
    longitude: float | None = None
    odometer: float | None = None
    warning_messages: object | None = None
    info_messages: object | None = None
    source_problems: dict[str, str] = field(default_factory=dict)
    source_units: SourceUnits = field(default_factory=SourceUnits)
    display_units: SourceUnits = field(default_factory=SourceUnits)
