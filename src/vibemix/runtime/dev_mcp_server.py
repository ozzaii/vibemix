# SPDX-License-Identifier: Apache-2.0
"""vibemix-dev MCP server — the agent-facing OBSERVE+DRIVE surface.

This is the in-house developer MCP server: it lets a coding agent perceive and
drive the *running* vibemix app (the perception loop the ``drive-vibemix`` skill
codifies, exposed as MCP tools so an agent can do it inline). It connects to the
live co-host as a WebSocket CLIENT, tails the two on-disk log roots, and resolves
IPC wiring — never launching the app, never opening a second listener.

Why a server next to ``ws_bus`` (not under ``library/``): every surface this
exposes is a *runtime* observe/drive concern (the ws bus, the recordings root,
the ui.log). ``runtime/`` is that home; ``library/`` is the curation/embedding
domain. The shipped FastMCP STDIO pattern is mirrored from
``vibemix.library.mcp_server`` (tools return plain dicts, never raise; errors
come back as ``{"error": ...}`` — the no-hang contract).

CARDINAL Invariant #4 (one socket): the live co-host BINDS ``127.0.0.1:8765`` as
the only listener. Every tool here connects as a CLIENT (``websockets.connect``)
or reads files — none ever calls ``websockets.serve``. The debrief window owns
``8766`` and is out of scope.

Config split-brain (two on-disk roots, both handled):
  * ui.log lives under the BUNDLE-ID root —
    ``<app_local_data_dir>/world.bravoh.vibemix/vibemix/logs/ui.log`` (Tauri
    ``app_local_data_dir`` joins ``vibemix/logs``).
  * events.jsonl / recordings live under the PLAIN root —
    ``<app_support>/vibemix/recordings/<session>/`` (``config_store.app_data_dir``
    / ``__main__._resolve_recordings_root``).

Env does NOT cross to an MCP child process (documented Codex-boundary gotcha), so
both roots arrive as ARGS: ``--repo-root`` and ``--log-root`` / ``--data-root``.
Sensible OS-aware defaults are computed when an arg is absent so a local
``uv run`` invocation works with no flags.

Run standalone (what an MCP host's config points at):

    python -m vibemix.runtime.dev_mcp_server --repo-root /path/to/dj-set-ai

Tools (all fail-soft, actionable on error):
  * ``ws_observe(seconds, type_filter?)`` — client-attach, collect inbound frames.
  * ``ws_trigger(action, payload?)`` — send one inbound control frame.
  * ``tail_ui_log(lines=80)`` — last N lines of the bundle-id ui.log.
  * ``tail_events(lines=40, session?)`` — recent events.jsonl from a session dir.
  * ``which_handler(type_or_control)`` — resolve an ipc type to TS sender + Py handler.
  * ``sidecar_status()`` — ws reachable? dev-source mode? GEMINI_API_KEY present?
"""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Pinned to audio/constants.py (WS_HOST/WS_PORT). Imported lazily-safe: the
# constants module is import-light (no audio backend). If the import ever fails
# in a stripped env, fall back to the documented literals so the server still
# boots and reports an actionable status rather than crashing at import.
try:
    from vibemix.audio.constants import WS_HOST, WS_PORT
except Exception:  # pragma: no cover — defensive, constants is import-light
    WS_HOST, WS_PORT = "127.0.0.1", 8765

# ws:// (not wss://) is correct here and not a security gap: the co-host binds a
# loopback-only socket on 127.0.0.1:8765 (Cardinal Invariant #4) with no TLS
# terminator; wss:// would fail to connect to the running bus. Traffic never
# leaves the host. ws_probe.py / ws_bus.py use the same plaintext loopback uri.
DEFAULT_WS_URI = f"ws://{WS_HOST}:{WS_PORT}"  # nosemgrep: insecure-websocket

# Tauri app_local_data_dir bundle id — where debug_log.rs writes ui.log
# (joins "vibemix/logs/ui.log"). Verified against
# tauri/src-tauri/src/debug_log.rs + tauri.conf identifier.
_BUNDLE_ID = "world.bravoh.vibemix"


# ---------------------------------------------------------------------------
# Path resolution — both on-disk roots (the config split-brain)
# ---------------------------------------------------------------------------


