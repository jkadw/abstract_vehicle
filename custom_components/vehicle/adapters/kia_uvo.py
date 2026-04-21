"""Adapter for vehicles sourced from the Hyundai-Kia-Connect/kia_uvo integration."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .base import (
    ActionResult,
    RawMetricsPayload,
    RawStatePayload,
    UnsupportedVehicleActionError,
    VehicleAdapter,
)
from ..model import CapabilitySupport, VehicleCapabilities


class KiaUvoVehicleAdapter(VehicleAdapter):
    """Map configured kia_uvo vehicle payloads into the shared adapter interface."""

    def __init__(
        self,
        vehicles: list[dict[str, Any]],
        vehicle_id: str | None = None,
    ) -> None:
        if not vehicles:
            raise ValueError("kia_uvo adapter requires at least one configured vehicle")

        self._vehicles: dict[str, dict[str, Any]] = {}
        for vehicle in vehicles:
            raw_vehicle_id = vehicle.get("vehicle_id") or vehicle.get("id")
            if not isinstance(raw_vehicle_id, str) or not raw_vehicle_id:
                raise ValueError("Each configured kia_uvo vehicle requires a vehicle_id")
            self._vehicles[raw_vehicle_id] = deepcopy(vehicle)

        self._vehicle_id = vehicle_id or next(iter(self._vehicles))
        if self._vehicle_id not in self._vehicles:
            raise ValueError(f"Configured kia_uvo vehicle_id not found: {self._vehicle_id}")

    async def get_raw_state(self) -> RawStatePayload:
        """Return raw state for the configured kia_uvo vehicle."""

        vehicle = self._vehicle
        status = vehicle.get("status")
        if not isinstance(status, str):
            status = self._derive_status(vehicle)

        return {
            "vehicle_id": self._vehicle_id,
            "name": self._as_str(vehicle.get("name")) or "Kia UVO Vehicle",
            "manufacturer": self._as_str(vehicle.get("manufacturer")) or "Kia/Hyundai",
            "model": self._as_str(vehicle.get("model")) or "Unknown",
            "vehicle_type": self._as_str(vehicle.get("vehicle_type")) or "unknown",
            "status": status,
            "available": self._as_bool(vehicle.get("available"), default=True),
            "backend_online": self._as_bool(vehicle.get("backend_online"), default=True),
            "has_error": self._as_bool(vehicle.get("has_error"), default=False),
            "driving": self._as_bool(vehicle.get("driving"), default=False),
            "charging_active": self._as_bool(
                vehicle.get("charging_active"), default=False
            ),
            "charging_plugged": self._as_bool(
                vehicle.get("charging_plugged"), default=False
            ),
            "locked": self._as_bool(vehicle.get("locked")),
            "climate_active": self._as_bool(vehicle.get("climate_active")),
        }

    async def get_raw_metrics(self) -> RawMetricsPayload:
        """Return raw metrics for the configured kia_uvo vehicle."""

        vehicle = self._vehicle
        metrics = vehicle.get("metrics")
        if not isinstance(metrics, dict):
            metrics = {}

        openings = vehicle.get("openings")
        if not isinstance(openings, dict):
            openings = {}

        source_units = vehicle.get("source_units")
        if not isinstance(source_units, dict):
            source_units = {}

        return {
            "battery_level": self._as_float(metrics.get("battery_level")),
            "fuel_level": self._as_float(metrics.get("fuel_level")),
            "range": self._as_float(metrics.get("range")),
            "odometer": self._as_float(metrics.get("odometer")),
            "latitude": self._as_float(metrics.get("latitude")),
            "longitude": self._as_float(metrics.get("longitude")),
            "openings": {key: str(value) for key, value in openings.items()},
            "source_units": {key: str(value) for key, value in source_units.items()},
        }

    async def get_capabilities(self) -> VehicleCapabilities:
        """Return declared capability support for the configured kia_uvo vehicle."""

        capabilities = self._vehicle.get("capabilities")
        if not isinstance(capabilities, dict):
            capabilities = {}

        return VehicleCapabilities(
            lock=self._capability_support(capabilities.get("lock")),
            windows=self._capability_support(capabilities.get("windows")),
            climate=self._capability_support(capabilities.get("climate")),
            charging=self._capability_support(capabilities.get("charging")),
            location=self._capability_support(capabilities.get("location")),
            battery=self._capability_support(capabilities.get("battery")),
            fuel=self._capability_support(capabilities.get("fuel")),
            odometer=self._capability_support(capabilities.get("odometer")),
        )

    async def execute_action(self, action: str, **kwargs: Any) -> ActionResult:
        """Apply a supported action to the configured kia_uvo vehicle payload."""

        _ = kwargs
        capabilities = await self.get_capabilities()
        vehicle = self._vehicle

        if action in {"lock", "unlock"}:
            if not capabilities.lock.action_supported:
                raise UnsupportedVehicleActionError(f"Unsupported action: {action}")
            vehicle["locked"] = action == "lock"
        elif action in {"start_climate", "stop_climate"}:
            if not capabilities.climate.action_supported:
                raise UnsupportedVehicleActionError(f"Unsupported action: {action}")
            vehicle["climate_active"] = action == "start_climate"
        else:
            raise UnsupportedVehicleActionError(f"Unsupported action: {action}")

        vehicle["status"] = self._derive_status(vehicle)
        return {"success": True, "action": action}

    @property
    def _vehicle(self) -> dict[str, Any]:
        return self._vehicles[self._vehicle_id]

    def _capability_support(self, raw_support: Any) -> CapabilitySupport:
        if not isinstance(raw_support, dict):
            return CapabilitySupport()
        return CapabilitySupport(
            state_supported=self._as_bool(
                raw_support.get("state_supported"), default=False
            ),
            action_supported=self._as_bool(
                raw_support.get("action_supported"), default=False
            ),
        )

    def _derive_status(self, vehicle: dict[str, Any]) -> str:
        if self._as_bool(vehicle.get("has_error"), default=False):
            return "error"
        if self._as_bool(vehicle.get("charging_active"), default=False):
            return "charging"
        if not self._as_bool(vehicle.get("backend_online"), default=True):
            return "offline"
        if self._as_bool(vehicle.get("driving"), default=False):
            return "driving"
        if not self._as_bool(vehicle.get("available"), default=True):
            return "unavailable"
        return "parked"

    def _as_bool(self, value: Any, default: bool | None = None) -> bool | None:
        if isinstance(value, bool):
            return value
        return default

    def _as_float(self, value: Any) -> float | None:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
        return None

    def _as_str(self, value: Any) -> str | None:
        return value if isinstance(value, str) else None
