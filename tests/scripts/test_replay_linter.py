# SPDX-License-Identifier: Apache-2.0
"""Plan 20-03 Task 2 — pass-criteria tests for ``scripts/replay_linter.py``.

Drives the CLI exactly the way Phase 16 ear-test will — via ``subprocess``
against ``sys.executable`` (NOT importing main() directly) — so the test
matrix pins the CLI contract, not the in-process Python API.

Each test function takes the ``replay_session_dir`` fixture which copies
the committed synthetic_session fixture to ``tmp_path`` so tests do not
pollute the source fixture dir with stale ``linter_report.csv`` files
(every test starts without one, so any test that does not produce one
catches a silent no-op regression).

Test catalogue (9 cases, mirrors the plan's Task 2 behavior list):

1. ``test_synthetic_session_stripped_rate_below_0_15`` — the GROUND-06
   gate (replay-validation invariant).
2. ``test_csv_report_has_correct_shape`` — header + 7 data rows + 6 cols.
3. ``test_csv_response_id_lex_sorted`` — invocation-order pin.
4. ``test_csv_t_session_first_row_is_zero`` — baseline pin.
5. ``test_csv_t_session_increases_monotonically`` — HHMMSS-delta math pin.
6. ``test_csv_invalid_row_has_reason_no_citations`` — fail-soft path pin.
7. ``test_mode_debrief_accepted_as_arg`` — --mode flag contract.
8. ``test_missing_session_dir_raises`` — input-validation gate.
9. ``test_missing_responses_subdir_raises`` — input-validation gate.
"""

from __future__ import annotations

import csv
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SYNTHETIC_FIXTURE = REPO_ROOT / "tests/scripts/fixtures/synthetic_session"


# ---------------------------------------------------------------------------
# Shared fixture — fresh copy of the synthetic session per test so the
# committed fixture dir never accumulates stale linter_report.csv writes.
# ---------------------------------------------------------------------------


@pytest.fixture
def replay_session_dir(tmp_path: Path) -> Path:
    """Copy the committed synthetic_session fixture into tmp_path.

    Returns the path of the *copy* — tests that mutate (e.g., remove the
    responses/ subdir) work on the copy, not the source.
    """
    dst = tmp_path / "synthetic_session"
    shutil.copytree(SYNTHETIC_FIXTURE, dst)
    return dst


def _run_replay(
    session_dir: Path,
    *,
    extra_args: tuple[str, ...] = (),
) -> subprocess.CompletedProcess[str]:
    """Invoke scripts/replay_linter.py via subprocess from REPO_ROOT.

    Uses ``sys.executable`` so the test inherits the same interpreter +
    site-packages the developer ran pytest with. Returns the
    CompletedProcess for caller-side assertions.
    """
    return subprocess.run(
        [
            sys.executable,
            "scripts/replay_linter.py",
            "--session",
            str(session_dir),
            "--print-rate",
            *extra_args,
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        check=False,
    )


def _parse_stripped_rate(stdout: str) -> float:
    """Pull the STRIPPED_RATE=<float> line out of stdout."""
    matches = [
        ln for ln in stdout.splitlines() if ln.startswith("STRIPPED_RATE=")
    ]
    assert matches, f"no STRIPPED_RATE line in stdout: {stdout!r}"
    return float(matches[-1].split("=", 1)[1])


def _read_csv_rows(csv_path: Path) -> list[list[str]]:
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.reader(f))


# ---------------------------------------------------------------------------
# 1 — GROUND-06 stripped_rate gate
# ---------------------------------------------------------------------------


def test_synthetic_session_stripped_rate_below_0_15(replay_session_dir: Path) -> None:
    """The replay-validation contract: stripped_rate < 0.15 on the fixture."""
    result = _run_replay(replay_session_dir)
    assert result.returncode == 0, (
        f"replay exit nonzero: {result.returncode}\nSTDERR:\n{result.stderr}"
    )
    rate = _parse_stripped_rate(result.stdout)
    assert rate < 0.15, f"stripped_rate {rate} >= 0.15 — fixture or linter regressed"


# ---------------------------------------------------------------------------
# 2 — CSV shape pin (header + 7 data rows + 6 cols)
# ---------------------------------------------------------------------------


def test_csv_report_has_correct_shape(replay_session_dir: Path) -> None:
    csv_path = replay_session_dir / "linter_report.csv"
    assert not csv_path.exists(), "fixture copy must start without a CSV"

    result = _run_replay(replay_session_dir)
    assert result.returncode == 0, result.stderr
    assert csv_path.exists(), "replay did not write linter_report.csv"

    rows = _read_csv_rows(csv_path)
    assert rows[0] == [
        "response_id",
        "t_session",
        "citations_found",
        "valid",
        "reason",
        "missing_atoms",
    ], f"unexpected header: {rows[0]}"
    data_rows = rows[1:]
    assert len(data_rows) == 7, f"expected 7 data rows, got {len(data_rows)}"
    for row in data_rows:
        assert len(row) == 6, f"row not 6 cols: {row}"


# ---------------------------------------------------------------------------
# 3 — invocation-order pin (lex sort matches dir name order)
# ---------------------------------------------------------------------------


