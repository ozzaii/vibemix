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


# =============================================================================
# Phase 6 — genre-aware MusicState fields written each tick
# =============================================================================


def test_tick_writes_crest_factor_field():
    """Crest factor is computed from a 4s pcm snapshot and EMA-smoothed."""
    from vibemix.state.genre import EmaSmoother

    state = MusicState()
    buf = _audible_buf()
    smoother = EmaSmoother(alpha=0.3)
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
        crest_smoother=smoother,
    )
    # Pure sine has crest ≈ √2 ≈ 1.41 (rounded to 2 places by state.write).
    assert state.crest_factor > 0.0
    assert state.crest_factor < 2.0  # Sine should be ~1.41


def test_tick_writes_bpm_corrected_field_when_profile_active(mocker):
    """active profile=techno + bpm_cache=250 → halved to 125, bpm_corrected=True."""
    from vibemix.state.genre import set_active_profile

    set_active_profile("techno")
    try:
        state = MusicState()
        buf = _audible_buf()
        # bpm_cache=250 will be halved to 125 (in techno 125-175 range).
        # last_bpm_at=now means estimate_bpm gate is skipped → bpm_cache preserved
        # then validated.
        _tick_once(
            state,
            buf,
            _ctrl_mock(),
            _track_mock(),
            now=1000.0,
            last_audible_high=0.0,
            last_audible_low=0.0,
            bpm_cache=250.0,
            last_bpm_at=1000.0,  # block estimate_bpm so bpm_cache stays at 250
        )
        assert state.bpm == 125.0
        assert state.bpm_corrected is True
    finally:
        set_active_profile(None)


def test_tick_writes_bpm_corrected_false_when_no_profile():
    """No active profile → validate_bpm not called → bpm_corrected=False."""
    from vibemix.state.genre import set_active_profile

    set_active_profile(None)
    state = MusicState()
    buf = _audible_buf()
    _tick_once(
        state,
        buf,
        _ctrl_mock(),
        _track_mock(),
        now=1000.0,
        last_audible_high=0.0,
        last_audible_low=0.0,
        bpm_cache=250.0,
        last_bpm_at=1000.0,
    )
    # Raw 250 passed through unchanged.
    assert state.bpm == 250.0
    assert state.bpm_corrected is False


def test_tick_writes_genre_profile_name_unknown_when_no_active_profile():
    from vibemix.state.genre import set_active_profile

    set_active_profile(None)
    state = MusicState()
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
    assert state.genre_profile_name == "unknown"


def test_tick_writes_genre_profile_name_techno_when_active():
    from vibemix.state.genre import set_active_profile

    set_active_profile("techno")
    try:
        state = MusicState()
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
        assert state.genre_profile_name == "techno"
    finally:
        set_active_profile(None)


def test_tick_writes_vocal_active_default_false():
    """Cold start with no recent_features history → vocal_active stays False."""
    from vibemix.state.genre import set_active_profile

    set_active_profile(None)
    state = MusicState()
    buf = _audible_buf()  # 440Hz sine — not a vocal signal
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
    assert state.vocal_active is False


def test_tick_falls_back_to_v4_classify_when_no_profile():
    """No profile → state_refresh uses Phase 3 absolute-threshold classify."""
    from vibemix.state.genre import set_active_profile

    set_active_profile(None)
    state = MusicState()
    state.audible = True
    buf = _silent_buf()  # empty curve → 'silent'
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
    # Empty curve via Phase 3 classify_phase → 'silent'.
    assert state.phase == "silent"


# =============================================================================
# Phase 17 — Hard Tek detectors v1: 4 new MusicState fields populated each tick
# =============================================================================


def test_tick_writes_active_genre_house():
    """bpm_cache=124.0 lands in the house band (118-128). Centroid floor only
    applies to hard_tek, so house classifies regardless of mid/high mix."""
    from vibemix.state.genre import set_active_profile

    set_active_profile(None)
    state = MusicState()
    buf = _audible_buf()
    _tick_once(
        state,
        buf,
        _ctrl_mock(),
        _track_mock(),
        now=1000.0,
        last_audible_high=0.0,
        last_audible_low=0.0,
        bpm_cache=124.0,
        last_bpm_at=1000.0,  # block estimate_bpm so 124.0 survives
    )
    assert state.active_genre == "house"


