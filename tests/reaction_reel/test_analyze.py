# SPDX-License-Identifier: Apache-2.0
"""Phase 17-03 — Reaction-reel slop analyzer unit tests.

Covers the autonomous deliverable for Area 3 / 4 (CONTEXT decisions):

1. ``compute_verdict`` implements the locked rubric: avg >= 4.0 AND zero
   1-2 ratings → PASS; otherwise FAIL; missing-rater or partial-grading →
   INCOMPLETE; tie-breaker band → PASS_TIE_BREAKER_NEEDED.
2. ``analyze_session`` orchestrates load → verdict → report.md + scores.csv,
   returns the rubric-mapped exit code.
3. ``build_report_md`` is a pure function that renders the report with a
   deterministic timestamp when ``now`` is injected (test-friendly).
4. ``build_scores_csv`` is a pure function with the locked CSV columns.
5. Output writes are atomic (tmp + os.replace).
6. Malformed JSONL lines are logged at WARNING and skipped, not silently
   dropped — verdict computed from validated records only.

14 tests total — see Plan 17-03 §behavior list.
"""

from __future__ import annotations

import csv as csv_mod
import io
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _make_grade_record(
    reaction_id: str,
    rater: str,
    score: int,
    *,
    grounded: bool = True,
    timely: bool = True,
    unique: bool = True,
    personality_fit: bool = True,
    slop_flag: str = "none",
    comment: str = "",
    would_clip: bool = False,
    graded_at_iso: str = "2026-05-13T14:00:00+00:00",
) -> dict:
    """Build a single valid grade record matching the locked schema."""
    return {
        "reaction_id": reaction_id,
        "score": int(score),
        "rater": rater,
        "grounded": bool(grounded),
        "timely": bool(timely),
        "unique": bool(unique),
        "personality_fit": bool(personality_fit),
        "slop_flag": slop_flag,
        "comment": comment,
        "would_clip": bool(would_clip),
        "graded_at_iso": graded_at_iso,
    }


def _write_rater_jsonl(grades_dir: Path, rater: str, records: list[dict]) -> Path:
    """Write a synthetic <rater>.jsonl atomically."""
    grades_dir.mkdir(parents=True, exist_ok=True)
    path = grades_dir / f"{rater}.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return path


def _write_grades_key(grades_dir: Path, mapping: dict[str, dict]) -> Path:
    """Write a synthetic grades.key.json mapping reaction_id → {text, t}."""
    grades_dir.mkdir(parents=True, exist_ok=True)
    path = grades_dir / "grades.key.json"
    path.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _synthesize_session(
    tmp_path: Path,
    *,
    raters: list[str],
    reaction_ids: list[str],
    score_by: Callable[[str, str], int],
    slop_flag_by: Optional[Callable[[str, str], str]] = None,
    comment_by: Optional[Callable[[str, str], str]] = None,
    write_key: bool = True,
) -> Path:
    """Build a synthetic <session_dir>/grades/ with N raters × M reactions.

    Returns the session_dir Path.
    """
    session_dir = tmp_path / "20260513-180000"
    grades_dir = session_dir / "grades"
    grades_dir.mkdir(parents=True, exist_ok=True)

    for rater in raters:
        records = []
        for rid in reaction_ids:
            score = score_by(rater, rid)
            flag = slop_flag_by(rater, rid) if slop_flag_by else "none"
            comment = comment_by(rater, rid) if comment_by else (
                "needs work" if score <= 3 else ""
            )
            records.append(_make_grade_record(
                rid, rater, score, slop_flag=flag, comment=comment,
            ))
        _write_rater_jsonl(grades_dir, rater, records)

    if write_key:
        mapping = {
            rid: {
                "text": f"reaction text for {rid}",
                "t": float(i * 5),
            }
            for i, rid in enumerate(reaction_ids)
        }
        _write_grades_key(grades_dir, mapping)

    return session_dir


# ---------------------------------------------------------------------------
# Test 1 — PASS verdict (4 raters × 10 reactions, all scores in {4, 5})
# ---------------------------------------------------------------------------


