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
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from tests.audio.conftest import int16_sine
from vibemix.audio import AudioBuffer
from vibemix.library.prepared_pool import PreparedPool, PreparedPoolTrack
from vibemix.library.rekordbox import CuePoint, TrackEntry
from vibemix.state import MusicState, state_refresh_loop
from vibemix.state.deck_state import DeckTrack
from vibemix.state.prompt_builder import AICoach
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
    m.events_since.return_value = []
    m.activity_snapshot.return_value = {
        "connected": connected,
        "messages_seen_total": 0,
        "events_seen_total": 0,
        "moves_seen_total": 0,
        "recent_moves": 0,
    }
    return m


def _silent_ctrl_mock(connected: bool = True) -> MagicMock:
    """Controller snapshot with no usable deck evidence."""
    m = _ctrl_mock(connected=connected)
    m.deck_snapshot.return_value = {
        "A": {"vol": 0, "play": False, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64},
        "B": {"vol": 0, "play": False, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64},
        "xfader": 64,
        "connected": connected,
    }
    return m


def _track_mock(title: str = "") -> MagicMock:
    m = MagicMock()
    m.snapshot.return_value = {"title": title, "prev_title": "", "title_changed_at": 0.0}
    return m


def _track_position_mock(
    title: str = "",
    position_s: float = 0.0,
    *,
    position_sampled_at: float | None = None,
) -> MagicMock:
    m = MagicMock()
    m.snapshot.return_value = {
        "title": title,
        "prev_title": "",
        "title_changed_at": 0.0,
        "position_sec": position_s,
        "position_sampled_at": position_sampled_at,
        "duration_sec": 300.0,
        "playback_rate": 1.0,
    }
    return m


def _section_entry(
    *,
    track_id: str = "track-1",
    title: str = "Cue Test",
    cues=(),
) -> TrackEntry:
    return TrackEntry(
        track_id=track_id,
        title=title,
        artist="",
        album="",
        bpm=120.0,
        key="Am",
        duration_s=180.0,
        cues=tuple(cues),
        filepath="",
    )


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


def test_tick_sets_course3_session_active_only_with_audible_deck() -> None:
    state = MusicState()
    buf = _audible_buf()
    learn = SimpleNamespace(current_course_id="course_3_play_mode")

    _tick_once(
        state,
        buf,
        _ctrl_mock(),
        _track_mock(),
        now=1000.0,
        last_audible_high=990.0,
        last_audible_low=0.0,
        bpm_cache=0.0,
        last_bpm_at=0.0,
        learn_state=learn,
    )

    assert state.audible is True
    assert state.audible_deck == "A"
    assert state.session_active is True


def test_tick_keeps_course3_graduation_review_out_of_live_lens() -> None:
    state = MusicState()
    state.phrase_position_confidence = 0.9
    state.next_phrase_at = 123.0
    state.next_phrase_cue_id = "phrase_boundary@123.0"
    buf = _audible_buf()
    learn = SimpleNamespace(
        current_course_id="course_3_play_mode",
        current_lesson_id="L3.06",
    )

    _tick_once(
        state,
        buf,
        _ctrl_mock(),
        _track_mock(),
        now=1000.0,
        last_audible_high=990.0,
        last_audible_low=0.0,
        bpm_cache=0.0,
        last_bpm_at=0.0,
        learn_state=learn,
    )

    assert state.audible is True
    assert state.audible_deck == "A"
    assert state.session_active is False
    assert state.phrase_position_confidence == 0.0
    assert state.next_phrase_at is None
    assert state.next_phrase_cue_id is None


def test_tick_course3_live_clears_stale_phrase_until_source_exists() -> None:
    state = MusicState()
    state.phrase_position_confidence = 0.9
    state.next_phrase_at = 123.0
    state.next_phrase_cue_id = "phrase_boundary@123.0"
    buf = _audible_buf()
    learn = SimpleNamespace(current_course_id="course_3_play_mode")

    _tick_once(
        state,
        buf,
        _ctrl_mock(),
        _track_mock(),
        now=1000.0,
        last_audible_high=990.0,
        last_audible_low=0.0,
        bpm_cache=0.0,
        last_bpm_at=0.0,
        learn_state=learn,
    )

    assert state.session_active is True
    assert state.phrase_position_confidence == 0.0
    assert state.next_phrase_at is None
    assert state.next_phrase_cue_id is None


