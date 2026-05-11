# SPDX-License-Identifier: Apache-2.0
"""EventDetector behavior coverage — every cardinal rule + 7 event types.

Tests use ``mocker.patch('vibemix.state.event_detector.time.time')`` to control
the clock deterministically. The ``_state`` helper builds a MusicState with
"music truly playing" defaults so tests opt INTO restrictive conditions
(silent / bpm-out-of-range) rather than setting them every time.

Constants under test (imported from vibemix.audio.constants — v4 verbatim):
    MUSIC_PRESENCE_MIN_SECONDS = 4.0
    BPM_VALID_MIN              = 100.0
    BPM_VALID_MAX              = 180.0
    EVENT_GLOBAL_MIN_GAP       = 10.0
    HEARTBEAT_SEC              = 70.0
    TRACK_CHANGE_MIN_CONFIDENCE = 0.5
    MIN_EVENT_GAP_PER_TYPE = {TRACK_CHANGE: 6.0, PHASE: 18.0, LAYER_ARRIVAL: 16.0,
                              MIX_MOVE: 20.0, HEARTBEAT: 70.0, MIC: 3.0, MANUAL: 1.5}
"""

from __future__ import annotations

from vibemix.state import Event, EventDetector, MusicState


def _state(
    *,
    audible: bool = True,
    bpm: float = 130.0,
    audible_track: str | None = None,
    audible_track_confidence: float = 0.0,
    phase: str = "groove",
    bands: dict | None = None,
    rms: float = 0.06,
    recent_moves: list | None = None,
) -> MusicState:
    """Build a MusicState pre-populated with 'music truly playing' defaults.
    Tests opt INTO silence / bpm-edge by overriding the defaults."""
    ms = MusicState()
    ms.audible = audible
    ms.bpm = bpm
    ms.audible_track = audible_track
    ms.audible_track_confidence = audible_track_confidence
    ms.phase = phase
    ms.bands = bands if bands is not None else {"sub": 0.2, "low": 0.3, "mid": 0.3, "high": 0.2}
    ms.rms = rms
    ms.recent_moves = recent_moves if recent_moves is not None else []
    return ms


def _patch_time(mocker, value: float):
    return mocker.patch("vibemix.state.event_detector.time.time", return_value=value)


# ---------- Class shape / constants ----------


def test_event_detector_imports_from_package():
    from vibemix.state import EventDetector as ED  # noqa: F401


def test_constants_are_NOT_class_attrs():
    """The v4:1182-1186 class-attrs (MUSIC_PRESENCE_MIN_SECONDS / BPM_VALID_*)
    were lifted OUT to vibemix.audio.constants per 03-CONTEXT decision.
    They must NOT exist as class-level attributes."""
    assert not hasattr(EventDetector, "MUSIC_PRESENCE_MIN_SECONDS")
    assert not hasattr(EventDetector, "BPM_VALID_MIN")
    assert not hasattr(EventDetector, "BPM_VALID_MAX")


def test_constructor_defaults():
    d = EventDetector()
    assert d.last_event_at == 0.0
    assert d.last_per_type_at == {}
    assert d.last_phase == "silent"
    assert d.last_audible_track is None
    assert d.last_band_signature is None
    assert d.last_mix_moves_seen == []
    assert d._audible_since is None


# ---------- Cardinal rule 1: KAAN_SPOKE bypass ----------


def test_kaan_spoke_bypasses_music_presence_gate(mocker):
    """KAAN_SPOKE fires even when state.audible=False and bpm=0."""
    d = EventDetector()
    ms = _state(audible=False, bpm=0.0)
    _patch_time(mocker, 1000.0)
    ev = d.detect(ms, kaan_just_spoke=True, manual=False)
    assert ev is not None
    assert ev.type == "KAAN_SPOKE"
    assert d.last_per_type_at["MIC"] == 1000.0
    assert d.last_event_at == 1000.0


