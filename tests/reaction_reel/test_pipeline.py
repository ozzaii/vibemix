# SPDX-License-Identifier: Apache-2.0
"""Phase 17-03 — End-to-end pipeline integration tests.

Synthesizes ``recordings/<session>/`` dirs with events.jsonl + voice.wav,
drives the full grade.py + analyze.py pipeline against the synthesized
inputs, and verifies the report.md + scores.csv verdict matches expectation.

Six integration tests:

1. Full PASS pipeline (10 reactions × 4 raters all 4-5 → PASS).
2. Full FAIL via 2-score (one rater gives a 2 → FAIL; 1-2 table enumerates).
3. INCOMPLETE via missing rater (3 raters only → INCOMPLETE).
4. Pipeline via grade.py's main() with mocked stdin (real CLI path).
5. Anti-slop dictionary linkage (NEGATIVE_PHRASES visible in grade.py source).
6. POC files untouched (paranoia invariant for CI).

CI-clean: no real audio I/O, tmp_path for all session dirs, monkeypatched
subprocess.run for the playback path. CONTEXT references:
  Area 3 §Blind-Grading Tooling — pipeline shape
  Area 4 §Iteration Loop — verdict drives Phase 10 re-entry
  Plan 17-03 Task 2 §behavior
"""

from __future__ import annotations

import json
import wave
from pathlib import Path
from typing import Callable, Optional
from unittest.mock import patch

import pytest

from scripts.reaction_reel import analyze as analyze_mod
from scripts.reaction_reel import grade as grade_mod
from vibemix.prompts import NEGATIVE_PHRASES


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _write_silent_wav(path: Path, *, duration_s: float, sample_rate: int) -> None:
    """Write a real WAV file with ``duration_s`` seconds of silent int16 mono PCM.

    Uses the wave stdlib module (no numpy dep — keeps the integration test
    light and CI-friendly across platforms).
    """
    n_frames = int(duration_s * sample_rate)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        # Silent int16 PCM: 2 bytes per frame × n_frames bytes total.
        w.writeframes(b"\x00\x00" * n_frames)


def _build_synthetic_session(
    tmp_path: Path,
    *,
    dir_name: str = "20260513-180000",
    ai_text_events: Optional[list[tuple[float, str]]] = None,
    extra_events: Optional[list[dict]] = None,
) -> Path:
    """Build a synthetic recording session dir with events.jsonl, session.json,
    voice.wav, input.wav. Returns the session_dir Path."""
    session_dir = tmp_path / dir_name
    session_dir.mkdir(parents=True, exist_ok=True)

    # WAV files — short, silent, real headers.
    _write_silent_wav(session_dir / "voice.wav", duration_s=2.0, sample_rate=24000)
    _write_silent_wav(session_dir / "input.wav", duration_s=2.0, sample_rate=16000)

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
            lines.append({
                "t": t,
                "kind": "ai_text",
                "text": text,
                "latency_s": 1.2,
            })
    with events_path.open("w", encoding="utf-8") as f:
        for rec in sorted(lines, key=lambda r: r["t"]):
            json.dump(rec, f, ensure_ascii=False)
            f.write("\n")

    # session.json carries persona/mode/genre/skill — should be stripped from
    # the rater view (verified separately in test_grade.py).
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
    (session_dir / "session.json").write_text(
        json.dumps(meta), encoding="utf-8",
    )
    return session_dir


def _populated_grades(session_dir: Path) -> tuple[list[dict], list[str]]:
    """Run the grade.py extraction + anonymization stages against a synthesized
    session and return ``(anonymized_reactions, reaction_ids)``. Mirrors what
    a real rater workflow would have produced up to the point of grading.
    """
    raw = grade_mod.extract_reactions(session_dir)
    grades_dir = session_dir / "grades"
    anonymized = grade_mod.anonymize_reactions(raw, grades_dir=grades_dir)
    reaction_ids = [r["reaction_id"] for r in anonymized]
    return anonymized, reaction_ids


