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
from .mapping import (
    ActionMapping,
    CapabilityMapping,
    MappingIntegration,
    MappingMetadata,
    MappingValidationError,
    StateMapping,
    VehicleAdapterMapping,
    load_adapter_mapping,
    load_mapping_file,
)
from .runtime import (
    MappingRuntime,
    PreparedAction,
    ResolvedDerivedEntity,
    ResolvedMappingRuntime,
)
from .registry import ADAPTER_DEFINITIONS, AdapterDefinition, get_adapter_definition

__all__ = [
    "ActionResult",
    "ADAPTER_DEFINITIONS",
    "ActionMapping",
    "AdapterDefinition",
    "CapabilityMapping",
    "create_adapter_from_entry",
    "discover_adapter_vehicles",
    "DiscoveredVehicle",
    "get_adapter_definition",
    "get_available_adapter_definitions",
    "get_available_adapter_options",
    "is_adapter_available",
    "load_adapter_mapping",
    "load_adapter_class",
    "load_mapping_file",
    "MappingIntegration",
    "MappingMetadata",
    "MappingValidationError",
    "MappingRuntime",
    "PreparedAction",
    "RawMetricsPayload",
    "RawStatePayload",
    "ResolvedDerivedEntity",
    "ResolvedMappingRuntime",
    "StateMapping",
    "UnsupportedVehicleActionError",
    "VehicleAdapter",
    "VehicleAdapterMapping",
    "VehicleAdapterError",
]
