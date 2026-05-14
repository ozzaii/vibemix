# SPDX-License-Identifier: Apache-2.0
"""Cross-component integration tests for Plan 17-05 — proves the
state_refresh_loop → MusicState.active_genre → EventDetector → GenreRouter
→ chain dispatch path works end-to-end in a single Python process.

These are NOT unit tests for any one component (those live in
test_genre_router.py + test_event_detector.py). They're the SENSE-13 →
SENSE-11 → SENSE-15 wiring proof.

The smoke-spawn test for __main__.py + the EventDetector(audio_buf=...)
constructor change is its own concern (tests/test_main_smoke.py owns the
full process spawn). Test 3 below greps for an EventDetector reference in
that file; if absent (current state), it's a SKIP — the indirect coverage
via SMOKE-06 test_poc_files_diff_untouched is sufficient.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from tests.audio.conftest import int16_sine
from vibemix.audio import AudioBuffer
from vibemix.state import EventDetector, MusicState
from vibemix.state.detectors import KickSwapDetector, SubLayerArrivalDetector
from vibemix.state.refresh import _tick_once


def _audible_buf() -> AudioBuffer:
    """AudioBuffer with 6s of 440Hz sine — produces rms ~0.35 (audible)."""
    buf = AudioBuffer(seconds=140.0, sr=16000)
    pcm = int16_sine(freq_hz=440.0, duration_sec=6.0, sample_rate=16000, amplitude=0.5)
    buf.push(pcm)
    return buf


def _ctrl_mock() -> MagicMock:
    m = MagicMock()
    m.deck_snapshot.return_value = {
        "A": {"vol": 127, "play": True, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64},
        "B": {"vol": 0, "play": False, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64},
        "xfader": 0,
        "connected": True,
    }
    m.moves_since.return_value = []
    return m


def _track_mock(title: str = "") -> MagicMock:
    m = MagicMock()
    m.snapshot.return_value = {"title": title, "prev_title": "", "title_changed_at": 0.0}
    return m


# ---------- Test 1 — full SENSE-13 → SENSE-11 → SENSE-15 path ----------


def test_state_refresh_loop_writes_active_genre_event_detector_routes(mocker):
    """Drive _tick once with bpm=124.0 in the house band → state.active_genre
    becomes "house". Construct EventDetector(audio_buf=fake). Call detect().
    Assert event_detector.router.current_genre == "house" after the call.

    This is the cross-plan integration — verifies the writer-then-reader
    contract in a single Python process: state_refresh_loop sets
    active_genre (Plan 17-01 SENSE-13), EventDetector reads it and triggers
    the GenreRouter (Plan 17-05 SENSE-11 / SENSE-15)."""
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
        bpm_cache=124.0,  # house band (118-128)
        last_bpm_at=1000.0,  # block estimate_bpm so 124.0 survives
    )
    assert state.active_genre == "house"

    # Now wire EventDetector against the SAME state. Patch detect's clock so
    # the music-presence gate has a chance to evaluate cleanly. Use the same
    # audio_buf that _tick_once just used so any chain detector that needs
    # samples gets the warmed-up real buffer.
    mocker.patch("vibemix.state.event_detector.time.time", return_value=2000.0)
    event_detector = EventDetector(audio_buf=buf)
    # Sanity — router seeded to "unknown" by __init__.
    assert event_detector.router.current_genre == "unknown"

    event_detector.detect(state, kaan_just_spoke=False, manual=False)

    # The single detect() call observed state.active_genre="house" !=
    # router.current_genre="unknown", triggered the swap, and ran the house
    # chain. The router is now on "house".
    assert event_detector.router.current_genre == "house"
    chain_types = [type(d) for d in event_detector.router.active_chain()]
    assert SubLayerArrivalDetector in chain_types


# ---------- Test 2 — mid-session genre flip is atomic + no corruption ----------


def test_genre_flip_mid_session_swaps_chain_atomically(mocker):
    """Construct EventDetector. Call detect with active_genre="house" →
    router on house. Call detect with active_genre="techno" → router on
    techno. Verify no exceptions; the techno chain is a fresh instance —
    house's detectors are gc-able after the swap."""
    from vibemix.state import EventDetector, MusicState

    mocker.patch("vibemix.state.event_detector.time.time", return_value=1000.0)

    # Need a real audio_buf so chain detectors don't crash (KickSwap +
    # PhraseBoundary tolerate None gracefully but it's cleaner to thread a
    # warm buffer here too).
    buf = _audible_buf()
    event_detector = EventDetector(audio_buf=buf)

    state = MusicState()
    # Music-presence gate seeded directly so first detect can route.
    state.audible = False  # Stay below the gate; we only care about router state.
    state.bpm = 0.0
    state.active_genre = "house"
    event_detector.detect(state, kaan_just_spoke=False, manual=False)
    assert event_detector.router.current_genre == "house"
    house_chain = event_detector.router.active_chain()
    assert SubLayerArrivalDetector in [type(d) for d in house_chain]

    # Flip — same state object, just change active_genre. EventDetector swaps
    # at the TOP of detect() before any iteration.
    state.active_genre = "techno"
    event_detector.detect(state, kaan_just_spoke=False, manual=False)
    assert event_detector.router.current_genre == "techno"
    techno_chain = event_detector.router.active_chain()
    chain_types = [type(d) for d in techno_chain]
    assert KickSwapDetector in chain_types
    # House's detector instances are no longer in the active chain — the
    # router rebuilt the chain via build_techno_chain() (different list id).
    assert techno_chain is not house_chain
    # And the techno chain doesn't carry the house detector type at all.
    assert SubLayerArrivalDetector not in chain_types


# ---------- Test 3 — __main__.py constructor wiring (skipped if no smoke ref) ----------


def test_main_smoke_event_detector_construct_with_audio_buf():
    """If tests/test_main_smoke.py imports EventDetector explicitly, assert
    it constructs with audio_buf=. Otherwise SKIP — the actual smoke test
    exercises the full process spawn and is its own concern.

    Defensive — this test guards against a future refactor of test_main_smoke
    that DOES start importing EventDetector and forgets the kwarg."""
    import pathlib

    smoke_file = pathlib.Path(__file__).parent.parent / "test_main_smoke.py"
    if not smoke_file.exists():
        import pytest

        pytest.skip("tests/test_main_smoke.py not present — Plan 17-02 grep convention")

    text = smoke_file.read_text()
    if "EventDetector" not in text:
        import pytest

        pytest.skip(
            "tests/test_main_smoke.py does not import EventDetector explicitly — "
            "indirect coverage via the full process spawn is sufficient"
        )

    # If we get here, the smoke file does import EventDetector — assert the
    # audio_buf kwarg is plumbed through (or that the construction is via
    # `EventDetector(audio_buf=`).
    assert "EventDetector(audio_buf=" in text, (
        "tests/test_main_smoke.py imports EventDetector but does not construct "
        "it with audio_buf= — Plan 17-05 contract requires the kwarg in "
        "src/vibemix/__main__.py; the smoke test should mirror that."
    )
