# SPDX-License-Identifier: Apache-2.0
"""Phase 17-03 — Reaction-reel slop grading aggregator.

Usage:
    python -m scripts.reaction_reel.analyze <session_dir> [--output-dir PATH]
                                              [--quiet]

Reads every ``<session_dir>/grades/<rater>.jsonl`` produced by Plan 17-02's
``grade.py``, validates each record against the locked schema, computes the
pass/fail verdict against ``17-RUBRIC.md`` thresholds, and writes a
deterministic ``report.md`` + flat ``scores.csv`` to the same grades dir.

Verdict logic (per ``17-RUBRIC.md`` and CONTEXT Area 4):

* **PASS** — at least one record present, all expected raters present,
  every reaction graded by every present rater, avg score ≥ 4.0,
  zero records with score in {1, 2}.
* **FAIL** — avg < 4.0 OR any record with score in {1, 2}.
* **INCOMPLETE** — zero records, fewer raters than expected, or any
  reaction missing a grade from any present rater.
* **PASS_TIE_BREAKER_NEEDED** — would-be-PASS, but avg lands in
  ``[4.00 - 0.05, 4.00 + 0.05]`` AND share of 3-scores exceeds
  ``TIE_BREAKER_THREE_PCT`` (25%). Triggers Kaan's manual ship-vs-iterate
  decision per Plan 17-01's iteration loop.

Exit codes map 1:1 to verdicts so the iteration loop document
(17-ITERATION-LOOP.md) can pin the re-entry trigger mechanically:

  0 — PASS
  1 — FAIL
  2 — INCOMPLETE
  3 — PASS_TIE_BREAKER_NEEDED

Writes are atomic (tmp + ``os.replace``) — a mid-write OSError leaves the
previous file intact so the iteration loop never sees half-flushed output.

CONTEXT references:
  Area 3 §Blind-Grading Tooling — analyze.py spec
  Area 4 §Iteration Loop — verdict-driven Phase 10 re-entry trigger
  17-RUBRIC.md §Pass Thresholds & Tie-Breaker
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import logging
import os
import statistics
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

logger = logging.getLogger(__name__)

__all__ = [
    "EXIT_PASS",
    "EXIT_FAIL",
    "EXIT_INCOMPLETE",
    "EXIT_TIE_BREAKER",
    "EXPECTED_RATERS",
    "PASS_AVG_THRESHOLD",
    "TIE_BREAKER_BAND",
    "TIE_BREAKER_THREE_PCT",
    "VALID_RATERS",
    "SLOP_FLAGS",
    "VERDICT_PASS",
    "VERDICT_FAIL",
    "VERDICT_INCOMPLETE",
    "VERDICT_TIE_BREAKER",
    "analyze_session",
    "build_report_md",
    "build_scores_csv",
    "compute_verdict",
    "enumerate_low_scores",
    "load_all_grades",
    "load_grades_key",
    "main",
    "validate_record",
]


# ---------------------------------------------------------------------------
# Rubric thresholds + named constants — encode 17-RUBRIC.md verbatim
# ---------------------------------------------------------------------------

#: Expected rater roster (per CONTEXT Area 1 + 17-RUBRIC.md §3 schema).
VALID_RATERS: tuple[str, ...] = ("kaan", "francesco", "dj1", "dj2")

#: Required rater count for a non-INCOMPLETE verdict.
EXPECTED_RATERS: int = 4

#: Pass-threshold average per ROADMAP Success Criterion #3 / 17-RUBRIC.md §5.
PASS_AVG_THRESHOLD = 4.0

#: Half-width of the tie-breaker band around PASS_AVG_THRESHOLD.
TIE_BREAKER_BAND = 0.05

#: Share of score==3 records that triggers PASS_TIE_BREAKER_NEEDED when
#: the average lands inside the tie-breaker band.
TIE_BREAKER_THREE_PCT = 0.25

#: Allowed slop_flag enum values (mirrors grade.py SLOP_FLAGS — re-defined
#: here for module independence so analyze.py never imports grade.py).
SLOP_FLAGS: tuple[str, ...] = (
    "none",
    "late",
    "generic",
    "hallucination",
    "repetition",
    "cringe",
)

#: Verdict strings — written verbatim into report.md.
VERDICT_PASS: str = "PASS"
VERDICT_FAIL: str = "FAIL"
VERDICT_INCOMPLETE: str = "INCOMPLETE"
VERDICT_TIE_BREAKER: str = "PASS_TIE_BREAKER_NEEDED"

#: Exit codes — mapped 1:1 to verdicts for shell/CI integration.
EXIT_PASS: int = 0
EXIT_FAIL: int = 1
EXIT_INCOMPLETE: int = 2
EXIT_TIE_BREAKER: int = 3

_VERDICT_TO_EXIT: dict[str, int] = {
    VERDICT_PASS: EXIT_PASS,
    VERDICT_FAIL: EXIT_FAIL,
    VERDICT_INCOMPLETE: EXIT_INCOMPLETE,
    VERDICT_TIE_BREAKER: EXIT_TIE_BREAKER,
}


# Locked grade-record schema. Mirrors grade.py's _REQUIRED_FIELDS plus the
# ``graded_at_iso`` field that grade.py writes (recorded in 17-RUBRIC.md
# §Per-Reaction Grade Fields). Booleans are checked strictly (bool-as-int
# is rejected) for defense-in-depth — the producer (grade.py) already
# enforces this but the analyzer is a second line.
_REQUIRED_FIELDS: dict[str, type | tuple[type, ...]] = {
    "reaction_id": str,
    "score": int,
    "rater": str,
    "grounded": bool,
    "timely": bool,
    "unique": bool,
    "personality_fit": bool,
    "slop_flag": str,
    "comment": str,
    "would_clip": bool,
    "graded_at_iso": str,
}

#: scores.csv column order (locked for external spreadsheet consumers).
_CSV_COLUMNS: tuple[str, ...] = (
    "reaction_id",
    "rater",
    "score",
    "grounded",
    "timely",
    "unique",
    "personality_fit",
    "slop_flag",
    "comment",
    "would_clip",
    "graded_at_iso",
    "reaction_text",
)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_record(record: object, *, source: str = "") -> bool:
    """Validate ``record`` against the locked grade-record schema.

    Returns True iff every required field is present, has the correct type,
    score is in 1..5, and slop_flag is in :data:`SLOP_FLAGS`. On any
    violation, emits a WARNING to :data:`logger` and returns False — the
    caller skips the record from verdict computation.

    ``source`` is included verbatim in the warning so the operator can trace
    back to the offending JSONL file + line.
    """
    if not isinstance(record, dict):
        logger.warning(
            "skipping malformed grade record (not a dict) from %s: %r",
            source, record,
        )
        return False

    for field, expected in _REQUIRED_FIELDS.items():
        if field not in record:
            logger.warning(
                "skipping grade record from %s: missing required field %r "
                "(reaction_id=%r)",
                source, field, record.get("reaction_id", "?"),
            )
            return False
        value = record[field]
        # Strict bool — bool is a subclass of int so we check it first.
        if expected is bool:
            if not isinstance(value, bool):
                logger.warning(
                    "skipping grade record from %s: field %r must be bool, "
                    "got %s (reaction_id=%r)",
                    source, field, type(value).__name__,
                    record.get("reaction_id", "?"),
                )
                return False
            continue
        if expected is int:
            # Reject bool-as-int (True == 1 would otherwise pass).
            if isinstance(value, bool) or not isinstance(value, int):
                logger.warning(
                    "skipping grade record from %s: field %r must be int, "
                    "got %s (reaction_id=%r)",
                    source, field, type(value).__name__,
                    record.get("reaction_id", "?"),
                )
                return False
            continue
        if expected is str:
            if not isinstance(value, str):
                logger.warning(
                    "skipping grade record from %s: field %r must be str, "
                    "got %s (reaction_id=%r)",
                    source, field, type(value).__name__,
                    record.get("reaction_id", "?"),
                )
                return False
            continue
        # Fallback isinstance — keeps the dispatch general if the schema
        # later picks up a non-str/int/bool type.
        if not isinstance(value, expected):  # type: ignore[arg-type]
            logger.warning(
                "skipping grade record from %s: field %r failed isinstance "
                "check (reaction_id=%r)",
                source, field, record.get("reaction_id", "?"),
            )
            return False

    score = record["score"]
    if not (1 <= score <= 5):
        logger.warning(
            "skipping grade record from %s: score %r out of range 1..5 "
            "(reaction_id=%r)",
            source, score, record.get("reaction_id", "?"),
        )
        return False

    flag = record["slop_flag"]
    if flag not in SLOP_FLAGS:
        logger.warning(
            "skipping grade record from %s: slop_flag %r not in %r "
            "(reaction_id=%r)",
            source, flag, SLOP_FLAGS, record.get("reaction_id", "?"),
        )
        return False

    return True


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def load_all_grades(grades_dir: Path) -> tuple[list[dict], list[str]]:
    """Walk ``grades_dir`` for ``*.jsonl`` (excluding ``grades.key.json``).

    Parses each line, validates against the locked schema. Malformed lines
    are logged at WARNING and skipped. Returns ``(records, raters_present)``
    where ``raters_present`` is the alphabetically-sorted list of rater
    names derived from the JSONL filenames whose files have at least one
    *valid* record.

    Missing dir → ``([], [])``.
    """
    if not grades_dir.exists() or not grades_dir.is_dir():
        return ([], [])

    raters_present: set[str] = set()
    records: list[dict] = []
    for path in sorted(grades_dir.glob("*.jsonl")):
        rater = path.stem
        rater_has_valid = False
        try:
            with path.open(encoding="utf-8") as f:
                for lineno, line in enumerate(f, 1):
                    s = line.strip()
                    if not s:
                        continue
                    try:
                        rec = json.loads(s)
                    except json.JSONDecodeError as e:
                        logger.warning(
                            "skipping malformed JSONL line %s:%d: %s",
                            path, lineno, e,
                        )
                        continue
                    source = f"{path.name}:{lineno}"
                    if not validate_record(rec, source=source):
                        continue
                    records.append(rec)
                    rater_has_valid = True
        except OSError as e:
            logger.warning("could not read %s: %s", path, e)
            continue
        if rater_has_valid:
            raters_present.add(rater)

    return (records, sorted(raters_present))


def load_grades_key(grades_dir: Path) -> dict[str, dict]:
    """Read ``grades.key.json`` and return the ``reaction_id → {text, t}``
    mapping. Returns ``{}`` on missing file / JSON decode error (the report
    still renders; reaction_text in CSV / 1-2 enumeration shows empty for
    any reaction_id not in the key — UX degradation, not a crash).
    """
    key_path = grades_dir / "grades.key.json"
    if not key_path.exists():
        return {}
    try:
        data = json.loads(key_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("could not load grades.key.json: %s", e)
        return {}
    if not isinstance(data, dict):
        logger.warning(
            "grades.key.json is not a JSON object (got %s) — ignoring",
            type(data).__name__,
        )
        return {}
    # Only keep dict-valued entries — defensive.
    out: dict[str, dict] = {}
    for rid, entry in data.items():
        if isinstance(rid, str) and isinstance(entry, dict):
            out[rid] = entry
    return out


# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------


def compute_verdict(
    records: list[dict],
    raters_present: list[str],
    *,
    expected_raters: int = EXPECTED_RATERS,
) -> tuple[str, dict]:
    """Compute the rubric verdict against ``records``.

    Returns ``(verdict_string, metrics_dict)``. ``metrics_dict`` carries
    everything build_report_md / build_scores_csv need to render output:

      * ``total_records``         — int
      * ``total_reactions``       — int (distinct reaction_ids)
      * ``raters_present``        — list[str] (sorted)
      * ``raters_expected``       — int (EXPECTED_RATERS or override)
      * ``average_score``         — float | None
      * ``score_counts``          — dict[int, int] for scores 1..5
      * ``per_rater``             — dict[str, {graded, average, low_count}]
      * ``per_reaction_graders``  — dict[reaction_id, set[rater]]
      * ``incomplete_raters``     — list[str] of raters who skipped reactions
      * ``low_records``           — list[dict] (score in {1, 2})
      * ``three_pct``             — float (count(3) / total_records)
      * ``in_tie_band``           — bool
    """
    metrics: dict = {
        "total_records": len(records),
        "total_reactions": 0,
        "raters_present": list(raters_present),
        "raters_expected": expected_raters,
        "average_score": None,
        "score_counts": {i: 0 for i in range(1, 6)},
        "per_rater": {},
        "per_reaction_graders": {},
        "incomplete_raters": [],
        "low_records": [],
        "three_pct": 0.0,
        "in_tie_band": False,
    }

    # No records → INCOMPLETE.
    if not records:
        return (VERDICT_INCOMPLETE, metrics)

    # Aggregate.
    scores: list[int] = []
    per_rater_scores: dict[str, list[int]] = {r: [] for r in raters_present}
    per_reaction_graders: dict[str, set[str]] = {}
    low_records: list[dict] = []
    score_counts = {i: 0 for i in range(1, 6)}

    for rec in records:
        s = int(rec["score"])
        scores.append(s)
        score_counts[s] = score_counts.get(s, 0) + 1
        rater = rec["rater"]
        per_rater_scores.setdefault(rater, []).append(s)
        rid = rec["reaction_id"]
        per_reaction_graders.setdefault(rid, set()).add(rater)
        if s <= 2:
            low_records.append(rec)

    metrics["total_reactions"] = len(per_reaction_graders)
    metrics["score_counts"] = score_counts
    metrics["per_reaction_graders"] = per_reaction_graders
    metrics["low_records"] = low_records

    avg = statistics.fmean(scores) if scores else 0.0
    metrics["average_score"] = avg

    # Per-rater breakdown.
    per_rater: dict[str, dict] = {}
    for rater, rscores in per_rater_scores.items():
        if not rscores:
            continue
        per_rater[rater] = {
            "graded": len(rscores),
            "average": statistics.fmean(rscores),
            "low_count": sum(1 for s in rscores if s <= 2),
        }
    metrics["per_rater"] = per_rater

    # Check completeness: every rater_present graded every reaction.
    incomplete: list[str] = []
    expected_reactions = set(per_reaction_graders.keys())
    for rater in raters_present:
        graded_reactions = {
            rid for rid, graders in per_reaction_graders.items() if rater in graders
        }
        if graded_reactions != expected_reactions:
            incomplete.append(rater)
    metrics["incomplete_raters"] = incomplete

    # Tie-breaker band membership + 3-score share.
    three_pct = score_counts.get(3, 0) / len(records) if records else 0.0
    metrics["three_pct"] = three_pct
    in_band = (
        (PASS_AVG_THRESHOLD - TIE_BREAKER_BAND)
        <= avg
        <= (PASS_AVG_THRESHOLD + TIE_BREAKER_BAND)
    )
    metrics["in_tie_band"] = in_band

    # ---- Verdict resolution ----
    # INCOMPLETE wins over PASS/FAIL when roster or per-reaction coverage
    # is short.
    if len(raters_present) < expected_raters:
        return (VERDICT_INCOMPLETE, metrics)
    if incomplete:
        return (VERDICT_INCOMPLETE, metrics)

    low_count = score_counts.get(1, 0) + score_counts.get(2, 0)
    if avg < PASS_AVG_THRESHOLD or low_count > 0:
        return (VERDICT_FAIL, metrics)

    # Would-be PASS — check tie-breaker.
    if in_band and three_pct > TIE_BREAKER_THREE_PCT:
        return (VERDICT_TIE_BREAKER, metrics)

    return (VERDICT_PASS, metrics)


def enumerate_low_scores(
    records: list[dict], key: dict[str, dict]
) -> list[dict]:
    """Filter records with score in {1, 2}, join with ``key`` to attach
    ``reaction_text``. Returns a list of new dicts sorted by
    ``(score asc, rater asc, reaction_id asc)`` for deterministic report
    output.
    """
    out: list[dict] = []
    for rec in records:
        if int(rec["score"]) > 2:
            continue
        merged = dict(rec)
        entry = key.get(rec["reaction_id"]) or {}
        merged["reaction_text"] = entry.get("text", "")
        out.append(merged)
    out.sort(key=lambda r: (int(r["score"]), str(r["rater"]), str(r["reaction_id"])))
    return out


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _iso_now(now: Optional[datetime] = None) -> str:
    """ISO-8601 timestamp string for the report header. Injected ``now``
    keeps tests deterministic; production passes None and uses UTC now."""
    if now is None:
        now = datetime.now(timezone.utc)
    return now.replace(microsecond=0).isoformat()


def _score_histogram(score_counts: dict[int, int]) -> str:
    """Render a tiny ASCII bar chart for the 1-5 distribution. Each bar is
    a string of ``#`` proportional to count, scaled so the tallest bar
    is at most 40 chars."""
    max_count = max(score_counts.values()) if score_counts else 0
    if max_count == 0:
        return "  (no scores)"
    width = 40
    lines: list[str] = []
    for s in (5, 4, 3, 2, 1):
        n = score_counts.get(s, 0)
        bar_len = int(round((n / max_count) * width))
        bar = "#" * bar_len
        lines.append(f"  {s}: {bar:<{width}}  ({n})")
    return "\n".join(lines)


def build_report_md(
    verdict: str,
    metrics: dict,
    *,
    records: list[dict],
    key: dict[str, dict],
    session_dir_name: str,
    now: Optional[datetime] = None,
) -> str:
    """Render the analyzer report. Pure function: same inputs → identical
    output when ``now`` is injected (used by tests for determinism)."""
    ts = _iso_now(now)
    avg = metrics.get("average_score")
    avg_str = f"{avg:.2f}" if isinstance(avg, (int, float)) else "—"
    total_records = metrics.get("total_records", 0)
    total_reactions = metrics.get("total_reactions", 0)
    raters_present = metrics.get("raters_present", []) or []
    raters_expected = metrics.get("raters_expected", EXPECTED_RATERS)
    sc = metrics.get("score_counts", {i: 0 for i in range(1, 6)})
    per_rater = metrics.get("per_rater", {})
    incomplete = metrics.get("incomplete_raters", []) or []

    lines: list[str] = [
        "# Phase 17 Reaction Reel — Analysis Report",
        "",
        f"**Session:** {session_dir_name}",
        f"**Generated:** {ts}",
        f"**Verdict:** {verdict}",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total reactions | {total_reactions} |",
        f"| Total records | {total_records} |",
        f"| Raters present | {', '.join(raters_present) if raters_present else '—'} |",
        f"| Raters expected | {raters_expected} |",
        f"| Average score | {avg_str} |",
        f"| Score 1 count | {sc.get(1, 0)} |",
        f"| Score 2 count | {sc.get(2, 0)} |",
        f"| Score 3 count | {sc.get(3, 0)} |",
        f"| Score 4 count | {sc.get(4, 0)} |",
        f"| Score 5 count | {sc.get(5, 0)} |",
        "",
        "## Per-rater breakdown",
        "",
        "| Rater | Reactions graded | Average | 1-2 count |",
        "|-------|------------------|---------|-----------|",
    ]
    if per_rater:
        # Stable rater order — alphabetic.
        for rater in sorted(per_rater.keys()):
            entry = per_rater[rater]
            lines.append(
                f"| {rater} | {entry['graded']} | "
                f"{entry['average']:.2f} | {entry['low_count']} |"
            )
    else:
        lines.append("| — | — | — | — |")

    # Incomplete raters callout — only when relevant.
    if incomplete:
        lines += [
            "",
            "### Incomplete raters",
            "",
            "The following raters present a JSONL but did not grade every "
            "reaction; verdict is INCOMPLETE:",
            "",
        ]
        for rater in incomplete:
            lines.append(f"- {rater}")

    # 1-2 enumeration — verdict-impacting gate.
    low_records = metrics.get("low_records", []) or []
    lines += [
        "",
        "## All 1-2 ratings (gate-blocking)",
        "",
    ]
    if low_records:
        lines += [
            "| Reaction ID | Rater | Score | slop_flag | Comment | Reaction text |",
            "|-------------|-------|-------|-----------|---------|---------------|",
        ]
        for rec in enumerate_low_scores(low_records, key):
            rid = rec["reaction_id"]
            rater = rec["rater"]
            score = rec["score"]
            slop_flag = rec.get("slop_flag", "")
            comment = (rec.get("comment") or "").replace("|", "\\|")
            rxn_text = (rec.get("reaction_text") or "").replace("|", "\\|")
            lines.append(
                f"| {rid} | {rater} | {score} | {slop_flag} | "
                f"{comment} | {rxn_text} |"
            )
    else:
        lines.append("_No 1-2 ratings — gate not blocked on this axis._")

    # Score distribution histogram.
    lines += [
        "",
        "## Score distribution",
        "",
        "```",
        _score_histogram(sc),
        "```",
    ]

    # Iteration guidance.
    lines += [
        "",
        "## Iteration guidance",
        "",
    ]
    if verdict == VERDICT_PASS:
        lines.append("No iteration needed — verdict is PASS.")
    elif verdict == VERDICT_INCOMPLETE:
        lines.append(
            "Verdict is INCOMPLETE — collect missing rater grades and re-run "
            "the analyzer. No Phase 10 re-entry triggered yet."
        )
    else:
        # FAIL or PASS_TIE_BREAKER_NEEDED — same iteration-guidance shape.
        worst_rater = None
        if per_rater:
            worst_rater = min(per_rater.items(), key=lambda kv: kv[1]["average"])
        lines.append(
            "Per `.planning/phases/17-reaction-reel-slop-grading-gate/"
            "17-ITERATION-LOOP.md`, the next step depends on the verdict:"
        )
        lines.append("")
        if verdict == VERDICT_FAIL:
            lines.append(
                "- **FAIL** → re-enter Phase 10 (prompt template matrix) for "
                "another iteration cycle (3-cycle budget)."
            )
        else:
            lines.append(
                "- **PASS_TIE_BREAKER_NEEDED** → escalate to Kaan for a "
                "ship-vs-one-more-Phase-10-cycle decision. The math passes; "
                "the texture may not (≥25% 3-scores)."
            )
        if worst_rater is not None:
            wr_name, wr_entry = worst_rater
            lines.append(
                f"- Lowest-average rater: **{wr_name}** "
                f"(avg {wr_entry['average']:.2f}). Focus iteration on "
                f"reactions they scored ≤3."
            )
        # Top 5 worst reactions by per-reaction average across raters.
        per_reaction_scores: dict[str, list[int]] = {}
        for rec in records:
            per_reaction_scores.setdefault(rec["reaction_id"], []).append(
                int(rec["score"])
            )
        worst = sorted(
            per_reaction_scores.items(),
            key=lambda kv: (statistics.fmean(kv[1]), kv[0]),
        )[:5]
        if worst:
            lines.append("")
            lines.append("### Worst-performing reactions (lowest avg)")
            lines.append("")
            lines.append("| Reaction ID | Avg | Raters | Reaction text |")
            lines.append("|-------------|-----|--------|---------------|")
            for rid, rs in worst:
                rxn_text = (key.get(rid) or {}).get("text", "") or ""
                rxn_text = rxn_text.replace("|", "\\|")
                lines.append(
                    f"| {rid} | {statistics.fmean(rs):.2f} | "
                    f"{len(rs)} | {rxn_text} |"
                )

    # Methodology — pins the rubric reference verbatim.
    lines += [
        "",
        "## Methodology",
        "",
        f"Pass requires average score ≥ {PASS_AVG_THRESHOLD:.1f} across all "
        "(reactions × raters) AND zero 1-2 ratings, per "
        "`.planning/phases/17-reaction-reel-slop-grading-gate/17-RUBRIC.md`. "
        f"Tie-breaker triggers when average is in "
        f"[{PASS_AVG_THRESHOLD - TIE_BREAKER_BAND:.2f}, "
        f"{PASS_AVG_THRESHOLD + TIE_BREAKER_BAND:.2f}] AND more than "
        f"{int(TIE_BREAKER_THREE_PCT * 100)}% of records are score 3.",
        "",
    ]
    return "\n".join(lines)


def build_scores_csv(
    records: list[dict], key: dict[str, dict]
) -> str:
    """Render the flat (reaction × rater) CSV. Joins reaction_text from
    the ``key`` map; missing entries get an empty string for reaction_text.
    """
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(_CSV_COLUMNS))
    writer.writeheader()
    for rec in records:
        row = {col: "" for col in _CSV_COLUMNS}
        for col in _CSV_COLUMNS:
            if col == "reaction_text":
                entry = key.get(rec["reaction_id"]) or {}
                row[col] = entry.get("text", "") or ""
            elif col in rec:
                row[col] = rec[col]
        writer.writerow(row)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Atomic file writes — tmp + os.replace (mirror grade.py's append fsync,
# adapted for full-file rewrite).
# ---------------------------------------------------------------------------


def _atomic_write_text(path: Path, content: str) -> None:
    """Write ``content`` to ``path`` atomically: tmp + ``os.replace``.

    The tmp file is created in the same directory (so the replace is
    rename-on-same-filesystem). A mid-write OSError raised by ``os.replace``
    leaves the previous file at ``path`` intact (the tmp file is cleaned
    up best-effort, but the destination is never half-written).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=str(path.parent),
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            try:
                os.fsync(f.fileno())
            except (OSError, AttributeError):
                # tmpfs / network FS — best-effort.
                pass
        os.replace(tmp_path, path)
    except BaseException:
        # On any failure, leave the previous ``path`` (if any) intact and
        # clean up the tmp file.
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Top-level orchestration
# ---------------------------------------------------------------------------