def test_tick_course3_live_uses_dj_cue_sections_for_phrase_anchor() -> None:
    state = MusicState()
    state.set_start_at = 900.0
    entry = _section_entry(
        cues=(
            CuePoint(name="intro", type="cue", start_s=0.0, end_s=None, number=0),
            CuePoint(name="breakdown", type="cue", start_s=64.0, end_s=None, number=2),
        )
    )
    section_source = SimpleNamespace(lookup_by_id=lambda track_id: entry)
    deck_source = MagicMock()
    deck_source.snapshot.return_value = {
        "A": DeckTrack(
            title=entry.title,
            track_id=entry.track_id,
            bpm=entry.bpm,
            key=entry.key,
            confidence=0.95,
            source="rekordbox_xml",
        )
    }
    registry = EvidenceRegistry()

    _tick_once(
        state,
        _audible_buf(),
        _ctrl_mock(),
        _track_position_mock(title=entry.title, position_s=56.0),
        now=1000.0,
        last_audible_high=990.0,
        last_audible_low=0.0,
        bpm_cache=120.0,
        last_bpm_at=999.0,
        learn_state=SimpleNamespace(current_course_id="course_3_play_mode"),
        deck_source=deck_source,
        section_source=section_source,
        evidence_registry=registry,
    )

    assert state.session_active is True
    assert state.phrase_position_confidence == 0.85
    assert state.next_phrase_at == 108.0
    assert state.next_phrase_cue_id == "track-1:breakdown@64.0"
    assert registry.snapshot()["cue"]["track-1:breakdown@64.0"] == (108.0,)

    state.bpm_confidence = 0.95
    line = AICoach.evidence_line(state)
    assert "lens=count_in_eligible[next@108.0]" in line
    assert "cue_anchor=track-1:breakdown@64.0" in line


def _mix_ctrl_mock() -> MagicMock:
    m = _ctrl_mock()
    m.deck_snapshot.return_value = {
        "A": {"vol": 127, "play": True, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64},
        "B": {"vol": 127, "play": True, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64},
        "xfader": 64,
        "connected": True,
    }
    return m


def test_tick_course3_mix_uses_unambiguous_title_match_for_phrase_anchor() -> None:
    state = MusicState()
    state.set_start_at = 900.0
    entry_a = _section_entry(track_id="track-a", title="Outgoing")
    entry_b = _section_entry(
        track_id="track-b",
        title="Incoming",
        cues=(
            CuePoint(name="intro", type="cue", start_s=0.0, end_s=None, number=0),
            CuePoint(name="breakdown", type="cue", start_s=64.0, end_s=None, number=2),
        ),
    )
    entries = {"track-a": entry_a, "track-b": entry_b}
    section_source = SimpleNamespace(lookup_by_id=lambda track_id: entries.get(track_id))
    deck_source = MagicMock()
    deck_source.snapshot.return_value = {
        "A": DeckTrack(
            title=entry_a.title,
            track_id=entry_a.track_id,
            bpm=entry_a.bpm,
            key=entry_a.key,
            confidence=0.95,
            source="rekordbox_xml",
        ),
        "B": DeckTrack(
            title=entry_b.title,
            track_id=entry_b.track_id,
            bpm=entry_b.bpm,
            key=entry_b.key,
            confidence=0.95,
            source="rekordbox_xml",
        ),
    }
    registry = EvidenceRegistry()

    _tick_once(
        state,
        _audible_buf(),
        _mix_ctrl_mock(),
        _track_position_mock(title=entry_b.title, position_s=56.0),
        now=1000.0,
        last_audible_high=990.0,
        last_audible_low=0.0,
        bpm_cache=120.0,
        last_bpm_at=999.0,
        learn_state=SimpleNamespace(current_course_id="course_3_play_mode"),
        deck_source=deck_source,
        section_source=section_source,
        evidence_registry=registry,
    )

    assert state.audible_deck == "mix"
    assert state.session_active is True
    assert state.phrase_position_confidence == 0.75
    assert state.next_phrase_at == 108.0
    assert state.next_phrase_cue_id == "track-b:breakdown@64.0"
    assert registry.snapshot()["cue"]["track-b:breakdown@64.0"] == (108.0,)


