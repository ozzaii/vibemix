# SPDX-License-Identifier: Apache-2.0
"""Live drop-anticipation — turn the audible deck's sections + position into
"seconds until the next drop" (the substrate the co-host calls the drop on).

``refresh.py`` already computes the audible deck's structural sections (via
``cue_detect`` / DJ cues) and its play position every tick, but ``predicted_drop_in_sec``
has stayed ``None`` forever (SYSTEM-AUDIT C9 dead-end). This pure helper closes that
gap: given the sections ahead and where we are, how long until the drop lands?
Pure + deterministic so it's graded here, not in the live harness.
"""
from __future__ import annotations

from dataclasses import dataclass

from vibemix.state.drop_predict import (
    DROP_ARM_WINDOW_S,
    drop_call_cue,
    next_drop_section,
    predict_drop_in_sec,
    should_arm_drop_call,
)


@dataclass(frozen=True)
class _Sec:
    role: str
    start_s: float
    confidence: float = 1.0


def _track() -> list[_Sec]:
    # a typical structure: intro → build → DROP → groove → breakdown → DROP → outro
    return [
        _Sec("intro", 0.0),
        _Sec("build", 16.0),
        _Sec("drop", 32.0),
        _Sec("groove", 64.0),
        _Sec("breakdown", 96.0),
        _Sec("drop", 128.0),
        _Sec("outro", 160.0),
    ]


def test_returns_seconds_to_the_next_drop_ahead() -> None:
    # at 20s (mid-build), the next drop is at 32s → 12s away.
    assert predict_drop_in_sec(_track(), 20.0) == 12.0


def test_skips_a_drop_already_passed_to_the_next_one() -> None:
    # at 40s (just into the first drop), the NEXT drop is at 128s → 88s away.
    assert predict_drop_in_sec(_track(), 40.0) == 88.0


def test_none_when_no_drop_remains() -> None:
    # at 130s, both drops are behind us.
    assert predict_drop_in_sec(_track(), 130.0) is None


def test_none_when_position_is_unknown() -> None:
    assert predict_drop_in_sec(_track(), None) is None


def test_low_confidence_drop_is_skipped() -> None:
    secs = [_Sec("build", 16.0), _Sec("drop", 32.0, confidence=0.2), _Sec("drop", 80.0, confidence=0.9)]
    # the 32s drop is below the floor → fall through to the trusted 80s drop.
    assert predict_drop_in_sec(secs, 10.0, min_confidence=0.5) == 70.0


def test_next_drop_section_matches_eta_selection() -> None:
    secs = [_Sec("drop", 80.0), _Sec("drop", 32.0), _Sec("build", 16.0)]
    section = next_drop_section(secs, 10.0)
    assert section is secs[1]
    assert predict_drop_in_sec(secs, 10.0) == 22.0


def test_next_drop_section_respects_confidence_and_horizon() -> None:
    secs = [_Sec("drop", 32.0, confidence=0.2), _Sec("drop", 80.0, confidence=0.9)]
    assert next_drop_section(secs, 10.0, min_confidence=0.5) is secs[1]
    assert next_drop_section(secs, 10.0, min_confidence=0.5, max_horizon_s=30.0) is None


def test_drop_beyond_horizon_is_not_predicted() -> None:
    # a drop 88s away is too far to "call" — beyond a 30s horizon → None.
    assert predict_drop_in_sec(_track(), 40.0, max_horizon_s=30.0) is None
    # but within horizon it IS returned.
    assert predict_drop_in_sec(_track(), 20.0, max_horizon_s=30.0) == 12.0


def test_exactly_on_the_drop_boundary_is_not_in_the_future() -> None:
    # standing exactly at a drop's start is not "incoming" — look past it.
    assert predict_drop_in_sec(_track(), 32.0) == 96.0  # next drop at 128 → 96s


def test_empty_sections_is_none() -> None:
    assert predict_drop_in_sec([], 10.0) is None


def test_non_negative_result() -> None:
    # never returns a negative ETA even with odd inputs.
    out = predict_drop_in_sec(_track(), 31.999)
    assert out is not None and out >= 0.0


# --- arming: when the countdown crosses into the window, fire exactly once ---


def test_arms_when_countdown_crosses_into_window() -> None:
    # prev was outside the 2s window (3.0s), now inside (1.5s) → arm.
    assert should_arm_drop_call(1.5, 3.0) is True


def test_does_not_arm_while_drop_is_still_far() -> None:
    assert should_arm_drop_call(5.0, 8.0) is False


def test_does_not_refire_once_already_inside_window() -> None:
    # both readings inside the window → already called, stay quiet.
    assert should_arm_drop_call(0.5, 1.5) is False


def test_arms_on_first_reading_when_prev_unknown() -> None:
    # no prior reading but already inside the window → arm (e.g. cue jump).
    assert should_arm_drop_call(1.0, None) is True


def test_none_prediction_never_arms() -> None:
    assert should_arm_drop_call(None, 1.0) is False
    assert should_arm_drop_call(None, None) is False


def test_exactly_on_window_edge_counts_as_inside() -> None:
    assert should_arm_drop_call(DROP_ARM_WINDOW_S, DROP_ARM_WINDOW_S + 0.5) is True


def test_custom_arm_window_respected() -> None:
    assert should_arm_drop_call(3.5, 6.0, arm_window_s=4.0) is True
    assert should_arm_drop_call(3.5, 6.0, arm_window_s=2.0) is False


def test_drop_call_cue_is_a_known_reaction_key() -> None:
    from vibemix.runtime.drop_reaction import REACTION_LINES

    assert drop_call_cue(1.5) in REACTION_LINES
