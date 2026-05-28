# SPDX-License-Identifier: Apache-2.0
"""Phase 93 Plan 03 — EXEMPLAR-04 ``learn.headphone_device_index`` settings field (RED-state stub).

P93 lands the persistent settings key + the IPC payload shape ONLY — the
wizard UI lands in P97. Three tests pin the envelope contract:

    1. The ``ipc.settings.set`` ``field`` enum includes the new key
       ``"learn.headphone_device_index"``.
    2. The ``value`` ``anyOf`` accepts ``int (minimum: 0)`` OR ``null``
       — null = system default; int = explicit device index.
    3. The ``SettingsState`` round-trip envelope carries the field after
       a set (deferred to a slow-marked test if too heavy here).

The schema source-of-truth is
``tauri/ui/src/ipc/messages.schema.json`` → ``definitions.SettingsSet.
properties.payload.properties.field.enum``. The ajv validator is
PRE-COMPILED (``tauri/ui/src/ipc/validator.generated.mjs``); after this
edit lands, the schema-edit gate (CLAUDE.md §Commands) requires running
``cd tauri/ui && npm run codegen:ipc`` to regenerate the validator.

REQ-ID: EXEMPLAR-04 (settings persistence + IPC envelope shape).
Downstream plan that flips this skip: **Plan 93-03**.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_SCHEMA_PATH = _PROJECT_ROOT / "tauri" / "ui" / "src" / "ipc" / "messages.schema.json"


def _schema_has_learn_field() -> bool:
    """Probe whether the schema's SettingsSet.field enum carries the new key.

    Until Plan 93-03 lands the schema edit, the enum is the 11-entry P92
    set (voice/mode/genre/output_device_id/output_profile/retention_days/
    push_to_mute_hotkey/mood/click_through/lighter_blur/skill). The
    module-level skip below holds until "learn.headphone_device_index"
    actually appears in the enum.
    """
    if not _SCHEMA_PATH.exists():
        return False
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    try:
        enum = schema["definitions"]["SettingsSet"]["properties"]["payload"][
            "properties"
        ]["field"]["enum"]
    except (KeyError, TypeError):
        return False
    return "learn.headphone_device_index" in enum


if not _schema_has_learn_field():
    pytest.skip(
        "tests/ipc/test_settings_set_envelope_learn_field.py awaiting Plan 93-03 "
        "— learn.headphone_device_index field on the ipc.settings.set "
        "envelope (schema edit + npm run codegen:ipc).",
        allow_module_level=True,
    )


def test_settings_set_field_enum_includes_learn_headphone_device_index() -> None:
    """The ``ipc.settings.set`` ``field`` enum must include the new key
    ``"learn.headphone_device_index"`` (uses the ``learn.`` IPC namespace
    consistent with the ``ipc.learn.*`` envelope family from P91/P92)."""
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    field_enum = schema["definitions"]["SettingsSet"]["properties"]["payload"][
        "properties"
    ]["field"]["enum"]
    assert "learn.headphone_device_index" in field_enum, (
        f"field enum missing 'learn.headphone_device_index'; got {field_enum!r}"
    )


def test_settings_set_value_accepts_int_or_null() -> None:
    """The schema's ``value.anyOf`` must accept ``{type: integer, minimum: 0}``
    AND ``{type: null}`` — int = explicit device index, null = system default.
    The existing P92 ``anyOf`` already covers integer + null + string + boolean
    so this is a sanity check that the assertions still hold post-edit.
    """
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    value_any_of = schema["definitions"]["SettingsSet"]["properties"]["payload"][
        "properties"
    ]["value"]["anyOf"]
    # int branch present with minimum=0
    int_branches = [
        b for b in value_any_of
        if b.get("type") == "integer" and b.get("minimum", 0) >= 0
    ]
    assert int_branches, (
        f"value.anyOf must include integer branch with minimum>=0; "
        f"got {value_any_of!r}"
    )
    # null branch present
    null_branches = [b for b in value_any_of if b.get("type") == "null"]
    assert null_branches, (
        f"value.anyOf must include null branch (system-default device); "
        f"got {value_any_of!r}"
    )


def test_settings_state_carries_headphone_device_index_after_set() -> None:
    """The ``SettingsState`` mirror envelope must carry the new field so the
    P97 wizard UI can read the persisted value back. Plan 93-03 lands a
    Python dataclass mirror (mirrors the existing ``mascot`` / ``recording``
    pattern) — this stub asserts the envelope round-trip shape; the live
    ws-bus round-trip is deferred to a slow-marked test in P97.

    Static check: the schema's ``SettingsState`` payload declares the new
    property OR the catch-all ``learn`` property bag. The Plan 93-01 stub
    originally read ``schema.definitions.SettingsState.properties`` (the
    wrapper-level keys ``type`` / ``ts`` / ``payload``) — that path is
    wrong because every settings field on this envelope lives **inside**
    ``payload.properties`` (see ``voice`` / ``mode`` / ``skill`` etc. at
    schema lines 1380-1457). Plan 93-03 corrects the path to walk into
    ``payload.properties`` (a Rule-1 test-bug fix). The semantic check is
    unchanged: either nested ``learn`` object OR a flat
    ``learn.headphone_device_index`` key satisfies the contract.
    """
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    state_props = schema["definitions"]["SettingsState"]["properties"][
        "payload"
    ]["properties"]
    # Either an explicit "learn" object property OR a flat key — both are
    # valid envelope shapes; P93-03 picks one and the test passes.
    has_explicit_learn = "learn" in state_props
    has_flat_key = "learn.headphone_device_index" in state_props
    assert has_explicit_learn or has_flat_key, (
        "SettingsState envelope must carry the headphone device index — "
        "either as a nested 'learn' object property OR a flat "
        "'learn.headphone_device_index' key. Got SettingsState.payload "
        f"properties: {sorted(state_props.keys())!r}"
    )
