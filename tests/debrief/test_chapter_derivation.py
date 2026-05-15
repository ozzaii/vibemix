# SPDX-License-Identifier: Apache-2.0
"""DEBRIEF-03 — chapter derivation from events.jsonl."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vibemix.debrief import ChapterRegion, derive_chapters


def _write_events(tmp_path: Path, events: list[dict]) -> Path:
    p = tmp_path / "events.jsonl"
    p.write_text("\n".join(json.dumps(e) for e in events), encoding="utf-8")
    return p


def test_three_track_changes_five_minutes_apart(tmp_path: Path):
    events = [
        {"t": 0.0, "kind": "session_start"},
        {"t": 0.5, "kind": "event", "type": "TRACK_CHANGE", "track": "Track One"},
        {"t": 300.0, "kind": "event", "type": "TRACK_CHANGE", "track": "Track Two"},
        {"t": 600.0, "kind": "event", "type": "TRACK_CHANGE", "track": "Track Three"},
        {"t": 900.0, "kind": "event", "type": "HEARTBEAT"},
    ]
    p = _write_events(tmp_path, events)
    chapters = derive_chapters(p)
    assert len(chapters) == 3
    assert all(c.kind == "track" for c in chapters)
    assert chapters[0].label == "Track 1: Track One"


def test_phase_split_after_30s_gap(tmp_path: Path):
    """A PHASE event ≥ 30s after the last break should split into a sub-chapter."""
    events = [
        {"t": 0.0, "kind": "session_start"},
        {"t": 0.5, "kind": "event", "type": "TRACK_CHANGE", "track": "Opening"},
        {"t": 45.0, "kind": "event", "type": "PHASE", "phase": "build"},
        {"t": 90.0, "kind": "event", "type": "PHASE", "phase": "peak"},
        {"t": 200.0, "kind": "event", "type": "HEARTBEAT"},
    ]
    p = _write_events(tmp_path, events)
    chapters = derive_chapters(p)
    # TRACK_CHANGE + 2 PHASE breaks (both ≥30s apart from prev)
    assert len(chapters) == 3
    assert chapters[0].kind == "track"
    assert chapters[1].kind == "phase"
    assert chapters[2].kind == "phase"


def test_heartbeat_events_ignored(tmp_path: Path):
    """HEARTBEAT events must not create chapter breaks."""
    events = [
        {"t": 0.0, "kind": "event", "type": "TRACK_CHANGE", "track": "Only"},
        {"t": 100.0, "kind": "event", "type": "HEARTBEAT"},
        {"t": 200.0, "kind": "event", "type": "HEARTBEAT"},
        {"t": 300.0, "kind": "event", "type": "HEARTBEAT"},
    ]
    p = _write_events(tmp_path, events)
    chapters = derive_chapters(p)
    assert len(chapters) == 1
    assert chapters[0].kind == "track"


def test_chapters_are_contiguous(tmp_path: Path):
    """chapter[i+1].start == chapter[i].end — no overlap, no gap."""
    events = [
        {"t": 0.0, "kind": "event", "type": "TRACK_CHANGE", "track": "A"},
        {"t": 300.0, "kind": "event", "type": "TRACK_CHANGE", "track": "B"},
        {"t": 600.0, "kind": "event", "type": "TRACK_CHANGE", "track": "C"},
        {"t": 900.0, "kind": "event", "type": "HEARTBEAT"},
    ]
    p = _write_events(tmp_path, events)
    chapters = derive_chapters(p)
    for i in range(len(chapters) - 1):
        assert chapters[i].end == chapters[i + 1].start, (
            f"chapter {i} end {chapters[i].end} != chapter {i+1} start "
            f"{chapters[i + 1].start}"
        )


def test_citation_event_id_format(tmp_path: Path):
    events = [
        {"t": 5.0, "kind": "event", "type": "TRACK_CHANGE", "track": "X"},
        {"t": 100.0, "kind": "event", "type": "HEARTBEAT"},
    ]
    p = _write_events(tmp_path, events)
    chapters = derive_chapters(p)
    assert chapters[0].citation_event_id.startswith("ev:TRACK_CHANGE@")


def test_empty_events_jsonl_returns_empty(tmp_path: Path):
    p = _write_events(tmp_path, [])
    assert derive_chapters(p) == []


def test_malformed_jsonl_lines_skipped(tmp_path: Path):
    p = tmp_path / "events.jsonl"
    p.write_text(
        "\n".join(
            [
                "{not json}",
                json.dumps({"t": 0.0, "kind": "event", "type": "TRACK_CHANGE"}),
                "// also not json",
                json.dumps({"t": 100.0, "kind": "event", "type": "HEARTBEAT"}),
            ]
        ),
        encoding="utf-8",
    )
    chapters = derive_chapters(p)
    assert len(chapters) == 1  # derivation continues past garbage lines


def test_chapter_dataclass_is_frozen():
    c = ChapterRegion(
        id="x",
        start=0.0,
        end=1.0,
        label="x",
        kind="track",
        citation_event_id="ev:x@0",
    )
    with pytest.raises((AttributeError, Exception)):
        c.id = "y"  # type: ignore[misc]
