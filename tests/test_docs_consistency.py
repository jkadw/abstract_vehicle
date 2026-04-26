"""Lightweight consistency checks for documentation and metadata."""

from __future__ import annotations

import json
from pathlib import Path

from custom_components.my_vehicles.const import DOMAIN
from custom_components.my_vehicles.services import SERVICE_SCHEMAS


REPO_ROOT = Path(__file__).resolve().parents[1]
README_PATH = REPO_ROOT / "README.md"
MANIFEST_PATH = REPO_ROOT / "custom_components" / "my_vehicles" / "manifest.json"
SERVICES_PATH = REPO_ROOT / "custom_components" / "my_vehicles" / "services.yaml"
MAPPING_PATH = (
    REPO_ROOT
    / "custom_components"
    / "my_vehicles"
    / "mappings"
    / "hyundai_kia_connect_kia_uvo.yaml"
)


def test_manifest_matches_documented_name_and_domain() -> None:
    """Published integration metadata should match the documented identity."""

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    assert manifest["domain"] == DOMAIN == "my_vehicles"
    assert manifest["name"] == "My Vehicles"


def test_readme_uses_current_name_domain_and_doc_index() -> None:
    """The README should use the current public name and audience split."""

    readme = README_PATH.read_text(encoding="utf-8")

    assert "# My Vehicles" in readme
    assert "`my_vehicles`" in readme
    assert "Documentation By Audience" in readme
    assert "./docs/mapping_schema.md" in readme
    assert "./docs/backend_architecture.md" in readme
    assert "./docs/domain_model.md" in readme


def test_services_yaml_contains_current_public_service_names() -> None:
    """The documented service metadata should exist for the live service surface."""

    services_yaml = SERVICES_PATH.read_text(encoding="utf-8")

    for service_name in sorted(set(SERVICE_SCHEMAS) | {"diagnostics"}):
        assert f"{service_name}:" in services_yaml


def test_documented_example_mapping_file_exists() -> None:
    """The example mapping referenced by the docs should exist in the repo."""

    assert MAPPING_PATH.exists()
