# SPDX-License-Identifier: Apache-2.0
"""next_suggestion — the pill "what's next" engine. Fake store + in-memory
library; no network, no real vectors. Pins grounding (only library-resolved
ids), seed/played exclusion, honest-null, and the Phase-2 harmonic refine.
"""

from __future__ import annotations

import numpy as np
import pytest

from vibemix.library.next_suggestion import (
    NextSuggestion,
    next_suggestion,
    promote_transition_alternative,
    seed_vector_for_track_id,
)
from vibemix.library.rekordbox import CuePoint, RekordboxLibrary, TrackEntry


def _track(
    tid: str,
    bpm: float = 124.0,
    key: str = "8A",
    cues: tuple[CuePoint, ...] = (),
) -> TrackEntry:
    return TrackEntry(
        track_id=tid,
        title=f"Title {tid}",
        artist=f"Artist {tid}",
        album="A",
        bpm=bpm,
        key=key,
        duration_s=300.0,
        cues=cues,
        filepath=f"/tmp/{tid}.mp3",
    )


class _FakeBackend:
    def __init__(self, ids, vectors):
        self._ids, self._vectors = ids, vectors

    def load_all(self):
        return self._ids, self._vectors


class _FakeStore:
    """Returns a scripted ranked list from search_centered; load_all via backend."""

    def __init__(self, ranked, ids=None, vectors=None, section_vectors=None):
        self._ranked = ranked  # list[(track_id, sim)] in rank order
        self._backend = _FakeBackend(
            ids or [t for t, _ in ranked],
            vectors if vectors is not None else np.eye(len(ranked), 4, dtype=np.float32),
        )
        self.section_vectors = section_vectors or {}

    def search_centered(self, qvec, k=10):
        return self._ranked[:k]


@pytest.fixture
def library() -> RekordboxLibrary:
    lib = RekordboxLibrary()
    lib.tracks = {f"t{i}": _track(f"t{i}") for i in range(6)}
    return lib


SEED = np.ones(4, dtype=np.float32)


def test_returns_top_grounded_neighbour(library):
    store = _FakeStore([("t0", 0.99), ("t1", 0.88), ("t2", 0.77)])
    s = next_suggestion(store, library, seed_vector=SEED, seed_track_id="t0", played_ids=set())
    assert isinstance(s, NextSuggestion)
    assert s.track_id == "t1"  # t0 is the seed → skipped
    assert s.similarity == 0.88
    assert s.why == "similar vibe · 8A · 124"  # key+bpm resolved from library


def test_excludes_played(library):
    store = _FakeStore([("t0", 0.99), ("t1", 0.88), ("t2", 0.77)])
    s = next_suggestion(
        store,
        library,
        seed_vector=SEED,
        seed_track_id="t0",
        played_ids={"t1"},
    )
    assert s is not None and s.track_id == "t2"


def test_skips_ids_absent_from_library(library):
    # GHOST is in the store ranking but not the library → ungrounded, skipped.
    store = _FakeStore([("t0", 0.99), ("GHOST", 0.95), ("t3", 0.80)])
    s = next_suggestion(store, library, seed_vector=SEED, seed_track_id="t0", played_ids=set())
    assert s is not None and s.track_id == "t3"


def test_none_when_nothing_qualifies(library):
    store = _FakeStore([("t0", 0.99)])  # only the seed
    s = next_suggestion(store, library, seed_vector=SEED, seed_track_id="t0", played_ids=set())
    assert s is None


def test_honest_null_when_no_metadata():
    lib = RekordboxLibrary()
    lib.tracks = {
        "t0": _track("t0"),
        "f1": TrackEntry(
            track_id="f1",
            title="Folder Track",
            artist="",
            album="",
            bpm=0.0,
            key="",
            duration_s=0.0,
            cues=(),
            filepath="/tmp/f1.mp3",
        ),
    }
    store = _FakeStore([("t0", 0.99), ("f1", 0.90)])
    s = next_suggestion(store, lib, seed_vector=SEED, seed_track_id="t0", played_ids=set())
    assert s is not None and s.track_id == "f1"
    assert s.why == "similar vibe"  # no key/bpm → honest, no fabricated values
    assert s.camelot is None and s.bpm is None


