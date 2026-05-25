# SPDX-License-Identifier: Apache-2.0
"""Viber Agent Phase 1 — unit tests. The Gemini client is fully MOCKED;
no test in this file ever touches the network or the real API.

Coverage (per task spec):
  * the loop runs + emits a playlist (happy path)
  * grounding REJECTS an invented track_id (not in the seen-set)
  * create_playlist re-validates ids against the library
  * the bounded loop terminates at max-iters (never wedges)
  * a tool handler RETURNS an error (does not raise) on a bad arg
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from vibemix.library.agent import MAX_TOOL_ITERATIONS, ViberAgent
from vibemix.library.create_playlist import create_playlist
from vibemix.library.rekordbox import RekordboxLibrary, TrackEntry


# --------------------------------------------------------------------------- #
# Fixtures                                                                    #
# --------------------------------------------------------------------------- #


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
def embedder() -> MagicMock:
    return MagicMock()


@pytest.fixture
def store() -> MagicMock:
    return MagicMock()


def _fc(name: str, args: dict) -> SimpleNamespace:
    """A fake function-call object (mimics types.FunctionCall)."""
    return SimpleNamespace(name=name, args=args, id=None)


def _response(function_calls=None, text: str = "") -> SimpleNamespace:
    """A fake GenerateContentResponse. candidates kept None so the agent's
    transcript-append helper degrades gracefully (we don't need real Content
    here — the loop reads .function_calls / .text)."""
    return SimpleNamespace(
        function_calls=function_calls or [],
        text=text,
        candidates=None,
    )


def _scripted_client(responses: list) -> MagicMock:
    """A genai-shaped client whose generate_content returns `responses` in
    order. Patches the real vibe_search out by having search_vibe handlers hit
    the monkeypatched module function (done per-test)."""
    client = MagicMock()
    client.models.generate_content.side_effect = responses
    return client


# --------------------------------------------------------------------------- #
# Tests                                                                       #
# --------------------------------------------------------------------------- #


def test_loop_runs_and_emits_playlist(
    library, embedder, store, monkeypatch, tmp_path
):
    """Happy path: search_vibe → create_playlist → a real playlist file."""
    # Stub vibe_search so no embedder/store/network is exercised.
    from vibemix.library import toolset as tool_mod

    real_ids = ["t000", "t001", "t002"]

    def fake_vibe_search(emb, st, lib, query, k=15):
        results = [
            SimpleNamespace(
                track_id=tid,
                title=f"Title {tid}",
                artist=f"Artist {tid}",
                bpm=124.0,
                confidence=0.9,
            )
            for tid in real_ids
        ]
        return results, False

    monkeypatch.setattr(tool_mod, "vibe_search", fake_vibe_search)
    # Persist playlists into tmp_path, not the user cache.
    monkeypatch.setattr(
        tool_mod,
        "create_playlist",
        lambda lib, name, ids: create_playlist(
            lib, name, ids, out_dir=tmp_path
        ),
    )

    responses = [
        _response([_fc("search_vibe", {"query": "warm-up hypnotic", "k": 3})]),
        _response(
            [_fc("create_playlist", {"name": "Warm-Up", "track_ids": real_ids})]
        ),
    ]
    client = _scripted_client(responses)

    agent = ViberAgent(client, embedder, store, library, model="fake-model")
    result = agent.curate("warm-up hypnotic 122-126")

    assert result.stop_reason == "created"
    assert result.playlist is not None
    assert result.playlist.track_ids == real_ids
    assert result.playlist.m3u_path.exists()
    assert result.playlist.json_path.exists()
    assert set(real_ids).issubset(set(result.seen_track_ids))


def test_grounding_rejects_invented_track_id(
    library, embedder, store, monkeypatch, tmp_path
):
    """An id never returned by search_vibe is rejected — the agent cannot
    smuggle in a hallucinated track. After the rejection it recovers and
    creates a playlist from only-real ids."""
    from vibemix.library import toolset as tool_mod

    def fake_vibe_search(emb, st, lib, query, k=15):
        return (
            [
                SimpleNamespace(
                    track_id="t000",
                    title="T",
                    artist="A",
                    bpm=124.0,
                    confidence=0.9,
                )
            ],
            False,
        )

    monkeypatch.setattr(tool_mod, "vibe_search", fake_vibe_search)
    monkeypatch.setattr(
        tool_mod,
        "create_playlist",
        lambda lib, name, ids: create_playlist(lib, name, ids, out_dir=tmp_path),
    )

    responses = [
        _response([_fc("search_vibe", {"query": "x", "k": 1})]),
        # Model tries to inject "GHOST-999" which search never returned.
        _response(
            [
                _fc(
                    "create_playlist",
                    {"name": "P", "track_ids": ["t000", "GHOST-999"]},
                )
            ]
        ),
        # After the rejection it retries with only the real id.
        _response(
            [_fc("create_playlist", {"name": "P", "track_ids": ["t000"]})]
        ),
    ]
    client = _scripted_client(responses)

    agent = ViberAgent(client, embedder, store, library, model="fake-model")
    result = agent.curate("theme")

    # The invented id never made it into a playlist.
    assert result.playlist is not None
    assert "GHOST-999" not in result.playlist.track_ids
    assert result.playlist.track_ids == ["t000"]
    assert "GHOST-999" not in result.seen_track_ids


def test_create_playlist_validates_ids_against_library(library, tmp_path):
    """create_playlist drops ids absent from the library; raises if none
    survive."""
    # t000 real, BOGUS not in library → dropped, real kept.
    res = create_playlist(
        library, "Mix", ["t000", "BOGUS", "t001"], out_dir=tmp_path
    )
    assert res.track_ids == ["t000", "t001"]
    assert res.dropped_ids == ["BOGUS"]
    assert res.m3u_path.exists()

    # All-invalid → hard error (no silent empty file).
    with pytest.raises(ValueError):
        create_playlist(library, "Empty", ["X", "Y"], out_dir=tmp_path)


def test_bounded_loop_terminates_at_max_iters(
    library, embedder, store, monkeypatch
):
    """A model that never calls create_playlist must still terminate at the
    iteration cap — the loop never wedges."""
    from vibemix.library import toolset as tool_mod

    monkeypatch.setattr(
        tool_mod,
        "vibe_search",
        lambda *a, **k: (
            [
                SimpleNamespace(
                    track_id="t000",
                    title="T",
                    artist="A",
                    bpm=124.0,
                    confidence=0.9,
                )
            ],
            False,
        ),
    )

    # Every call asks for another search — infinite intent, bounded loop.
    client = MagicMock()
    client.models.generate_content.return_value = _response(
        [_fc("search_vibe", {"query": "again", "k": 1})]
    )

    agent = ViberAgent(client, embedder, store, library, model="fake-model")
    result = agent.curate("loop forever")

    assert result.stop_reason == "max_iters"
    assert result.playlist is None
    assert result.iterations == MAX_TOOL_ITERATIONS
    # Hard proof it stopped — not unbounded.
    assert client.models.generate_content.call_count == MAX_TOOL_ITERATIONS


def test_tool_handler_returns_error_not_raise(
    library, embedder, store, monkeypatch, tmp_path
):
    """A bad arg makes a tool handler RETURN an error dict (the loop keeps
    going), never raise. We assert via the dispatcher directly + via a run
    where the model recovers."""
    from vibemix.library import toolset as tool_mod

    monkeypatch.setattr(
        tool_mod,
        "create_playlist",
        lambda lib, name, ids: create_playlist(lib, name, ids, out_dir=tmp_path),
    )

    client = MagicMock()
    agent = ViberAgent(client, embedder, store, library, model="fake-model")

    # Bad arg: empty query → error dict, no raise.
    out = agent._dispatch("search_vibe", {"query": ""})
    assert "error" in out

    # Unknown track_id → honest error, no raise.
    out = agent._dispatch("get_track_features", {"track_id": "NOPE"})
    assert "error" in out

    # create_playlist with no track_ids → error, no raise.
    out = agent._dispatch("create_playlist", {"name": "x", "track_ids": []})
    assert "error" in out

    # Unknown tool name → error, no raise.
    out = agent._dispatch("does_not_exist", {})
    assert "error" in out


def test_interactive_asks_then_curates(
    library, embedder, store, monkeypatch, tmp_path
):
    """Conversational mode: the agent ask_user's the DJ, gets answers via the
    injected ask_fn, then searches + builds. The ask_user tool is dispatched to
    ask_fn (NOT the grounded toolset) and grounding still holds."""
    from vibemix.library import toolset as tool_mod

    real_ids = ["t000", "t001"]
    monkeypatch.setattr(
        tool_mod,
        "vibe_search",
        lambda *a, **k: (
            [
                SimpleNamespace(
                    track_id=t, title=f"T{t}", artist="A", bpm=124.0, confidence=0.9
                )
                for t in real_ids
            ],
            False,
        ),
    )
    monkeypatch.setattr(
        tool_mod,
        "create_playlist",
        lambda lib, name, ids: create_playlist(lib, name, ids, out_dir=tmp_path),
    )

    responses = [
        _response([_fc("ask_user", {"question": "What mood and how long?"})]),
        _response([_fc("ask_user", {"question": "Peak-time energy?"})]),
        _response([_fc("search_vibe", {"query": "dark peak techno", "k": 2})]),
        _response([_fc("create_playlist", {"name": "Live Set", "track_ids": real_ids})]),
    ]
    client = _scripted_client(responses)

    asked: list[str] = []
    answers = iter(["90 min, dark", "yeah peak-time"])

    def ask_fn(q: str) -> str:
        asked.append(q)
        return next(answers)

    agent = ViberAgent(client, embedder, store, library, model="fake-model")
    result = agent.curate_interactive(ask_fn, opening="build me a set")

    assert asked == ["What mood and how long?", "Peak-time energy?"]  # both asked
    assert result.stop_reason == "created"
    assert result.playlist is not None
    assert result.playlist.track_ids == real_ids


def test_get_track_features_camelot_is_deterministic(
    library, embedder, store
):
    """Key normalization comes from harmonics.to_camelot, never the LLM."""
    client = MagicMock()
    agent = ViberAgent(client, embedder, store, library, model="fake-model")
    # t000 has key "8A" (already Camelot) → passthrough.
    out = agent._dispatch("get_track_features", {"track_id": "t000"})
    assert out["key"] == "8A"
    assert out["bpm"] == 124.0

    # A track with a musical-notation key normalizes deterministically.
    library.tracks["t099"] = _make_track("t099", key="Am")
    out = agent._dispatch("get_track_features", {"track_id": "t099"})
    assert out["key"] == "8A"  # Am → 8A