def test_tick_course3_mix_refuses_ambiguous_title_match_for_phrase_anchor() -> None:
    state = MusicState()
    entry_a = _section_entry(track_id="track-a", title="Same Title")
    entry_b = _section_entry(
        track_id="track-b",
        title="Same Title",
        cues=(CuePoint(name="breakdown", type="cue", start_s=64.0, end_s=None, number=2),),
    )
    entries = {"track-a": entry_a, "track-b": entry_b}
    section_source = SimpleNamespace(lookup_by_id=lambda track_id: entries.get(track_id))
    deck_source = MagicMock()
    deck_source.snapshot.return_value = {
        side: DeckTrack(
            title=entry.title,
            track_id=entry.track_id,
            bpm=entry.bpm,
            key=entry.key,
            confidence=0.95,
            source="rekordbox_xml",
        )
        for side, entry in (("A", entry_a), ("B", entry_b))
    }

    _tick_once(
        state,
        _audible_buf(),
        _mix_ctrl_mock(),
        _track_position_mock(title="Same Title", position_s=56.0),
        now=1000.0,
        last_audible_high=990.0,
        last_audible_low=0.0,
        bpm_cache=120.0,
        last_bpm_at=999.0,
        learn_state=SimpleNamespace(current_course_id="course_3_play_mode"),
        deck_source=deck_source,
        section_source=section_source,
        evidence_registry=EvidenceRegistry(),
    )

    assert state.audible_deck == "mix"
    assert state.session_active is True
    assert state.phrase_position_confidence == 0.0
    assert state.next_phrase_at is None
    assert state.next_phrase_cue_id is None


def test_tick_course3_cue_registry_write_is_change_only() -> None:
    state = MusicState()
    state.set_start_at = 900.0
    entry = _section_entry(
        cues=(
            CuePoint(name="intro", type="cue", start_s=0.0, end_s=None, number=0),
            CuePoint(name="breakdown", type="cue", start_s=64.0, end_s=None, number=2),
        )
    )
    section_source = SimpleNamespace(lookup_by_id=lambda track_id: entry)
    deck_source = MagicMock()
    deck_source.snapshot.return_value = {
        "A": DeckTrack(
            title=entry.title,
            track_id=entry.track_id,
            bpm=entry.bpm,
            key=entry.key,
            confidence=0.95,
            source="rekordbox_xml",
        )
    }
    registry = EvidenceRegistry()
    kwargs = dict(
        audio_buf=_audible_buf(),
        controller_state=_ctrl_mock(),
        track_info=_track_position_mock(title=entry.title, position_s=56.0),
        last_audible_high=990.0,
        last_audible_low=0.0,
        bpm_cache=120.0,
        last_bpm_at=999.0,
        learn_state=SimpleNamespace(current_course_id="course_3_play_mode"),
        deck_source=deck_source,
        section_source=section_source,
        evidence_registry=registry,
    )

    _tick_once(state, now=1000.0, **kwargs)
    _tick_once(state, now=1000.1, **kwargs)

    assert registry.snapshot()["cue"]["track-1:breakdown@64.0"] == (108.0,)


def test_tick_course3_live_ignores_fallback_sections_for_forward_anchor() -> None:
    state = MusicState()
    entry = _section_entry(cues=())
    section_source = SimpleNamespace(lookup_by_id=lambda track_id: entry)
    deck_source = MagicMock()
    deck_source.snapshot.return_value = {
        "A": DeckTrack(
            title=entry.title,
            track_id=entry.track_id,
            bpm=entry.bpm,
            key=entry.key,
            confidence=0.95,
            source="rekordbox_xml",
        )
    }
    registry = EvidenceRegistry()

    _tick_once(
        state,
        _audible_buf(),
        _ctrl_mock(),
        _track_position_mock(title=entry.title, position_s=56.0),
        now=1000.0,
        last_audible_high=990.0,
        last_audible_low=0.0,
        bpm_cache=120.0,
        last_bpm_at=999.0,
        learn_state=SimpleNamespace(current_course_id="course_3_play_mode"),
        deck_source=deck_source,
        section_source=section_source,
        evidence_registry=registry,
    )

    assert state.session_active is True
    assert state.phrase_position_confidence == 0.0
    assert state.next_phrase_at is None
    assert state.next_phrase_cue_id is None
    assert "cue" not in registry.snapshot()


