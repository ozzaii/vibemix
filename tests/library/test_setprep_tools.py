# SPDX-License-Identifier: Apache-2.0
"""Set-prep tool handlers on LibraryToolset (Vibe Mix engine wiring).

Pins the 4 new grounded tools — get_track_energy / discover_pool / sequence_set
/ export_set — and, critically, that grounding (Cardinal Invariant #2) holds on
the new write/order surfaces exactly as it does for create_playlist:

  * get_track_energy is honest-null on no audio (energy is COMPUTED, never the
    model's; the energy cache hits on a second identical call).
  * discover_pool adds every returned id to the seen-set (a discovery path).
  * sequence_set REJECTS any id not in seen (the never-invent-id gate).
  * export_set rejects un-seen ids AND re-validates surviving ids against the
    live library (the 2-gate mirror of create_playlist).

No network: discover/sequence/export engine internals are exercised against a
fake store + in-memory library; energy is monkeypatched.
"""

from __future__ import annotations

import json
import pathlib
import shutil
import time
import xml.etree.ElementTree as ET
from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest

from vibemix.intel.transition_scorer import SectionRecord
from vibemix.library import cue_landing as cue_landing_mod
from vibemix.library import energy as energy_mod
from vibemix.library import toolset as tool_mod
from vibemix.library.cue_types import CueAnchor
from vibemix.library.next_suggestion import next_suggestion
from vibemix.library.rekordbox import (
    CuePoint,
    RekordboxLibrary,
    TempoNode,
    TrackEntry,
)
from vibemix.library.staleness import LibraryFreshness
from vibemix.library.toolset import MAX_INSPECT_CANDIDATES, LibraryToolset

_REAL_MP3 = pathlib.Path(__file__).resolve().parents[1] / "bench" / "data" / "t1_pyrez_darkside.mp3"

# --------------------------------------------------------------------------- #
# Fixtures — mirror test_discovery.py / test_next_suggestion.py fakes.
# --------------------------------------------------------------------------- #


def _track(tid: str, bpm: float = 124.0, key: str = "8A") -> TrackEntry:
    return TrackEntry(
        track_id=tid,
        title=f"Title {tid}",
        artist=f"Artist {tid}",
        album="A",
        bpm=bpm,
        key=key,
        duration_s=300.0,
        cues=(),
        filepath=f"/tmp/{tid}.mp3",
    )


def _section(track_section_id: str, role: str, start_s: float, end_s: float) -> SectionRecord:
    track_id = track_section_id.split("#", 1)[0]
    return SectionRecord(
        section_id=track_section_id,
        track_id=track_id,
        role=role,
        source="anlz",
        source_detail="pssi",
        confidence=0.92,
        start_s=start_s,
        end_s=end_s,
        start_beat=round(start_s * 2),
        end_beat=round(end_s * 2),
        bar_count=(end_s - start_s) * 124.0 / 60.0 / 4.0,
        bpm=124.0,
        camelot="8A",
        cue_source="anlz",
        cue_confidence=0.92,
    )


class _FakeBackend:
    def __init__(self, ids, vectors):
        self._ids, self._vectors = ids, vectors

    def load_all(self):
        return self._ids, self._vectors


class _FakeStore:
    def __init__(self, ids, vectors, ranked, section_vectors=None):
        self._backend = _FakeBackend(ids, vectors)
        self._ranked = ranked  # list[(track_id, sim)]
        self.section_vectors = section_vectors or {}

    def search_centered(self, qvec, k=10):
        return self._ranked[:k]


@pytest.fixture
def library() -> RekordboxLibrary:
    lib = RekordboxLibrary()
    # Spread keys so harmonic gates pass, distinct enough to sequence.
    keys = ["8A", "9A", "8B", "7A", "8A"]
    lib.tracks = {f"t{i:03d}": _track(f"t{i:03d}", bpm=124.0 + i, key=keys[i]) for i in range(5)}
    return lib


@pytest.fixture
def store() -> _FakeStore:
    ids = [f"t{i:03d}" for i in range(5)]
    # Orthogonal-ish unit vectors so MMR + coherence are meaningful.
    vectors = np.eye(5, 8, dtype=np.float32)
    ranked = [(tid, 0.9 - 0.05 * i) for i, tid in enumerate(ids)]
    return _FakeStore(ids, vectors, ranked)


@pytest.fixture
def toolset(store, library) -> LibraryToolset:
    # embedder is unused on the ref-ids / no-text path.
    return LibraryToolset(embedder=None, store=store, library=library)


def _fresh_library() -> LibraryFreshness:
    return LibraryFreshness(
        status="fresh",
        stale=False,
        reason="test_current",
        age_days=0,
        cache_path="/tmp/library.pkl",
    )


def _stale_library() -> LibraryFreshness:
    return LibraryFreshness(
        status="stale",
        stale=True,
        reason="source_newer_than_cache",
        age_days=0,
        cache_path="/tmp/library.pkl",
        source_path="/tmp/collection.xml",
    )


# --------------------------------------------------------------------------- #
# get_track_energy — honest-null + cache
# --------------------------------------------------------------------------- #


def test_get_track_energy_honest_null_on_no_audio(toolset, monkeypatch):
    """Undecodable / absent audio → energy: None (never a fabricated number)."""
    monkeypatch.setattr(
        tool_mod.__dict__.get("score_energy_cached", None) or energy_mod,
        "score_energy_cached",
        lambda *a, **k: None,
        raising=False,
    )
    # The handler lazy-imports score_energy_cached from energy_mod — patch there.
    monkeypatch.setattr(energy_mod, "score_energy_cached", lambda *a, **k: None)
    out = toolset.get_track_energy({"track_id": "t000"})
    assert out == {"track_id": "t000", "energy": None}


def test_get_track_energy_unknown_id_errors(toolset):
    out = toolset.get_track_energy({"track_id": "GHOST"})
    assert "error" in out


def test_get_track_energy_returns_computed_score(toolset, monkeypatch):
    from vibemix.library.energy import EnergyScore

    monkeypatch.setattr(
        energy_mod,
        "score_energy_cached",
        lambda *a, **k: EnergyScore(score=72.0, breakdown={"loudness": 0.5}),
    )
    out = toolset.get_track_energy({"track_id": "t000"})
    assert out["energy"] == 72.0
    assert out["breakdown"] == {"loudness": 0.5}


def test_energy_cache_hits_second_call(monkeypatch, tmp_path):
    """ENERGY-03: a second call with the same content signature hits the cache —
    score_energy is invoked exactly once."""
    from vibemix.library import energy as e

    monkeypatch.setattr(e, "ENERGY_CACHE_PATH", tmp_path / "energy.json")

    # Stable content signature regardless of the real filesystem.
    monkeypatch.setattr(e, "_content_signature", lambda p: "SIG::1::1")

    calls = {"n": 0}

    def fake_score_energy(path, *, sample_rate=16000):
        calls["n"] += 1
        return e.EnergyScore(score=55.0, breakdown={"flux": 0.4})

    monkeypatch.setattr(e, "score_energy", fake_score_energy)

    first = e.score_energy_cached("/tmp/x.mp3")
    second = e.score_energy_cached("/tmp/x.mp3")
    assert first is not None and second is not None
    assert first.score == second.score == 55.0
    assert calls["n"] == 1  # second call served from cache


