# SPDX-License-Identifier: Apache-2.0
"""Phase 13-05 Task 1 — MusicState mood / bpm_confidence / downbeat_phase fields.

The mascot renderer (Plan 13-04) and event dispatcher (Plan 13-06) read these
three new fields off the bus. Defaults MUST be backward-compatible so the
existing 22-field surface keeps working (Phase 3 invariant).

Threading: writes are STILL gated on ``state._lock``. ``state_refresh_loop``
is the only writer of ``bpm_confidence`` / ``downbeat_phase``;
``SettingsApplier`` is the only writer of ``mood`` (Task 2).
"""

from __future__ import annotations

import threading

from vibemix.state import MusicState


def test_default_mood_is_hype_man():
    """Default mood is 'hype-man' — Phase 13 backward-compat for callers that
    instantiate MusicState() without an explicit mood."""
    state = MusicState()
    assert state.mood == "hype-man"


def test_default_bpm_confidence_is_zero():
    """bpm_confidence defaults to 0.0 (no lock yet). Renderer below 0.6
    confidence skips beat-locked entry (Plan 13-04)."""
    state = MusicState()
    assert state.bpm_confidence == 0.0


def test_default_downbeat_phase_is_zero():
    """downbeat_phase defaults to 0.0 (on the 1 of an imagined bar)."""
    state = MusicState()
    assert state.downbeat_phase == 0.0


def test_mood_write_under_lock_holds_from_multiple_threads():
    """Two threads each write a sequence of moods to MusicState.mood under
    state._lock; the final value must be one of the writes — never a torn
    intermediate value, never a default fallback."""
    state = MusicState()
    moods = ["hype-man", "teacher", "coach"]
    iterations = 200
    observed: list[str] = []

    def worker(start: int) -> None:
        for i in range(iterations):
            new = moods[(start + i) % 3]
            with state._lock:
                state.mood = new
            with state._lock:
                observed.append(state.mood)

    t1 = threading.Thread(target=worker, args=(0,))
    t2 = threading.Thread(target=worker, args=(1,))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # All observed values are valid (no torn writes or defaults).
    assert all(m in moods for m in observed), f"unexpected mood values: {set(observed) - set(moods)}"
    # Final value is one of the valid options.
    assert state.mood in moods


def test_existing_music_state_fields_unchanged_regression():
    """Regression — Phase 3 invariants must continue to hold after the 3-field
    extension. If any of these defaults shift, downstream consumers
    (EventDetector, AICoach, ws_broadcast) regress silently."""
    state = MusicState()
    # Audio block
    assert state.audible is False
    assert state.rms == 0.0
    assert state.bpm == 0.0
    # Phase block
    assert state.phase == "silent"
    assert state.phase_started_at == 0.0
    # Controller block
    assert state.audible_deck == "none"
    # Genre-aware (Phase 6) — also intact
    assert state.crest_factor == 0.0
    assert state.vocal_active is False
    assert state.bpm_corrected is False
    assert state.genre_profile_name == "unknown"
