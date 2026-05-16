# SPDX-License-Identifier: Apache-2.0
"""Phase 42 Plan 02 — unit tests for `recalibrate_thresholds.py`.

Pins:
    - ±0.10 tolerance-band math (in / boundary / out).
    - Append-only audit-log invariant (3 sequential writes preserve header
      + previous entries).
    - THRESHOLD-LOCK.md never auto-mutated (md5 invariance after a full
      out-of-tolerance recalibration run).
    - `--dry-run` exits 0 cleanly for a small corpus.
    - `main(--corpus <empty>)` exits 2 (corpus too small).
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

from scripts.eval import recalibrate_thresholds as rt


# ----------------------------------------------------------------------
# compute_delta (the tolerance-band invariant).
# ----------------------------------------------------------------------


def test_compute_delta_in_tolerance() -> None:
    delta, verdict = rt.compute_delta(0.83, 0.80)
    assert pytest.approx(delta, abs=1e-9) == 0.03
    assert verdict == "in_tolerance"


def test_compute_delta_negative_in_tolerance() -> None:
    delta, verdict = rt.compute_delta(0.75, 0.80)
    assert pytest.approx(delta, abs=1e-9) == -0.05
    assert verdict == "in_tolerance"


def test_compute_delta_on_boundary() -> None:
    """|delta| == 0.10 must be classed as in_tolerance (inclusive band)."""
    delta, verdict = rt.compute_delta(0.70, 0.80)
    assert pytest.approx(delta, abs=1e-9) == -0.10
    assert verdict == "in_tolerance"

    delta, verdict = rt.compute_delta(0.90, 0.80)
    assert pytest.approx(delta, abs=1e-9) == 0.10
    assert verdict == "in_tolerance"


def test_compute_delta_outside_band() -> None:
    delta, verdict = rt.compute_delta(0.65, 0.80)
    assert pytest.approx(delta, abs=1e-9) == -0.15
    assert verdict == "out_of_tolerance"


def test_aggregate_verdict_any_outside_promotes() -> None:
    """A single metric outside the band promotes the corpus to out_of_tolerance."""
    deltas = {
        "f1": (0.02, "in_tolerance"),
        "substance": (-0.01, "in_tolerance"),
        "cited_cosine": (-0.20, "out_of_tolerance"),
        "bypass": (0.05, "in_tolerance"),
    }
    assert rt.aggregate_verdict(deltas) == "out_of_tolerance"


def test_aggregate_verdict_all_inside() -> None:
    deltas = {
        "f1": (0.02, "in_tolerance"),
        "substance": (-0.01, "in_tolerance"),
        "cited_cosine": (-0.09, "in_tolerance"),
        "bypass": (0.05, "in_tolerance"),
    }
    assert rt.aggregate_verdict(deltas) == "in_tolerance"


# ----------------------------------------------------------------------
# format_audit_entry — ISO8601 + schema fidelity.
# ----------------------------------------------------------------------


def _stub_measured() -> dict:
    return {
        "aggregate": {
            "f1": 0.83,
            "substance": 0.68,
            "cited_cosine": 0.42,
            "bypass": 0.12,
        },
        "per_session": [],
        "per_genre": {
            "hard_tek": {"f1": 0.81, "count": 2},
            "techno": {"f1": 0.85, "count": 2},
            "house": {"f1": 0.84, "count": 2},
        },
        "session_count": 6,
        "genre_count": 3,
    }


def _stub_locked() -> dict:
    return {
        "f1_min": 0.80,
        "substance_min": 0.65,
        "cited_cosine_min": 0.40,
        "bypass_max": 0.15,
        "per_genre_f1_min": 0.70,
    }


def test_format_audit_entry_iso8601_timestamp() -> None:
    deltas = {
        "f1": rt.compute_delta(0.83, 0.80),
        "substance": rt.compute_delta(0.68, 0.65),
        "cited_cosine": rt.compute_delta(0.42, 0.40),
        "bypass": rt.compute_delta(0.12, 0.15),
    }
    entry = rt.format_audit_entry(
        _stub_measured(),
        _stub_locked(),
        timestamp="2026-05-16T12:34:56Z",
        judges="gemini-3-flash,gemini-3-pro",
        corpus_dir=Path("eval/corpus/sessions"),
        verdict="in_tolerance",
        deltas=deltas,
    )
    # ISO8601 header on the first line.
    assert re.search(
        r"###\s+\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\s+—\s+verdict=in_tolerance",
        entry,
    ), entry
    # All four metrics surface in measured + locked + delta blocks.
    assert "measured: f1=0.83" in entry
    assert "locked:   f1=0.80" in entry
    assert "delta:    f1=+0.03" in entry
    assert "per-genre: hard_tek f1=0.81" in entry
    # In-tolerance entries surface a clean "none" action line.
    assert "action:  none" in entry


def test_format_audit_entry_out_of_tolerance_flags_recalibration() -> None:
    deltas = {
        "f1": rt.compute_delta(0.65, 0.80),
        "substance": rt.compute_delta(0.50, 0.65),
        "cited_cosine": rt.compute_delta(0.42, 0.40),
        "bypass": rt.compute_delta(0.12, 0.15),
    }
    entry = rt.format_audit_entry(
        _stub_measured(),
        _stub_locked(),
        timestamp="2026-05-16T12:34:56Z",
        judges="gemini-3-flash,gemini-3-pro",
        corpus_dir=Path("eval/corpus/sessions"),
        verdict="out_of_tolerance",
        deltas=deltas,
    )
    assert "verdict=out_of_tolerance" in entry
    assert "RECALIBRATION_REQUIRED" in entry


# ----------------------------------------------------------------------
# append_audit_entry — append-only invariant.
# ----------------------------------------------------------------------


def test_append_audit_entry_is_append_only(tmp_path: Path) -> None:
    """Three sequential writes preserve header + all entries in order."""
    log = tmp_path / "RECALIBRATION-LOG.md"
    # Seed with the header (matches the in-repo seed shape).
    log.write_text(
        "# Threshold Audit Trail\n\n## Audit Trail\n\n",
        encoding="utf-8",
    )
    entries = [
        "### 2026-05-16T10:00:00Z — verdict=in_tolerance\n- entry-1 marker\n\n",
        "### 2026-05-16T11:00:00Z — verdict=in_tolerance\n- entry-2 marker\n\n",
        "### 2026-05-16T12:00:00Z — verdict=out_of_tolerance\n- entry-3 marker\n\n",
    ]
    for e in entries:
        rt.append_audit_entry(log, e)

    text = log.read_text(encoding="utf-8")
    # Header intact.
    assert text.startswith("# Threshold Audit Trail")
    assert "## Audit Trail" in text
    # All three markers present in order.
    i1 = text.index("entry-1 marker")
    i2 = text.index("entry-2 marker")
    i3 = text.index("entry-3 marker")
    assert i1 < i2 < i3


def test_append_audit_entry_creates_seed_if_missing(tmp_path: Path) -> None:
    """When the log file is absent, the writer materializes the seed first."""
    log = tmp_path / "fresh.md"
    assert not log.exists()
    rt.append_audit_entry(log, "### 2026-05-16T10:00:00Z — verdict=in_tolerance\n- marker\n\n")
    text = log.read_text(encoding="utf-8")
    assert "Audit Trail" in text
    assert "marker" in text


# ----------------------------------------------------------------------
# THRESHOLD-LOCK.md is NEVER mutated by this script (T-42-02-01).
# ----------------------------------------------------------------------


def _md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def test_script_never_writes_to_lock_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A full out-of-tolerance recalibration run must NOT touch THRESHOLD-LOCK.md."""
    # Build a synthetic 6-session corpus (each with a placeholder input.wav).
    corpus = tmp_path / "sessions"
    corpus.mkdir()
    genres = ["hard_tek", "hard_tek", "techno", "techno", "house", "house"]
    for i, g in enumerate(genres):
        sdir = corpus / f"{g}_{i+1:02d}"
        sdir.mkdir()
        (sdir / "input.wav").write_bytes(b"RIFF\x00\x00\x00\x00WAVE")
        (sdir / "genre.txt").write_text(g + "\n", encoding="utf-8")

    # Copy the real lock into tmp so the test never touches the live file.
    real_lock = Path("eval/THRESHOLD-LOCK.md")
    lock_copy = tmp_path / "THRESHOLD-LOCK.md"
    lock_copy.write_bytes(real_lock.read_bytes())
    pre_md5 = _md5(lock_copy)

    log_path = tmp_path / "LOG.md"

    # Stub the replay-harness runner so no Gemini call happens.
    def fake_runner(argv: list[str]) -> int:
        # Find the --output dir argv slot.
        out_dir = Path(argv[argv.index("--output") + 1])
        out_dir.mkdir(parents=True, exist_ok=True)
        # Write an out-of-tolerance eval_report.json.
        report = {
            "sessions": [
                {
                    "session": f"{g}_{i+1:02d}",
                    "genre": g,
                    "f1": 0.60,          # 0.20 below locked f1_min=0.80
                    "substance": 0.50,   # 0.15 below substance_min=0.65
                    "cited_cosine": 0.30,
                    "bypass": 0.20,
                    "verdict": "below_threshold",
                }
                for i, g in enumerate(genres)
            ]
        }
        (out_dir / "eval_report.json").write_text(
            json.dumps(report), encoding="utf-8"
        )
        return 1  # harness's normal sub-threshold exit code

    monkeypatch.setattr(rt, "measure_against_corpus",
                        lambda corpus_dir, judges, **kw: rt._parse_eval_report(
                            _materialize_report(tmp_path, fake_runner)
                        ))

    # Invoke the recalibration path directly.
    rc = rt._run_recalibration(
        corpus_dir=corpus,
        judges="gemini-3-flash,gemini-3-pro",
        lock_path=lock_copy,
        log_path=log_path,
        dry_run=False,
        runner=fake_runner,
        now=datetime(2026, 5, 16, 12, 0, 0, tzinfo=timezone.utc),
    )

    # Exit 1 = out_of_tolerance (audit entry appended, but lock untouched).
    assert rc == 1
    assert _md5(lock_copy) == pre_md5, "THRESHOLD-LOCK.md was mutated!"
    # Audit entry exists.
    log_text = log_path.read_text(encoding="utf-8")
    assert "verdict=out_of_tolerance" in log_text
    assert "RECALIBRATION_REQUIRED" in log_text


