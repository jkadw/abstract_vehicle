"""Internal helpers for My Vehicles event emission."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN, EVENT_ACTION_EXECUTED, EVENT_STATE_CHANGED
from .domain.capability_registry import CORE_CAPABILITIES
from .domain.model import NormalizedVehicleData


def async_fire_action_executed(
    hass: HomeAssistant,
    normalized: NormalizedVehicleData,
    capability_name: str,
    action_name: str,
    action_data: Any,
) -> None:
    """Emit the generic action-executed event for one vehicle action."""

    hass.bus.async_fire(
        EVENT_ACTION_EXECUTED,
        {
            **_event_vehicle_context(hass, normalized),
            "capability": capability_name,
            "action": action_name,
            "action_data": action_data,
        },
    )


def async_fire_state_changes(
    hass: HomeAssistant,
    previous: NormalizedVehicleData | None,
    updated: NormalizedVehicleData,
) -> None:
    """Emit state-changed events for changed canonical capability values."""

    if previous is None:
        return

    context = _event_vehicle_context(hass, updated)
    previous_values = previous.capability_values
    updated_values = updated.capability_values

    for capability_name in CORE_CAPABILITIES:
        old_value = previous_values.get(capability_name)
        new_value = updated_values.get(capability_name)
        if old_value == new_value:
            continue
        hass.bus.async_fire(
            EVENT_STATE_CHANGED,
            {
                **context,
                "capability": capability_name,
                "old_value": old_value,
                "new_value": new_value,
            },
        )


def _event_vehicle_context(
    hass: HomeAssistant, normalized: NormalizedVehicleData
) -> dict[str, Any]:
    device_registry = dr.async_get(hass)
    device = device_registry.async_get_device(
        identifiers={(DOMAIN, normalized.info.vehicle_id)},
        connections=set(),
    )
    return {
        "device_id": None if device is None else device.id,
        "vehicle_id": normalized.info.vehicle_id,
    }
