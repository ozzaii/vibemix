"""The MCP tool path must flow through ``LibraryToolset.dispatch``.

Phase 99 built per-tool hard timeouts, the consecutive-empty starvation
counter, and the terminal stop_reason short-circuit INSIDE ``dispatch()`` —
but the FastMCP wrappers called handlers directly through ``_ToolTapProxy``,
so none of that machinery protected real Codex runs. The proxy now routes
every registered tool through ``dispatch`` (which also owns the tape emit and
the freshness guard); non-tool attributes pass through untouched.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from vibemix.library import toolset as tool_mod
from vibemix.library.mcp_server import _ToolTapProxy
from vibemix.library.rekordbox import RekordboxLibrary, TrackEntry
from vibemix.library.toolset import TOOL_STARVATION_THRESHOLD, LibraryToolset


def _make_track(track_id: str) -> TrackEntry:
    return TrackEntry(
        track_id=track_id,
        title=f"T{track_id}",
        artist="A",
        album="",
        bpm=124.0,
        key="8A",
        duration_s=300.0,
        cues=(),
        filepath=f"/tmp/{track_id}.mp3",
    )


@pytest.fixture
def library() -> RekordboxLibrary:
    lib = RekordboxLibrary()
    lib.tracks = {f"t{i:03d}": _make_track(f"t{i:03d}") for i in range(3)}
    return lib


@pytest.fixture
def toolset(library) -> LibraryToolset:
    return LibraryToolset(MagicMock(), MagicMock(), library)


def _stub_search(monkeypatch, ids: list[str]) -> None:
    def fake(emb, st, lib, query, k=15):
        return (
            [
                SimpleNamespace(track_id=t, title=f"T{t}", artist="A", bpm=124.0, confidence=0.9)
                for t in ids
            ],
            False,
        )

    monkeypatch.setattr(tool_mod, "vibe_search", fake)


def test_proxy_routes_registered_tools_through_dispatch(toolset, monkeypatch) -> None:
    seen_calls: list[tuple[str, dict]] = []
    real_dispatch = toolset.dispatch

    def spying_dispatch(name, args):
        seen_calls.append((name, args))
        return real_dispatch(name, args)

    monkeypatch.setattr(toolset, "dispatch", spying_dispatch)
    _stub_search(monkeypatch, ["t000"])
    proxy = _ToolTapProxy(toolset)
    out = proxy.search_vibe({"query": "hypnotic", "k": 1})
    assert seen_calls == [("search_vibe", {"query": "hypnotic", "k": 1})]
    assert {r["track_id"] for r in out["results"]} == {"t000"}
    assert toolset.seen == {"t000"}


def test_starvation_trips_and_goes_terminal_on_the_mcp_path(toolset, monkeypatch) -> None:
    _stub_search(monkeypatch, [])
    proxy = _ToolTapProxy(toolset)
    for _ in range(TOOL_STARVATION_THRESHOLD):
        out = proxy.search_vibe({"query": "nothing matches", "k": 5})
        assert out["results"] == []
    assert toolset.stop_reason is not None
    # Terminal echo: subsequent calls short-circuit without invoking handlers.
    out = proxy.search_vibe({"query": "still nothing", "k": 5})
    assert out["error"] == "tool_starvation"
    assert out["stop_reason"]["reason"] == "tool_starvation"


def test_exactly_one_tape_row_per_call(toolset, monkeypatch, tmp_path) -> None:
    # dispatch owns the tape emit now — the proxy must NOT add a second row.
    tape = tmp_path / "tool_events.jsonl"
    monkeypatch.setenv("VIBEMIX_TOOL_EVENTS_FILE", str(tape))
    _stub_search(monkeypatch, ["t000"])
    proxy = _ToolTapProxy(toolset)
    proxy.search_vibe({"query": "hypnotic", "k": 1})
    lines = [json.loads(line) for line in tape.read_text(encoding="utf-8").splitlines()]
    assert len(lines) == 1
    # Schema unchanged: codex_curate's receipt recovery + the in-app live tape
    # read these exact keys.
    assert set(lines[0]) >= {"tool", "arg", "ok", "summary", "ts"}
    assert lines[0]["tool"] == "search_vibe"
    assert lines[0]["ok"] is True


def test_non_tool_callables_pass_through_without_dispatch(toolset, monkeypatch, tmp_path) -> None:
    tape = tmp_path / "tool_events.jsonl"
    monkeypatch.setenv("VIBEMIX_TOOL_EVENTS_FILE", str(tape))
    proxy = _ToolTapProxy(toolset)
    # seed_working_set is a public toolset method but NOT a dispatched tool —
    # it must reach the inner object directly (no unknown-tool error, no tape).
    assert proxy.seed_working_set([]) == []
    assert not tape.exists()


def test_dispatch_handlers_registry_matches_dispatch_behavior(toolset) -> None:
    # Single-source pin: every name the registry exposes dispatches to a real
    # handler (no drift between the proxy's routing set and dispatch's dict).
    for name in toolset._dispatch_handlers():
        out = toolset.dispatch(name, {})
        assert "error" not in out or "unknown tool" not in str(out.get("error", ""))
