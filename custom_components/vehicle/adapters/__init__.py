"""Adapter interfaces for vehicle data sources."""

from .base import (
    ActionResult,
    DiscoveredVehicle,
    RawMetricsPayload,
    RawStatePayload,
    UnsupportedVehicleActionError,
    VehicleAdapter,
    VehicleAdapterError,
)
from .kia_hyundai import KiaHyundaiVehicleAdapter
from .kia_uvo import KiaUvoVehicleAdapter
from .mock import MockVehicleAdapter

__all__ = [
    "ActionResult",
    "DiscoveredVehicle",
    "KiaHyundaiVehicleAdapter",
    "KiaUvoVehicleAdapter",
    "MockVehicleAdapter",
    "RawMetricsPayload",
    "RawStatePayload",
    "UnsupportedVehicleActionError",
    "VehicleAdapter",
    "VehicleAdapterError",
]
