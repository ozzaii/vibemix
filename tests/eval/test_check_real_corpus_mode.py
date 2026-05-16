# SPDX-License-Identifier: Apache-2.0
"""Phase 42 Plan 02 — workflow + CLI contract tests for `--check-real-corpus` mode.

Pins:
    - `.github/workflows/eval.yml` parses as valid YAML.
    - The new step (`Real-corpus calibration freshness gate (Phase 42 GATE-04)`)
      lives in the eval job's step list and gates on `schedule` OR
      `workflow_dispatch` only (NOT `pull_request`).
    - The step body invokes `recalibrate_thresholds.py` with `--check-only`.
    - The CLI `--check-only` mode exits 1 on a small corpus, 1 on a stale
      log, and 0 when both invariants are fresh.
"""

from __future__ import annotations

import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

EVAL_YML = Path(".github/workflows/eval.yml")
SCRIPT = "scripts.eval.recalibrate_thresholds"


# ----------------------------------------------------------------------
# YAML structure tests.
# ----------------------------------------------------------------------


def _load_eval_yml() -> dict:
    return yaml.safe_load(EVAL_YML.read_text(encoding="utf-8"))


def test_eval_yml_parses_as_valid_yaml() -> None:
    """yaml.safe_load must succeed (no syntax drift from the Phase 42 edit)."""
    data = _load_eval_yml()
    assert isinstance(data, dict)
    assert "jobs" in data
    assert "eval" in data["jobs"]


def _steps() -> list[dict]:
    return _load_eval_yml()["jobs"]["eval"]["steps"]


def test_eval_yml_has_check_real_corpus_step() -> None:
    """A step named `Real-corpus calibration freshness gate` exists."""
    steps = _steps()
    matched = [
        s for s in steps
        if re.search(r"Real-corpus calibration freshness gate", s.get("name", ""))
    ]
    assert len(matched) == 1, (
        "expected exactly one step named "
        "'Real-corpus calibration freshness gate (Phase 42 GATE-04)'; "
        f"found {len(matched)}"
    )


def test_check_real_corpus_step_gated_on_schedule_only() -> None:
    """The step must fire on schedule + workflow_dispatch ONLY — never on PR.

    PR mode uses VCR cassettes (no live judges). The real-corpus freshness
    gate is a nightly + manual surface only.
    """
    steps = _steps()
    target = next(
        s for s in steps
        if "Real-corpus calibration freshness gate" in s.get("name", "")
    )
    if_expr = target.get("if", "")
    assert "schedule" in if_expr, if_expr
    assert "workflow_dispatch" in if_expr, if_expr
    # Must NOT fire on PRs — that path is cassette-backed.
    assert "pull_request" not in if_expr, if_expr


def test_check_real_corpus_step_invokes_recalibrate_script() -> None:
    """The step's `run` body must invoke recalibrate_thresholds.py + --check-only."""
    steps = _steps()
    target = next(
        s for s in steps
        if "Real-corpus calibration freshness gate" in s.get("name", "")
    )
    run_body = target.get("run", "")
    assert "recalibrate_thresholds" in run_body, run_body
    assert "--check-only" in run_body, run_body
    # Lock + log paths are explicit (defensive against silent default drift).
    assert "eval/THRESHOLD-LOCK.md" in run_body
    assert "eval/THRESHOLD-RECALIBRATION-LOG.md" in run_body


def test_check_real_corpus_step_placed_before_post_scorecard() -> None:
    """Step ordering: real-corpus gate sits between nightly-canary and post-scorecard.

    Plan 42-02 contract: insert AFTER 'Run replay harness (nightly canary …)'
    and BEFORE 'Post scorecard to PR'.
    """
    steps = _steps()
    names = [s.get("name", "") for s in steps]
    canary_idx = next(
        i for i, n in enumerate(names) if "nightly canary" in n
    )
    gate_idx = next(
        i for i, n in enumerate(names) if "Real-corpus calibration freshness gate" in n
    )
    post_idx = next(
        i for i, n in enumerate(names) if "Post scorecard to PR" in n
    )
    assert canary_idx < gate_idx < post_idx, (
        f"step order broken: canary={canary_idx} gate={gate_idx} "
        f"post={post_idx} (names={names})"
    )


