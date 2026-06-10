# SPDX-License-Identifier: Apache-2.0
"""Unit coverage for the session-level persona reviewer's deterministic half."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.eval.session_review import assemble_digest, render_digest_text, salvage_json


def _write_session(tmp_path: Path, rows: list[dict], meta: dict | None = None) -> Path:
    session = tmp_path / "20260610-000000"
    session.mkdir()
    (session / "events.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8"
    )
    (session / "session.json").write_text(
        json.dumps(meta if meta is not None else {"sven_probe_mode": False}), encoding="utf-8"
    )
    return session


def test_assemble_digest_stats(tmp_path: Path) -> None:
    rows = [
        {"t": 0.0, "kind": "session_start"},
        {"t": 26.0, "kind": "event", "type": "PHASE", "phase": "build"},
        {
            "t": 29.5,
            "kind": "ai_message",
            "event": "PHASE",
            "latency_s": 3.5,
            "message": "Build is stacking, kick still clean.",
            "citation": {"count": 1, "action": "emit"},
        },
        {"t": 80.0, "kind": "event", "type": "TRACK_CHANGE"},
        {"t": 140.0, "kind": "speak_gate", "type": "HEARTBEAT", "verdict": "silent", "reason": "below_worthiness"},
        {
            "t": 200.0,
            "kind": "ai_message",
            "event": "PHRASE_BOUNDARY",
            "latency_s": 2.0,
            "message": "Build is stacking, kick still clean.",
            "citation": {"count": 1, "action": "emit"},
        },
        # Suppressed line must NOT count as spoken.
        {
            "t": 220.0,
            "kind": "ai_message",
            "event": "PHASE",
            "latency_s": 2.0,
            "message": "held reply",
            "suppression": "manual_no_evidence",
        },
        {"t": 300.0, "kind": "session_lifecycle", "status": "stopped"},
    ]
    digest = assemble_digest(_write_session(tmp_path, rows))
    stats = digest["stats"]

    assert stats["duration_s"] == 300.0
    assert stats["musical_events"] == 2
    assert stats["spoken_lines"] == 2
    assert stats["gated_silent"] == 1
    assert stats["time_to_first_line_s"] == 29.5
    # Gaps: 0->29.5, 29.5->200, 200->300 — longest is the mid-set dead air.
    assert stats["longest_silence_s"] == 170.5
    # TRACK_CHANGE at t=80 had no spoken line within 30s.
    assert stats["unreacted_events"] == 1
    assert stats["max_latency_s"] == 3.5
    # The identical line spoken twice registers as repetition.
    assert list(stats["repeated_lines"].values()) == [2]
    assert stats["probe_capture"] == "shipped"


def test_digest_text_carries_timeline_and_silence(tmp_path: Path) -> None:
    rows = [
        {"t": 10.0, "kind": "event", "type": "PHASE"},
    ]
    session = _write_session(tmp_path, rows)
    digest = assemble_digest(session)
    text = render_digest_text(session.name, digest)

    assert "EVENT PHASE — no reaction" in text
    assert "0 lines spoken" in text
    assert session.name in text


def test_assemble_digest_empty_session(tmp_path: Path) -> None:
    digest = assemble_digest(_write_session(tmp_path, [], meta={}))
    assert digest["stats"]["spoken_lines"] == 0
    assert digest["stats"]["musical_events"] == 0
    assert digest["stats"]["probe_capture"] == "unknown"
    assert "silence" in render_digest_text("s", digest)


def test_salvage_json_recovers_trailing_garbage() -> None:
    # The exact observed failure: a valid object whose closing brace is
    # preceded by junk lines the model appended after the last value.
    content = (
        '{\n  "overall_feeling": "fine",\n  "would_use_again_0_10": 5,\n'
        '  "top_annoyances": [\n    {"category": "silence", "what": "ghosted", "evidence_t": 125}\n  ],\n'
        '  "change_one_thing": "speak sooner"\n'
        '."\n."\n"\n}'
    )
    doc = salvage_json(content)
    assert doc is not None
    assert doc["would_use_again_0_10"] == 5
    assert doc["top_annoyances"][0]["category"] == "silence"


def test_salvage_json_plain_and_hopeless() -> None:
    assert salvage_json('{"a": 1}') == {"a": 1}
    assert salvage_json('prose before {"a": 1} prose after') == {"a": 1}
    assert salvage_json("no json here at all") is None