def _materialize_report(tmp_path: Path, runner) -> Path:
    """Helper: run the stub runner once + return the eval_report.json path."""
    out = tmp_path / "harness-out"
    out.mkdir()
    argv = ["python", "-m", "scripts.eval.replay_harness",
            "--corpus", "x", "--judges", "x",
            "--output", str(out)]
    runner(argv)
    return out / "eval_report.json"


# ----------------------------------------------------------------------
# main() exit codes — corpus-size + dry-run.
# ----------------------------------------------------------------------


def test_main_exits_2_when_corpus_too_small(tmp_path: Path) -> None:
    """Empty corpus → exit 2 (corpus too small)."""
    empty = tmp_path / "empty"
    empty.mkdir()
    log = tmp_path / "LOG.md"
    rc = rt.main([
        "--corpus", str(empty),
        "--lock-path", "eval/THRESHOLD-LOCK.md",
        "--log-path", str(log),
    ])
    assert rc == 2


def test_main_dry_run_with_full_corpus(tmp_path: Path) -> None:
    """Dry-run path with 6 populated sessions exits 0 without invoking harness."""
    corpus = tmp_path / "sessions"
    corpus.mkdir()
    for i, g in enumerate(["hard_tek", "hard_tek", "techno", "techno", "house", "house"]):
        sdir = corpus / f"{g}_{i+1:02d}"
        sdir.mkdir()
        (sdir / "input.wav").write_bytes(b"RIFF")
        (sdir / "genre.txt").write_text(g + "\n", encoding="utf-8")

    log = tmp_path / "LOG.md"
    rc = rt.main([
        "--corpus", str(corpus),
        "--lock-path", "eval/THRESHOLD-LOCK.md",
        "--log-path", str(log),
        "--dry-run",
    ])
    assert rc == 0
    # Dry-run must NOT append to the log.
    assert not log.exists() or "verdict=" not in log.read_text(encoding="utf-8")


