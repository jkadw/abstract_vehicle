"""Canonical vehicle domain model for the integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .const import CORE_CAPABILITIES, DOCUMENTED_ATTRIBUTE_SCHEMA, NORMALIZED_STATES


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
    """Capability support matrix for the normalized vehicle model."""

    lock: CapabilitySupport = field(default_factory=CapabilitySupport)
    windows: CapabilitySupport = field(default_factory=CapabilitySupport)
    climate: CapabilitySupport = field(default_factory=CapabilitySupport)
    charging: CapabilitySupport = field(default_factory=CapabilitySupport)
    location: CapabilitySupport = field(default_factory=CapabilitySupport)
    battery: CapabilitySupport = field(default_factory=CapabilitySupport)
    fuel: CapabilitySupport = field(default_factory=CapabilitySupport)
    odometer: CapabilitySupport = field(default_factory=CapabilitySupport)


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
    battery_level: float | None = None
    fuel_level: float | None = None
    range: float | None = None
    locked: bool | None = None
    windows_open: bool | None = None
    climate_active: bool | None = None
    charging_active: bool | None = None
    charging_plugged: bool | None = None
    latitude: float | None = None
    longitude: float | None = None
    odometer: float | None = None
    source_units: SourceUnits = field(default_factory=SourceUnits)
    display_units: SourceUnits = field(default_factory=SourceUnits)