def _write_synthetic_grades(
    session_dir: Path,
    rater: str,
    reaction_ids: list[str],
    score_func: Callable[[int, str], int],
    *,
    slop_flag_func: Optional[Callable[[int, str], str]] = None,
    comment_func: Optional[Callable[[int, str], str]] = None,
    graded_at_iso: str = "2026-05-13T14:00:00+00:00",
) -> Path:
    """Synthesize a <rater>.jsonl by writing grade records via grade.write_grade.

    Uses the real producer-side writer so analyze.py reads exactly what
    grade.py would have produced. No terminal UI involvement.
    """
    grades_dir = session_dir / "grades"
    grades_dir.mkdir(parents=True, exist_ok=True)
    rater_jsonl = grades_dir / f"{rater}.jsonl"
    for i, rid in enumerate(reaction_ids):
        score = score_func(i, rid)
        flag = slop_flag_func(i, rid) if slop_flag_func else "none"
        comment = (
            comment_func(i, rid)
            if comment_func is not None
            else ("needs work" if score <= 3 else "")
        )
        record = {
            "reaction_id": rid,
            "score": int(score),
            "rater": rater,
            "grounded": True,
            "timely": True,
            "unique": True,
            "personality_fit": True,
            "slop_flag": flag,
            "comment": comment,
            "would_clip": False,
            "graded_at_iso": graded_at_iso,
        }
        grade_mod.write_grade(rater_jsonl, record)
    return rater_jsonl


# ---------------------------------------------------------------------------
# Test 1 — Full PASS pipeline (synthesized recordings → grade → analyze)
# ---------------------------------------------------------------------------


