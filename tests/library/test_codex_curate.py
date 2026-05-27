# SPDX-License-Identifier: Apache-2.0
"""Codex curate wrapper — every guard branch, no Codex installed.

The subprocess runner is injected (``_runner``) so these tests exercise the
spawn → timeout → parse → degrade → grounding-revalidation logic without the
``codex`` binary. ``codex_path`` is pointed at a real existing file so
``find_codex`` resolves; the fake runner stands in for ``codex exec``.
"""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from vibemix.library.codex_curate import (
    BUILD_SET_TIMEOUT_S,
    CHAT_TIMEOUT_S,
    CodexChatResult,
    build_argv,
    build_prompt,
    build_set_prompt,
    build_subprocess_env,
    chat_prompt,
    chat_with_codex,
    curate_with_codex,
    find_codex,
)
from vibemix.library.rekordbox import RekordboxLibrary, TrackEntry


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


def _out_path_from_argv(argv: list[str]) -> str:
    return argv[argv.index("-o") + 1]


def _runner_writing(payload, *, returncode=0, stderr="", raw=None):
    """Build a fake subprocess.run that writes ``payload`` to the -o path."""

    def runner(argv, **kw):
        out_path = _out_path_from_argv(argv)
        text = raw if raw is not None else json.dumps(payload)
        Path(out_path).write_text(text, encoding="utf-8")
        return subprocess.CompletedProcess(argv, returncode, stdout="", stderr=stderr)

    return runner


# -- pure helpers ----------------------------------------------------------- #


def test_build_prompt_has_grounding_rules():
    p = build_prompt("hypnotic warm-up")
    assert "hypnotic warm-up" in p
    assert "ONLY put a track" in p  # grounding rule present


def test_build_set_prompt_has_set_prep_workflow():
    p = build_set_prompt(
        "dark warehouse",
        curve="peak_time",
        name="Peak Set",
        n_slots=3,
        export=True,
    )
    assert "dark warehouse" in p
    assert "prefer the 'peak_time' energy curve" in p
    assert "name the set 'Peak Set'" in p
    assert "target exactly 3 slots" in p
    assert "export requested" in p
    assert "discover_pool" in p
    assert "sequence_set" in p
    assert "get_track_sections" in p
    assert "transition_slate" in p
    assert "smart_hot_cues" in p
    assert "export_smart_cues" in p
    assert "export_set" in p


def test_chat_timeout_is_interactive():
    assert CHAT_TIMEOUT_S <= BUILD_SET_TIMEOUT_S


def test_chat_prompt_threads_history_and_rules():
    p = chat_prompt(
        "what bridges from this?",
        history=[
            {"role": "you", "text": "playing 124 bpm"},
            {"role": "viber", "text": "keep it tight"},
        ],
    )

    assert "CHAT" in p
    assert "DJ: playing 124 bpm" in p
    assert "Viber: keep it tight" in p
    assert "DJ: what bridges from this?" in p
    assert "Never invent a track" in p
    assert "transition_slate" in p
    assert "compile_musical_context" in p
    assert "smart_hot_cues" in p
    assert "export_smart_cues" in p
    assert "never raw cue payloads" in p


def test_chat_prompt_does_not_advertise_gemini_youtube_tool():
    p = chat_prompt("any external references?")

    assert "ingest_youtube" not in p
    assert "YouTube claim" not in p


def test_codex_chat_result_to_dict_matches_chat_shape():
    out = CodexChatResult(
        reply="try t000 next",
        tools_used=["search_vibe"],
        track_ids=["t000"],
    ).to_dict()

    assert out == {
        "reply": "try t000 next",
        "tool_trace": [{"name": "search_vibe", "arg": "", "ok": True}],
        "playlist": None,
        "export_path": None,
        "seen_track_ids": ["t000"],
        "iterations": 1,
        "stop_reason": "model_done",
    }


