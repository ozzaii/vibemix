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

import numpy as np
import pytest

from vibemix.library import energy as energy_mod
from vibemix.library import toolset as tool_mod
from vibemix.library.rekordbox import RekordboxLibrary, TrackEntry
from vibemix.library.toolset import LibraryToolset


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


class _FakeBackend:
    def __init__(self, ids, vectors):
        self._ids, self._vectors = ids, vectors

    def load_all(self):
        return self._ids, self._vectors


class _FakeStore:
    def __init__(self, ids, vectors, ranked):
        self._backend = _FakeBackend(ids, vectors)
        self._ranked = ranked  # list[(track_id, sim)]

    def search_centered(self, qvec, k=10):
        return self._ranked[:k]


@pytest.fixture
def library() -> RekordboxLibrary:
    lib = RekordboxLibrary()
    # Spread keys so harmonic gates pass, distinct enough to sequence.
    keys = ["8A", "9A", "8B", "7A", "8A"]
    lib.tracks = {
        f"t{i:03d}": _track(f"t{i:03d}", bpm=124.0 + i, key=keys[i])
        for i in range(5)
    }
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
    monkeypatch.setattr(
        e, "score_energy", lambda *a, **k: e.EnergyScore(score=33.0, breakdown={})
    )
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


def test_discover_pool_error_when_no_inputs(toolset):
    out = toolset.discover_pool({})
    assert "error" in out


# --------------------------------------------------------------------------- #
# sequence_set — rejects ids not in seen (grounding gate)
# --------------------------------------------------------------------------- #


def test_sequence_set_rejects_unseen_ids(toolset):
    # Nothing discovered yet → every id is "invented".
    out = toolset.sequence_set(
        {"track_ids": ["t000", "t001"], "curve": "peak_time"}
    )
    assert "error" in out
    assert "invented" in out["error"]


def test_sequence_set_orders_seen_pool(toolset):
    toolset.discover_pool({"ref_track_ids": ["t000"], "k": 10})
    seen_ids = sorted(toolset.seen)
    assert len(seen_ids) >= 2
    out = toolset.sequence_set(
        {"track_ids": seen_ids, "curve": "peak_time"}
    )
    assert "candidates" in out
    assert out["candidates"]
    first = out["candidates"][0]
    assert "track_ids" in first
    assert "energy_fit" in first
    assert "avg_coherence" in first
    # Every sequenced id is a real, grounded id.
    assert set(first["track_ids"]).issubset(toolset.seen)


def test_sequence_set_unknown_curve_is_actionable(toolset):
    toolset.discover_pool({"ref_track_ids": ["t000"], "k": 10})
    out = toolset.sequence_set(
        {"track_ids": sorted(toolset.seen), "curve": "no_such_curve"}
    )
    assert "error" in out


# --------------------------------------------------------------------------- #
# export_set — rejects un-seen ids + re-validates against the library
# --------------------------------------------------------------------------- #


def test_export_set_rejects_unseen_ids(toolset):
    out = toolset.export_set(
        {"name": "Set", "track_ids": ["t001"]}
    )
    assert "error" in out
    assert "invented" in out["error"]


def test_export_set_writes_grounded_xml(toolset, tmp_path):
    toolset.discover_pool({"ref_track_ids": ["t000"], "k": 10})
    seen_ids = sorted(toolset.seen)[:2]
    out_xml = tmp_path / "set.xml"
    out = toolset.export_set(
        {"name": "Test Set", "track_ids": seen_ids, "out_path": str(out_xml)}
    )
    assert out.get("exported") is True
    assert out["path"] == str(out_xml)
    assert out_xml.exists()
    assert out["written"] >= 1


def test_export_set_records_exported_on_toolset(toolset, tmp_path):
    """BL-02: a successful export_set records the ExportResult on the toolset
    (mirrors ``created``) so the agent loop can break on it."""
    from vibemix.library.export_rekordbox import ExportResult

    assert toolset.exported is None
    toolset.discover_pool({"ref_track_ids": ["t000"], "k": 10})
    seen_ids = sorted(toolset.seen)[:2]
    out_xml = tmp_path / "recorded.xml"
    out = toolset.export_set(
        {"name": "Recorded", "track_ids": seen_ids, "out_path": str(out_xml)}
    )
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
    assert "error" in toolset.dispatch("discover_pool", {})
    assert "error" in toolset.dispatch("sequence_set", {"track_ids": [], "curve": "x"})
    assert "error" in toolset.dispatch("export_set", {"name": "", "track_ids": []})