def _os_app_support_root() -> Path:
    """OS-aware base for the PLAIN data root (mirrors config_store._app_data_dir).

    macOS:   ~/Library/Application Support
    Windows: %APPDATA% (or ~/AppData/Roaming)
    Other:   $XDG_CONFIG_HOME or ~/.config
    """
    if sys.platform == "darwin":
        return Path(os.path.expanduser("~")) / "Library" / "Application Support"
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata)
        return Path(os.path.expanduser("~")) / "AppData" / "Roaming"
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg)
    return Path(os.path.expanduser("~")) / ".config"


def default_data_root() -> Path:
    """Plain root that holds ``recordings/<session>/events.jsonl``.

    = ``config_store.app_data_dir()`` (``<app_support>/vibemix``). Recordings
    live under ``recordings/`` of this; events.jsonl per session dir.
    """
    return _os_app_support_root() / "vibemix"


def default_log_root() -> Path:
    """Bundle-id root that holds ``vibemix/logs/ui.log``.

    On macOS Tauri's ``app_local_data_dir`` returns the bundle-id dir under
    Application Support, then ``debug_log.rs`` joins ``vibemix/logs``. On other
    OSes the local-data dir differs but the bundle-id segment is the stable
    anchor we can compute; callers can override with ``--log-root`` when their
    layout differs.
    """
    return _os_app_support_root() / _BUNDLE_ID


def default_repo_root() -> Path:
    """Infer the repo root from this module's install location.

    ``src/vibemix/runtime/dev_mcp_server.py`` -> runtime -> vibemix -> src ->
    repo root. When installed (not editable) this points into site-packages and
    the which_handler scan finds nothing — callers MUST pass ``--repo-root`` in
    that case (the tool says so in its error).
    """
    return Path(__file__).resolve().parents[3]


# ---------------------------------------------------------------------------
# which_handler — reuse the proven check_ipc_wiring scanner (no duplicate-drift)
# ---------------------------------------------------------------------------


def _load_ipc_checker(repo_root: Path) -> Any | None:
    """Import the skill's ``check_ipc_wiring`` module by file path.

    It lives under ``.claude/skills/`` (not on the package path), so load it via
    its file. Returns the module, or ``None`` when the skill is absent (a
    stripped checkout) — the caller then degrades to an actionable error rather
    than crashing.
    """
    script = (
        repo_root
        / ".claude"
        / "skills"
        / "ipc-wiring-checker"
        / "scripts"
        / "check_ipc_wiring.py"
    )
    if not script.exists():
        return None
    try:
        spec = importlib.util.spec_from_file_location("_vibemix_ipc_checker", script)
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Read-only file tail (shared by tail_ui_log / tail_events)
# ---------------------------------------------------------------------------


def _tail_lines(path: Path, n: int) -> list[str]:
    """Return the last ``n`` lines of ``path`` (stripped of trailing newline).

    Reads the whole file then slices — ui.log can be large (MBs), so we read in
    a bounded way: pull only the tail bytes. Best-effort decode (errors ignored)
    so a partially-written UTF-8 line never raises.
    """
    n = max(1, int(n))
    # Read a bounded tail rather than the whole multi-MB file. 1KB/line is a
    # generous upper bound for these log lines; clamp so a huge N still bounds.
    approx = min(max(n, 1) * 1024, 8_000_000)
    size = path.stat().st_size
    start = max(0, size - approx)
    with path.open("rb") as fh:
        fh.seek(start)
        chunk = fh.read()
    text = chunk.decode("utf-8", errors="ignore")
    lines = text.splitlines()
    # If we started mid-file the first line is likely partial — drop it unless
    # we read from the very start.
    if start > 0 and len(lines) > 1:
        lines = lines[1:]
    return lines[-n:]


def _latest_session_dir(data_root: Path) -> Path | None:
    """Newest ``recordings/<session>/`` dir under the plain data root, by mtime.

    Returns ``None`` when no recordings exist (a fresh install) — the caller
    reports that honestly instead of erroring.
    """
    rec = data_root / "recordings"
    if not rec.is_dir():
        return None
    sessions = [p for p in rec.iterdir() if p.is_dir()]
    if not sessions:
        return None
    return max(sessions, key=lambda p: p.stat().st_mtime)