def test_pass_verdict_all_high_scores(tmp_path: Path) -> None:
    """4 raters × 10 reactions, alternating 4/5 → avg 4.5, zero 1-2 → PASS."""
    from scripts.reaction_reel.analyze import analyze_session, EXIT_PASS

    reaction_ids = [f"rxn{i:02d}aa" for i in range(10)]
    session = _synthesize_session(
        tmp_path,
        raters=["kaan", "francesco", "dj1", "dj2"],
        reaction_ids=reaction_ids,
        score_by=lambda rater, rid: 5 if int(rid[3:5]) % 2 == 0 else 4,
    )
    exit_code = analyze_session(session)
    assert exit_code == EXIT_PASS

    report = (session / "grades" / "report.md").read_text(encoding="utf-8")
    assert "Verdict:** PASS" in report or "**Verdict:** PASS" in report


# ---------------------------------------------------------------------------
# Test 2 — FAIL via average (4 raters × 10, all 3 → avg 3.0)
# ---------------------------------------------------------------------------


def test_fail_verdict_via_average(tmp_path: Path) -> None:
    """All raters give all reactions a 3 → avg 3.0 but zero 1-2 → FAIL on
    the average gate. Exit code 1."""
    from scripts.reaction_reel.analyze import analyze_session, EXIT_FAIL

    reaction_ids = [f"rxn{i:02d}aa" for i in range(10)]
    session = _synthesize_session(
        tmp_path,
        raters=["kaan", "francesco", "dj1", "dj2"],
        reaction_ids=reaction_ids,
        score_by=lambda rater, rid: 3,
    )
    exit_code = analyze_session(session)
    assert exit_code == EXIT_FAIL

    report = (session / "grades" / "report.md").read_text(encoding="utf-8")
    assert "FAIL" in report


# ---------------------------------------------------------------------------
# Test 3 — FAIL via single 2-score
# ---------------------------------------------------------------------------


def test_fail_verdict_single_two_score(tmp_path: Path) -> None:
    """Avg 4.5 but one rater gives one reaction a 2 → FAIL on the 1-2 gate."""
    from scripts.reaction_reel.analyze import analyze_session, EXIT_FAIL

    reaction_ids = [f"rxn{i:02d}aa" for i in range(10)]

    def score_by(rater: str, rid: str) -> int:
        if rater == "dj2" and rid == reaction_ids[0]:
            return 2
        return 5

    session = _synthesize_session(
        tmp_path,
        raters=["kaan", "francesco", "dj1", "dj2"],
        reaction_ids=reaction_ids,
        score_by=score_by,
        slop_flag_by=lambda rater, rid: "generic" if score_by(rater, rid) == 2 else "none",
    )
    exit_code = analyze_session(session)
    assert exit_code == EXIT_FAIL

    report = (session / "grades" / "report.md").read_text(encoding="utf-8")
    # The 1-2 enumeration table must call out the offending grade.
    assert reaction_ids[0] in report
    assert "dj2" in report


# ---------------------------------------------------------------------------
# Test 4 — FAIL via single 1-score
# ---------------------------------------------------------------------------


def test_fail_verdict_single_one_score(tmp_path: Path) -> None:
    """Avg 4.5 but one rater gives one reaction a 1 → FAIL on the 1-2 gate."""
    from scripts.reaction_reel.analyze import analyze_session, EXIT_FAIL

    reaction_ids = [f"rxn{i:02d}aa" for i in range(10)]

    def score_by(rater: str, rid: str) -> int:
        if rater == "kaan" and rid == reaction_ids[5]:
            return 1
        return 5

    session = _synthesize_session(
        tmp_path,
        raters=["kaan", "francesco", "dj1", "dj2"],
        reaction_ids=reaction_ids,
        score_by=score_by,
        slop_flag_by=lambda rater, rid: "cringe" if score_by(rater, rid) == 1 else "none",
    )
    exit_code = analyze_session(session)
    assert exit_code == EXIT_FAIL

    report = (session / "grades" / "report.md").read_text(encoding="utf-8")
    assert reaction_ids[5] in report
    # Reaction text from grades.key.json should be joined into the 1-2 table.
    assert f"reaction text for {reaction_ids[5]}" in report


