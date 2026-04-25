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
    create_adapter_from_discovered_vehicle,
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
from .mapped import MappedVehicleAdapter
from .runtime import (
    MappingRuntime,
    PreparedAction,
    ResolvedDerivedEntity,
    ResolvedMappingRuntime,
)
from .registry import (
    AdapterDefinition,
    CUSTOM_ADAPTER_DEFINITIONS,
    get_adapter_definition,
    get_adapter_definitions,
)

__all__ = [
    "ActionResult",
    "ActionMapping",
    "AdapterDefinition",
    "CUSTOM_ADAPTER_DEFINITIONS",
    "CapabilityMapping",
    "create_adapter_from_entry",
    "create_adapter_from_discovered_vehicle",
    "discover_adapter_vehicles",
    "DiscoveredVehicle",
    "get_adapter_definition",
    "get_adapter_definitions",
    "get_available_adapter_definitions",
    "get_available_adapter_options",
    "is_adapter_available",
    "load_adapter_mapping",
    "load_adapter_class",
    "load_mapping_file",
    "MappingIntegration",
    "MappingMetadata",
    "MappingValidationError",
    "MappedVehicleAdapter",
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
