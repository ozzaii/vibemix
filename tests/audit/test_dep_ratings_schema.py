"""DEPS-04 — assert dep_ratings.yaml conforms to dep_ratings_schema.json."""

import json
from pathlib import Path

import jsonschema
import yaml

REPO = Path(__file__).resolve().parents[2]
YAML_FILE = REPO / "scripts" / "audit" / "dep_ratings.yaml"
SCHEMA = REPO / "scripts" / "audit" / "dep_ratings_schema.json"


def test_yaml_validates_against_schema():
    schema = json.loads(SCHEMA.read_text())
    with YAML_FILE.open() as f:
        data = yaml.safe_load(f)
    jsonschema.validate(instance=data, schema=schema)


def test_schema_is_draft_2020_12():
    schema = json.loads(SCHEMA.read_text())
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"


def test_schema_enforces_rating_enum():
    schema = json.loads(SCHEMA.read_text())
    bad = {"python": {"foo": {"rating": "blue", "rationale": "x" * 20}}, "rust": {}, "js": {}}
    try:
        jsonschema.validate(instance=bad, schema=schema)
    except jsonschema.ValidationError:
        return
    raise AssertionError("schema accepted invalid rating 'blue'")


def test_schema_enforces_required_rationale():
    schema = json.loads(SCHEMA.read_text())
    bad = {"python": {"foo": {"rating": "green"}}, "rust": {}, "js": {}}
    try:
        jsonschema.validate(instance=bad, schema=schema)
    except jsonschema.ValidationError:
        return
    raise AssertionError("schema accepted entry without rationale")