# ---------------------------------------------------------------------------
# Test 5 — INCOMPLETE via missing rater
# ---------------------------------------------------------------------------


def test_incomplete_verdict_missing_rater(tmp_path: Path) -> None:
    """3 raters × 10 reactions, all 4-5 → INCOMPLETE (missing fourth rater)."""
    from scripts.reaction_reel.analyze import analyze_session, EXIT_INCOMPLETE

    reaction_ids = [f"rxn{i:02d}aa" for i in range(10)]
    session = _synthesize_session(
        tmp_path,
        raters=["kaan", "francesco", "dj1"],
        reaction_ids=reaction_ids,
        score_by=lambda rater, rid: 5,
    )
    exit_code = analyze_session(session)
    assert exit_code == EXIT_INCOMPLETE

    report = (session / "grades" / "report.md").read_text(encoding="utf-8")
    assert "INCOMPLETE" in report


# ---------------------------------------------------------------------------
# Test 6 — INCOMPLETE via partial grading
# ---------------------------------------------------------------------------


def test_incomplete_verdict_partial_grading(tmp_path: Path) -> None:
    """4 raters but kaan graded only 8 of 10 reactions → INCOMPLETE."""
    from scripts.reaction_reel.analyze import analyze_session, EXIT_INCOMPLETE

    reaction_ids = [f"rxn{i:02d}aa" for i in range(10)]
    session_dir = tmp_path / "20260513-180000"
    grades_dir = session_dir / "grades"
    grades_dir.mkdir(parents=True, exist_ok=True)

    # 3 raters fully grade all 10; kaan grades only first 8.
    for rater in ["francesco", "dj1", "dj2"]:
        recs = [_make_grade_record(rid, rater, 5) for rid in reaction_ids]
        _write_rater_jsonl(grades_dir, rater, recs)
    kaan_recs = [_make_grade_record(rid, "kaan", 5) for rid in reaction_ids[:8]]
    _write_rater_jsonl(grades_dir, "kaan", kaan_recs)

    _write_grades_key(grades_dir, {
        rid: {"text": f"reaction text for {rid}", "t": float(i)}
        for i, rid in enumerate(reaction_ids)
    })

    exit_code = analyze_session(session_dir)
    assert exit_code == EXIT_INCOMPLETE


# ---------------------------------------------------------------------------
# Test 7 — PASS_TIE_BREAKER_NEEDED (avg ≈ 4.0, ≥25% 3-scores)
# ---------------------------------------------------------------------------


def test_tie_breaker_needed_when_borderline_avg_and_many_threes(tmp_path: Path) -> None:
    """4 raters × 20 reactions, avg lands in [3.95, 4.05] AND >25% of records
    are score==3 → PASS_TIE_BREAKER_NEEDED, exit code 3.

    Construction: 4 × 20 = 80 records total. Target avg ≈ 4.0 with ≥21 threes
    (26.25%). Pattern per rater (20 reactions): 6 threes, 8 fours, 6 fives →
    sum = 18 + 32 + 30 = 80, avg per rater = 4.0. Across 4 raters: 24 threes
    (30%), avg 4.0, zero 1-2. Verdict = PASS_TIE_BREAKER_NEEDED.
    """
    from scripts.reaction_reel.analyze import analyze_session, EXIT_TIE_BREAKER

    reaction_ids = [f"rxn{i:02d}aa" for i in range(20)]

    # Per rater, scores by reaction index:
    # idx 0-5 → 3, idx 6-13 → 4, idx 14-19 → 5
    def score_by(rater: str, rid: str) -> int:
        idx = reaction_ids.index(rid)
        if idx < 6:
            return 3
        if idx < 14:
            return 4
        return 5

    session = _synthesize_session(
        tmp_path,
        raters=["kaan", "francesco", "dj1", "dj2"],
        reaction_ids=reaction_ids,
        score_by=score_by,
    )
    exit_code = analyze_session(session)
    assert exit_code == EXIT_TIE_BREAKER, (
        f"expected EXIT_TIE_BREAKER ({EXIT_TIE_BREAKER}), got {exit_code}"
    )


