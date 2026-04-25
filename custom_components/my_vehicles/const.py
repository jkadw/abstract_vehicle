"""Constants for the My Vehicles integration."""

from typing import Final

DOMAIN: Final = "my_vehicles"
PLATFORMS: Final[tuple[str, ...]] = (
    "sensor",
    "binary_sensor",
    "lock",
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

SERVICE_LOCK: Final = "lock"
SERVICE_UNLOCK: Final = "unlock"
SERVICE_START_CLIMATE: Final = "start_climate"
SERVICE_STOP_CLIMATE: Final = "stop_climate"
SERVICE_REFRESH: Final = "refresh"
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

CORE_CAPABILITIES: Final[tuple[str, ...]] = (
    "lock",
    "windows",
    "climate",
    "charging",
    "location",
    "battery",
    "fuel",
    "odometer",
    "refresh",
)

DOCUMENTED_ATTRIBUTE_SCHEMA: Final[tuple[str, ...]] = (
    "manufacturer",
    "model",
    "vehicle_type",
    "battery_level",
    "fuel_level",
    "range",
    "locked",
    "windows_open",
    "climate_active",
    "charging_active",
    "charging_plugged",
    "latitude",
    "longitude",
    "odometer",
    "lock_state_supported",
    "lock_action_supported",
    "windows_state_supported",
    "windows_action_supported",
    "climate_state_supported",
    "climate_action_supported",
    "charging_state_supported",
    "charging_action_supported",
    "location_state_supported",
    "location_action_supported",
    "battery_state_supported",
    "battery_action_supported",
    "fuel_state_supported",
    "fuel_action_supported",
    "odometer_state_supported",
    "odometer_action_supported",
    "refresh_state_supported",
    "refresh_action_supported",
)