def analyze_session(
    session_dir: Path,
    output_dir: Optional[Path] = None,
    *,
    now: Optional[datetime] = None,
    quiet: bool = False,
) -> int:
    """Aggregate grades, write report.md + scores.csv, return the exit code.

    ``output_dir`` defaults to ``session_dir / "grades"``. When the
    grades dir does not exist, the verdict is INCOMPLETE and the exit
    code is :data:`EXIT_INCOMPLETE` — we still attempt to write report.md
    + scores.csv with empty content so the operator sees a verdict file.
    """
    session_dir = Path(session_dir)
    grades_dir = session_dir / "grades"
    out_dir = Path(output_dir) if output_dir is not None else grades_dir

    records, raters_present = load_all_grades(grades_dir)
    key = load_grades_key(grades_dir)
    verdict, metrics = compute_verdict(records, raters_present)

    report_md = build_report_md(
        verdict, metrics,
        records=records, key=key,
        session_dir_name=session_dir.name,
        now=now,
    )
    scores_csv = build_scores_csv(records, key)

    out_dir.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(out_dir / "report.md", report_md)
    _atomic_write_text(out_dir / "scores.csv", scores_csv)

    if not quiet:
        avg = metrics.get("average_score")
        avg_str = f"{avg:.2f}" if isinstance(avg, (int, float)) else "—"
        low_count = (
            metrics.get("score_counts", {}).get(1, 0)
            + metrics.get("score_counts", {}).get(2, 0)
        )
        banner = (
            "=====================================================\n"
            " Phase 17 Slop Grading Analysis\n"
            f" Session: {session_dir.name}\n"
            f" Verdict: {verdict}\n"
            "=====================================================\n"
            f"Total reactions: {metrics.get('total_reactions', 0)}\n"
            f"Raters present: {', '.join(raters_present) if raters_present else '—'}\n"
            f"Average score: {avg_str}\n"
            f"Low scores (1-2): {low_count}\n"
            f"Report written: {out_dir / 'report.md'}\n"
            f"Scores CSV written: {out_dir / 'scores.csv'}\n"
        )
        sys.stdout.write(banner)
        sys.stdout.flush()

    return _VERDICT_TO_EXIT[verdict]


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------


