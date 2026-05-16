# SPDX-License-Identifier: Apache-2.0
"""Phase 43 Plan 09 — Demo-mode deterministic sequence pinning.

VIS-09: the hero-demo capture day requires bit-identical event timing
across takes. These tests pin the load-bearing anchors per CONTEXT
§VIS-09: kick_swap @ 2:33 (153.0s), layer_drop @ 4:50 (290.0s),
track_end @ 6:00 (360.0s). Total = 30 events; sequence is monotonic
by timestamp.

Filler-event timings are NOT pinned (CONTEXT calls them flexible);
only the count + anchor times are load-bearing.
"""

from __future__ import annotations

import pytest

# Plan 43-09 deviation R1: PLAN sample used `from src.vibemix...` but
# the project convention (and every test in tests/runtime/) imports from
# the installed wheel root `vibemix.*`. See test_diag.py for precedent.
from vibemix.runtime.demo_mode import (
    DEMO_SEQUENCE,
    DemoEvent,
    DemoState,
    load_sequence,
    reset,
    step,
)


# ---------------------------------------------------------------------------
# Anchor constants (load-bearing — pinned by tests below)
# ---------------------------------------------------------------------------

KICK_SWAP_TS = 153.0   # 2:33
LAYER_DROP_TS = 290.0  # 4:50
TRACK_END_TS = 360.0   # 6:00
SEQUENCE_LENGTH = 30


@pytest.fixture(autouse=True)
def _reset_between_tests():
    """Each test starts with the cursor at step 0 (module-level state)."""
    reset()
    yield
    reset()


# ---------------------------------------------------------------------------
# Test 1 — Public API importable
# ---------------------------------------------------------------------------


def test_public_api_importable():
    """`from vibemix.runtime.demo_mode import DEMO_SEQUENCE, load_sequence,
    step, reset` must succeed without error (already exercised by the
    top-of-file import; this test pins the public surface)."""
    assert DEMO_SEQUENCE is not None
    assert callable(load_sequence)
    assert callable(step)
    assert callable(reset)


# ---------------------------------------------------------------------------
# Test 2 — Sequence length is the deterministic 30
# ---------------------------------------------------------------------------


def test_sequence_has_30_events():
    """CONTEXT §VIS-09: '30-event sequence'. Load-bearing."""
    assert len(DEMO_SEQUENCE) == SEQUENCE_LENGTH


# ---------------------------------------------------------------------------
# Test 3 — kick_swap anchor at 2:33 (153.0s)
# ---------------------------------------------------------------------------


def test_kick_swap_at_153s():
    """CONTEXT §VIS-09: '2:33 kick swap event (mascot celebrate trigger)'."""
    kick_swaps = [
        e for e in DEMO_SEQUENCE
        if e.kind == "kick_swap" and e.timestamp_s == KICK_SWAP_TS
    ]
    assert len(kick_swaps) == 1, (
        f"Expected exactly one kick_swap event at {KICK_SWAP_TS}s; "
        f"found {len(kick_swaps)}"
    )


# ---------------------------------------------------------------------------
# Test 4 — layer_drop anchor at 4:50 (290.0s)
# ---------------------------------------------------------------------------


def test_layer_drop_at_290s():
    """CONTEXT §VIS-09: '4:50 layer drop event (mascot teacher line trigger)'."""
    layer_drops = [
        e for e in DEMO_SEQUENCE
        if e.kind == "layer_drop" and e.timestamp_s == LAYER_DROP_TS
    ]
    assert len(layer_drops) == 1, (
        f"Expected exactly one layer_drop event at {LAYER_DROP_TS}s; "
        f"found {len(layer_drops)}"
    )


# ---------------------------------------------------------------------------
# Test 5 — Sequence ends at 6:00 (360.0s) with track_end
# ---------------------------------------------------------------------------


def test_sequence_ends_at_360s_with_track_end():
    """CONTEXT §VIS-09: '6:00 end'. Last event must be track_end at 360s."""
    last = DEMO_SEQUENCE[-1]
    assert last.timestamp_s == TRACK_END_TS, (
        f"Last event timestamp must be {TRACK_END_TS}s, got {last.timestamp_s}s"
    )
    assert last.kind == "track_end", (
        f"Last event kind must be 'track_end', got {last.kind!r}"
    )


