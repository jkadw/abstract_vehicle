"""Constants for the My Vehicles integration."""

from typing import Final

from .domain.capability_registry import DOCUMENTED_ATTRIBUTE_SCHEMA as REGISTRY_ATTRIBUTE_SCHEMA

DOMAIN: Final = "my_vehicles"
PLATFORMS: Final[tuple[str, ...]] = (
    "sensor",
    "binary_sensor",
    "lock",
    "switch",
    "device_tracker",
    "button",
)

CONF_ADAPTER: Final = "adapter"
CONF_VEHICLE_ID: Final = "vehicle_id"
CONF_VEHICLES: Final = "vehicles"

DEFAULT_ENTRY_TITLE: Final = "My Vehicles"

DATA_ADAPTER: Final = "adapter"
DATA_NORMALIZED: Final = "normalized_data"
DATA_ENTITIES: Final = "entities"
DATA_VEHICLES: Final = "vehicles"
DATA_DISCOVERY_SNAPSHOTS: Final = "discovery_snapshots"
DATA_SERVICES_REGISTERED: Final = "services_registered"

SERVICE_DIAGNOSTICS: Final = "diagnostics"

NORMALIZED_STATES: Final[tuple[str, ...]] = (
    "unknown",
    "unavailable",
    "offline",
    "parked",
    "charging",
    "driving",
    "error",
)

DOCUMENTED_ATTRIBUTE_SCHEMA: Final[tuple[str, ...]] = REGISTRY_ATTRIBUTE_SCHEMA
