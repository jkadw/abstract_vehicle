"""Adapter interfaces for vehicle data sources."""

from .base import (
    ActionResult,
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
    "KiaHyundaiVehicleAdapter",
    "KiaUvoVehicleAdapter",
    "MockVehicleAdapter",
    "RawMetricsPayload",
    "RawStatePayload",
    "UnsupportedVehicleActionError",
    "VehicleAdapter",
    "VehicleAdapterError",
]
