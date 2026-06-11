"""Chat playlist DTO enrichment — grounded display facts at the result boundary.

The shipped chat surface rendered raw hex ids because the playlist payload
carried only ``track_ids``. ``_enrich_playlist_tracks`` resolves
title/artist/bpm/camelot for ALREADY-VALIDATED ids from the live store and
rides the additive top-level ``playlist_tracks`` field (the ``playlist`` dict
shape is exact-pinned by existing tests, so the rich rows live beside it).
Receipts, not model text — every field comes from the store entry,
honest-null when absent.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from vibemix.library.codex_curate import (
    CodexChatResult,
    _enrich_playlist_tracks,
    _normalize_chat_playlist,
)


class _FakeLibrary:
    def __init__(self, entries: dict[str, Any]) -> None:
        self._entries = entries

    def lookup_by_id(self, track_id: str) -> Any | None:
        return self._entries.get(track_id)


def _entry(**kw: Any) -> SimpleNamespace:
    base = {"title": "", "artist": "", "bpm": 0.0, "camelot": None}
    base.update(kw)
    return SimpleNamespace(**base)


def test_enrich_resolves_display_facts_in_order() -> None:
    lib = _FakeLibrary(
        {
            "t1": _entry(title="WHEN_", artist="WILDERICH", bpm=124.0, camelot="8A"),
            "t2": _entry(title="I Got You", artist="Marlon Hoffstadt", bpm=138.5, camelot="11B"),
        }
    )
    rows = _enrich_playlist_tracks(["t1", "t2"], lib)
    assert rows == [
        {"track_id": "t1", "title": "WHEN_", "artist": "WILDERICH", "bpm": 124.0, "camelot": "8A"},
        {
            "track_id": "t2",
            "title": "I Got You",
            "artist": "Marlon Hoffstadt",
            "bpm": 138.5,
            "camelot": "11B",
        },
    ]


def test_enrich_is_honest_null_never_fabricates() -> None:
    # bpm=0.0 is the library's "no tempo" sentinel -> None in the DTO; an empty
    # title falls back to the id (same honesty rule the Rust mapper applies).
    lib = _FakeLibrary({"t1": _entry(title="", artist="", bpm=0.0, camelot=None)})
    (row,) = _enrich_playlist_tracks(["t1"], lib)
    assert row == {"track_id": "t1", "title": "t1", "artist": "", "bpm": None, "camelot": None}


def test_enrich_survives_entry_vanishing_mid_run() -> None:
    # Ids are validated upstream; a store mutation between validation and
    # enrichment must degrade to an id-only row, never raise or drop the row.
    lib = _FakeLibrary({})
    (row,) = _enrich_playlist_tracks(["gone"], lib)
    assert row == {"track_id": "gone", "title": "gone", "artist": "", "bpm": None, "camelot": None}


def test_normalize_chat_playlist_shape_is_unchanged(tmp_path) -> None:
    # The playlist dict is exact-pinned by existing chat tests — enrichment
    # must NOT add keys to it. Rich rows live in the sibling field instead.
    m3u = tmp_path / "set.m3u8"
    js = tmp_path / "set.json"
    m3u.write_text("#EXTM3U\n", encoding="utf-8")
    js.write_text("{}", encoding="utf-8")
    lib = _FakeLibrary({"t1": _entry(title="WHEN_", artist="WILDERICH", bpm=124.0, camelot="8A")})
    out = _normalize_chat_playlist(
        {
            "name": "night-opener",
            "track_ids": ["t1", "invented"],
            "m3u_path": str(m3u),
            "json_path": str(js),
        },
        lib,  # type: ignore[arg-type]
    )
    assert out == {
        "name": "night-opener",
        "track_ids": ["t1"],  # grounding validation still drops invented ids
        "m3u_path": str(m3u),
        "json_path": str(js),
        "dropped_ids": [],
    }


def test_chat_result_emits_playlist_tracks_only_when_present() -> None:
    rows = [
        {"track_id": "t1", "title": "WHEN_", "artist": "WILDERICH", "bpm": 124.0, "camelot": "8A"}
    ]
    rich = CodexChatResult(
        reply="done",
        playlist={"name": "x", "track_ids": ["t1"]},
        playlist_tracks=rows,
    )
    assert rich.to_dict()["playlist_tracks"] == rows
    # No playlist -> the key is ABSENT (payload byte-identical to before the
    # field existed), not null.
    bare = CodexChatResult(reply="done")
    assert "playlist_tracks" not in bare.to_dict()