def test_tick_clears_course3_lens_when_not_in_course3() -> None:
    state = MusicState()
    state.session_active = True
    state.phrase_position_confidence = 0.9
    state.next_phrase_at = 123.0
    state.next_phrase_cue_id = "phrase_boundary@123.0"
    buf = _audible_buf()
    learn = SimpleNamespace(current_course_id="course_2_transitions")

    _tick_once(
        state,
        buf,
        _ctrl_mock(),
        _track_mock(),
        now=1000.0,
        last_audible_high=990.0,
        last_audible_low=0.0,
        bpm_cache=0.0,
        last_bpm_at=0.0,
        learn_state=learn,
    )

    assert state.session_active is False
    assert state.phrase_position_confidence == 0.0
    assert state.next_phrase_at is None
    assert state.next_phrase_cue_id is None


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


def test_tick_writes_audible_track_position_when_confident():
    state = MusicState()
    state.audible = True
    buf = _audible_buf()
    _tick_once(
        state,
        buf,
        _ctrl_mock(),
        _track_position_mock(title="X", position_s=64.5),
        now=1000.0,
        last_audible_high=999.0,
        last_audible_low=0.0,
        bpm_cache=130.0,
        last_bpm_at=999.0,
    )

    assert state.audible_track == "X"
    assert state.audible_track_position_s == 64.5
    assert state.audible_track_duration_s == 300.0
    assert state.audible_track_position_confidence >= 0.8


def test_tick_dead_reckons_track_position_between_nowplaying_polls(mocker):
    state = MusicState()
    state.audible = True
    buf = _audible_buf()
    mocker.patch(
        "vibemix.state.refresh.compute_downbeat_phase",
        return_value=(0.25, 0.95),
    )
    _tick_once(
        state,
        buf,
        _ctrl_mock(),
        _track_position_mock(title="X", position_s=64.5, position_sampled_at=999.5),
        now=1000.0,
        last_audible_high=999.0,
        last_audible_low=0.0,
        bpm_cache=130.0,
        last_bpm_at=999.0,
    )

    assert state.audible_track == "X"
    assert state.audible_track_position_s == 65.0
    assert state.audible_track_position_confidence >= 0.8
    assert state.audible_track_beat_fraction is not None
    assert state.audible_track_seconds_to_nearest_beat is not None


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


def test_tick_infers_audible_deck_from_verified_deck_audio_when_controller_silent():
    state = MusicState()
    state.set_start_at = 900.0
    registry = EvidenceRegistry()

    _tick_once(
        state,
        _audible_buf(),
        _silent_ctrl_mock(),
        _track_mock(title="Deck B Tune"),
        now=1000.0,
        last_audible_high=999.0,
        last_audible_low=0.0,
        bpm_cache=130.0,
        last_bpm_at=999.0,
        evidence_registry=registry,
        audio_capture_context={
            "deck_audio_capture_enabled": True,
            "deck_audio_capture_verified": True,
            "deck_audio_rms": {"A": 0.001, "B": 0.04},
        },
    )

    assert state.audible_deck == "B"
    assert state.deck_confidence >= 0.6
    assert state.audible_track == "Deck B Tune"
    assert registry.snapshot()["mix"]["audible_deck=B"] == (100.0,)


def test_tick_marks_verified_dual_deck_audio_as_mix_when_controller_silent():
    state = MusicState()

    _tick_once(
        state,
        _audible_buf(),
        _silent_ctrl_mock(),
        _track_mock(title="Either Deck"),
        now=1000.0,
        last_audible_high=999.0,
        last_audible_low=0.0,
        bpm_cache=130.0,
        last_bpm_at=999.0,
        audio_capture_context={
            "deck_audio_capture_enabled": True,
            "deck_audio_capture_verified": True,
            "deck_audio_rms": {"A": 0.04, "B": 0.03},
        },
    )

    assert state.audible_deck == "mix"
    assert state.deck_confidence >= 0.5
    assert state.audible_track == "Either Deck"
    assert state.audible_track_confidence == 0.4


def test_tick_refuses_unverified_deck_audio_fallback_when_controller_silent():
    state = MusicState()

    _tick_once(
        state,
        _audible_buf(),
        _silent_ctrl_mock(),
        _track_mock(title="Unproven Route"),
        now=1000.0,
        last_audible_high=999.0,
        last_audible_low=0.0,
        bpm_cache=130.0,
        last_bpm_at=999.0,
        audio_capture_context={
            "deck_audio_capture_enabled": False,
            "deck_audio_capture_verified": False,
            "deck_audio_rms": {"A": 0.001, "B": 0.04},
        },
    )

    assert state.audible_deck == "none"
    assert state.deck_confidence == 0.0
    assert state.audible_track == "Unproven Route"
    assert state.audible_track_confidence == 0.3


