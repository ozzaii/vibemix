"""Retrospective session tools — Viber's eyes over vibemix's own tape.

``list_past_sessions`` / ``analyze_past_set`` read the user's recorded
sessions through ``RecordingsIndex`` (path-safe reader) and resolve tape
titles against the live library, honest-null on miss. ``similar_tracks``
exposes the existing ``similar_to`` engine to the agent for any grounded id.
All resolved/returned ids enter the grounding spine via ``seed_working_set``
(re-validated, never on faith). Key/BPM facts are LIBRARY joins — the tape
carries no key field and ~0.4-0.7-confidence nowplaying titles.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from vibemix.library import toolset as tool_mod
from vibemix.library.rekordbox import RekordboxLibrary, TrackEntry
from vibemix.library.toolset import LibraryToolset


def _make_track(track_id: str, title: str, bpm: float = 124.0, key: str = "8A") -> TrackEntry:
    return TrackEntry(
        track_id=track_id,
        title=title,
        artist="A",
        album="",
        bpm=bpm,
        key=key,
        duration_s=300.0,
        cues=(),
        filepath=f"/tmp/{track_id}.mp3",
        # Set at parse time in production (to_camelot(key)); explicit here.
        camelot=key,
    )


def _event(t: float, **kw) -> str:
    return json.dumps({"t": t, "kind": "event", **kw})


@pytest.fixture
def library() -> RekordboxLibrary:
    lib = RekordboxLibrary()
    lib.tracks = {
        "t001": _make_track("t001", "Mitro - Atencion"),
        "t002": _make_track("t002", "WILDERICH - WHEN_", bpm=0.0),
    }
    return lib


@pytest.fixture
def recordings(tmp_path):
    root = tmp_path / "recordings"
    # Boot-noise session: short, zero TRACK_CHANGE — must be filtered out.
    boot = root / "20260601-090000"
    boot.mkdir(parents=True)
    (boot / "events.jsonl").write_text(
        _event(1.0, type="HEARTBEAT") + "\n" + _event(30.0, type="HEARTBEAT") + "\n",
        encoding="utf-8",
    )
    # Real session: 10 minutes, track changes + phases + mix moves + gate reasons.
    real = root / "20260601-220000"
    real.mkdir(parents=True)
    lines = [
        _event(10.0, type="TRACK_CHANGE", deck="A", track="Mitro - Atencion", track_conf=0.7),
        _event(60.0, type="PHASE", phase="build"),
        _event(120.0, type="MIX_MOVE", deck="B"),
        _event(
            180.0,
            type="TRACK_CHANGE",
            deck="B",
            track="Totally Unknown Dub",
            track_conf=0.4,
            coach_speak_gate_reason="below_worthiness",
        ),
        _event(600.0, type="HEARTBEAT"),
    ]
    (real / "events.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return root


@pytest.fixture
def toolset(library, recordings) -> LibraryToolset:
    return LibraryToolset(MagicMock(), MagicMock(), library, recordings_root=recordings)


def test_list_past_sessions_filters_boot_noise(toolset) -> None:
    out = toolset.list_past_sessions({})
    ids = [s["session_id"] for s in out["sessions"]]
    assert ids == ["20260601-220000"]
    row = out["sessions"][0]
    assert row["track_changes"] == 2
    assert row["duration_s"] >= 600.0


def test_list_past_sessions_honest_empty_without_root(library, tmp_path) -> None:
    ts = LibraryToolset(MagicMock(), MagicMock(), library, recordings_root=tmp_path / "nope")
    assert ts.list_past_sessions({})["sessions"] == []


def test_analyze_past_set_grounds_resolution_and_labels_sources(toolset) -> None:
    out = toolset.analyze_past_set({"session_id": "20260601-220000"})
    assert "error" not in out
    titles = [row["tape_title"] for row in out["tracks"]]
    assert titles == ["Mitro - Atencion", "Totally Unknown Dub"]
    resolved = {row["tape_title"]: row for row in out["tracks"]}
    hit = resolved["Mitro - Atencion"]
    # Library join, explicitly labeled — never presented as tape facts.
    assert hit["track_id"] == "t001"
    assert hit["library_facts"] == {"source": "library", "bpm": 124.0, "camelot": "8A"}
    # Resolution registers the id into the grounding spine (re-validated).
    assert "t001" in toolset.seen
    miss = resolved["Totally Unknown Dub"]
    assert miss["track_id"] is None
    assert miss["library_facts"] is None
    assert "t999" not in toolset.seen
    assert out["phases"] == [{"t": 60.0, "phase": "build"}]
    assert out["mix_move_count"] == 1
    assert out["gate_reasons"] == {"below_worthiness": 1}
    assert "nowplaying" in out["tape_disclaimer"]


def test_analyze_past_set_rejects_path_traversal(toolset) -> None:
    out = toolset.analyze_past_set({"session_id": "../../etc"})
    assert "error" in out


def test_similar_tracks_requires_grounded_seed(toolset) -> None:
    out = toolset.similar_tracks({"track_id": "t001"})
    assert "error" in out and "t001" in out["error"]


def test_similar_tracks_registers_results_into_seen(toolset, monkeypatch) -> None:
    toolset.seed_working_set(["t001"])

    def fake_similar(emb, st, lib, seed, k=10):
        assert seed == "t001"
        return [
            SimpleNamespace(
                to_dict=lambda: {
                    "track_id": "t002",
                    "similarity": 0.81,
                    "title": "WILDERICH - WHEN_",
                    "artist": "A",
                    "bpm": None,
                    "camelot": "8A",
                    "harmonic_compatible": True,
                    "bpm_delta": None,
                },
                track_id="t002",
            )
        ]

    monkeypatch.setattr(tool_mod, "similar_to", fake_similar)
    out = toolset.similar_tracks({"track_id": "t001", "k": 5})
    assert out["seed_track_id"] == "t001"
    assert out["results"][0]["track_id"] == "t002"
    assert "t002" in toolset.seen


def test_new_tools_ride_dispatch(toolset) -> None:
    # dispatch is the production MCP path — the new tools must be registered.
    for name in ("list_past_sessions", "analyze_past_set", "similar_tracks"):
        assert name in toolset._dispatch_handlers()
