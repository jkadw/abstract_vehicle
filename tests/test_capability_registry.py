"""Tests for the canonical capability registry."""

from __future__ import annotations

from custom_components.my_vehicles.domain.capability_registry import (
    button_rule_map,
    get_capability_definition,
    should_create_entity_rule,
    state_entity_rules_for_domain,
)


def test_lock_vehicle_registry_definition_matches_contract() -> None:
    """The lock capability should expose the documented verbs and entity rules."""

    definition = get_capability_definition("lock_vehicle")

    assert definition.action_verbs == ("lock", "unlock")
    assert tuple(rule.domain for rule in definition.ui.state_entities) == (
        "lock",
        "binary_sensor",
    )
    assert tuple(rule.domain for rule in definition.ui.control_entities) == ()
    assert tuple(rule.key for rule in definition.ui.buttons) == (
        "lock_vehicle",
        "unlock_vehicle",
    )


def test_button_rule_map_exposes_registry_driven_service_names() -> None:
    """Button keys should define the action-facing service surface."""

    rules = button_rule_map()

    assert rules["lock_vehicle"][0] == "lock_vehicle"
    assert rules["lock_vehicle"][1].action == "lock"
    assert rules["unlock_vehicle"][0] == "lock_vehicle"
    assert rules["unlock_vehicle"][1].action == "unlock"
    assert rules["open_windows"][0] == "windows"
    assert rules["open_windows"][1].action == "open"
    assert rules["close_windows"][0] == "windows"
    assert rules["close_windows"][1].action == "close"
    assert rules["start_climate"][0] == "climate"
    assert rules["turn_on_hazard_lights"][1].icon == "mdi:car-hazard-lights"
    assert rules["refresh"][0] == "refresh"


def test_lock_vehicle_state_rules_are_indexed_by_platform_domain() -> None:
    """Platform code should be able to query registry rules by HA domain."""

    lock_rules = dict(state_entity_rules_for_domain("lock"))
    binary_rules = dict(state_entity_rules_for_domain("binary_sensor"))

    assert lock_rules["lock_vehicle"].key == "lock_vehicle"
    assert binary_rules["lock_vehicle"].key == "vehicle_locked"
    assert binary_rules["doors"].key == "doors"


def test_entity_rule_predicates_cover_lock_vehicle_generation_cases() -> None:
    """The registry should express the lock exception and binary/switch policies."""

    definition = get_capability_definition("lock_vehicle")
    lock_rule = definition.ui.state_entities[0]
    binary_rule = definition.ui.state_entities[1]

    assert should_create_entity_rule(
        lock_rule,
        state_supported=False,
        action_supported=False,
    )
    assert should_create_entity_rule(
        binary_rule,
        state_supported=True,
        action_supported=False,
    )