def test_energy_cache_corrupt_degrades_to_recompute(monkeypatch, tmp_path):
    from vibemix.library import energy as e

    cache_path = tmp_path / "energy.json"
    cache_path.write_text("{ this is not json")
    monkeypatch.setattr(e, "ENERGY_CACHE_PATH", cache_path)
    monkeypatch.setattr(e, "_content_signature", lambda p: "SIG::2::2")
    monkeypatch.setattr(e, "score_energy", lambda *a, **k: e.EnergyScore(score=33.0, breakdown={}))
    out = e.score_energy_cached("/tmp/y.mp3")
    assert out is not None and out.score == 33.0


# --------------------------------------------------------------------------- #
# discover_pool — adds ids to seen (a discovery path)
# --------------------------------------------------------------------------- #


def test_discover_pool_adds_ids_to_seen(toolset):
    out = toolset.discover_pool({"ref_track_ids": ["t000"], "k": 10})
    assert "pool" in out
    pool_ids = {p["track_id"] for p in out["pool"]}
    assert pool_ids  # found something
    # Every surfaced id is now grounded (seen) — sequence/export may use them.
    assert pool_ids.issubset(toolset.seen)
    # The reference itself is excluded from its own pool.
    assert "t000" not in pool_ids


def test_discover_pool_marks_unverified_bpm_filter(toolset, library):
    for tid in ("t001", "t002", "t003", "t004"):
        library.tracks[tid] = _track(tid, bpm=0.0)

    out = toolset.discover_pool(
        {"ref_track_ids": ["t000"], "k": 10, "bpm_min": 128.0, "bpm_max": 138.0}
    )

    warning = out["metadata_warnings"][0]
    assert warning["field"] == "bpm"
    assert warning["reason"] == "missing_library_metadata"
    assert warning["unknown_count"] == len(out["pool"])
    assert warning["total_count"] == len(out["pool"])
    assert "do not treat the range as verified" in warning["message"]

    summary = LibraryToolset._tool_event_summary("discover_pool", out)
    assert f"bpm_unknown={len(out['pool'])}/{len(out['pool'])}" in summary


def test_discover_pool_surfaces_duration_filter_in_tool_tape(toolset):
    out = toolset.discover_pool({"ref_track_ids": ["t000"], "k": 10, "min_duration_s": 120})

    assert out["filters"]["min_duration_s"] == 120.0
    arg = LibraryToolset._tool_event_arg_summary(
        "discover_pool",
        {"ref_track_ids": ["t000"], "k": 10, "min_duration_s": 120},
    )
    summary = LibraryToolset._tool_event_summary("discover_pool", out)

    assert "min_dur=120s" in arg
    assert "track" in summary


def test_dispatch_blocks_set_prep_when_library_freshness_is_stale(store, library):
    guarded = LibraryToolset(
        embedder=None,
        store=store,
        library=library,
        freshness_provider=_stale_library,
    )

    out = guarded.dispatch("discover_pool", {"ref_track_ids": ["t000"], "k": 10})

    assert out["blocked_by"] == "library_freshness"
    assert out["library_freshness"]["reason"] == "source_newer_than_cache"
    assert "not current" in out["error"]
    assert guarded.seen == set()


def test_dispatch_allows_set_prep_when_library_freshness_is_fresh(store, library):
    guarded = LibraryToolset(
        embedder=None,
        store=store,
        library=library,
        freshness_provider=_fresh_library,
    )

    out = guarded.dispatch("discover_pool", {"ref_track_ids": ["t000"], "k": 10})

    assert "pool" in out
    assert {p["track_id"] for p in out["pool"]}.issubset(guarded.seen)


def test_mcp_tool_proxy_blocks_direct_handler_calls_when_freshness_is_stale(store, library):
    from vibemix.library.mcp_server import _ToolTapProxy

    guarded = LibraryToolset(
        embedder=None,
        store=store,
        library=library,
        freshness_provider=_stale_library,
    )
    proxy = _ToolTapProxy(guarded)

    out = proxy.discover_pool({"ref_track_ids": ["t000"], "k": 10})

    assert out["blocked_by"] == "library_freshness"
    assert out["library_freshness"]["status"] == "stale"
    assert guarded.seen == set()


def test_discover_pool_error_when_no_inputs(toolset):
    out = toolset.discover_pool({})
    assert "error" in out


# --------------------------------------------------------------------------- #
# sequence_set — rejects ids not in seen (grounding gate)
# --------------------------------------------------------------------------- #


def test_sequence_set_rejects_unseen_ids(toolset):
    # Nothing discovered yet → every id is "invented".
    out = toolset.sequence_set({"track_ids": ["t000", "t001"], "curve": "peak_time"})
    assert "error" in out
    assert "invented" in out["error"]


def test_sequence_set_orders_seen_pool(toolset):
    toolset.discover_pool({"ref_track_ids": ["t000"], "k": 10})
    seen_ids = sorted(toolset.seen)
    assert len(seen_ids) >= 2
    out = toolset.sequence_set({"track_ids": seen_ids, "curve": "peak_time"})
    assert "candidates" in out
    assert out["candidates"]
    first = out["candidates"][0]
    assert "track_ids" in first
    assert "energy_fit" in first
    assert "avg_coherence" in first
    # Every sequenced id is a real, grounded id.
    assert set(first["track_ids"]).issubset(toolset.seen)


def test_sequence_set_dedupes_obvious_file_copies_before_ordering(monkeypatch):
    from vibemix.library import sequencer as sequencer_mod

    lib = RekordboxLibrary()
    lib.tracks = {
        "a": TrackEntry(
            track_id="a",
            title="Mass In Orbit - Connect",
            artist="",
            album="A",
            bpm=124.0,
            key="8A",
            duration_s=323.29,
            cues=(),
            filepath="/tmp/connect.mp3",
        ),
        "b": TrackEntry(
            track_id="b",
            title="Mass In Orbit - Connect (1)",
            artist="",
            album="A",
            bpm=124.0,
            key="8A",
            duration_s=323.29,
            cues=(),
            filepath="/tmp/connect-copy.mp3",
        ),
        "c": TrackEntry(
            track_id="c",
            title="Other Peak Tool",
            artist="",
            album="A",
            bpm=125.0,
            key="8A",
            duration_s=300.0,
            cues=(),
            filepath="/tmp/other.mp3",
        ),
    }
    ids = ["a", "b", "c"]
    vectors = np.eye(3, 8, dtype=np.float32)
    ranked = [(tid, 0.9 - 0.05 * i) for i, tid in enumerate(ids)]
    toolset = LibraryToolset(embedder=None, store=_FakeStore(ids, vectors, ranked), library=lib)
    toolset.seen.update(ids)

    def fake_sequence_set(pool, *, curve, n_slots, **_kwargs):
        return [
            SimpleNamespace(
                track_ids=[p.track_id for p in pool],
                cost=0.0,
                energy_fit=0.0,
                avg_coherence=1.0,
                relaxed_transitions=[],
            )
        ]

    monkeypatch.setattr(sequencer_mod, "sequence_set", fake_sequence_set)

    out = toolset.sequence_set({"track_ids": ids, "curve": "peak_time", "n_slots": 3})

    assert out["deduped_track_ids"] == ["b"]
    assert out["candidates"][0]["track_ids"] == ["a", "c"]
    assert LibraryToolset._tool_event_summary("sequence_set", out) == "1 candidate; deduped=1"


