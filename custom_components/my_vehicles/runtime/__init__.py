"""Runtime exports for the My Vehicles integration."""

from .base import (
    UnsupportedVehicleActionError,
    VehicleAdapter,
    VehicleAdapterError,
)
from .loader import (
    create_adapter,
    create_adapter_from_entry,
    discover_adapter_vehicles,
    get_adapter_definition,
    get_adapter_definitions,
    get_available_adapter_definitions,
    get_available_adapter_options,
)
from .mapped import MappedVehicleAdapter

__all__ = [
    "MappedVehicleAdapter",
    "UnsupportedVehicleActionError",
    "VehicleAdapter",
    "VehicleAdapterError",
    "create_adapter",
    "create_adapter_from_entry",
    "discover_adapter_vehicles",
    "get_adapter_definition",
    "get_adapter_definitions",
    "get_available_adapter_definitions",
    "get_available_adapter_options",
]