def test_kaan_spoke_respects_MIC_cooldown(mocker):
    """MIC cooldown is 3.0s; global cooldown is 10.0s. Both must clear before
    a second KAAN_SPOKE fires (v4:1198-1201 — both per-type AND global gate)."""
    d = EventDetector()
    ms = _state(audible=False, bpm=0.0)
    t = _patch_time(mocker, 1000.0)
    ev1 = d.detect(ms, kaan_just_spoke=True, manual=False)
    assert ev1 is not None

    t.return_value = 1002.0  # 2s later, < 3.0s MIC + < 10s global
    ev2 = d.detect(ms, kaan_just_spoke=True, manual=False)
    assert ev2 is None

    t.return_value = 1009.5  # 9.5s later, > 3.0s MIC but still < 10s global
    ev3 = d.detect(ms, kaan_just_spoke=True, manual=False)
    assert ev3 is None  # global cooldown still blocks

    t.return_value = 1011.0  # > 10s global → KAAN_SPOKE fires again
    ev4 = d.detect(ms, kaan_just_spoke=True, manual=False)
    assert ev4 is not None
    assert ev4.type == "KAAN_SPOKE"


# ---------- Cardinal rule 1: MANUAL bypass ----------


def test_manual_bypasses_music_presence_gate(mocker):
    d = EventDetector()
    ms = _state(audible=False, bpm=0.0)
    _patch_time(mocker, 1000.0)
    ev = d.detect(ms, kaan_just_spoke=False, manual=True)
    assert ev is not None
    assert ev.type == "MANUAL"
    assert d.last_per_type_at["MANUAL"] == 1000.0


def test_manual_respects_MANUAL_cooldown(mocker):
    """MANUAL cooldown is 1.5s; global is 10.0s. Both gates must clear."""
    d = EventDetector()
    ms = _state(audible=False, bpm=0.0)
    t = _patch_time(mocker, 1000.0)
    ev1 = d.detect(ms, kaan_just_spoke=False, manual=True)
    assert ev1 is not None

    t.return_value = 1001.0  # 1s later, < 1.5s MANUAL + < 10s global
    ev2 = d.detect(ms, kaan_just_spoke=False, manual=True)
    assert ev2 is None

    t.return_value = 1009.5  # > 1.5s MANUAL but < 10s global
    ev3 = d.detect(ms, kaan_just_spoke=False, manual=True)
    assert ev3 is None

    t.return_value = 1011.0  # > 10s global → MANUAL fires again
    ev4 = d.detect(ms, kaan_just_spoke=False, manual=True)
    assert ev4 is not None
    assert ev4.type == "MANUAL"


# ---------- Cardinal rule 2: Music-presence gate ----------


def test_music_presence_gate_blocks_when_not_audible(mocker):
    d = EventDetector()
    ms = _state(audible=False, bpm=0.0)
    _patch_time(mocker, 1000.0)
    ev = d.detect(ms, kaan_just_spoke=False, manual=False)
    assert ev is None
    # _reset_change_refs was called → _audible_since is None
    assert d._audible_since is None
    # Refs synced to current state
    assert d.last_phase == "groove"
    assert d.last_audible_track is None


def test_music_presence_gate_blocks_when_sustained_below_4s(mocker):
    """audible=True for only 2s → gate blocks (< MUSIC_PRESENCE_MIN_SECONDS=4.0)."""
    d = EventDetector()
    ms = _state(audible=True, bpm=130.0)
    t = _patch_time(mocker, 1000.0)
    ev1 = d.detect(ms, kaan_just_spoke=False, manual=False)
    # First call sets _audible_since=1000.0 and returns None (sustained < 4s).
    assert ev1 is None
    assert d._audible_since == 1000.0

    t.return_value = 1002.0  # 2s later, still < 4s
    ev2 = d.detect(ms, kaan_just_spoke=False, manual=False)
    assert ev2 is None


def test_music_presence_gate_blocks_when_bpm_too_low(mocker):
    """bpm=50 (< BPM_VALID_MIN=100) → blocked even after sustained-audible passes."""
    d = EventDetector()
    ms = _state(audible=True, bpm=50.0)
    t = _patch_time(mocker, 1000.0)
    d.detect(ms, kaan_just_spoke=False, manual=False)
    t.return_value = 1005.0  # 5s sustained
    ev = d.detect(ms, kaan_just_spoke=False, manual=False)
    assert ev is None