def test_sequence_set_novelty_uses_discovery_similarity_as_surprise(toolset, monkeypatch):
    from vibemix.library import sequencer as sequencer_mod

    toolset.discover_pool({"ref_track_ids": ["t000"], "k": 10})
    seen_ids = sorted(toolset.seen)
    captured: dict[str, object] = {}

    def fake_sequence_set(pool, *, curve, n_slots, weights=None, surprise=None, **_kwargs):
        captured["track_ids"] = [p.track_id for p in pool]
        captured["curve"] = curve
        captured["n_slots"] = n_slots
        captured["weights"] = weights
        captured["surprise"] = surprise
        return [
            SimpleNamespace(
                track_ids=[p.track_id for p in pool],
                cost=0.0,
                energy_fit=0.0,
                avg_coherence=1.0,
                relaxed_transitions=[],
            )
        ]

    monkeypatch.setattr(sequencer_mod, "sequence_set", fake_sequence_set)

    out = toolset.sequence_set({"track_ids": seen_ids, "curve": "peak_time", "novelty": 0.4})

    assert "candidates" in out
    assert captured["weights"] == {"gamma": 0.4}
    surprise = captured["surprise"]
    assert isinstance(surprise, dict)
    # Lower discovery similarity means a higher deterministic novelty reward.
    assert max(surprise.values()) > min(surprise.values())


def test_sequence_set_unknown_curve_is_actionable(toolset):
    toolset.discover_pool({"ref_track_ids": ["t000"], "k": 10})
    out = toolset.sequence_set({"track_ids": sorted(toolset.seen), "curve": "no_such_curve"})
    assert "error" in out


# --------------------------------------------------------------------------- #
# section-aware transition slate — issues grounded section/candidate/context ids
# --------------------------------------------------------------------------- #


def test_get_track_sections_rejects_unseen_track(toolset):
    out = toolset.get_track_sections({"track_id": "t000"})

    assert "error" in out
    assert "invented" in out["error"]


def test_get_track_sections_issues_cue_derived_sections(toolset):
    toolset.seen.add("t000")
    toolset._library.tracks["t000"] = TrackEntry(
        track_id="t000",
        title="Section Track",
        artist="Artist",
        album="A",
        bpm=128.0,
        key="8A",
        duration_s=300.0,
        cues=(
            CuePoint(name="IN", type="cue", start_s=0.0, end_s=None, number=0),
            CuePoint(name="DROP", type="cue", start_s=64.0, end_s=None, number=3),
            CuePoint(name="OUT", type="cue", start_s=240.0, end_s=None, number=5),
        ),
        filepath="/tmp/t000.mp3",
    )

    out = toolset.get_track_sections({"track_id": "t000"})

    assert [section["section_id"] for section in out["sections"]] == [
        "t000#s000",
        "t000#s001",
        "t000#s002",
    ]
    assert out["sections"][0]["role"] == "intro"
    assert out["sections"][1]["role"] == "drop"
    assert out["sections"][2]["role"] == "outro"
    assert set(toolset.seen_sections) >= {"t000#s000", "t000#s001", "t000#s002"}


def test_inspect_candidates_batches_features_sections_and_energy(toolset, monkeypatch):
    from vibemix.library.energy import EnergyScore

    monkeypatch.setattr(
        energy_mod,
        "score_energy_cached",
        lambda *a, **k: EnergyScore(score=71.6, breakdown={"loudness": 0.6}),
    )
    toolset.seen.update({"t000", "t001"})

    out = toolset.inspect_candidates({"track_ids": ["t000", "t001"]})

    assert out["track_ids"] == ["t000", "t001"]
    assert out["truncated"] is False
    assert len(out["candidates"]) == 2
    first = out["candidates"][0]
    assert first["features"]["track_id"] == "t000"
    assert first["features"]["bpm"] == 124.0
    assert first["sections"]
    assert first["sections"][0]["section_id"].startswith("t000#")
    assert first["energy"] == {"energy": 71.6, "breakdown": {"loudness": 0.6}}
    assert any(section_id.startswith("t000#") for section_id in toolset.seen_sections)


def test_inspect_candidates_parallelizes_rows(toolset, monkeypatch):
    ids = ["t000", "t001", "t002", "t003", "t004", "t000", "t001", "t002"]
    toolset.seen.update(ids)

    def slow_features(args):
        time.sleep(0.05)
        return {
            "track_id": args["track_id"],
            "bpm": 124.0,
            "camelot": "8A",
            "duration_s": 300.0,
            "genre": None,
        }

    def slow_sections(args):
        time.sleep(0.05)
        return {"track_id": args["track_id"], "sections": []}

    def slow_energy(args):
        time.sleep(0.05)
        return {"track_id": args["track_id"], "energy": 64.0, "breakdown": {}}

    monkeypatch.setattr(toolset, "get_track_features", slow_features)
    monkeypatch.setattr(toolset, "get_track_sections", slow_sections)
    monkeypatch.setattr(toolset, "get_track_energy", slow_energy)

    started = time.perf_counter()
    out = toolset.inspect_candidates({"track_ids": ids})
    elapsed = time.perf_counter() - started

    assert out["track_ids"] == ids
    assert [row["track_id"] for row in out["candidates"]] == ids
    assert elapsed < 0.65


def test_inspect_candidates_rejects_unseen_ids_per_row(toolset, monkeypatch):
    monkeypatch.setattr(energy_mod, "score_energy_cached", lambda *a, **k: None)
    toolset.seen.add("t000")

    out = toolset.inspect_candidates({"track_ids": ["t000", "GHOST"]})

    assert out["track_ids"] == ["t000"]
    assert "features" in out["candidates"][0]
    rejected = out["candidates"][1]
    assert rejected["track_id"] == "GHOST"
    assert "invented" in rejected["error"]
    assert "features" not in rejected
    assert "sections" not in rejected
    assert "energy" not in rejected


def test_inspect_candidates_caps_large_batches(toolset, monkeypatch):
    monkeypatch.setattr(energy_mod, "score_energy_cached", lambda *a, **k: None)
    toolset.seen.add("t000")

    out = toolset.inspect_candidates({"track_ids": ["t000"] * (MAX_INSPECT_CANDIDATES + 1)})

    assert out["truncated"] is True
    assert len(out["candidates"]) == MAX_INSPECT_CANDIDATES
    assert "truncated" in out["note"]