def test_why_includes_first_structural_cue_hint(library):
    library.tracks["t1"] = _track(
        "t1",
        cues=(
            CuePoint(name="DROP", type="cue", start_s=64.0, end_s=None, number=0),
            CuePoint(name="BREAK", type="cue", start_s=128.0, end_s=None, number=1),
        ),
    )
    store = _FakeStore([("t0", 0.99), ("t1", 0.88)])
    s = next_suggestion(store, library, seed_vector=SEED, seed_track_id="t0", played_ids=set())

    assert s is not None
    assert s.why == "similar vibe · 8A · 124 · cue drop @ 1:04"


def test_why_ignores_non_structural_cues(library):
    library.tracks["t1"] = _track(
        "t1",
        cues=(
            CuePoint(name="LOAD", type="load", start_s=0.0, end_s=None, number=-1),
            CuePoint(name="FADE", type="fadein", start_s=2.0, end_s=None, number=-1),
        ),
    )
    store = _FakeStore([("t0", 0.99), ("t1", 0.88)])
    s = next_suggestion(store, library, seed_vector=SEED, seed_track_id="t0", played_ids=set())

    assert s is not None
    assert s.why == "similar vibe · 8A · 124"


def test_suggestion_includes_set_aware_transition_when_cues_exist(library):
    library.tracks["t0"] = _track(
        "t0",
        cues=(CuePoint(name="OUT", type="cue", start_s=224.0, end_s=None, number=5),),
    )
    library.tracks["t1"] = _track(
        "t1",
        key="9A",
        cues=(CuePoint(name="IN", type="cue", start_s=0.0, end_s=None, number=0),),
    )
    store = _FakeStore([("t0", 0.99), ("t1", 0.88)])

    s = next_suggestion(store, library, seed_vector=SEED, seed_track_id="t0", played_ids=set())

    assert s is not None
    assert s.transition is not None
    assert s.transition["cue_slot"] == "A"
    assert s.transition["from_role"] == "outro"
    assert s.transition["to_role"] == "intro"
    assert s.transition["from_start_s"] == 224.0
    assert s.transition["to_start_s"] == 0.0
    assert s.transition["from_camelot"] == "8A"
    assert s.transition["to_camelot"] == "9A"
    assert s.transition["cue_source"] == "dj"
    assert s.transition["cue_confidence"] == 1.0
    assert s.transition["start_in_bars"] is None  # no live playhead confidence yet
    assert "enter cue A" not in s.why  # the dedicated transition line owns actions


def test_set_aware_transition_can_promote_lower_embedding_candidate(library):
    library.tracks["t0"] = _track(
        "t0",
        cues=(CuePoint(name="OUT", type="cue", start_s=224.0, end_s=None, number=5),),
    )
    # Higher embedding similarity, but no trustworthy section/cue handle for a
    # live transition.
    library.tracks["t1"] = _track("t1", key="9A", cues=())
    # Slightly lower embedding similarity, but a grounded cue/section pair.
    library.tracks["t2"] = _track(
        "t2",
        key="9A",
        cues=(CuePoint(name="IN", type="cue", start_s=0.0, end_s=None, number=0),),
    )
    store = _FakeStore([("t0", 0.99), ("t1", 0.91), ("t2", 0.86)])

    s = next_suggestion(store, library, seed_vector=SEED, seed_track_id="t0", played_ids=set())

    assert s is not None
    assert s.track_id == "t2"
    assert s.similarity == 0.86
    assert s.transition is not None
    assert s.transition["to_track_id"] == "t2"
    assert s.transition["selection_basis"] == "section_transition"
    assert s.transition["selection_score"] > 0
    assert s.transition["scores"]["semantic"] >= 0.0
    assert s.transition_alternatives[0]["selected"] is True
    assert s.transition_alternatives[0]["track_id"] == "t2"
    assert s.transition_alternatives[0]["candidate_id"] == "tr_001"
    assert s.transition_alternatives[0]["transition"]["candidate_id"] == "tr_001"
    assert s.transition_alternatives[0]["transition"]["to_track_id"] == "t2"
    assert len(s.transition_alternatives) <= 3
    assert len({alt["candidate_id"] for alt in s.transition_alternatives}) == len(
        s.transition_alternatives
    )


