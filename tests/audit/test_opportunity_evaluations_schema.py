"""OPP-02 schema-extension smoke test — validates dep_ratings.yaml against
the extended schema and asserts the Phase 48 additions are wired without
breaking Phase 46's existing shape.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA = REPO_ROOT / "scripts" / "audit" / "dep_ratings_schema.json"
YAML_FILE = REPO_ROOT / "scripts" / "audit" / "dep_ratings.yaml"


def _load_schema() -> dict:
    return json.loads(SCHEMA.read_text())


def _load_yaml() -> dict:
    return yaml.safe_load(YAML_FILE.read_text())


def test_yaml_validates_against_schema():
    jsonschema.validate(instance=_load_yaml(), schema=_load_schema())


def test_schema_has_opportunity_evaluations_required():
    s = _load_schema()
    assert "opportunity_evaluations" in s["required"]
    assert "opportunity_evaluations" in s["properties"]


def test_schema_opportunity_entry_4color_rating_enum():
    s = _load_schema()
    entry = s["$defs"]["opportunity_entry"]
    assert set(entry["properties"]["rating"]["enum"]) == {
        "green-adopt", "yellow-defer", "red-constraint", "red-risk",
    }


def test_schema_phase46_rating_entry_untouched():
    # Phase 46 axis: install-impact only (green/yellow/red).
    s = _load_schema()
    assert s["$defs"]["rating_entry"]["properties"]["rating"]["enum"] == [
        "green", "yellow", "red",
    ]


def test_yaml_phase46_ecosystem_maps_intact():
    d = _load_yaml()
    assert "livekit-plugins-openai" in d["python"]
    assert d["python"]["livekit-plugins-openai"]["rating"] == "yellow"


def test_synthetic_green_adopt_row_validates():
    """Sanity: a fully-populated opportunity_entry round-trips through the
    schema validator. Catches typos in the $defs block."""
    s = _load_schema()
    sample = {
        "id": "DEP-OPP-01",
        "date": "2026-05-18",
        "candidate": "OBS browser-source mascot path",
        "category": "integration",
        "rating": "green-adopt",
        "install_impact": "n/a",
        "rationale": "Tauri webview WS port 8765 already serves; docs-only adoption with zero new runtime code.",
        "integration_surface": "docs-only",
        "rejected_constraints": [],
        "adr_sidecar": ".planning/decisions/DEP-OPP-01-obs-browser-source.md",
    }
    jsonschema.validate(
        instance={
            "python": {}, "rust": {}, "js": {},
            "opportunity_evaluations": [sample],
        },
        schema=s,
    )