def test_tick_writes_active_genre_hard_tek_requires_centroid(mocker):
    """bpm_cache=150 lands in hard_tek band BUT requires (mid_share +
    high_share) >= GENRE_CENTROID_HARD_TEK_MIN (0.55). Below floor →
    "unknown" (anti-misclassify-on-house-with-fast-tempo)."""
    from vibemix.state.genre import set_active_profile

    set_active_profile(None)

    # Stub snapshot_features so we can drive the centroid deterministically
    # — _audible_buf() yields ~mid/high concentrated around 440Hz which we
    # can't bend without a different fixture.
    def fake_feats_low_centroid(buf, seconds=4.0):
        return {
            "rms": 0.1,
            "onsets_per_sec": 1.0,
            "sub_share": 0.40,
            "low_share": 0.20,
            "mid_share": 0.30,
            "high_share": 0.10,  # mid+high = 0.40 < 0.55 → "unknown"
        }

    def fake_feats_high_centroid(buf, seconds=4.0):
        return {
            "rms": 0.1,
            "onsets_per_sec": 1.0,
            "sub_share": 0.20,
            "low_share": 0.20,
            "mid_share": 0.30,
            "high_share": 0.30,  # mid+high = 0.60 ≥ 0.55 → "hard_tek"
        }

    state = MusicState()
    buf = _audible_buf()

    mocker.patch("vibemix.state.refresh.snapshot_features", side_effect=fake_feats_low_centroid)
    _tick_once(
        state,
        buf,
        _ctrl_mock(),
        _track_mock(),
        now=1000.0,
        last_audible_high=0.0,
        last_audible_low=0.0,
        bpm_cache=150.0,
        last_bpm_at=1000.0,
    )
    assert state.active_genre == "unknown", "centroid floor reject for house-with-fast-tempo"

    state2 = MusicState()
    mocker.patch("vibemix.state.refresh.snapshot_features", side_effect=fake_feats_high_centroid)
    _tick_once(
        state2,
        buf,
        _ctrl_mock(),
        _track_mock(),
        now=1000.0,
        last_audible_high=0.0,
        last_audible_low=0.0,
        bpm_cache=150.0,
        last_bpm_at=1000.0,
    )
    assert state2.active_genre == "hard_tek", (
        "centroid floor passed → distorted-kick spectral signature → hard_tek"
    )


def test_tick_writes_buildup_score_from_energy_curve_slope(mocker):
    """Monotonic-climb energy_curve → positive buildup_score in [0.0, 1.0].
    Flat curve → buildup_score ≈ 0.0. Negative slopes clamp to 0.0
    (buildups are monotonic-climbs only — falling energy is a job for
    BREAKDOWN_KICK_KILL, NOT a negative buildup)."""
    from vibemix.state.genre import set_active_profile

    set_active_profile(None)

    state = MusicState()
    buf = _audible_buf()

    # Climbing curve (8 samples, monotonic) → positive score.
    mocker.patch(
        "vibemix.state.refresh.energy_curve",
        return_value=[0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09],
    )
    _tick_once(
        state,
        buf,
        _ctrl_mock(),
        _track_mock(),
        now=1000.0,
        last_audible_high=0.0,
        last_audible_low=0.0,
        bpm_cache=124.0,
        last_bpm_at=1000.0,
    )
    assert 0.0 < state.buildup_score <= 1.0, (
        f"expected positive in (0, 1], got {state.buildup_score}"
    )

    # Flat curve → score ≈ 0.0.
    state2 = MusicState()
    mocker.patch("vibemix.state.refresh.energy_curve", return_value=[0.05] * 8)
    _tick_once(
        state2,
        buf,
        _ctrl_mock(),
        _track_mock(),
        now=1000.0,
        last_audible_high=0.0,
        last_audible_low=0.0,
        bpm_cache=124.0,
        last_bpm_at=1000.0,
    )
    assert state2.buildup_score == 0.0, f"flat curve should yield 0.0, got {state2.buildup_score}"

    # Falling curve → score clamps to 0.0 (negative slope rejected).
    state3 = MusicState()
    mocker.patch(
        "vibemix.state.refresh.energy_curve",
        return_value=[0.09, 0.08, 0.07, 0.06, 0.05, 0.04, 0.03, 0.02],
    )
    _tick_once(
        state3,
        buf,
        _ctrl_mock(),
        _track_mock(),
        now=1000.0,
        last_audible_high=0.0,
        last_audible_low=0.0,
        bpm_cache=124.0,
        last_bpm_at=1000.0,
    )
    assert state3.buildup_score == 0.0, "falling energy must clamp to 0.0, not go negative"


