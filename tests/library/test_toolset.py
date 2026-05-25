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
