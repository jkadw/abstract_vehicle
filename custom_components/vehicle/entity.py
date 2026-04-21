"""Shared entity helpers for normalized vehicle capability entities."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .model import NormalizedVehicleData, VehicleState
from .normalization import build_vehicle_attributes


class VehicleBaseEntity(Entity):
    """Base Home Assistant layer over normalized vehicle data."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, normalized_data: NormalizedVehicleData, key: str, name: str) -> None:
        self._normalized_data = normalized_data
        self._entity_key = key
        self._entity_name = name
        self._sync_entity_metadata()

    @property
    def available(self) -> bool:
        """Return whether the entity is available."""

        return self._normalized_data.state is not VehicleState.UNAVAILABLE

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return normalized state attributes."""

        return build_vehicle_attributes(self._normalized_data)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device metadata for the vehicle."""

        info = self._normalized_data.info
        return DeviceInfo(
            identifiers={(DOMAIN, info.vehicle_id)},
            manufacturer=info.manufacturer,
            model=info.model,
            name=info.name,
        )

    def update_normalized_data(self, normalized_data: NormalizedVehicleData) -> None:
        """Replace the current normalized snapshot."""

        self._normalized_data = normalized_data
        self._sync_entity_metadata()

    def _sync_entity_metadata(self) -> None:
        """Keep core HA-facing metadata aligned with normalized data."""

        self._attr_name = f"{self._normalized_data.info.name} {self._entity_name}"
        self._attr_unique_id = (
            f"{self._normalized_data.info.vehicle_id}_{self._entity_key}"
        )


class VehicleEntity(VehicleBaseEntity):
    """Backward-compatible aggregate state entity."""

    def __init__(self, normalized_data: NormalizedVehicleData) -> None:
        super().__init__(normalized_data, "state", "State")

    @property
    def state(self) -> str:
        """Return the canonical vehicle state."""

        return self._normalized_data.state.value