def test_get_track_sections_preserves_materialized_auto_hot_cue_slots(toolset):
    toolset.seen.add("t000")
    toolset._library.tracks["t000"] = TrackEntry(
        track_id="t000",
        title="Auto Section Track",
        artist="Artist",
        album="A",
        bpm=128.0,
        key="8A",
        duration_s=300.0,
        cues=(
            CuePoint(
                name="INTRO",
                type="cue",
                start_s=0.0,
                end_s=64.0,
                number=0,
                source="auto",
                confidence=0.88,
            ),
            CuePoint(
                name="DROP",
                type="cue",
                start_s=96.0,
                end_s=176.0,
                number=3,
                source="auto",
                confidence=0.9,
            ),
            CuePoint(
                name="OUTRO",
                type="cue",
                start_s=240.0,
                end_s=300.0,
                number=5,
                source="auto",
                confidence=0.86,
            ),
        ),
        filepath="/tmp/t000.mp3",
    )

    out = toolset.get_track_sections({"track_id": "t000"})

    assert [section["role"] for section in out["sections"]] == ["intro", "drop", "outro"]
    assert [section["cue_slot"] for section in out["sections"]] == ["A", "D", "F"]
    assert {section["cue_source"] for section in out["sections"]} == {"auto"}
    assert {section["source_detail"] for section in out["sections"]} == {"auto_cue"}


def test_transition_slate_issues_grounded_candidates(toolset):
    toolset.seen.update({"t000", "t001"})
    toolset._library.tracks["t000"] = TrackEntry(
        track_id="t000",
        title="Outgoing",
        artist="Artist",
        album="A",
        bpm=128.0,
        key="8A",
        duration_s=300.0,
        cues=(CuePoint(name="OUT", type="cue", start_s=240.0, end_s=None, number=5),),
        filepath="/tmp/t000.mp3",
    )
    toolset._library.tracks["t001"] = TrackEntry(
        track_id="t001",
        title="Incoming",
        artist="Artist",
        album="A",
        bpm=128.0,
        key="9A",
        duration_s=300.0,
        cues=(CuePoint(name="IN", type="cue", start_s=0.0, end_s=None, number=0),),
        filepath="/tmp/t001.mp3",
    )

    out = toolset.transition_slate(
        {
            "source_track_id": "t000",
            "candidate_track_ids": ["t001"],
            "mode": "live",
            "remaining_bars": 16,
            "playhead_confidence": 0.95,
        }
    )

    assert out["source_section_id"] == "t000#s000"
    assert len(out["candidates"]) == 1
    candidate = out["candidates"][0]
    assert candidate["candidate_id"] == "tr_001"
    assert candidate["to_track_id"] == "t001"
    assert candidate["from_role"] == "outro"
    assert candidate["to_role"] == "intro"
    assert candidate["from_start_s"] == 240.0
    assert candidate["to_start_s"] == 0.0
    assert candidate["from_camelot"] == "8A"
    assert candidate["to_camelot"] == "9A"
    assert candidate["cue_slot"] == "A"
    assert candidate["start_in_bars"] == 16
    assert candidate["semantic_basis"] == "track_vector_fallback"
    assert candidate["move_grade"]["slug"] in {"clean", "sexy", "bomb", "lit_aff"}
    assert candidate["move_grade"]["xp"] > 0
    assert "tr_001" in toolset.issued_transition_candidates


def test_transition_slate_uses_section_vectors_when_available(store, library):
    store.section_vectors = {
        "t000#s000": np.array([1.0, 0.0], dtype=np.float32),
        "t001#s000": np.array([0.95, 0.05], dtype=np.float32),
    }
    toolset = LibraryToolset(embedder=None, store=store, library=library)
    toolset.seen.update({"t000", "t001"})
    toolset._library.tracks["t000"] = TrackEntry(
        track_id="t000",
        title="Outgoing",
        artist="Artist",
        album="A",
        bpm=128.0,
        key="8A",
        duration_s=300.0,
        cues=(CuePoint(name="OUT", type="cue", start_s=240.0, end_s=None, number=5),),
        filepath="/tmp/t000.mp3",
    )
    toolset._library.tracks["t001"] = TrackEntry(
        track_id="t001",
        title="Incoming",
        artist="Artist",
        album="A",
        bpm=128.0,
        key="9A",
        duration_s=300.0,
        cues=(CuePoint(name="IN", type="cue", start_s=0.0, end_s=None, number=0),),
        filepath="/tmp/t001.mp3",
    )

    out = toolset.transition_slate({"source_track_id": "t000", "candidate_track_ids": ["t001"]})

    assert out["candidates"][0]["semantic_basis"] == "section_vector"
    assert out["candidates"][0]["components"]["semantic"] > 0.9


def test_transition_slate_rejects_unseen_candidate(toolset):
    toolset.seen.add("t000")
    out = toolset.transition_slate({"source_track_id": "t000", "candidate_track_ids": ["GHOST"]})

    assert "error" in out
    assert "invented" in out["error"]


def test_compile_musical_context_uses_issued_candidates_and_redacts(toolset):
    toolset.seen.update({"t000", "t001"})
    toolset._library.tracks["t000"] = TrackEntry(
        track_id="t000",
        title="Outgoing",
        artist="Artist",
        album="A",
        bpm=128.0,
        key="8A",
        duration_s=300.0,
        cues=(CuePoint(name="OUT", type="cue", start_s=240.0, end_s=None, number=5),),
        filepath="/tmp/t000.mp3",
    )
    toolset._library.tracks["t001"] = TrackEntry(
        track_id="t001",
        title="Incoming",
        artist="Artist",
        album="A",
        bpm=128.0,
        key="9A",
        duration_s=300.0,
        cues=(CuePoint(name="IN", type="cue", start_s=0.0, end_s=None, number=0),),
        filepath="/tmp/t001.mp3",
    )
    slate = toolset.transition_slate({"source_track_id": "t000", "candidate_track_ids": ["t001"]})
    candidate_id = slate["candidates"][0]["candidate_id"]

    out = toolset.compile_musical_context(
        {
            "candidate_ids": [candidate_id],
            "mode": "prep",
            "current": {"active_track_id": "t000", "filepath": "/tmp/private.mp3"},
        }
    )

    packet = out["packet"]
    assert packet["packet_id"] == "ctx_001"
    assert packet["candidates"][0]["candidate_id"] == candidate_id
    assert "filepath" not in packet["current"]
    assert "ctx_001" in toolset.issued_context_packets


def test_compile_musical_context_rejects_unknown_candidate(toolset):
    out = toolset.compile_musical_context({"candidate_ids": ["tr_404"]})

    assert "error" in out
    assert "not issued" in out["error"]


# --------------------------------------------------------------------------- #
# smart_hot_cues / export_smart_cues — auto cue provenance through Viber
# --------------------------------------------------------------------------- #


