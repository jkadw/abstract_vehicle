"""Setup and config-entry orchestration for My Vehicles."""

from __future__ import annotations

import logging

from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers.event import async_track_state_change_event

from ..const import (
    CONF_ADAPTER,
    DATA_ADAPTER,
    DATA_DISCOVERY_SNAPSHOTS,
    DATA_ENTITIES,
    DATA_NORMALIZED,
    DATA_VEHICLES,
    DOMAIN,
    PLATFORMS,
)
from ..domain.normalization import normalize_vehicle_data
from ..runtime.loader import create_adapter_from_discovered_vehicle, discover_adapter_vehicles
from ..services import async_register_services, async_unregister_services

LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the My Vehicles integration."""

    _ = config
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(DATA_DISCOVERY_SNAPSHOTS, {})
    await async_register_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a My Vehicles config entry."""

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(DATA_DISCOVERY_SNAPSHOTS, {})

    adapter_type = entry.data.get(CONF_ADAPTER)
    if not isinstance(adapter_type, str) or not adapter_type:
        raise ValueError("Configured adapter type must be a non-empty string")

    if not hass.is_running:

        async def _async_reload_on_started(event: Event) -> None:
            _ = event
            await hass.config_entries.async_reload(entry.entry_id)

        entry.async_on_unload(
            hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_STARTED,
                _async_reload_on_started,
            )
        )

    snapshots = hass.data[DOMAIN][DATA_DISCOVERY_SNAPSHOTS]
    previous_snapshot = set(snapshots.get(entry.entry_id, ()))
    discovered_vehicles = await _discover_entry_vehicles(hass, entry)
    vehicle_entries = []
    for discovered_vehicle in discovered_vehicles:
        try:
            vehicle_adapter = await create_adapter_from_discovered_vehicle(
                hass,
                adapter_type,
                discovered_vehicle,
            )
            raw_state = await vehicle_adapter.get_raw_state()
            raw_metrics = await vehicle_adapter.get_raw_metrics()
            capabilities = await vehicle_adapter.get_capabilities()
            normalized_data = normalize_vehicle_data(raw_state, raw_metrics, capabilities)
        except Exception as err:
            LOGGER.warning(
                "Skipping discovered vehicle '%s' for adapter '%s': %s",
                discovered_vehicle.vehicle_id,
                adapter_type,
                err,
            )
            continue

        vehicle_entries.append(
            {
                DATA_ADAPTER: vehicle_adapter,
                DATA_ENTITIES: [],
                DATA_NORMALIZED: normalized_data,
            }
        )

    hass.data[DOMAIN][entry.entry_id] = {
        DATA_ADAPTER: adapter_type,
        DATA_VEHICLES: vehicle_entries,
    }
    _register_vehicle_state_listeners(hass, entry, vehicle_entries)
    current_snapshot = _snapshot_vehicle_ids(vehicle_entries)
    snapshots[entry.entry_id] = sorted(current_snapshot)
    _log_vehicle_reconciliation(entry, adapter_type, previous_snapshot, current_snapshot)

    await async_register_services(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a vehicle config entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        domain_data = hass.data[DOMAIN]
        entry_data = domain_data.get(entry.entry_id)
        snapshots = domain_data.setdefault(DATA_DISCOVERY_SNAPSHOTS, {})
        if isinstance(entry_data, dict):
            snapshots[entry.entry_id] = sorted(
                _snapshot_vehicle_ids(entry_data.get(DATA_VEHICLES, []))
            )

        domain_data.pop(entry.entry_id, None)
        if not any(
            isinstance(value, dict) and DATA_VEHICLES in value
            for value in domain_data.values()
        ):
            await async_unregister_services(hass)
    return unload_ok


async def _discover_entry_vehicles(hass: HomeAssistant, entry: ConfigEntry) -> list:
    """Discover all source vehicles for the selected mapping entry."""

    adapter_type = entry.data.get(CONF_ADAPTER)
    if not isinstance(adapter_type, str) or not adapter_type:
        raise ValueError("Configured adapter type must be a non-empty string")
    return await discover_adapter_vehicles(hass, adapter_type)


def _snapshot_vehicle_ids(vehicle_entries: object) -> set[str]:
    """Return the current set of normalized vehicle ids for one entry."""

    if not isinstance(vehicle_entries, list):
        return set()

    vehicle_ids: set[str] = set()
    for vehicle_entry in vehicle_entries:
        if not isinstance(vehicle_entry, dict):
            continue
        normalized = vehicle_entry.get(DATA_NORMALIZED)
        if normalized is None:
            continue
        vehicle_id = getattr(getattr(normalized, "info", None), "vehicle_id", None)
        if isinstance(vehicle_id, str) and vehicle_id:
            vehicle_ids.add(vehicle_id)
    return vehicle_ids


def _log_vehicle_reconciliation(
    entry: ConfigEntry,
    adapter_type: object,
    previous_snapshot: set[str],
    current_snapshot: set[str],
) -> None:
    """Log add/remove reconciliation results for one entry."""

    added = sorted(current_snapshot - previous_snapshot)
    removed = sorted(previous_snapshot - current_snapshot)
    unchanged = sorted(current_snapshot & previous_snapshot)

    if added or removed:
        LOGGER.info(
            "Reconciled My Vehicles entry '%s' for adapter '%s': added=%s removed=%s kept=%s",
            entry.entry_id,
            adapter_type,
            added or ["-"],
            removed or ["-"],
            unchanged or ["-"],
        )
        return

    LOGGER.debug(
        "My Vehicles entry '%s' for adapter '%s' is unchanged with vehicles=%s",
        entry.entry_id,
        adapter_type,
        unchanged or ["-"],
    )


def _register_vehicle_state_listeners(
    hass: HomeAssistant,
    entry: ConfigEntry,
    vehicle_entries: list[dict[str, object]],
) -> None:
    """Register refresh-only listeners for source entity state changes."""

    for vehicle_entry in vehicle_entries:
        adapter = vehicle_entry.get(DATA_ADAPTER)
        if adapter is None:
            continue
        source_entity_ids = tuple(
            entity_id for entity_id in getattr(adapter, "source_entity_ids", lambda: ())()
            if isinstance(entity_id, str) and entity_id
        )
        if not source_entity_ids:
            continue

        async def _async_refresh_on_state_change(event: Event, *, entry_data=vehicle_entry) -> None:
            _ = event
            await _refresh_vehicle_entry(entry_data)

        def _handle_state_change(event: Event, *, refresh=_async_refresh_on_state_change) -> None:
            hass.async_create_task(refresh(event))

        entry.async_on_unload(
            async_track_state_change_event(
                hass,
                list(source_entity_ids),
                _handle_state_change,
            )
        )


async def _refresh_vehicle_entry(entry_data: dict[str, object]) -> None:
    """Refresh one vehicle entry from source state without executing actions."""

    adapter = entry_data[DATA_ADAPTER]
    entities = entry_data.get(DATA_ENTITIES, [])

    raw_state = await adapter.get_raw_state()
    raw_metrics = await adapter.get_raw_metrics()
    capabilities = await adapter.get_capabilities()
    updated = normalize_vehicle_data(raw_state, raw_metrics, capabilities)
    entry_data[DATA_NORMALIZED] = updated

    for entity in entities:
        entity.update_normalized_data(updated)
        entity.async_write_ha_state()
