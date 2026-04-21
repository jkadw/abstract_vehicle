"""Constants for the vehicle integration."""

from typing import Final

DOMAIN: Final = "vehicle"
PLATFORMS: Final[tuple[str, ...]] = ("sensor",)

CONF_ADAPTER: Final = "adapter"
CONF_VEHICLE_ID: Final = "vehicle_id"
CONF_VEHICLES: Final = "vehicles"

ADAPTER_TYPE_MOCK: Final = "mock"
ADAPTER_TYPE_KIA_UVO: Final = "kia_uvo"

DEFAULT_ENTRY_TITLE: Final = "Vehicle"

DATA_ADAPTER: Final = "adapter"
DATA_NORMALIZED: Final = "normalized_data"
DATA_ENTITY: Final = "entity"
DATA_SERVICES_REGISTERED: Final = "services_registered"

SERVICE_LOCK: Final = "lock"
SERVICE_UNLOCK: Final = "unlock"
SERVICE_START_CLIMATE: Final = "start_climate"
SERVICE_STOP_CLIMATE: Final = "stop_climate"

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
)