def test_tick_writes_recent_moves():
    state = MusicState()
    buf = _audible_buf()
    ctrl = _ctrl_mock()
    ctrl.moves_since.return_value = [(2.0, "A_play→ON"), (5.0, "xfader→full-A")]
    ctrl.activity_snapshot.return_value = {
        "connected": True,
        "messages_seen_total": 3,
        "events_seen_total": 3,
        "moves_seen_total": 2,
        "recent_moves": 2,
    }
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
    assert state.controller_midi_activity == "active"
    assert state.controller_midi_messages_seen == 3
    assert state.controller_midi_events_seen == 3
    assert state.controller_midi_moves_seen == 2
    # moves_since was called with now - 12.0.
    ctrl.moves_since.assert_called_with(988.0)


def test_tick_distinguishes_connected_controller_with_no_midi_traffic():
    state = MusicState()
    buf = _audible_buf()
    ctrl = _ctrl_mock()
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
    assert state.controller_connected is True
    assert state.controller_midi_activity == "connected_no_midi_traffic"
    assert state.controller_midi_messages_seen == 0


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


def test_tick_writes_active_genre_psytrance_before_hard_tek_overlay(mocker):
    """Fast psytrance should not fall into the Hard Tek overlay chain solely
    because its BPM is high. Low mid/high share routes psytrance; high mid/high
    share at the same tempo still routes hard_tek."""
    from vibemix.state.genre import set_active_profile

    set_active_profile(None)

    def psy_feats(buf, seconds=4.0):
        return {
            "rms": 0.1,
            "onsets_per_sec": 3.0,
            "sub_share": 0.42,
            "low_share": 0.30,
            "mid_share": 0.12,
            "high_share": 0.08,  # mid+high = 0.20 < 0.55 → "psytrance"
        }

    def hard_tek_feats(buf, seconds=4.0):
        return {
            "rms": 0.1,
            "onsets_per_sec": 5.0,
            "sub_share": 0.15,
            "low_share": 0.20,
            "mid_share": 0.38,
            "high_share": 0.27,  # mid+high = 0.65 ≥ 0.55 → "hard_tek"
        }

    buf = _audible_buf()

    state = MusicState()
    mocker.patch("vibemix.state.refresh.snapshot_features", side_effect=psy_feats)
    _tick_once(
        state,
        buf,
        _ctrl_mock(),
        _track_mock(),
        now=1000.0,
        last_audible_high=0.0,
        last_audible_low=0.0,
        bpm_cache=149.0,
        last_bpm_at=1000.0,
    )
    assert state.active_genre == "psytrance"

    state2 = MusicState()
    mocker.patch("vibemix.state.refresh.snapshot_features", side_effect=hard_tek_feats)
    _tick_once(
        state2,
        buf,
        _ctrl_mock(),
        _track_mock(),
        now=1000.0,
        last_audible_high=0.0,
        last_audible_low=0.0,
        bpm_cache=149.0,
        last_bpm_at=1000.0,
    )
    assert state2.active_genre == "hard_tek"