def test_pipeline_full_pass(tmp_path: Path) -> None:
    """Synthesize 10 ai_text events, write 4 rater JSONLs (all 4-5) via the
    real producer-side writer, run analyze.analyze_session → PASS verdict,
    exit code 0, report.md contains 'Verdict: PASS', scores.csv has 40 rows.
    """
    session = _build_synthetic_session(
        tmp_path,
        ai_text_events=[
            (float(i * 5) + 5.0, f"reaction text {i}") for i in range(10)
        ],
    )
    _, reaction_ids = _populated_grades(session)
    assert len(reaction_ids) == 10

    for rater in ("kaan", "francesco", "dj1", "dj2"):
        _write_synthetic_grades(
            session, rater, reaction_ids,
            score_func=lambda i, rid: 5 if i % 2 == 0 else 4,
        )

    exit_code = analyze_mod.analyze_session(session)
    assert exit_code == analyze_mod.EXIT_PASS

    report = (session / "grades" / "report.md").read_text(encoding="utf-8")
    assert "Verdict:** PASS" in report

    # scores.csv → 4 × 10 = 40 rows of data (plus the header).
    import csv as csv_mod
    with (session / "grades" / "scores.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv_mod.DictReader(f))
    assert len(rows) == 40
    # reaction_text joined from grades.key.json.
    assert any("reaction text" in r["reaction_text"] for r in rows)


# ---------------------------------------------------------------------------
# Test 2 — Full FAIL via 2-score (1-2 enumeration surfaces the offender)
# ---------------------------------------------------------------------------


def test_pipeline_full_fail_via_two_score(tmp_path: Path) -> None:
    """Same setup but dj2 gives reaction #3 a score of 2 with slop_flag=generic
    and a comment → analyze reports FAIL, exit code 1, 1-2 table enumerates
    the 2-score with the correct rater + reaction text from grades.key.json.
    """
    reaction_texts = [f"reaction text {i}" for i in range(10)]
    session = _build_synthetic_session(
        tmp_path,
        ai_text_events=[
            (float(i * 5) + 5.0, reaction_texts[i]) for i in range(10)
        ],
    )
    _, reaction_ids = _populated_grades(session)
    target_idx = 3
    target_rid = reaction_ids[target_idx]
    target_text = reaction_texts[target_idx]
    canned_comment = "this transition was textbook slop"

    def score_func(rater: str, i: int, rid: str) -> int:
        if rater == "dj2" and rid == target_rid:
            return 2
        return 5

    for rater in ("kaan", "francesco", "dj1", "dj2"):
        _write_synthetic_grades(
            session, rater, reaction_ids,
            score_func=lambda i, rid, r=rater: score_func(r, i, rid),
            slop_flag_func=lambda i, rid, r=rater: (
                "generic" if score_func(r, i, rid) == 2 else "none"
            ),
            comment_func=lambda i, rid, r=rater: (
                canned_comment if score_func(r, i, rid) == 2 else ""
            ),
        )

    exit_code = analyze_mod.analyze_session(session)
    assert exit_code == analyze_mod.EXIT_FAIL

    report = (session / "grades" / "report.md").read_text(encoding="utf-8")
    # The 1-2 enumeration table surfaces this exact record.
    assert target_rid in report
    assert "dj2" in report
    assert "generic" in report
    assert canned_comment in report
    # And the reaction_text from grades.key.json is joined into the same row.
    assert target_text in report


# ---------------------------------------------------------------------------
# Test 3 — INCOMPLETE via missing rater (only 3 raters present)
# ---------------------------------------------------------------------------


def test_pipeline_incomplete_via_missing_rater(tmp_path: Path) -> None:
    """Only 3 rater JSONLs exist (no dj2) → analyze reports INCOMPLETE, exit
    code 2. The verdict is INCOMPLETE regardless of how high the present
    scores are."""
    session = _build_synthetic_session(
        tmp_path,
        ai_text_events=[
            (float(i * 5) + 5.0, f"reaction text {i}") for i in range(10)
        ],
    )
    _, reaction_ids = _populated_grades(session)

    for rater in ("kaan", "francesco", "dj1"):
        _write_synthetic_grades(
            session, rater, reaction_ids,
            score_func=lambda i, rid: 5,
        )

    exit_code = analyze_mod.analyze_session(session)
    assert exit_code == analyze_mod.EXIT_INCOMPLETE

    report = (session / "grades" / "report.md").read_text(encoding="utf-8")
    assert "INCOMPLETE" in report


# ---------------------------------------------------------------------------
# Test 4 — Real grade.py main() via mocked stdin → analyze
# ---------------------------------------------------------------------------


def test_pipeline_grade_main_via_mocked_stdin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Drive grade.main() with monkeypatched input() to write a real rater
    JSONL (2 reactions, score 5), then run analyze.analyze_session on a
    full 4-rater setup that fills in the rest of the grades. Verifies the
    two halves of the pipeline integrate at the public-API level.

    grade.main() asks per reaction:
      score, grounded, timely, unique, personality_fit, slop_flag,
      would_clip, comment

    Per the schema and the rater UX: 8 prompts per reaction (7 y/n/choice +
    one free-text comment).
    """
    # Build a session with exactly 2 ai_text events so grade.main() prompts
    # us for 2 reactions only — keeps the canned-input list short.
    session = _build_synthetic_session(
        tmp_path,
        ai_text_events=[
            (5.0, "first reaction text"),
            (15.0, "second reaction text"),
        ],
    )

    # Each reaction prompts: score, grounded, timely, unique, personality_fit,
    # slop_flag, would_clip, comment → 8 inputs per reaction.
    canned_per_reaction = ["5", "y", "y", "y", "y", "none", "y", ""]
    canned_inputs = canned_per_reaction * 2
    input_iter = iter(canned_inputs)

    def fake_input(prompt: str = "") -> str:
        try:
            return next(input_iter)
        except StopIteration:
            raise AssertionError(
                f"grade.main() asked for more input than canned "
                f"({len(canned_inputs)} answers used). Last prompt: {prompt!r}"
            )

    monkeypatch.setattr("builtins.input", fake_input)
    # Stub subprocess so play_audio's afplay invocation is a no-op.
    monkeypatch.setattr(
        "scripts.reaction_reel.grade.subprocess.run",
        lambda *a, **kw: None,
    )

    rc = grade_mod.main([str(session), "kaan"])
    assert rc == 0, "grade.main() should exit 0 on full completion"

    rater_jsonl = session / "grades" / "kaan.jsonl"
    assert rater_jsonl.exists()
    with rater_jsonl.open(encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]
    assert len(records) == 2
    assert {r["score"] for r in records} == {5}
    assert {r["rater"] for r in records} == {"kaan"}

    # Round out the remaining 3 raters synthetically to satisfy the analyzer's
    # 4-rater expectation, then run the verdict.
    reaction_ids = [r["reaction_id"] for r in records]
    for rater in ("francesco", "dj1", "dj2"):
        _write_synthetic_grades(
            session, rater, reaction_ids,
            score_func=lambda i, rid: 5,
        )
    exit_code = analyze_mod.analyze_session(session)
    assert exit_code == analyze_mod.EXIT_PASS

    report = (session / "grades" / "report.md").read_text(encoding="utf-8")
    assert "Verdict:** PASS" in report
    # kaan's grade flowed through to the report.
    assert "kaan" in report


# ---------------------------------------------------------------------------
# Test 5 — Anti-slop dictionary linkage (NEGATIVE_PHRASES visible in grade.py)
# ---------------------------------------------------------------------------


def test_pipeline_anti_slop_dictionary_is_linked_to_grade_module() -> None:
    """The anti-slop dictionary (NEGATIVE_PHRASES from vibemix.prompts) must
    be alive — not just on paper — in the rater pipeline. Verify:

      1. grade_mod re-exports NEGATIVE_REGEX from vibemix.prompts.negative_dict
         (identity check, not a copy).
      2. At least one phrase from NEGATIVE_PHRASES would be flagged by
         grade.slop_highlights when present in reaction text.
      3. The grade.py source file references the dictionary so a future
         contributor can find the wiring point.
    """
    from vibemix.prompts.negative_dict import NEGATIVE_REGEX

    # Linkage by identity, not value.
    assert grade_mod.NEGATIVE_REGEX is NEGATIVE_REGEX, (
        "grade.NEGATIVE_REGEX must be the same object as "
        "vibemix.prompts.negative_dict.NEGATIVE_REGEX (single source of truth)"
    )

    # Functional check — at least one phrase in the dictionary lights up
    # slop_highlights when present in a reaction.
    sample_phrase = next(p for p in NEGATIVE_PHRASES)
    test_text = f"this is {sample_phrase} for sure"
    hits = grade_mod.slop_highlights(test_text)
    assert hits, f"NEGATIVE_PHRASES phrase {sample_phrase!r} not flagged by slop_highlights"

    # The grade.py source must reference the dictionary by name so the
    # wiring is grep-findable for future contributors.
    source = Path(grade_mod.__file__).read_text(encoding="utf-8")
    assert "NEGATIVE_REGEX" in source
    assert "negative_dict" in source


# ---------------------------------------------------------------------------
# Test 6 — POC files untouched (paranoia invariant for CI)
# ---------------------------------------------------------------------------


def test_pipeline_poc_files_untouched_after_pipeline_run(tmp_path: Path) -> None:
    """After running the full pipeline, the synthesized recordings dir must
    NOT contain any files matching the POC pattern (cohost*.py, mascot.html).
    Phase 17 is read-only against the POC; the test pins the invariant.

    This is paranoia, not a realistic threat — but it pins a CI signal so a
    future contributor who accidentally writes a cohost*.py inside the
    grading harness gets caught.
    """
    session = _build_synthetic_session(
        tmp_path,
        ai_text_events=[
            (float(i * 5) + 5.0, f"reaction text {i}") for i in range(4)
        ],
    )
    _, reaction_ids = _populated_grades(session)
    for rater in ("kaan", "francesco", "dj1", "dj2"):
        _write_synthetic_grades(
            session, rater, reaction_ids,
            score_func=lambda i, rid: 5,
        )
    analyze_mod.analyze_session(session)

    # Walk the entire synthesized session dir; no POC artifacts allowed.
    forbidden_globs = ("cohost*.py", "mascot.html", "cohost.streaming.py.bak")
    for pattern in forbidden_globs:
        leaks = list(session.rglob(pattern))
        assert not leaks, (
            f"pipeline run leaked POC artifact pattern {pattern!r}: {leaks}"
        )