# ----------------------------------------------------------------------
# CLI subprocess tests — full --check-only flow.
# ----------------------------------------------------------------------


def _populate_corpus(corpus_dir: Path, n: int = 6) -> None:
    """Materialize ``n`` session dirs each with a placeholder input.wav."""
    corpus_dir.mkdir(parents=True, exist_ok=True)
    genres = ["hard_tek", "hard_tek", "techno", "techno", "house", "house"]
    for i in range(n):
        g = genres[i % len(genres)]
        sdir = corpus_dir / f"{g}_{i+1:02d}"
        sdir.mkdir()
        (sdir / "input.wav").write_bytes(b"RIFF")


def test_check_only_mode_exits_1_on_small_corpus(tmp_path: Path) -> None:
    """Empty corpus → exit 1 with structured stderr."""
    corpus = tmp_path / "sessions"
    corpus.mkdir()  # zero populated sessions
    log = tmp_path / "LOG.md"
    log.write_text(
        "# Audit Trail\n## Audit Trail\n\n"
        f"### {_recent_iso()} — verdict=in_tolerance\n- marker\n\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            sys.executable, "-m", SCRIPT,
            "--corpus", str(corpus),
            "--check-only",
            "--log-path", str(log),
        ],
        capture_output=True,
        text=True,
        cwd=Path.cwd(),
    )
    assert proc.returncode == 1, proc.stderr
    assert "fewer than 6 sessions" in proc.stderr, proc.stderr


def test_check_only_mode_exits_1_on_stale_log(tmp_path: Path) -> None:
    """6 populated sessions + empty log → exit 1 with stale-log reason."""
    corpus = tmp_path / "sessions"
    _populate_corpus(corpus)
    log = tmp_path / "LOG.md"
    log.write_text(
        "# Audit Trail\n## Audit Trail\n\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            sys.executable, "-m", SCRIPT,
            "--corpus", str(corpus),
            "--check-only",
            "--log-path", str(log),
        ],
        capture_output=True,
        text=True,
        cwd=Path.cwd(),
    )
    assert proc.returncode == 1, proc.stderr
    assert re.search(
        r"no recalibration log entry in last 30 days|stale recalibration log",
        proc.stderr,
    ), proc.stderr


def test_check_only_mode_exits_1_on_old_audit_entry(tmp_path: Path) -> None:
    """6 sessions + audit entry timestamped >30 days ago → exit 1 stale."""
    corpus = tmp_path / "sessions"
    _populate_corpus(corpus)
    log = tmp_path / "LOG.md"
    old = (datetime.now(timezone.utc) - timedelta(days=45)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    log.write_text(
        "# Audit Trail\n## Audit Trail\n\n"
        f"### {old} — verdict=in_tolerance\n- old marker\n\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            sys.executable, "-m", SCRIPT,
            "--corpus", str(corpus),
            "--check-only",
            "--log-path", str(log),
        ],
        capture_output=True,
        text=True,
        cwd=Path.cwd(),
    )
    assert proc.returncode == 1, proc.stderr
    assert "stale recalibration log" in proc.stderr or "no recalibration log entry" in proc.stderr


def test_check_only_mode_exits_0_when_both_fresh(tmp_path: Path) -> None:
    """6 sessions + audit entry within last 30 days → exit 0."""
    corpus = tmp_path / "sessions"
    _populate_corpus(corpus)
    log = tmp_path / "LOG.md"
    log.write_text(
        "# Audit Trail\n## Audit Trail\n\n"
        f"### {_recent_iso()} — verdict=in_tolerance\n- fresh marker\n\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            sys.executable, "-m", SCRIPT,
            "--corpus", str(corpus),
            "--check-only",
            "--log-path", str(log),
        ],
        capture_output=True,
        text=True,
        cwd=Path.cwd(),
    )
    assert proc.returncode == 0, f"stdout={proc.stdout}\nstderr={proc.stderr}"
    assert "CHECK_REAL_CORPUS_OK" in proc.stdout


# ----------------------------------------------------------------------
# Helpers.
# ----------------------------------------------------------------------


def _recent_iso() -> str:
    """ISO8601 timestamp 1 hour in the past (always within the 30-day window)."""
    ts = datetime.now(timezone.utc) - timedelta(hours=1)
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")