def test_tick_writes_active_genre_drum_and_bass_before_hard_tek_overlay(mocker):
    """D&B should not abstain or fall into Hard Tek solely because its BPM is
    high. Low mid/high share at 174 BPM routes D&B; high mid/high share at the
    same tempo still routes hard_tek."""
    from vibemix.state.genre import set_active_profile

    set_active_profile(None)

    def dnb_feats(buf, seconds=4.0):
        return {
            "rms": 0.1,
            "onsets_per_sec": 5.0,
            "sub_share": 0.40,
            "low_share": 0.20,
            "mid_share": 0.15,
            "high_share": 0.20,  # mid+high = 0.35 < 0.55 → "drum_and_bass"
        }

    def hard_tek_feats(buf, seconds=4.0):
        return {
            "rms": 0.1,
            "onsets_per_sec": 5.0,
            "sub_share": 0.15,
            "low_share": 0.20,
            "mid_share": 0.35,
            "high_share": 0.30,  # mid+high = 0.65 ≥ 0.55 → "hard_tek"
        }

    buf = _audible_buf()

    state = MusicState()
    mocker.patch("vibemix.state.refresh.snapshot_features", side_effect=dnb_feats)
    _tick_once(
        state,
        buf,
        _ctrl_mock(),
        _track_mock(),
        now=1000.0,
        last_audible_high=0.0,
        last_audible_low=0.0,
        bpm_cache=174.0,
        last_bpm_at=1000.0,
    )
    assert state.active_genre == "drum_and_bass"

    state2 = MusicState()
    mocker.patch("vibemix.state.refresh.snapshot_features", side_effect=hard_tek_feats)
    _tick_once(
        state2,
        buf,
        _ctrl_mock(),
        _track_mock(),
        now=1000.0,
        last_audible_high=0.0,
        last_audible_low=0.0,
        bpm_cache=174.0,
        last_bpm_at=1000.0,
    )
    assert state2.active_genre == "hard_tek"


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
from vibemix.state.loop_geometry import beatgrid_exact_atom  # noqa: E402


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
    expected_keys = {
        "rms",
        "bpm",
        "onset_density",
        "sub_share",
        "low_share",
        "mid_share",
        "high_share",
    }
    assert set(aud.keys()) >= expected_keys, f"missing keys: {expected_keys - set(aud.keys())}"
    # Each key has exactly one observation from this single tick
    for k in expected_keys:
        assert len(aud[k]) == 1, f"{k} has {len(aud[k])} observations, expected 1"
        # t_session = now - set_start_at = 1000.0 - 900.0 = 100.0
        assert abs(aud[k][0] - 100.0) < 0.001


def test_tick_writes_loop_geometry_receipts_from_typed_controller_events() -> None:
    registry = EvidenceRegistry()
    state = MusicState()
    state.set_start_at = 900.0
    ctrl = _ctrl_mock()
    ctrl.moves_since.return_value = [(2.0, "A_loop_roll:1/4beat")]
    ctrl.events_since.return_value = [
        SimpleNamespace(
            at=998.0,
            kind="beatloop_roll_1_4",
            deck="A",
        )
    ]
    dedupe: set[str] = set()

    kwargs = dict(
        audio_buf=_audible_buf(),
        controller_state=ctrl,
        track_info=_track_mock(),
        last_audible_high=900.0,
        last_audible_low=0.0,
        bpm_cache=130.0,
        last_bpm_at=999.5,
        evidence_registry=registry,
        evidence_dedupe=dedupe,
    )
    _tick_once(state, now=1000.0, **kwargs)
    _tick_once(state, now=1000.1, **kwargs)

    key = beatgrid_exact_atom("A", "loop_roll", 0.25)
    assert registry.snapshot()["mix"][key] == (98.0,)
    ctrl.events_since.assert_called_with(992.1)


def test_tick_registers_citable_deck_source_evidence_from_deck_snapshot() -> None:
    """A real tick must make deck-source truth citable for live Viber/Gemini context."""
    registry = EvidenceRegistry()
    state = MusicState()
    state.set_start_at = 900.0
    deck_source = MagicMock()
    deck_source.snapshot.return_value = {
        "A": DeckTrack(
            title="Source Proof",
            track_id="track-source-proof",
            bpm=124.0,
            key="Am",
            confidence=0.95,
            source="rekordbox_xml",
        )
    }

    _tick_once(
        state,
        _audible_buf(),
        _ctrl_mock(),
        _track_mock(),
        now=1000.0,
        last_audible_high=900.0,
        last_audible_low=0.0,
        bpm_cache=124.0,
        last_bpm_at=999.5,
        evidence_registry=registry,
        deck_source=deck_source,
    )

    expected = "deck_source=deck1_A_known_src_rekordbox_xml+deck2_B_unknown_src_none"
    assert registry.snapshot()["mix"][expected] == (100.0,)