# ---------------------------------------------------------------------------
# Test 8 — Empty input → INCOMPLETE
# ---------------------------------------------------------------------------


def test_empty_grades_dir_returns_incomplete(tmp_path: Path) -> None:
    """Zero records → INCOMPLETE (can't determine pass/fail with no data)."""
    from scripts.reaction_reel.analyze import analyze_session, EXIT_INCOMPLETE

    session_dir = tmp_path / "20260513-180000"
    grades_dir = session_dir / "grades"
    grades_dir.mkdir(parents=True, exist_ok=True)
    _write_grades_key(grades_dir, {})

    exit_code = analyze_session(session_dir)
    assert exit_code == EXIT_INCOMPLETE


# ---------------------------------------------------------------------------
# Test 9 — Per-rater breakdown correctness
# ---------------------------------------------------------------------------


def test_per_rater_breakdown_correctness(tmp_path: Path) -> None:
    """kaan all-5, francesco all-4, dj1 all-4, dj2 all-5 → per-rater table
    shows kaan=5.0, francesco=4.0, dj1=4.0, dj2=5.0 (avg 4.5, PASS)."""
    from scripts.reaction_reel.analyze import analyze_session, EXIT_PASS

    reaction_ids = [f"rxn{i:02d}aa" for i in range(10)]

    def score_by(rater: str, rid: str) -> int:
        return 5 if rater in {"kaan", "dj2"} else 4

    session = _synthesize_session(
        tmp_path,
        raters=["kaan", "francesco", "dj1", "dj2"],
        reaction_ids=reaction_ids,
        score_by=score_by,
    )
    exit_code = analyze_session(session)
    assert exit_code == EXIT_PASS

    report = (session / "grades" / "report.md").read_text(encoding="utf-8")
    # Per-rater table must surface each rater's average.
    assert "5.00" in report or "5.0" in report  # kaan / dj2
    assert "4.00" in report or "4.0" in report  # francesco / dj1
    # All rater names present in the table.
    for rater in ("kaan", "francesco", "dj1", "dj2"):
        assert rater in report


# ---------------------------------------------------------------------------
# Test 10 — 1-2 enumeration with reaction_text joined from grades.key.json
# ---------------------------------------------------------------------------


def test_low_score_enumeration_joins_reaction_text(tmp_path: Path) -> None:
    """Two raters give 1-2 scores; report.md "All 1-2 ratings" enumerates both
    with the reaction text joined from grades.key.json."""
    from scripts.reaction_reel.analyze import analyze_session, EXIT_FAIL

    reaction_ids = [f"rxn{i:02d}aa" for i in range(10)]

    def score_by(rater: str, rid: str) -> int:
        if rater == "kaan" and rid == reaction_ids[0]:
            return 2
        if rater == "dj2" and rid == reaction_ids[3]:
            return 1
        return 5

    def comment_by(rater: str, rid: str) -> str:
        if score_by(rater, rid) <= 2:
            return f"this is {rater}'s issue with {rid}"
        return ""

    def slop_flag_by(rater: str, rid: str) -> str:
        s = score_by(rater, rid)
        if s == 1:
            return "cringe"
        if s == 2:
            return "generic"
        return "none"

    session_dir = tmp_path / "20260513-180000"
    grades_dir = session_dir / "grades"
    grades_dir.mkdir(parents=True, exist_ok=True)
    for rater in ["kaan", "francesco", "dj1", "dj2"]:
        recs = [
            _make_grade_record(
                rid, rater, score_by(rater, rid),
                slop_flag=slop_flag_by(rater, rid),
                comment=comment_by(rater, rid),
            )
            for rid in reaction_ids
        ]
        _write_rater_jsonl(grades_dir, rater, recs)

    _write_grades_key(grades_dir, {
        rid: {"text": f"the reaction text for {rid}", "t": float(i)}
        for i, rid in enumerate(reaction_ids)
    })

    exit_code = analyze_session(session_dir)
    assert exit_code == EXIT_FAIL

    report = (session_dir / "grades" / "report.md").read_text(encoding="utf-8")
    # Both 1-2 records must appear with reaction text and rater identity.
    assert f"the reaction text for {reaction_ids[0]}" in report
    assert f"the reaction text for {reaction_ids[3]}" in report
    assert "kaan" in report
    assert "dj2" in report
    # slop_flag surfaced.
    assert "generic" in report
    assert "cringe" in report


