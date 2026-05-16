# SPDX-License-Identifier: Apache-2.0
"""Plan 42-03 Task 1 — protocol document + JSON Schema contract.

Pins the load-bearing invariants in ``eval/EAR-TEST-PROTOCOL.md`` so
the doc and the schema cannot drift silently. Mirrors the audit-trail
pattern of ``tests/eval/test_threshold_lock.py``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


PROTOCOL_PATH = Path("eval/EAR-TEST-PROTOCOL.md")
SCHEMA_PATH = Path("eval/ear-test-logs/schema.json")


@pytest.fixture(scope="module")
def protocol_text() -> str:
    return PROTOCOL_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def schema_obj() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_protocol_doc_exists():
    assert PROTOCOL_PATH.is_file(), (
        f"protocol doc missing: {PROTOCOL_PATH}"
    )


def test_protocol_doc_documents_30min_minimum(protocol_text: str):
    """30 min / 1800 s rule must appear (forces schema-doc parity)."""
    assert (
        "30 min" in protocol_text
        or "30-min" in protocol_text
        or "1800" in protocol_text
    )
    # Reference the duration_s field name so doc → schema linkage is
    # explicit.
    assert "duration_s" in protocol_text


def test_protocol_doc_documents_two_genre_minimum(protocol_text: str):
    """The ≥ 2 genres invariant must be documented verbatim."""
    assert (
        "≥ 2 genres" in protocol_text
        or "≥2 genres" in protocol_text
    )


def test_protocol_doc_documents_14d_window(protocol_text: str):
    """The 14-day window must be documented verbatim."""
    assert (
        "14 days" in protocol_text
        or "14-day" in protocol_text
        or "14d" in protocol_text
    )


def test_protocol_doc_lists_all_four_slop_flags(protocol_text: str):
    """All four slop-flag keys must appear by name."""
    for key in ("felt_slop", "felt_scripted", "felt_late", "felt_generic"):
        assert key in protocol_text, f"missing slop flag: {key}"


def test_protocol_doc_documents_privacy_redaction(protocol_text: str):
    """Logs stay in repo; public README redacts content."""
    # "repo" = logs stay in repo as audit trail.
    assert "repo" in protocol_text.lower()
    # "redact" = eval/README.md redacts public textual content.
    assert "redact" in protocol_text.lower()


def test_protocol_doc_references_check_script(protocol_text: str):
    """Cross-link to the bash gate must exist."""
    assert "scripts/release/check_ear_test.sh" in protocol_text


def test_protocol_doc_references_kaan_action(protocol_text: str):
    """Cross-link to the Kaan-discharge runbook must exist."""
    assert "KAAN-ACTION-LEGAL.md" in protocol_text
    assert "§GATE-05" in protocol_text


def test_schema_json_parses_as_valid_jsonschema(schema_obj: dict):
    """Schema is a valid draft-2020-12 schema."""
    jsonschema = pytest.importorskip("jsonschema")
    # ``check_schema`` raises if the schema is malformed.
    jsonschema.Draft202012Validator.check_schema(schema_obj)


def test_schema_locks_duration_min_1800(schema_obj: dict):
    """Schema-level 30-min rule pinned to 1800 s."""
    assert schema_obj["properties"]["duration_s"]["minimum"] == 1800


def test_schema_locks_signed_by_to_kaan(schema_obj: dict):
    """Single-DJ regime: signed_by enum is ``[kaan]`` exactly."""
    assert schema_obj["properties"]["signed_by"]["enum"] == ["kaan"]


def test_schema_requires_all_four_slop_flags(schema_obj: dict):
    """The 4 slop-flag boolean keys must be required + additionalProperties:false."""
    sf = schema_obj["properties"]["slop_flags"]
    assert set(sf["required"]) == {
        "felt_slop",
        "felt_scripted",
        "felt_late",
        "felt_generic",
    }
    assert sf["additionalProperties"] is False
    for k in sf["required"]:
        assert sf["properties"][k]["type"] == "boolean"


def test_schema_top_level_additional_properties_false(schema_obj: dict):
    """Top-level shape is closed — no smuggled keys."""
    assert schema_obj.get("additionalProperties") is False


def test_schema_genre_enum_pins_seven_values(schema_obj: dict):
    """Genre enum is the locked list — change requires schema bump."""
    assert set(schema_obj["properties"]["genre"]["enum"]) == {
        "hard_tek",
        "techno",
        "house",
        "hip_hop",
        "dnb",
        "dubstep",
        "other",
    }
