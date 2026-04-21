"""Adapter interfaces and dynamic loading helpers for vehicle data sources."""

from .base import (
    ActionResult,
    DiscoveredVehicle,
    RawMetricsPayload,
    RawStatePayload,
    UnsupportedVehicleActionError,
    VehicleAdapter,
    VehicleAdapterError,
)
from .loader import (
    create_adapter_from_entry,
    discover_adapter_vehicles,
    get_available_adapter_definitions,
    get_available_adapter_options,
    is_adapter_available,
    load_adapter_class,
)
from .registry import ADAPTER_DEFINITIONS, AdapterDefinition, get_adapter_definition

__all__ = [
    "ActionResult",
    "ADAPTER_DEFINITIONS",
    "AdapterDefinition",
    "create_adapter_from_entry",
    "discover_adapter_vehicles",
    "DiscoveredVehicle",
    "get_adapter_definition",
    "get_available_adapter_definitions",
    "get_available_adapter_options",
    "is_adapter_available",
    "load_adapter_class",
    "RawMetricsPayload",
    "RawStatePayload",
    "UnsupportedVehicleActionError",
    "VehicleAdapter",
    "VehicleAdapterError",
]