# ---------------------------------------------------------------------------
# Test 11 — Schema strictness: malformed records logged WARNING, skipped
# ---------------------------------------------------------------------------


def test_malformed_records_logged_and_skipped(tmp_path: Path, caplog) -> None:
    """A JSONL line with missing fields or wrong enum value MUST be logged
    at WARNING and skipped from the verdict computation."""
    from scripts.reaction_reel.analyze import analyze_session, EXIT_PASS

    session_dir = tmp_path / "20260513-180000"
    grades_dir = session_dir / "grades"
    grades_dir.mkdir(parents=True, exist_ok=True)

    # 4 raters × 10 records each, all 5s; insert one malformed line in
    # kaan.jsonl (missing 'rater' field) and one with bad enum value.
    reaction_ids = [f"rxn{i:02d}aa" for i in range(10)]
    for rater in ["francesco", "dj1", "dj2"]:
        recs = [_make_grade_record(rid, rater, 5) for rid in reaction_ids]
        _write_rater_jsonl(grades_dir, rater, recs)

    kaan_path = grades_dir / "kaan.jsonl"
    with kaan_path.open("w", encoding="utf-8") as f:
        for rid in reaction_ids:
            f.write(json.dumps(_make_grade_record(rid, "kaan", 5)) + "\n")
        # Malformed: missing rater field
        f.write(json.dumps({"reaction_id": "BADRECRD", "score": 5}) + "\n")
        # Malformed: invalid slop_flag enum
        bad = _make_grade_record("BADRECR2", "kaan", 5)
        bad["slop_flag"] = "definitely-not-an-enum-value"
        f.write(json.dumps(bad) + "\n")

    _write_grades_key(grades_dir, {
        rid: {"text": f"reaction text for {rid}", "t": float(i)}
        for i, rid in enumerate(reaction_ids)
    })

    with caplog.at_level(logging.WARNING):
        exit_code = analyze_session(session_dir)

    # Verdict still PASS — malformed records skipped, the 40 valid ones win.
    assert exit_code == EXIT_PASS

    # WARNING log entries for the skipped records.
    warning_text = "\n".join(r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING)
    assert "BADRECRD" in warning_text or "missing" in warning_text.lower()
    assert "BADRECR2" in warning_text or "slop_flag" in warning_text.lower()


# ---------------------------------------------------------------------------
# Test 12 — scores.csv shape and row count
# ---------------------------------------------------------------------------


def test_scores_csv_shape_and_row_count(tmp_path: Path) -> None:
    """scores.csv has the documented columns; row count == sum across raters
    of reactions graded."""
    from scripts.reaction_reel.analyze import analyze_session, EXIT_PASS

    reaction_ids = [f"rxn{i:02d}aa" for i in range(5)]
    session = _synthesize_session(
        tmp_path,
        raters=["kaan", "francesco", "dj1", "dj2"],
        reaction_ids=reaction_ids,
        score_by=lambda rater, rid: 5,
    )
    exit_code = analyze_session(session)
    assert exit_code == EXIT_PASS

    csv_path = session / "grades" / "scores.csv"
    assert csv_path.exists()
    with csv_path.open(encoding="utf-8", newline="") as f:
        reader = csv_mod.DictReader(f)
        rows = list(reader)

    # 4 raters × 5 reactions = 20 rows.
    assert len(rows) == 20
    # Documented columns.
    expected_cols = {
        "reaction_id", "rater", "score", "grounded", "timely", "unique",
        "personality_fit", "slop_flag", "comment", "would_clip",
        "graded_at_iso", "reaction_text",
    }
    assert expected_cols.issubset(set(rows[0].keys()))
    # reaction_text joined from grades.key.json.
    assert any("reaction text for" in r["reaction_text"] for r in rows)