# ---------------------------------------------------------------------------
# Test 6 — Monotonic timestamps (sorted ascending)
# ---------------------------------------------------------------------------


def test_sequence_monotonic_by_timestamp():
    """A demo sequence with out-of-order timestamps would replay wrong on
    capture day. Enforce monotonic invariant."""
    timestamps = [e.timestamp_s for e in DEMO_SEQUENCE]
    assert timestamps == sorted(timestamps), (
        "DEMO_SEQUENCE timestamps must be sorted ascending"
    )


# ---------------------------------------------------------------------------
# Test 7 — load_sequence() returns fresh state at step 0
# ---------------------------------------------------------------------------


def test_load_sequence_returns_fresh_state():
    """`load_sequence()` is the entry point Francesco's take workflow calls
    before each take — must return a fresh state object cursor=0."""
    state = load_sequence()
    assert isinstance(state, DemoState)
    assert state.step_index == 0


# ---------------------------------------------------------------------------
# Test 8 — step() advances cursor; 30 calls exhaust; 31st returns None
# ---------------------------------------------------------------------------


def test_step_advances_and_exhausts():
    """`step()` advances the cursor; after 30 calls the sequence is
    exhausted and subsequent calls return None (sentinel — NOT raise)."""
    load_sequence()
    for i in range(SEQUENCE_LENGTH):
        ev = step()
        assert ev is not None, f"step #{i+1} unexpectedly returned None"
        assert isinstance(ev, DemoEvent), (
            f"step #{i+1} returned {type(ev).__name__}, expected DemoEvent"
        )

    # 31st call exhausts → None sentinel
    assert step() is None, "step() after exhaustion must return None"
    # Repeat call still None (idempotent)
    assert step() is None


# ---------------------------------------------------------------------------
# Test 9 — reset() returns cursor to step 0
# ---------------------------------------------------------------------------


def test_reset_returns_cursor_to_zero():
    """`vibemix --demo-mode reset` is Francesco's per-take call — must
    return the sequencer to step 0 for repeatable takes."""
    load_sequence()
    # Advance partway
    for _ in range(5):
        step()
    # Reset
    reset()
    # Next step should be the first event again
    first = step()
    assert first is not None
    assert first.timestamp_s == DEMO_SEQUENCE[0].timestamp_s
    assert first.kind == DEMO_SEQUENCE[0].kind


# ---------------------------------------------------------------------------
# Test 10 — Step-index-driven traversal returns events in DEMO_SEQUENCE order;
# kick_swap arrives at the index it occupies in the sequence (not "when wall
# clock crosses 153s"). The sequencer is step-index driven per implementation.
# ---------------------------------------------------------------------------


def test_step_traversal_yields_kick_swap_in_sequence_order():
    """Plan 43-09 Test 10 — implementation chooses step-index-driven traversal
    (vs timestamp-driven). Pin: stepping through the sequence yields the
    kick_swap event at its index, before layer_drop, before track_end."""
    load_sequence()
    seen_kinds: list[str] = []
    seen_kick_swap_ts: float | None = None
    seen_layer_drop_ts: float | None = None
    seen_track_end_ts: float | None = None

    while True:
        ev = step()
        if ev is None:
            break
        seen_kinds.append(ev.kind)
        if ev.kind == "kick_swap":
            seen_kick_swap_ts = ev.timestamp_s
        elif ev.kind == "layer_drop":
            seen_layer_drop_ts = ev.timestamp_s
        elif ev.kind == "track_end":
            seen_track_end_ts = ev.timestamp_s

    # All three anchors observed at the expected timestamps
    assert seen_kick_swap_ts == KICK_SWAP_TS
    assert seen_layer_drop_ts == LAYER_DROP_TS
    assert seen_track_end_ts == TRACK_END_TS

    # Anchor order: track_start → ... → kick_swap → ... → layer_drop → ... → track_end
    kick_idx = seen_kinds.index("kick_swap")
    drop_idx = seen_kinds.index("layer_drop")
    end_idx = seen_kinds.index("track_end")
    assert kick_idx < drop_idx < end_idx, (
        f"Anchor ordering broken: kick_swap@{kick_idx}, "
        f"layer_drop@{drop_idx}, track_end@{end_idx}"
    )
    # Track must start at the very first step
    assert seen_kinds[0] == "track_start"
