# SPDX-License-Identifier: Apache-2.0
"""MusicState dataclass smoke + property + single-writer contract tests.

Covers behavior pinned in 03-01-PLAN.md Task 1.1: 22 fields at v4 defaults,
mutable defaults are per-instance (no shared dict/list/lock), set_seconds and
time_in_phase properties, _lock is a threading.Lock instance.
"""

from __future__ import annotations

import threading

from vibemix.state import MusicState


def test_state_imports_from_package():
    from vibemix.state import MusicState as MS  # noqa: F401


def test_default_construction_exposes_26_fields():
    state = MusicState()

    # Audio block (6 fields)
    assert state.audible is False
    assert state.rms == 0.0
    assert state.bands == {"sub": 0.0, "low": 0.0, "mid": 0.0, "high": 0.0}
    assert state.onset_density == 0.0
    assert state.bpm == 0.0
    assert state.energy_curve == []

    # Phase block (2 fields)
    assert state.phase == "silent"
    assert state.phase_started_at == 0.0

    # Controller block (4 fields)
    assert state.deck_a == {}
    assert state.deck_b == {}
    assert state.xfader == 64
    assert state.controller_connected is False

    # Audible deck inference (2 fields)
    assert state.audible_deck == "none"
    assert state.deck_confidence == 0.0

    # Track (3 fields)
    assert state.audible_track is None
    assert state.audible_track_confidence == 0.0
    assert state.last_audible_track is None

    # Recent moves (1 field)
    assert state.recent_moves == []

    # Historical context (3 fields)
    assert state.long_arc == []
    assert state.phase_history == []
    assert state.track_history == []

    # Set timing (2 fields)
    assert state.set_start_at == 0.0
    assert state.last_kaan_spoke_at == 0.0

    # Phase 17 — Hard Tek detectors v1 (SENSE-13). Backward-compat defaults
    # so Phase 3 golden-equivalence holds (4 fields).
    assert state.buildup_score == 0.0
    assert state.predicted_drop_in_sec is None
    assert state.beat_phase == 0.0
    assert state.active_genre == "unknown"

    # Lock (1 field) — covered by separate test


def test_phase_17_fields_have_backward_compat_defaults():
    """Phase 3 golden-equivalence guard — DO NOT relax these defaults.

    The four Phase 17 fields (`buildup_score`, `predicted_drop_in_sec`,
    `beat_phase`, `active_genre`) MUST default to v4-compatible inert values
    so consumers built before Phase 17 see no behavioral change. Predictive
    drop firing is OFF-by-default in v2.0 — `predicted_drop_in_sec is None`
    is the documented sentinel that downstream code (Phase 19 ack bank,
    detector consumers) uses to skip predictive paths. Locks T-17-01-04 from
    the threat register: silent default-drift would break Phase 3 / Phase 6
    regression coverage at the source-of-truth dataclass."""
    state = MusicState()
    assert state.buildup_score == 0.0, "buildup_score default must be 0.0 (silence-equivalent)"
    assert state.predicted_drop_in_sec is None, (
        "predicted_drop_in_sec default must be None — predictive firing OFF by default per CONTEXT"
    )
    assert state.beat_phase == 0.0, "beat_phase default must be 0.0 (mirrors downbeat_phase default)"
    assert state.active_genre == "unknown", (
        "active_genre default must be 'unknown' — never fabricate a genre during BPM lock-up"
    )

    # Phase 3 golden-equivalence — every PRE-Phase-17 field on a default
    # MusicState() retains its v4-baseline value. If any of these regress,
    # Phase 3 / Phase 6 / Phase 13 tests break silently.
    assert state.audible is False
    assert state.rms == 0.0
    assert state.bands == {"sub": 0.0, "low": 0.0, "mid": 0.0, "high": 0.0}
    assert state.onset_density == 0.0
    assert state.bpm == 0.0
    assert state.energy_curve == []
    assert state.phase == "silent"
    assert state.phase_started_at == 0.0
    assert state.crest_factor == 0.0
    assert state.vocal_active is False
    assert state.bpm_corrected is False
    assert state.genre_profile_name == "unknown"
    assert state.mood == "hype-man"
    assert state.bpm_confidence == 0.0
    assert state.downbeat_phase == 0.0
    assert state.deck_a == {}
    assert state.deck_b == {}
    assert state.xfader == 64
    assert state.controller_connected is False
    assert state.audible_deck == "none"
    assert state.deck_confidence == 0.0
    assert state.audible_track is None
    assert state.audible_track_confidence == 0.0
    assert state.last_audible_track is None
    assert state.recent_moves == []
    assert state.long_arc == []
    assert state.phase_history == []
    assert state.track_history == []
    assert state.set_start_at == 0.0
    assert state.last_kaan_spoke_at == 0.0


def test_phase_17_field_types_via_dataclass_fields():
    """Lock the Phase 17 type annotations via dataclasses.fields() introspection
    so a future refactor can't widen `predicted_drop_in_sec` to a non-Optional
    float (which would break the OFF-by-default sentinel) or narrow
    `active_genre` to a Literal that can't accept future genre strings."""
    import dataclasses

    by_name = {f.name: f for f in dataclasses.fields(MusicState)}
    assert by_name["buildup_score"].type == "float"
    assert by_name["predicted_drop_in_sec"].type == "float | None"
    assert by_name["beat_phase"].type == "float"
    assert by_name["active_genre"].type == "str"


def test_default_factories_not_shared():
    """Critical: dict/list defaults MUST use field(default_factory=...) so that
    two MusicState() instances do not share the same mutable container.
    Catches the classic ``=[]``/``={}`` dataclass footgun (which dataclass
    actually rejects, but a lambda-returning-shared-instance would silently
    leak)."""
    s1 = MusicState()
    s2 = MusicState()

    # All seven mutable defaults
    assert s1.bands is not s2.bands
    assert s1.energy_curve is not s2.energy_curve
    assert s1.deck_a is not s2.deck_a
    assert s1.deck_b is not s2.deck_b
    assert s1.recent_moves is not s2.recent_moves
    assert s1.long_arc is not s2.long_arc
    assert s1.phase_history is not s2.phase_history
    assert s1.track_history is not s2.track_history
    assert s1._lock is not s2._lock


def test_set_seconds_zero_when_unset():
    state = MusicState()
    assert state.set_seconds == 0.0


def test_set_seconds_progresses_with_time(mocker):
    state = MusicState(set_start_at=100.0)
    mocker.patch("vibemix.state.music_state.time.time", return_value=130.0)
    assert state.set_seconds == 30.0


def test_time_in_phase_zero_when_unset():
    state = MusicState()
    assert state.time_in_phase == 0.0


def test_time_in_phase_progresses(mocker):
    state = MusicState(phase_started_at=200.0)
    mocker.patch("vibemix.state.music_state.time.time", return_value=212.5)
    assert state.time_in_phase == 12.5


def test_lock_is_threading_lock():
    state = MusicState()
    # threading.Lock is a builtin factory; type name on macOS is 'lock'.
    # Use duck typing instead.
    assert hasattr(state._lock, "acquire")
    assert hasattr(state._lock, "release")
    assert hasattr(state._lock, "locked")
    # Smoke test: acquire/release works.
    with state._lock:
        assert state._lock.locked() is True
    assert state._lock.locked() is False


def test_lock_factory_returns_distinct_locks():
    s1 = MusicState()
    s2 = MusicState()
    assert s1._lock is not s2._lock
    # And the constructor uses threading.Lock specifically
    canary = threading.Lock()
    assert type(s1._lock) is type(canary)
