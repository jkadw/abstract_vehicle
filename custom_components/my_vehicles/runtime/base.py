"""Abstract adapter contract for raw vehicle data sources."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, TypedDict

from ..model import VehicleCapabilities


@dataclass(frozen=True, slots=True)
class DiscoveredVehicle:
    """Vehicle metadata returned during config-flow discovery."""

    vehicle_id: str
    title: str
    payload: dict[str, Any]


class RawStatePayload(TypedDict, total=False):
    """Loose raw state payload returned by adapters."""

    vehicle_id: str
    name: str
    manufacturer: str
    model: str
    vehicle_type: str
    status: str
    available: bool
    backend_online: bool
    has_error: bool
    driving: bool
    charging_active: bool
    charging_plugged: bool
    locked: bool
    climate_active: bool


class RawMetricsPayload(TypedDict, total=False):
    """Loose raw metrics payload returned by adapters."""

    battery_level: float
    fuel_level: float | None
    range: float
    odometer: float
    latitude: float
    longitude: float
    openings: Mapping[str, str]
    source_units: Mapping[str, str]


class ActionResult(TypedDict, total=False):
    """Result payload for adapter actions."""

    success: bool
    action: str
    message: str


class VehicleAdapterError(Exception):
    """Base exception for adapter failures."""


class UnsupportedVehicleActionError(VehicleAdapterError):
    """Raised when an adapter cannot execute the requested action."""


class VehicleAdapter(ABC):
    """Async interface that separates raw acquisition from normalization."""

    @classmethod
    def get_friendly_name(cls) -> str:
        """Return a user-facing name for the underlying integration."""

        return cls.__name__

    @classmethod
    async def async_discover_vehicles(cls, hass: Any) -> list[DiscoveredVehicle]:
        """Return vehicles discoverable for this adapter in the current HA instance."""

        _ = hass
        return []

    @abstractmethod
    async def get_raw_state(self) -> RawStatePayload:
        """Return raw vehicle state signals from the source."""

    @abstractmethod
    async def get_raw_metrics(self) -> RawMetricsPayload:
        """Return raw vehicle metrics, location, and openings."""

    @abstractmethod
    async def get_capabilities(self) -> VehicleCapabilities:
        """Return structured capability support for the source."""

    @abstractmethod
    async def execute_action(self, action: str, **kwargs: Any) -> ActionResult:
        """Execute a supported vehicle action."""

    async def get_diagnostics(self) -> dict[str, Any]:
        """Return read-only diagnostic data for the adapter."""

        raw_state = await self.get_raw_state()
        raw_metrics = await self.get_raw_metrics()
        capabilities = await self.get_capabilities()
        return {
            "adapter_type": self.get_friendly_name(),
            "raw_state": dict(raw_state),
            "raw_metrics": dict(raw_metrics),
            "capabilities": _serialize_capabilities(capabilities),
        }


def _serialize_capabilities(capabilities: VehicleCapabilities) -> dict[str, dict[str, bool]]:
    """Convert typed capability support into a plain dict for diagnostics."""

    return {
        capability_name: {
            "state_supported": support.state_supported,
            "action_supported": support.action_supported,
        }
        for capability_name, support in capabilities.items()
    }