# ---------------------------------------------------------------------------
# Test 13 — build_report_md is deterministic when `now` is injected
# ---------------------------------------------------------------------------


def test_build_report_md_is_deterministic_with_injected_now(tmp_path: Path) -> None:
    """Calling build_report_md twice with the same inputs returns identical
    strings when ``now`` is injected (no timestamp drift in test mode)."""
    from scripts.reaction_reel.analyze import (
        build_report_md,
        compute_verdict,
        load_all_grades,
        load_grades_key,
    )

    reaction_ids = [f"rxn{i:02d}aa" for i in range(4)]
    session = _synthesize_session(
        tmp_path,
        raters=["kaan", "francesco", "dj1", "dj2"],
        reaction_ids=reaction_ids,
        score_by=lambda rater, rid: 5,
    )
    grades_dir = session / "grades"
    records, raters_present = load_all_grades(grades_dir)
    key = load_grades_key(grades_dir)
    verdict, metrics = compute_verdict(records, raters_present)

    fixed_now = datetime(2026, 5, 13, 14, 0, 0, tzinfo=timezone.utc)

    md_a = build_report_md(
        verdict, metrics, records=records, key=key,
        session_dir_name=session.name, now=fixed_now,
    )
    md_b = build_report_md(
        verdict, metrics, records=records, key=key,
        session_dir_name=session.name, now=fixed_now,
    )
    assert md_a == md_b
    # The injected timestamp must appear in the output.
    assert "2026-05-13" in md_a


# ---------------------------------------------------------------------------
# Test 14 — Atomic writes: failure mid-write leaves previous file intact
# ---------------------------------------------------------------------------


def test_atomic_write_leaves_previous_file_intact_on_failure(tmp_path: Path) -> None:
    """If os.replace raises OSError during report write, the previous
    file (if any) MUST remain readable — no half-written corruption."""
    from scripts.reaction_reel import analyze as analyze_mod

    # Pre-populate a "previous" report.md with sentinel content.
    session_dir = tmp_path / "20260513-180000"
    grades_dir = session_dir / "grades"
    grades_dir.mkdir(parents=True, exist_ok=True)

    reaction_ids = [f"rxn{i:02d}aa" for i in range(3)]
    for rater in ["kaan", "francesco", "dj1", "dj2"]:
        recs = [_make_grade_record(rid, rater, 5) for rid in reaction_ids]
        _write_rater_jsonl(grades_dir, rater, recs)
    _write_grades_key(grades_dir, {
        rid: {"text": f"reaction text for {rid}", "t": float(i)}
        for i, rid in enumerate(reaction_ids)
    })

    # Write a "previous" report.md the test expects to be preserved.
    sentinel = "PREVIOUS REPORT — must survive failed write"
    (grades_dir / "report.md").write_text(sentinel, encoding="utf-8")

    # Patch os.replace to raise OSError on the first call only.
    call_count = {"n": 0}
    real_replace = os.replace

    def fake_replace(src, dst):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise OSError("simulated mid-write failure")
        return real_replace(src, dst)

    with patch.object(analyze_mod.os, "replace", side_effect=fake_replace):
        with pytest.raises(OSError):
            analyze_mod.analyze_session(session_dir)

    # The previous file content survives — atomic write contract.
    assert (grades_dir / "report.md").read_text(encoding="utf-8") == sentinel
