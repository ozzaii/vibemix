# SPDX-License-Identifier: Apache-2.0
"""LibraryToolset — the shared grounded tool core. These tests pin the
grounding gate (Cardinal Invariant #2) directly on the toolset, independent
of which backend (Gemini agent / Codex MCP server) drives it.

No network: vibe_search is monkeypatched, the library is in-memory.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from vibemix.library import toolset as tool_mod
from vibemix.library.create_playlist import create_playlist
from vibemix.library.rekordbox import RekordboxLibrary, TrackEntry
from vibemix.library.toolset import LibraryToolset


def _make_track(tid: str, bpm: float = 124.0, key: str = "8A") -> TrackEntry:
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


@pytest.fixture
def library() -> RekordboxLibrary:
    lib = RekordboxLibrary()
    lib.tracks = {f"t{i:03d}": _make_track(f"t{i:03d}") for i in range(5)}
    return lib


@pytest.fixture
def toolset(library) -> LibraryToolset:
    return LibraryToolset(MagicMock(), MagicMock(), library)


def _stub_search(monkeypatch, ids):
    def fake(emb, st, lib, query, k=15):
        return (
            [
                SimpleNamespace(
                    track_id=t, title=f"T{t}", artist="A", bpm=124.0, confidence=0.9
                )
                for t in ids
            ],
            False,
        )

    monkeypatch.setattr(tool_mod, "vibe_search", fake)


def test_search_populates_seen_set(toolset, monkeypatch):
    _stub_search(monkeypatch, ["t000", "t001"])
    out = toolset.search_vibe({"query": "hypnotic", "k": 2})
    assert {r["track_id"] for r in out["results"]} == {"t000", "t001"}
    assert toolset.seen == {"t000", "t001"}


def test_create_rejects_invented_id(toolset, monkeypatch, tmp_path):
    _stub_search(monkeypatch, ["t000"])
    monkeypatch.setattr(
        tool_mod,
        "create_playlist",
        lambda lib, name, ids: create_playlist(lib, name, ids, out_dir=tmp_path),
    )
    toolset.search_vibe({"query": "x", "k": 1})
    # GHOST never came from search → whole call rejected, nothing persisted.
    out = toolset.create_playlist({"name": "P", "track_ids": ["t000", "GHOST"]})
    assert "error" in out
    assert "GHOST" in out["error"]
    assert toolset.created is None


def test_create_persists_grounded_playlist(toolset, monkeypatch, tmp_path):
    _stub_search(monkeypatch, ["t000", "t001", "t002"])
    monkeypatch.setattr(
        tool_mod,
        "create_playlist",
        lambda lib, name, ids: create_playlist(lib, name, ids, out_dir=tmp_path),
    )
    toolset.search_vibe({"query": "x", "k": 3})
    out = toolset.create_playlist(
        {"name": "Warm-Up", "track_ids": ["t000", "t001", "t002"]}
    )
    assert out["created"] is True
    assert out["track_count"] == 3
    assert toolset.created is not None


def test_features_camelot_is_deterministic(toolset):
    out = toolset.get_track_features({"track_id": "t000"})
    assert out["key"] == "8A"
    assert out["bpm"] == 124.0
    # Musical-notation key normalizes deterministically (never LLM-computed).
    toolset._library.tracks["t099"] = _make_track("t099", key="Am")
    out = toolset.get_track_features({"track_id": "t099"})
    assert out["key"] == "8A"  # Am → 8A


def test_dispatch_errors_never_raise(toolset):
    assert "error" in toolset.dispatch("search_vibe", {"query": ""})
    assert "error" in toolset.dispatch("get_track_features", {"track_id": "NOPE"})
    assert "error" in toolset.dispatch("create_playlist", {"name": "x", "track_ids": []})
    assert "error" in toolset.dispatch("does_not_exist", {})


# ---------------------------------------------------------------------------
# Phase 82 Wave 0 — CURATE-01 SEAM #1: genre via the ONE perception mechanism
#
# Today `get_track_features` hardcodes `genre: None` (toolset.py:124). Plan 02
# routes it through the SHARED `genre_prototypes` mechanism the co-host already
# reads (state/refresh.py:254 -> GenrePrototypeLookup.classify_playing), so the
# curator and co-host derive genre from ONE source — not two parallel notions.
#
# Plan 02 (this commit) landed the seam: get_track_features now routes genre
# through GenrePrototypeLookup.classify_playing, so these are real-green (the
# xfail scaffolds flipped). Honest-null on the mechanism's abstain.
#
# Honest green: NO genai.Client, NO GEMINI_API_KEY. The in-memory `library`
# fixture sets `lib.tracks` directly and never writes RekordboxLibrary.CACHE_PATH
# (the library.pkl gotcha) — we monkeypatch the prototype mechanism instead.
# Pitfall 2: the assertions pin that the curator routes through `genre_prototypes`
# (classify_playing), NEVER a fresh np.mean/cosine classifier in toolset.py.
# ---------------------------------------------------------------------------

from vibemix.library import genre_prototypes as _proto_mod  # noqa: E402


def test_genre_via_prototypes_when_classified(toolset, monkeypatch):
    """get_track_features routes genre through the shared prototype mechanism.

    Monkeypatch the ONE perception mechanism (GenrePrototypeLookup.classify_playing)
    to return a real label for the known track; assert the seam surfaces that
    library-derived label — NOT the hardcoded `None` of today.
    """

    def fake_classify_playing(self, track_id: str):
        return ("hardtechno", 0.91) if track_id == "t000" else ("unknown", 0.0)

    # Patch the class method — robust to however the seam binds the lookup.
    monkeypatch.setattr(
        _proto_mod.GenrePrototypeLookup,
        "classify_playing",
        fake_classify_playing,
        raising=True,
    )
    out = toolset.get_track_features({"track_id": "t000"})
    assert out["genre"] == "hardtechno", (
        "CURATE-01: genre must be the prototype-resolved label, not None"
    )


def test_genre_honest_none_on_abstain(toolset, monkeypatch):
    """On prototype abstain (("unknown", 0.0)), genre is honest-null, never fabricated.

    This pins TWO things at once: (1) the seam actually CONSULTS the shared
    prototype mechanism (it must be called — proven by the spy), and (2) on its
    abstain the genre is honest-null (None/"unknown"), byte-identical class to
    today's `genre: None` and the Camelot honest-null at toolset.py:116. The
    model NEVER invents a genre (invariant #3, Trust the audio).

    RED today because the seam does not yet call the mechanism (the spy is never
    hit); it flips GREEN only when Plan 02 routes the curator genre through
    `genre_prototypes` — a strict xfail, so the "genre is already None" path can
    never silently satisfy it.
    """
    called: list[str] = []

    def fake_abstain(self, track_id: str):
        called.append(track_id)
        return ("unknown", 0.0)

    monkeypatch.setattr(
        _proto_mod.GenrePrototypeLookup,
        "classify_playing",
        fake_abstain,
        raising=True,
    )
    out = toolset.get_track_features({"track_id": "t000"})
    # The seam MUST route through the shared mechanism (Pitfall 2: no parallel
    # classifier) — proven by the spy firing for this track_id.
    assert called == ["t000"], (
        "CURATE-01: get_track_features must consult genre_prototypes, not a "
        "parallel np.mean/cosine classifier"
    )
    assert out["genre"] in (None, "unknown"), (
        "CURATE-01: prototype abstain must yield honest-null genre, never a fabrication"
    )
