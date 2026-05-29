# SPDX-License-Identifier: Apache-2.0
"""Course 3 live-set rehearsal contract.

This is not a controller/audio ear-pass. It is the deterministic rehearsal for
the backstage seams a real beginner set depends on:

* state refresh resolves Course 3's cue-anchored count-in from DJ-authored cues;
* the coach line only permits forward count-in language with grounded cue proof;
* the live suggestion engine uses the saved pool as a soft prepared target;
* an off-pool track change is treated as a graceful deviation, not a stale plan.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np

from tests.audio.conftest import int16_sine
from vibemix.audio import AudioBuffer
from vibemix.library.prepared_pool import PreparedPool, PreparedPoolTrack
from vibemix.library.rekordbox import CuePoint, RekordboxLibrary, TrackEntry
from vibemix.runtime.suggestion import SuggestionService
from vibemix.state import MusicState
from vibemix.state.coach import AICoach
from vibemix.state.deck_state import DeckState, DeckTrack
from vibemix.state.evidence_registry import EvidenceRegistry
from vibemix.state.refresh import _tick_once


class _FakeBackend:
    def __init__(self, ids: list[str]) -> None:
        self._ids = ids
        self._vectors = np.eye(len(ids), 4, dtype=np.float32)

    def load_all(self):
        return self._ids, self._vectors


class _FakeStore:
    def __init__(self, ids: list[str], ranked: list[tuple[str, float]]) -> None:
        self._backend = _FakeBackend(ids)
        self._ranked = ranked
        self.section_vectors = {
            "s#s000": np.array([1.0, 0.0], dtype=np.float32),
            "s#s001": np.array([0.0, 1.0], dtype=np.float32),
            "s#s002": np.array([0.0, 1.0], dtype=np.float32),
            "a#s000": np.array([0.8, 0.2], dtype=np.float32),
            "a#s001": np.array([0.0, 1.0], dtype=np.float32),
            "b#s000": np.array([0.0, 1.0], dtype=np.float32),
            "c#s000": np.array([0.2, 0.8], dtype=np.float32),
        }

    def search_centered(self, _qvec, k: int = 10):
        return self._ranked[:k]


def _audible_buf() -> AudioBuffer:
    buf = AudioBuffer(seconds=140.0, sr=16000)
    pcm = int16_sine(freq_hz=440.0, duration_sec=6.0, sample_rate=16000, amplitude=0.5)
    buf.push(pcm)
    return buf


def _ctrl_mock() -> MagicMock:
    controller = MagicMock()
    controller.deck_snapshot.return_value = {
        "A": {"vol": 127, "play": True, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64},
        "B": {"vol": 0, "play": False, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64},
        "xfader": 0,
        "connected": True,
    }
    controller.moves_since.return_value = []
    return controller


def _track_info(title: str, position_s: float) -> MagicMock:
    track_info = MagicMock()
    track_info.snapshot.return_value = {
        "title": title,
        "prev_title": "",
        "title_changed_at": 0.0,
        "position_sec": position_s,
        "duration_sec": 300.0,
        "playback_rate": 1.0,
    }
    return track_info


def _cue(name: str, start_s: float, number: int) -> CuePoint:
    return CuePoint(name=name, type="cue", start_s=start_s, end_s=None, number=number)


def _track(track_id: str, title: str, cues: tuple[CuePoint, ...]) -> TrackEntry:
    return TrackEntry(
        track_id=track_id,
        title=title,
        artist="A",
        album="X",
        bpm=120.0,
        key="8A",
        duration_s=300.0,
        cues=cues,
        filepath=f"/music/{track_id}.mp3",
    )


def _library() -> RekordboxLibrary:
    lib = RekordboxLibrary()
    lib.tracks = {
        "s": _track(
            "s",
            "Source",
            (
                _cue("intro", 0.0, 0),
                _cue("breakdown", 64.0, 2),
                _cue("outro", 224.0, 5),
            ),
        ),
        "a": _track("a", "Deviation", (_cue("intro", 0.0, 0), _cue("outro", 224.0, 5))),
        "b": _track("b", "Prepared next", (_cue("intro", 0.0, 0),)),
        "c": _track("c", "Backup", (_cue("intro", 0.0, 0),)),
        "d": _track("d", "Pool filler D", (_cue("intro", 0.0, 0),)),
        "e": _track("e", "Pool filler E", (_cue("intro", 0.0, 0),)),
    }
    return lib


def _pool() -> PreparedPool:
    return PreparedPool(
        name="Beginner five-track pool",
        created_at=1.0,
        json_path=Path("pool.json"),
        tracks=(
            PreparedPoolTrack("s"),
            PreparedPoolTrack("b"),
            PreparedPoolTrack("c"),
            PreparedPoolTrack("d"),
            PreparedPoolTrack("e"),
        ),
    )


def _run_course3_tick(state: MusicState, source: TrackEntry) -> EvidenceRegistry:
    state.set_start_at = 900.0
    deck_source = MagicMock()
    deck_source.snapshot.return_value = {
        "A": DeckTrack(
            title=source.title,
            track_id=source.track_id,
            bpm=source.bpm,
            key=source.key,
            confidence=0.95,
            source="rekordbox_xml",
        )
    }
    registry = EvidenceRegistry()
    section_source = SimpleNamespace(lookup_by_id=lambda track_id: source if track_id == "s" else None)

    _tick_once(
        state,
        _audible_buf(),
        _ctrl_mock(),
        _track_info(source.title, position_s=56.0),
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
    state.bpm_confidence = 0.95
    return registry


def _service(feedback_events=None) -> SuggestionService:
    store = _FakeStore(
        ["s", "a", "b", "c", "d", "e"],
        [("s", 0.99), ("a", 0.94), ("c", 0.88), ("d", 0.70), ("e", 0.69)],
    )
    return SuggestionService(
        store,
        _library(),
        prepared_pool_loader=_pool,
        feedback_sink=feedback_events.append if feedback_events is not None else None,
    )


def test_course3_rehearsal_joins_cue_count_in_and_saved_pool_target() -> None:
    lib = _library()
    state = MusicState()
    registry = _run_course3_tick(state, lib.tracks["s"])
    svc = _service()

    line = AICoach.evidence_line(state)
    suggestion = svc.compute_from_state(state)
    envelope = svc.context_for_state(state, packet_id="ctx_course3_rehearsal")

    assert state.session_active is True
    assert state.phrase_position_confidence == 0.85
    assert state.next_phrase_at == 108.0
    assert registry.snapshot()["cue"]["s:breakdown@64.0"] == (108.0,)
    assert "lens=count_in_eligible[next@108.0]" in line
    assert "cue_anchor=s:breakdown@64.0" in line

    assert suggestion is not None
    assert suggestion["track_id"] == "b"
    assert suggestion["why"].startswith("next in saved pool")
    assert suggestion["transition"]["to_track_id"] == "b"
    assert suggestion["transition"]["timing_basis"] == "section_lookahead"
    assert suggestion["transition"]["start_in_bars"] == 4

    assert envelope is not None
    assert envelope.current["active_track_id"] == "s"
    assert envelope.current["prepared_target_track_id"] == "b"


def test_course3_rehearsal_treats_off_pool_play_as_graceful_deviation() -> None:
    events = []
    svc = _service(feedback_events=events)
    state = MusicState()
    _run_course3_tick(state, _library().tracks["s"])

    first = svc.compute_from_state(state)
    assert first is not None
    assert first["track_id"] == "b"

    state.audible_deck = "A"
    state.audible_track_position_s = 16.0
    state.audible_track_position_confidence = 0.85
    state.deck_state = DeckState(
        decks={"A": DeckTrack(title="Deviation", track_id="a", camelot="8A", bpm=120.0)}
    )

    assert svc.refresh_from_state(state, now=20.0, min_interval_s=0.0) is None
    assert events[-1].action == "suggestion_different_track"
    assert events[-1].label == "different_track"
    assert events[-1].raw["actual_next_track_id"] == "a"

    second = svc.compute_from_state(state)
    envelope = svc.context_for_state(state, packet_id="ctx_course3_deviation")

    assert second is not None
    assert not second["why"].startswith("next in saved pool")
    assert envelope is not None
    assert envelope.current["active_track_id"] == "a"
    assert envelope.current.get("prepared_target_track_id") is None
