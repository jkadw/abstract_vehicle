"""Shared entity helpers for normalized vehicle capability entities."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DATA_ADAPTER, DOMAIN
from ..domain.model import NormalizedVehicleData, VehicleState
from ..domain.normalization import build_vehicle_attributes


class VehicleBaseEntity(Entity):
    """Base Home Assistant layer over normalized vehicle data."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        normalized_data: NormalizedVehicleData,
        key: str,
        name: str,
    ) -> None:
        self._normalized_data = normalized_data
        self._entity_key = key
        self._entity_name = name
        self._sync_entity_metadata()

    @property
    def available(self) -> bool:
        """Return whether the entity is available."""

        return self._normalized_data.state is not VehicleState.UNAVAILABLE

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        """Expose detailed attributes only on the aggregate vehicle entity."""

        return None

    @property
    def device_info(self) -> DeviceInfo:
        """Return device metadata for the vehicle."""

        info = self._normalized_data.info
        return DeviceInfo(
            identifiers={(DOMAIN, info.vehicle_id)},
            manufacturer=info.manufacturer,
            model=info.model,
            name=f"My {info.name}",
        )

    def update_normalized_data(self, normalized_data: NormalizedVehicleData) -> None:
        """Replace the current normalized snapshot."""

        self._normalized_data = normalized_data
        self._sync_entity_metadata()

    def _sync_entity_metadata(self) -> None:
        """Keep core HA-facing metadata aligned with normalized data."""

        self._attr_name = self._entity_name
        self._attr_unique_id = (
            f"{self._normalized_data.info.vehicle_id}_{self._entity_key}"
        )

    def _capability_value(self, capability_name: str):
        return self._normalized_data.capability_values.get(capability_name)


class VehicleEntity(VehicleBaseEntity, SensorEntity):
    """Aggregate vehicle state entity exposed in the sensor domain."""

    _attr_has_entity_name = False
    _attr_translation_key = "vehicle_state"

    def __init__(self, normalized_data: NormalizedVehicleData) -> None:
        super().__init__(normalized_data, "state", "State")

    @property
    def state(self) -> str:
        """Return the canonical vehicle state."""

        return self._normalized_data.state.value

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return the aggregate normalized vehicle attributes."""

        return build_vehicle_attributes(self._normalized_data)

    @property
    def icon(self) -> str:
        """Return an icon that matches the aggregate vehicle state."""

        if self._normalized_data.state is VehicleState.CHARGING:
            return "mdi:car-electric"
        if self._normalized_data.state is VehicleState.DRIVING:
            return "mdi:car-sports"
        if self._normalized_data.state is VehicleState.ERROR:
            return "mdi:car-alert"
        if self._normalized_data.state in {VehicleState.OFFLINE, VehicleState.UNAVAILABLE}:
            return "mdi:car-off"
        return "mdi:car"

    def _sync_entity_metadata(self) -> None:
        """Keep the aggregate sensor metadata aligned with the normalized data."""

        self._attr_name = f"My {self._normalized_data.info.name}"
        self._attr_unique_id = self._normalized_data.info.vehicle_id


def capability_source_domains(entry_data: dict[str, object], capability_name: str) -> set[str]:
    """Return source entity domains referenced by one capability mapping."""

    adapter = entry_data.get(DATA_ADAPTER)
    mapping = getattr(adapter, "_mapping", None)
    if mapping is None:
        return set()

    capability = mapping.capability(capability_name)
    if capability is None:
        return set()

    domains: set[str] = set()
    for entity_id in capability.state.source_entities():
        if "." in entity_id:
            domains.add(entity_id.split(".", 1)[0])
    return domains
