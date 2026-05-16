# SPDX-License-Identifier: Apache-2.0
"""Phase 42 Plan 02 — threshold recalibration driver + ±0.10 tolerance band.

Per CONTEXT D-GATE-04 and the Phase 27 re-tuning protocol:

- This script READS ``eval/THRESHOLD-LOCK.md`` and MEASURES the locked
  thresholds against the real corpus at ``eval/corpus/sessions/`` via the
  existing 2-judge replay harness.
- When the measured F1 / substance / cited-cosine / bypass are within ±0.10
  of the locked values, the script appends an in-tolerance audit entry to
  ``eval/THRESHOLD-RECALIBRATION-LOG.md`` and exits ``0``.
- When the measured values fall outside the ±0.10 band, the script
  appends an out-of-tolerance audit entry and exits ``1`` with a
  structured ``RECALIBRATION_REQUIRED`` stderr line.
- The script **NEVER** auto-edits ``eval/THRESHOLD-LOCK.md``. Autonomous
  re-signing of the lock is FORBIDDEN by the Phase 27-04 re-tuning
  protocol. Re-locking is a deliberate human action.

Two operational modes:

``(default — full recalibration)``
    Walks the corpus, invokes the replay harness, parses ``eval_report.json``,
    appends an audit entry, returns the exit code dictated by the tolerance
    band. This is the slow lane — it calls real Gemini judges and costs
    money; it's intended for nightly canary + manual operator runs.

``--check-only``
    Skips the replay harness entirely (no Gemini calls). Verifies only:

      (i)  ``eval/corpus/sessions/`` carries ≥6 sessions whose ``input.wav``
           exists (placeholder dirs with only ``genre.txt`` do NOT count).
      (ii) ``eval/THRESHOLD-RECALIBRATION-LOG.md`` carries at least one
           ``### YYYY-MM-DDTHH:MM:SSZ — verdict=…`` entry timestamped within
           the last 30 days.

    Exit ``0`` iff both invariants hold. Exit ``1`` on either failure with
    a structured stderr reason. This is the fast lane — the CI workflow
    runs this against every nightly schedule + manual dispatch.

Public surface (the test suite pins this contract — keep stable):
    - ``main(argv: list[str] | None = None) -> int``
    - ``measure_against_corpus(corpus_dir, judges, *, threshold_lock, output_dir) -> dict``
    - ``compute_delta(measured: float, locked: float) -> tuple[float, str]``
    - ``RECALIBRATION_TOLERANCE: float = 0.10``
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# ----------------------------------------------------------------------
# Constants — exported in the must_haves contract (`exports`).
# ----------------------------------------------------------------------

#: Tolerance band, inclusive on both ends. ``|measured - locked| <=
#: RECALIBRATION_TOLERANCE`` → ``in_tolerance``; strictly outside →
#: ``out_of_tolerance``.
RECALIBRATION_TOLERANCE: float = 0.10

#: Float-representation slack for the boundary comparison. ``0.70 - 0.80``
#: yields ``-0.10000000000000009`` (8e-17 drift) on CPython 3.12 IEEE-754
#: doubles; without this epsilon the inclusive boundary contract in
#: ``test_compute_delta_on_boundary`` flips ``out_of_tolerance``.
_TOLERANCE_FLOAT_EPS: float = 1e-9

#: Path to the locked thresholds; READ-ONLY from this script. The
#: ``test_script_never_writes_to_lock_file`` test md5-pins this guarantee.
LOCK_PATH: Path = Path("eval/THRESHOLD-LOCK.md")

#: Path to the append-only audit trail. The script's only write target.
LOG_PATH: Path = Path("eval/THRESHOLD-RECALIBRATION-LOG.md")

#: Default real-corpus root.
DEFAULT_CORPUS: Path = Path("eval/corpus/sessions")

#: Minimum populated session count for the ``--check-only`` corpus-size gate.
#: Mirrors the GATE-03 6×30-min discharge target.
MIN_REAL_CORPUS_SESSIONS: int = 6

#: Audit-log freshness window for ``--check-only`` mode. An entry within
#: the last 30 days satisfies the freshness gate.
LOG_FRESHNESS_DAYS: int = 30

#: Regex that matches an audit entry header line. Used by ``_latest_audit_entry_at``.
_AUDIT_HEADER_RE = re.compile(
    r"^###\s+(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\s+—\s+verdict=([a-z_]+)"
)

#: Markdown ``responses/*.txt`` content fields that ``measure_against_corpus``
#: explicitly does NOT consume — present as a documentation marker for the
#: T-42-02-03 mitigation (we only consume numeric metric fields).
_FORBIDDEN_REPORT_FIELDS = frozenset({"response", "response_text", "transcript"})


# ----------------------------------------------------------------------
# Tolerance-band math (the load-bearing invariant).
# ----------------------------------------------------------------------


def compute_delta(measured: float, locked: float) -> tuple[float, str]:
    """Return ``(delta, verdict)`` for a single metric.

    ``delta = measured - locked``. Verdict is ``"in_tolerance"`` iff
    ``abs(delta) <= RECALIBRATION_TOLERANCE`` (inclusive on the boundary,
    per the plan's ``test_compute_delta_on_boundary`` contract).
    """
    delta = float(measured) - float(locked)
    verdict = (
        "in_tolerance"
        if abs(delta) <= RECALIBRATION_TOLERANCE + _TOLERANCE_FLOAT_EPS
        else "out_of_tolerance"
    )
    return delta, verdict


def aggregate_verdict(deltas: dict[str, tuple[float, str]]) -> str:
    """Reduce per-metric verdicts to a single corpus-level verdict.

    Any single metric falling outside the band promotes the aggregate to
    ``out_of_tolerance`` (the band is conjunctive — every locked metric
    must hold). Empty dict → ``out_of_tolerance`` (no measurements ⇒ we
    cannot affirm the lock).
    """
    if not deltas:
        return "out_of_tolerance"
    for _delta, verdict in deltas.values():
        if verdict == "out_of_tolerance":
            return "out_of_tolerance"
    return "in_tolerance"


# ----------------------------------------------------------------------
# Replay-harness invocation + eval_report.json parsing.
# ----------------------------------------------------------------------


def measure_against_corpus(
    corpus_dir: Path,
    judges: str,
    *,
    threshold_lock: Path | None = None,
    output_dir: Path | None = None,
    runner: "callable | None" = None,
) -> dict[str, Any]:
    """Drive the 2-judge replay harness against the real corpus.

    Parameters
    ----------
    corpus_dir
        Directory of session subdirs (each with ``input.wav`` etc.).
    judges
        Comma-joined judge backends; passed straight to
        ``replay_harness --judges``.
    threshold_lock
        Optional path to ``THRESHOLD-LOCK.md`` (forwarded to the harness so
        ``threshold_pass`` flags use the locked values).
    output_dir
        Where the harness writes ``eval_report.json`` + ``scorecard.md``.
        If ``None``, allocates a fresh temporary directory.
    runner
        Optional injected callable ``(argv: list[str]) -> int`` used by the
        test suite to stub out the real subprocess. When ``None``, the real
        ``subprocess.run`` is used (process isolation, T-42-02-03).

    Returns
    -------
    dict
        ``{
            "aggregate": {"f1": float, "substance": float,
                          "cited_cosine": float, "bypass": float},
            "per_session": [ {session, genre, f1, substance,
                              cited_cosine, bypass, verdict}, ... ],
            "per_genre": { genre: {"f1": float, "count": int}, ... },
            "session_count": int,
            "genre_count": int,
            "eval_report_path": Path,
        }``

    Raises
    ------
    RuntimeError
        If the harness exits with a code other than 0 / 1 (i.e. an
        unexpected fault — exit 1 is the harness's normal way of
        flagging a sub-threshold session and is recoverable here).
    FileNotFoundError
        If the harness did not produce ``eval_report.json``.
    """
    corpus_dir = Path(corpus_dir)
    own_tmp = False
    if output_dir is None:
        tmp = tempfile.mkdtemp(prefix="vibemix-recalibrate-")
        output_dir = Path(tmp)
        own_tmp = True
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    argv = [
        sys.executable,
        "-m",
        "scripts.eval.replay_harness",
        "--corpus",
        str(corpus_dir),
        "--judges",
        judges,
        "--output",
        str(output_dir),
    ]
    if threshold_lock is not None:
        argv += ["--threshold-lock", str(threshold_lock)]

    if runner is not None:
        rc = runner(argv)
    else:
        # subprocess isolation — judge failures should not crash the
        # recalibration script's parser.
        result = subprocess.run(argv, capture_output=True, text=True)
        rc = result.returncode
        if rc not in (0, 1):
            raise RuntimeError(
                f"replay_harness exited with unexpected code {rc}: "
                f"{result.stderr.strip()[:500]}"
            )

    report_path = output_dir / "eval_report.json"
    if not report_path.exists():
        raise FileNotFoundError(
            f"replay_harness produced no eval_report.json at {report_path}"
        )

    parsed = _parse_eval_report(report_path)
    parsed["eval_report_path"] = report_path
    parsed["replay_harness_exit"] = rc
    parsed["_own_tmp"] = own_tmp
    return parsed


def _parse_eval_report(report_path: Path) -> dict[str, Any]:
    """Pull aggregate + per-session + per-genre metrics from eval_report.json.

    Only numeric metric fields are consumed (T-42-02-03 mitigation —
    ``responses/<event>.txt`` content is NOT touched by this parser).
    """
    data = json.loads(report_path.read_text(encoding="utf-8"))
    sessions = data.get("sessions") or []

    per_session: list[dict[str, Any]] = []
    per_genre: dict[str, dict[str, Any]] = {}
    sums = {"f1": 0.0, "substance": 0.0, "cited_cosine": 0.0, "bypass": 0.0}
    count = 0

    for sess in sessions:
        # Defensive: forbidden response-text fields must not leak.
        for forbidden in _FORBIDDEN_REPORT_FIELDS:
            sess.pop(forbidden, None)

        sid = sess.get("session", "?")
        genre = sess.get("genre", "unknown")
        f1 = float(sess.get("f1", 0.0))
        substance = float(sess.get("substance", 0.0))
        cited_cosine = float(sess.get("cited_cosine", 0.0))
        bypass = float(sess.get("bypass", 0.0))
        verdict = sess.get("verdict", "?")

        per_session.append(
            {
                "session": sid,
                "genre": genre,
                "f1": f1,
                "substance": substance,
                "cited_cosine": cited_cosine,
                "bypass": bypass,
                "verdict": verdict,
            }
        )

        bucket = per_genre.setdefault(genre, {"f1_sum": 0.0, "count": 0})
        bucket["f1_sum"] += f1
        bucket["count"] += 1

        sums["f1"] += f1
        sums["substance"] += substance
        sums["cited_cosine"] += cited_cosine
        sums["bypass"] += bypass
        count += 1

    aggregate = (
        {k: (v / count) for k, v in sums.items()}
        if count
        else {k: 0.0 for k in sums}
    )

    per_genre_final = {
        g: {
            "f1": (b["f1_sum"] / b["count"]) if b["count"] else 0.0,
            "count": b["count"],
        }
        for g, b in per_genre.items()
    }

    return {
        "aggregate": aggregate,
        "per_session": per_session,
        "per_genre": per_genre_final,
        "session_count": count,
        "genre_count": len(per_genre_final),
    }


# ----------------------------------------------------------------------
# Locked-value loader (read-only; never writes).
# ----------------------------------------------------------------------


def load_locked_values(lock_path: Path) -> dict[str, float]:
    """Read locked thresholds via the existing Phase 27-04 parser.

    Only the four aggregate metrics flow through the tolerance band:
    ``f1_min``, ``substance_min``, ``cited_cosine_min``, ``bypass_max``.
    Per-genre F1 is reported but is not part of the four-metric delta
    table — it's a separate floor that the plan's audit log surfaces
    independently.
    """
    # Lazy import keeps the module importable even when yaml is unavailable
    # (e.g. minimal CI envs running unit tests that monkeypatch this loader).
    from scripts.eval.threshold_lock import (
        DEFAULT_THRESHOLDS,
        parse_threshold_lock_frontmatter,
    )

    try:
        parsed = parse_threshold_lock_frontmatter(lock_path)
    except FileNotFoundError:
        return dict(DEFAULT_THRESHOLDS)
    thresholds = parsed.get("thresholds") or {}
    if not isinstance(thresholds, dict) or not thresholds:
        return dict(DEFAULT_THRESHOLDS)
    out = dict(DEFAULT_THRESHOLDS)
    out.update({k: float(v) for k, v in thresholds.items()})
    return out


# ----------------------------------------------------------------------
# Audit-log writer (append-only).
# ----------------------------------------------------------------------


def format_audit_entry(
    measured: dict[str, Any],
    locked: dict[str, float],
    *,
    timestamp: str,
    judges: str,
    corpus_dir: Path,
    verdict: str,
    deltas: dict[str, tuple[float, str]],
) -> str:
    """Produce a markdown audit-entry block matching the plan's schema.

    Block shape (header ``###`` + bullet lines). The block ends with a
    single trailing blank line so successive appends remain readable.
    """
    agg = measured.get("aggregate", {})
    per_genre = measured.get("per_genre", {})
    session_count = measured.get("session_count", 0)
    genre_count = measured.get("genre_count", 0)

    f1_d, _ = deltas.get("f1", (0.0, "in_tolerance"))
    sub_d, _ = deltas.get("substance", (0.0, "in_tolerance"))
    cc_d, _ = deltas.get("cited_cosine", (0.0, "in_tolerance"))
    by_d, _ = deltas.get("bypass", (0.0, "in_tolerance"))

    per_genre_str = (
        "  ".join(
            f"{g} f1={info['f1']:.2f}"
            for g, info in sorted(per_genre.items())
        )
        if per_genre
        else "(no genres measured)"
    )

    action = (
        "none"
        if verdict == "in_tolerance"
        else "RECALIBRATION_REQUIRED — re-sign THRESHOLD-LOCK.md after re-run"
    )

    return (
        f"### {timestamp} — verdict={verdict}\n"
        f"- corpus: {corpus_dir} ({session_count} sessions, {genre_count} genres)\n"
        f"- judges: {judges}\n"
        f"- measured: f1={agg.get('f1', 0.0):.2f}  "
        f"substance={agg.get('substance', 0.0):.2f}  "
        f"cited_cosine={agg.get('cited_cosine', 0.0):.2f}  "
        f"bypass={agg.get('bypass', 0.0):.2f}\n"
        f"- locked:   f1={locked.get('f1_min', 0.0):.2f}  "
        f"substance={locked.get('substance_min', 0.0):.2f}  "
        f"cited_cosine={locked.get('cited_cosine_min', 0.0):.2f}  "
        f"bypass={locked.get('bypass_max', 0.0):.2f}\n"
        f"- delta:    f1={f1_d:+.2f} substance={sub_d:+.2f} "
        f"cited_cosine={cc_d:+.2f} bypass={by_d:+.2f}\n"
        f"- per-genre: {per_genre_str}\n"
        f"- verdict: {verdict}\n"
        f"- action:  {action}\n"
        f"\n"
    )


def append_audit_entry(log_path: Path, entry: str) -> None:
    """Append-only writer. Never truncates, never rewrites prior entries.

    Creates a minimal seed file when the log is missing — this keeps the
    fresh-clone bootstrap path working without forcing the seed to live
    in two places.
    """
    log_path = Path(log_path)
    if not log_path.exists():
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(_seed_log_text(), encoding="utf-8")
    with log_path.open("a", encoding="utf-8") as f:
        if not entry.endswith("\n"):
            entry += "\n"
        f.write(entry)


def _seed_log_text() -> str:
    """Minimal seed content when the audit log is missing on disk."""
    return (
        "# vibemix Threshold Recalibration Audit Trail\n\n"
        "Append-only log of every `recalibrate_thresholds.py` run.\n\n"
        "## Audit Trail\n\n"
    )


def _latest_audit_entry_at(log_path: Path) -> datetime | None:
    """Return the most recent audit-entry timestamp (UTC) or None.

    Walks ``log_path`` line-by-line, matches the ``### YYYY-...Z — verdict=…``
    header regex, parses the ISO8601 stamp. The seed schema example
    (``verdict=schema_example``) is treated as a real entry only when its
    timestamp is parseable — the seed file ships with a placeholder
    timestamp that's deliberately old (1970-...) so it never satisfies the
    30-day freshness gate alone.
    """
    if not log_path.exists():
        return None
    latest: datetime | None = None
    for line in log_path.read_text(encoding="utf-8").splitlines():
        m = _AUDIT_HEADER_RE.match(line)
        if not m:
            continue
        ts_str = m.group(1)
        try:
            ts = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            continue
        verdict = m.group(2)
        if verdict == "schema_example":
            # The seed placeholder NEVER satisfies the freshness gate;
            # it's documentation, not data.
            continue
        if latest is None or ts > latest:
            latest = ts
    return latest


# ----------------------------------------------------------------------
# --check-only mode (no replay-harness invocation).
# ----------------------------------------------------------------------


def _count_real_sessions(corpus_dir: Path) -> int:
    """Count session subdirs that carry an ``input.wav``.

    Placeholder dirs (only ``genre.txt`` / ``source.txt``) do not count.
    """
    if not corpus_dir.exists():
        return 0
    return sum(1 for p in corpus_dir.glob("*/input.wav") if p.is_file())


def _run_check_only(
    corpus_dir: Path,
    log_path: Path,
    *,
    now: datetime | None = None,
) -> int:
    """Implement the CI ``--check-only`` mode. Returns process exit code.

    Exits 1 with a structured stderr message on:
      - corpus has fewer than 6 sessions with input.wav
      - audit log has no entry within the last 30 days
    """
    now = now or datetime.now(timezone.utc)
    real = _count_real_sessions(corpus_dir)
    if real < MIN_REAL_CORPUS_SESSIONS:
        print(
            f"CHECK_REAL_CORPUS_FAILED: fewer than {MIN_REAL_CORPUS_SESSIONS} "
            f"sessions in {corpus_dir} (found {real}). "
            f"See KAAN-ACTION-LEGAL.md §GATE-03 for discharge.",
            file=sys.stderr,
        )
        return 1

    latest = _latest_audit_entry_at(log_path)
    if latest is None:
        print(
            f"CHECK_REAL_CORPUS_FAILED: no recalibration log entry in "
            f"last {LOG_FRESHNESS_DAYS} days — log empty or stale "
            f"({log_path}).",
            file=sys.stderr,
        )
        return 1

    age = now - latest
    if age > timedelta(days=LOG_FRESHNESS_DAYS):
        print(
            f"CHECK_REAL_CORPUS_FAILED: stale recalibration log — latest "
            f"entry {latest.isoformat()} is {age.days}d old (limit "
            f"{LOG_FRESHNESS_DAYS}d). "
            f"Run `python -m scripts.eval.recalibrate_thresholds` "
            f"against the real corpus.",
            file=sys.stderr,
        )
        return 1

    print(
        f"CHECK_REAL_CORPUS_OK: {real} populated sessions in {corpus_dir}; "
        f"latest audit entry {latest.isoformat()} ({age.days}d ago).",
    )
    return 0


# ----------------------------------------------------------------------
# Full-recalibration mode (replay-harness driven).
# ----------------------------------------------------------------------


def _run_recalibration(
    corpus_dir: Path,
    judges: str,
    lock_path: Path,
    log_path: Path,
    *,
    dry_run: bool,
    runner: "callable | None" = None,
    now: datetime | None = None,
) -> int:
    """Implement the full recalibration path. Returns process exit code."""
    real = _count_real_sessions(corpus_dir)
    if real < MIN_REAL_CORPUS_SESSIONS:
        print(
            f"corpus too small: {real} populated sessions in {corpus_dir} "
            f"(need ≥{MIN_REAL_CORPUS_SESSIONS}). "
            f"See KAAN-ACTION-LEGAL.md §GATE-03 for discharge.",
            file=sys.stderr,
        )
        return 2

    if dry_run:
        print(
            f"--dry-run: would recalibrate {real} sessions in {corpus_dir} "
            f"with judges={judges} against {lock_path}; no harness call made.",
        )
        return 0

    try:
        measured = measure_against_corpus(
            corpus_dir,
            judges,
            threshold_lock=lock_path,
            runner=runner,
        )
    except (RuntimeError, FileNotFoundError) as exc:
        print(f"recalibration aborted: {exc}", file=sys.stderr)
        return 2

    locked = load_locked_values(lock_path)
    deltas = {
        "f1": compute_delta(measured["aggregate"]["f1"], locked["f1_min"]),
        "substance": compute_delta(
            measured["aggregate"]["substance"], locked["substance_min"]
        ),
        "cited_cosine": compute_delta(
            measured["aggregate"]["cited_cosine"], locked["cited_cosine_min"]
        ),
        "bypass": compute_delta(
            measured["aggregate"]["bypass"], locked["bypass_max"]
        ),
    }
    verdict = aggregate_verdict(deltas)
    timestamp = (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry = format_audit_entry(
        measured,
        locked,
        timestamp=timestamp,
        judges=judges,
        corpus_dir=corpus_dir,
        verdict=verdict,
        deltas=deltas,
    )
    append_audit_entry(log_path, entry)

    if verdict == "out_of_tolerance":
        print(
            "RECALIBRATION_REQUIRED: re-sign eval/THRESHOLD-LOCK.md "
            "manually after re-running both judges (autonomous re-sign "
            "is FORBIDDEN by Phase 27-04 protocol).",
            file=sys.stderr,
        )
        return 1

    print(
        f"recalibration in-tolerance: audit entry appended to {log_path} "
        f"(verdict={verdict}).",
    )
    return 0


# ----------------------------------------------------------------------
# CLI entry point.
# ----------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="scripts.eval.recalibrate_thresholds",
        description=(
            "Phase 42 Plan 02 threshold recalibration driver. "
            "Measures locked thresholds against real corpus via the "
            "2-judge replay harness. ±0.10 tolerance band — in-band "
            "appends an audit entry and exits 0; out-of-band appends "
            "an audit entry and exits 1 with RECALIBRATION_REQUIRED. "
            "NEVER auto-edits THRESHOLD-LOCK.md."
        ),
    )
    p.add_argument(
        "--corpus",
        type=Path,
        default=DEFAULT_CORPUS,
        help="Real-corpus directory (default eval/corpus/sessions).",
    )
    p.add_argument(
        "--judges",
        type=str,
        default="gemini-3-flash,gemini-3-pro",
        help="Comma-joined judge backends (forwarded to replay_harness).",
    )
    p.add_argument(
        "--lock-path",
        type=Path,
        default=LOCK_PATH,
        help="Path to eval/THRESHOLD-LOCK.md (READ-ONLY from this script).",
    )
    p.add_argument(
        "--log-path",
        type=Path,
        default=LOG_PATH,
        help="Append-only audit log path (default eval/THRESHOLD-RECALIBRATION-LOG.md).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Skip the replay harness invocation; print what would happen.",
    )
    p.add_argument(
        "--check-only",
        action="store_true",
        default=False,
        help=(
            "CI mode: do NOT invoke replay_harness. Verify only that the "
            "corpus has ≥6 populated sessions AND the audit log has an "
            "entry within the last 30 days. Exits 0 / 1 accordingly."
        ),
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.check_only:
        return _run_check_only(args.corpus, args.log_path)
    return _run_recalibration(
        args.corpus,
        args.judges,
        args.lock_path,
        args.log_path,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":  # pragma: no cover — exercised via subprocess.
    raise SystemExit(main())