def test_music_presence_gate_blocks_when_bpm_too_high(mocker):
    """bpm=200 (> BPM_VALID_MAX=180) → blocked."""
    d = EventDetector()
    ms = _state(audible=True, bpm=200.0)
    t = _patch_time(mocker, 1000.0)
    d.detect(ms, kaan_just_spoke=False, manual=False)
    t.return_value = 1005.0
    ev = d.detect(ms, kaan_just_spoke=False, manual=False)
    assert ev is None


# ---------- TRACK_CHANGE ----------


def _prime_music_playing(
    d: EventDetector,
    ms: MusicState,
    mocker,
    *,
    t0: float = 1000.0,
    sync_phase: bool = True,
):
    """Helper: prime the detector so that on the NEXT detect() call, the
    music-presence gate passes.

    Walking through ``detect`` to set ``_audible_since`` would also call
    ``_reset_change_refs`` (which syncs last_phase/last_audible_track/
    last_mix_moves_seen to the current state), polluting the refs and
    preventing the change-driven event types (TRACK_CHANGE, PHASE, MIX_MOVE)
    from firing. So we set ``_audible_since`` directly.

    ``sync_phase=True`` (default) seeds ``last_phase = state.phase`` so a
    PHASE transition from default ``"silent"`` doesn't accidentally fire when
    the test is exercising a different event type. Tests that DO want to
    trigger a PHASE transition pass ``sync_phase=False`` and set
    ``d.last_phase`` themselves.

    Returns the clock mock so callers can advance it further if needed.
    """
    t = _patch_time(mocker, t0 + 5.0)
    # Bypass _reset_change_refs by setting _audible_since manually; the gate
    # will then see (1005 - 1000) = 5.0s >= MUSIC_PRESENCE_MIN_SECONDS (4.0).
    d._audible_since = t0
    if sync_phase:
        d.last_phase = ms.phase
    return t


def test_track_change_fires_when_confidence_above_threshold(mocker):
    d = EventDetector()
    ms = _state(audible_track="Daft Punk - Around the World", audible_track_confidence=0.6)
    _prime_music_playing(d, ms, mocker)
    ev = d.detect(ms, kaan_just_spoke=False, manual=False)
    assert ev is not None
    assert ev.type == "TRACK_CHANGE"
    assert ev.extra == {"prev_track": None, "new_track": "Daft Punk - Around the World"}
    assert d.last_audible_track == "Daft Punk - Around the World"


def test_track_change_blocked_below_confidence_threshold(mocker):
    """audible_track_confidence=0.4 < TRACK_CHANGE_MIN_CONFIDENCE=0.5 → no fire."""
    d = EventDetector()
    ms = _state(audible_track="X", audible_track_confidence=0.4)
    _prime_music_playing(d, ms, mocker)
    ev = d.detect(ms, kaan_just_spoke=False, manual=False)
    # Either falls through to HEARTBEAT or returns None — but NOT a TRACK_CHANGE.
    assert ev is None or ev.type != "TRACK_CHANGE"


def test_track_change_does_not_refire_for_same_title(mocker):
    d = EventDetector()
    ms = _state(audible_track="X", audible_track_confidence=0.6)
    t = _prime_music_playing(d, ms, mocker)
    ev1 = d.detect(ms, kaan_just_spoke=False, manual=False)
    assert ev1.type == "TRACK_CHANGE"
    # Now last_audible_track == "X", so same title diff is false.
    # Move time forward past all cooldowns:
    t.return_value = 1200.0  # way past 6s TRACK_CHANGE + 10s global
    ev2 = d.detect(ms, kaan_just_spoke=False, manual=False)
    # ev2 may be a HEARTBEAT (which is allowed), but cannot be TRACK_CHANGE for the same title.
    assert ev2 is None or ev2.type != "TRACK_CHANGE"


# ---------- PHASE ----------


def test_phase_fires_on_transition(mocker):
    d = EventDetector()
    ms = _state(phase="drop")
    # Prime with last_phase="groove" so state.phase ("drop") != last_phase ("groove")
    # triggers the PHASE branch.
    _prime_music_playing(d, ms, mocker, sync_phase=False)
    d.last_phase = "groove"
    ev = d.detect(ms, kaan_just_spoke=False, manual=False)
    assert ev is not None
    assert ev.type == "PHASE"
    assert ev.extra == {"prev_phase": "groove", "new_phase": "drop"}


