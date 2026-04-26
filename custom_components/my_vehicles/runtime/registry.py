"""Dynamic metadata for vehicle adapters discovered from mapping files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..mappings.schema import MappingValidationError, load_mapping_file


@dataclass(frozen=True, slots=True)
class AdapterDefinition:
    """Metadata needed to construct one adapter definition."""

    key: str
    fallback_label: str
    source_integration: str
    kind: str = "mapping"
    mapping_name: str | None = None
    module_path: str | None = None
    class_name: str | None = None


CUSTOM_ADAPTER_DEFINITIONS: tuple[AdapterDefinition, ...] = ()


def get_adapter_definitions() -> tuple[AdapterDefinition, ...]:
    """Return adapter definitions discovered from mappings plus custom extensions."""

    definitions: list[AdapterDefinition] = []
    for mapping_path in _mapping_directory().glob("*.yaml"):
        mapping_name = mapping_path.stem
        try:
            mapping = load_mapping_file(mapping_path)
        except MappingValidationError:
            continue

        definitions.append(
            AdapterDefinition(
                key=mapping_name,
                fallback_label=mapping.integration.friendly_name,
                source_integration=mapping.integration.domain,
                kind="mapping",
                mapping_name=mapping_name,
            )
        )

    definitions.extend(CUSTOM_ADAPTER_DEFINITIONS)
    return tuple(sorted(definitions, key=lambda definition: definition.key))


def get_adapter_definition(adapter_key: str) -> AdapterDefinition | None:
    """Return adapter metadata for the given primary key."""

    for definition in get_adapter_definitions():
        if definition.key == adapter_key:
            return definition
    return None


async def async_get_adapter_definitions(hass: Any) -> tuple[AdapterDefinition, ...]:
    """Return adapter definitions without blocking the event loop."""

    return await hass.async_add_executor_job(get_adapter_definitions)


async def async_get_adapter_definition(
    hass: Any, adapter_key: str
) -> AdapterDefinition | None:
    """Return one adapter definition without blocking the event loop."""

    definitions = await async_get_adapter_definitions(hass)
    for definition in definitions:
        if definition.key == adapter_key:
            return definition
    return None


def _mapping_directory() -> Path:
    return Path(__file__).resolve().parent
