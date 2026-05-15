# SPDX-License-Identifier: Apache-2.0
"""Plan 29-03 Task 2 — P82 hard gate: debrief.v1 schema is additive-only.

Diffs the current ``messages.schema.json`` debrief.* slice against the
v2.1 baseline fixture. Any of the following is a HARD FAILURE:

- a baseline definition is removed
- a property on a baseline definition is removed or renamed
- a property's ``type`` changed
- a NEW required field is added to an EXISTING definition (renderer
  consumers that ship pre-Phase-29 don't emit it)
- a baseline KIND string disappears from oneOf

The following are explicitly ALLOWED (additive):
- new definitions appended to the debrief namespace
- new OPTIONAL fields on existing definitions
- new entries in enum lists (relaxation of value-domain is non-breaking
  for emitters but Phase 29 keeps enums frozen too out of caution —
  see DebriefError.reason enum)
- removing a field from ``required`` (relaxation is fine for emitters
  but could break consumers — we WARN-flag it but don't fail)

DEBRIEF-10. P82 lock baseline lives at
``tests/ui_bus/fixtures/debrief_schema_v2_1_baseline.json``.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "tauri" / "ui" / "src" / "ipc" / "messages.schema.json"
BASELINE_PATH = (
    Path(__file__).parent / "fixtures" / "debrief_schema_v2_1_baseline.json"
)


def _load_current_debrief_slice() -> dict:
    schema = json.loads(SCHEMA_PATH.read_text())
    return {
        "oneOf": [
            r for r in schema["oneOf"] if r["$ref"].startswith("#/definitions/Debrief")
        ],
        "definitions": {
            k: v for k, v in schema["definitions"].items() if k.startswith("Debrief")
        },
    }


def _load_baseline() -> dict:
    return json.loads(BASELINE_PATH.read_text())


def _props(defn: dict) -> dict:
    return defn.get("properties", {}).get("payload", {}).get("properties", {})


def _required(defn: dict) -> list[str]:
    return defn.get("properties", {}).get("payload", {}).get("required", [])


def _diff_violations(baseline: dict, current: dict) -> list[str]:
    """Return list of P82 violation messages; empty list means PASS."""
    violations: list[str] = []
    base_defs = baseline["definitions"]
    cur_defs = current["definitions"]

    for name, base_def in base_defs.items():
        if name not in cur_defs:
            violations.append(f"P82 VIOLATION: definition {name} removed from schema")
            continue
        cur_def = cur_defs[name]

        base_props = _props(base_def)
        cur_props = _props(cur_def)
        for prop, base_spec in base_props.items():
            if prop not in cur_props:
                violations.append(
                    f"P82 VIOLATION: field payload.{prop} removed from {name}"
                )
                continue
            cur_spec = cur_props[prop]
            # type field comparison (handle union types via list)
            base_type = base_spec.get("type")
            cur_type = cur_spec.get("type")
            if base_type is not None and base_type != cur_type:
                violations.append(
                    f"P82 VIOLATION: field payload.{prop} type changed in {name}: "
                    f"{base_type!r} -> {cur_type!r}"
                )

        base_req = set(_required(base_def))
        cur_req = set(_required(cur_def))
        added_required = cur_req - base_req
        if added_required:
            violations.append(
                f"P82 VIOLATION: new required field(s) {sorted(added_required)} "
                f"added to existing definition {name}"
            )

    # oneOf removal check
    base_refs = {r["$ref"] for r in baseline["oneOf"]}
    cur_refs = {r["$ref"] for r in current["oneOf"]}
    removed_refs = base_refs - cur_refs
    if removed_refs:
        violations.append(
            f"P82 VIOLATION: oneOf entries removed: {sorted(removed_refs)}"
        )

    return violations


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_current_schema_is_additive_only_vs_baseline():
    baseline = _load_baseline()
    current = _load_current_debrief_slice()
    violations = _diff_violations(baseline, current)
    assert violations == [], "\n".join(violations)


def test_baseline_fixture_exists():
    assert BASELINE_PATH.exists(), (
        f"P82 baseline fixture missing — recreate via "
        f"snapshot of current debrief.* schema slice: {BASELINE_PATH}"
    )


# ---------------------------------------------------------------------------
# Negative simulations (assert the gate fires on every breaking pattern)
# ---------------------------------------------------------------------------


def test_simulated_field_removal_is_caught():
    baseline = _load_baseline()
    mutated = copy.deepcopy(baseline)
    # Drop the duration_s field from DebriefSessionLoaded
    del (
        mutated["definitions"]["DebriefSessionLoaded"]["properties"]["payload"][
            "properties"
        ]["duration_s"]
    )
    violations = _diff_violations(baseline, mutated)
    assert any("duration_s" in v and "removed" in v for v in violations), violations


def test_simulated_type_change_is_caught():
    baseline = _load_baseline()
    mutated = copy.deepcopy(baseline)
    mutated["definitions"]["DebriefSessionLoaded"]["properties"]["payload"][
        "properties"
    ]["duration_s"]["type"] = "string"
    violations = _diff_violations(baseline, mutated)
    assert any("type changed" in v for v in violations), violations


def test_simulated_new_required_on_existing_def_is_caught():
    baseline = _load_baseline()
    mutated = copy.deepcopy(baseline)
    mutated["definitions"]["DebriefSessionLoaded"]["properties"]["payload"][
        "required"
    ].append("new_field")
    mutated["definitions"]["DebriefSessionLoaded"]["properties"]["payload"][
        "properties"
    ]["new_field"] = {"type": "string"}
    violations = _diff_violations(baseline, mutated)
    assert any("new required field" in v for v in violations), violations


def test_simulated_definition_removal_is_caught():
    baseline = _load_baseline()
    mutated = copy.deepcopy(baseline)
    del mutated["definitions"]["DebriefError"]
    violations = _diff_violations(baseline, mutated)
    assert any("DebriefError removed" in v for v in violations), violations


def test_simulated_oneof_removal_is_caught():
    baseline = _load_baseline()
    mutated = copy.deepcopy(baseline)
    mutated["oneOf"] = [
        r
        for r in mutated["oneOf"]
        if r["$ref"] != "#/definitions/DebriefError"
    ]
    violations = _diff_violations(baseline, mutated)
    assert any("DebriefError" in v and "oneOf" in v for v in violations), violations


def test_simulated_optional_field_addition_is_allowed():
    """Adding a NEW optional field on an existing definition is fine."""
    baseline = _load_baseline()
    mutated = copy.deepcopy(baseline)
    # Add an optional field — not in required list
    mutated["definitions"]["DebriefSessionLoaded"]["properties"]["payload"][
        "properties"
    ]["optional_v2_2_field"] = {"type": "string"}
    violations = _diff_violations(baseline, mutated)
    assert violations == [], "additive optional field should be allowed"


def test_simulated_new_definition_is_allowed():
    """Appending a new debrief.* definition is fine (additive growth)."""
    baseline = _load_baseline()
    mutated = copy.deepcopy(baseline)
    mutated["definitions"]["DebriefSomeNewThing"] = {
        "type": "object",
        "properties": {"payload": {"properties": {}, "required": []}},
    }
    violations = _diff_violations(baseline, mutated)
    assert violations == []
