"""Adapter for vehicles sourced from the Hyundai-Kia-Connect/kia_uvo integration."""

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


class HyundaiKiaConnectKiaUvoVehicleAdapter(VehicleAdapter):
    """Map configured kia_uvo vehicle payloads into the shared adapter interface."""

    @classmethod
    def get_friendly_name(cls) -> str:
        """Return the friendly name of the upstream integration."""

        return "Hyundai / Kia Connect"

    @classmethod
    async def async_discover_vehicles(cls, hass: Any) -> list[DiscoveredVehicle]:
        """Discover kia_uvo vehicles from the HA registries and current state."""

        from homeassistant.helpers import device_registry as dr
        from homeassistant.helpers import entity_registry as er

        device_registry = dr.async_get(hass)
        entity_registry = er.async_get(hass)
        devices = getattr(device_registry, "devices", {})
        entities = getattr(entity_registry, "entities", {})

        discovered: list[DiscoveredVehicle] = []
        for device in devices.values():
            identifiers = getattr(device, "identifiers", set())
            vehicle_id = cls._vehicle_id_from_identifiers(identifiers)
            if vehicle_id is None:
                continue

            vehicle_payload = cls._build_vehicle_payload_from_device(
                hass, device, entities.values(), vehicle_id
            )
            title = vehicle_payload.get("name") or f"kia_uvo {vehicle_id}"
            discovered.append(
                DiscoveredVehicle(
                    vehicle_id=vehicle_id,
                    title=str(title),
                    payload=vehicle_payload,
                )
            )

        return discovered

    def __init__(
        self,
        vehicles: list[dict[str, Any]],
        vehicle_id: str | None = None,
        hass: Any | None = None,
    ) -> None:
        self._hass = hass
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

        if self._hass is not None:
            refreshed_vehicle = self._build_vehicle_payload_from_hass(
                self._hass,
                self._vehicle_id,
            )
            if refreshed_vehicle is not None:
                self._vehicles[self._vehicle_id] = refreshed_vehicle

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
            refresh=self._capability_support(capabilities.get("refresh")),
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
        elif action == "refresh":
            if not capabilities.refresh.action_supported:
                raise UnsupportedVehicleActionError(f"Unsupported action: {action}")
            await self._execute_refresh()
        else:
            raise UnsupportedVehicleActionError(f"Unsupported action: {action}")

        vehicle["status"] = self._derive_status(vehicle)
        return {"success": True, "action": action}

    async def _execute_refresh(self) -> None:
        """Trigger a refresh in the source Hyundai/Kia integration."""

        if self._hass is None:
            raise UnsupportedVehicleActionError("Unsupported action: refresh")

        refresh_entities = self._as_entity_id_list(self._vehicle.get("refresh_entity_ids"))
        if refresh_entities:
            for entity_id in refresh_entities:
                await self._hass.services.async_call(
                    "button",
                    "press",
                    {"entity_id": entity_id},
                    blocking=True,
                )
            return

        source_entities = self._as_entity_id_list(self._vehicle.get("source_entity_ids"))
        if not source_entities:
            raise UnsupportedVehicleActionError("Unsupported action: refresh")

        await self._hass.services.async_call(
            "homeassistant",
            "update_entity",
            {"entity_id": source_entities},
            blocking=True,
        )

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

    def _as_entity_id_list(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [
            entity_id
            for entity_id in value
            if isinstance(entity_id, str) and "." in entity_id
        ]

    @classmethod
    def _build_vehicle_payload_from_hass(
        cls,
        hass: Any,
        vehicle_id: str,
    ) -> dict[str, Any] | None:
        """Rebuild a configured vehicle payload from current HA registry state."""

        from homeassistant.helpers import device_registry as dr
        from homeassistant.helpers import entity_registry as er

        device_registry = dr.async_get(hass)
        entity_registry = er.async_get(hass)
        devices = getattr(device_registry, "devices", {})
        entities = getattr(entity_registry, "entities", {})

        for device in devices.values():
            identifiers = getattr(device, "identifiers", set())
            if cls._vehicle_id_from_identifiers(identifiers) != vehicle_id:
                continue

            return cls._build_vehicle_payload_from_device(
                hass,
                device,
                entities.values(),
                vehicle_id,
            )

        return None

    @classmethod
    def _vehicle_id_from_identifiers(cls, identifiers: Any) -> str | None:
        """Return the kia_uvo vehicle id from a registry identifier set."""

        if not isinstance(identifiers, (set, list, tuple)):
            return None

        for identifier in identifiers:
            if not isinstance(identifier, tuple) or len(identifier) != 2:
                continue
            identifier_domain, identifier_value = identifier
            if identifier_domain != "kia_uvo":
                continue
            if isinstance(identifier_value, str) and identifier_value:
                return identifier_value

        return None

    @classmethod
    def _build_vehicle_payload_from_device(
        cls,
        hass: Any,
        device: Any,
        entity_entries: Any,
        vehicle_id: str,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "vehicle_id": vehicle_id,
            "name": getattr(device, "name_by_user", None)
            or getattr(device, "name", None)
            or f"kia_uvo {vehicle_id}",
            "manufacturer": getattr(device, "manufacturer", None) or "Kia/Hyundai",
            "model": getattr(device, "model", None) or "Unknown",
            "vehicle_type": "unknown",
            "available": True,
            "backend_online": True,
            "has_error": False,
            "driving": False,
            "charging_active": False,
            "charging_plugged": False,
            "locked": None,
            "climate_active": None,
            "metrics": {},
            "openings": {},
            "source_units": {},
            "capabilities": {
                capability_name: {"state_supported": False, "action_supported": False}
                for capability_name in (
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
            },
            "source_entity_ids": [],
            "refresh_entity_ids": [],
        }

        for entity_entry in entity_entries:
            if getattr(entity_entry, "device_id", None) != getattr(device, "id", None):
                continue

            entity_id = getattr(entity_entry, "entity_id", "")
            payload["source_entity_ids"].append(entity_id)

            domain, _, object_id = entity_id.partition(".")
            object_id = object_id.lower()
            original_name = str(getattr(entity_entry, "original_name", "") or "").lower()
            match_text = f"{object_id} {original_name}"

            if domain == "button" and any(
                token in match_text for token in ("refresh", "update", "force update")
            ):
                payload["refresh_entity_ids"].append(entity_id)
                payload["capabilities"]["refresh"]["action_supported"] = True
                continue

            state = hass.states.get(entity_id)
            if state is None:
                continue

            if domain == "lock":
                payload["locked"] = state.state == "locked"
                payload["capabilities"]["lock"] = {
                    "state_supported": True,
                    "action_supported": True,
                }
                continue

            if domain == "climate":
                payload["climate_active"] = state.state not in {"off", "unavailable", "unknown"}
                payload["capabilities"]["climate"] = {
                    "state_supported": True,
                    "action_supported": True,
                }
                continue

            if domain == "device_tracker":
                latitude = state.attributes.get("latitude")
                longitude = state.attributes.get("longitude")
                if isinstance(latitude, (int, float)) and isinstance(longitude, (int, float)):
                    payload["metrics"]["latitude"] = float(latitude)
                    payload["metrics"]["longitude"] = float(longitude)
                    payload["capabilities"]["location"]["state_supported"] = True
                continue

            if domain not in {"sensor", "binary_sensor"}:
                continue

            if "battery" in match_text and "12v" not in match_text:
                value = cls._float_from_state(state.state)
                if value is not None:
                    payload["metrics"]["battery_level"] = value
                    payload["capabilities"]["battery"]["state_supported"] = True
                continue

            if "odometer" in match_text:
                value = cls._float_from_state(state.state)
                if value is not None:
                    payload["metrics"]["odometer"] = value
                    payload["capabilities"]["odometer"]["state_supported"] = True
                    unit = state.attributes.get("unit_of_measurement")
                    if isinstance(unit, str):
                        payload["source_units"]["distance_unit"] = unit
                continue

            if "range" in match_text and "fuel" not in match_text:
                value = cls._float_from_state(state.state)
                if value is not None:
                    payload["metrics"]["range"] = value
                    unit = state.attributes.get("unit_of_measurement")
                    if isinstance(unit, str):
                        payload["source_units"]["distance_unit"] = unit
                continue

            if "fuel" in match_text and "range" in match_text:
                value = cls._float_from_state(state.state)
                if value is not None:
                    payload["metrics"]["fuel_level"] = value
                    payload["capabilities"]["fuel"]["state_supported"] = True
                continue

            if "charge" in match_text and "plug" in match_text:
                payload["charging_plugged"] = state.state in {"on", "true", "plugged_in"}
                payload["capabilities"]["charging"]["state_supported"] = True
                continue

            if "charge" in match_text:
                payload["charging_active"] = state.state in {"on", "true", "charging"}
                payload["capabilities"]["charging"]["state_supported"] = True
                continue

            if "window" in match_text or "sunroof" in match_text:
                payload["openings"][object_id] = (
                    "open" if state.state in {"on", "open", "true"} else "closed"
                )
                payload["capabilities"]["windows"]["state_supported"] = True

        if payload["source_entity_ids"]:
            payload["capabilities"]["refresh"]["action_supported"] = True

        return payload

    @classmethod
    def _float_from_state(cls, value: Any) -> float | None:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return None
        return None
