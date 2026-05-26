# SPDX-License-Identifier: Apache-2.0
"""Codex curate wrapper — every guard branch, no Codex installed.

The subprocess runner is injected (``_runner``) so these tests exercise the
spawn → timeout → parse → degrade → grounding-revalidation logic without the
``codex`` binary. ``codex_path`` is pointed at a real existing file so
``find_codex`` resolves; the fake runner stands in for ``codex exec``.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from vibemix.library import codex_curate
from vibemix.library.codex_curate import (
    build_argv,
    build_prompt,
    curate_with_codex,
    find_codex,
)
from vibemix.library.rekordbox import RekordboxLibrary, TrackEntry


def _track(tid: str) -> TrackEntry:
    return TrackEntry(
        track_id=tid, title=f"T{tid}", artist="A", album="X",
        bpm=124.0, key="8A", duration_s=300.0, cues=(), filepath=f"/tmp/{tid}.mp3",
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
    assert '"-m", "vibemix.library.mcp_server"' in joined.replace("'", '"') or \
        any("vibemix.library.mcp_server" in a for a in argv)
    assert "read-only" in argv  # tools write, not the shell


def test_find_codex_override_missing(tmp_path):
    assert find_codex(str(tmp_path / "nope")) is None


# -- guard branches --------------------------------------------------------- #


def test_not_installed(library, tmp_path):
    res = curate_with_codex(
        "theme", library, codex_path=str(tmp_path / "nope-codex")
    )
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
    res = curate_with_codex("theme", library, codex_path=sys.executable, allow_shell=True, _runner=runner)
    assert res.stop_reason == "codex_auth_required"
    assert "codex login" in (res.error or "")


def test_generic_error(library):
    runner = _runner_writing(None, returncode=3, stderr="internal explosion")
    res = curate_with_codex("theme", library, codex_path=sys.executable, allow_shell=True, _runner=runner)
    assert res.stop_reason == "error"
    assert "exit 3" in (res.error or "")


def test_empty_output(library):
    runner = _runner_writing(None, returncode=0, raw="")
    res = curate_with_codex("theme", library, codex_path=sys.executable, allow_shell=True, _runner=runner)
    assert res.stop_reason == "empty_output"


def test_garbage_output(library):
    runner = _runner_writing(None, returncode=0, raw="not json {{{")
    res = curate_with_codex("theme", library, codex_path=sys.executable, allow_shell=True, _runner=runner)
    assert res.stop_reason == "empty_output"


def test_no_track_ids(library):
    runner = _runner_writing({"name": "P", "track_ids": [], "rationale": "meh"})
    res = curate_with_codex("theme", library, codex_path=sys.executable, allow_shell=True, _runner=runner)
    assert res.stop_reason == "no_playlist"
    assert res.rationale == "meh"


def test_created_with_grounding_revalidation(library, monkeypatch, tmp_path):
    # Codex returns one real id + one bogus id → bogus dropped at the boundary,
    # then the WRAPPER persists the survivors (codex SELECTS, wrapper WRITES).
    # Redirect the persist into tmp via PLAYLISTS_DIR (the submodule is shadowed
    # by the same-named function in the package namespace, so reach it through
    # sys.modules).
    import sys as _sys

    cp_mod = _sys.modules["vibemix.library.create_playlist"]
    monkeypatch.setattr(cp_mod, "PLAYLISTS_DIR", tmp_path)
    runner = _runner_writing(
        {"name": "Warm-Up", "track_ids": ["t000", "GHOST-999", "t001"],
         "rationale": "hypnotic build"}
    )
    res = curate_with_codex("theme", library, codex_path=sys.executable, allow_shell=True, _runner=runner)
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
    res = curate_with_codex("theme", library, codex_path=sys.executable, allow_shell=True, _runner=runner)
    assert res.stop_reason == "no_playlist"  # nothing survived grounding


def test_build_set_codex_created_with_export_and_grounding(library, monkeypatch, tmp_path):
    """Set-prep over Codex: discover→sequence→export. The wrapper re-validates the
    sequenced ids (grounding) and surfaces the export_set Rekordbox XML path — but
    ONLY when the path actually exists on disk (honest)."""
    import sys as _sys

    from vibemix.library.codex_curate import build_set_with_codex

    cp_mod = _sys.modules["vibemix.library.create_playlist"]
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
        "dark warehouse", library, curve="peak_time",
        codex_path=sys.executable, allow_shell=True, _runner=runner,
    )
    assert res.stop_reason == "created"
    assert res.track_ids == ["t002", "t003"]  # GHOST dropped (grounding)
    assert res.playlist_name == "Peak Set"
    assert res.export_path == str(export_xml)  # surfaced (file exists)
    assert res.m3u_path is not None and Path(res.m3u_path).exists()


def test_build_set_codex_export_path_nulled_when_missing(library, monkeypatch, tmp_path):
    """A returned export_path that does NOT exist on disk is treated as no export
    (never trust the model's claim of a file that isn't there)."""
    import sys as _sys

    from vibemix.library.codex_curate import build_set_with_codex

    cp_mod = _sys.modules["vibemix.library.create_playlist"]
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
