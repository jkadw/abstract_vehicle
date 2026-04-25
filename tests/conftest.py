"""Test fixtures for the vehicle integration."""

from __future__ import annotations

import sys
import types
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if "voluptuous" not in sys.modules:
    voluptuous = types.ModuleType("voluptuous")

    def _schema(value):
        return value

    def _required(value, default=None):
        _ = default
        return value

    def _any(*validators):
        _ = validators
        return lambda value: value

    def _in(options):
        _ = options
        return lambda value: value

    voluptuous.Schema = _schema
    voluptuous.Required = _required
    voluptuous.Any = _any
    voluptuous.In = _in
    sys.modules["voluptuous"] = voluptuous

if "homeassistant" not in sys.modules:
    homeassistant = types.ModuleType("homeassistant")
    const = types.ModuleType("homeassistant.const")
    config_entries = types.ModuleType("homeassistant.config_entries")
    core = types.ModuleType("homeassistant.core")
    exceptions = types.ModuleType("homeassistant.exceptions")
    helpers = types.ModuleType("homeassistant.helpers")
    entity_module = types.ModuleType("homeassistant.helpers.entity")
    device_registry_module = types.ModuleType("homeassistant.helpers.device_registry")
    entity_registry_module = types.ModuleType("homeassistant.helpers.entity_registry")
    config_validation_module = types.ModuleType("homeassistant.helpers.config_validation")
    data_entry_flow = types.ModuleType("homeassistant.data_entry_flow")
    components = types.ModuleType("homeassistant.components")
    sensor = types.ModuleType("homeassistant.components.sensor")
    entity_platform = types.ModuleType("homeassistant.helpers.entity_platform")

    class ConfigFlow:
        def __init_subclass__(cls, **kwargs):
            _ = kwargs
            return super().__init_subclass__()

    class ConfigEntry:
        def __init__(self, entry_id: str = "entry-1", data: dict | None = None):
            self.entry_id = entry_id
            self.data = data or {}

    class HomeAssistant:
        def __init__(self):
            self.data = {}

    class Event:
        def __init__(self, data: dict | None = None):
            self.data = data or {}

    class ServiceCall:
        def __init__(self, data: dict):
            self.data = data

    class HomeAssistantError(Exception):
        pass

    class ServiceValidationError(HomeAssistantError):
        pass

    class Entity:
        def async_write_ha_state(self) -> None:
            return None

    class DeviceInfo(dict):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)

    class SensorEntity(Entity):
        pass

    const.EVENT_HOMEASSISTANT_STARTED = "homeassistant_started"
    config_entries.ConfigFlow = ConfigFlow
    config_entries.ConfigEntry = ConfigEntry
    core.HomeAssistant = HomeAssistant
    core.Event = Event
    core.ServiceCall = ServiceCall
    exceptions.HomeAssistantError = HomeAssistantError
    exceptions.ServiceValidationError = ServiceValidationError
    entity_module.Entity = Entity
    device_registry_module.DeviceInfo = DeviceInfo
    entity_registry_module.async_get = lambda hass: None
    config_validation_module.entity_id = lambda value: value
    config_validation_module.string = lambda value: value
    data_entry_flow.FlowResult = dict
    sensor.SensorEntity = SensorEntity
    entity_platform.AddEntitiesCallback = object

    helpers.entity = entity_module
    helpers.device_registry = device_registry_module
    helpers.entity_registry = entity_registry_module
    helpers.config_validation = config_validation_module
    homeassistant.const = const
    homeassistant.config_entries = config_entries
    homeassistant.core = core
    homeassistant.exceptions = exceptions
    homeassistant.helpers = helpers
    homeassistant.data_entry_flow = data_entry_flow
    homeassistant.components = components
    components.sensor = sensor

    sys.modules["homeassistant"] = homeassistant
    sys.modules["homeassistant.const"] = const
    sys.modules["homeassistant.config_entries"] = config_entries
    sys.modules["homeassistant.core"] = core
    sys.modules["homeassistant.exceptions"] = exceptions
    sys.modules["homeassistant.helpers"] = helpers
    sys.modules["homeassistant.helpers.entity"] = entity_module
    sys.modules["homeassistant.helpers.device_registry"] = device_registry_module
    sys.modules["homeassistant.helpers.entity_registry"] = entity_registry_module
    sys.modules["homeassistant.helpers.config_validation"] = config_validation_module
    sys.modules["homeassistant.data_entry_flow"] = data_entry_flow
    sys.modules["homeassistant.components"] = components
    sys.modules["homeassistant.components.sensor"] = sensor
    sys.modules["homeassistant.helpers.entity_platform"] = entity_platform
