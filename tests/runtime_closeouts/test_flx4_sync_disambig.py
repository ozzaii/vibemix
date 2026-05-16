# SPDX-License-Identifier: Apache-2.0
"""Phase 27-09 — DDJ-FLX4 sync note disambiguation tests (MIDI-20).

Per CONTEXT decision MIDI-20 + RESEARCH §Common Pitfalls + autonomous mode:
the verdict is autonomous-derived from cohost_v4.py:786 _NOTE_MAP — sync
fires on note 0x60 (96 dec) only; note 0x58 (88 dec) is Mixxx-canonical
defensive, retained as 'tentative'.

Tests verify:
1. Fixture provenance line references the POC source (not a real hardware sniff).
2. JSON status fields match the verdict (sync_a/b verified; sync_a/b_alt tentative).
3. Verified bindings produce valid MIDI parser lookups for note 0x60.
4. Tentative bindings ARE present in the JSON but documented as such.
5. Comparison: verified play binding (0x0B) still resolves correctly (regression).
"""

from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[2]
FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "ddj_flx4_sync_capture.jsonl"
CONTROLLER_JSON = (
    PROJECT_ROOT / "src" / "vibemix" / "midi" / "controllers" / "ddj-flx4.json"
)


def _load_fixture_events() -> list[dict]:
    """Load the synthetic MIDI events (skip the _provenance header line)."""
    events = []
    for ln in FIXTURE.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        rec = json.loads(ln)
        if "type" in rec and rec["type"] in ("note_on", "note_off"):
            events.append(rec)
    return events


def _load_controller_mapping() -> dict[str, dict]:
    return json.loads(CONTROLLER_JSON.read_text(encoding="utf-8"))["controls"]


def test_fixture_provenance_line_references_poc_source() -> None:
    first_line = next(
        ln for ln in FIXTURE.read_text(encoding="utf-8").splitlines() if ln.strip()
    )
    rec = json.loads(first_line)
    assert "_provenance" in rec, f"first line missing _provenance: {rec}"
    assert (
        "cohost_v4" in rec["_provenance"].lower()
        or "v4" in rec["_provenance"].lower()
    ), f"_provenance does not reference POC source: {rec['_provenance']}"


def test_json_sync_a_b_status_verified() -> None:
    mapping = _load_controller_mapping()
    assert mapping["sync_a"]["status"] == "verified", mapping["sync_a"]
    assert mapping["sync_b"]["status"] == "verified", mapping["sync_b"]
    assert mapping["sync_a"]["value"] == 96
    assert mapping["sync_b"]["value"] == 96


def test_json_sync_alt_status_tentative() -> None:
    mapping = _load_controller_mapping()
    # Schema's canonical "tentative" string includes a clarifying suffix.
    assert mapping["sync_a_alt"]["status"].startswith("tentative"), mapping["sync_a_alt"]
    assert mapping["sync_b_alt"]["status"].startswith("tentative"), mapping["sync_b_alt"]
    assert mapping["sync_a_alt"]["value"] == 88
    assert mapping["sync_b_alt"]["value"] == 88


def test_top_level_verified_flag_is_true() -> None:
    payload = json.loads(CONTROLLER_JSON.read_text(encoding="utf-8"))
    assert payload.get("verified") is True


def test_description_documents_disambiguation() -> None:
    payload = json.loads(CONTROLLER_JSON.read_text(encoding="utf-8"))
    desc = payload.get("description", "")
    assert "disambiguated" in desc, desc
    assert "tests/fixtures/ddj_flx4_sync_capture.jsonl" in desc, desc


def test_note_0x60_events_resolve_to_verified_sync_binding() -> None:
    mapping = _load_controller_mapping()
    events = _load_fixture_events()
    sync_events = [
        e for e in events if e.get("note") == 96 and e["type"] == "note_on"
    ]
    assert len(sync_events) >= 2
    for ev in sync_events:
        binding = next(
            (
                b
                for b in mapping.values()
                if b["type"] == "note"
                and b["channel"] == ev["channel"]
                and b["value"] == ev["note"]
            ),
            None,
        )
        assert binding is not None, f"no mapping for {ev}"
        assert binding["status"] == "verified", binding
        assert "sync" in binding["semantic"], binding


def test_note_0x58_events_resolve_to_tentative_alt_binding() -> None:
    mapping = _load_controller_mapping()
    events = _load_fixture_events()
    alt_events = [
        e for e in events if e.get("note") == 88 and e["type"] == "note_on"
    ]
    assert len(alt_events) >= 2
    for ev in alt_events:
        binding = next(
            (
                b
                for b in mapping.values()
                if b["type"] == "note"
                and b["channel"] == ev["channel"]
                and b["value"] == ev["note"]
            ),
            None,
        )
        assert binding is not None
        assert binding["status"].startswith("tentative"), binding


def test_play_note_regression_guard() -> None:
    mapping = _load_controller_mapping()
    events = _load_fixture_events()
    play_events = [
        e for e in events if e.get("note") == 11 and e["type"] == "note_on"
    ]
    assert len(play_events) >= 1
    for ev in play_events:
        binding = next(
            (
                b
                for b in mapping.values()
                if b["type"] == "note"
                and b["channel"] == ev["channel"]
                and b["value"] == ev["note"]
            ),
            None,
        )
        assert binding is not None
        assert binding["status"] == "verified"
        assert binding["semantic"].startswith("play_")


def test_grep_gate_status_field_drift() -> None:
    text = CONTROLLER_JSON.read_text(encoding="utf-8")
    assert '"sync_a":' in text
    assert '"sync_b":' in text
    assert '"sync_a_alt":' in text
    assert '"sync_b_alt":' in text
    assert "pending-verdict" not in text, (
        "pending-verdict status still present in ddj-flx4.json — Phase 27 "
        "MIDI-20 closure incomplete"
    )


def test_poc_source_reference_in_provenance_includes_line_number() -> None:
    first_line = next(
        ln for ln in FIXTURE.read_text(encoding="utf-8").splitlines() if ln.strip()
    )
    rec = json.loads(first_line)
    source = rec.get("source", "")
    assert "cohost_v4" in source.lower(), source
    assert "_NOTE_MAP" in source or "786" in source, source