# ---------------------------------------------------------------------------
# ws client (observe + trigger). CLIENT ONLY — Invariant #4.
# ---------------------------------------------------------------------------


async def _ws_collect(uri: str, seconds: float, type_filter: str | None) -> dict[str, Any]:
    """Attach as a client, collect inbound frames for ``seconds``, return them.

    ``type_filter`` semantics mirror ws_probe ``--watch``: ``None``/``"all"`` =
    every frame; ``"mascot"`` = only the flat type-less mascot frame; otherwise
    a substring matched against the frame's ``type``. Fail-soft: a refused
    connection returns ``{"error": ...}`` with the launch hint.
    """
    try:
        import websockets
        from websockets.exceptions import WebSocketException
    except ImportError:
        return {
            "error": "websockets not importable in the MCP child — install the "
            "project deps (it is a pyproject dependency: websockets>=13).",
            "frames": [],
            "count": 0,
        }

    seconds = max(0.1, float(seconds))
    frames: list[dict[str, Any]] = []
    try:
        async with websockets.connect(uri) as ws:
            deadline = time.monotonic() + seconds
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
                except TimeoutError:
                    break
                if not isinstance(raw, str):
                    continue
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if not isinstance(data, dict):
                    continue
                if not _frame_matches(data, type_filter):
                    continue
                frames.append(data)
    # OSError = refused/unreachable socket; WebSocketException = bad uri
    # (InvalidURI) or a botched handshake — neither is an OSError subclass, so
    # both must be caught explicitly or a malformed --ws-uri would escape this
    # tool as a raw traceback instead of an actionable error (fail-soft).
    except (ConnectionRefusedError, OSError, WebSocketException) as e:
        return {
            "error": f"cannot reach {uri} ({e}). Is the co-host running? "
            "Launch dev-source (VIBEMIX_DEV_SIDECAR=1 cargo tauri dev) or the "
            "engine alone (uv run python -m vibemix). Connecting attaches as a "
            "CLIENT — it never opens a second listener (Invariant #4).",
            "frames": [],
            "count": 0,
        }
    return {"uri": uri, "seconds": seconds, "count": len(frames), "frames": frames}


def _frame_matches(data: dict[str, Any], type_filter: str | None) -> bool:
    if type_filter in (None, "", "all"):
        return True
    if type_filter == "mascot":
        # The mascot frame is the only one with no ``type`` but WITH meters.
        return "type" not in data and all(k in data for k in ("music", "voice", "mic"))
    return type_filter in str(data.get("type", ""))


async def _ws_send_one(uri: str, frame: dict[str, Any]) -> dict[str, Any]:
    """Send exactly one inbound frame and return a send confirmation.

    The live ``ws_broadcast`` handler does NOT schema-validate inbound frames —
    it acts on ``action`` (trigger / next_suggestion.*) or routes ``type``
    (ipc.*) via ``IpcRouterBus.dispatch``. We briefly wait for the first immediate
    reply because many typed IPC handlers answer on the same socket; broader
    broadcast effects still belong to ws_observe.
    """
    reply: Any | None = None
    reply_raw: str | None = None
    try:
        import websockets
        from websockets.exceptions import WebSocketException
    except ImportError:
        return {"error": "websockets not importable in the MCP child."}
    try:
        async with websockets.connect(uri) as ws:
            await ws.send(json.dumps(frame))
            # Brief drain so the server has accepted the frame before we close;
            # capture an immediate typed-IPC reply when one exists. Swallow ANY
            # recv error here (timeout, closed, protocol) — the send already landed.
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=0.5)
                reply_raw = raw if isinstance(raw, str) else raw.decode("utf-8", errors="replace")
                try:
                    reply = json.loads(reply_raw)
                except json.JSONDecodeError:
                    pass
            except Exception:
                pass
    # OSError = refused/unreachable; WebSocketException = bad uri / handshake —
    # not an OSError subclass, so caught explicitly to keep the tool fail-soft.
    except (ConnectionRefusedError, OSError, WebSocketException) as e:
        return {
            "error": f"cannot reach {uri} ({e}). Is the co-host running? "
            "(client-only send; never opens a second listener — Invariant #4)."
        }
    out: dict[str, Any] = {
        "sent": frame,
        "uri": uri,
        "note": "immediate reply included when available; use ws_observe for broadcasts",
    }
    if reply is not None:
        out["reply"] = reply
    elif reply_raw is not None:
        out["reply_raw"] = reply_raw
    return out