def test_codex_chat_result_to_dict_prefers_rich_tool_trace():
    out = CodexChatResult(
        reply="saved",
        tools_used=["search_vibe", "create_playlist"],
        tool_trace=[
            {"name": "search_vibe", "arg": "dark peak techno", "ok": True},
            {"name": "create_playlist", "arg": "Dark Fuse", "ok": True},
        ],
    ).to_dict()

    assert out["tool_trace"] == [
        {"name": "search_vibe", "arg": "dark peak techno", "ok": True},
        {"name": "create_playlist", "arg": "Dark Fuse", "ok": True},
    ]
    assert out["iterations"] == 2


def test_codex_chat_result_to_dict_surfaces_terminal_artifacts(tmp_path):
    playlist = {
        "name": "Dark Fuse",
        "track_ids": ["t000", "t001"],
        "m3u_path": str(tmp_path / "dark-fuse.m3u8"),
        "json_path": str(tmp_path / "dark-fuse.json"),
        "dropped_ids": [],
    }

    out = CodexChatResult(
        reply="saved it",
        tools_used=["search_vibe", "create_playlist"],
        track_ids=["t000", "t001"],
        playlist=playlist,
        stop_reason="created",
    ).to_dict()

    assert out["playlist"] == playlist
    assert out["iterations"] == 2
    assert out["stop_reason"] == "created"


def test_chat_with_codex_not_installed(library, tmp_path):
    res = chat_with_codex(
        "hello",
        library,
        codex_path=str(tmp_path / "missing-codex"),
    )

    assert res.stop_reason == "codex_not_installed"
    assert "Codex CLI not found" in (res.error or "")


def test_chat_with_codex_surfaces_created_playlist_artifact(library, tmp_path):
    m3u = tmp_path / "dark-fuse.m3u8"
    json_path = tmp_path / "dark-fuse.json"
    m3u.write_text("#EXTM3U\n/tmp/t000.mp3\n", encoding="utf-8")
    json_path.write_text("{}", encoding="utf-8")
    runner = _runner_writing(
        {
            "reply": "Saved Dark Fuse.",
            "tools_used": ["search_vibe", "create_playlist"],
            "tool_trace": [
                {"name": "search_vibe", "arg": "dark peak techno", "ok": True},
                {"name": "create_playlist", "arg": "Dark Fuse", "ok": True},
            ],
            "track_ids": ["t000"],
            "playlist": {
                "name": "Dark Fuse",
                "track_ids": ["t000", "GHOST"],
                "m3u_path": str(m3u),
                "json_path": str(json_path),
                "dropped_ids": ["GHOST"],
            },
            "export_path": None,
        }
    )

    res = chat_with_codex(
        "save this as a playlist",
        library,
        codex_path=sys.executable,
        allow_shell=True,
        _runner=runner,
    )

    assert res.stop_reason == "created"
    assert res.to_dict()["tool_trace"] == [
        {"name": "search_vibe", "arg": "dark peak techno", "ok": True},
        {"name": "create_playlist", "arg": "Dark Fuse", "ok": True},
    ]
    assert res.track_ids == ["t000"]
    assert res.playlist == {
        "name": "Dark Fuse",
        "track_ids": ["t000"],
        "m3u_path": str(m3u),
        "json_path": str(json_path),
        "dropped_ids": ["GHOST"],
    }
    assert res.to_dict()["playlist"]["m3u_path"] == str(m3u)


def test_chat_with_codex_drops_phantom_playlist_artifact(library):
    runner = _runner_writing(
        {
            "reply": "I tried but no saved file came back.",
            "tools_used": ["search_vibe", "create_playlist"],
            "tool_trace": [
                {"name": "search_vibe", "arg": "peak tracks", "ok": True},
                {"name": "create_playlist", "arg": "Phantom", "ok": True},
            ],
            "track_ids": ["t000"],
            "playlist": {
                "name": "Phantom",
                "track_ids": ["t000"],
                "m3u_path": "/nonexistent/phantom.m3u8",
                "json_path": "/nonexistent/phantom.json",
                "dropped_ids": [],
            },
            "export_path": None,
        }
    )

    res = chat_with_codex(
        "save this as a playlist",
        library,
        codex_path=sys.executable,
        allow_shell=True,
        _runner=runner,
    )

    assert res.stop_reason == "model_done"
    assert res.playlist is None
    assert res.track_ids == ["t000"]