def test_phase_does_not_fire_for_silent_phase(mocker):
    """state.phase == 'silent' explicitly skipped (v4:1266 `state.phase not in ("silent",)`)."""
    d = EventDetector()
    ms = _state(phase="silent")
    _prime_music_playing(d, ms, mocker, sync_phase=False)
    d.last_phase = "groove"
    ev = d.detect(ms, kaan_just_spoke=False, manual=False)
    # Should NOT be a PHASE event with new_phase="silent" — that branch is skipped.
    # May be HEARTBEAT (which is allowed), but not PHASE.
    assert ev is None or ev.type != "PHASE"


# ---------- LAYER_ARRIVAL ----------


def test_layer_arrival_first_call_does_not_fire(mocker):
    """First detect: last_band_signature is None → guard at v4:1279 skips the LAYER branch."""
    d = EventDetector()
    ms = _state(bands={"sub": 0.0, "low": 0.0, "mid": 0.5, "high": 0.5})
    _prime_music_playing(d, ms, mocker)
    # The prime walked the detector through one cycle while music-presence gate was blocking,
    # so last_band_signature was reset to None by _reset_change_refs.
    # Plus the first post-gate cycle SETS last_band_signature but doesn't fire (guard).
    ev = d.detect(ms, kaan_just_spoke=False, manual=False)
    # Could be HEARTBEAT but NOT LAYER_ARRIVAL (signature baseline just established).
    if ev is not None:
        assert ev.type != "LAYER_ARRIVAL"


def test_layer_arrival_fires_on_mid_jump(mocker):
    d = EventDetector()
    ms = _state(bands={"sub": 0.4, "low": 0.4, "mid": 0.3, "high": 0.3})
    t = _prime_music_playing(d, ms, mocker)
    # Prime: one tick at sustained-audible time, sets sig=(0.30, 0.30); does NOT fire.
    d.detect(ms, kaan_just_spoke=False, manual=False)
    # Move forward past LAYER_ARRIVAL cooldown (16.0s) AND global (10s):
    t.return_value = 1030.0
    # Now spike mid by 0.20 (> 0.15 threshold) with rms > LOW_RMS (0.040).
    ms.bands = {"sub": 0.2, "low": 0.2, "mid": 0.5, "high": 0.3}
    ms.rms = 0.06
    ev = d.detect(ms, kaan_just_spoke=False, manual=False)
    assert ev is not None
    assert ev.type == "LAYER_ARRIVAL"
    assert ev.extra["mid_jump"] == 0.2
    assert ev.extra["high_jump"] == 0.0


# ---------- MIX_MOVE significance filter (the KEY assertion) ----------


def test_mix_move_fires_on_low_eq_kill(mocker):
    """'_low:' in label → significance match → fires."""
    d = EventDetector()
    ms = _state(recent_moves=[(2.0, "A_low: flat→killed (big twist)")])
    _prime_music_playing(d, ms, mocker)
    ev = d.detect(ms, kaan_just_spoke=False, manual=False)
    assert ev is not None
    assert ev.type == "MIX_MOVE"
    assert ev.extra["moves"] == ["A_low: flat→killed (big twist)"]


def test_mix_move_fires_on_play_arrow(mocker):
    """'_play→' substring → fires (v4 added this in tightening)."""
    d = EventDetector()
    ms = _state(recent_moves=[(1.0, "A_play→ON")])
    _prime_music_playing(d, ms, mocker)
    ev = d.detect(ms, kaan_just_spoke=False, manual=False)
    assert ev is not None
    assert ev.type == "MIX_MOVE"


def test_mix_move_fires_on_xfader(mocker):
    d = EventDetector()
    ms = _state(recent_moves=[(1.0, "xfader→full-A")])
    _prime_music_playing(d, ms, mocker)
    ev = d.detect(ms, kaan_just_spoke=False, manual=False)
    assert ev is not None
    assert ev.type == "MIX_MOVE"


def test_mix_move_DOES_NOT_fire_on_cue_hit(mocker):
    """v3 had 'cue_hit' as significant; v4 dropped it (v4:1299-1305 tightening)."""
    d = EventDetector()
    ms = _state(recent_moves=[(1.0, "A_cue_hit")])
    _prime_music_playing(d, ms, mocker)
    ev = d.detect(ms, kaan_just_spoke=False, manual=False)
    # May be HEARTBEAT but NOT MIX_MOVE.
    assert ev is None or ev.type != "MIX_MOVE"