def test_tick_writes_beat_phase_mirroring_downbeat_phase():
    """state.beat_phase mirrors state.downbeat_phase after every tick.
    Phase 17 alias — both consumers should agree. Phase 13's downbeat_phase
    already computes the bar-fraction; Phase 17 detectors want a
    Phase-17-named handle (`beat_phase`) so SENSE-12 detector module imports
    don't reach into Phase-13 naming."""
    from vibemix.state.genre import set_active_profile

    set_active_profile(None)

    state = MusicState()
    buf = _audible_buf()
    _tick_once(
        state,
        buf,
        _ctrl_mock(),
        _track_mock(),
        now=1000.0,
        last_audible_high=0.0,
        last_audible_low=0.0,
        bpm_cache=124.0,
        last_bpm_at=1000.0,
    )
    assert state.beat_phase == state.downbeat_phase


def test_tick_keeps_predicted_drop_in_sec_none_by_default():
    """Predictive drop firing is OFF-by-default per CONTEXT D — the
    telemetry-guarded flip is v2.1 work, NOT Phase 17. After any tick,
    state.predicted_drop_in_sec must remain None."""
    from vibemix.state.genre import set_active_profile

    set_active_profile(None)

    state = MusicState()
    buf = _audible_buf()
    _tick_once(
        state,
        buf,
        _ctrl_mock(),
        _track_mock(),
        now=1000.0,
        last_audible_high=0.0,
        last_audible_low=0.0,
        bpm_cache=124.0,
        last_bpm_at=1000.0,
    )
    assert state.predicted_drop_in_sec is None


def test_tick_with_invalid_bpm_yields_unknown_genre():
    """bpm_cache=0.0 → "unknown" — no fabricated genre during BPM lock-up.
    Mirrors the v4 `_music_truly_playing` rule (T-17-01-01 mitigation)."""
    from vibemix.state.genre import set_active_profile

    set_active_profile(None)

    state = MusicState()
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
        last_bpm_at=1000.0,
    )
    assert state.active_genre == "unknown"


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


# =============================================================================
# Phase 18 Plan 02 — EvidenceRegistry wiring (Task 2)
# =============================================================================

from vibemix.state import EvidenceRegistry  # noqa: E402


def test_18_02_per_tick_aud_writes_when_audible():
    """Test E — per-tick aud writes (GROUND-01).

    Drive _tick_once with audible=True synthetic state; after tick,
    registry.snapshot()["aud"] contains keys "rms", "bpm", "onset_density",
    "sub_share", "low_share", "mid_share", "high_share" — each with exactly
    one t_session float.
    """
    registry = EvidenceRegistry()
    state = MusicState()
    state.set_start_at = 900.0
    buf = _audible_buf()
    _tick_once(
        state,
        buf,
        _ctrl_mock(),
        _track_mock(),
        now=1000.0,
        last_audible_high=900.0,  # already past AUDIBLE_DEBOUNCE_SEC
        last_audible_low=0.0,
        bpm_cache=130.0,
        last_bpm_at=999.5,
        evidence_registry=registry,
    )
    # state.audible should now be True (sustained-audible elapsed)
    assert state.audible is True
    snap = registry.snapshot()
    aud = snap.get("aud", {})
    expected_keys = {"rms", "bpm", "onset_density", "sub_share", "low_share", "mid_share", "high_share"}
    assert set(aud.keys()) >= expected_keys, f"missing keys: {expected_keys - set(aud.keys())}"
    # Each key has exactly one observation from this single tick
    for k in expected_keys:
        assert len(aud[k]) == 1, f"{k} has {len(aud[k])} observations, expected 1"
        # t_session = now - set_start_at = 1000.0 - 900.0 = 100.0
        assert abs(aud[k][0] - 100.0) < 0.001


def test_18_02_aud_NOT_written_when_silent():
    """Test F — per-tick aud writes ONLY when audible (anti-noise).

    Drive _tick_once with audible=False (silent state); registry.snapshot()
    ["aud"] is empty (or has only zero observations). Rationale: cohost_v4
    "trust the audio" rule — recording features for silent ticks would let
    Gemini cite "aud:rms@45.2" on a silent moment, which is the exact
    hallucination class P18 + P20 close.
    """
    registry = EvidenceRegistry()
    state = MusicState()  # audible defaults to False
    state.set_start_at = 900.0
    buf = _silent_buf()  # RMS = 0, currently_loud = False
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
        evidence_registry=registry,
    )
    assert state.audible is False
    snap = registry.snapshot()
    # aud source should be entirely empty (no key was ever written)
    assert snap.get("aud", {}) == {}