def test_taste_scores_thread_into_transition_components(library):
    library.tracks["t0"] = _track(
        "t0",
        cues=(CuePoint(name="OUT", type="cue", start_s=224.0, end_s=None, number=5),),
    )
    library.tracks["t1"] = _track(
        "t1",
        key="9A",
        cues=(CuePoint(name="IN", type="cue", start_s=0.0, end_s=None, number=0),),
    )
    store = _FakeStore([("t0", 0.99), ("t1", 0.91)])

    s = next_suggestion(
        store,
        library,
        seed_vector=SEED,
        seed_track_id="t0",
        played_ids=set(),
        taste_scores={("outro", "intro"): 0.73},
    )

    assert s is not None
    assert s.transition is not None
    assert s.transition["from_role"] == "outro"
    assert s.transition["to_role"] == "intro"
    assert s.transition["scores"]["taste"] == 0.73


def test_promote_transition_alternative_reassigns_rank_local_candidate_ids():
    alternatives = (
        {
            "candidate_id": "tr_001",
            "rank": 1,
            "selected": True,
            "track_id": "a",
            "transition": {"candidate_id": "tr_001", "to_track_id": "a"},
        },
        {
            "candidate_id": "tr_002",
            "rank": 2,
            "selected": False,
            "track_id": "b",
            "transition": {"candidate_id": "tr_002", "to_track_id": "b"},
        },
    )

    promoted = promote_transition_alternative(alternatives, candidate_id="tr_002")

    assert promoted[0]["track_id"] == "b"
    assert promoted[0]["candidate_id"] == "tr_001"
    assert promoted[0]["rank"] == 1
    assert promoted[0]["selected"] is True
    assert promoted[0]["transition"]["candidate_id"] == "tr_001"
    assert promoted[1]["track_id"] == "a"
    assert promoted[1]["candidate_id"] == "tr_002"
    assert promoted[1]["selected"] is False


def test_section_vectors_can_promote_better_section_texture(library):
    library.tracks["t0"] = _track(
        "t0",
        cues=(CuePoint(name="OUT", type="cue", start_s=224.0, end_s=None, number=5),),
    )
    library.tracks["t1"] = _track(
        "t1",
        key="9A",
        cues=(CuePoint(name="IN", type="cue", start_s=0.0, end_s=None, number=0),),
    )
    library.tracks["t2"] = _track(
        "t2",
        key="9A",
        cues=(CuePoint(name="IN", type="cue", start_s=0.0, end_s=None, number=0),),
    )
    store = _FakeStore(
        [("t0", 0.99), ("t1", 0.91), ("t2", 0.86)],
        section_vectors={
            "t0#s000": np.array([1.0, 0.0], dtype=np.float32),
            "t1#s000": np.array([0.0, 1.0], dtype=np.float32),
            "t2#s000": np.array([1.0, 0.0], dtype=np.float32),
        },
    )

    s = next_suggestion(store, library, seed_vector=SEED, seed_track_id="t0", played_ids=set())

    assert s is not None
    assert s.track_id == "t2"
    assert s.transition is not None
    assert s.transition["semantic_basis"] == "section_vector"
    assert "section texture is close" in s.transition["reasons"]


def test_section_vector_dim_mismatch_reports_semantic_unknown(library):
    library.tracks["t0"] = _track(
        "t0",
        cues=(CuePoint(name="OUT", type="cue", start_s=224.0, end_s=None, number=5),),
    )
    library.tracks["t1"] = _track(
        "t1",
        key="9A",
        cues=(CuePoint(name="IN", type="cue", start_s=0.0, end_s=None, number=0),),
    )
    store = _FakeStore(
        [("t0", 0.99), ("t1", 0.88)],
        section_vectors={
            "t0#s000": np.array([1.0, 0.0], dtype=np.float32),
            "t1#s000": np.array([1.0, 0.0, 0.0], dtype=np.float32),
        },
    )

    s = next_suggestion(store, library, seed_vector=SEED, seed_track_id="t0", played_ids=set())

    assert s is not None
    assert s.transition is not None
    assert s.transition["semantic_basis"] == "semantic_unknown"
    assert "semantic_dim_mismatch" in s.transition["risk_flags"]


