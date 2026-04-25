"""Static metadata for dynamically loadable vehicle adapters."""

from __future__ import annotations

from dataclasses import dataclass

from ..const import ADAPTER_TYPE_KIA_UVO, ADAPTER_TYPE_MOCK


@dataclass(frozen=True, slots=True)
class AdapterDefinition:
    """Metadata needed to discover and lazily import an adapter."""

    key: str
    module_path: str
    class_name: str
    fallback_label: str
    mapping_name: str | None = None
    source_integration: str | None = None
    always_available: bool = False


ADAPTER_DEFINITIONS: tuple[AdapterDefinition, ...] = (
    AdapterDefinition(
        key=ADAPTER_TYPE_MOCK,
        module_path="custom_components.vehicle.adapters.mock",
        class_name="MockVehicleAdapter",
        fallback_label="Mock Adapter",
        always_available=True,
    ),
    AdapterDefinition(
        key=ADAPTER_TYPE_KIA_UVO,
        module_path="custom_components.vehicle.adapters.mapped",
        class_name="MappedVehicleAdapter",
        fallback_label="Hyundai / Kia Connect",
        mapping_name="hyundai_kia_connect_kia_uvo",
        source_integration="kia_uvo",
    ),
)


def get_adapter_definition(adapter_key: str) -> AdapterDefinition | None:
    """Return adapter metadata for the given adapter key."""

    for definition in ADAPTER_DEFINITIONS:
        if definition.key == adapter_key:
            return definition
    return None