def test_smart_hot_cues_exports_materialized_auto_cues(toolset, tmp_path):
    toolset.seen.add("t001")
    toolset._library.tracks["t001"] = TrackEntry(
        track_id="t001",
        title="Auto Cued",
        artist="Artist",
        album="A",
        bpm=128.0,
        key="9A",
        duration_s=300.0,
        cues=(
            CuePoint(
                name="INTRO",
                type="cue",
                start_s=0.0,
                end_s=64.0,
                number=0,
                source="auto",
                confidence=0.88,
            ),
            CuePoint(
                name="DROP",
                type="cue",
                start_s=96.0,
                end_s=176.0,
                number=3,
                source="auto",
                confidence=0.9,
            ),
            CuePoint(
                name="OUTRO",
                type="cue",
                start_s=240.0,
                end_s=300.0,
                number=5,
                source="auto",
                confidence=0.86,
            ),
        ),
        filepath="/tmp/t001.mp3",
    )

    issued = toolset.smart_hot_cues({"track_id": "t001"})

    proposal = issued["proposals"][0]
    assert proposal["proposal_id"] in toolset.issued_cue_proposals
    by_slot = {cue["slot"]: cue for cue in proposal["cues"]}
    assert by_slot["A"]["source"] == "auto"
    assert tuple(by_slot["A"]["reason_codes"]) == ("high_confidence",)
    assert by_slot["A"]["export_label"] == "VM A IN"

    out_xml = tmp_path / "auto-cues.xml"
    cue_id = by_slot["A"]["cue_id"]
    exported = toolset.export_smart_cues(
        {
            "proposal_id": proposal["proposal_id"],
            "selected_cue_ids": [cue_id],
            "include_review": True,
            "out_path": str(out_xml),
        }
    )

    assert exported.get("exported") is True
    assert exported["cue_count"] == 1
    assert exported["cue_ids"] == [cue_id]
    mark = ET.parse(out_xml).getroot().find(".//POSITION_MARK")
    assert mark is not None
    assert mark.attrib["Name"] == "VM A IN"
    assert mark.attrib["Num"] == "0"


# --------------------------------------------------------------------------- #
# export_set — rejects un-seen ids + re-validates against the library
# --------------------------------------------------------------------------- #


def test_export_set_rejects_unseen_ids(toolset):
    out = toolset.export_set({"name": "Set", "track_ids": ["t001"]})
    assert "error" in out
    assert "invented" in out["error"]


def test_export_set_writes_grounded_xml(toolset, tmp_path):
    toolset.discover_pool({"ref_track_ids": ["t000"], "k": 10})
    seen_ids = sorted(toolset.seen)[:2]
    out_xml = tmp_path / "set.xml"
    out = toolset.export_set({"name": "Test Set", "track_ids": seen_ids, "out_path": str(out_xml)})
    assert out.get("exported") is True
    assert out["path"] == str(out_xml)
    assert out_xml.exists()
    assert out["written"] >= 1


def test_export_set_default_path_is_visible_music_cue_folder(toolset, tmp_path, monkeypatch):
    toolset.seen.add("t000")
    monkeypatch.setattr(pathlib.Path, "home", lambda: tmp_path)

    out = toolset.export_set({"name": "Peak Set!", "track_ids": ["t000"], "cue": False})

    expected = tmp_path / "Music" / "vibemix" / "cues" / "peak-set.xml"
    expected_m3u8 = tmp_path / "Music" / "vibemix" / "cues" / "peak-set.m3u8"
    assert out.get("exported") is True
    assert out["target"] == "both"
    assert out["path"] == str(expected)
    assert out["outputs"] == {"rekordbox": str(expected), "m3u8": str(expected_m3u8)}
    assert expected.exists()
    assert expected_m3u8.exists()


def test_export_set_target_m3u8_writes_order_only_crate(toolset, tmp_path):
    toolset.seen.add("t000")
    out_m3u8 = tmp_path / "crate.m3u8"

    out = toolset.export_set(
        {
            "name": "Portable Crate",
            "track_ids": ["t000"],
            "out_path": str(out_m3u8),
            "target": "m3u8",
        }
    )

    assert out.get("exported") is True
    assert out["target"] == "m3u8"
    assert out["auto_cues"]["enabled"] is False
    assert out["auto_cues"]["tracks_attempted"] == 0
    assert out["path"] == str(out_m3u8)
    assert out["outputs"] == {"m3u8": str(out_m3u8)}
    assert out["written"] == 1
    lines = out_m3u8.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "#EXTM3U"
    assert lines[-1] == "/tmp/t000.mp3"


def test_export_set_serato_tags_requires_explicit_permission(toolset):
    toolset.seen.add("t000")

    out = toolset.export_set({"name": "Tag Write", "track_ids": ["t000"], "target": "serato_tags"})

    assert "error" in out
    assert "tag_write_granted=True" in out["error"]


@pytest.mark.skipif(not _REAL_MP3.exists(), reason="needs the in-repo test mp3")
def test_export_set_serato_tags_writes_vm_cues_with_permission(toolset, tmp_path, monkeypatch):
    pytest.importorskip("mutagen")
    dst = tmp_path / "track.mp3"
    shutil.copy(_REAL_MP3, dst)
    toolset.seen.add("t000")
    toolset._library.tracks["t000"] = replace(_track("t000", bpm=120.0), filepath=str(dst))
    monkeypatch.setattr(
        tool_mod,
        "sections_for_entry",
        lambda entry: (
            _section(f"{entry.track_id}#intro", "intro", 10.21, 32.0),
            _section(f"{entry.track_id}#drop", "drop", 64.26, 128.0),
        ),
    )

    out = toolset.export_set(
        {
            "name": "Tag Write",
            "track_ids": ["t000"],
            "target": "serato_tags",
            "tag_write_granted": True,
        }
    )

    assert out.get("exported") is True
    assert out["target"] == "serato_tags"
    assert out["outputs"] == {}
    assert out["tag_receipts"][0]["tagged"] == 1
    assert out["auto_cues"]["snap_adjusted_count"] >= 2
    from vibemix.library.export_serato import read_serato_cues

    cues = {cue.name: cue for cue in read_serato_cues(dst)}
    assert "VM A IN" in cues
    assert "VM D DROP" in cues
    assert cues["VM A IN"].position_ms == 10000
    assert cues["VM D DROP"].position_ms == 64500


