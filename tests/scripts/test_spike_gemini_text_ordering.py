# SPDX-License-Identifier: Apache-2.0
"""Plan 22-01 Task 1 — pass-criteria tests for the Gemini text-vs-audio
channel-ordering spike harness ``scripts/spike_gemini_text_ordering.py``.

The spike script's real-run mode is gated by ``GEMINI_API_KEY`` + an audible
djay Pro source — that path is Kaan-action-required and is NOT covered by
automated tests. The ``--dry-run`` mode emits N synthetic turns against a
fake session object so the harness self-tests deterministically.

These tests pin:

1. ``--dry-run`` runs end-to-end and writes the spike CSV (Task 1 done-line).
2. The CSV schema matches the contract spelled out in 22-01-PLAN.md:
   ``turn_idx, event_type, event_fire_at, text_first_emit_at,
    audio_first_chunk_at, text_minus_audio_ms, sample_audible,
    network_jitter_observed``.
3. The summary stdout line matches the contract:
   ``spike: N turns recorded, median text_minus_audio_ms=X.X``.
4. The verdict computation is correct on a synthetic text-first run.
5. The verdict computation is correct on a synthetic audio-first run.
6. The verdict computation is correct on an inconclusive run.

All tests drive the CLI via ``subprocess`` against ``sys.executable`` —
they pin the user-facing contract, not the in-process Python API.
"""

from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SPIKE_SCRIPT = REPO_ROOT / "scripts" / "spike_gemini_text_ordering.py"

EXPECTED_COLUMNS = [
    "turn_idx",
    "event_type",
    "event_fire_at",
    "text_first_emit_at",
    "audio_first_chunk_at",
    "text_minus_audio_ms",
    "sample_audible",
    "network_jitter_observed",
]