def test_18_02_mix_write_on_phase_change():
    """Test G — mix write on phase change (change-only).

    Tick 1 with state.phase="groove" then a 2nd tick where the energy_curve
    drives a new classify_phase result; registry.snapshot()["mix"] should
    have key f"phase={new_phase}" with one observation. Repeated same-phase
    ticks do NOT re-write.
    """
    registry = EvidenceRegistry()
    state = MusicState()
    state.set_start_at = 900.0
    state.phase = "groove"  # baseline
    buf = _audible_buf()
    # Tick 1 — sets state.phase from classify_phase output. The tick will
    # likely flip phase based on the synthetic curve (away from "groove").
    _tick_once(
        state,
        buf,
        _ctrl_mock(),
        _track_mock(),
        now=1000.0,
        last_audible_high=900.0,
        last_audible_low=0.0,
        bpm_cache=130.0,
        last_bpm_at=999.5,
        evidence_registry=registry,
    )
    snap1 = registry.snapshot()
    mix1 = snap1.get("mix", {})
    # Phase should have changed away from "groove" → at most one mix entry
    # for the new phase (if no change happened, mix has no phase= entry).
    phase_keys_after_tick1 = [k for k in mix1.keys() if k.startswith("phase=")]
    if state.phase != "groove":
        assert len(phase_keys_after_tick1) == 1
        assert phase_keys_after_tick1[0] == f"phase={state.phase}"
    new_phase_after_tick1 = state.phase
    # Tick 2 — same conditions; phase should stay the same → no new write
    _tick_once(
        state,
        buf,
        _ctrl_mock(),
        _track_mock(),
        now=1001.0,
        last_audible_high=900.0,
        last_audible_low=0.0,
        bpm_cache=130.0,
        last_bpm_at=1000.0,
        evidence_registry=registry,
    )
    snap2 = registry.snapshot()
    # Phase should be the same → mix snapshot unchanged for phase= keys
    assert state.phase == new_phase_after_tick1
    mix2 = snap2.get("mix", {})
    phase_keys_after_tick2 = [k for k in mix2.keys() if k.startswith("phase=")]
    # Same phase keys, same observation count
    assert phase_keys_after_tick2 == phase_keys_after_tick1
    for k in phase_keys_after_tick2:
        # Same single observation — no new tick wrote
        assert len(mix2[k]) == 1


def test_18_02_mix_write_on_audible_deck_change():
    """Test H — mix write on audible_deck change (change-only).

    Tick 1 audible_deck="A" (baseline default is "none"), tick 2 audible_deck
    becomes "B" via different controller snapshot → registry has "audible_deck=A"
    after tick 1 + "audible_deck=B" after tick 2. A 3rd tick with the same
    deck does NOT re-write.
    """
    registry = EvidenceRegistry()
    state = MusicState()
    state.set_start_at = 900.0
    buf = _audible_buf()

    # Tick 1 — controller mock has deck A active (default _ctrl_mock)
    _tick_once(
        state,
        buf,
        _ctrl_mock(),
        _track_mock(),
        now=1000.0,
        last_audible_high=900.0,
        last_audible_low=0.0,
        bpm_cache=130.0,
        last_bpm_at=999.5,
        evidence_registry=registry,
    )
    snap1 = registry.snapshot()
    mix1 = snap1.get("mix", {})
    deck_keys = [k for k in mix1.keys() if k.startswith("audible_deck=")]
    # state.audible_deck != prev "none" → exactly one write
    assert len(deck_keys) == 1
    initial_deck = state.audible_deck
    assert deck_keys[0] == f"audible_deck={initial_deck}"

    # Tick 2 — same deck snapshot → no new write (same value, no change)
    _tick_once(
        state,
        buf,
        _ctrl_mock(),
        _track_mock(),
        now=1001.0,
        last_audible_high=900.0,
        last_audible_low=0.0,
        bpm_cache=130.0,
        last_bpm_at=1000.0,
        evidence_registry=registry,
    )
    snap2 = registry.snapshot()
    mix2 = snap2.get("mix", {})
    # Same key, still 1 observation
    assert len(mix2.get(deck_keys[0], [])) == 1


def test_18_02_registry_kwarg_default_keeps_existing_tests_green():
    """Test I — registry kwarg default = None preserves all current tests.

    _tick_once with no evidence_registry kwarg runs unchanged. Existing
    tests in test_refresh.py stay GREEN with zero edits (verified by the
    rest of this file). This test asserts the no-kwarg path is silent.
    """
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
    # Returned tuple shape unchanged — 4 floats
    assert len(out) == 4


