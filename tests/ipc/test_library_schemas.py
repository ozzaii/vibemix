# SPDX-License-Identifier: Apache-2.0
"""Plan 28-09 Task 3 — Library IPC schema validation tests.

Covers:
    - test_library_schemas_validate: every wrapper round-trips clean
    - test_library_schemas_reject_extra_field: additionalProperties: false
    - test_library_schemas_reject_missing_required: required fields enforced
    - test_schema_version_field: every payload pins schema_version="1"
    - test_count_parity_python_vs_schema: 1:1 wrapper ↔ oneOf entry
    - test_no_pydantic_dependency: Open Q4 — dataclasses only
    - test_renderer_outbound_messages_documented: $comment direction check
"""

from __future__ import annotations

import json
from dataclasses import fields
from pathlib import Path

import jsonschema
import pytest

from vibemix.ui_bus import (
    LibraryConfidence,
    LibraryImport,
    LibraryImportCancel,
    LibraryImportProgress,
    LibrarySearchRequest,
    LibrarySearchResult,
    LibrarySimilarRequest,
    LibrarySimilarResult,
    LibraryStalenessAction,
    LibraryStalenessNudge,
)
from vibemix.ui_bus import messages as ui_bus_messages

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCHEMA_PATH = _REPO_ROOT / "tauri" / "ui" / "src" / "ipc" / "messages.schema.json"
_SCHEMA = json.loads(_SCHEMA_PATH.read_text())
_VALIDATOR = jsonschema.Draft7Validator(_SCHEMA)


# ─── Minimal valid examples (shared with check_ipc_schema.py) ────────────────


def _library_wrappers() -> list[tuple[str, object]]:
    return [
        ("LibraryImport", LibraryImport.make(path="/tmp/lib.xml")),
        (
            "LibraryImportProgress",
            LibraryImportProgress.make(
                total=10,
                done=5,
                current_track_name="Artist — Track",
                cache_hits=3,
            ),
        ),
        ("LibraryImportCancel", LibraryImportCancel.make()),
        (
            "LibrarySearchRequest",
            LibrarySearchRequest.make(query="acid techno", k=10),
        ),
        (
            "LibrarySearchResult",
            LibrarySearchResult.make(
                query="acid techno",
                matches=(
                    {
                        "track_id": "t1",
                        "title": "X",
                        "artist": "Y",
                        "bpm": 138.0,
                        "confidence": 0.87,
                        "snippet": "X — Y",
                    },
                ),
                cache_hit=False,
            ),
        ),
        (
            "LibraryConfidence",
            LibraryConfidence.make(
                track_id="t1",
                cosine=0.85,
                decision="cited",
                event_id="ev-1",
            ),
        ),
        (
            "LibraryStalenessNudge",
            LibraryStalenessNudge.make(age_days=45, snoozed_until_ts=None),
        ),
        (
            "LibraryStalenessAction",
            LibraryStalenessAction.make(action="snooze_7d"),
        ),
        ("LibrarySimilarRequest", LibrarySimilarRequest.make(track_id="t1", k=10)),
        (
            "LibrarySimilarResult",
            LibrarySimilarResult.make(
                track_id="t1",
                results=(
                    {
                        "track_id": "t2",
                        "similarity": 0.82,
                        "title": "Z",
                        "artist": "W",
                        "bpm": 140.0,
                    },
                ),
            ),
        ),
    ]


# ─── Tests ───────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("name,instance", _library_wrappers())
def test_library_schemas_validate(name: str, instance: object) -> None:
    """Each wrapper.make(...).to_json() round-trips clean through the schema."""
    json_str = instance.to_json()  # type: ignore[attr-defined]
    d = json.loads(json_str)
    _VALIDATOR.validate(d)


def test_library_schemas_reject_extra_field() -> None:
    """additionalProperties: false on payload — extra fields raise."""
    bad = {
        "type": "ipc.library.import",
        "ts": "2026-05-15T12:00:00+00:00",
        "payload": {
            "path": "/tmp/lib.xml",
            "schema_version": "1",
            "evil_field": "x",
        },
    }
    with pytest.raises(jsonschema.ValidationError):
        _VALIDATOR.validate(bad)


