"""Import smoke tests and config-flow behavior checks."""

from __future__ import annotations

import asyncio
import importlib


def test_root_integration_modules_import_cleanly() -> None:
    """Home Assistant-facing root modules should remain importable after refactors."""

    module_names = [
        "custom_components.my_vehicles",
        "custom_components.my_vehicles.config_flow",
        "custom_components.my_vehicles.sensor",
        "custom_components.my_vehicles.binary_sensor",
        "custom_components.my_vehicles.lock",
        "custom_components.my_vehicles.switch",
        "custom_components.my_vehicles.button",
        "custom_components.my_vehicles.device_tracker",
        "custom_components.my_vehicles.services",
    ]

    for module_name in module_names:
        module = importlib.import_module(module_name)
        assert module is not None


class _FakeConfig:
    def __init__(self, components: set[str] | None = None) -> None:
        self.components = components or set()


class _FakeConfigEntries:
    def __init__(self, entries_by_domain: dict[str, list[object]] | None = None) -> None:
        self._entries_by_domain = entries_by_domain or {}

    def async_entries(self, domain: str) -> list[object]:
        return list(self._entries_by_domain.get(domain, []))


class _FakeHass:
    def __init__(
        self,
        *,
        components: set[str] | None = None,
        entries_by_domain: dict[str, list[object]] | None = None,
    ) -> None:
        self.config = _FakeConfig(components)
        self.config_entries = _FakeConfigEntries(entries_by_domain)


def test_config_flow_aborts_when_no_adapters_are_available(monkeypatch) -> None:
    """The user step should abort cleanly when no source mappings are available."""

    module = importlib.import_module("custom_components.my_vehicles.config_flow")
    flow = module.VehicleConfigFlow()
    flow.hass = _FakeHass()
    flow.async_abort = lambda *, reason: {"type": "abort", "reason": reason}

    async def _no_options(_hass):
        return {}

    monkeypatch.setattr(module, "get_available_adapter_options", _no_options)

    result = asyncio.run(flow.async_step_user())

    assert result == {"type": "abort", "reason": "no_adapters_available"}


def test_config_flow_shows_available_adapter_options(monkeypatch) -> None:
    """The user step should render a selection form for discovered mappings."""

    module = importlib.import_module("custom_components.my_vehicles.config_flow")
    flow = module.VehicleConfigFlow()
    flow.hass = _FakeHass(entries_by_domain={"kia_uvo": [object()]})
    flow.async_show_form = lambda *, step_id, data_schema: {
        "type": "form",
        "step_id": step_id,
        "data_schema": data_schema,
    }

    async def _options(_hass):
        return {"kia_uvo": "Hyundai / Kia Connect"}

    monkeypatch.setattr(module, "get_available_adapter_options", _options)

    result = asyncio.run(flow.async_step_user())

    assert result["type"] == "form"
    assert result["step_id"] == "user"


def test_config_flow_rejects_unknown_adapter_submission(monkeypatch) -> None:
    """Submitting an adapter that is not in the available mapping list should abort."""

    module = importlib.import_module("custom_components.my_vehicles.config_flow")
    flow = module.VehicleConfigFlow()
    flow.hass = _FakeHass()
    flow.async_abort = lambda *, reason: {"type": "abort", "reason": reason}

    async def _options(_hass):
        return {"kia_uvo": "Hyundai / Kia Connect"}

    monkeypatch.setattr(module, "get_available_adapter_options", _options)

    result = asyncio.run(flow.async_step_user({"adapter": "missing_mapping"}))

    assert result == {"type": "abort", "reason": "adapter_not_available"}


def test_config_flow_creates_entry_for_selected_adapter(monkeypatch) -> None:
    """A valid adapter selection should create one config entry for that mapping."""

    module = importlib.import_module("custom_components.my_vehicles.config_flow")
    flow = module.VehicleConfigFlow()
    flow.hass = _FakeHass(entries_by_domain={"kia_uvo": [object()]})
    unique_ids: list[str] = []
    flow.async_create_entry = lambda *, title, data: {
        "type": "create_entry",
        "title": title,
        "data": data,
    }
    flow._abort_if_unique_id_configured = lambda: None

    async def _set_unique_id(value: str):
        unique_ids.append(value)

    async def _options(_hass):
        return {"kia_uvo": "Hyundai / Kia Connect"}

    flow.async_set_unique_id = _set_unique_id
    monkeypatch.setattr(module, "get_available_adapter_options", _options)

    result = asyncio.run(
        flow.async_step_user({"adapter": "kia_uvo"})
    )

    assert unique_ids == ["kia_uvo"]
    assert result == {
        "type": "create_entry",
        "title": "Hyundai / Kia Connect",
        "data": {"adapter": "kia_uvo"},
    }
