# SPDX-License-Identifier: Apache-2.0
"""Contract tests for the durable judge pooling walker."""
from __future__ import annotations

import importlib.util
import json
import pathlib

_SPEC = importlib.util.spec_from_file_location(
    "judge_pool",
    pathlib.Path(__file__).resolve().parents[2] / "scripts" / "eval" / "judge_pool.py",
)
assert _SPEC is not None and _SPEC.loader is not None
judge_pool = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(judge_pool)


def _mk_run(tmp_path: pathlib.Path, name: str, rows: list[dict]) -> pathlib.Path:
    d = tmp_path / name
    d.mkdir(parents=True)
    (d / "judge.json").write_text(json.dumps({"rows": rows}))
    return d


def _row(ok: bool, friend: int = 2, status: int = 200) -> dict:
    return {
        "id": "0001_PHASE",
        "event": "PHASE",
        "line": "Hold the low end open. [energy:x]",
        "status": status,
        "scores": {
            "friend_not_narrator": friend,
            "grounded_not_fabricated": 3,
            "earned_not_constant": 2,
            "move_specific_not_spectrum": 2,
            "voice_no_slop": 2,
            "should_speak": ok,
            "why": "test row",
        } if status == 200 else None,
    }


def test_pools_across_runs_in_one_lane(tmp_path, capsys) -> None:
    _mk_run(tmp_path, "x-audio-r1", [_row(True, friend=3), _row(False, friend=1)])
    _mk_run(tmp_path, "x-audio-r2", [_row(True, friend=2)])
    rc = judge_pool.main(["--quiet", str(tmp_path / "x-audio-r1"), str(tmp_path / "x-audio-r2")])
    out = capsys.readouterr().out
    assert rc == 0
    assert "POOLED audio (n=3)" in out
    # friend pooled mean (3+1+2)/3 = 2.00 → meets the 2.0 bar
    assert "friend   2.00 ✓" in out
    # pooled should_NOT 1/3 = 33.3% → fails the ≤20% bar
    assert "1/3 = 33.3% ✗" in out


def test_small_pool_flagged_as_noise(tmp_path, capsys) -> None:
    _mk_run(tmp_path, "y-midi-r1", [_row(True)])
    judge_pool.main(["--quiet", str(tmp_path / "y-midi-r1")])
    out = capsys.readouterr().out
    assert "NOISE, do not verdict" in out


def test_unscored_rows_are_excluded_not_counted_ok(tmp_path, capsys) -> None:
    """A status:-1 judge row (parse failure) is unjudged — it must leave the
    denominator entirely (the lever3 audio-r2 incident), never count as OK."""
    _mk_run(tmp_path, "z-audio-r1", [_row(True), _row(False, status=-1)])
    judge_pool.main(["--quiet", str(tmp_path / "z-audio-r1")])
    out = capsys.readouterr().out
    assert "(n=1)" in out
    assert "0/1 = 0.0%" in out