def _setup_cli_logging() -> None:
    """Stream WARNING+ to stderr so the operator sees malformed-record
    callouts even with -q (the banner is silenced, the logs are not)."""
    if logger.handlers:
        return
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(logging.WARNING)
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.WARNING)


def main(argv: Optional[list[str]] = None) -> int:
    """Argparse wrapper. Returns the exit code from :func:`analyze_session`."""
    parser = argparse.ArgumentParser(
        prog="python -m scripts.reaction_reel.analyze",
        description="Aggregate Phase 17 reaction-reel grades into a pass/fail "
                    "verdict + report.md + scores.csv.",
    )
    parser.add_argument(
        "session_dir",
        type=Path,
        help="Path to the recording session dir "
             "(must contain grades/<rater>.jsonl files).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Override output dir (default: <session_dir>/grades/).",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress the stdout banner. Files are still written; WARNING "
             "logs still go to stderr.",
    )
    args = parser.parse_args(argv)

    _setup_cli_logging()

    session_dir: Path = args.session_dir.resolve()
    if not session_dir.exists() or not session_dir.is_dir():
        print(
            f"error: session_dir does not exist: {session_dir}",
            file=sys.stderr,
        )
        return 1

    return analyze_session(
        session_dir,
        output_dir=args.output_dir,
        quiet=args.quiet,
    )


if __name__ == "__main__":
    raise SystemExit(main())