def test_library_schemas_reject_missing_required() -> None:
    """LibraryImport requires `path` — missing it raises."""
    bad = {
        "type": "ipc.library.import",
        "ts": "2026-05-15T12:00:00+00:00",
        "payload": {"schema_version": "1"},
    }
    with pytest.raises(jsonschema.ValidationError):
        _VALIDATOR.validate(bad)


def test_schema_version_field() -> None:
    """Every payload pins schema_version == "1"."""
    for name, inst in _library_wrappers():
        d = json.loads(inst.to_json())  # type: ignore[attr-defined]
        assert d["payload"]["schema_version"] == "1", name


def test_count_parity_python_vs_schema() -> None:
    """Python wrappers ↔ schema oneOf entries — 1:1 contract."""
    wrapper_count = 0
    for attr_name in dir(ui_bus_messages):
        obj = getattr(ui_bus_messages, attr_name)
        if not isinstance(obj, type):
            continue
        if not hasattr(obj, "__dataclass_fields__"):
            continue
        if "type" in obj.__dataclass_fields__ and "payload" in obj.__dataclass_fields__:
            wrapper_count += 1
    assert wrapper_count == len(_SCHEMA["oneOf"]), (
        f"Count parity broken: Python has {wrapper_count} wrappers, "
        f"schema has {len(_SCHEMA['oneOf'])} oneOf entries"
    )


def test_no_pydantic_dependency() -> None:
    """Open Q4: library schemas must not import pydantic — dataclasses only.

    Check for actual import statements (line starts with ``import`` or
    ``from``) so the in-docstring word "pydantic" doesn't false-positive.
    """
    src = (
        _REPO_ROOT / "src" / "vibemix" / "ui_bus" / "schemas" / "library.py"
    ).read_text()
    for raw in src.splitlines():
        line = raw.strip()
        if line.startswith(("import ", "from ")):
            assert "pydantic" not in line, (
                f"library.py imports pydantic on line: {line!r}"
            )


def test_renderer_outbound_messages_documented() -> None:
    """Each library schema's $comment names its direction (renderer/sidecar)."""
    direction_keywords = ("renderer", "sidecar")
    library_defs = [
        k for k in _SCHEMA["definitions"] if k.startswith("Library")
    ]
    assert len(library_defs) == 10
    for name in library_defs:
        comment = _SCHEMA["definitions"][name].get("$comment", "")
        assert any(
            kw in comment.lower() for kw in direction_keywords
        ), f"{name} $comment must name a direction (renderer/sidecar)"


def test_library_wrapper_set_matches_expected() -> None:
    """Catch missing wrapper imports — explicit allowlist of 10 Library*."""
    expected = {
        "LibraryConfidence",
        "LibraryImport",
        "LibraryImportCancel",
        "LibraryImportProgress",
        "LibrarySearchRequest",
        "LibrarySearchResult",
        "LibrarySimilarRequest",
        "LibrarySimilarResult",
        "LibraryStalenessAction",
        "LibraryStalenessNudge",
    }
    found = {
        name
        for name in dir(ui_bus_messages)
        if name.startswith("Library") and not name.endswith("Payload")
    }
    assert expected <= found, f"Missing wrappers: {expected - found}"


def test_library_payload_only_no_type_field() -> None:
    """Payload structs must NOT have ``type`` field — only wrappers do."""
    from vibemix.ui_bus.schemas import library as lib_schemas

    for attr_name in dir(lib_schemas):
        obj = getattr(lib_schemas, attr_name)
        if not (isinstance(obj, type) and hasattr(obj, "__dataclass_fields__")):
            continue
        if not attr_name.endswith("Payload"):
            continue
        names = {f.name for f in fields(obj)}
        assert "type" not in names, (
            f"{attr_name} should not carry a 'type' field — wrappers do"
        )