# ----------------------------------------------------------------------
# --check-only mode (CI fast lane).
# ----------------------------------------------------------------------


def test_check_only_exits_1_on_small_corpus(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    log = tmp_path / "LOG.md"
    # Even a fresh log doesn't help — corpus is the first gate.
    rc = rt.main([
        "--corpus", str(empty),
        "--log-path", str(log),
        "--check-only",
    ])
    assert rc == 1


def test_check_only_exits_1_on_stale_log(tmp_path: Path) -> None:
    """6 populated sessions + empty log → exit 1 with stale-log reason."""
    corpus = tmp_path / "sessions"
    corpus.mkdir()
    for i, g in enumerate(["hard_tek", "hard_tek", "techno", "techno", "house", "house"]):
        sdir = corpus / f"{g}_{i+1:02d}"
        sdir.mkdir()
        (sdir / "input.wav").write_bytes(b"RIFF")
    log = tmp_path / "LOG.md"
    # Seed the log with header only — no entries.
    log.write_text("# Audit Trail\n\n## Audit Trail\n\n", encoding="utf-8")
    rc = rt._run_check_only(corpus, log, now=datetime(2026, 5, 16, 12, 0, tzinfo=timezone.utc))
    assert rc == 1


def test_check_only_exits_0_when_both_fresh(tmp_path: Path) -> None:
    corpus = tmp_path / "sessions"
    corpus.mkdir()
    for i, g in enumerate(["hard_tek", "hard_tek", "techno", "techno", "house", "house"]):
        sdir = corpus / f"{g}_{i+1:02d}"
        sdir.mkdir()
        (sdir / "input.wav").write_bytes(b"RIFF")
    log = tmp_path / "LOG.md"
    log.write_text(
        "# Audit Trail\n\n## Audit Trail\n\n"
        "### 2026-05-16T10:00:00Z — verdict=in_tolerance\n- marker\n\n",
        encoding="utf-8",
    )
    now = datetime(2026, 5, 16, 12, 0, tzinfo=timezone.utc)
    rc = rt._run_check_only(corpus, log, now=now)
    assert rc == 0


def test_check_only_treats_schema_example_as_not_a_real_entry(tmp_path: Path) -> None:
    """The schema_example seed entry must NOT satisfy the freshness gate."""
    corpus = tmp_path / "sessions"
    corpus.mkdir()
    for i, g in enumerate(["hard_tek", "hard_tek", "techno", "techno", "house", "house"]):
        sdir = corpus / f"{g}_{i+1:02d}"
        sdir.mkdir()
        (sdir / "input.wav").write_bytes(b"RIFF")
    log = tmp_path / "LOG.md"
    # Seed with ONLY the schema_example placeholder, timestamped today.
    log.write_text(
        "# Audit Trail\n\n## Audit Trail\n\n"
        "### 2026-05-16T10:00:00Z — verdict=schema_example\n- placeholder\n\n",
        encoding="utf-8",
    )
    rc = rt._run_check_only(corpus, log, now=datetime(2026, 5, 16, 12, 0, tzinfo=timezone.utc))
    assert rc == 1, "schema_example placeholder must not satisfy freshness gate"


# ----------------------------------------------------------------------
# Constants surface.
# ----------------------------------------------------------------------


def test_constants_exposed() -> None:
    """The plan's exports must remain importable for downstream consumers."""
    assert rt.RECALIBRATION_TOLERANCE == 0.10
    assert callable(rt.compute_delta)
    assert callable(rt.measure_against_corpus)
    assert callable(rt.main)


def test_audit_log_latest_entry_parser_skips_invalid_lines(tmp_path: Path) -> None:
    """The header regex must ignore non-conforming lines (no crash, no false-positive)."""
    log = tmp_path / "LOG.md"
    log.write_text(
        "# Audit Trail\n"
        "## Audit Trail\n"
        "### not-a-timestamp — verdict=garbage\n"
        "### 2026-05-16T10:00:00Z — verdict=in_tolerance\n"
        "- marker\n"
        "garbage line\n"
        "### 2026-05-15T10:00:00Z — verdict=out_of_tolerance\n"
        "- marker2\n",
        encoding="utf-8",
    )
    latest = rt._latest_audit_entry_at(log)
    assert latest is not None
    assert latest == datetime(2026, 5, 16, 10, 0, tzinfo=timezone.utc)