def test_tick_writes_set_progress_from_latest_prepared_pool() -> None:
    state = MusicState()
    state.set_start_at = 900.0
    deck_source = MagicMock()
    deck_source.snapshot.return_value = {
        "A": DeckTrack(
            title="Opening Spiral",
            track_id="track-a",
            bpm=150.0,
            key="Am",
            confidence=0.95,
            source="rekordbox_xml",
        )
    }
    pool = PreparedPool(
        name="Psy Plan",
        created_at=1.0,
        json_path=Path("psy-plan.json"),
        tracks=(
            PreparedPoolTrack("track-a", title="Opening Spiral", artist="One"),
            PreparedPoolTrack("track-b", title="Next Portal", artist="Two"),
            PreparedPoolTrack("track-c", title="Late Lift", artist="Three"),
        ),
    )

    _tick_once(
        state,
        _audible_buf(),
        _ctrl_mock(),
        _track_position_mock(title="Opening Spiral", position_s=12.0),
        now=1000.0,
        last_audible_high=900.0,
        last_audible_low=0.0,
        bpm_cache=150.0,
        last_bpm_at=999.5,
        deck_source=deck_source,
        prepared_pool=pool,
    )

    assert state.audible_deck == "A"
    assert state.set_progress == {
        "source": "prepared_pool",
        "pool_name": "Psy Plan",
        "pool_path": "psy-plan.json",
        "audible_deck": "A",
        "confidence": 0.95,
        "current_track_id": "track-a",
        "current_title": "Opening Spiral",
        "current_artist": "One",
        "current_index": 0,
        "total": 3,
        "next_track_id": "track-b",
        "next_title": "Next Portal",
        "next_artist": "Two",
    }


def test_tick_registers_citable_deck_audio_window_evidence() -> None:
    """The registry must cite pre/current Deck A/B audio windows, not only render them."""
    registry = EvidenceRegistry()
    state = MusicState()
    state.set_start_at = 900.0
    ctrl = _ctrl_mock()
    ctrl.moves_since.return_value = [(0.4, "A_low: flat→killed")]
    audio_capture_context = {
        "deck_audio_capture_enabled": True,
        "deck_audio_rms": {"A": 0.04, "B": 0.02},
        "deck_audio_features": {
            "A": {"activity": "active", "rms": 0.04},
            "B": {"activity": "active", "rms": 0.02},
        },
        "deck_audio_deltas": {
            "A": ["rms_rose_100pct_strong"],
            "B": ["rms_fell_33pct_clear"],
        },
        "deck_audio_windows": {
            "pre_s": (-6.0, -1.0),
            "current_s": (-1.0, 0.0),
            "A": {
                "pre": {"activity": "active", "rms": 0.02},
                "current": {"activity": "active", "rms": 0.04},
                "delta": ["rms_rose_100pct_strong"],
            },
            "B": {
                "pre": {"activity": "active", "rms": 0.03},
                "current": {"activity": "active", "rms": 0.02},
                "delta": ["rms_fell_33pct_clear"],
            },
        },
    }

    _tick_once(
        state,
        _audible_buf(),
        ctrl,
        _track_mock(),
        now=1000.0,
        last_audible_high=900.0,
        last_audible_low=0.0,
        bpm_cache=124.0,
        last_bpm_at=999.5,
        evidence_registry=registry,
        audio_capture_context=audio_capture_context,
    )

    mix = registry.snapshot()["mix"]
    assert "deck_audio_capture=A_active+B_active" in mix
    assert "deck_audio_features=A_active_rms_0.040+B_active_rms_0.020" in mix
    assert "deck_audio_delta=A_rms_rose_100pct_strong+B_rms_fell_33pct_clear" in mix
    assert (
        "deck_audio_window=A_active_pre_0.020_current_0.040+"
        "B_active_pre_0.030_current_0.020"
    ) in mix


