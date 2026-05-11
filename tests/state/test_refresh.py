# SPDX-License-Identifier: Apache-2.0
"""state_refresh_loop tests — drive _tick_once with mocked feature inputs.

The single-writer 10Hz loop is too thin to test as a unit on its own; instead
we exercise the extracted ``_tick_once`` helper deterministically and pin the
loop-level invariants (sleep cadence, error wrap) with one async test apiece.

Test strategy:
- Build a tiny real AudioBuffer + sine fixture so snapshot_features/energy_curve
  return non-zero values for the "audible" branches.
- Stub ControllerState + TrackInfo with unittest.mock.Mock to drive deck
  snapshots + track snapshots into the writer.
- Verify the free-function calls happen (not the old method calls).
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

from tests.audio.conftest import int16_sine
from vibemix.audio import AudioBuffer
from vibemix.state import MusicState, state_refresh_loop
from vibemix.state.refresh import _tick_once


def _audible_buf() -> AudioBuffer:
    """AudioBuffer with 6s of 440Hz sine at amplitude 0.5 — produces rms ~0.35
    (well above SILENT_RMS=0.012)."""
    buf = AudioBuffer(seconds=140.0, sr=16000)
    pcm = int16_sine(freq_hz=440.0, duration_sec=6.0, sample_rate=16000, amplitude=0.5)
    buf.push(pcm)
    return buf


def _silent_buf() -> AudioBuffer:
    """Empty buffer — RMS = 0, currently_loud = False."""
    return AudioBuffer(seconds=140.0, sr=16000)


def _ctrl_mock(connected: bool = True) -> MagicMock:
    """ControllerState stub with deck_snapshot + moves_since."""
    m = MagicMock()
    m.deck_snapshot.return_value = {
        "A": {"vol": 127, "play": True, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64},
        "B": {"vol": 0, "play": False, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64},
        "xfader": 0,  # full-A
        "connected": connected,
    }
    m.moves_since.return_value = []
    return m


def _track_mock(title: str = "") -> MagicMock:
    m = MagicMock()
    m.snapshot.return_value = {"title": title, "prev_title": "", "title_changed_at": 0.0}
    return m


# ---------- Import surface ----------


def test_state_refresh_loop_importable():
    from vibemix.state import state_refresh_loop  # noqa: F401


def test_state_refresh_loop_is_coroutine_function():
    import inspect

    assert inspect.iscoroutinefunction(state_refresh_loop)


# ---------- Free-function rewrite (the ONE structural deviation) ----------


def test_refresh_imports_free_functions_not_methods():
    """Verify the v4 method calls were rewritten as free-function calls in
    the executable code. The module docstring contains a "before/after" diff
    showing both shapes, so we AST-walk the module to inspect actual Call
    nodes — not raw text — to skip the docstring."""
    import ast

    import vibemix.state.refresh as r

    src = r.__file__
    with open(src) as f:
        tree = ast.parse(f.read(), filename=src)

    method_call_violations: list[str] = []
    free_call_hits: list[str] = []

    forbidden = {"snapshot_features", "energy_curve", "estimate_bpm", "long_arc_curve"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # Detect v4 method-call shape: audio_buf.METHOD(...).
            if isinstance(node.func, ast.Attribute):
                if (
                    isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "audio_buf"
                    and node.func.attr in forbidden
                ):
                    method_call_violations.append(node.func.attr)
            # Detect P3 free-function call shape: METHOD(audio_buf, ...).
            elif isinstance(node.func, ast.Name) and node.func.id in forbidden:
                if (
                    node.args
                    and isinstance(node.args[0], ast.Name)
                    and node.args[0].id == "audio_buf"
                ):
                    free_call_hits.append(node.func.id)

    assert method_call_violations == [], (
        f"v4 method-call shape still in code: {method_call_violations}"
    )
    # All four free-function rewrites must appear at least once.
    assert set(free_call_hits) == forbidden, (
        f"missing free-function rewrites: {forbidden - set(free_call_hits)}"
    )


# ---------- _tick_once: audio writes ----------


def test_tick_writes_audio_features():
    state = MusicState()
    buf = _audible_buf()
    out = _tick_once(
        state,
        buf,
        _ctrl_mock(),
        _track_mock(),
        now=1000.0,
        last_audible_high=0.0,
        last_audible_low=0.0,
        bpm_cache=0.0,
        last_bpm_at=0.0,
    )
    last_high, last_low, _bpm_cache, last_bpm_at = out

    # RMS should be > 0 (sine wave).
    assert state.rms > 0.0
    # Bands populated.
    assert set(state.bands.keys()) == {"sub", "low", "mid", "high"}
    # BPM was computed (currently_loud=True + now-last_bpm_at > 3.0).
    assert last_bpm_at == 1000.0
    # last_audible_high set on the rising edge.
    assert last_high == 1000.0
    assert last_low == 0.0


def test_tick_bpm_gate_skips_when_silent():
    """currently_loud = False → estimate_bpm NOT called → bpm_cache unchanged."""
    state = MusicState()
    buf = _silent_buf()
    out = _tick_once(
        state,
        buf,
        _ctrl_mock(),
        _track_mock(),
        now=1000.0,
        last_audible_high=0.0,
        last_audible_low=0.0,
        bpm_cache=42.0,  # pre-set
        last_bpm_at=0.0,
    )
    _, _, bpm_cache, last_bpm_at = out
    # bpm_cache and last_bpm_at unchanged (silent path skipped the call).
    assert bpm_cache == 42.0
    assert last_bpm_at == 0.0


def test_tick_bpm_gate_skips_when_within_3s_window():
    """last_bpm_at within 3.0s of now → skip estimate_bpm even if currently_loud."""
    state = MusicState()
    buf = _audible_buf()
    out = _tick_once(
        state,
        buf,
        _ctrl_mock(),
        _track_mock(),
        now=1002.5,  # 2.5s after last_bpm_at=1000.0
        last_audible_high=0.0,
        last_audible_low=0.0,
        bpm_cache=42.0,
        last_bpm_at=1000.0,
    )
    _, _, _bpm_cache, last_bpm_at = out
    # last_bpm_at unchanged — gate blocked the call.
    assert last_bpm_at == 1000.0


# ---------- Audible debouncing ----------


def test_tick_audible_debounce_up_edge():
    """Sustained loud for AUDIBLE_DEBOUNCE_SEC (0.6) → state.audible flips True."""
    state = MusicState()
    buf = _audible_buf()
    # Tick 1: first loud sample sets last_audible_high.
    out1 = _tick_once(
        state,
        buf,
        _ctrl_mock(),
        _track_mock(),
        now=1000.0,
        last_audible_high=0.0,
        last_audible_low=0.0,
        bpm_cache=0.0,
        last_bpm_at=0.0,
    )
    last_high1, _, _, _ = out1
    assert last_high1 == 1000.0
    assert state.audible is False  # not yet sustained

    # Tick 2: 0.7s later, still loud → exceeds 0.6s threshold → flips True.
    _tick_once(
        state,
        buf,
        _ctrl_mock(),
        _track_mock(),
        now=1000.7,
        last_audible_high=last_high1,
        last_audible_low=0.0,
        bpm_cache=130.0,
        last_bpm_at=1000.0,
    )
    assert state.audible is True


def test_tick_audible_debounce_down_edge():
    state = MusicState()
    state.audible = True  # pre-set
    buf = _silent_buf()
    # Tick 1: first silent sample sets last_audible_low.
    out1 = _tick_once(
        state,
        buf,
        _ctrl_mock(),
        _track_mock(),
        now=1000.0,
        last_audible_high=0.0,
        last_audible_low=0.0,
        bpm_cache=130.0,
        last_bpm_at=1000.0,
    )
    _, last_low1, _, _ = out1
    assert last_low1 == 1000.0
    assert state.audible is True  # SILENCE_DEBOUNCE_SEC = 1.2 not reached

    # Tick 2: 1.3s later → exceeds 1.2s → flips False.
    _tick_once(
        state,
        buf,
        _ctrl_mock(),
        _track_mock(),
        now=1001.3,
        last_audible_high=0.0,
        last_audible_low=last_low1,
        bpm_cache=130.0,
        last_bpm_at=1000.0,
    )
    assert state.audible is False


# ---------- Phase transition + phase_history ----------


def test_tick_appends_phase_history_on_transition():
    state = MusicState()
    state.audible = True
    state.phase = "groove"
    # AudioBuffer with energy curve that classifies as "peak":
    buf = AudioBuffer(seconds=140.0, sr=16000)
    # Push 12 seconds of a high-amplitude sine so energy_curve consistently
    # returns values ≥ 0.045 (peak classification).
    pcm = int16_sine(freq_hz=440.0, duration_sec=12.0, sample_rate=16000, amplitude=0.5)
    buf.push(pcm)

    _tick_once(
        state,
        buf,
        _ctrl_mock(),
        _track_mock(),
        now=1000.0,
        last_audible_high=999.0,  # already past 0.6s threshold
        last_audible_low=0.0,
        bpm_cache=130.0,
        last_bpm_at=999.0,
    )
    # Phase transitioned from "groove" → some other label (peak/build/drop/etc.).
    # state.phase_history appended a (now, prev, new) tuple.
    if state.phase != "groove":
        assert len(state.phase_history) == 1
        ts, prev, new = state.phase_history[0]
        assert ts == 1000.0
        assert prev == "groove"
        assert new == state.phase


def test_tick_trims_phase_history_to_last_6():
    state = MusicState()
    # Seed phase_history with 6 prior transitions.
    state.phase_history = [(i, "groove", f"x{i}") for i in range(6)]
    state.audible = True
    state.phase = "groove"
    buf = _audible_buf()
    _tick_once(
        state,
        buf,
        _ctrl_mock(),
        _track_mock(),
        now=1000.0,
        last_audible_high=999.0,
        last_audible_low=0.0,
        bpm_cache=130.0,
        last_bpm_at=999.0,
    )
    # If a new transition occurred, history was capped at 6.
    assert len(state.phase_history) <= 6


# ---------- Track history append gate ----------


def test_tick_appends_track_history_when_confidence_ge_05():
    state = MusicState()
    state.audible = True
    buf = _audible_buf()
    ctrl = _ctrl_mock()  # deck A play, xfader full-A → ("A", 1.0)
    track = _track_mock(title="X")  # title resolved
    _tick_once(
        state,
        buf,
        ctrl,
        track,
        now=1000.0,
        last_audible_high=999.0,
        last_audible_low=0.0,
        bpm_cache=130.0,
        last_bpm_at=999.0,
    )
    # derive_audible_track("X", "A", 1.0, audible=True) → ("X", clamp(1.0, 0.5, 0.85)) = ("X", 0.85)
    assert state.audible_track == "X"
    assert state.audible_track_confidence >= 0.5
    assert state.track_history == [(1000.0, "X")]


def test_tick_does_not_append_track_history_when_confidence_below_05():
    state = MusicState()
    state.audible = True
    buf = _audible_buf()
    # Controller silent → audible_deck="none" → derive_audible_track returns conf=0.3.
    ctrl = MagicMock()
    ctrl.deck_snapshot.return_value = {
        "A": {"vol": 0, "play": False, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64},
        "B": {"vol": 0, "play": False, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64},
        "xfader": 64,
        "connected": True,
    }
    ctrl.moves_since.return_value = []
    track = _track_mock(title="X")
    _tick_once(
        state,
        buf,
        ctrl,
        track,
        now=1000.0,
        last_audible_high=999.0,
        last_audible_low=0.0,
        bpm_cache=130.0,
        last_bpm_at=999.0,
    )
    # conf=0.3 < 0.5 → no track_history append.
    assert state.track_history == []


def test_tick_dedupes_same_title_in_track_history():
    state = MusicState()
    state.audible = True
    state.track_history = [(900.0, "X")]
    buf = _audible_buf()
    _tick_once(
        state,
        buf,
        _ctrl_mock(),
        _track_mock(title="X"),
        now=1000.0,
        last_audible_high=999.0,
        last_audible_low=0.0,
        bpm_cache=130.0,
        last_bpm_at=999.0,
    )
    # Same title as last entry → no append.
    assert state.track_history == [(900.0, "X")]


def test_tick_does_not_append_track_history_when_title_none():
    state = MusicState()
    state.audible = True
    buf = _audible_buf()
    _tick_once(
        state,
        buf,
        _ctrl_mock(),
        _track_mock(title=""),  # empty title → tt = None
        now=1000.0,
        last_audible_high=999.0,
        last_audible_low=0.0,
        bpm_cache=130.0,
        last_bpm_at=999.0,
    )
    assert state.track_history == []


# ---------- Audible deck + track wiring ----------


def test_tick_writes_audible_deck_and_track():
    state = MusicState()
    state.audible = True
    buf = _audible_buf()
    ctrl = _ctrl_mock()  # full-A
    track = _track_mock(title="Daft Punk - Around the World")
    _tick_once(
        state,
        buf,
        ctrl,
        track,
        now=1000.0,
        last_audible_high=999.0,
        last_audible_low=0.0,
        bpm_cache=130.0,
        last_bpm_at=999.0,
    )
    assert state.audible_deck == "A"
    assert state.deck_confidence > 0.5
    assert state.audible_track == "Daft Punk - Around the World"
    assert state.audible_track_confidence >= 0.5


def test_tick_writes_recent_moves():
    state = MusicState()
    buf = _audible_buf()
    ctrl = _ctrl_mock()
    ctrl.moves_since.return_value = [(2.0, "A_play→ON"), (5.0, "xfader→full-A")]
    _tick_once(
        state,
        buf,
        ctrl,
        _track_mock(),
        now=1000.0,
        last_audible_high=999.0,
        last_audible_low=0.0,
        bpm_cache=130.0,
        last_bpm_at=999.0,
    )
    assert state.recent_moves == [(2.0, "A_play→ON"), (5.0, "xfader→full-A")]
    # moves_since was called with now - 12.0.
    ctrl.moves_since.assert_called_with(988.0)


# ---------- Single-writer lock ----------


def test_tick_acquires_state_lock(mocker):
    state = MusicState()
    # Wrap _lock to count enter/exit.
    real_lock = state._lock
    enter_calls = []
    exit_calls = []

    class CountingLock:
        def __enter__(self):
            enter_calls.append(True)
            return real_lock.__enter__()

        def __exit__(self, *args):
            exit_calls.append(True)
            return real_lock.__exit__(*args)

    state._lock = CountingLock()

    buf = _audible_buf()
    _tick_once(
        state,
        buf,
        _ctrl_mock(),
        _track_mock(),
        now=1000.0,
        last_audible_high=0.0,
        last_audible_low=0.0,
        bpm_cache=0.0,
        last_bpm_at=0.0,
    )
    # Exactly one enter / exit per tick.
    assert len(enter_calls) == 1
    assert len(exit_calls) == 1


# ---------- Loop-level: sleep cadence + error wrap ----------
# pytest-asyncio is NOT a project dep (Phase 2 didn't add it); use asyncio.run
# directly inside sync test functions for the two async loop-level invariants.


def test_state_refresh_loop_sleeps_at_10hz(mocker):
    """Pin the v4:1659 ``await asyncio.sleep(0.1)`` cadence."""
    state = MusicState()
    buf = _audible_buf()
    stop = asyncio.Event()
    calls: list[float] = []

    original_sleep = asyncio.sleep

    async def capturing_sleep(delay):
        calls.append(delay)
        stop.set()  # exit after the very first sleep
        await original_sleep(0)

    mocker.patch("vibemix.state.refresh.asyncio.sleep", side_effect=capturing_sleep)

    asyncio.run(state_refresh_loop(state, buf, _ctrl_mock(), _track_mock(), stop))
    assert calls[0] == 0.1


def test_state_refresh_loop_swallows_tick_exceptions(mocker, capsys):
    """v4:1750-1751 — error wrap. Loop continues after exception, error
    written to stderr with the v4 prefix."""
    state = MusicState()
    buf = _audible_buf()
    stop = asyncio.Event()

    mocker.patch("vibemix.state.refresh._tick_once", side_effect=RuntimeError("boom"))

    original_sleep = asyncio.sleep
    iterations = [0]

    async def short_sleep(delay):
        iterations[0] += 1
        # Iteration 1: before-tick sleep. Iteration 2: next-cycle sleep after
        # the exception was caught + logged. Stop after seeing both.
        if iterations[0] >= 2:
            stop.set()
        await original_sleep(0)

    mocker.patch("vibemix.state.refresh.asyncio.sleep", side_effect=short_sleep)

    # Must NOT raise — error caught and printed.
    asyncio.run(state_refresh_loop(state, buf, _ctrl_mock(), _track_mock(), stop))
    err = capsys.readouterr().err
    assert "[state refresh err] boom" in err