def test_csv_response_id_lex_sorted(replay_session_dir: Path) -> None:
    result = _run_replay(replay_session_dir)
    assert result.returncode == 0, result.stderr

    rows = _read_csv_rows(replay_session_dir / "linter_report.csv")[1:]
    response_ids = [row[0] for row in rows]

    expected = sorted(
        p.name for p in (replay_session_dir / "responses").iterdir() if p.is_dir()
    )
    assert response_ids == expected, (
        f"response_id order drift: got {response_ids}, expected {expected}"
    )


# ---------------------------------------------------------------------------
# 4 — first-row baseline pin (t_session=0.0)
# ---------------------------------------------------------------------------


def test_csv_t_session_first_row_is_zero(replay_session_dir: Path) -> None:
    result = _run_replay(replay_session_dir)
    assert result.returncode == 0, result.stderr

    rows = _read_csv_rows(replay_session_dir / "linter_report.csv")[1:]
    assert float(rows[0][1]) == 0.0, (
        f"first-row t_session not zero: {rows[0]}"
    )


# ---------------------------------------------------------------------------
# 5 — monotonic t_session pin (HHMMSS-delta math)
# ---------------------------------------------------------------------------


def test_csv_t_session_increases_monotonically(replay_session_dir: Path) -> None:
    result = _run_replay(replay_session_dir)
    assert result.returncode == 0, result.stderr

    rows = _read_csv_rows(replay_session_dir / "linter_report.csv")[1:]
    t_values = [float(row[1]) for row in rows]
    for prev, cur in zip(t_values, t_values[1:]):
        assert cur > prev, (
            f"t_session not monotonic: prev={prev} cur={cur} all={t_values}"
        )


# ---------------------------------------------------------------------------
# 6 — fail-soft "I'm listening" row (no_citations + invalid + 0 citations)
# ---------------------------------------------------------------------------


def test_csv_invalid_row_has_reason_no_citations(replay_session_dir: Path) -> None:
    result = _run_replay(replay_session_dir)
    assert result.returncode == 0, result.stderr

    rows = _read_csv_rows(replay_session_dir / "linter_report.csv")[1:]
    layer_arrival_rows = [
        row for row in rows if row[0] == "0006_120115_LAYER_ARRIVAL"
    ]
    assert len(layer_arrival_rows) == 1, (
        f"expected exactly 1 LAYER_ARRIVAL row, got {layer_arrival_rows}"
    )
    row = layer_arrival_rows[0]
    # row layout: response_id, t_session, citations_found, valid, reason, missing_atoms
    assert row[2] == "0", f"citations_found not 0: {row}"
    assert row[3] == "False", f"valid not False: {row}"
    assert row[4] == "no_citations", f"reason not no_citations: {row}"


# ---------------------------------------------------------------------------
# 7 — --mode debrief accepted by the CLI
# ---------------------------------------------------------------------------


def test_mode_debrief_accepted_as_arg(replay_session_dir: Path) -> None:
    result = _run_replay(replay_session_dir, extra_args=("--mode", "debrief"))
    assert result.returncode == 0, (
        f"--mode debrief rejected: rc={result.returncode}\nSTDERR:\n{result.stderr}"
    )
    # Debrief widens tolerance — the synthetic fixture's invalid response
    # is "no_citations" (not a tolerance miss), so stripped_rate is the
    # same. Mode flag is contract-pinned here.
    rate = _parse_stripped_rate(result.stdout)
    assert rate < 0.15


# ---------------------------------------------------------------------------
# 8 — missing --session dir raises (FileNotFoundError surfaces)
# ---------------------------------------------------------------------------


def test_missing_session_dir_raises(tmp_path: Path) -> None:
    nonexistent = tmp_path / "does_not_exist"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/replay_linter.py",
            "--session",
            str(nonexistent),
            "--print-rate",
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        check=False,
    )
    assert result.returncode != 0, (
        f"expected nonzero exit on missing session, got {result.returncode}"
    )
    # stderr surfaces FileNotFoundError + the offending path.
    assert (
        "FileNotFoundError" in result.stderr
        or str(nonexistent) in result.stderr
    ), f"stderr does not surface the failure: {result.stderr!r}"


# ---------------------------------------------------------------------------
# 9 — missing responses/ subdir raises
# ---------------------------------------------------------------------------


def test_missing_responses_subdir_raises(tmp_path: Path) -> None:
    half_session = tmp_path / "half_session"
    half_session.mkdir()
    # events.jsonl present but responses/ missing.
    (half_session / "events.jsonl").write_text(
        '{"t": 0.0, "kind": "evidence_observation", "source": "ev", '
        '"key": "X", "t_session": 0.0}\n',
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/replay_linter.py",
            "--session",
            str(half_session),
            "--print-rate",
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        check=False,
    )
    assert result.returncode != 0, (
        f"expected nonzero exit on missing responses/, got {result.returncode}"
    )
    assert (
        "FileNotFoundError" in result.stderr
        or "responses" in result.stderr
    ), f"stderr does not surface missing responses/: {result.stderr!r}"
