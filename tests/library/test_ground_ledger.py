# SPDX-License-Identifier: Apache-2.0
"""Ground ledger — Viber's cross-turn grounded working set.

The goldfish-memory fix: each chat turn spawns a fresh ``codex exec`` + a
fresh MCP server, so the per-run seen-set forgot every track the PREVIOUS
turn had already discovered and validated — "drop the second one" forced a
full re-discovery or got gate-rejected as invented. The ledger persists ONLY
track ids + display meta between turns; NOTHING in it is trusted on load.
Every id is re-validated against the live library THIS process before it may
enter any grounding surface (Cardinal Invariant #2 — persistence is a hint,
never an authority).

Fixture pattern mirrors the codex_curate suite: the subprocess runner is
injected so no Codex binary is needed; ``codex_path`` points at a real file
so ``find_codex`` resolves.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from vibemix.library import ground_ledger, mcp_server
from vibemix.library import toolset as tool_mod
from vibemix.library.codex_curate import chat_prompt, chat_with_codex
from vibemix.library.ground_ledger import (
    default_ledger_path,
    load_working_set,
    save_working_set,
    working_set_enabled,
)
from vibemix.library.rekordbox import RekordboxLibrary, TrackEntry
from vibemix.library.toolset import LibraryToolset


def _track(tid: str) -> TrackEntry:
    return TrackEntry(
        track_id=tid,
        title=f"T{tid}",
        artist="A",
        album="X",
        bpm=124.0,
        key="8A",
        duration_s=300.0,
        cues=(),
        filepath=f"/tmp/{tid}.mp3",
    )


@pytest.fixture
def library() -> RekordboxLibrary:
    lib = RekordboxLibrary()
    lib.tracks = {f"t{i:03d}": _track(f"t{i:03d}") for i in range(5)}
    return lib


@pytest.fixture(autouse=True)
def ledger_path(tmp_path, monkeypatch) -> Path:
    """Point every test at an isolated ledger; never touch ~/.cache."""
    path = tmp_path / "viber_working_set.json"
    monkeypatch.setenv(ground_ledger.WORKING_SET_PATH_ENV, str(path))
    monkeypatch.delenv(ground_ledger.WORKING_SET_ENV, raising=False)
    monkeypatch.delenv("VIBEMIX_GROUND_LEDGER_FILE", raising=False)
    return path


# -- ledger primitives ------------------------------------------------------ #


def test_save_then_load_round_trip(ledger_path):
    meta = {"t000": {"title": "Tt000", "artist": "A"}, "t001": {"title": "Tt001", "artist": "A"}}
    assert save_working_set(ledger_path, ["t000", "t001"], meta) is True

    assert load_working_set(ledger_path) == ["t000", "t001"]
    payload = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert payload["version"] == ground_ledger.LEDGER_VERSION
    assert payload["updated_at"] > 0
    assert payload["track_ids"] == ["t000", "t001"]
    assert payload["meta"] == meta


def test_load_missing_file_returns_empty(tmp_path):
    assert load_working_set(tmp_path / "absent.json") == []


@pytest.mark.parametrize(
    "raw",
    [
        "{not json",
        '"a bare string"',
        "[1, 2, 3]",
        '{"track_ids": "not-a-list"}',
        '{"version": 1}',
    ],
)
def test_load_corrupt_or_foreign_file_returns_empty(ledger_path, raw):
    ledger_path.write_text(raw, encoding="utf-8")
    assert load_working_set(ledger_path) == []


def test_load_drops_non_string_ids_and_dedupes(ledger_path):
    ledger_path.write_text(
        json.dumps({"version": 1, "track_ids": ["t000", 7, None, "t000", "", "t001"]}),
        encoding="utf-8",
    )
    assert load_working_set(ledger_path) == ["t000", "t001"]


def test_save_dedupes_ids_and_scopes_meta_to_persisted_ids(ledger_path):
    save_working_set(
        ledger_path,
        ["t001", "t000", "t001"],
        {
            "t000": {"title": "Tt000", "artist": "A"},
            "ghost": {"title": "never persisted", "artist": "X"},
        },
    )
    payload = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert payload["track_ids"] == ["t001", "t000"]
    assert payload["meta"] == {"t000": {"title": "Tt000", "artist": "A"}}


def test_save_never_raises_on_unwritable_path():
    # A directory path can't be written as a file — best-effort means False.
    assert save_working_set(Path("/"), ["t000"], None) is False


def test_kill_switch_env(monkeypatch):
    for off in ("0", "false", "no", "off"):
        monkeypatch.setenv(ground_ledger.WORKING_SET_ENV, off)
        assert working_set_enabled() is False
    monkeypatch.setenv(ground_ledger.WORKING_SET_ENV, "1")
    assert working_set_enabled() is True
    monkeypatch.delenv(ground_ledger.WORKING_SET_ENV)
    assert working_set_enabled() is True  # default ON


def test_default_path_env_override(ledger_path, monkeypatch):
    assert default_ledger_path() == ledger_path
    monkeypatch.delenv(ground_ledger.WORKING_SET_PATH_ENV)
    assert default_ledger_path() == ground_ledger.DEFAULT_WORKING_SET_PATH
    assert default_ledger_path().name == "viber_working_set.json"


# -- toolset seeding (the grounding boundary) -------------------------------- #


def test_seed_working_set_revalidates_and_drops_dead_ids(library):
    ts = LibraryToolset(MagicMock(), MagicMock(), library)

    survivors = ts.seed_working_set(["t000", "ghost", "t001", "", 42])

    assert survivors == ["t000", "t001"]
    assert {"t000", "t001"} <= ts.seen
    assert "ghost" not in ts.seen
    assert ts.seeded_working_set == {
        "t000": {"title": "Tt000", "artist": "A"},
        "t001": {"title": "Tt001", "artist": "A"},
    }


def test_seed_working_set_is_idempotent(library):
    ts = LibraryToolset(MagicMock(), MagicMock(), library)
    assert ts.seed_working_set(["t000"]) == ["t000"]
    assert ts.seed_working_set(["t000", "t000"]) == ["t000"]
    assert ts.seen == {"t000"}


def test_seed_working_set_unblocks_create_playlist_gate(library, monkeypatch):
    ts = LibraryToolset(MagicMock(), MagicMock(), library)
    monkeypatch.setattr(
        tool_mod,
        "create_playlist",
        lambda lib, name, ids: SimpleNamespace(
            name=name,
            track_ids=list(ids),
            m3u_path=Path("/tmp/x.m3u8"),
            json_path=Path("/tmp/x.json"),
            dropped_ids=[],
        ),
    )

    rejected = ts.create_playlist({"name": "before seed", "track_ids": ["t000"]})
    assert "invented" in str(rejected.get("error"))

    ts.seed_working_set(["t000"])
    accepted = ts.create_playlist({"name": "after seed", "track_ids": ["t000"]})
    assert accepted.get("created") is True
    assert accepted["track_ids"] == ["t000"]


# -- MCP server seam --------------------------------------------------------- #


def test_promote_arg_paths_promotes_ground_ledger(monkeypatch):
    monkeypatch.delenv("VIBEMIX_GROUND_LEDGER_FILE", raising=False)
    monkeypatch.delenv("VIBEMIX_TOOL_EVENTS_FILE", raising=False)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "mcp_server",
            "--vibemix-tool-events",
            "/tmp/events.jsonl",
            "--vibemix-ground-ledger",
            "/tmp/ledger.json",
        ],
    )

    mcp_server._promote_arg_paths_to_env()

    import os

    assert os.environ["VIBEMIX_GROUND_LEDGER_FILE"] == "/tmp/ledger.json"
    assert os.environ["VIBEMIX_TOOL_EVENTS_FILE"] == "/tmp/events.jsonl"


def test_mcp_seed_from_env_revalidates_against_live_store(library, ledger_path, monkeypatch):
    save_working_set(ledger_path, ["t000", "ghost", "t002"], None)
    monkeypatch.setenv("VIBEMIX_GROUND_LEDGER_FILE", str(ledger_path))
    ts = LibraryToolset(MagicMock(), MagicMock(), library)

    mcp_server._seed_working_set_from_env(ts)

    assert {"t000", "t002"} <= ts.seen
    assert "ghost" not in ts.seen


def test_mcp_seed_from_env_noop_without_flag(library, monkeypatch):
    monkeypatch.delenv("VIBEMIX_GROUND_LEDGER_FILE", raising=False)
    ts = LibraryToolset(MagicMock(), MagicMock(), library)

    mcp_server._seed_working_set_from_env(ts)

    assert ts.seen == set()


def test_mcp_main_seeds_before_serving(monkeypatch, ledger_path):
    """main() must seed the toolset between build_toolset and server.run."""
    calls: list[str] = []
    fake_toolset = SimpleNamespace(
        seed_working_set=lambda ids: calls.append(f"seed:{','.join(ids)}") or list(ids)
    )
    monkeypatch.setenv("VIBEMIX_GROUND_LEDGER_FILE", str(ledger_path))
    save_working_set(ledger_path, ["t000"], None)
    monkeypatch.setattr(mcp_server, "build_toolset", lambda: fake_toolset)
    monkeypatch.setattr(
        mcp_server,
        "build_server",
        lambda ts: SimpleNamespace(run=lambda: calls.append("run")),
    )
    monkeypatch.setattr(sys, "argv", ["mcp_server"])

    mcp_server.main()

    assert calls == ["seed:t000", "run"]


# -- chat prompt rendering ---------------------------------------------------- #


def test_chat_prompt_renders_working_set_block():
    prompt = chat_prompt(
        "find me more dark techno for the warm-up",
        [{"role": "dj", "text": "warm-up set ideas?"}],
        working_set=[
            {"track_id": "t000", "title": "Tt000", "artist": "A"},
            {"track_id": "t001", "title": "Tt001", "artist": "A"},
        ],
    )
    assert "GROUNDED WORKING SET" in prompt
    assert "previous turns of THIS conversation" in prompt
    assert "re-validated against the library" in prompt
    assert "t000 — Tt000 — A" in prompt
    assert "t001 — Tt001 — A" in prompt
    # The rule text must license the working set as grounded (additively).
    assert "GROUNDED WORKING SET block" in prompt


def test_chat_prompt_without_working_set_has_no_block():
    prompt = chat_prompt("find me more dark techno for the warm-up", [])
    assert "GROUNDED WORKING SET (" not in prompt
    assert "t000 —" not in prompt


# -- chat_with_codex wiring (mock runner) ------------------------------------- #


def _chat_payload(track_ids: list[str]) -> dict:
    return {
        "reply": "Here is what I found.",
        "tools_used": ["search_vibe"],
        "tool_trace": [{"name": "search_vibe", "arg": "dark techno", "ok": True}],
        "track_ids": track_ids,
        "move_grades": [],
        "playlist": None,
        "export_path": None,
    }


def _capture_runner(captured: dict, track_ids: list[str]):
    def runner(argv, **kw):
        captured["argv"] = argv
        captured["prompt"] = argv[-1]
        out_path = argv[argv.index("-o") + 1]
        Path(out_path).write_text(json.dumps(_chat_payload(track_ids)), encoding="utf-8")
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    return runner


def _mcp_args_from_argv(argv: list[str]) -> list[str]:
    prefix = "mcp_servers.vibemix_library.args="
    for item in argv:
        if isinstance(item, str) and item.startswith(prefix):
            return json.loads(item[len(prefix) :])
    raise AssertionError(f"no vibemix_library args override in argv: {argv}")


_HISTORY = [
    {"role": "dj", "text": "warm-up set ideas?"},
    {"role": "viber", "text": "found a couple of grounded options"},
]


def test_chat_continuing_conversation_seeds_flag_and_prompt(library, ledger_path):
    save_working_set(ledger_path, ["t000", "ghost"], None)
    captured: dict = {}

    res = chat_with_codex(
        "find me more dark techno for the warm-up",
        library,
        history=_HISTORY,
        codex_path=sys.executable,
        allow_shell=True,
        _runner=_capture_runner(captured, ["t001"]),
    )

    assert res.stop_reason == "model_done"
    mcp_args = _mcp_args_from_argv(captured["argv"])
    flag_idx = mcp_args.index("--vibemix-ground-ledger")
    assert mcp_args[flag_idx + 1] == str(ledger_path)
    # Prompt shows only the LIVE-validated survivors; the dead id never leaks.
    assert "GROUNDED WORKING SET (cross-turn continuity)" in captured["prompt"]
    assert "t000 — Tt000 — A" in captured["prompt"]
    assert "ghost" not in captured["prompt"]


def test_chat_continuing_conversation_merges_harvest(library, ledger_path):
    save_working_set(ledger_path, ["t000", "ghost"], None)

    chat_with_codex(
        "find me more dark techno for the warm-up",
        library,
        history=_HISTORY,
        codex_path=sys.executable,
        allow_shell=True,
        _runner=_capture_runner({}, ["t001"]),
    )

    # Union of still-live prior ids + this run's validated ids; ghost dies.
    assert load_working_set(ledger_path) == ["t000", "t001"]
    payload = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert payload["meta"]["t001"] == {"title": "Tt001", "artist": "A"}


def test_chat_fresh_conversation_overwrites_ledger_and_skips_seed(library, ledger_path):
    save_working_set(ledger_path, ["t000"], None)
    captured: dict = {}

    chat_with_codex(
        "find me more dark techno for the warm-up",
        library,
        history=None,
        codex_path=sys.executable,
        allow_shell=True,
        _runner=_capture_runner(captured, ["t002"]),
    )

    # Fresh conversation: prior conversation's set never seeds prompt or child…
    # (the rules text always MENTIONS the block, so assert on the block header)
    assert "--vibemix-ground-ledger" not in _mcp_args_from_argv(captured["argv"])
    assert "GROUNDED WORKING SET (cross-turn continuity)" not in captured["prompt"]
    assert "t000 —" not in captured["prompt"]
    # …and the ledger is overwritten with this run's ids only.
    assert load_working_set(ledger_path) == ["t002"]


def test_chat_only_validated_run_ids_are_harvested(library, ledger_path):
    chat_with_codex(
        "find me more dark techno for the warm-up",
        library,
        history=None,
        codex_path=sys.executable,
        allow_shell=True,
        _runner=_capture_runner({}, ["t003", "invented-by-model"]),
    )

    # Invariant #2 at the result boundary carries into persistence: an id the
    # live library rejected this process never enters the ledger.
    assert load_working_set(ledger_path) == ["t003"]


def test_chat_kill_switch_disables_load_and_save(library, ledger_path, monkeypatch):
    monkeypatch.setenv(ground_ledger.WORKING_SET_ENV, "0")
    save_working_set(ledger_path, ["t000"], None)
    before = ledger_path.read_text(encoding="utf-8")
    captured: dict = {}

    chat_with_codex(
        "find me more dark techno for the warm-up",
        library,
        history=_HISTORY,
        codex_path=sys.executable,
        allow_shell=True,
        _runner=_capture_runner(captured, ["t001"]),
    )

    assert "--vibemix-ground-ledger" not in _mcp_args_from_argv(captured["argv"])
    assert "GROUNDED WORKING SET (cross-turn continuity)" not in captured["prompt"]
    assert ledger_path.read_text(encoding="utf-8") == before