# ---------------------------------------------------------------------------
# Server config (DI — paths arrive as ARGS, env does not cross to MCP children)
# ---------------------------------------------------------------------------


@dataclass
class DevServerConfig:
    """Resolved paths + ws uri for the dev MCP server.

    All three roots are explicit (DI over globals). Defaults are OS-aware so a
    bare local ``uv run`` works; an MCP host passes them as args because env
    does not cross to the child process.
    """

    repo_root: Path = field(default_factory=default_repo_root)
    log_root: Path = field(default_factory=default_log_root)
    data_root: Path = field(default_factory=default_data_root)
    ws_uri: str = DEFAULT_WS_URI

    def ui_log_path(self) -> Path:
        """``<log_root>/vibemix/logs/ui.log`` — the bundle-id ui.log."""
        return self.log_root / "vibemix" / "logs" / "ui.log"


# ---------------------------------------------------------------------------
# Tool implementations (pure-ish, server-agnostic — exercised directly in tests)
# ---------------------------------------------------------------------------


def tool_tail_ui_log(cfg: DevServerConfig, lines: int = 80) -> dict[str, Any]:
    """Return the last ``lines`` of the bundle-id ui.log (fail-soft if absent)."""
    path = cfg.ui_log_path()
    if not path.exists():
        return {
            "error": f"ui.log not found at {path}. The Tauri shell writes it only "
            "once the GUI has run at least once; the engine-only path does not. "
            "Pass --log-root if your bundle-id dir differs.",
            "path": str(path),
            "lines": [],
        }
    try:
        out = _tail_lines(path, lines)
    except OSError as e:
        return {"error": f"could not read {path}: {e}", "path": str(path), "lines": []}
    return {"path": str(path), "count": len(out), "lines": out}


def tool_tail_events(
    cfg: DevServerConfig, lines: int = 40, session: str | None = None
) -> dict[str, Any]:
    """Return recent ``events.jsonl`` lines from the latest (or named) session.

    ``session`` may be a bare session-dir name (``20260530-...``) or an absolute
    path to a session dir; absent = newest session by mtime.
    """
    if session:
        cand = Path(session)
        sess_dir = cand if cand.is_absolute() else (cfg.data_root / "recordings" / session)
    else:
        sess_dir = _latest_session_dir(cfg.data_root)
        if sess_dir is None:
            return {
                "error": f"no recordings under {cfg.data_root / 'recordings'} — the "
                "co-host has not run a session yet (or pass --data-root). "
                "events.jsonl is written per session under the PLAIN data root.",
                "lines": [],
            }
    events = sess_dir / "events.jsonl"
    if not events.exists():
        return {
            "error": f"events.jsonl not found at {events}.",
            "session_dir": str(sess_dir),
            "lines": [],
        }
    try:
        raw = _tail_lines(events, lines)
    except OSError as e:
        return {"error": f"could not read {events}: {e}", "lines": []}
    # Parse each line to JSON when possible so an agent sees structured events;
    # keep the raw string when a line is partial (best-effort, never raise).
    parsed: list[Any] = []
    for ln in raw:
        try:
            parsed.append(json.loads(ln))
        except json.JSONDecodeError:
            parsed.append(ln)
    return {"session_dir": str(sess_dir), "count": len(parsed), "events": parsed}