def test_suggestion_uses_explicit_live_bar_timing_when_locked(library):
    library.tracks["t0"] = _track(
        "t0",
        cues=(CuePoint(name="OUT", type="cue", start_s=224.0, end_s=None, number=5),),
    )
    library.tracks["t1"] = _track(
        "t1",
        key="9A",
        cues=(CuePoint(name="IN", type="cue", start_s=0.0, end_s=None, number=0),),
    )
    store = _FakeStore([("t0", 0.99), ("t1", 0.88)])

    s = next_suggestion(
        store,
        library,
        seed_vector=SEED,
        seed_track_id="t0",
        played_ids=set(),
        source_deck="A",
        target_deck="B",
        live_remaining_bars=1,
        live_playhead_confidence=0.95,
    )

    assert s is not None
    assert s.transition is not None
    assert s.transition["source_deck"] == "A"
    assert s.transition["target_deck"] == "B"
    assert s.transition["from_track_id"] == "t0"
    assert s.transition["to_track_id"] == "t1"
    assert s.transition["start_in_bars"] == 1
    assert s.transition["timing_basis"] == "bar_lock"
    assert s.transition["timing_anchor"] == "live_bar_countdown"


def test_suggestion_uses_live_position_to_pick_source_section(library):
    library.tracks["t0"] = _track(
        "t0",
        bpm=120.0,
        cues=(
            CuePoint(name="IN", type="cue", start_s=0.0, end_s=None, number=0),
            CuePoint(name="OUT", type="cue", start_s=224.0, end_s=None, number=5),
        ),
    )
    library.tracks["t1"] = _track(
        "t1",
        bpm=120.0,
        key="9A",
        cues=(CuePoint(name="IN", type="cue", start_s=0.0, end_s=None, number=0),),
    )
    store = _FakeStore([("t0", 0.99), ("t1", 0.88)])

    s = next_suggestion(
        store,
        library,
        seed_vector=SEED,
        seed_track_id="t0",
        played_ids=set(),
        source_position_s=236.0,
        live_playhead_confidence=0.85,
    )

    assert s is not None
    assert s.transition is not None
    assert s.transition["from_section_id"] == "t0#s001"
    assert s.transition["from_role"] == "outro"
    assert s.transition["to_role"] == "intro"
    assert s.transition["from_start_s"] == 224.0
    assert s.transition["from_end_s"] == 300.0
    assert s.transition["to_start_s"] == 0.0
    assert s.transition["to_end_s"] == 80.0
    assert s.transition["start_in_bars"] == 32
    assert s.transition["timing_basis"] == "section_playhead"
    assert s.transition["timing_anchor"] == "source_section_end"
    assert s.transition["source_anchor_s"] == 300.0
    assert s.transition["source_selection"] == "current_section"
    assert s.transition["cue_slot"] == "A"


def test_suggestion_forecasts_upcoming_mix_source_section(library):
    library.tracks["t0"] = _track(
        "t0",
        bpm=120.0,
        cues=(
            CuePoint(name="IN", type="cue", start_s=0.0, end_s=None, number=0),
            CuePoint(name="OUT", type="cue", start_s=224.0, end_s=None, number=5),
        ),
    )
    library.tracks["t1"] = _track(
        "t1",
        bpm=120.0,
        key="9A",
        cues=(CuePoint(name="IN", type="cue", start_s=0.0, end_s=None, number=0),),
    )
    store = _FakeStore([("t0", 0.99), ("t1", 0.88)])

    s = next_suggestion(
        store,
        library,
        seed_vector=SEED,
        seed_track_id="t0",
        played_ids=set(),
        source_position_s=216.0,
        live_playhead_confidence=0.85,
    )

    assert s is not None
    assert s.transition is not None
    assert s.transition["from_section_id"] == "t0#s001"
    assert s.transition["from_role"] == "outro"
    assert s.transition["to_role"] == "intro"
    assert s.transition["from_start_s"] == 224.0
    assert s.transition["to_start_s"] == 0.0
    assert s.transition["start_in_bars"] == 4
    assert s.transition["timing_basis"] == "section_lookahead"
    assert s.transition["timing_anchor"] == "source_section_start"
    assert s.transition["source_anchor_s"] == 224.0
    assert s.transition["source_selection"] == "upcoming_section"


