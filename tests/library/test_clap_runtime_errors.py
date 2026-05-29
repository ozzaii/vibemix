# SPDX-License-Identifier: Apache-2.0
"""When the CLAP runtime (onnxruntime/tokenizers) is absent, the failure must be
LEGIBLE and ACTIONABLE — not a bare ``ModuleNotFoundError`` whose module name is
swallowed before it reaches Set Notes.

This regressed in the field: the dev/sidecar env shipped without the
``[ai-local]`` extra, so every embedding-dependent tool (search_vibe, similar,
curate, build) died at query-embed time. The user saw only
``search_vibe failed: ModuleNotFoundError`` — with no hint that onnxruntime was
the missing piece. Two guards keep that visible:

1. ``ClapEngine`` raises a RuntimeError naming the missing package + the fix.
2. ``LibraryToolset`` tool errors carry the exception MESSAGE, not just its type.
"""

from __future__ import annotations

import builtins

import pytest

from vibemix.library.clap_engine import ClapEngine
from vibemix.library.toolset import LibraryToolset


def test_clap_engine_missing_runtime_is_actionable(monkeypatch):
    """onnxruntime absent → RuntimeError naming the package and the install fix,
    not a bare ModuleNotFoundError the user can't act on."""
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "onnxruntime" or name.startswith("onnxruntime"):
            raise ModuleNotFoundError("No module named 'onnxruntime'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    eng = ClapEngine(backend="onnx")
    with pytest.raises(RuntimeError) as excinfo:
        eng._ensure_onnx_model()

    msg = str(excinfo.value)
    assert "onnxruntime" in msg, msg
    assert "ai-local" in msg, f"error must name the install fix: {msg}"


def test_search_vibe_surfaces_missing_module_name():
    """A ModuleNotFoundError inside the embedder must reach the tool error dict
    WITH its message ('No module named onnxruntime'), not just the type name."""
    from unittest.mock import MagicMock

    embedder = MagicMock()
    embedder.embed_query.side_effect = ModuleNotFoundError(
        "No module named 'onnxruntime'"
    )
    store = MagicMock()
    store.snapshot_hash.return_value = "snapshot-for-test"
    library = MagicMock()
    library.tracks = {"t001": MagicMock()}  # non-empty → reaches embed_query

    ts = LibraryToolset(embedder, store, library)
    # A unique query string dodges any persisted query-cache hit.
    out = ts.search_vibe({"query": "zzz unique vibe probe 9173 onnx", "k": 3})

    assert "error" in out, out
    assert "onnxruntime" in out["error"], out["error"]


def _broken_search_toolset():
    """A toolset whose search_vibe errors (broken embedder) — used to exercise
    the dispatch tool-event emit without needing the real CLAP runtime."""
    from unittest.mock import MagicMock

    embedder = MagicMock()
    embedder.embed_query.side_effect = ModuleNotFoundError(
        "No module named 'onnxruntime'"
    )
    store = MagicMock()
    store.snapshot_hash.return_value = "snapshot-for-test"
    library = MagicMock()
    library.tracks = {"t001": MagicMock()}
    return LibraryToolset(embedder, store, library)


def test_dispatch_streams_tool_events_when_env_set(tmp_path, monkeypatch):
    """Every tool call appends one JSONL record to VIBEMIX_TOOL_EVENTS_FILE so a
    parent can tail it and show the user what Viber is doing, live."""
    import json

    events = tmp_path / "tool_events.jsonl"
    monkeypatch.setenv("VIBEMIX_TOOL_EVENTS_FILE", str(events))

    ts = _broken_search_toolset()
    ts.dispatch("search_vibe", {"query": "unique zzz dispatch probe 5521", "k": 3})

    lines = events.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1, lines
    rec = json.loads(lines[0])
    assert rec["tool"] == "search_vibe"
    assert rec["ok"] is False  # broken embedder → error result
    assert "unique zzz dispatch probe 5521" in rec["arg"], rec
    assert "k=3" in rec["arg"], rec
    assert "onnxruntime" in rec["summary"], rec["summary"]


def test_dispatch_tool_events_silent_without_env(tmp_path, monkeypatch):
    """No env var → no file, no raise (direct CLI + unit tests unaffected)."""
    monkeypatch.delenv("VIBEMIX_TOOL_EVENTS_FILE", raising=False)
    ts = _broken_search_toolset()
    out = ts.dispatch("search_vibe", {"query": "unique zzz noenv probe 7742", "k": 3})
    assert "error" in out  # dispatch still works
    assert not (tmp_path / "tool_events.jsonl").exists()


def test_mcp_server_promotes_tool_events_arg_to_env(monkeypatch):
    """Codex does NOT forward env to MCP children, so the tape path arrives as
    `--vibemix-tool-events <path>`; the MCP server must promote it to env before
    the toolset is built, or every tool call's tape write silently no-ops."""
    import os
    import sys

    from vibemix.library import mcp_server

    monkeypatch.delenv("VIBEMIX_TOOL_EVENTS_FILE", raising=False)
    monkeypatch.setattr(
        sys, "argv", ["mcp_server", "--vibemix-tool-events", "/tmp/vmx_tapeX.jsonl"]
    )
    try:
        mcp_server._promote_arg_paths_to_env()
        assert os.environ.get("VIBEMIX_TOOL_EVENTS_FILE") == "/tmp/vmx_tapeX.jsonl"
    finally:
        os.environ.pop("VIBEMIX_TOOL_EVENTS_FILE", None)


def test_tool_tap_proxy_emits_on_direct_handler_call(tmp_path, monkeypatch):
    """The MCP server calls handlers DIRECTLY (not via dispatch), so the tape
    emit must ride the build_server proxy. Without it the tape is silent on the
    real Codex path even though the dispatch-level emit is wired."""
    import json

    from vibemix.library.mcp_server import _ToolTapProxy

    events = tmp_path / "tape.jsonl"
    monkeypatch.setenv("VIBEMIX_TOOL_EVENTS_FILE", str(events))

    proxy = _ToolTapProxy(_broken_search_toolset())
    out = proxy.search_vibe({"query": "zzz proxy probe 8842", "k": 3})

    assert "error" in out  # call still returns the handler's result
    lines = events.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1, lines
    rec = json.loads(lines[0])
    assert rec["tool"] == "search_vibe"
    assert rec["ok"] is False
    assert "zzz proxy probe 8842" in rec["arg"], rec


def test_frozen_binary_intercepts_dash_m_mcp_launch(monkeypatch):
    """Packaged-Viber regression guard. Codex spawns the STDIO MCP server as
    ``sys.executable -m vibemix.library.mcp_server <flags>``. In a real
    interpreter ``-m`` is consumed before ``main()`` runs; in a PyInstaller
    binary the bootloader passes it through as ``argv[0]``, so ``cli_entry`` MUST
    intercept the module token and run the server itself — otherwise the bundled
    sidecar falls through to the live session and Codex gets ZERO grounded tools
    (search_vibe et al. unreachable → shipped Viber dead).
    """
    import sys

    from vibemix import __main__ as main_mod

    seen: dict[str, list[str]] = {}

    def fake_mcp_main() -> None:
        seen["argv"] = list(sys.argv)

    monkeypatch.setattr("vibemix.library.mcp_server.main", fake_mcp_main)

    with pytest.raises(SystemExit) as exc:
        main_mod.cli_entry(
            ["-m", "vibemix.library.mcp_server", "--vibemix-tool-events", "/tmp/tape.jsonl"]
        )

    assert exc.value.code == 0
    assert "argv" in seen, "the MCP server's main() never ran"
    # argv rewritten so mcp_server's sys.argv[1:] parser sees only the trailing
    # flags (the module token is stripped) — matches `python -m` semantics.
    assert seen["argv"][1:] == ["--vibemix-tool-events", "/tmp/tape.jsonl"]
