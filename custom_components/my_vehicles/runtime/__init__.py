"""Runtime exports for the My Vehicles integration."""

from .base import (
    UnsupportedVehicleActionError,
    VehicleAdapter,
    VehicleAdapterError,
)
from .loader import (
    create_adapter_from_entry,
    create_adapter_from_discovered_vehicle,
    discover_adapter_vehicles,
    get_available_adapter_definitions,
    get_available_adapter_options,
)
from .mapped import MappedVehicleAdapter
from .registry import (
    async_get_adapter_definition,
    async_get_adapter_definitions,
)

__all__ = [
    "MappedVehicleAdapter",
    "UnsupportedVehicleActionError",
    "VehicleAdapter",
    "VehicleAdapterError",
    "create_adapter_from_entry",
    "create_adapter_from_discovered_vehicle",
    "discover_adapter_vehicles",
    "async_get_adapter_definition",
    "async_get_adapter_definitions",
    "get_available_adapter_definitions",
    "get_available_adapter_options",
]