@pytest.mark.skipif(not _REAL_MP3.exists(), reason="needs the in-repo test mp3")
def test_export_set_all_writes_xml_m3u8_and_markers2_tags(toolset, tmp_path, monkeypatch):
    pytest.importorskip("mutagen")
    dst = tmp_path / "track.mp3"
    shutil.copy(_REAL_MP3, dst)
    toolset.seen.add("t000")
    toolset._library.tracks["t000"] = replace(_track("t000", bpm=120.0), filepath=str(dst))
    monkeypatch.setattr(
        tool_mod,
        "sections_for_entry",
        lambda entry: (
            _section(f"{entry.track_id}#intro", "intro", 10.21, 32.0),
            _section(f"{entry.track_id}#drop", "drop", 64.26, 128.0),
        ),
    )
    out_xml = tmp_path / "all.xml"
    events = tmp_path / "tool_events.jsonl"
    monkeypatch.setenv("VIBEMIX_TOOL_EVENTS_FILE", str(events))

    out = toolset.dispatch(
        "export_set",
        {
            "name": "All DJ",
            "track_ids": ["t000"],
            "out_path": str(out_xml),
            "target": "all",
            "tag_write_granted": True,
        },
    )

    assert out.get("exported") is True
    assert out["target"] == "all"
    assert out["outputs"] == {
        "rekordbox": str(out_xml),
        "m3u8": str(tmp_path / "all.m3u8"),
    }
    assert out["tag_receipts"][0]["carrier"] == "markers2_tags"
    assert out["tag_receipts"][0]["compatible_apps"] == ["Serato", "Mixxx"]
    assert out["tag_receipts"][0]["tagged"] == 1
    instructions = out["import_instructions"]
    assert [row["carrier"] for row in instructions] == [
        "rekordbox_xml",
        "m3u8",
        "markers2_tags",
    ]
    assert instructions[0]["app"] == "Rekordbox"
    assert instructions[0]["path"] == str(out_xml)
    assert "Imported Library" in instructions[0]["instruction"]
    assert instructions[1]["path"] == str(tmp_path / "all.m3u8")
    assert instructions[2]["writes_audio_tags"] is True
    assert instructions[2]["files"] == [str(dst)]
    assert "rescan" in instructions[2]["instruction"]
    assert out["auto_cues"]["cues_added"] == 2
    assert out_xml.exists()
    assert (tmp_path / "all.m3u8").exists()
    from vibemix.library.export_serato import read_serato_cues

    cues = {cue.name: cue for cue in read_serato_cues(dst)}
    assert cues["VM A IN"].position_ms == 10000
    assert cues["VM D DROP"].position_ms == 64500
    rec = json.loads(events.read_text(encoding="utf-8").splitlines()[0])
    assert rec["tool"] == "export_set"
    assert rec["receipt"]["target"] == "all"
    assert rec["receipt"]["outputs"] == out["outputs"]
    assert rec["receipt"]["tag_receipts"][0]["carrier"] == "markers2_tags"
    assert [row["carrier"] for row in rec["receipt"]["import_instructions"]] == [
        "rekordbox_xml",
        "m3u8",
        "markers2_tags",
    ]
    assert rec["receipt"]["auto_cues"]["cues_added"] == 2


def test_export_set_forwards_rekordbox_cues_and_beatgrid(toolset, tmp_path):
    toolset.discover_pool({"ref_track_ids": ["t000"], "k": 10})
    toolset.seen.add("t000")
    toolset._library.tracks["t000"] = TrackEntry(
        track_id="t000",
        title="Cued Track",
        artist="Artist",
        album="A",
        bpm=128.0,
        key="8A",
        duration_s=300.0,
        cues=(
            CuePoint(name="DROP", type="cue", start_s=64.0, end_s=None, number=0),
            CuePoint(name="LOOP", type="loop", start_s=96.0, end_s=104.0, number=1),
        ),
        filepath="/tmp/t000.mp3",
        beatgrid=(TempoNode(inizio_s=0.012, bpm=128.0, metro="4/4", battito=1),),
    )

    out_xml = tmp_path / "cued.xml"
    out = toolset.export_set(
        {"name": "Cued", "track_ids": ["t000"], "out_path": str(out_xml), "cue": False}
    )

    assert out.get("exported") is True
    track = ET.parse(out_xml).getroot().find("COLLECTION/TRACK")
    assert track is not None
    assert track.find("TEMPO") is not None
    marks = {m.attrib["Name"]: m for m in track.findall("POSITION_MARK")}
    assert set(marks) == {"DROP", "LOOP"}
    assert marks["DROP"].attrib["Num"] == "0"
    assert marks["LOOP"].attrib["Type"] == "4"


def test_export_set_auto_cues_empty_slots_by_default(toolset, tmp_path, monkeypatch):
    toolset.seen.add("t000")
    monkeypatch.setattr(
        tool_mod,
        "sections_for_entry",
        lambda entry: (
            _section(f"{entry.track_id}#intro", "intro", 0.0, 32.0),
            _section(f"{entry.track_id}#drop", "drop", 64.0, 128.0),
            _section(f"{entry.track_id}#outro", "outro", 192.0, 240.0),
        ),
    )

    out_xml = tmp_path / "auto-cued.xml"
    out = toolset.export_set({"name": "Auto Cued", "track_ids": ["t000"], "out_path": str(out_xml)})

    assert out.get("exported") is True
    assert out["auto_cues"]["enabled"] is True
    assert out["auto_cues"]["tracks_attempted"] == 1
    assert out["auto_cues"]["tracks_cued"] == 1
    assert out["auto_cues"]["cues_added"] >= 3
    assert out["auto_cues"]["proposal_export_ready_count"] >= out["auto_cues"]["cues_added"]
    marks = ET.parse(out_xml).getroot().findall(".//POSITION_MARK")
    names = {mark.attrib["Name"] for mark in marks}
    assert {"VM A IN", "VM D DROP", "VM F OUT"} <= names


def test_export_set_auto_cues_route_through_cue_landing_spine(
    toolset, tmp_path, monkeypatch
):
    """W13: live Viber auto-cues use the same mark projection as land()."""
    toolset.seen.add("t000")
    calls = []
    real_projection = cue_landing_mod.export_marks_for_cueset

    def spy_projection(cueset):
        calls.append(cueset)
        return real_projection(cueset)

    monkeypatch.setattr(cue_landing_mod, "export_marks_for_cueset", spy_projection)
    monkeypatch.setattr(
        tool_mod,
        "sections_for_entry",
        lambda entry: (
            _section(f"{entry.track_id}#intro", "intro", 0.0, 32.0),
            _section(f"{entry.track_id}#drop", "drop", 64.0, 128.0),
        ),
    )

    out_xml = tmp_path / "cue-landing-spine.xml"
    out = toolset.export_set({"name": "Cue Landing Spine", "track_ids": ["t000"], "out_path": str(out_xml)})

    assert out.get("exported") is True
    assert calls, "export_set auto-cue bypassed cue_landing.export_marks_for_cueset"
    assert calls[0].track_id == "t000"
    assert calls[0].summary.machine_count == len(calls[0].cues)
    marks = ET.parse(out_xml).getroot().findall(".//POSITION_MARK")
    names = {mark.attrib["Name"] for mark in marks}
    assert {"VM A IN", "VM D DROP"} <= names