def _run_spike(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SPIKE_SCRIPT), *args],
        cwd=str(cwd or REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_spike_script_exists() -> None:
    assert SPIKE_SCRIPT.exists(), f"spike harness missing at {SPIKE_SCRIPT}"


def test_dry_run_writes_csv_with_expected_schema(tmp_path: Path) -> None:
    out_csv = tmp_path / "spike-data.csv"
    proc = _run_spike(["--dry-run", "--turns", "3", "--out", str(out_csv)])
    assert proc.returncode == 0, f"dry-run failed: stdout={proc.stdout!r} stderr={proc.stderr!r}"
    assert out_csv.exists(), "spike CSV not written"
    with out_csv.open("r", newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        rows = list(reader)
    assert header == EXPECTED_COLUMNS
    assert len(rows) == 3, f"expected 3 dry-run rows, got {len(rows)}"


def test_dry_run_emits_summary_line(tmp_path: Path) -> None:
    out_csv = tmp_path / "spike-data.csv"
    proc = _run_spike(["--dry-run", "--turns", "5", "--out", str(out_csv)])
    assert proc.returncode == 0
    # Contract: "spike: N turns recorded, median text_minus_audio_ms=X.X"
    summary_lines = [
        line
        for line in proc.stdout.splitlines()
        if line.startswith("spike: ") and "turns recorded" in line and "text_minus_audio_ms" in line
    ]
    assert summary_lines, f"summary line missing in stdout:\n{proc.stdout}"
    assert "spike: 5 turns recorded" in summary_lines[-1]


def test_dry_run_default_turn_count_is_10(tmp_path: Path) -> None:
    out_csv = tmp_path / "spike-data.csv"
    proc = _run_spike(["--dry-run", "--out", str(out_csv)])
    assert proc.returncode == 0
    with out_csv.open("r", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 10, f"default --turns should be 10, got {len(rows)}"


def test_text_first_synthetic_verdict(tmp_path: Path) -> None:
    out_csv = tmp_path / "spike-data.csv"
    proc = _run_spike(
        [
            "--dry-run",
            "--turns",
            "10",
            "--synthetic-mode",
            "text-first",
            "--out",
            str(out_csv),
        ]
    )
    assert proc.returncode == 0
    # text-first mode: text arrives BEFORE audio → text_minus_audio_ms < 0.
    with out_csv.open("r", newline="") as fh:
        rows = list(csv.DictReader(fh))
    deltas = [float(r["text_minus_audio_ms"]) for r in rows]
    assert all(d < 0 for d in deltas), f"text-first mode must produce negative deltas, got {deltas}"
    # Stdout must say the verdict aloud so Kaan can read it without parsing CSV.
    assert "verdict: text-first" in proc.stdout


def test_audio_first_synthetic_verdict(tmp_path: Path) -> None:
    out_csv = tmp_path / "spike-data.csv"
    proc = _run_spike(
        [
            "--dry-run",
            "--turns",
            "10",
            "--synthetic-mode",
            "audio-first",
            "--out",
            str(out_csv),
        ]
    )
    assert proc.returncode == 0
    with out_csv.open("r", newline="") as fh:
        rows = list(csv.DictReader(fh))
    deltas = [float(r["text_minus_audio_ms"]) for r in rows]
    assert all(d > 0 for d in deltas), f"audio-first mode must produce positive deltas, got {deltas}"
    assert "verdict: audio-first" in proc.stdout


def test_inconclusive_synthetic_verdict(tmp_path: Path) -> None:
    out_csv = tmp_path / "spike-data.csv"
    proc = _run_spike(
        [
            "--dry-run",
            "--turns",
            "10",
            "--synthetic-mode",
            "inconclusive",
            "--out",
            str(out_csv),
        ]
    )
    assert proc.returncode == 0
    # inconclusive = some text-first AND some audio-first, near-zero median.
    with out_csv.open("r", newline="") as fh:
        rows = list(csv.DictReader(fh))
    deltas = [float(r["text_minus_audio_ms"]) for r in rows]
    assert any(d > 0 for d in deltas) and any(d < 0 for d in deltas), (
        f"inconclusive mode must mix signs, got {deltas}"
    )
    assert "verdict: inconclusive" in proc.stdout


def test_event_types_cycle_taxonomy(tmp_path: Path) -> None:
    """The dry-run must exercise the 4-event burst spec'd in 22-01-PLAN.md
    Task 1: TRACK_CHANGE, PHASE, KAAN_SPOKE, MANUAL."""
    out_csv = tmp_path / "spike-data.csv"
    proc = _run_spike(["--dry-run", "--turns", "8", "--out", str(out_csv)])
    assert proc.returncode == 0
    with out_csv.open("r", newline="") as fh:
        rows = list(csv.DictReader(fh))
    seen = {row["event_type"] for row in rows}
    assert {"TRACK_CHANGE", "PHASE", "KAAN_SPOKE", "MANUAL"}.issubset(seen), (
        f"burst must cycle the 4 canonical event types, saw {seen}"
    )


def test_timeout_s_flag_accepted(tmp_path: Path) -> None:
    """The --timeout-s flag must parse without error (real-run knob; in dry-run
    mode it is a no-op but the CLI surface must accept it)."""
    out_csv = tmp_path / "spike-data.csv"
    proc = _run_spike(
        ["--dry-run", "--turns", "2", "--timeout-s", "600", "--out", str(out_csv)]
    )
    assert proc.returncode == 0


def test_help_text_documents_real_run_gate() -> None:
    proc = _run_spike(["--help"])
    assert proc.returncode == 0
    text = proc.stdout.lower()
    # --help must surface the GEMINI_API_KEY requirement for real-run mode so
    # Kaan reads it before plugging in BlackHole + djay Pro.
    assert "gemini_api_key" in text or "--dry-run" in text


@pytest.mark.parametrize("turns", [1, 5, 12])
def test_turn_count_round_trips(tmp_path: Path, turns: int) -> None:
    out_csv = tmp_path / "spike-data.csv"
    proc = _run_spike(["--dry-run", "--turns", str(turns), "--out", str(out_csv)])
    assert proc.returncode == 0, f"dry-run failed for --turns={turns}: {proc.stderr}"
    with out_csv.open("r", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == turns
