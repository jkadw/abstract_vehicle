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
from .hyundai_kia_connect_kia_uvo import HyundaiKiaConnectKiaUvoVehicleAdapter
from .kia_uvo import KiaUvoVehicleAdapter
from .mock import MockVehicleAdapter

__all__ = [
    "ActionResult",
    "DiscoveredVehicle",
    "HyundaiKiaConnectKiaUvoVehicleAdapter",
    "KiaUvoVehicleAdapter",
    "MockVehicleAdapter",
    "RawMetricsPayload",
    "RawStatePayload",
    "UnsupportedVehicleActionError",
    "VehicleAdapter",
    "VehicleAdapterError",
]