def tool_which_handler(cfg: DevServerConfig, type_or_control: str) -> dict[str, Any]:
    """Resolve an ipc message type (or control id) to its TS sender + Py handler.

    Reuses the skill's ``check_ipc_wiring`` scanner (no duplicate-and-drift). A
    control id (e.g. ``mood-rocker``) is mapped by substring against the known
    ipc types when no exact type matches, so an agent can pass either form.
    """
    mod = _load_ipc_checker(cfg.repo_root)
    if mod is None:
        return {
            "error": "check_ipc_wiring scanner not found under "
            f"{cfg.repo_root}/.claude/skills/ipc-wiring-checker/. Pass --repo-root "
            "pointing at the vibemix checkout (env does not cross to the MCP child).",
        }
    schema_path = cfg.repo_root / mod.SCHEMA_REL
    if not schema_path.exists():
        return {
            "error": f"schema not found at {schema_path}. Pass --repo-root at the "
            "vibemix checkout root.",
        }
    try:
        types: list[str] = mod.enumerate_types(schema_path)
        ts_hits = mod.scan_tree(cfg.repo_root / mod.TS_ROOT_REL, ".ts", types, mod.TS_EXCLUDE)
        py_hits = mod.scan_tree(cfg.repo_root / mod.PY_ROOT_REL, ".py", types, mod.PY_EXCLUDE)
        rust_hits = mod.scan_tree(cfg.repo_root / mod.RUST_ROOT_REL, ".rs", types, ())
    except Exception as e:
        return {"error": f"scan failed: {e}"}

    target = type_or_control.strip()
    # Exact type match wins; else substring-resolve (control id -> ipc.* type).
    matched: list[str]
    if target in types:
        matched = [target]
    else:
        matched = sorted(t for t in types if target in t)
    if not matched:
        return {
            "query": type_or_control,
            "matched_types": [],
            "note": "no ipc.* type matched (exact or substring). The control may "
            "be a pure-frontend element with no ipc type, or use {action:...} on "
            "the ws bus (ws_observe to see its effect).",
        }

    def _rel(paths: list[str]) -> list[str]:
        out: list[str] = []
        for p in paths:
            try:
                out.append(str(Path(p).resolve().relative_to(cfg.repo_root)))
            except ValueError:
                out.append(p)
        return sorted(set(out))

    results = []
    for t in matched:
        in_ts = t in ts_hits
        in_py = t in py_hits
        if in_ts and in_py:
            wiring = "WIRED (both ends)"
        elif in_ts:
            wiring = "DEAD — shell sends/subscribes but no sidecar handler/emit"
        elif in_py:
            wiring = "DEAD — sidecar emits/handles but no shell sender/consumer"
        else:
            wiring = "ORPHANED — neither end references it (schema-only)"
        results.append(
            {
                "type": t,
                "wiring": wiring,
                "shell_ts": _rel(ts_hits.get(t, [])),
                "sidecar_py": _rel(py_hits.get(t, [])),
                "rust_passthrough": _rel(rust_hits.get(t, [])),
            }
        )
    return {"query": type_or_control, "matched_types": matched, "results": results}


async def tool_ws_observe_async(
    cfg: DevServerConfig, seconds: float = 5.0, type_filter: str | None = None
) -> dict[str, Any]:
    """Async core of ws_observe — attach as client, collect frames for N s."""
    return await _ws_collect(cfg.ws_uri, seconds, type_filter)


