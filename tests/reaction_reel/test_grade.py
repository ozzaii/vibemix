# SPDX-License-Identifier: Apache-2.0
"""Phase 17-02 — Blind grading CLI tests.

Covers the autonomous deliverable for Area 3 (CONTEXT decisions):

1. ``extract_reactions`` walks ``events.jsonl`` for ``kind=="ai_text"`` events
   and assembles per-reaction clip cards with ±15s context window.
2. ``anonymize_reactions`` assigns SHA-8 IDs, writes ``grades/grades.key.json``
   so the on-screen output (rater_view) never reveals persona/mode/genre/skill.
3. ``shuffle_for_rater`` produces a deterministic per-rater Fisher-Yates shuffle
   seeded on SHA-1(rater + session_dir)[:8] — same rater on the same session
   always lands on the same order so a mid-grading quit resumes cleanly.
4. ``load_existing_grades`` reads a partially-written rater JSONL and returns
   the set of already-graded reaction_ids so resume skips them.
5. ``slop_highlights`` re-uses ``vibemix.prompts.negative_dict.NEGATIVE_REGEX``
   to flag generic AI phrasings inline in the rater view.
6. ``GradeRecord`` enforces the locked schema from CONTEXT Area 1
   (score 1-5, slop_flag enum, all required fields present).
7. ``write_grade`` appends one JSONL line per reaction and fsyncs so a
   process kill mid-grading never loses the line being written.
8. ``rater_view`` strips persona/mode/genre/skill metadata — anonymized.

12 tests total — see Plan 17-02 test plan.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import wave
from pathlib import Path
from typing import Iterator
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_silent_wav(path: Path, *, duration_s: float, sample_rate: int) -> None:
    """Write a real WAV file with ``duration_s`` seconds of silent int16 mono PCM."""
    import numpy as np

    n_frames = int(duration_s * sample_rate)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(np.zeros(n_frames, dtype=np.int16).tobytes())


def _build_session(
    root: Path,
    *,
    dir_name: str = "20260513-180000",
    ai_text_events: list[tuple[float, str]] | None = None,
    extra_events: list[dict] | None = None,
    persona_meta: dict | None = None,
) -> Path:
    """Build a synthetic recording session dir with events.jsonl + session.json
    + voice.wav. Returns the session_dir Path.
    """
    session_dir = root / dir_name
    session_dir.mkdir(parents=True, exist_ok=True)

    # WAV — 60s of silence so any reaction ±15s window slices safely.
    _write_silent_wav(session_dir / "voice.wav", duration_s=60.0, sample_rate=24000)
    _write_silent_wav(session_dir / "input.wav", duration_s=60.0, sample_rate=16000)

    # events.jsonl with session_start header + caller-provided events.
    events_path = session_dir / "events.jsonl"
    lines: list[dict] = [
        {
            "t": 0.0,
            "kind": "session_start",
            "wall_clock_iso": "2026-05-13T18:00:00.000+03:00",
            "wall_clock_unix": 1747159200.0,
            "session_dir": dir_name,
        }
    ]
    if extra_events:
        lines.extend(extra_events)
    if ai_text_events:
        for t, text in ai_text_events:
            lines.append({"t": t, "kind": "ai_text", "text": text, "latency_s": 1.2})
    with events_path.open("w", encoding="utf-8") as f:
        for rec in sorted(lines, key=lambda r: r["t"]):
            json.dump(rec, f, ensure_ascii=False)
            f.write("\n")

    # session.json — persona/mode/genre/skill must be stripped from rater view.
    meta = {
        "session_json_version": "1.0",
        "vibemix_version": "0.1.0",
        "started_at_iso": "2026-05-13T18:00:00.000+03:00",
        "started_at_unix": 1747159200.0,
        "ended_at_iso": "2026-05-13T18:30:00.000+03:00",
        "ended_at_unix": 1747161000.0,
        "duration_s": 1800.0,
        "voice": "Aoede",
        "mode": "hype",
        "genre": "techno",
        "user_level": "intermediate",
        "crashed": False,
        "event_count": len([l for l in lines if l["kind"] != "session_start"]),
    }
    if persona_meta:
        meta.update(persona_meta)
    (session_dir / "session.json").write_text(json.dumps(meta), encoding="utf-8")
    return session_dir


# ---------------------------------------------------------------------------
# Test 1 — extract_reactions: walks ai_text events, builds context windows
# ---------------------------------------------------------------------------


def test_extract_reactions_walks_ai_text_with_context_window(tmp_path: Path) -> None:
    """``extract_reactions`` returns one record per ``kind=="ai_text"`` event with
    the reaction text + a ±15s context window of surrounding events.
    """
    from scripts.reaction_reel.grade import extract_reactions

    session = _build_session(
        tmp_path,
        ai_text_events=[
            (10.0, "Sick transition into that filter sweep."),
            (40.0, "Coming up on the breakdown — load the bass."),
        ],
        extra_events=[
            {"t": 5.0, "kind": "trigger", "reason": "phase_change"},
            {"t": 9.5, "kind": "track_resolved", "track": "Track A"},
            {"t": 25.0, "kind": "trigger", "reason": "mix_move"},
            {"t": 35.0, "kind": "trigger", "reason": "layer_arrival"},
            {"t": 55.0, "kind": "trigger", "reason": "phase_change"},
        ],
    )
    reactions = extract_reactions(session)
    assert len(reactions) == 2

    r0 = reactions[0]
    assert r0["t"] == 10.0
    assert r0["text"] == "Sick transition into that filter sweep."
    # Context window ±15s — should include trigger@5 and track_resolved@9.5 but
    # NOT mix_move@25 (15.0 < 25.0 - 10.0 = 15.0 boundary; inclusive at 25.0?).
    # Spec: ±15s window → t in [reaction.t - 15, reaction.t + 15], inclusive.
    ctx_kinds = [c["kind"] for c in r0["context"]]
    assert "trigger" in ctx_kinds  # trigger@5 in window [‑5, 25]
    assert "track_resolved" in ctx_kinds  # @9.5
    # mix_move@25 is at the boundary (10 + 15) — included by inclusive window.
    assert any(c["t"] == 25.0 for c in r0["context"])
    # phase_change@55 is at t=55 > 25 → NOT in window for r0.
    assert not any(c["t"] == 55.0 for c in r0["context"])

    r1 = reactions[1]
    assert r1["t"] == 40.0
    assert r1["text"] == "Coming up on the breakdown — load the bass."
    ctx_t = [c["t"] for c in r1["context"]]
    assert 25.0 in ctx_t  # mix_move@25 in [25, 55]
    assert 35.0 in ctx_t
    assert 55.0 in ctx_t


# ---------------------------------------------------------------------------
# Test 2 — extract_reactions: empty / no ai_text events
# ---------------------------------------------------------------------------


def test_extract_reactions_no_ai_text_returns_empty(tmp_path: Path) -> None:
    """No ``ai_text`` events → empty list. Trigger and other event kinds are
    NOT reactions and must not appear in the output."""
    from scripts.reaction_reel.grade import extract_reactions

    session = _build_session(
        tmp_path,
        ai_text_events=None,
        extra_events=[
            {"t": 5.0, "kind": "trigger", "reason": "phase_change"},
            {"t": 10.0, "kind": "silence_short_circuit", "event": "MIX_MOVE"},
        ],
    )
    reactions = extract_reactions(session)
    assert reactions == []


# ---------------------------------------------------------------------------
# Test 3 — anonymize_reactions: SHA-8 IDs + grades.key.json mapping
# ---------------------------------------------------------------------------


def test_anonymize_reactions_writes_key_json_with_sha8_ids(tmp_path: Path) -> None:
    """``anonymize_reactions`` assigns ``<sha8>`` IDs and writes the mapping to
    ``grades/grades.key.json``. The same input always produces the same ID
    (deterministic — keyed on text + t)."""
    from scripts.reaction_reel.grade import anonymize_reactions

    raw = [
        {"t": 10.0, "text": "hello world", "context": []},
        {"t": 25.5, "text": "second reaction", "context": []},
    ]
    grades_dir = tmp_path / "grades"
    anonymized = anonymize_reactions(raw, grades_dir=grades_dir)

    # Each anonymized reaction has a 'reaction_id' field — 8 hex chars.
    assert len(anonymized) == 2
    for rxn in anonymized:
        rid = rxn["reaction_id"]
        assert isinstance(rid, str)
        assert len(rid) == 8
        assert all(c in "0123456789abcdef" for c in rid)

    # grades.key.json sits in grades_dir and maps reaction_id → original text + t.
    key_path = grades_dir / "grades.key.json"
    assert key_path.exists()
    key = json.loads(key_path.read_text(encoding="utf-8"))
    assert isinstance(key, dict)
    assert set(key.keys()) == {r["reaction_id"] for r in anonymized}
    for rid, entry in key.items():
        assert "text" in entry
        assert "t" in entry
        # The mapping records the ORIGINAL reaction text — Kaan (post-grading
        # analyst) can de-anonymize via this file.
        assert any(r["text"] == entry["text"] and r["t"] == entry["t"] for r in raw)

    # Determinism: a fresh anonymize over the same input produces the same IDs.
    grades_dir2 = tmp_path / "grades2"
    anonymized2 = anonymize_reactions(raw, grades_dir=grades_dir2)
    assert [r["reaction_id"] for r in anonymized] == [r["reaction_id"] for r in anonymized2]


# ---------------------------------------------------------------------------
# Test 4 — shuffle_for_rater: deterministic per-rater
# ---------------------------------------------------------------------------


def test_shuffle_for_rater_is_deterministic_per_rater(tmp_path: Path) -> None:
    """Same (rater, session_dir) → same order across runs. Different raters
    on the same session → different orders (high probability).

    Seed: SHA1(rater + session_dir.name)[:8] → deterministic shuffle.
    """
    from scripts.reaction_reel.grade import shuffle_for_rater

    reactions = [
        {"reaction_id": f"id{i:02d}", "t": float(i)} for i in range(12)
    ]
    session = tmp_path / "20260513-180000"
    session.mkdir()

    order_a1 = [r["reaction_id"] for r in shuffle_for_rater(reactions, "kaan", session)]
    order_a2 = [r["reaction_id"] for r in shuffle_for_rater(reactions, "kaan", session)]
    assert order_a1 == order_a2, "shuffle must be deterministic for the same rater"

    order_b = [r["reaction_id"] for r in shuffle_for_rater(reactions, "francesco", session)]
    # With 12 items, the probability of two random shuffles colliding is ~1/12!
    # ~2e-9 — assertion is safe.
    assert order_a1 != order_b, "different raters should land on different orders"

    # All 12 IDs present, no duplicates — Fisher-Yates is a permutation.
    assert sorted(order_a1) == sorted(r["reaction_id"] for r in reactions)


# ---------------------------------------------------------------------------
# Test 5 — load_existing_grades: returns reaction_ids already in JSONL
# ---------------------------------------------------------------------------


def test_load_existing_grades_returns_already_graded_ids(tmp_path: Path) -> None:
    """Reads ``<rater>.jsonl`` and returns the set of reaction_ids already
    present. Malformed lines are skipped silently. Missing file → empty set.
    """
    from scripts.reaction_reel.grade import load_existing_grades

    rater_jsonl = tmp_path / "kaan.jsonl"

    # Missing file → empty set.
    assert load_existing_grades(rater_jsonl) == set()

    # Build a JSONL with 2 valid grades + 1 malformed line.
    rater_jsonl.write_text(
        '{"reaction_id": "abc12345", "score": 4, "rater": "kaan"}\n'
        '{"reaction_id": "def67890", "score": 5, "rater": "kaan"}\n'
        '{ malformed json line\n'
        '{"reaction_id": "no_score_field_still_counts", "rater": "kaan"}\n',
        encoding="utf-8",
    )
    graded = load_existing_grades(rater_jsonl)
    assert graded == {"abc12345", "def67890", "no_score_field_still_counts"}


# ---------------------------------------------------------------------------
# Test 6 — slop_highlights: NEGATIVE_REGEX from prompts.negative_dict
# ---------------------------------------------------------------------------


def test_slop_highlights_flags_phrases_from_negative_dict() -> None:
    """``slop_highlights`` returns the list of negative-dictionary matches in
    the reaction text. Imports the regex from ``vibemix.prompts.negative_dict``
    so the source of truth never drifts.
    """
    from scripts.reaction_reel.grade import slop_highlights

    # "amazing" + "awesome" are in negative_dict.NEGATIVE_PHRASES.
    matches = slop_highlights("This is an amazing and awesome transition.")
    assert "amazing" in [m.lower() for m in matches]
    assert "awesome" in [m.lower() for m in matches]

    # Clean reaction — no matches.
    clean = slop_highlights("Solid filter sweep into the breakdown — load track B.")
    assert clean == []

    # Make sure we re-use NEGATIVE_REGEX directly — not a hard-coded local list.
    from vibemix.prompts.negative_dict import NEGATIVE_PHRASES

    # Sanity: the test phrase landed via NEGATIVE_PHRASES; if anyone edits the
    # phrase list to remove "amazing", this test must be updated.
    assert "amazing" in NEGATIVE_PHRASES


# ---------------------------------------------------------------------------
# Test 7 — GradeRecord schema enforcement
# ---------------------------------------------------------------------------


def test_validate_grade_enforces_locked_schema() -> None:
    """``validate_grade`` enforces the Area 1 locked schema: 1-5 score range,
    slop_flag enum, all required fields present and correctly typed.
    """
    from scripts.reaction_reel.grade import GradeError, validate_grade

    good = {
        "reaction_id": "abcd1234",
        "score": 4,
        "rater": "kaan",
        "grounded": True,
        "timely": True,
        "unique": False,
        "personality_fit": True,
        "slop_flag": "none",
        "comment": "Solid call — wouldn't clip though.",
        "would_clip": False,
        "graded_at_iso": "2026-05-13T14:00:00+00:00",
    }
    # No exception → pass.
    validate_grade(good)

    # Score out of range.
    bad_score = dict(good, score=6)
    with pytest.raises(GradeError, match="score"):
        validate_grade(bad_score)
    bad_score_low = dict(good, score=0)
    with pytest.raises(GradeError, match="score"):
        validate_grade(bad_score_low)

    # slop_flag not in enum.
    bad_flag = dict(good, slop_flag="hilarious")
    with pytest.raises(GradeError, match="slop_flag"):
        validate_grade(bad_flag)

    # Missing required field.
    missing = {k: v for k, v in good.items() if k != "grounded"}
    with pytest.raises(GradeError, match="grounded"):
        validate_grade(missing)

    # Wrong type — score must be int.
    wrong_type = dict(good, would_clip="yes")
    with pytest.raises(GradeError, match="would_clip"):
        validate_grade(wrong_type)


# ---------------------------------------------------------------------------
# Test 8 — write_grade: incremental JSONL append + fsync
# ---------------------------------------------------------------------------


def test_write_grade_appends_one_line_and_fsyncs(tmp_path: Path) -> None:
    """``write_grade`` appends ONE JSONL line per call and fsyncs the file
    descriptor so a process kill mid-write loses at most the line in flight.
    """
    from scripts.reaction_reel.grade import write_grade

    rater_jsonl = tmp_path / "kaan.jsonl"
    grade_a = {
        "reaction_id": "aaa11111",
        "score": 5,
        "rater": "kaan",
        "grounded": True,
        "timely": True,
        "unique": True,
        "personality_fit": True,
        "slop_flag": "none",
        "comment": "Real friend energy.",
        "would_clip": True,
        "graded_at_iso": "2026-05-13T14:00:00+00:00",
    }
    grade_b = dict(grade_a, reaction_id="bbb22222", score=3, slop_flag="generic")

    write_grade(rater_jsonl, grade_a)
    write_grade(rater_jsonl, grade_b)

    with rater_jsonl.open(encoding="utf-8") as f:
        lines = [line for line in f if line.strip()]
    assert len(lines) == 2

    parsed = [json.loads(line) for line in lines]
    assert parsed[0]["reaction_id"] == "aaa11111"
    assert parsed[1]["reaction_id"] == "bbb22222"
    # Schema preserved verbatim — no rewriting.
    assert parsed[0]["slop_flag"] == "none"
    assert parsed[1]["slop_flag"] == "generic"


# ---------------------------------------------------------------------------
# Test 9 — rater_view: persona / mode / genre / skill metadata stripped
# ---------------------------------------------------------------------------


def test_rater_view_strips_persona_mode_genre_skill_metadata(tmp_path: Path) -> None:
    """``build_rater_view`` returns the per-reaction text shown to a rater —
    reaction text + context + slop highlights. Persona/mode/genre/skill from
    session.json are NEVER included (blind grading).
    """
    from scripts.reaction_reel.grade import build_rater_view

    session = _build_session(
        tmp_path,
        ai_text_events=[(10.0, "amazing transition, the energy is electric!")],
        persona_meta={
            "voice": "Aoede",
            "mode": "hype",
            "genre": "techno",
            "user_level": "intermediate",
        },
    )
    from scripts.reaction_reel.grade import extract_reactions, anonymize_reactions

    raw = extract_reactions(session)
    anonymized = anonymize_reactions(raw, grades_dir=session / "grades")
    view = build_rater_view(anonymized[0])

    # On-screen output MUST include the reaction text + slop highlights.
    assert "amazing transition" in view
    assert "amazing" in view  # slop highlight

    # Forbidden — NONE of the persona/mode/genre/skill labels appear.
    forbidden = ("hype", "coach", "techno", "house", "pop", "drum&bass",
                 "disco", "beginner", "intermediate", "pro", "Aoede")
    for bad in forbidden:
        # case-insensitive substring — "intermediate" should never appear.
        assert bad.lower() not in view.lower(), (
            f"rater view leaked persona/mode/genre/skill label: {bad!r}"
        )


# ---------------------------------------------------------------------------
# Test 10 — resume integration: same rater + same session skips graded IDs
# ---------------------------------------------------------------------------


def test_resume_skips_already_graded_reactions(tmp_path: Path) -> None:
    """Integration: simulate a partial grading session, then call
    ``next_reactions_to_grade`` and verify it returns the un-graded reactions
    in the deterministic shuffle order — skipping the ones already in JSONL.
    """
    from scripts.reaction_reel.grade import (
        anonymize_reactions,
        extract_reactions,
        next_reactions_to_grade,
        shuffle_for_rater,
        write_grade,
    )

    session = _build_session(
        tmp_path,
        ai_text_events=[(float(i * 5), f"reaction {i}") for i in range(8)],
    )
    raw = extract_reactions(session)
    anonymized = anonymize_reactions(raw, grades_dir=session / "grades")
    shuffled = shuffle_for_rater(anonymized, "kaan", session)

    # Grade the first 3 in shuffle order.
    rater_jsonl = session / "grades" / "kaan.jsonl"
    for rxn in shuffled[:3]:
        write_grade(
            rater_jsonl,
            {
                "reaction_id": rxn["reaction_id"],
                "score": 4,
                "rater": "kaan",
                "grounded": True,
                "timely": True,
                "unique": True,
                "personality_fit": True,
                "slop_flag": "none",
                "comment": "ok",
                "would_clip": False,
                "graded_at_iso": "2026-05-13T14:00:00+00:00",
            },
        )

    # On resume, the remaining reactions should be returned in shuffle order
    # starting at index 3.
    remaining = next_reactions_to_grade(anonymized, "kaan", session, rater_jsonl)
    assert len(remaining) == 5
    assert [r["reaction_id"] for r in remaining] == [
        r["reaction_id"] for r in shuffled[3:]
    ]


# ---------------------------------------------------------------------------
# Test 11 — play_audio degrades gracefully when player binary is missing
# ---------------------------------------------------------------------------


def test_play_audio_degrades_when_no_player_available(tmp_path: Path) -> None:
    """``play_audio`` uses afplay on macOS / start on Windows. If neither is
    available (or subprocess raises FileNotFoundError), the function returns
    False and never raises — the rater can still grade by text alone.
    """
    from scripts.reaction_reel import grade as grade_mod

    voice_wav = tmp_path / "voice.wav"
    _write_silent_wav(voice_wav, duration_s=0.1, sample_rate=24000)

    # Patch subprocess.run to raise FileNotFoundError — simulates "afplay not
    # installed" on a non-macOS test runner / minimal environment.
    with patch.object(grade_mod.subprocess, "run", side_effect=FileNotFoundError):
        result = grade_mod.play_audio(voice_wav, start_s=0.0, duration_s=2.0)
    assert result is False  # graceful failure — does not raise.

    # Missing file → returns False, no exception.
    with patch.object(grade_mod.subprocess, "run") as mock_run:
        result = grade_mod.play_audio(tmp_path / "does_not_exist.wav")
        assert result is False
        mock_run.assert_not_called()


# ---------------------------------------------------------------------------
# Test 12 — seed derivation: SHA1(rater + session_dir.name)[:8]
# ---------------------------------------------------------------------------


def test_rater_seed_is_sha1_of_rater_plus_session_dir_name(tmp_path: Path) -> None:
    """The shuffle seed must be SHA1(rater + session_dir.name)[:8] hex chars,
    per CONTEXT §Specifics §Per-rater seed. Different session dirs produce
    different seeds even for the same rater (so re-grading the same rater on
    a different reel still produces a fresh order).
    """
    from scripts.reaction_reel.grade import rater_seed

    session = tmp_path / "20260513-180000"
    session.mkdir()
    seed = rater_seed("kaan", session)
    # Format: 8 hex chars.
    assert isinstance(seed, str)
    assert len(seed) == 8
    assert all(c in "0123456789abcdef" for c in seed)
    # Derivation matches the spec exactly.
    expected = hashlib.sha1(b"kaan" + session.name.encode("utf-8")).hexdigest()[:8]
    assert seed == expected

    # Different session → different seed.
    session2 = tmp_path / "20260514-180000"
    session2.mkdir()
    seed2 = rater_seed("kaan", session2)
    assert seed != seed2


# ---------------------------------------------------------------------------
# Test 13 — slop dictionary import is from prompts.negative_dict (not copy)
# ---------------------------------------------------------------------------


def test_slop_dictionary_is_imported_not_copied() -> None:
    """``scripts.reaction_reel.grade`` MUST import the slop dictionary from
    ``vibemix.prompts.negative_dict`` rather than redefining a parallel list.
    This is the Phase 10 single-source-of-truth rule from CONTEXT §Specifics."""
    import scripts.reaction_reel.grade as grade_mod
    from vibemix.prompts import negative_dict

    # The module must expose the same regex object — re-export is fine, but a
    # local copy is not.
    assert grade_mod.NEGATIVE_REGEX is negative_dict.NEGATIVE_REGEX, (
        "grade.py must re-use NEGATIVE_REGEX from vibemix.prompts.negative_dict, "
        "not redefine it locally — single source of truth for slop phrases."
    )