def test_export_set_auto_cues_snap_to_exported_bpm_grid(toolset, tmp_path, monkeypatch):
    """Machine-authored pads land on the TEMPO grid exported to Rekordbox."""
    toolset.seen.add("t000")
    toolset._library.tracks["t000"] = _track("t000", bpm=120.0)
    monkeypatch.setattr(
        tool_mod,
        "sections_for_entry",
        lambda entry: (
            _section(f"{entry.track_id}#intro", "intro", 10.21, 32.0),
            _section(f"{entry.track_id}#drop", "drop", 64.26, 128.0),
        ),
    )

    out_xml = tmp_path / "snap-bpm-grid.xml"
    out = toolset.export_set({"name": "Snap Grid", "track_ids": ["t000"], "out_path": str(out_xml)})

    assert out.get("exported") is True
    assert out["auto_cues"]["snap_adjusted_count"] >= 2
    assert out["auto_cues"]["snap_max_adjustment_ms"] == pytest.approx(240.0)
    track = ET.parse(out_xml).getroot().find("COLLECTION/TRACK")
    assert track is not None
    tempo = track.find("TEMPO")
    assert tempo is not None
    assert float(tempo.attrib["Bpm"]) == pytest.approx(120.0)
    marks = {m.attrib["Name"]: m for m in track.findall("POSITION_MARK")}
    assert float(marks["VM A IN"].attrib["Start"]) == pytest.approx(10.0)
    assert float(marks["VM D DROP"].attrib["Start"]) == pytest.approx(64.5)


def test_export_set_auto_cues_materialize_for_live_pill(toolset, tmp_path, monkeypatch):
    """Viber-landed VM cues become visible to next_suggestion without re-import."""
    from vibemix.library.section_builder import sections_for_entry as real_sections_for_entry

    toolset.seen.add("t000")
    toolset._library.tracks["t000"] = _track("t000", bpm=120.0)
    monkeypatch.setattr(
        tool_mod,
        "sections_for_entry",
        lambda entry: (
            _section(f"{entry.track_id}#intro", "intro", 10.21, 32.0),
            _section(f"{entry.track_id}#drop", "drop", 64.26, 128.0),
        ),
    )

    out_xml = tmp_path / "pill-visible.xml"
    out = toolset.export_set(
        {"name": "Pill Visible", "track_ids": ["t000"], "out_path": str(out_xml)}
    )

    assert out.get("exported") is True
    assert out["pill_cues_materialized"] == {"tracks": 1, "cues": 2}
    materialized = toolset._library.tracks["t000"]
    by_name = {cue.name: cue for cue in materialized.cues}
    assert by_name["VM A IN"].start_s == pytest.approx(10.0)
    assert by_name["VM A IN"].number == 0
    assert by_name["VM A IN"].source == "anlz"
    assert by_name["VM A IN"].confidence == pytest.approx(0.92)
    assert by_name["VM D DROP"].start_s == pytest.approx(64.5)
    assert by_name["VM D DROP"].number == 3

    sections = {section.cue_slot: section for section in real_sections_for_entry(materialized)}
    assert sections["A"].cue_source == "anlz"
    assert sections["A"].cue_confidence == pytest.approx(0.92)
    assert sections["D"].role == "drop"


def test_viber_exported_auto_cues_drive_next_suggestion_pill(
    toolset, store, tmp_path, monkeypatch
) -> None:
    """A Viber-built set's landed cues feed the pill transition payload immediately."""
    toolset.seen.add("t001")
    toolset._library.tracks["t000"] = replace(
        _track("t000", bpm=124.0, key="8A"),
        cues=(CuePoint(name="OUT", type="cue", start_s=224.0, end_s=None, number=5),),
    )
    toolset._library.tracks["t001"] = _track("t001", bpm=124.0, key="9A")
    monkeypatch.setattr(
        tool_mod,
        "sections_for_entry",
        lambda entry: (
            _section(f"{entry.track_id}#intro", "intro", 0.0, 32.0),
            _section(f"{entry.track_id}#drop", "drop", 64.0, 128.0),
        ),
    )

    out_xml = tmp_path / "viber-to-pill.xml"
    out = toolset.export_set(
        {"name": "Viber To Pill", "track_ids": ["t001"], "out_path": str(out_xml)}
    )

    assert out.get("exported") is True
    assert out["pill_cues_materialized"] == {"tracks": 1, "cues": 2}

    suggestion = next_suggestion(
        store,
        toolset._library,
        seed_vector=np.ones(8, dtype=np.float32),
        seed_track_id="t000",
        played_ids=set(),
        source_deck="A",
        target_deck="B",
    )

    assert suggestion is not None
    assert suggestion.track_id == "t001"
    assert suggestion.transition is not None
    assert suggestion.transition["target_deck"] == "B"
    assert suggestion.transition["cue_slot"] == "A"
    assert suggestion.transition["cue_source"] == "anlz"
    assert suggestion.transition["cue_confidence"] == pytest.approx(0.92)
    assert suggestion.transition["from_role"] == "outro"
    assert suggestion.transition["to_role"] == "intro"
    assert "outro into intro is a strong role pair" in suggestion.transition["reasons"]
    assert "cue vm a in @ 0:00" in suggestion.why


def test_export_set_auto_cues_snap_to_real_grid_inizio(toolset, tmp_path, monkeypatch):
    """Machine cue snap respects a persisted Rekordbox beatgrid phase."""
    toolset.seen.add("t000")
    toolset._library.tracks["t000"] = TrackEntry(
        track_id="t000",
        title="Gridded Track",
        artist="Artist",
        album="A",
        bpm=120.0,
        key="8A",
        duration_s=300.0,
        cues=(),
        filepath="/tmp/t000.mp3",
        beatgrid=(TempoNode(inizio_s=0.125, bpm=120.0, metro="4/4", battito=1),),
    )
    monkeypatch.setattr(
        tool_mod,
        "sections_for_entry",
        lambda entry: (_section(f"{entry.track_id}#intro", "intro", 10.21, 32.0),),
    )

    out_xml = tmp_path / "snap-real-grid.xml"
    out = toolset.export_set(
        {"name": "Snap Real Grid", "track_ids": ["t000"], "out_path": str(out_xml)}
    )

    assert out.get("exported") is True
    track = ET.parse(out_xml).getroot().find("COLLECTION/TRACK")
    assert track is not None
    tempo = track.find("TEMPO")
    assert tempo is not None
    assert float(tempo.attrib["Inizio"]) == pytest.approx(0.125)
    mark = track.find("POSITION_MARK")
    assert mark is not None
    assert mark.attrib["Name"] == "VM A IN"
    assert float(mark.attrib["Start"]) == pytest.approx(10.125)


def test_export_set_auto_cues_from_producer_when_cache_sections_are_not_ready(
    toolset, tmp_path, monkeypatch
):
    import vibemix.library.cue_engine as cue_engine

    toolset.seen.add("t000")
    monkeypatch.setattr(tool_mod, "sections_for_entry", lambda entry: ())
    monkeypatch.setattr(
        cue_engine,
        "detect_cues_auto",
        lambda *_args, **_kwargs: [
            CueAnchor("intro", 0.0, 32.0, 0.93, "auto"),
            CueAnchor("drop", 64.0, 128.0, 0.94, "auto"),
        ],
    )

    out_xml = tmp_path / "producer-cued.xml"
    out = toolset.export_set(
        {"name": "Producer Cued", "track_ids": ["t000"], "out_path": str(out_xml)}
    )

    assert out.get("exported") is True
    assert out["auto_cues"]["tracks_cued"] == 1
    marks = {m.attrib["Name"]: m for m in ET.parse(out_xml).getroot().findall(".//POSITION_MARK")}
    assert marks["VM A IN"].attrib["Num"] == "0"
    assert marks["VM D DROP"].attrib["Num"] == "3"