async def tool_ws_trigger_async(
    cfg: DevServerConfig, action: str = "trigger", payload: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Async core of ws_trigger — build + send one inbound frame.

    ``action`` shapes the frame: a bare control (``"trigger"``) goes as
    ``{"action": action, **payload}``; an ``ipc.*`` action is sent as a typed
    envelope ``{"type": action, "ts": <ISO date-time>, "payload": payload}``
    (the form the IpcRouterBus dispatch path expects). next_suggestion.* go as
    ``action``.
    """
    payload = payload or {}
    if action.startswith("ipc."):
        frame: dict[str, Any] = {
            "type": action,
            "ts": datetime.now(UTC).isoformat(),
            "payload": payload,
        }
    else:
        frame = {"action": action, **payload}
    return await _ws_send_one(cfg.ws_uri, frame)


async def tool_sidecar_status_async(cfg: DevServerConfig) -> dict[str, Any]:
    """Report the live brain-mute diagnostic surface.

    * ``ws_reachable`` — is something listening on :8765 (the co-host)?
    * ``dev_sidecar`` — is VIBEMIX_DEV_SIDECAR=1 set in THIS process (the dev
      source path)? Note: env does not cross to the MCP child, so this reflects
      the MCP server's own env, reported honestly as such.
    * ``gemini_key_present`` — is GEMINI_API_KEY set (the #1 brain-mute cause:
      no key -> co-host never speaks)? Checks env and the repo-root .env.
    """
    # ws reachability — a 0.5s client connect probe (client-only; Invariant #4).
    ws_reachable = False
    ws_err: str | None = None
    try:
        import websockets
        from websockets.exceptions import WebSocketException

        try:
            async with await asyncio.wait_for(
                websockets.connect(cfg.ws_uri), timeout=1.0
            ) as _ws:
                ws_reachable = True
        # WebSocketException (bad uri / handshake) is not an OSError subclass;
        # catch it too so a malformed --ws-uri reports cleanly instead of
        # crashing the status tool.
        except (ConnectionRefusedError, OSError, TimeoutError, WebSocketException) as e:
            ws_err = str(e)
    except ImportError:
        ws_err = "websockets not importable in the MCP child"

    gemini_present, gemini_src = _gemini_key_present(cfg.repo_root)

    return {
        "ws_uri": cfg.ws_uri,
        "ws_reachable": ws_reachable,
        "ws_error": ws_err,
        "dev_sidecar": os.environ.get("VIBEMIX_DEV_SIDECAR") == "1",
        "dev_sidecar_note": "reflects the MCP child's env; env does not cross from "
        "the launching app, so this is the server's own VIBEMIX_DEV_SIDECAR.",
        "gemini_key_present": gemini_present,
        "gemini_key_source": gemini_src,
        "brain_mute_hint": (
            "co-host will never speak without GEMINI_API_KEY (the #1 mute cause); "
            "with a key, watch events.jsonl citation_count — repeated 0 = un-cited "
            "ack-bank fallback (Invariant #2)."
        ),
    }


def _gemini_key_present(repo_root: Path) -> tuple[bool, str | None]:
    """True if GEMINI_API_KEY is resolvable (env or repo-root .env). No value
    is ever returned — only presence + source, to keep the key out of logs."""
    if os.environ.get("GEMINI_API_KEY"):
        return True, "env"
    env_file = repo_root / ".env"
    if env_file.exists():
        try:
            for ln in env_file.read_text(errors="ignore").splitlines():
                s = ln.strip()
                if s.startswith("GEMINI_API_KEY") and "=" in s:
                    _, _, val = s.partition("=")
                    if val.strip().strip("'\""):
                        return True, str(env_file)
        except OSError:
            pass
    return False, None


# ---------------------------------------------------------------------------
# FastMCP server build (mirrors library/mcp_server.build_server)
# ---------------------------------------------------------------------------


def build_server(cfg: DevServerConfig) -> Any:
    """Wrap ``cfg`` in a FastMCP STDIO server exposing the observe+drive tools.

    Each tool delegates to a module-level implementation (so tests exercise the
    logic without the FastMCP wrapper). Tools return plain dicts; errors come
    back as ``{"error": ...}`` rather than raising — the no-hang contract.
    """
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("vibemix-dev")

    @mcp.tool()
    async def ws_observe(seconds: float = 5.0, type_filter: str | None = None) -> dict[str, Any]:
        """Attach to the live co-host ws bus (ws://127.0.0.1:8765) as a CLIENT and
        collect every inbound frame for ``seconds``. READ-ONLY — never opens a
        second listener (Invariant #4). ``type_filter``: omit/``all`` for every
        frame, ``mascot`` for the flat 30Hz meter frame, or a substring of the
        frame ``type`` (e.g. ``ipc.session.snapshot`` to SEE transcript_delta /
        cohost_status / grounded, ``ipc.status.tick`` for badges)."""
        return await tool_ws_observe_async(cfg, seconds=seconds, type_filter=type_filter)

    @mcp.tool()
    async def ws_trigger(action: str = "trigger", payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Send ONE inbound control frame to the live ws bus to drive a control.
        CLIENT-only (Invariant #4). ``action='trigger'`` (the always-safe one)
        sets manual_trigger so the co-host speaks next tick. ``action`` starting
        with ``ipc.`` is wrapped as a typed envelope {type, ISO ts, payload} routed
        via IpcRouterBus.dispatch; ``next_suggestion.choose`` / ``.feedback`` and
        other bare actions go as {action, **payload}. Returns a send
        confirmation plus an immediate reply when available; use ws_observe for
        broader broadcasts."""
        return await tool_ws_trigger_async(cfg, action=action, payload=payload)

    @mcp.tool()
    def tail_ui_log(lines: int = 80) -> dict[str, Any]:
        """Return the last ``lines`` of the frontend ui.log (bundle-id root:
        <log_root>/vibemix/logs/ui.log). Tags: [vmx:click] [vmx:ipc>] [vmx:ipc<]
        [vmx:ws] [vmx:state] [vmx:error]. A dead button = [vmx:click] with no
        matching [vmx:ipc<] reply. Fail-soft when the file is absent (engine-only
        runs never write it)."""
        return tool_tail_ui_log(cfg, lines=lines)

    @mcp.tool()
    def tail_events(lines: int = 40, session: str | None = None) -> dict[str, Any]:
        """Return recent events.jsonl entries (parsed JSON) from the latest — or
        named — session dir under the PLAIN data root
        (<data_root>/recordings/<session>/events.jsonl). Line kinds: ``event``
        (TRACK_CHANGE/PHASE/HEARTBEAT…), ``llm_invoke``, and ``citation_count``
        (count:0 repeatedly = slop / ack-bank fallback, Invariant #2). ``session``
        = a bare dir name or absolute path; omit for newest by mtime."""
        return tool_tail_events(cfg, lines=lines, session=session)

    @mcp.tool()
    def which_handler(type_or_control: str) -> dict[str, Any]:
        """Resolve an ipc message ``type`` (or a control id) to its TypeScript
        sender(s) + Python handler(s), reusing the both-ends ipc-wiring scanner.
        Reports WIRED / DEAD / ORPHANED per matched type so an agent can tell a
        live control from a dead one without launching the app. Needs the repo
        checkout — pass --repo-root (env does not cross to the MCP child)."""
        return tool_which_handler(cfg, type_or_control)

    @mcp.tool()
    async def sidecar_status() -> dict[str, Any]:
        """Report the brain-mute diagnostic at a glance: is the ws bus on :8765
        reachable (co-host running)? is this MCP child in dev-source mode
        (VIBEMIX_DEV_SIDECAR=1)? is GEMINI_API_KEY present (no key => the co-host
        never speaks — the #1 mute cause)? Presence-only, never the key value."""
        return await tool_sidecar_status_async(cfg)

    return mcp


# ---------------------------------------------------------------------------
# CLI / entrypoint
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> DevServerConfig:
    """Parse ARGS into a DevServerConfig.

    Env does NOT cross to an MCP child process (documented Codex boundary), so
    the repo root + both on-disk roots arrive as args. OS-aware defaults make a
    bare local ``uv run`` work with no flags.
    """
    ap = argparse.ArgumentParser(
        prog="python -m vibemix.runtime.dev_mcp_server",
        description="vibemix-dev MCP server — observe + drive the running app (client-only).",
    )
    ap.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="vibemix checkout root (for which_handler). Default: inferred from "
        "the install location (pass this when installed non-editably).",
    )
    ap.add_argument(
        "--log-root",
        type=Path,
        default=None,
        help="bundle-id root holding vibemix/logs/ui.log. Default: OS-aware "
        f"<app_support>/{_BUNDLE_ID}.",
    )
    ap.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help="plain root holding recordings/<session>/events.jsonl. Default: "
        "OS-aware <app_support>/vibemix.",
    )
    ap.add_argument(
        "--ws-uri",
        default=DEFAULT_WS_URI,
        help=f"ws bus uri (default {DEFAULT_WS_URI}).",
    )
    args = ap.parse_args(argv)
    cfg = DevServerConfig(ws_uri=args.ws_uri)
    if args.repo_root is not None:
        cfg.repo_root = args.repo_root.resolve()
    if args.log_root is not None:
        cfg.log_root = args.log_root.resolve()
    if args.data_root is not None:
        cfg.data_root = args.data_root.resolve()
    return cfg


def main(argv: list[str] | None = None) -> None:
    cfg = parse_args(argv)
    print(
        f"[vibemix-dev] repo_root={cfg.repo_root} log_root={cfg.log_root} "
        f"data_root={cfg.data_root} ws={cfg.ws_uri}",
        file=sys.stderr,
        flush=True,
    )
    server = build_server(cfg)
    server.run()  # STDIO transport


if __name__ == "__main__":
    main()