def test_low_confidence_live_position_does_not_anchor_source_section(library):
    library.tracks["t0"] = _track(
        "t0",
        bpm=120.0,
        cues=(
            CuePoint(name="IN", type="cue", start_s=0.0, end_s=None, number=0),
            CuePoint(name="OUT", type="cue", start_s=224.0, end_s=None, number=5),
        ),
    )
    library.tracks["t1"] = _track(
        "t1",
        bpm=120.0,
        key="9A",
        cues=(CuePoint(name="IN", type="cue", start_s=0.0, end_s=None, number=0),),
    )
    store = _FakeStore([("t0", 0.99), ("t1", 0.88)])

    s = next_suggestion(
        store,
        library,
        seed_vector=SEED,
        seed_track_id="t0",
        played_ids=set(),
        source_position_s=32.0,
        live_playhead_confidence=0.25,
    )

    assert s is not None
    assert s.transition is not None
    # Low-confidence position is not trusted as "current section"; fall back to
    # the best mix-out section and withhold exact timing.
    assert s.transition["from_section_id"] == "t0#s001"
    assert s.transition["start_in_bars"] is None
    assert s.transition["timing_basis"] is None
    assert "timing_low_confidence" in s.transition["risk_flags"]


def test_phase2_harmonic_filter_drops_incompatible(library):
    # seed 8A; t1 is also 8A (compatible), but make t1 a BPM clash to force the
    # filter to fall through to the next compatible candidate.
    library.tracks["t1"] = _track("t1", bpm=150.0, key="8A")  # far BPM
    library.tracks["t2"] = _track("t2", bpm=126.0, key="8A")  # compatible
    store = _FakeStore([("t0", 0.99), ("t1", 0.92), ("t2", 0.80)])
    s = next_suggestion(
        store,
        library,
        seed_vector=SEED,
        seed_track_id="t0",
        played_ids=set(),
        seed_camelot="8A",
        seed_bpm=124.0,
        bpm_window=15.0,
    )
    assert s is not None and s.track_id == "t2"  # t1 dropped on BPM
    assert s.camelot == "8A" and s.bpm == 126.0


def test_phase2_keeps_candidate_missing_metadata(library):
    # A candidate with no key/bpm must NOT be dropped by the refine filter.
    library.tracks["t1"] = TrackEntry(
        track_id="t1",
        title="No Meta",
        artist="X",
        album="",
        bpm=0.0,
        key="",
        duration_s=0.0,
        cues=(),
        filepath="/tmp/t1.mp3",
    )
    store = _FakeStore([("t0", 0.99), ("t1", 0.92)])
    s = next_suggestion(
        store,
        library,
        seed_vector=SEED,
        seed_track_id="t0",
        played_ids=set(),
        seed_camelot="8A",
        seed_bpm=124.0,
    )
    assert s is not None and s.track_id == "t1"  # kept despite missing meta
    assert s.why == "similar vibe"


def test_seed_vector_helper(library):
    vectors = np.array([[1, 0, 0, 0], [0, 1, 0, 0]], dtype=np.float32)
    store = _FakeStore([], ids=["t0", "t1"], vectors=vectors)
    v = seed_vector_for_track_id(store, "t1")
    assert v is not None and np.allclose(v, [0, 1, 0, 0])
    assert seed_vector_for_track_id(store, "missing") is None
