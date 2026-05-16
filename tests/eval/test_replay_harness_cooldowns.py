# SPDX-License-Identifier: Apache-2.0
"""Plan 40-04 / AUDIO-03 — replay_harness --print-cooldowns mode.

Pins the cooldown-report observational contract on a synthetic-event fixture.
The flag is additive (default off) and emits per-type measured median gaps
plus delta-from-locked to stderr. ABS delta > 1.0s triggers a WARNING line
but does NOT exit non-zero — Phase 42 GATE-04 will harden this into a CI
exit-non-zero gate once the real-corpus baseline is signed.
"""

from __future__ import annotations

import statistics
from pathlib import Path

import pytest

from scripts.eval.replay_harness import (
    _emit_cooldown_report,
    main,
)


# ----------------------------------------------------------------------
# Unit test on the pure-function emitter — drives the synthetic input that
# Task 2 spec calls out: 5 PHASE events spaced 12s apart, 4 MIX_MOVE events
# spaced 15s apart. Asserts the per-type report rows match the v4-baseline
# locked values (PHASE 10s, MIX_MOVE 14s).
# ----------------------------------------------------------------------


def _build_synthetic_gaps() -> dict[str, list[float]]:
    """5 PHASE events @ 12s spacing → 4 gaps of 12.0;
    4 MIX_MOVE events @ 15s spacing → 3 gaps of 15.0.

    Gap arithmetic in --print-cooldowns excludes the bootstrap gap (first
    fire has no predecessor — the harness records `now - now = 0` on the
    first fire, but the report SKIPS that zero so the median reflects real
    inter-event gaps only). See _emit_cooldown_report.
    """
    return {
        "PHASE": [12.0, 12.0, 12.0, 12.0],
        "MIX_MOVE": [15.0, 15.0, 15.0],
    }


def test_emit_cooldown_report_emits_per_type_median_lines(capsys) -> None:
    """5 PHASE @ 12s, 4 MIX_MOVE @ 15s → median PHASE=12, MIX_MOVE=15;
    delta(PHASE)=+2.0 (> 1.0 → WARNING), delta(MIX_MOVE)=+1.0 (== 1.0 →
    no warning, edge-case treated as not-exceeding)."""
    gaps = _build_synthetic_gaps()
    _emit_cooldown_report(gaps)
    err = capsys.readouterr().err
    # Per-type lines emitted
    assert "PHASE" in err
    assert "MIX_MOVE" in err
    # Median + expected + delta values land where expected
    assert "median_gap= 12.00s" in err
    assert "expected_min=10.00s" in err
    assert "delta= +2.00s" in err
    assert "median_gap= 15.00s" in err
    assert "expected_min=14.00s" in err
    assert "delta= +1.00s" in err
    # WARNING fires for PHASE (delta=+2.0 > 1.0)
    assert "WARNING: PHASE measured gap outside" in err
    # WARNING does NOT fire for MIX_MOVE (delta=+1.0 not strictly > 1.0)
    assert "WARNING: MIX_MOVE measured gap outside" not in err


def test_emit_cooldown_report_within_tolerance_emits_no_warning(capsys) -> None:
    """PHASE measured gap == locked value → delta=0 → no WARNING."""
    gaps = {"PHASE": [10.0, 10.0, 10.0]}
    _emit_cooldown_report(gaps)
    err = capsys.readouterr().err
    assert "median_gap= 10.00s" in err
    assert "delta= +0.00s" in err
    assert "WARNING" not in err


def test_emit_cooldown_report_unknown_event_type_falls_back_to_global(
    capsys,
) -> None:
    """Event type not in MIN_EVENT_GAP_PER_TYPE → compares against
    EVENT_GLOBAL_MIN_GAP (10.0) per the additive lookup semantics."""
    gaps = {"NOVEL_DETECTOR_TYPE_X": [11.0, 11.0]}
    _emit_cooldown_report(gaps)
    err = capsys.readouterr().err
    assert "NOVEL_DETECTOR_TYPE_X" in err
    assert "expected_min=10.00s" in err  # EVENT_GLOBAL_MIN_GAP fallback
    assert "median_gap= 11.00s" in err


def test_emit_cooldown_report_skips_single_event_types(capsys) -> None:
    """A type that fires only once has no inter-event gap → skip in report
    (no median is meaningful). Avoids spurious 0.0-median lines for one-off
    detectors that never refired in the replay window."""
    gaps = {"PHASE": [], "MIX_MOVE": [14.0, 14.0]}
    _emit_cooldown_report(gaps)
    err = capsys.readouterr().err
    assert "MIX_MOVE" in err
    # PHASE had no real gap recorded → row omitted
    assert "PHASE" not in err


def test_emit_cooldown_report_does_not_raise_on_empty_dict(capsys) -> None:
    """Empty accumulator (no events fired at all) emits a no-data marker
    but does NOT raise — harness with --print-cooldowns must complete
    cleanly even on a silent corpus."""
    _emit_cooldown_report({})
    err = capsys.readouterr().err
    # Either an explicit "no events recorded" marker OR an empty block — both
    # are acceptable; what matters is no exception was raised.
    assert "no events recorded" in err.lower() or err.strip() == ""


def test_emit_cooldown_report_median_handles_uneven_spacing(capsys) -> None:
    """Median (not mean) — robust to one outlier. 3 gaps of 10s + 1 outlier
    gap of 30s → median = 10.0 (not 15.0 from mean)."""
    gaps = {"PHASE": [10.0, 10.0, 10.0, 30.0]}
    _emit_cooldown_report(gaps)
    err = capsys.readouterr().err
    # Median of [10, 10, 10, 30] = 10.0 (not 15.0 mean)
    assert "median_gap= 10.00s" in err
    # Sanity — statistics.median agrees
    assert statistics.median([10.0, 10.0, 10.0, 30.0]) == 10.0


# ----------------------------------------------------------------------
# Integration test — CLI invocation with --print-cooldowns flag enabled
# against the synthetic_session fixture. The noop path's predicted_events
# is the ground_truth (3 events at t=1.0, 2.5, 4.0 in the fixture). The
# cooldown accumulator records inter-event gaps using session-relative
# timestamps (t_session). Since each event type fires exactly once in the
# fixture (TRACK_CHANGE, PHRASE_BOUNDARY, MIX_MOVE), no inter-event gaps
# exist → the report emits a "no events recorded" marker per type or
# omits empty rows. The flag itself must register on argparse without
# breaking existing harness behavior.
# ----------------------------------------------------------------------


FIXTURES = Path(__file__).parent / "fixtures"


def test_cli_accepts_print_cooldowns_flag_additively(tmp_path) -> None:
    """--print-cooldowns must register on argparse + not break existing
    invocation. Returns exit code 0 on the synth happy path identically
    to the existing CLI smoke test."""
    out = tmp_path / "out"
    rc = main(
        [
            "--corpus",
            str(FIXTURES),
            "--judges",
            "noop",
            "--output",
            str(out),
            "--print-cooldowns",
        ]
    )
    assert rc == 0
    # Existing artifacts still produced (additive flag — does not replace
    # the scorecard emission path).
    assert (out / "eval_report.json").exists()
    assert (out / "scorecard.md").exists()


def test_cli_help_lists_print_cooldowns_flag(capsys) -> None:
    """--help must list the new --print-cooldowns flag — discoverability
    contract for a future operator running `replay_harness --help`."""
    with pytest.raises(SystemExit):
        main(["--help"])
    captured = capsys.readouterr()
    # argparse emits --help to stdout
    assert "--print-cooldowns" in captured.out