def test_chat_with_codex_surfaces_export_path_when_file_exists(library, tmp_path):
    export_xml = tmp_path / "set.xml"
    export_xml.write_text("<DJ_PLAYLISTS/>", encoding="utf-8")
    runner = _runner_writing(
        {
            "reply": "Exported the set.",
            "tools_used": ["discover_pool", "sequence_set", "export_set"],
            "tool_trace": [
                {"name": "discover_pool", "arg": "two track set", "ok": True},
                {"name": "sequence_set", "arg": "peak_time", "ok": True},
                {"name": "export_set", "arg": "set.xml", "ok": True},
            ],
            "track_ids": ["t000", "t001"],
            "playlist": None,
            "export_path": str(export_xml),
        }
    )

    res = chat_with_codex(
        "export a two track set",
        library,
        codex_path=sys.executable,
        allow_shell=True,
        _runner=runner,
    )

    assert res.stop_reason == "exported"
    assert res.export_path == str(export_xml)
    assert res.to_dict()["tool_trace"][2]["arg"] == "set.xml"
    assert res.to_dict()["export_path"] == str(export_xml)


def test_build_argv_injects_mcp_config_and_schema(tmp_path):
    argv = build_argv(
        "/usr/bin/codex",
        mcp_command="python",
        mcp_args=["-m", "vibemix.library.mcp_server"],
        schema_path=str(tmp_path / "s.json"),
        out_path=str(tmp_path / "o.json"),
        prompt="hi",
    )
    assert argv[0] == "/usr/bin/codex" and argv[1] == "exec"
    assert "--output-schema" in argv and "--sandbox" in argv
    joined = " ".join(argv)
    assert "mcp_servers.vibemix_library.command=" in joined
    assert '"-m", "vibemix.library.mcp_server"' in joined.replace("'", '"') or any(
        "vibemix.library.mcp_server" in a for a in argv
    )
    assert "read-only" in argv  # tools write, not the shell


def test_find_codex_override_missing(tmp_path):
    assert find_codex(str(tmp_path / "nope")) is None


def test_find_codex_env_override(monkeypatch, tmp_path):
    codex = tmp_path / "codex"
    codex.write_text("#!/bin/sh\n", encoding="utf-8")
    monkeypatch.setenv("VIBEMIX_CODEX_BIN", str(codex))

    assert find_codex() == str(codex)


def test_build_subprocess_env_adds_codex_and_node_paths(monkeypatch, tmp_path):
    codex = tmp_path / "codex-bin" / "codex"
    node = tmp_path / "node-bin" / "node"
    codex.parent.mkdir()
    node.parent.mkdir()
    codex.write_text("#!/usr/bin/env node\n", encoding="utf-8")
    node.write_text("#!/bin/sh\n", encoding="utf-8")
    monkeypatch.setenv("PATH", "/usr/bin")
    monkeypatch.setenv("VIBEMIX_NODE_BIN", str(node))

    env = build_subprocess_env(str(codex))
    parts = env["PATH"].split(":")

    assert parts[0] == str(codex.parent)
    assert str(node.parent) in parts[:3]
    assert "/usr/bin" in parts


# -- guard branches --------------------------------------------------------- #


def test_not_installed(library, tmp_path):
    res = curate_with_codex("theme", library, codex_path=str(tmp_path / "nope-codex"))
    assert res.stop_reason == "codex_not_installed"
    assert "codex login" in (res.error or "")


def test_timeout(library):
    def runner(argv, **kw):
        raise subprocess.TimeoutExpired(argv, kw.get("timeout", 1))

    res = curate_with_codex(
        "theme", library, codex_path=sys.executable, allow_shell=True, timeout_s=5, _runner=runner
    )
    assert res.stop_reason == "timeout"