def test_tick_keeps_move_aligned_audio_delta_when_next_tick_is_flat(mocker) -> None:
    state = MusicState(audible=True)
    state.prev_perceive = {
        "rms": 0.10,
        "sub": 0.24,
        "low": 0.32,
        "mid": 0.30,
        "high": 0.20,
        "onset_density": 2.0,
    }
    ctrl = _ctrl_mock()
    ctrl.moves_since.return_value = [(0.2, "A_low: flat->killed")]
    baselines: dict[str, dict[str, object]] = {}
    features = {
        "rms": 0.12,
        "sub_share": 0.12,
        "low_share": 0.16,
        "mid_share": 0.40,
        "high_share": 0.32,
        "onsets_per_sec": 3.0,
    }
    mocker.patch("vibemix.state.refresh.snapshot_features", return_value=features)
    mocker.patch("vibemix.state.refresh.energy_curve", return_value=[0.12] * 12)
    mocker.patch("vibemix.state.refresh.long_arc_curve", return_value=[0.12] * 12)

    _tick_once(
        state,
        _audible_buf(),
        ctrl,
        _track_mock(),
        now=1000.0,
        last_audible_high=990.0,
        last_audible_low=0.0,
        bpm_cache=124.0,
        last_bpm_at=999.5,
        move_audio_baselines=baselines,
    )
    first_move_delta = list(state.move_audio_delta)

    _tick_once(
        state,
        _audible_buf(),
        ctrl,
        _track_mock(),
        now=1000.1,
        last_audible_high=990.0,
        last_audible_low=0.0,
        bpm_cache=124.0,
        last_bpm_at=999.5,
        move_audio_baselines=baselines,
    )

    assert "sub energy fell 50% (strong)" in first_move_delta
    assert state.audio_delta == []
    assert "sub energy fell 50% (strong)" in state.move_audio_delta


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
            (registry_writes_inside_lock if inside_lock else registry_writes_outside_lock).append(
                node
            )
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
    assert "audio_capture_context" in sig.parameters
    # Default is None for backward compat
    assert sig.parameters["evidence_registry"].default is None
    assert sig.parameters["audio_capture_context"].default is None

    # Behavioral: call state_refresh_loop with registry, capture _tick_once kwargs
    state = MusicState()
    state.set_start_at = 900.0
    buf = _audible_buf()
    stop = asyncio.Event()
    registry = EvidenceRegistry()
    audio_capture_context = {"deck_audio_capture_enabled": True}

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
        state_refresh_loop(
            state,
            buf,
            _ctrl_mock(),
            _track_mock(),
            stop,
            evidence_registry=registry,
            audio_capture_context=audio_capture_context,
        )
    )
    assert captured_kwargs, "tick_once was never called"
    assert captured_kwargs[0].get("evidence_registry") is registry
    assert captured_kwargs[0].get("audio_capture_context") is audio_capture_context


# ---------- Phase 52 (GENRE-01): genre auto-detect wiring ----------


def test_tick_writes_detected_genre_and_confidence():
    """After an audible tick, state.detected_genre is a str and
    state.genre_confidence is a float in [0, 1] — the two additive bus fields
    are written single-writer-safe inside _tick_once."""
    from vibemix.state.genre import set_active_profile, set_auto_enabled

    set_active_profile(None)
    set_auto_enabled(True)
    try:
        state = MusicState()
        _tick_once(
            state,
            _audible_buf(),
            _ctrl_mock(),
            _track_mock(),
            now=1000.0,
            last_audible_high=0.0,
            last_audible_low=0.0,
            bpm_cache=0.0,
            last_bpm_at=0.0,
        )
        assert isinstance(state.detected_genre, str)
        assert isinstance(state.genre_confidence, float)
        assert 0.0 <= state.genre_confidence <= 1.0
    finally:
        set_active_profile(None)
        set_auto_enabled(True)


def test_tick_lazy_defaults_genre_hysteresis_kwarg():
    """Omitting genre_hysteresis must not crash existing _tick_once callers —
    the kwarg lazy-defaults a fresh GenreHysteresis (backward-compat)."""
    from vibemix.state.genre import set_active_profile, set_auto_enabled

    set_active_profile(None)
    set_auto_enabled(True)
    try:
        state = MusicState()
        # No genre_hysteresis kwarg passed — must not raise.
        out = _tick_once(
            state,
            _audible_buf(),
            _ctrl_mock(),
            _track_mock(),
            now=1000.0,
            last_audible_high=0.0,
            last_audible_low=0.0,
            bpm_cache=0.0,
            last_bpm_at=0.0,
        )
        assert len(out) == 4  # still returns the (high, low, bpm_cache, last_bpm_at) tuple
    finally:
        set_active_profile(None)
        set_auto_enabled(True)


def test_tick_does_not_touch_active_genre_path():
    """The routeable active_genre path stays honest on cold/unknown input."""
    from vibemix.state.genre import set_active_profile, set_auto_enabled

    set_active_profile(None)
    set_auto_enabled(True)
    try:
        state = MusicState()
        _tick_once(
            state,
            _audible_buf(),
            _ctrl_mock(),
            _track_mock(),
            now=1000.0,
            last_audible_high=0.0,
            last_audible_low=0.0,
            bpm_cache=0.0,
            last_bpm_at=0.0,
        )
        assert state.active_genre == "unknown"
    finally:
        set_active_profile(None)
        set_auto_enabled(True)