def test_mix_move_DOES_NOT_fire_on_sync_hit(mocker):
    d = EventDetector()
    ms = _state(recent_moves=[(1.0, "A_sync_hit")])
    _prime_music_playing(d, ms, mocker)
    ev = d.detect(ms, kaan_just_spoke=False, manual=False)
    assert ev is None or ev.type != "MIX_MOVE"


def test_mix_move_DOES_NOT_fire_on_loop_in_play_substring(mocker):
    """'A_loop_in_hit (play=ON)' contains 'play=ON' but NOT '_play→' → NO fire.
    Verifies the v4 tightening: partial 'play' matches must be tightened to '_play→'."""
    d = EventDetector()
    ms = _state(recent_moves=[(1.0, "A_loop_in_hit (play=ON)")])
    _prime_music_playing(d, ms, mocker)
    ev = d.detect(ms, kaan_just_spoke=False, manual=False)
    assert ev is None or ev.type != "MIX_MOVE"


def test_mix_move_filters_already_seen(mocker):
    """Replayed moves (in last_mix_moves_seen) do not refire."""
    d = EventDetector()
    ms = _state(recent_moves=[(2.0, "A_low: flat→killed (big twist)")])
    t = _prime_music_playing(d, ms, mocker)
    ev1 = d.detect(ms, kaan_just_spoke=False, manual=False)
    assert ev1.type == "MIX_MOVE"
    # Move past all cooldowns:
    t.return_value = 1200.0
    # Same move, still in last_mix_moves_seen → no MIX_MOVE refire.
    ev2 = d.detect(ms, kaan_just_spoke=False, manual=False)
    assert ev2 is None or ev2.type != "MIX_MOVE"


# ---------- HEARTBEAT fallthrough ----------


def test_heartbeat_fires_on_fallthrough(mocker):
    """Music truly playing, no other event applies → HEARTBEAT fires once cooldown is OK."""
    d = EventDetector()
    ms = _state()  # default bands + no track + no moves + phase=groove
    _prime_music_playing(d, ms, mocker)
    # After prime: last_phase=ms.phase ("groove") via sync_phase=True.
    # No phase change, no track, no layer (signature was just set + no jump), no moves.
    ev = d.detect(ms, kaan_just_spoke=False, manual=False)
    assert ev is not None
    assert ev.type == "HEARTBEAT"


# ---------- Global cooldown ----------


def test_global_cooldown_blocks_back_to_back_fires(mocker):
    """After any fire, second call within 10s returns None for new events."""
    d = EventDetector()
    ms = _state()
    t = _prime_music_playing(d, ms, mocker)
    ev1 = d.detect(ms, kaan_just_spoke=False, manual=False)
    assert ev1 is not None  # HEARTBEAT

    # Try to fire MIX_MOVE within global cooldown (10s):
    t.return_value = 1009.0  # 4s after HEARTBEAT fire @ 1005
    ms.recent_moves = [(0.5, "A_low: flat→killed (big twist)")]
    ev2 = d.detect(ms, kaan_just_spoke=False, manual=False)
    # Should be blocked by global cooldown (now - last_event_at = 4 < 10).
    assert ev2 is None


# ---------- Ref-update invariant ----------


def test_change_refs_updated_even_when_cooldown_blocks_fire(mocker):
    """The change-detection refs (last_phase, last_audible_track, etc.) are
    updated on every cycle, even when cooldown blocks the fire."""
    d = EventDetector()
    ms = _state(phase="groove", audible_track="X", audible_track_confidence=0.6)
    t = _prime_music_playing(d, ms, mocker)
    # First call fires TRACK_CHANGE (well, depending on prime — see below). Actually after prime,
    # last_audible_track == "X" already (because prime ran through detect once which executes
    # `self.last_audible_track = state.audible_track` outside the fire branch).
    # So this fire path: TRACK_CHANGE blocked by same-title, may fire HEARTBEAT.
    d.detect(ms, kaan_just_spoke=False, manual=False)
    assert d.last_audible_track == "X"

    # Now flip phase but stay within all per-type cooldowns.
    t.return_value = 1006.0  # 1s after fire, within all cooldowns
    ms.phase = "drop"
    d.detect(ms, kaan_just_spoke=False, manual=False)
    # Even though cooldown blocked the PHASE fire, last_phase WAS updated:
    assert d.last_phase == "drop"