def test_auth_required(library):
    runner = _runner_writing(None, returncode=1, stderr="Error: please run codex login first")
    res = curate_with_codex(
        "theme", library, codex_path=sys.executable, allow_shell=True, _runner=runner
    )
    assert res.stop_reason == "codex_auth_required"
    assert "codex login" in (res.error or "")


def test_generic_error(library):
    runner = _runner_writing(None, returncode=3, stderr="internal explosion")
    res = curate_with_codex(
        "theme", library, codex_path=sys.executable, allow_shell=True, _runner=runner
    )
    assert res.stop_reason == "error"
    assert "exit 3" in (res.error or "")


def test_empty_output(library):
    runner = _runner_writing(None, returncode=0, raw="")
    res = curate_with_codex(
        "theme", library, codex_path=sys.executable, allow_shell=True, _runner=runner
    )
    assert res.stop_reason == "empty_output"


def test_garbage_output(library):
    runner = _runner_writing(None, returncode=0, raw="not json {{{")
    res = curate_with_codex(
        "theme", library, codex_path=sys.executable, allow_shell=True, _runner=runner
    )
    assert res.stop_reason == "empty_output"


def test_no_track_ids(library):
    runner = _runner_writing({"name": "P", "track_ids": [], "rationale": "meh"})
    res = curate_with_codex(
        "theme", library, codex_path=sys.executable, allow_shell=True, _runner=runner
    )
    assert res.stop_reason == "no_playlist"
    assert res.rationale == "meh"


def test_created_with_grounding_revalidation(library, monkeypatch, tmp_path):
    # Codex returns one real id + one bogus id → bogus dropped at the boundary,
    # then the WRAPPER persists the survivors (codex SELECTS, wrapper WRITES).
    # Redirect the persist into tmp via PLAYLISTS_DIR.
    cp_mod = importlib.import_module("vibemix.library.create_playlist")
    monkeypatch.setattr(cp_mod, "PLAYLISTS_DIR", tmp_path)
    runner = _runner_writing(
        {
            "name": "Warm-Up",
            "track_ids": ["t000", "GHOST-999", "t001"],
            "rationale": "hypnotic build",
        }
    )
    res = curate_with_codex(
        "theme", library, codex_path=sys.executable, allow_shell=True, _runner=runner
    )
    assert res.stop_reason == "created"
    assert res.track_ids == ["t000", "t001"]  # GHOST dropped
    assert "GHOST-999" not in res.track_ids
    assert res.playlist_name == "Warm-Up"
    assert res.rationale == "hypnotic build"
    # The wrapper persisted a real M3U + JSON (the single validated write).
    assert res.m3u_path is not None and Path(res.m3u_path).exists()
    assert res.json_path is not None and Path(res.json_path).exists()


def test_created_all_bogus_is_no_playlist(library):
    runner = _runner_writing({"name": "P", "track_ids": ["X", "Y"], "rationale": "r"})
    res = curate_with_codex(
        "theme", library, codex_path=sys.executable, allow_shell=True, _runner=runner
    )
    assert res.stop_reason == "no_playlist"  # nothing survived grounding


def test_build_set_codex_exported_with_export_and_grounding(library, monkeypatch, tmp_path):
    """Set-prep over Codex: discover→sequence→export. The wrapper re-validates the
    sequenced ids (grounding) and surfaces the export_set Rekordbox XML path — but
    ONLY when the path actually exists on disk (honest)."""
    from vibemix.library.codex_curate import build_set_with_codex

    cp_mod = importlib.import_module("vibemix.library.create_playlist")
    monkeypatch.setattr(cp_mod, "PLAYLISTS_DIR", tmp_path)
    # The export_set tool would have written this XML during the run.
    export_xml = tmp_path / "set.xml"
    export_xml.write_text("<DJ_PLAYLISTS/>", encoding="utf-8")
    runner = _runner_writing(
        {
            "name": "Peak Set",
            "track_ids": ["t002", "GHOST", "t003"],
            "export_path": str(export_xml),
            "rationale": "controlled tension → plateau",
        }
    )
    res = build_set_with_codex(
        "dark warehouse",
        library,
        curve="peak_time",
        codex_path=sys.executable,
        allow_shell=True,
        _runner=runner,
    )
    assert res.stop_reason == "exported"
    assert res.track_ids == ["t002", "t003"]  # GHOST dropped (grounding)
    assert res.playlist_name == "Peak Set"
    assert res.export_path == str(export_xml)  # surfaced (file exists)
    assert res.m3u_path is not None and Path(res.m3u_path).exists()