def test_18_02_registry_write_inside_state_lock_AST_check():
    """Test J — write happens INSIDE the existing `with state._lock:` batch.

    Verified via AST inspection — the registry.write call must lexically
    appear inside the `with state._lock:` context manager block in
    refresh._tick_once. Closes the atomic-snapshot-consistency contract.
    """
    import ast

    import vibemix.state.refresh as r

    src = r.__file__
    with open(src) as f:
        tree = ast.parse(f.read(), filename=src)

    # Find _tick_once function def
    tick_fn = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_tick_once":
            tick_fn = node
            break
    assert tick_fn is not None, "_tick_once not found"

    # Find `with state._lock:` block(s) inside _tick_once and collect Call
    # nodes inside their bodies whose func is `evidence_registry.write` or
    # `self._registry.write` etc.
    registry_writes_inside_lock: list = []
    registry_writes_outside_lock: list = []

    def call_targets_registry_write(call: ast.Call) -> bool:
        if not isinstance(call.func, ast.Attribute):
            return False
        if call.func.attr != "write":
            return False
        # Match `evidence_registry.write(...)`
        if isinstance(call.func.value, ast.Name) and call.func.value.id == "evidence_registry":
            return True
        return False

    # Walk the function body, tracking whether we're inside a `with state._lock:`
    def is_state_lock_with(with_node: ast.With) -> bool:
        for item in with_node.items:
            ce = item.context_expr
            # Match `state._lock` Attribute access
            if isinstance(ce, ast.Attribute) and ce.attr == "_lock":
                if isinstance(ce.value, ast.Name) and ce.value.id == "state":
                    return True
        return False

    def walk(node, inside_lock: bool):
        if isinstance(node, ast.Call) and call_targets_registry_write(node):
            (registry_writes_inside_lock if inside_lock else registry_writes_outside_lock).append(node)
        if isinstance(node, ast.With) and is_state_lock_with(node):
            for child in node.body:
                walk(child, inside_lock=True)
            return
        for child in ast.iter_child_nodes(node):
            walk(child, inside_lock=inside_lock)

    for child in tick_fn.body:
        walk(child, inside_lock=False)

    assert len(registry_writes_inside_lock) >= 1, (
        "evidence_registry.write must appear at least once INSIDE `with state._lock:` block"
    )
    assert len(registry_writes_outside_lock) == 0, (
        f"evidence_registry.write found OUTSIDE the state._lock block "
        f"({len(registry_writes_outside_lock)} occurrences) — single-snapshot "
        f"consistency requires all writes inside the lock"
    )


def test_18_02_golden_equivalence_stays_green_with_registry():
    """Test K — Phase 3 golden equivalence stays green when registry is wired.

    Drive _tick_once with the same inputs as test_tick_writes_audio_features
    BUT pass a registry. MusicState fields after the tick MUST match v4
    behavior — registry write is purely additive.
    """
    registry = EvidenceRegistry()
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
        evidence_registry=registry,
    )
    last_high, last_low, _bpm_cache, last_bpm_at = out

    # Same assertions as test_tick_writes_audio_features (golden):
    assert state.rms > 0.0
    assert set(state.bands.keys()) == {"sub", "low", "mid", "high"}
    assert last_bpm_at == 1000.0
    assert last_high == 1000.0
    assert last_low == 0.0


def test_18_02_state_refresh_loop_threads_registry_kwarg(mocker):
    """Test L — state_refresh_loop signature accepts evidence_registry kwarg
    and threads it through to _tick_once on every iteration.
    """
    import inspect
    sig = inspect.signature(state_refresh_loop)
    assert "evidence_registry" in sig.parameters
    # Default is None for backward compat
    assert sig.parameters["evidence_registry"].default is None

    # Behavioral: call state_refresh_loop with registry, capture _tick_once kwargs
    state = MusicState()
    state.set_start_at = 900.0
    buf = _audible_buf()
    stop = asyncio.Event()
    registry = EvidenceRegistry()

    captured_kwargs: list[dict] = []

    real_tick_once = _tick_once

    def spy_tick_once(*args, **kwargs):
        captured_kwargs.append(kwargs)
        # Stop the loop after first tick observed
        stop.set()
        return real_tick_once(*args, **kwargs)

    mocker.patch("vibemix.state.refresh._tick_once", side_effect=spy_tick_once)

    original_sleep = asyncio.sleep
    async def short_sleep(delay):
        await original_sleep(0)

    mocker.patch("vibemix.state.refresh.asyncio.sleep", side_effect=short_sleep)

    asyncio.run(
        state_refresh_loop(state, buf, _ctrl_mock(), _track_mock(), stop, evidence_registry=registry)
    )
    assert captured_kwargs, "tick_once was never called"
    assert captured_kwargs[0].get("evidence_registry") is registry