def test_export_set_no_cue_opt_out_skips_auto_cue(toolset, tmp_path, monkeypatch):
    toolset.seen.add("t000")

    def fail_sections(_entry):
        raise AssertionError("sections_for_entry should not run when cue=False")

    monkeypatch.setattr(tool_mod, "sections_for_entry", fail_sections)
    out_xml = tmp_path / "no-cue.xml"
    out = toolset.export_set(
        {"name": "No Cues", "track_ids": ["t000"], "out_path": str(out_xml), "cue": False}
    )

    assert out.get("exported") is True
    assert out["auto_cues"]["enabled"] is False
    assert out["auto_cues"]["tracks_attempted"] == 0
    assert ET.parse(out_xml).getroot().find(".//POSITION_MARK") is None


def test_export_set_auto_cues_fill_empty_slots_without_clobbering_dj(
    toolset, tmp_path, monkeypatch
):
    toolset.seen.add("t000")
    toolset._library.tracks["t000"] = TrackEntry(
        track_id="t000",
        title="Cued Track",
        artist="Artist",
        album="A",
        bpm=128.0,
        key="8A",
        duration_s=300.0,
        cues=(CuePoint(name="MY A", type="cue", start_s=4.0, end_s=None, number=0),),
        filepath="/tmp/t000.mp3",
    )
    monkeypatch.setattr(
        tool_mod,
        "sections_for_entry",
        lambda entry: (
            _section(f"{entry.track_id}#intro", "intro", 0.0, 32.0),
            _section(f"{entry.track_id}#drop", "drop", 64.0, 128.0),
        ),
    )

    out_xml = tmp_path / "preserve.xml"
    out = toolset.export_set({"name": "Preserve", "track_ids": ["t000"], "out_path": str(out_xml)})

    assert out.get("exported") is True
    marks = {m.attrib["Name"]: m for m in ET.parse(out_xml).getroot().findall(".//POSITION_MARK")}
    assert marks["MY A"].attrib["Num"] == "0"
    assert "VM MY A" not in marks
    assert marks["VM D DROP"].attrib["Num"] == "3"
    materialized_names = {cue.name for cue in toolset._library.tracks["t000"].cues}
    assert "MY A" in materialized_names
    assert "VM MY A" not in materialized_names
    assert "VM D DROP" in materialized_names


def test_export_set_auto_cue_snap_preserves_dj_offgrid_cues(toolset, tmp_path, monkeypatch):
    """DJ-authored pads may be intentionally off-grid; never quantize them."""
    toolset.seen.add("t000")
    toolset._library.tracks["t000"] = TrackEntry(
        track_id="t000",
        title="Human Cued Track",
        artist="Artist",
        album="A",
        bpm=120.0,
        key="8A",
        duration_s=300.0,
        cues=(CuePoint(name="MY A", type="cue", start_s=4.21, end_s=None, number=0),),
        filepath="/tmp/t000.mp3",
    )
    monkeypatch.setattr(
        tool_mod,
        "sections_for_entry",
        lambda entry: (_section(f"{entry.track_id}#drop", "drop", 64.26, 128.0),),
    )

    out_xml = tmp_path / "preserve-dj-offgrid.xml"
    out = toolset.export_set(
        {"name": "Preserve DJ Offgrid", "track_ids": ["t000"], "out_path": str(out_xml)}
    )

    assert out.get("exported") is True
    marks = {m.attrib["Name"]: m for m in ET.parse(out_xml).getroot().findall(".//POSITION_MARK")}
    assert float(marks["MY A"].attrib["Start"]) == pytest.approx(4.21)
    assert float(marks["VM D DROP"].attrib["Start"]) == pytest.approx(64.5)


def test_export_set_records_exported_on_toolset(toolset, tmp_path):
    """BL-02: a successful export_set records the ExportResult on the toolset
    (mirrors ``created``) so the agent loop can break on it."""
    from vibemix.library.export_rekordbox import ExportResult

    assert toolset.exported is None
    toolset.discover_pool({"ref_track_ids": ["t000"], "k": 10})
    seen_ids = sorted(toolset.seen)[:2]
    out_xml = tmp_path / "recorded.xml"
    out = toolset.export_set({"name": "Recorded", "track_ids": seen_ids, "out_path": str(out_xml)})
    assert out.get("exported") is True
    assert isinstance(toolset.exported, ExportResult)
    assert str(toolset.exported.path) == str(out_xml)


def test_export_set_revalidates_against_library(toolset, tmp_path):
    """An id that is in seen but vanished from the library is dropped (gate #2),
    never crashing the export."""
    toolset.discover_pool({"ref_track_ids": ["t000"], "k": 10})
    seen_ids = sorted(toolset.seen)
    # Force gate #1 to pass for a now-missing id, then remove it from the library.
    toolset.seen.add("t000")
    victim = seen_ids[0]
    del toolset._library.tracks[victim]
    out_xml = tmp_path / "set2.xml"
    out = toolset.export_set(
        {
            "name": "Revalidate",
            "track_ids": [victim, *[i for i in seen_ids if i != victim]],
            "out_path": str(out_xml),
        }
    )
    assert out.get("exported") is True
    # The vanished track was silently dropped (re-validation), survivors written.
    assert out_xml.exists()


# --------------------------------------------------------------------------- #
# dispatch wiring — the 4 tools are reachable + never raise
# --------------------------------------------------------------------------- #


def test_dispatch_registers_setprep_tools(toolset):
    assert "error" in toolset.dispatch("get_track_energy", {"track_id": "NOPE"})
    assert "error" in toolset.dispatch("get_track_sections", {"track_id": "NOPE"})
    assert "error" in toolset.dispatch("inspect_candidates", {"track_ids": []})
    assert "error" in toolset.dispatch("transition_slate", {})
    assert "error" in toolset.dispatch("compile_musical_context", {})
    assert "error" in toolset.dispatch("discover_pool", {})
    assert "error" in toolset.dispatch("sequence_set", {"track_ids": [], "curve": "x"})
    assert "error" in toolset.dispatch("export_set", {"name": "", "track_ids": []})


def test_dispatch_gives_batched_candidate_inspection_a_larger_timeout(toolset, monkeypatch):
    seen_timeouts: list[float | None] = []
    original_result = tool_mod.concurrent.futures.Future.result

    def spy_result(self, timeout=None):
        seen_timeouts.append(timeout)
        return original_result(self, timeout=timeout)

    monkeypatch.setattr(tool_mod.concurrent.futures.Future, "result", spy_result)

    toolset.dispatch("inspect_candidates", {"track_ids": []})
    toolset.dispatch("get_track_features", {"track_id": "NOPE"})

    assert tool_mod.BATCH_TOOL_CALL_TIMEOUT_S > tool_mod.TOOL_CALL_TIMEOUT_S
    assert tool_mod.BATCH_TOOL_CALL_TIMEOUT_S in seen_timeouts
    assert tool_mod.TOOL_CALL_TIMEOUT_S in seen_timeouts
