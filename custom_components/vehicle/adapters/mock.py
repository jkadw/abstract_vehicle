"""Mock adapter for domain and entity development."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .base import (
    ActionResult,
    DiscoveredVehicle,
    RawMetricsPayload,
    RawStatePayload,
    UnsupportedVehicleActionError,
    VehicleAdapter,
)
from ..model import CapabilitySupport, VehicleCapabilities


class MockVehicleAdapter(VehicleAdapter):
    """Small in-memory adapter with realistic sample data."""

    @classmethod
    async def async_discover_vehicles(cls, hass: Any) -> list[DiscoveredVehicle]:
        """Expose a single development vehicle for config-flow discovery."""

        _ = hass
        adapter = cls()
        payload = {
            "vehicle_id": "mock-vehicle-001",
            "name": "Family EV",
            "manufacturer": "Mock Motors",
            "model": "Atlas",
            "vehicle_type": "ev",
            "available": True,
            "backend_online": True,
            "has_error": False,
            "driving": False,
            "charging_active": False,
            "charging_plugged": True,
            "locked": True,
            "climate_active": False,
            "metrics": dict(adapter._base_metrics),
            "openings": dict(adapter._base_metrics["openings"]),
            "source_units": dict(adapter._base_metrics["source_units"]),
            "capabilities": {
                "lock": {"state_supported": True, "action_supported": True},
                "windows": {"state_supported": True, "action_supported": False},
                "climate": {"state_supported": True, "action_supported": True},
                "charging": {"state_supported": True, "action_supported": False},
                "location": {"state_supported": True, "action_supported": False},
                "battery": {"state_supported": True, "action_supported": False},
                "fuel": {"state_supported": False, "action_supported": False},
                "odometer": {"state_supported": True, "action_supported": False},
            },
        }
        return [
            DiscoveredVehicle(
                vehicle_id="mock-vehicle-001",
                title="Mock Motors Atlas",
                payload=payload,
            )
        ]

    def __init__(self, initial_state: str = "parked") -> None:
        self._vehicle_info: RawStatePayload = {
            "vehicle_id": "mock-vehicle-001",
            "name": "Family EV",
            "manufacturer": "Mock Motors",
            "model": "Atlas",
            "vehicle_type": "ev",
        }
        self._base_state: RawStatePayload = {
            "status": "parked",
            "available": True,
            "backend_online": True,
            "has_error": False,
            "driving": False,
            "charging_active": False,
            "charging_plugged": True,
            "locked": True,
            "climate_active": False,
        }
        self._base_metrics: RawMetricsPayload = {
            "battery_level": 72.5,
            "fuel_level": None,
            "range": 248.0,
            "odometer": 18342.4,
            "latitude": 37.7749,
            "longitude": -122.4194,
            "openings": {
                "front_left_window": "closed",
                "front_right_window": "closed",
                "rear_left_window": "closed",
                "rear_right_window": "closed",
                "sunroof": "closed",
            },
            "source_units": {
                "distance_unit": "km",
                "temperature_unit": "C",
                "power_unit": "kW",
                "energy_unit": "kWh",
            },
        }
        self._state: RawStatePayload = deepcopy(self._base_state)
        self._metrics: RawMetricsPayload = deepcopy(self._base_metrics)
        self._capabilities = VehicleCapabilities(
            lock=CapabilitySupport(state_supported=True, action_supported=True),
            windows=CapabilitySupport(state_supported=True, action_supported=False),
            climate=CapabilitySupport(state_supported=True, action_supported=True),
            charging=CapabilitySupport(state_supported=True, action_supported=False),
            location=CapabilitySupport(state_supported=True, action_supported=False),
            battery=CapabilitySupport(state_supported=True, action_supported=False),
            fuel=CapabilitySupport(state_supported=False, action_supported=False),
            odometer=CapabilitySupport(state_supported=True, action_supported=False),
        )
        self.set_scenario(initial_state)

    async def get_raw_state(self) -> RawStatePayload:
        """Return raw operational state for the mock vehicle."""

        return {**self._vehicle_info, **self._state}

    async def get_raw_metrics(self) -> RawMetricsPayload:
        """Return raw metrics for the mock vehicle."""

        return {
            **self._metrics,
            "openings": dict(self._metrics["openings"]),
            "source_units": dict(self._metrics["source_units"]),
        }

    async def get_capabilities(self) -> VehicleCapabilities:
        """Return structured support flags."""

        return self._capabilities

    async def execute_action(self, action: str, **kwargs: Any) -> ActionResult:
        """Apply simple internal transitions for supported actions."""

        _ = kwargs
        if action == "lock" and self._capabilities.lock.action_supported:
            self._state["locked"] = True
        elif action == "unlock" and self._capabilities.lock.action_supported:
            self._state["locked"] = False
        elif action == "start_climate" and self._capabilities.climate.action_supported:
            self._state["climate_active"] = True
        elif action == "stop_climate" and self._capabilities.climate.action_supported:
            self._state["climate_active"] = False
        else:
            raise UnsupportedVehicleActionError(f"Unsupported action: {action}")

        return {"success": True, "action": action}

    def set_scenario(self, scenario: str) -> None:
        """Apply one of the supported mock backend scenarios."""

        self._state = deepcopy(self._base_state)
        self._metrics = deepcopy(self._base_metrics)

        if scenario == "parked":
            return

        if scenario == "charging":
            self._state["status"] = "charging"
            self._state["charging_active"] = True
            self._state["charging_plugged"] = True
            self._state["climate_active"] = False
            self._metrics["battery_level"] = 79.0
            self._metrics["range"] = 272.0
            return

        if scenario == "offline":
            self._state["status"] = "offline"
            self._state["backend_online"] = False
            self._state["available"] = True
            self._state["charging_active"] = False
            self._state["climate_active"] = False
            return

        raise ValueError(f"Unsupported mock scenario: {scenario}")