def test_returns_event_type_object():
    """Confirm a fired event is the Event dataclass, not just a tuple."""
    d = EventDetector()
    ms = _state(audible=False, bpm=0.0)
    ev = d.detect(ms, kaan_just_spoke=True, manual=False)
    assert isinstance(ev, Event)


# =============================================================================
# Phase 6 — LAYER_ARRIVAL vocal-active gate
# =============================================================================


def test_layer_arrival_suppressed_when_vocal_active(mocker):
    """LAYER_ARRIVAL band-jump suppressed when state.vocal_active=True. Per
    06-CONTEXT.md §EventDetector: vocal arrival isn't a 'new sonic layer' in
    the sense the event was designed to surface."""
    d = EventDetector()
    ms = _state(bands={"sub": 0.4, "low": 0.4, "mid": 0.3, "high": 0.3})
    t = _prime_music_playing(d, ms, mocker)
    # Prime: one tick at sustained-audible time, sets sig=(0.30, 0.30); does NOT fire.
    d.detect(ms, kaan_just_spoke=False, manual=False)
    # Move forward past cooldowns:
    t.return_value = 1030.0
    # Spike mid (> 0.15 threshold) AND set vocal_active=True
    ms.bands = {"sub": 0.2, "low": 0.2, "mid": 0.5, "high": 0.3}
    ms.rms = 0.06
    ms.vocal_active = True
    ev = d.detect(ms, kaan_just_spoke=False, manual=False)
    # Either no event (heartbeat may also be blocked by cooldown) OR not a LAYER_ARRIVAL.
    assert ev is None or ev.type != "LAYER_ARRIVAL"


def test_layer_arrival_fires_when_vocal_not_active(mocker):
    """Regression — same setup but vocal_active=False → LAYER_ARRIVAL fires."""
    d = EventDetector()
    ms = _state(bands={"sub": 0.4, "low": 0.4, "mid": 0.3, "high": 0.3})
    t = _prime_music_playing(d, ms, mocker)
    d.detect(ms, kaan_just_spoke=False, manual=False)
    t.return_value = 1030.0
    ms.bands = {"sub": 0.2, "low": 0.2, "mid": 0.5, "high": 0.3}
    ms.rms = 0.06
    ms.vocal_active = False
    ev = d.detect(ms, kaan_just_spoke=False, manual=False)
    assert ev is not None
    assert ev.type == "LAYER_ARRIVAL"


def test_layer_arrival_baseline_still_updates_when_vocal_active(mocker):
    """When the gate suppresses LAYER_ARRIVAL, last_band_signature still gets
    updated to the new sig — so a non-vocal post-vocal jump doesn't false-fire
    against a stale baseline."""
    d = EventDetector()
    ms = _state(bands={"sub": 0.4, "low": 0.4, "mid": 0.3, "high": 0.3})
    t = _prime_music_playing(d, ms, mocker)
    d.detect(ms, kaan_just_spoke=False, manual=False)
    t.return_value = 1030.0
    ms.bands = {"sub": 0.2, "low": 0.2, "mid": 0.5, "high": 0.3}
    ms.rms = 0.06
    ms.vocal_active = True
    d.detect(ms, kaan_just_spoke=False, manual=False)
    # Baseline updated to the new sig.
    assert d.last_band_signature == (0.5, 0.3)


def test_phase_event_still_fires_when_vocal_active(mocker):
    """PHASE transitions are NOT gated on vocal_active — only LAYER_ARRIVAL is."""
    d = EventDetector()
    ms = _state(phase="drop")
    _prime_music_playing(d, ms, mocker, sync_phase=False)
    d.last_phase = "groove"
    ms.vocal_active = True  # would-be gate, but PHASE ignores it
    ev = d.detect(ms, kaan_just_spoke=False, manual=False)
    assert ev is not None
    assert ev.type == "PHASE"
