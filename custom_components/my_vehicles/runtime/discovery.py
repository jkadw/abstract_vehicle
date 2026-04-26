"""Generic discovery helpers for mapping-based adapters."""

from __future__ import annotations

import re
from typing import Any

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .base import DiscoveredVehicle
from ..mappings.schema import VehicleAdapterMapping, async_load_adapter_mapping


async def discover_vehicles_for_mapping(
    hass: Any, mapping_name: str
) -> list[DiscoveredVehicle]:
    """Discover source vehicles/devices for one mapping definition."""

    mapping = await async_load_adapter_mapping(hass, mapping_name)

    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    devices = getattr(device_registry, "devices", {})
    entity_entries = getattr(entity_registry, "entities", {})

    discovered: list[DiscoveredVehicle] = []
    for device in devices.values():
        vehicle_id = _vehicle_id_from_identifiers(
            getattr(device, "identifiers", set()),
            mapping.integration.domain,
        )
        if vehicle_id is None:
            continue

        payload = build_vehicle_payload_from_device(mapping, device, entity_entries.values())
        if payload is None:
            continue
        payload["vehicle_id"] = vehicle_id
        title = str(payload.get("name") or vehicle_id)
        discovered.append(
            DiscoveredVehicle(
                vehicle_id=vehicle_id,
                title=title,
                payload=payload,
            )
        )

    return discovered


def build_vehicle_payload_from_hass(
    hass: Any, mapping: VehicleAdapterMapping, vehicle_id: str
) -> dict[str, Any] | None:
    """Rebuild one discovered vehicle payload from current HA registry state."""

    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    devices = getattr(device_registry, "devices", {})
    entity_entries = getattr(entity_registry, "entities", {})

    for device in devices.values():
        current_vehicle_id = _vehicle_id_from_identifiers(
            getattr(device, "identifiers", set()),
            mapping.integration.domain,
        )
        if current_vehicle_id != vehicle_id:
            continue

        payload = build_vehicle_payload_from_device(mapping, device, entity_entries.values())
        if payload is None:
            return None
        payload["vehicle_id"] = vehicle_id
        return payload

    return None


def build_vehicle_payload_from_device(
    mapping: VehicleAdapterMapping,
    device: Any,
    entity_entries: Any,
) -> dict[str, Any] | None:
    """Build the generic discovered-vehicle payload for one source device."""

    source_entity_ids: list[str] = []
    for entity_entry in entity_entries:
        if getattr(entity_entry, "device_id", None) != getattr(device, "id", None):
            continue
        entity_id = getattr(entity_entry, "entity_id", None)
        if isinstance(entity_id, str) and "." in entity_id:
            source_entity_ids.append(entity_id)

    source_vehicle = _derive_vehicle_token(mapping, source_entity_ids)
    if source_vehicle is None:
        return None

    return {
        "name": getattr(device, "name_by_user", None)
        or getattr(device, "name", None)
        or f"{mapping.integration.domain} vehicle",
        "manufacturer": getattr(device, "manufacturer", None) or "Unknown",
        "model": getattr(device, "model", None) or "Unknown",
        "source_device_id": getattr(device, "id", None),
        "source_vehicle": source_vehicle,
        "source_entity_ids": sorted(source_entity_ids),
        "available": True,
        "backend_online": True,
        "has_error": False,
        "driving": False,
        "charging_active": False,
        "charging_plugged": False,
    }


def _vehicle_id_from_identifiers(
    identifiers: Any, integration_domain: str
) -> str | None:
    if not isinstance(identifiers, (set, list, tuple)):
        return None

    for identifier in identifiers:
        if not isinstance(identifier, tuple) or len(identifier) != 2:
            continue
        identifier_domain, identifier_value = identifier
        if identifier_domain != integration_domain:
            continue
        if isinstance(identifier_value, str) and identifier_value:
            return identifier_value
    return None


def _derive_vehicle_token(
    mapping: VehicleAdapterMapping, entity_ids: list[str]
) -> str | None:
    patterns = _collect_vehicle_patterns(mapping)
    if not patterns:
        return None

    matches: dict[str, int] = {}
    for pattern in patterns:
        regex = _pattern_to_regex(pattern)
        for entity_id in entity_ids:
            match = regex.fullmatch(entity_id)
            if not match:
                continue
            token = match.group("vehicle")
            matches[token] = matches.get(token, 0) + 1

    if not matches:
        return None

    return max(sorted(matches), key=lambda token: matches[token])


def _collect_vehicle_patterns(mapping: VehicleAdapterMapping) -> set[str]:
    patterns: set[str] = set()

    for capability in mapping.capabilities.values():
        for entity_id in capability.state.source_entities():
            if "{vehicle}" in entity_id:
                patterns.add(entity_id)
        for action in capability.actions.values():
            _collect_patterns_from_value(action.data, patterns)
            _collect_patterns_from_value(action.target, patterns)

    return patterns


def _collect_patterns_from_value(value: Any, patterns: set[str]) -> None:
    if isinstance(value, str):
        if "{vehicle}" in value and "." in value:
            patterns.add(value)
        return
    if isinstance(value, dict):
        for item in value.values():
            _collect_patterns_from_value(item, patterns)
        return
    if isinstance(value, list):
        for item in value:
            _collect_patterns_from_value(item, patterns)


def _pattern_to_regex(pattern: str) -> re.Pattern[str]:
    parts: list[str] = ["^"]
    index = 0
    seen_vehicle = False

    while index < len(pattern):
        if pattern.startswith("{vehicle}", index):
            if seen_vehicle:
                parts.append(r"(?P=vehicle)")
            else:
                parts.append(r"(?P<vehicle>.+?)")
                seen_vehicle = True
            index += len("{vehicle}")
            continue
        if pattern.startswith("{device}", index):
            parts.append(r".+?")
            index += len("{device}")
            continue
        parts.append(re.escape(pattern[index]))
        index += 1

    parts.append("$")
    return re.compile("".join(parts))
