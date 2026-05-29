# SPDX-License-Identifier: Apache-2.0
"""LESSON-04 advancement-gate predicate regression tests.

Five small targeted tests covering the lesson-advancement decision
points:

1. ``test_cc_drop_30pct`` — ``action_matches`` returns True when a CC
   delta ≥30% of the 127 range (≥38) is observed; False below the
   threshold.
2. ``test_button_press`` — ``action_matches`` returns True for a
   matching button+deck+direction; False when any field differs.
3. ``test_3_strike_escalation`` — 30 s of awaiting_action escalates
   ``strike_count`` once per 30 s up to 3; further ticks cap at 3.
4. ``test_min_dwell_blocks_skip`` — sending ``skip`` before t=45 s
   keeps the runtime in ``awaiting_action``.
5. ``test_skip_after_dwell`` — sending ``skip`` after t=45 s
   transitions to ``advancing``.

REQ-ID: LESSON-04 (advance gate + min-dwell + 3-strike escalation).
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

try:
    from vibemix.learn.runtime import LessonRuntime
    from vibemix.learn.state import LearnState
except ImportError:
    pytest.skip(
        "LessonRuntime advancement gates unavailable in this partial Learn build.",
        allow_module_level=True,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _runtime_at_awaiting_action() -> LessonRuntime:
    """Build + drive a LessonRuntime to ``awaiting_action`` state."""
    rt = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=MagicMock(name="midi_mirror"),
        controller_state=MagicMock(name="controller_state"),
        ipc_router=MagicMock(name="ipc_router"),
        progress_store=MagicMock(name="progress_store"),
    )
    rt.send(
        "load",
        lesson_id="L0.00-press-play",
        course_id="course_0",
        controller_id="pioneer_ddj_flx4",
    )
    rt.send("begin")
    return rt


# ---------------------------------------------------------------------------
# Test 1: CC drop ≥30% of range advances; <30% does not
# ---------------------------------------------------------------------------


def test_cc_drop_30pct() -> None:
    """CC delta ≥38 (30% of 127) → match; delta <38 → no match.

    The expected_action is a CC with ``min_delta`` of 38 (per the
    fixture). ``action_matches`` returns True iff the observed event
    is a CC with the same control AND ``abs(value - prev_value)`` ≥
    ``min_delta``.
    """
    rt = _runtime_at_awaiting_action()

    matches_big = rt.action_matches(
        {
            "type": "cc",
            "control": "vol:A",
            "value": 127,
            "prev_value": 80,
        },
        expected={
            "type": "cc",
            "control": "vol:A",
            "min_delta": 38,
        },
    )
    assert matches_big is True, (
        "CC delta 47 ≥ min_delta 38 should match, but action_matches "
        "returned False"
    )

    matches_small = rt.action_matches(
        {
            "type": "cc",
            "control": "vol:A",
            "value": 100,
            "prev_value": 80,
        },
        expected={
            "type": "cc",
            "control": "vol:A",
            "min_delta": 38,
        },
    )
    assert matches_small is False, (
        "CC delta 20 < min_delta 38 should NOT match, but "
        "action_matches returned True"
    )


# ---------------------------------------------------------------------------
# Test 2: button press matches on type+control+deck+direction
# ---------------------------------------------------------------------------


def test_button_press() -> None:
    """A button-press event matches the expected_action only when
    every relevant field matches: type, control, deck, direction."""
    rt = _runtime_at_awaiting_action()
    expected = {
        "type": "button",
        "control": "play",
        "deck": "A",
        "direction": "down",
    }

    assert (
        rt.action_matches(
            {
                "type": "button",
                "control": "play",
                "deck": "A",
                "direction": "down",
            },
            expected=expected,
        )
        is True
    ), "exact match should be True"

    assert (
        rt.action_matches(
            {
                "type": "button",
                "control": "play",
                "deck": "B",  # WRONG DECK
                "direction": "down",
            },
            expected=expected,
        )
        is False
    ), "deck mismatch should be False"

    assert (
        rt.action_matches(
            {
                "type": "button",
                "control": "play",
                "deck": "A",
                "direction": "up",  # WRONG DIRECTION
            },
            expected=expected,
        )
        is False
    ), "direction mismatch should be False"


def test_action_matches_accepts_split_or_colon_deck_ids() -> None:
    """Runtime matching accepts both wire shapes for deck-scoped controls."""
    rt = _runtime_at_awaiting_action()

    assert rt.action_matches(
        {
            "type": "cc",
            "control": "vol",
            "deck": "A",
            "value": 127,
            "prev_value": 60,
        },
        expected={
            "type": "cc",
            "control": "vol:A",
            "min_delta": 38,
        },
    )

    assert rt.action_matches(
        {
            "type": "button",
            "control": "play:A",
            "direction": "down",
        },
        expected={
            "type": "button",
            "control": "play",
            "deck": "A",
            "direction": "down",
        },
    )


# ---------------------------------------------------------------------------
# Test 3: 3-strike escalation
# ---------------------------------------------------------------------------


def test_3_strike_escalation(monkeypatch: pytest.MonkeyPatch) -> None:
    """While in ``awaiting_action``, ``strike_count`` escalates once per
    30 s up to 3; a 4th 30 s window does NOT push to 4 (cap holds)."""
    import time

    base = 1_700_000_000.0
    fake_now = {"t": base}

    def fake_monotonic() -> float:
        return fake_now["t"]

    monkeypatch.setattr(time, "monotonic", fake_monotonic)

    rt = _runtime_at_awaiting_action()

    # t = 30 s → strike 1
    fake_now["t"] = base + 30.0
    rt.send("strike")
    assert rt.current_state.id == "hint_strike_1", (
        f"after 30 s expect hint_strike_1, got {rt.current_state.id!r}"
    )

    # t = 60 s → strike 2
    fake_now["t"] = base + 60.0
    rt.send("strike")
    assert rt.current_state.id == "hint_strike_2", (
        f"after 60 s expect hint_strike_2, got {rt.current_state.id!r}"
    )

    # t = 90 s → strike 3
    fake_now["t"] = base + 90.0
    rt.send("strike")
    assert rt.current_state.id == "hint_strike_3", (
        f"after 90 s expect hint_strike_3, got {rt.current_state.id!r}"
    )

    # t = 120 s → strike 4 attempt — state STAYS at hint_strike_3 (cap)
    fake_now["t"] = base + 120.0
    rt.send("strike")
    assert rt.current_state.id == "hint_strike_3", (
        "strike escalation should cap at 3, but state advanced past "
        f"hint_strike_3 to {rt.current_state.id!r}"
    )


# ---------------------------------------------------------------------------
# Test 4: min-dwell guard rejects skip < 45 s
# ---------------------------------------------------------------------------


def test_min_dwell_blocks_skip(monkeypatch: pytest.MonkeyPatch) -> None:
    """``send("skip")`` before 45 s elapsed must keep the runtime in
    ``awaiting_action`` — the 45 s anti-speedrun floor."""
    import time

    base = 1_700_000_000.0
    fake_now = {"t": base}

    def fake_monotonic() -> float:
        return fake_now["t"]

    monkeypatch.setattr(time, "monotonic", fake_monotonic)

    rt = _runtime_at_awaiting_action()

    fake_now["t"] = base + 10.0  # only 10 s in
    rt.send("skip")
    assert rt.current_state.id == "awaiting_action", (
        "min-dwell guard failed — skip at t+10s should NOT advance; "
        f"state is {rt.current_state.id!r}"
    )


# ---------------------------------------------------------------------------
# Test 5: skip after dwell advances
# ---------------------------------------------------------------------------


def test_skip_after_dwell(monkeypatch: pytest.MonkeyPatch) -> None:
    """``send("skip")`` after 45 s elapsed transitions to ``advancing``
    or further to ``completed`` (depending on Plan 92-03 sequencing)."""
    import time

    base = 1_700_000_000.0
    fake_now = {"t": base}

    def fake_monotonic() -> float:
        return fake_now["t"]

    monkeypatch.setattr(time, "monotonic", fake_monotonic)

    rt = _runtime_at_awaiting_action()

    fake_now["t"] = base + 46.0  # past the 45 s floor
    rt.send("skip")
    assert rt.current_state.id in {"advancing", "completed"}, (
        "post-dwell skip should advance — state is "
        f"{rt.current_state.id!r}"
    )