def test_build_set_cli_treats_codex_exported_as_success(library, monkeypatch, capsys, tmp_path):
    """Regression: exported is the successful set-prep terminal.

    The Codex wrapper returns ``stop_reason="exported"`` when export_set wrote a
    Rekordbox XML. The CLI bridge must put that JSON on stdout and return zero,
    otherwise Tauri treats a successful exported set as a failed command.
    """
    import argparse

    import vibemix.__main__ as main_mod
    import vibemix.library.codex_curate as codex_mod

    export_xml = tmp_path / "set.xml"
    export_xml.write_text("<DJ_PLAYLISTS/>", encoding="utf-8")

    def fake_build_set_with_codex(*args, **kwargs):
        assert kwargs["n_slots"] == 3
        assert kwargs["export"] is True
        return codex_mod.CodexCurateResult(
            theme="dark warehouse",
            stop_reason="exported",
            playlist_name="Peak Set",
            track_ids=["t002", "t003"],
            rationale="controlled tension",
            export_path=str(export_xml),
        )

    monkeypatch.setattr(codex_mod, "build_set_with_codex", fake_build_set_with_codex)
    rc = main_mod._cmd_library_build_set_codex(
        argparse.Namespace(
            brief="dark warehouse",
            curve="peak_time",
            name=None,
            n_slots=3,
            export="rekordbox",
        ),
        library,
    )

    assert rc == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["stop_reason"] == "exported"
    assert payload["export_path"] == str(export_xml)
    assert "exported" in captured.err


def test_build_set_codex_export_path_nulled_when_missing(library, monkeypatch, tmp_path):
    """A returned export_path that does NOT exist on disk is treated as no export
    (never trust the model's claim of a file that isn't there)."""
    from vibemix.library.codex_curate import build_set_with_codex

    cp_mod = importlib.import_module("vibemix.library.create_playlist")
    monkeypatch.setattr(cp_mod, "PLAYLISTS_DIR", tmp_path)
    runner = _runner_writing(
        {
            "name": "Set",
            "track_ids": ["t000"],
            "export_path": "/nonexistent/phantom.xml",
            "rationale": "r",
        }
    )
    res = build_set_with_codex(
        "brief", library, codex_path=sys.executable, allow_shell=True, _runner=runner
    )
    assert res.stop_reason == "created"
    assert res.export_path is None  # phantom path dropped


def test_blocked_without_opt_in(library):
    """Default (no VIBEMIX_CODEX_ALLOW_SHELL): the upstream MCP-cancel bug means
    we don't even spawn — surface the honest blocked result + the opt-in path.
    The runner is NEVER called."""
    called = {"n": 0}

    def runner(argv, **kw):
        called["n"] += 1
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    res = curate_with_codex(
        "theme", library, codex_path=sys.executable, allow_shell=False, _runner=runner
    )
    assert res.stop_reason == "codex_mcp_blocked"
    assert "VIBEMIX_CODEX_ALLOW_SHELL" in (res.error or "")
    assert "16685" in (res.error or "")  # cites the upstream bug
    assert called["n"] == 0  # never spawned


def test_build_argv_bypass_uses_dangerous_flag(tmp_path):
    argv = build_argv(
        "/usr/bin/codex",
        mcp_command="python",
        mcp_args=["-m", "x"],
        schema_path=str(tmp_path / "s.json"),
        out_path=str(tmp_path / "o.json"),
        prompt="hi",
        bypass_sandbox=True,
    )
    assert "--dangerously-bypass-approvals-and-sandbox" in argv
    assert "--sandbox" not in argv  # bypass replaces the read-only sandbox
