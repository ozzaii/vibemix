# SPDX-License-Identifier: Apache-2.0
"""Codex curate backend — spawn ``codex exec`` against the vibemix MCP server.

The Hermes pattern, native CLI: Codex (``provider: openai-codex``, the owner's
flat-rate ChatGPT subscription) is the bounded reasoning harness; vibemix's
:mod:`vibemix.library.mcp_server` exposes the grounded Viber tool surface over
STDIO. Codex's own harness owns the agentic loop, per-tool timeouts, and
sandboxing. Historical pre-implementation research is archived under
``.planning/archive/2026-05-27-stale-viber-direction-research/``.

This wrapper is deliberately thin — spawn + outer timeout + parse + degrade.
It owns ONLY the guards Codex's harness does not:

1. **codex-not-installed** — no ``codex`` on PATH → actionable message
   (mirrors the P74 api-key-missing UI loop).
2. **codex-not-logged-in / auth** — non-zero exit whose stderr names a login
   problem → "run ``codex login``".
3. **outer wall-clock timeout** — Codex bounds *tool* calls, but a wedged
   process or stuck OAuth refresh needs an outer kill.
4. **empty / garbage output** — degrade to "no playlist", never crash.
5. **grounding re-validation** — the wrapper trusts ONLY track_ids that
   resolve in the live library (Cardinal Invariant #2 at the result boundary);
   the model's free-text list is never taken on faith. The MCP server's
   seen-set gate + ``create_playlist`` library re-validation are the upstream
   lines; this is belt-and-braces on the way out.

Codex is NOT a dependency and may be absent on a given machine — this module
imports cleanly without it and only shells out at call time. The unit tests
inject a fake runner, so they exercise every branch without Codex installed.
"""

from __future__ import annotations

import glob
import json
import logging
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from vibemix.library.rekordbox import RekordboxLibrary
from vibemix.runtime.ai_observability import append_global_ai_message
from vibemix.state.deck_context import (
    DECK_CONTEXT_TRUSTED_SOURCES as _SHARED_DECK_CONTEXT_TRUSTED_SOURCES,
)
from vibemix.state.deck_context import (
    LIVE_CANDIDATE_HELD_REPLY as _SHARED_LIVE_CANDIDATE_HELD_REPLY,
)
from vibemix.state.deck_context import (
    LIVE_TRANSITION_HELD_REPLY as _SHARED_LIVE_TRANSITION_HELD_REPLY,
)
from vibemix.state.deck_context import (
    apply_live_claim_guard as _shared_apply_live_claim_guard,
)
from vibemix.state.deck_context import (
    has_multi_deck_outcome_claim as _shared_has_multi_deck_outcome_claim,
)
from vibemix.state.deck_context import (
    has_multi_deck_outcome_disclaimer as _shared_has_multi_deck_outcome_disclaimer,
)
from vibemix.state.deck_context import (
    has_unsafe_multi_deck_disclaimer_claim as _shared_has_unsafe_multi_deck_disclaimer_claim,
)
from vibemix.state.deck_context import (
    live_claim_policy as _shared_live_claim_policy,
)
from vibemix.state.deck_context import (
    live_evidence_packet as _shared_live_evidence_packet,
)
from vibemix.state.deck_context import (
    normalize_audio_part_context_text as _shared_normalize_audio_part_context_text,
)
from vibemix.state.deck_context import (
    normalize_audio_window_context_text as _shared_normalize_audio_window_context_text,
)
from vibemix.state.deck_context import (
    normalize_deck_audio_context_text as _shared_normalize_deck_audio_context_text,
)
from vibemix.state.deck_context import (
    normalize_deck_audio_delta_context_text as _shared_normalize_deck_audio_delta_context,
)
from vibemix.state.deck_context import (
    normalize_deck_audio_features_context_text as _shared_normalize_deck_audio_features_context,
)
from vibemix.state.deck_context import (
    normalize_deck_audio_separation_context_text as _shared_normalize_deck_audio_separation,
)
from vibemix.state.deck_context import (
    normalize_deck_audio_window_context_text as _shared_normalize_deck_audio_window_context,
)
from vibemix.state.deck_context import (
    normalize_deck_lanes_context_text as _shared_normalize_deck_lanes_context_text,
)
from vibemix.state.deck_context import (
    normalize_deck_reference_context_text as _shared_normalize_deck_reference_context_text,
)
from vibemix.state.deck_context import (
    normalize_deck_source_context_text as _shared_normalize_deck_source_context_text,
)
from vibemix.state.deck_context import (
    render_audio_part_context as _shared_render_audio_part_context,
)
from vibemix.state.deck_context import (
    render_audio_window_context as _shared_render_audio_window_context,
)
from vibemix.state.deck_context import (
    render_context_feed_contract as _shared_render_context_feed_contract,
)
from vibemix.state.deck_context import (
    render_deck_audio_context as _shared_render_deck_audio_context,
)
from vibemix.state.deck_context import (
    render_deck_audio_delta_context as _shared_render_deck_audio_delta_context,
)
from vibemix.state.deck_context import (
    render_deck_audio_features_context as _shared_render_deck_audio_features_context,
)
from vibemix.state.deck_context import (
    render_deck_audio_separation_context as _shared_render_deck_audio_separation,
)
from vibemix.state.deck_context import (
    render_deck_audio_window_context as _shared_render_deck_audio_window_context,
)
from vibemix.state.deck_context import (
    render_deck_change_context as _shared_render_deck_change_context,
)
from vibemix.state.deck_context import (
    render_deck_context as _shared_render_deck_context,
)
from vibemix.state.deck_context import (
    render_deck_lane_context as _shared_render_deck_lane_context,
)
from vibemix.state.deck_context import (
    render_deck_reference_context as _shared_render_deck_reference_context,
)
from vibemix.state.deck_context import (
    render_deck_source_context as _shared_render_deck_source_context,
)
from vibemix.state.deck_context import (
    render_mixer_context as _shared_render_mixer_context,
)
from vibemix.state.deck_context import (
    render_move_context as _shared_render_move_context,
)
from vibemix.state.deck_context import (
    render_move_effect_context as _shared_render_move_effect_context,
)
from vibemix.state.deck_context import (
    sanitize_historical_move_signature_for_prompt as _shared_sanitize_history_signature,
)
from vibemix.state.deck_state import DeckState, DeckTrack

logger = logging.getLogger(__name__)

if TYPE_CHECKING:  # pragma: no cover - typing only
    from vibemix.state import MusicState

# Outer wall-clock guard. Codex bounds tool calls (tool_timeout_sec) and its
# own loop; this is the belt-and-braces kill for a wedged process.
DEFAULT_TIMEOUT_S = 120.0
# Set-prep is multi-step, but it is still an interactive app action. Keep the
# wall-clock short enough that the Library UI can degrade during a demo instead
# of looking wedged for several minutes.
BUILD_SET_TIMEOUT_S = 90.0
# MCP tool/startup timeouts handed to Codex via -c overrides (its harness owns
# enforcement; we only set the values).
_MCP_STARTUP_TIMEOUT_S = 15
_MCP_TOOL_TIMEOUT_S = 30

# Substrings in Codex stderr that mean "not authenticated" rather than a
# genuine runtime error — used to surface the actionable `codex login` hint.
_AUTH_HINTS = ("login", "log in", "auth", "sign in", "not authenticated", "401")

# Finder/Dock-launched macOS apps usually do not inherit the user's shell PATH,
# so Homebrew/npm-installed Codex can be invisible to shutil.which("codex").
# Search the common install locations before declaring the local brain missing.
_CODEX_BIN_ENV_KEYS = ("VIBEMIX_CODEX_BIN", "CODEX_BIN")
_NODE_BIN_ENV_KEYS = ("VIBEMIX_NODE_BIN", "NODE_BIN")
_CODEX_UNIX_CANDIDATES = (
    "/opt/homebrew/bin/codex",
    "/usr/local/bin/codex",
    "/opt/local/bin/codex",
    "~/.local/bin/codex",
    "~/.npm-global/bin/codex",
    "~/.bun/bin/codex",
    "~/.volta/bin/codex",
    "~/Library/pnpm/codex",
)
_NODE_UNIX_CANDIDATES = (
    "/opt/homebrew/bin/node",
    "/usr/local/bin/node",
    "/opt/local/bin/node",
    "~/.volta/bin/node",
    "~/.local/bin/node",
)
_NODE_GLOB_CANDIDATES = (
    "~/.nvm/versions/node/*/bin/node",
    "~/.fnm/node-versions/*/installation/bin/node",
    "/opt/homebrew/Cellar/node/*/bin/node",
    "/opt/homebrew/Cellar/node@*/*/bin/node",
    "/usr/local/Cellar/node/*/bin/node",
    "/usr/local/Cellar/node@*/*/bin/node",
)

# WIRE-04 (Phase 77 Plan 02): persona opener sourced from the shared matrix
# seam (build_curator_instruction) — the same voice family the live co-host uses.
# The "Use ONLY the provided tools" bridge is codex-specific
# (MCP tool surface) and the RULES below — including codex's distinct rule #3
# (return final JSON, no create_playlist) — are PRESERVED VERBATIM.
#
# The seam is imported LAZILY (inside the builder), so importing this module
# does NOT pull ``vibemix.prompts`` into ``sys.modules`` — preserving the memory
# storage spine's no-live-path import boundary (tests/memory/
# test_no_live_path_import.py). ``_SYSTEM_PROMPT`` is exposed via PEP 562
# ``__getattr__`` so attribute access stays a plain string.
_RULES_BLOCK = (
    "Use ONLY the provided tools.\n"
    "RULES (non-negotiable):\n"
    "1. You may ONLY put a track in a playlist if a prior search_vibe call "
    "returned its track_id in THIS run. Never invent a track_id, title, "
    "artist, BPM, or key. Call search_vibe to find candidates.\n"
    "2. Keys/BPM come from get_track_features (deterministic) — never compute "
    "or guess them.\n"
    "3. When you have chosen the tracks, return them as the final JSON object "
    "{name, track_ids, rationale} with track_ids in play order. The app "
    "persists the playlist — you do NOT need to call create_playlist.\n"
    "4. Keep it tight — a focused set beats a padded one."
)

_SYSTEM_PROMPT_CACHE: str | None = None
# Phase 79 LENS-02 — the lens the cache was built under (rebuild on change).
_SYSTEM_PROMPT_LENS: str | None = None
# WR-04: guard the check-then-set so a concurrent lens-change rebuild can't
# interleave the (_CACHE, _LENS) writes and serve the wrong voice. Mirrors the
# legacy agent seam; uncontended on the steady-state cache hit.
_CACHE_LOCK = threading.Lock()


def _shared_lens() -> str:
    """Read the ONE shared lens (LENS-02) — delegates to the shared seam.

    IN-01: the codex backend reads the lens through the SAME
    ``library._curator_seams.shared_lens`` so Viber set-prep/chat and the
    live co-host read the same lens selection. Lazy-imported to keep the
    import-time no-live-path boundary clean.
    """
    from vibemix.library._curator_seams import shared_lens

    return shared_lens()


def _taste_hint() -> str:
    """SEAM #2 (CURATE-02) taste hint — delegates to the shared seam.

    IN-01 + WR-01: the codex backend calls the SAME consent-gated
    ``library._curator_seams.taste_hint`` so the consent contract is
    single-sourced. Returns ``""`` when consent is OFF or the profile is absent
    → byte-identical cold path even with a stale ``profile.json``.
    """
    from vibemix.library._curator_seams import taste_hint

    return taste_hint()


def _system_prompt() -> str:
    """Build (and cache) the codex curator system prompt from the matrix seam."""
    global _SYSTEM_PROMPT_CACHE, _SYSTEM_PROMPT_LENS
    lens = _shared_lens()
    # WR-04: serialize the check-then-set (see _CACHE_LOCK rationale above).
    with _CACHE_LOCK:
        if _SYSTEM_PROMPT_CACHE is None or _SYSTEM_PROMPT_LENS != lens:
            from vibemix.prompts.matrix import build_curator_instruction

            _SYSTEM_PROMPT_CACHE = build_curator_instruction(lens) + " " + _RULES_BLOCK
            _SYSTEM_PROMPT_LENS = lens
        base = _SYSTEM_PROMPT_CACHE
    # SEAM #2: append the taste hint OUTSIDE the lens-keyed cache (recompute per
    # call); "" on the cold path → byte-identical to today.
    return base + _taste_hint()


def __getattr__(name: str) -> Any:
    # PEP 562 — _SYSTEM_PROMPT builds the matrix seam on first access, keeping
    # the import-time no-live-path boundary clean.
    if name == "_SYSTEM_PROMPT":
        return _system_prompt()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# JSON Schema enforced on Codex's final message (--output-schema). OpenAI strict
# structured outputs require `additionalProperties: false` AND every property in
# `required` (no truly-optional fields) — otherwise a 400 invalid_json_schema.
# We keep it to the three fields we actually consume; the M3U/JSON paths come
# from the MCP create_playlist tool's persisted file, not this final message.
_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "track_ids": {"type": "array", "items": {"type": "string"}},
        "rationale": {"type": "string"},
    },
    "required": ["name", "track_ids", "rationale"],
    "additionalProperties": False,
}


@dataclass(slots=True)
class CodexCurateResult:
    """Outcome of one Codex curation run."""

    theme: str
    stop_reason: str  # see _STOP_REASONS below
    playlist_name: str | None = None
    track_ids: list[str] = field(default_factory=list)
    m3u_path: str | None = None
    json_path: str | None = None
    rationale: str = ""
    error: str | None = None
    # Set-prep only: the Rekordbox XML path written by the export_set MCP tool
    # during a `build_set_with_codex` run. None for plain curation.
    export_path: str | None = None
    # Phase 100 HARDEN-CLARIFY-03: populated when the MCP-side toolset's
    # request_clarification handler trips (stop_reason="clarification_needed").
    # Defaults preserve the cold path — every non-clarification result keeps
    # question + choices as None. CLI (Plan 100-04) + Telegram (Plan 100-05)
    # read these fields to render the disambiguation prompt to the user.
    question: str | None = None
    choices: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# created            — a grounded playlist came back
# codex_not_installed — no `codex` binary on PATH
# codex_auth_required — codex ran but is not logged in
# timeout            — outer wall-clock kill
# empty_output       — codex produced nothing parseable
# no_playlist        — output had no track_ids surviving library validation
# tool_starvation    — Plan 99-04 propagation: the MCP-side toolset hit the
#                      TOOL_STARVATION_THRESHOLD (3 consecutive empty/error
#                      tool returns) and wrote stop_reason.json to the env-var
#                      path; the wrapper short-circuits with the hint as error.
# clarification_needed — Plan 100-03 propagation: the MCP-side toolset's
#                        request_clarification handler validated args + wrote
#                        stop_reason.json with reason="clarification_needed"
#                        + question + choices. The wrapper short-circuits
#                        with those fields populated; CLI prints + exits 11,
#                        Telegram renders numbered choices.
# error              — any other non-zero exit / failure


def find_codex(codex_path: str | None = None) -> str | None:
    """Locate the ``codex`` binary, honoring explicit and app-friendly paths.

    ``shutil.which("codex")`` is enough in a terminal, but not in a packaged
    macOS app launched from Finder. The desktop bridge also forwards
    ``VIBEMIX_CODEX_BIN`` so users can pin a binary path without changing shell
    startup files.
    """
    candidates: list[str] = []
    if codex_path:
        candidates.append(codex_path)
    else:
        for key in _CODEX_BIN_ENV_KEYS:
            raw = os.environ.get(key)
            if raw:
                candidates.append(raw)
        found = shutil.which("codex")
        if found:
            candidates.append(found)
        candidates.extend(_CODEX_UNIX_CANDIDATES)
        home = Path.home()
        candidates.extend(str(p) for p in home.glob(".nvm/versions/node/*/bin/codex"))

    for raw in candidates:
        path = Path(raw).expanduser()
        if path.is_file():
            return str(path)
    return None


def build_subprocess_env(codex_path: str) -> dict[str, str]:
    """Build an app-friendly env for ``codex exec``.

    Homebrew/npm Codex is often a ``#!/usr/bin/env node`` script. Finder-launched
    apps can find ``codex`` through ``VIBEMIX_CODEX_BIN`` or the common-path scan
    above while still missing ``node`` from PATH. Prepending discovered Node bin
    dirs keeps the local brain usable without requiring users to hand-edit shell
    startup files that the desktop app will not read anyway.
    """
    env = os.environ.copy()
    path_dirs: list[str] = []

    def add_dir(raw: str | Path | None) -> None:
        if raw is None:
            return
        p = Path(raw).expanduser()
        if p.is_file():
            p = p.parent
        if not p.exists():
            return
        s = str(p)
        if s not in path_dirs:
            path_dirs.append(s)

    add_dir(Path(codex_path).expanduser().parent)
    for key in _NODE_BIN_ENV_KEYS:
        raw = env.get(key)
        if raw:
            add_dir(raw)
    found_node = shutil.which("node")
    if found_node:
        add_dir(found_node)
    for raw in _NODE_UNIX_CANDIDATES:
        add_dir(raw)
    for pattern in _NODE_GLOB_CANDIDATES:
        for p in sorted(glob.glob(str(Path(pattern).expanduser()))):
            add_dir(p)

    old_path = env.get("PATH", "")
    prefix = os.pathsep.join(path_dirs)
    env["PATH"] = prefix + (os.pathsep + old_path if prefix and old_path else old_path)
    return env


def build_prompt(theme: str) -> str:
    return f"{_system_prompt()}\n\nTheme: {theme.strip()}"


def build_argv(
    codex_path: str,
    *,
    mcp_command: str,
    mcp_args: list[str],
    schema_path: str,
    out_path: str,
    prompt: str,
    bypass_sandbox: bool = False,
) -> list[str]:
    """Build the ``codex exec`` argv.

    MCP-server config is injected via ``-c`` overrides (TOML/JSON values) so we
    never touch the user's global ``~/.codex/config.toml``. Auth still comes
    from the default ``~/.codex`` (the user's own ``codex login``); only the
    server wiring is overridden per-invocation.

    **Sandbox / the upstream MCP-approval bug.** Ideally we run
    ``--sandbox read-only`` (tools write, never the shell). But codex has an
    OPEN regression (openai/codex#16685, #24135): in non-interactive
    ``codex exec`` every MCP tool call is auto-cancelled ("user cancelled MCP
    tool call") UNLESS ``--dangerously-bypass-approvals-and-sandbox`` is set —
    ``default_tools_approval_mode="auto"`` does NOT take effect in exec mode.
    So MCP-backed curation is impossible today without the bypass, which also
    drops the shell sandbox. ``bypass_sandbox`` is therefore a CONSCIOUS opt-in
    (env ``VIBEMIX_CODEX_ALLOW_SHELL``), gated by the caller; the default path
    stays read-only and surfaces the honest "blocked by upstream bug" error.
    """
    server = "mcp_servers.vibemix_library"
    sandbox_args = (
        ["--dangerously-bypass-approvals-and-sandbox"]
        if bypass_sandbox
        else ["--sandbox", "read-only"]
    )
    return [
        codex_path,
        "exec",
        *sandbox_args,
        "--skip-git-repo-check",
        "--output-schema",
        schema_path,
        "-o",
        out_path,
        "-c",
        f"{server}.command={json.dumps(mcp_command)}",
        "-c",
        f"{server}.args={json.dumps(mcp_args)}",
        "-c",
        f"{server}.startup_timeout_sec={_MCP_STARTUP_TIMEOUT_S}",
        "-c",
        f"{server}.tool_timeout_sec={_MCP_TOOL_TIMEOUT_S}",
        "-c",
        f'{server}.default_tools_approval_mode="auto"',  # no-op today (upstream bug)
        prompt,
    ]


def _validate_against_library(track_ids: list[str], library: RekordboxLibrary) -> list[str]:
    """Keep only ids that resolve in the live library (order-preserving).

    The grounding guard at the result boundary — the model's list is never
    trusted on faith. De-dupes while preserving order.
    """
    out: list[str] = []
    seen: set[str] = set()
    for tid in track_ids:
        if not isinstance(tid, str) or tid in seen:
            continue
        if library.lookup_by_id(tid) is not None:
            out.append(tid)
            seen.add(tid)
    return out


def _drain_tool_tape(events_path: str, printed: int) -> int:
    """Print any new complete tool-event lines since ``printed``; return the new
    count. The MCP child appends one JSON record per tool call; we echo each as
    a ``[viber-tool] <name> <ok|err> <summary>`` line on STDERR (stdout stays the
    pristine result-JSON channel). Best-effort: a missing file or a half-written
    final line is skipped, never fatal."""
    try:
        text = Path(events_path).read_text(encoding="utf-8")
    except OSError:
        return printed
    lines = text.split("\n")
    complete = lines[:-1]  # trailing element is "" (or a partial line) until \n lands
    for line in complete[printed:]:
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if not isinstance(rec, dict):
            continue
        name = str(rec.get("tool", "?"))
        ok = "ok" if rec.get("ok") else "err"
        arg = str(rec.get("arg", "")).strip()
        summary = str(rec.get("summary", ""))
        detail = f"{arg}; {summary}" if arg and summary else arg or summary
        print(f"[viber-tool] {name} {ok} {detail}".rstrip(), file=sys.stderr, flush=True)
    return len(complete)


def _tool_event_display_arg(rec: dict[str, Any]) -> str:
    arg = str(rec.get("arg", "")).replace("\n", " ").strip()
    summary = str(rec.get("summary", "")).replace("\n", " ").strip()
    if arg and summary:
        return f"{arg}; {summary}"[:220]
    return (arg or summary)[:220]


def _read_tool_event_trace(events_path: str) -> list[dict[str, Any]]:
    """Return the authoritative MCP tool tape as UI-ready chat trace rows."""
    try:
        lines = Path(events_path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    rows: list[dict[str, Any]] = []
    for line in lines:
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if not isinstance(rec, dict):
            continue
        name = str(rec.get("tool") or "").strip()
        if not name:
            continue
        ok = rec.get("ok")
        rows.append(
            {
                "name": name,
                "arg": _tool_event_display_arg(rec),
                "ok": ok if isinstance(ok, bool) else True,
            }
        )
    return rows


def _record_codex_ai_message(
    *,
    surface: str,
    request: str,
    prompt: str | None,
    result: object,
    live_context: dict[str, Any] | None = None,
) -> None:
    """Persist a fail-soft observability row for a Codex-backed engine turn."""
    try:
        reply = str(getattr(result, "reply", "") or "").strip()
        rationale = str(getattr(result, "rationale", "") or "").strip()
        error = getattr(result, "error", None)
        text = reply or rationale or (str(error) if error else "")
        tools_used = getattr(result, "tools_used", None)
        tool_trace = getattr(result, "tool_trace", None)
        track_ids = getattr(result, "track_ids", None)
        move_grades = getattr(result, "move_grades", None)
        stop_reason = getattr(result, "stop_reason", None)
        playlist = getattr(result, "playlist", None)
        export_path = getattr(result, "export_path", None)
        if playlist is None:
            playlist_name = getattr(result, "playlist_name", None)
            m3u_path = getattr(result, "m3u_path", None)
            json_path = getattr(result, "json_path", None)
            if playlist_name or m3u_path or json_path:
                playlist = {
                    "name": playlist_name,
                    "m3u_path": m3u_path,
                    "json_path": json_path,
                }
        stop_text = str(stop_reason or "model_done")
        response_id = f"{time.strftime('%Y%m%d-%H%M%S')}_{surface}_{stop_text}"
        append_global_ai_message(
            engine="codex",
            surface=surface,
            direction="assistant",
            text=text,
            response_id=response_id,
            event=surface,
            provider="codex_cli",
            model=None,
            stop_reason=str(stop_reason or "model_done"),
            prompt_chars=len(prompt) if prompt is not None else None,
            response_chars=len(text),
            live_context=live_context,
            tools_used=[str(t) for t in tools_used] if isinstance(tools_used, list) else [],
            tool_trace=tool_trace if isinstance(tool_trace, list) else [],
            move_grades=move_grades if isinstance(move_grades, list) else [],
            extra={
                "request": request,
                "track_ids": track_ids if isinstance(track_ids, list) else [],
                "playlist": playlist,
                "export_path": export_path,
                "error": str(error) if error else None,
                "question": getattr(result, "question", None),
                "choices": getattr(result, "choices", None),
                "live_verification": getattr(result, "live_verification", None),
                "backend": "codex_exec",
            },
            prompt=prompt,
            response=text,
        )
    except Exception:
        pass


def _start_tool_tape(events_path: str) -> Callable[[], None]:
    """Start a daemon tailer that streams the live tool tape to STDERR while the
    blocking Codex subprocess runs. Returns a ``stop()`` callable the caller MUST
    invoke (in a ``finally``) to halt the thread and drain the last lines —
    otherwise the daemon spins until process exit once the tempdir is cleaned."""
    stop = threading.Event()

    def _tail() -> None:
        printed = 0
        while not stop.is_set():
            printed = _drain_tool_tape(events_path, printed)
            stop.wait(0.15)
        _drain_tool_tape(events_path, printed)  # final drain after Codex exits

    t = threading.Thread(target=_tail, name="viber-tool-tape", daemon=True)
    t.start()

    def _stop() -> None:
        stop.set()
        t.join(timeout=1.0)

    return _stop


def curate_with_codex(
    theme: str,
    library: RekordboxLibrary,
    *,
    name: str | None = None,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    codex_path: str | None = None,
    mcp_command: str | None = None,
    mcp_args: list[str] | None = None,
    allow_shell: bool | None = None,
    _runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> CodexCurateResult:
    """Run one curation via ``codex exec`` against the MCP server.

    ``allow_shell`` opts into ``--dangerously-bypass-approvals-and-sandbox`` —
    REQUIRED today because of the open codex regression (openai/codex#16685)
    that auto-cancels every MCP tool call in non-interactive exec otherwise.
    ``None`` (default) reads env ``VIBEMIX_CODEX_ALLOW_SHELL``. Without it, the
    run uses the safe read-only sandbox and returns an honest "blocked by
    upstream bug" result instead of silently granting shell access.

    ``_runner`` is injectable so tests exercise every guard branch without
    Codex installed. ``library`` is used only for the result-boundary
    grounding re-validation (read-only).
    """
    prompt_text: str | None = None

    def _finish(result: CodexCurateResult) -> CodexCurateResult:
        _record_codex_ai_message(
            surface="viber_curate",
            request=theme,
            prompt=prompt_text,
            result=result,
        )
        return result

    if allow_shell is None:
        allow_shell = os.environ.get("VIBEMIX_CODEX_ALLOW_SHELL", "").strip() not in (
            "",
            "0",
            "false",
            "no",
        )

    codex = find_codex(codex_path)
    if codex is None:
        return _finish(
            CodexCurateResult(
                theme=theme,
                stop_reason="codex_not_installed",
                error=(
                    "Codex CLI not found. Install it (`npm i -g @openai/codex` or "
                    "`brew install codex`) and run `codex login` to enable AI "
                    "playlists."
                ),
            )
        )

    # Upstream regression gate: without the bypass, codex exec auto-cancels
    # every MCP tool call (openai/codex#16685) → curation can't run. Rather than
    # fail cryptically, surface the honest choice up-front. The user opts into
    # the bypass (which grants codex shell access) consciously.
    if not allow_shell:
        return _finish(
            CodexCurateResult(
                theme=theme,
                stop_reason="codex_mcp_blocked",
                error=(
                    "Codex's MCP tool calls are auto-cancelled in non-interactive "
                    "mode (upstream bug openai/codex#16685). Running them needs "
                    "`--dangerously-bypass-approvals-and-sandbox`, which also grants "
                    "codex shell access. Set VIBEMIX_CODEX_ALLOW_SHELL=1 for the "
                    "current local Codex path."
                ),
            )
        )

    # The MCP server is launched by Codex as a STDIO child: this interpreter
    # running `-m vibemix.library.mcp_server`. Absolute interpreter path so it
    # works regardless of Codex's cwd / PATH.
    command = mcp_command or sys.executable
    args = mcp_args if mcp_args is not None else ["-m", "vibemix.library.mcp_server"]

    with tempfile.TemporaryDirectory(prefix="viber-codex-") as td:
        schema_path = str(Path(td) / "schema.json")
        out_path = str(Path(td) / "out.json")
        # Plan 99-04: side-channel file the MCP-side LibraryToolset writes on
        # threshold-trip. Allocated INSIDE the TemporaryDirectory `with` block
        # (Pitfall 4): the temp dir is cleaned up at `with` exit, so the read
        # MUST happen before this block ends or the file disappears.
        stop_reason_path = str(Path(td) / "stop_reason.json")
        # Live tool-tape side-channel. Passed to the MCP child as an ARG (see
        # build_argv mcp_args below), NOT via env: the boot-probe verified Codex
        # does not forward the parent's process env to MCP children, so the env
        # route silently no-ops. Args are part of the spawn command → always cross.
        tool_events_path = str(Path(td) / "tool_events.jsonl")
        Path(schema_path).write_text(json.dumps(_OUTPUT_SCHEMA), encoding="utf-8")

        prompt_text = build_prompt(theme)
        argv = build_argv(
            codex,
            mcp_command=command,
            mcp_args=[*args, "--vibemix-tool-events", tool_events_path],
            schema_path=schema_path,
            out_path=out_path,
            prompt=prompt_text,
            bypass_sandbox=allow_shell,
        )

        # Plan 99-04: inject the side-channel path on the subprocess env arg
        # (NOT os.environ — test isolation, the wrapper never mutates the
        # parent process's env). Codex CLI passes env to its MCP children;
        # build_toolset() in mcp_server logs presence/absence at boot
        # (Plan 99-04 Task 5, B1 Option A probe).
        env = build_subprocess_env(codex)
        env["VIBEMIX_STOP_REASON_FILE"] = stop_reason_path
        # LIVE TOOL TAPE: the MCP child (LibraryToolset.dispatch) appends one
        # JSON record per tool call to this path; a daemon tailer echoes each to
        # STDERR as `[viber-tool] …` while the (blocking) Codex subprocess runs,
        # so the user watches Viber work instead of a frozen prompt. STDERR keeps
        # the stdout result-JSON channel pristine; the Rust layer tails these
        # `[viber-tool]` lines for the in-app tape.
        env["VIBEMIX_TOOL_EVENTS_FILE"] = tool_events_path
        _tape_stop = _start_tool_tape(tool_events_path)

        try:
            proc = _runner(
                argv,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                env=env,
                # `codex exec` reads extra instructions from stdin when it's
                # piped/inherited; a non-TTY child stdin makes it block/err with
                # "Reading additional input from stdin...". DEVNULL = the prompt
                # is the positional arg, full stop.
                stdin=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            # Race: binary vanished between which() and spawn.
            return _finish(
                CodexCurateResult(
                    theme=theme,
                    stop_reason="codex_not_installed",
                    error="Codex CLI disappeared at spawn time.",
                )
            )
        except subprocess.TimeoutExpired:
            return _finish(
                CodexCurateResult(
                    theme=theme,
                    stop_reason="timeout",
                    error=f"Codex did not finish within {timeout_s:.0f}s.",
                )
            )
        finally:
            _tape_stop()

        stderr = proc.stderr or ""
        if proc.returncode != 0:
            low = stderr.lower()
            if any(h in low for h in _AUTH_HINTS):
                return _finish(
                    CodexCurateResult(
                        theme=theme,
                        stop_reason="codex_auth_required",
                        error="Codex is not logged in. Run `codex login`.",
                    )
                )
            return _finish(
                CodexCurateResult(
                    theme=theme,
                    stop_reason="error",
                    error=f"codex exec failed (exit {proc.returncode}): {stderr.strip()[:400]}",
                )
            )

        # Plan 99-04: Channel A side-channel SHORT-CIRCUIT — runs BEFORE the
        # out.json parse so a tool_starvation trip on the MCP side wins over
        # any (likely-stale) out.json content. Phase 100 forward-compat: the
        # branch reads ``payload.get("reason") == "tool_starvation"`` so a
        # sibling ``elif payload.get("reason") == "clarification_needed":``
        # drops in without refactoring. The fallback string is structurally
        # UNREACHABLE in production — Plan 99-03's _build_starvation_payload
        # always seeds 'hint' for cases A/B/C; the fallback is defensive only.
        if Path(stop_reason_path).exists():
            try:
                payload = json.loads(Path(stop_reason_path).read_text(encoding="utf-8"))
                if isinstance(payload, dict) and payload.get("reason") == "tool_starvation":
                    return _finish(
                        CodexCurateResult(
                            theme=theme,
                            stop_reason="tool_starvation",
                            error=str(
                                payload.get("hint")
                                or "no playlist — tool starvation, no hint available"
                            ),
                        )
                    )
                # Plan 100-03: sibling extension of the tool_starvation branch.
                # Same side-channel file, same wrapper-side read, same short-
                # circuit posture. Question + choices propagate to CLI (exit
                # 11 in Plan 100-04) + Telegram (Plan 100-05) via the new
                # CodexCurateResult fields. Defensive isinstance checks fall
                # back to None on malformed shape — structurally unreachable
                # in production (Plan 100-01's _build_clarification_payload
                # always populates both fields with the right shape, pinned
                # by Plan 100-01's tests).
                if isinstance(payload, dict) and payload.get("reason") == "clarification_needed":
                    q = payload.get("question")
                    cs = payload.get("choices")
                    return _finish(
                        CodexCurateResult(
                            theme=theme,
                            stop_reason="clarification_needed",
                            question=str(q) if isinstance(q, str) else None,
                            choices=([str(c) for c in cs] if isinstance(cs, list) else None),
                        )
                    )
            except (OSError, json.JSONDecodeError):
                pass  # fall through to existing parse logic

        # Parse the schema-enforced final message.
        try:
            raw = Path(out_path).read_text(encoding="utf-8").strip()
        except OSError:
            raw = ""
        if not raw:
            return _finish(
                CodexCurateResult(
                    theme=theme,
                    stop_reason="empty_output",
                    error="Codex produced no output.",
                )
            )
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return _finish(
                CodexCurateResult(
                    theme=theme,
                    stop_reason="empty_output",
                    error="Codex output was not valid JSON.",
                )
            )
        # --output-schema enforces an object, but never trust it on faith — a
        # bare array/scalar would AttributeError on .get() below (and that line
        # is outside the try, so it would escape "never raises").
        if not isinstance(payload, dict):
            return _finish(
                CodexCurateResult(
                    theme=theme,
                    stop_reason="empty_output",
                    error="Codex output was not a JSON object.",
                )
            )

    raw_ids = payload.get("track_ids")
    if not isinstance(raw_ids, list) or not raw_ids:
        return _finish(
            CodexCurateResult(
                theme=theme,
                stop_reason="no_playlist",
                rationale=str(payload.get("rationale", "")),
                error="Codex returned no track_ids.",
            )
        )

    # GROUNDING re-validation at the result boundary.
    validated = _validate_against_library(raw_ids, library)
    if not validated:
        return _finish(
            CodexCurateResult(
                theme=theme,
                stop_reason="no_playlist",
                rationale=str(payload.get("rationale", "")),
                error="No returned track_id resolved in the library (grounding).",
            )
        )

    # PERSIST — the wrapper is the single validated writer (codex SELECTS, we
    # WRITE), so a playlist file always lands even if the model didn't call the
    # MCP create_playlist tool. create_playlist re-validates every id against the
    # library (gate #2) and writes the neutral M3U + JSON.
    playlist_name = name or str(payload.get("name") or theme)
    m3u_path: str | None = None
    json_path: str | None = None
    try:
        from vibemix.library.create_playlist import create_playlist as _persist

        res = _persist(library, playlist_name, validated)
        m3u_path = str(res.m3u_path)
        json_path = str(res.json_path)
        validated = res.track_ids  # the persisted, de-duped, validated order
    except Exception as e:
        logger.warning("[codex] persist failed: %s", e)

    return _finish(
        CodexCurateResult(
            theme=theme,
            stop_reason="created",
            playlist_name=playlist_name,
            track_ids=validated,
            m3u_path=m3u_path,
            json_path=json_path,
            rationale=str(payload.get("rationale", "")),
        )
    )


# ---------------------------------------------------------------------------- #
# Set-prep (build-set) over Codex — discover → sequence → export.               #
# ---------------------------------------------------------------------------- #

# The set-prep tools (discover_pool / get_track_energy / sequence_set /
# export_set) are exposed by the SAME MCP server as the curate tools, so the
# grounding gate (seen-set + library re-validation) is identical. Only the
# prompt + output schema differ: the model must SEQUENCE on an energy curve and
# EXPORT to a Rekordbox-importable XML, then return the export path.
_BUILD_SET_RULES = (
    "You are preparing a DJ SET (an ordered, mixable sequence), not just a "
    "playlist. Use ONLY the provided tools.\n"
    "WORKFLOW (in order):\n"
    "1. discover_pool — find a grounded candidate pool for the brief (normally "
    "k=15 unless the user asked for a long set; optionally bounded by "
    "bpm/duration). This is the ONLY way to introduce track_ids.\n"
    "2. get_track_energy — inspect candidates' perceived energy as needed.\n"
    "3. sequence_set — order the chosen track_ids on the requested energy curve. "
    "Pass ONLY track_ids returned by discover_pool this run. If the DJ asks for "
    "deep cuts / surprise / less obvious picks, pass novelty in the 0..1 range; "
    "otherwise leave novelty unset.\n"
    "4. For set-aware mix points, use get_track_sections on the ordered tracks, "
    "then transition_slate for adjacent moves you need to explain. The tr_* "
    "candidate ids come from the tool; never invent them.\n"
    "5. For smart hot-cue prep, call smart_hot_cues on grounded track_ids; if "
    "the DJ asks to write cues, call export_smart_cues with issued proposal/cue "
    "ids. Never pass raw cue payloads.\n"
    "6. If export is requested, export_set — write the final ordered set to a "
    "Rekordbox XML and capture the returned `path`. If export is not requested, "
    "skip export_set and return export_path as an empty string.\n"
    "RULES (non-negotiable):\n"
    "1. NEVER invent a track_id, title, artist, BPM, or key. Every track_id MUST "
    "have come from a discover_pool result in THIS run.\n"
    "2. Keys/BPM/energy come from the tools (deterministic) — never compute or "
    "guess them.\n"
    "3. Cue/section/timing claims must come from get_track_sections / "
    "transition_slate / compile_musical_context / smart_hot_cues; never invent "
    "a cue slot, proposal id, cue id, or exact bar count.\n"
    "4. Return the final JSON object {name, track_ids, export_path, rationale}: "
    "the ORDERED track_ids in play order, the export_set `path` as export_path "
    "(empty string if you did not export), and a short rationale for the arc.\n"
    "5. Keep it tight and mixable — a focused, well-sequenced set beats a padded "
    "one."
)

# Strict structured-output schema (OpenAI strict mode: every prop in `required`,
# additionalProperties: false). export_path is required-but-may-be-empty so the
# model always surfaces the field; we treat "" as "not exported".
_BUILD_SET_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "track_ids": {"type": "array", "items": {"type": "string"}},
        "export_path": {"type": "string"},
        "rationale": {"type": "string"},
    },
    "required": ["name", "track_ids", "export_path", "rationale"],
    "additionalProperties": False,
}


def build_set_prompt(
    brief: str,
    *,
    curve: str | None = None,
    name: str | None = None,
    n_slots: int | None = None,
    export: bool = True,
) -> str:
    """Compose the set-prep prompt: shared persona/lens + set-prep rules + brief.

    Curve / name are folded in as grounded hints; the agent still owns the tool
    calls (mirrors the legacy `_cmd_library_build_set` hint-folding).
    """
    hints: list[str] = []
    if curve:
        hints.append(f"prefer the '{curve}' energy curve")
    if name:
        hints.append(f"name the set '{name}'")
    if n_slots:
        hints.append(f"target exactly {n_slots} slots")
    hints.append("export requested" if export else "do not export; return export_path as empty")
    brief_line = brief.strip()
    if hints:
        brief_line = f"{brief_line} ({'; '.join(hints)})"
    # Reuse the shared lens/persona prefix from the curate system prompt, then
    # swap the rule block for the set-prep workflow.
    persona = _system_prompt().rsplit(_RULES_BLOCK, 1)[0].rstrip()
    return f"{persona} {_BUILD_SET_RULES}\n\nSet brief: {brief_line}"


def build_set_with_codex(
    brief: str,
    library: RekordboxLibrary,
    *,
    curve: str | None = None,
    name: str | None = None,
    n_slots: int | None = None,
    export: bool = True,
    timeout_s: float = BUILD_SET_TIMEOUT_S,
    codex_path: str | None = None,
    mcp_command: str | None = None,
    mcp_args: list[str] | None = None,
    allow_shell: bool | None = None,
    _runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> CodexCurateResult:
    """Run one set-prep (discover → sequence → export) via ``codex exec``.

    Mirrors :func:`curate_with_codex` (same guards, MCP wiring, result-boundary
    grounding) but drives the set-prep tool surface and surfaces the Rekordbox
    ``export_path`` written by the ``export_set`` MCP tool. The export tool is
    itself grounded (seen-set + library re-validation), so the written XML never
    references an invented track.
    """
    prompt_text: str | None = None

    def _finish(result: CodexCurateResult) -> CodexCurateResult:
        _record_codex_ai_message(
            surface="viber_build_set",
            request=brief,
            prompt=prompt_text,
            result=result,
        )
        return result

    if allow_shell is None:
        allow_shell = os.environ.get("VIBEMIX_CODEX_ALLOW_SHELL", "").strip() not in (
            "",
            "0",
            "false",
            "no",
        )

    codex = find_codex(codex_path)
    if codex is None:
        return _finish(
            CodexCurateResult(
                theme=brief,
                stop_reason="codex_not_installed",
                error=(
                    "Codex CLI not found. Install it (`npm i -g @openai/codex` or "
                    "`brew install codex`) and run `codex login` to enable AI sets."
                ),
            )
        )

    if not allow_shell:
        return _finish(
            CodexCurateResult(
                theme=brief,
                stop_reason="codex_mcp_blocked",
                error=(
                    "Codex's MCP tool calls are auto-cancelled in non-interactive "
                    "mode (upstream bug openai/codex#16685). Running them needs "
                    "`--dangerously-bypass-approvals-and-sandbox`. To use the Codex "
                    "backend, set VIBEMIX_CODEX_ALLOW_SHELL=1."
                ),
            )
        )

    command = mcp_command or sys.executable
    args = mcp_args if mcp_args is not None else ["-m", "vibemix.library.mcp_server"]

    with tempfile.TemporaryDirectory(prefix="viber-codex-set-") as td:
        schema_path = str(Path(td) / "schema.json")
        out_path = str(Path(td) / "out.json")
        # Plan 99-04: parallel propagation for set-prep. Same Pitfall-4
        # discipline as curate_with_codex — read INSIDE the `with` block.
        stop_reason_path = str(Path(td) / "stop_reason.json")
        # Live tool-tape side-channel. Passed to the MCP child as an ARG (see
        # build_argv mcp_args below), NOT via env: the boot-probe verified Codex
        # does not forward the parent's process env to MCP children, so the env
        # route silently no-ops. Args are part of the spawn command → always cross.
        tool_events_path = str(Path(td) / "tool_events.jsonl")
        Path(schema_path).write_text(json.dumps(_BUILD_SET_SCHEMA), encoding="utf-8")

        prompt_text = build_set_prompt(
            brief,
            curve=curve,
            name=name,
            n_slots=n_slots,
            export=export,
        )
        argv = build_argv(
            codex,
            mcp_command=command,
            mcp_args=[*args, "--vibemix-tool-events", tool_events_path],
            schema_path=schema_path,
            out_path=out_path,
            prompt=prompt_text,
            bypass_sandbox=allow_shell,
        )

        # Plan 99-04: inject side-channel path on subprocess env (uniform
        # with curate_with_codex; see that wrapper's comment for the test-
        # isolation rationale).
        env = build_subprocess_env(codex)
        env["VIBEMIX_STOP_REASON_FILE"] = stop_reason_path
        # LIVE TOOL TAPE: the MCP child (LibraryToolset.dispatch) appends one
        # JSON record per tool call to this path; a daemon tailer echoes each to
        # STDERR as `[viber-tool] …` while the (blocking) Codex subprocess runs,
        # so the user watches Viber work instead of a frozen prompt. STDERR keeps
        # the stdout result-JSON channel pristine; the Rust layer tails these
        # `[viber-tool]` lines for the in-app tape.
        env["VIBEMIX_TOOL_EVENTS_FILE"] = tool_events_path
        _tape_stop = _start_tool_tape(tool_events_path)

        try:
            proc = _runner(
                argv,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                env=env,
                stdin=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            return _finish(
                CodexCurateResult(
                    theme=brief,
                    stop_reason="codex_not_installed",
                    error="Codex CLI disappeared at spawn time.",
                )
            )
        except subprocess.TimeoutExpired:
            return _finish(
                CodexCurateResult(
                    theme=brief,
                    stop_reason="timeout",
                    error=f"Codex did not finish within {timeout_s:.0f}s.",
                )
            )
        finally:
            _tape_stop()

        stderr = proc.stderr or ""
        if proc.returncode != 0:
            low = stderr.lower()
            if any(h in low for h in _AUTH_HINTS):
                return _finish(
                    CodexCurateResult(
                        theme=brief,
                        stop_reason="codex_auth_required",
                        error="Codex is not logged in. Run `codex login`.",
                    )
                )
            return _finish(
                CodexCurateResult(
                    theme=brief,
                    stop_reason="error",
                    error=f"codex exec failed (exit {proc.returncode}): {stderr.strip()[:400]}",
                )
            )

        # Plan 99-04: Channel A side-channel SHORT-CIRCUIT (parallel of
        # curate_with_codex). Phase 100 forward-compat: branch on
        # ``payload.get("reason") == "tool_starvation"`` so the sibling
        # ``clarification_needed`` extension lands cleanly. Fallback string
        # is structurally UNREACHABLE in production (Plan 99-03's
        # _build_starvation_payload always seeds 'hint').
        if Path(stop_reason_path).exists():
            try:
                payload = json.loads(Path(stop_reason_path).read_text(encoding="utf-8"))
                if isinstance(payload, dict) and payload.get("reason") == "tool_starvation":
                    return _finish(
                        CodexCurateResult(
                            theme=brief,
                            stop_reason="tool_starvation",
                            error=str(
                                payload.get("hint")
                                or "no playlist — tool starvation, no hint available"
                            ),
                        )
                    )
                # Plan 100-03: parallel of the curate_with_codex sibling
                # branch. Uniform propagation across both wrappers — the
                # set-prep code path also surfaces clarification_needed via
                # the same dataclass shape (theme=brief substitution).
                if isinstance(payload, dict) and payload.get("reason") == "clarification_needed":
                    q = payload.get("question")
                    cs = payload.get("choices")
                    return _finish(
                        CodexCurateResult(
                            theme=brief,
                            stop_reason="clarification_needed",
                            question=str(q) if isinstance(q, str) else None,
                            choices=([str(c) for c in cs] if isinstance(cs, list) else None),
                        )
                    )
            except (OSError, json.JSONDecodeError):
                pass  # fall through to existing parse logic

        try:
            raw = Path(out_path).read_text(encoding="utf-8").strip()
        except OSError:
            raw = ""
        if not raw:
            return _finish(
                CodexCurateResult(
                    theme=brief, stop_reason="empty_output", error="Codex produced no output."
                )
            )
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return _finish(
                CodexCurateResult(
                    theme=brief,
                    stop_reason="empty_output",
                    error="Codex output was not valid JSON.",
                )
            )
        if not isinstance(payload, dict):
            return _finish(
                CodexCurateResult(
                    theme=brief,
                    stop_reason="empty_output",
                    error="Codex output was not a JSON object.",
                )
            )

    raw_ids = payload.get("track_ids")
    if not isinstance(raw_ids, list) or not raw_ids:
        return _finish(
            CodexCurateResult(
                theme=brief,
                stop_reason="no_playlist",
                rationale=str(payload.get("rationale", "")),
                error="Codex returned no track_ids.",
            )
        )

    validated = _validate_against_library(raw_ids, library)
    if not validated:
        return _finish(
            CodexCurateResult(
                theme=brief,
                stop_reason="no_playlist",
                rationale=str(payload.get("rationale", "")),
                error="No returned track_id resolved in the library (grounding).",
            )
        )

    # export_path comes from the export_set tool (grounded writer). Trust only a
    # path that actually exists on disk — an empty/missing path means "no export".
    raw_export = str(payload.get("export_path") or "").strip()
    export_path: str | None = raw_export if raw_export and Path(raw_export).exists() else None

    # Persist a neutral M3U/JSON too (mirror curate: the wrapper is the validated
    # writer), so the set has a playlist artifact alongside the Rekordbox XML.
    playlist_name = name or str(payload.get("name") or brief)
    m3u_path: str | None = None
    json_path: str | None = None
    try:
        from vibemix.library.create_playlist import create_playlist as _persist

        res = _persist(library, playlist_name, validated)
        m3u_path = str(res.m3u_path)
        json_path = str(res.json_path)
        validated = res.track_ids
    except Exception as e:
        logger.warning("[codex] set persist failed: %s", e)

    return _finish(
        CodexCurateResult(
            theme=brief,
            stop_reason="exported" if export_path is not None else "created",
            playlist_name=playlist_name,
            track_ids=validated,
            m3u_path=m3u_path,
            json_path=json_path,
            rationale=str(payload.get("rationale", "")),
            export_path=export_path,
        )
    )


# --------------------------------------------------------------------------- #
# Viber CHAT over Codex — the conversational co-host on the agentic engine.    #
# Same MCP grounded-tool surface + same guards as curate; free-text reply.     #
# --------------------------------------------------------------------------- #

# Chat is an interactive UI turn. It may chain tools, but a stalled Codex loop
# must degrade quickly enough that the Library window does not look frozen.
CHAT_TIMEOUT_S = 90.0

# Structured final message for a chat turn. Like _OUTPUT_SCHEMA: every property
# is `required` + additionalProperties:false (structured-output constraint).
_CHAT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "reply": {"type": "string"},
        "tools_used": {"type": "array", "items": {"type": "string"}},
        "tool_trace": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "arg": {"type": "string"},
                    "ok": {"type": "boolean"},
                },
                "required": ["name", "arg", "ok"],
                "additionalProperties": False,
            },
        },
        "track_ids": {"type": "array", "items": {"type": "string"}},
        "move_grades": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "candidate_id": {"type": "string"},
                    "track_id": {"type": "string"},
                    "title": {"type": "string"},
                    "slug": {"type": "string"},
                    "label": {"type": "string"},
                    "xp": {"type": "number"},
                    "reason": {"type": "string"},
                    "overdrive": {"type": "boolean"},
                    "streak": {"type": ["number", "null"]},
                    "total_xp": {"type": ["number", "null"]},
                    "level": {"type": ["number", "null"]},
                    "level_xp": {"type": ["number", "null"]},
                    "next_level_xp": {"type": ["number", "null"]},
                    "level_up": {"type": "boolean"},
                    "levels_gained": {"type": "number"},
                },
                "required": [
                    "candidate_id",
                    "track_id",
                    "title",
                    "slug",
                    "label",
                    "xp",
                    "reason",
                    "overdrive",
                    "streak",
                    "total_xp",
                    "level",
                    "level_xp",
                    "next_level_xp",
                    "level_up",
                    "levels_gained",
                ],
                "additionalProperties": False,
            },
        },
        "playlist": {
            "type": ["object", "null"],
            "properties": {
                "name": {"type": "string"},
                "track_ids": {"type": "array", "items": {"type": "string"}},
                "m3u_path": {"type": "string"},
                "json_path": {"type": "string"},
                "dropped_ids": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["name", "track_ids", "m3u_path", "json_path", "dropped_ids"],
            "additionalProperties": False,
        },
        "export_path": {"type": ["string", "null"]},
    },
    "required": [
        "reply",
        "tools_used",
        "tool_trace",
        "track_ids",
        "move_grades",
        "playlist",
        "export_path",
    ],
    "additionalProperties": False,
}

_CHAT_RULES_BLOCK = (
    "You are in an ongoing CHAT with a DJ — talk like a real friend in their "
    "ear: concrete, tight, no generic AI filler. Use ONLY the provided tools to "
    "ground facts.\n"
    "RULES (non-negotiable):\n"
    "1. Only name a track that a search_vibe / discover_pool call returned THIS "
    "run. Never invent a track, title, artist, BPM, or key.\n"
    "2. Keys / BPM / energy come from the tools (get_track_features / "
    "get_track_energy), never your memory.\n"
    "3. For mix-point or cue-entry advice, use get_track_sections, "
    "transition_slate, compile_musical_context, and smart_hot_cues. Only mention "
    "cue slots, proposal ids, cue ids, candidate ids, or exact timing that "
    "those tools issued. If writing smart cues, use export_smart_cues with "
    "issued ids, never raw cue payloads.\n"
    "4. Ground a web or technique claim with the matching tool "
    "(web_search / retrieve_dj_knowledge) — let the source "
    "show.\n"
    "5. You do NOT have to call a tool every turn; if they're just chatting, "
    "chat back.\n"
    "6. When done, return the final JSON {reply, tools_used, tool_trace, "
    "track_ids, move_grades, playlist, export_path}: reply is your spoken answer to the DJ; "
    "tools_used lists the tool names you called this turn. tool_trace lists the "
    "same calls as {name, arg, ok}, where arg is the shortest useful argument "
    "or intent the DJ should see and ok is false only if the tool failed. "
    "track_ids is any library track you referenced (in order, empty if none). "
    "move_grades is any transition_slate / compile_musical_context grade you "
    "explicitly used, copied as {candidate_id, track_id, title, slug, label, "
    "xp, reason, overdrive, streak, total_xp, level, level_xp, next_level_xp, "
    "level_up, levels_gained}. Copy streak/level fields from current.grade_progress "
    "or a grade_progress claim only when the tool packet exposed them; otherwise "
    "use null for numeric progress fields, false for level_up, and 0 for "
    "levels_gained. Use [] if no transition grade was used. "
    "If you call create_playlist, "
    "copy its returned {name, track_ids, m3u_path, json_path, dropped_ids} into "
    "playlist; otherwise playlist=null. If you call export_set, copy its "
    "returned path into export_path; otherwise export_path=null.\n"
    "7. If a live/deck/move answer has weak evidence, do not confess, apologize, "
    "self-correct, or expose guard/proof/debug language. Use calm product "
    "language about the grounded move or sound note, and keep the internal "
    "reasons in tool_trace / live_verification only."
)


def _chat_system_prompt() -> str:
    """Codex chat system prompt — shared curator voice + chat rules + taste."""
    from vibemix.prompts.matrix import build_curator_instruction

    return build_curator_instruction(_shared_lens()) + "\n" + _CHAT_RULES_BLOCK + _taste_hint()


_LIVE_CONTEXT_MIN_CONF: float = 0.3
_LIVE_DECK_SIDES = ("A", "B", "C", "D")
_LIVE_MOVE_RE = re.compile(r"\b([ABCD])_(?:low|mid|hi|filter|volume|play)")
_LIVE_RECENT_MOVE_CAP = 6
_LIVE_AUDIO_DELTA_CAP = 4
_LIVE_EVIDENCE_CAP = 10
_LIVE_EVIDENCE_REFS_CAP = 14
_LIVE_MIDI_EVIDENCE_CAP = 4
_LIVE_HISTORY_CAP = 3
_LIVE_HISTORY_SCAN_LIMIT = 80
_CHAT_HISTORY_TURNS_CAP = 8
_CHAT_HISTORY_TEXT_CAP = 500
_LIVE_EVIDENCE_TOKEN_RE = re.compile(r"^[A-Za-z0-9_:.=@+-]{1,128}$")
_LIVE_SOURCE_STATUS_KEYS: tuple[str, ...] = (
    "controller",
    "controller_connection",
    "library",
    "library_tracks",
    "library_source",
    "library_match",
    "nowplaying",
    "nowplaying_owner",
    "nowplaying_title",
    "audible_deck",
    "resolution",
    "resolved_side",
    "second_deck_source",
    "screen_vision",
    "last_known_sides",
    "last_known_rule",
)
_LIVE_TRUSTED_DECK_SOURCES: frozenset[str] = _SHARED_DECK_CONTEXT_TRUSTED_SOURCES
_LIVE_DECK_SOURCES: frozenset[str] = _LIVE_TRUSTED_DECK_SOURCES | frozenset(
    {"last_known", "live_context", "unknown"}
)
_LIVE_CONTEXT_CAP = 16
_LIVE_CONTEXT_SCHEMA_VERSION = 2
_LIVE_CONTEXT_REQUIRED_CAPABILITIES: frozenset[str] = frozenset(
    {
        "audio_part_context",
        "deck_audio_separation_context",
        "deck_audio_features_context",
        "deck_audio_delta_context",
        "deck_audio_window_context",
        "deck_source_status",
        "audio_window_map",
        "audio_delta",
        "live_evidence",
    }
)
_MULTI_DECK_VERDICT_RE = re.compile(
    r"\b("
    r"great|good|clean|successful|smooth|tight|solid|nice|nailed|worked|perfect|"
    r"lit|bomb|sexy"
    r")\b",
    re.IGNORECASE,
)
_LIVE_CONTEXT_DIRECT_REQUEST_RE = re.compile(
    r"\b("
    r"what happened|what(?:'s| is) happening|was that|did that|did it|did i|am i|"
    r"current|currently|right now|now playing|live deck|loaded|audible|"
    r"deck|move|knob|fader|crossfader|xfader|eq|filter|mixer|controller"
    r")\b",
    re.IGNORECASE,
)
_LIVE_CONTEXT_DEICTIC_RE = re.compile(
    r"\b(what happened|what(?:'s| is) happening|was that|did that|did it|did i|am i|this|that|just)\b",
    re.IGNORECASE,
)
_LIVE_CONTEXT_OUTCOME_RE = re.compile(
    r"\b("
    r"transition|blend|switch|segue|handoff|bridge|layer|drop|mix"
    r")\b",
    re.IGNORECASE,
)
_LIBRARY_CONTEXT_REQUEST_RE = re.compile(
    r"\b("
    r"find|search|discover|dig|recommend|suggest|give me|make me|build|curate|"
    r"playlist|crate|set|tracks?|songs?|vibe"
    r")\b",
    re.IGNORECASE,
)
_LIVE_CONTEXT_CORRECTION_REPLY_RE = re.compile(
    r"\b("
    r"i need to correct (?:the|that) live read|resolved decks=|"
    r"live evidence gate:|won't call that a transition|"
    r"cannot call that a transition|can't call that a transition|"
    r"musical outcome claim needs|live proof is incomplete|"
    r"transition verdict is held|quality grade is held|"
    r"cause or quality verdict is held|"
    r"hold the transition verdict|hold the quality grade|"
    r"hold the cause/quality verdict|"
    r"tracking that as a live mix moment|tracking that as a live move|"
    r"i only have audible deck mix|cleaner two-deck read|"
    r"live read is stronger|live read is still locking"
    r")\b",
    re.IGNORECASE,
)
_LIVE_CONTEXT_PUBLIC_DIAGNOSTIC_REPLY_RE = re.compile(
    r"\b("
    r"i need to correct (?:the|that) live read|resolved decks=|"
    r"live evidence gate:|transition_block=|transition_watch=|"
    r"second_deck_identity=|deck_lanes=|deck_reference=|deck_source=|"
    r"claim_policy=|proof_not_ready|missing_physical_proof|"
    r"unsupported_live_outcome_claim|move_grades_without_live_proof|"
    r"guard_violations|live_verification|tool_trace|"
    r"source_status_rule=|rule=unresolved_deck_is_not_transition_evidence|"
    r"rule=deck1_deck2_reference_not_outcome|"
    r"rule=per_lane_identity_route_control_not_outcome|"
    r"my bad(?: on| with)? (?:the )?live|"
    r"my mistake(?: on| with)? (?:the )?live|"
    r"bad read on my part|"
    r"i (?:gave|fed) you (?:a )?(?:bad|wrong) (?:live )?read|"
    r"i (?:messed|screwed) up(?: on| with)? (?:the )?live|"
    r"i (?:was|am|'m) wrong(?: about| on| with)? (?:the )?live|"
    r"i (?:made|am making|made a) mistake(?: in| with| on)? (?:the )?live|"
    r"i (?:got|read) (?:that|this) wrong(?: from| in)? (?:the )?live|"
    r"i hallucinated (?:the )?live|"
    r"i (?:should(?:n't| not) have|should not have) (?:called|claimed|said)|"
    r"i (?:overclaimed|over-claimed|falsely claimed)|"
    r"i(?:'m| am| was) (?:being )?(?:stupid|dumb|confused)(?: about| on| with)? "
    r"(?:the )?live|"
    r"i(?:'m| am| was) (?:doing|saying) (?:something )?(?:stupid|dumb|stupidity)"
    r"(?: about| on| with)? (?:the )?live|"
    r"(?:that|this) was (?:stupid|dumb) (?:on|from) (?:the )?live|"
    r"i only have audible deck mix|live read is still locking|"
    r"i(?:'m| am) not sure(?: yet)? (?:what happened|from this live read|"
    r"from the live read|about the live read|on the live read)|"
    r"i (?:can't|cannot) tell(?: yet)? (?:what happened|from this live read|"
    r"from the live read)"
    r")\b",
    re.IGNORECASE,
)
_LIBRARY_REQUEST_LIVE_LEAK_RE = re.compile(
    r"\b("
    r"live(?:[- ]?read|[- ]?move|[- ]?deck|[- ]?context)?|current deck|"
    r"resolved decks?|deck blockers?|evidence gates?|claim_policy|"
    r"sound change(?: right there)?|move right there|that drop|the drop|"
    r"caught the live move|transition_block|transition_watch"
    r")\b",
    re.IGNORECASE,
)
_LIVE_AUDIO_SOURCE_DETAIL_NOUN_RE = re.compile(
    r"\b("
    r"vocal|vocals|voice|lyric|lyrics|kick|kickdrum|kick drum|snare|clap|"
    r"hi[- ]?hat|hat|hats|drum|drums|bassline|lead|synth|pad|stem|stems|"
    r"acapella|instrumental"
    r")\b",
    re.IGNORECASE,
)
_LIVE_AUDIO_SOURCE_DETAIL_CLAIM_RE = re.compile(
    r"\b("
    r"hear|heard|sounds?|feels?|opened(?:\s+up)?|opening|tight(?:ened|er|ening)?|"
    r"clean(?:ed|er)?|clear(?:ed|er)?|brighter|darker|wider|punch(?:y|ier)|"
    r"muddy|muddier|landed|came in|sits?|cut(?:s|ting)? through|present|up front"
    r")\b",
    re.IGNORECASE,
)
_LIVE_AUDIO_SOURCE_DETAIL_BOUNDARY_RE = re.compile(
    r"\b("
    r"can't tell|cannot tell|can't say|cannot say|not enough proof|not proof|"
    r"don't have proof|do not have proof|won't claim|will not claim|"
    r"not source[- ]level proof|not stem proof|not isolated"
    r")\b",
    re.IGNORECASE,
)
_LIVE_GROUNDED_PUBLIC_REPLY = (
    "The live read is grounded now. I can score it from the locked deck context."
)
_LIVE_AUDIO_SOURCE_DETAIL_HELD_REPLY = (
    "I only have a broad listener read from the audio here, not source-level proof."
)
_LIVE_AUDIO_VIBE_CONTRACT = (
    "LIVE AUDIO CONTRACT: audio_delta, deck_audio_features_context, "
    "deck_audio_delta_context, deck_audio_window_context, audio_part_context, "
    "and audio_window_context are listener/vibe evidence for texture, energy, "
    "motion, density, mood, and silence/music presence. They are not proof of "
    "track identity, deck identity, hidden sources such as vocals/kicks/stems, "
    "or EQ/fader/filter/cue causality. If the DJ asks whether a move fixed, "
    "cleaned, opened, tightened, saved, or improved the sound, give a pure "
    "listener read like 'the low end "
    "got hollow for a moment' or stay at the evidence boundary; never credit or "
    "blame the control from audio alone."
)


def _compact_chat_request(message: str) -> str:
    return " ".join(str(message or "").strip().lower().split())


def _live_context_use_mode(message: str) -> str:
    """Return how prominently Viber should use the live deck packet this turn."""
    text = _compact_chat_request(message)
    if not text:
        return "silent_guard"

    direct_live_request = bool(_LIVE_CONTEXT_DIRECT_REQUEST_RE.search(text))
    deictic_outcome_request = bool(
        _LIVE_CONTEXT_DEICTIC_RE.search(text) and _LIVE_CONTEXT_OUTCOME_RE.search(text)
    )
    if not (direct_live_request or deictic_outcome_request):
        return "silent_guard"

    # Search/crate/set-prep words do not hide an explicit current-deck ask
    # ("find me something for what is loaded now"), but they keep generic
    # library requests from being pulled into live-deck correction mode just
    # because the live packet is attached.
    library_request = bool(_LIBRARY_CONTEXT_REQUEST_RE.search(text))
    current_deck_anchor = bool(
        re.search(
            r"\b(current|currently|right now|now playing|loaded|audible|live deck|deck)\b",
            text,
            re.IGNORECASE,
        )
    )
    if library_request and not (current_deck_anchor or deictic_outcome_request):
        return "silent_guard"
    return "active_live_context"


def _is_library_context_request(message: str) -> bool:
    """Return true when the DJ is asking for crate/library/set help."""
    return bool(_LIBRARY_CONTEXT_REQUEST_RE.search(_compact_chat_request(message)))


def _live_context_transport_is_stale(live_context: dict[str, Any] | None) -> bool:
    if not live_context:
        return False
    schema_version = _clean_live_float(live_context.get("live_context_schema_version"))
    capabilities = set(_live_context_capabilities(live_context.get("live_context_capabilities")))
    return bool(
        schema_version is None
        or schema_version < _LIVE_CONTEXT_SCHEMA_VERSION
        or (_LIVE_CONTEXT_REQUIRED_CAPABILITIES - capabilities)
    )


def _live_context_use_instruction(
    message: str,
    live_context: dict[str, Any] | None = None,
) -> str:
    mode = _live_context_use_mode(message)
    if mode == "active_live_context":
        text = (
            "LIVE CONTEXT USE: active_live_context. The DJ is asking about the "
            "current live deck/move/audio moment, so apply CURRENT LIVE DECK "
            "CONTEXT, claim_policy, freshness, provenance, and evidence gates "
            "directly before answering. "
            + _LIVE_AUDIO_VIBE_CONTRACT
        )
        if _live_context_transport_is_stale(live_context):
            text += (
                " Transport is stale_or_pre_schema_v2, so treat live context as "
                "partial: do not judge transitions or move outcomes; say the live "
                "session must be restarted/resampled before a reliable live verdict."
            )
        return text
    text = (
        "LIVE CONTEXT USE: silent_guard. The DJ's last turn is not asking about "
        "the current live deck/move/audio moment. Keep CURRENT LIVE DECK CONTEXT "
        "as a hidden safety rail only: do not mention live_context, claim_policy, "
        "resolved decks, deck blockers, evidence gates, or live-read correction "
        "language. For crate, library search, vibe, playlist, or set-building "
        "requests, answer the requested library job with grounded tool results. "
        "If no grounded library tool result is available, say that plainly; never "
        "fill the turn by describing a live move, current deck, or sound change."
    )
    if _live_context_transport_is_stale(live_context):
        text += " Stale transport remains hidden unless the DJ asks about current live proof."
    return text


def _looks_like_unprompted_live_correction(reply: str) -> bool:
    return bool(
        reply
        and (
            _LIVE_CONTEXT_CORRECTION_REPLY_RE.search(reply)
            or _LIVE_CONTEXT_PUBLIC_DIAGNOSTIC_REPLY_RE.search(reply)
        )
    )


def _looks_like_library_request_live_leak(reply: str) -> bool:
    return bool(reply and _LIBRARY_REQUEST_LIVE_LEAK_RE.search(reply))


def _clean_live_text(raw: Any, *, max_len: int = 96) -> str | None:
    if raw is None:
        return None
    text = " ".join(str(raw).split())
    if not text:
        return None
    return text[:max_len]


def _clean_live_float(raw: Any) -> float | None:
    if raw is None or isinstance(raw, bool):
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if not (value == value and value not in (float("inf"), float("-inf"))):
        return None
    return value


def _clean_live_evidence_token(raw: Any, *, max_len: int = 128) -> str | None:
    text = _clean_live_text(raw, max_len=max_len)
    if not text or " " in text:
        return None
    return text if _LIVE_EVIDENCE_TOKEN_RE.fullmatch(text) else None


def _live_evidence_priority(token: str) -> int:
    if token.startswith("midi:"):
        return 0
    if "deck_lanes=" in token:
        return 1
    if "deck_reference=" in token:
        return 2
    if "deck_source=" in token:
        return 3
    if "transition_block=" in token or "transition_watch=" in token:
        return 4
    if "transition_candidate=" in token:
        return 5
    if "second_deck_identity=" in token:
        return 6
    if "deck_audio_capture=" in token:
        return 7
    if "deck_audio_features=" in token:
        return 8
    if "deck_audio_delta=" in token:
        return 9
    if "deck_audio_window=" in token:
        return 10
    if "move_scope=" in token:
        return 11
    if "move_effect=" in token or "audio_delta=" in token:
        return 12
    if "deck_audio_support=" in token:
        return 13
    if "deck_route=" in token:
        return 14
    return 15


def _clean_live_evidence_list(raw: Any, *, cap: int = _LIVE_EVIDENCE_CAP) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[tuple[int, int, str]] = []
    seen: set[str] = set()
    index = 0
    for item in raw:
        token = _clean_live_evidence_token(item)
        if token and token not in seen:
            out.append((_live_evidence_priority(token), index, token))
            seen.add(token)
            index += 1
    if len(out) <= cap:
        return [token for _priority, _index, token in out]
    selected = sorted(out, key=lambda item: (item[0], item[1]))[:cap]
    selected.sort(key=lambda item: item[1])
    return [token for _priority, _index, token in selected]


def _live_evidence(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None

    out: dict[str, Any] = {}
    mix = _clean_live_evidence_list(raw.get("mix"))
    if mix:
        out["mix"] = mix

    midi: list[dict[str, Any]] = []
    raw_midi = raw.get("midi")
    if isinstance(raw_midi, list):
        for item in raw_midi[-_LIVE_MIDI_EVIDENCE_CAP:]:
            if not isinstance(item, dict):
                continue
            key = _clean_live_evidence_token(item.get("key"), max_len=96)
            t_session = _clean_live_float(item.get("t"))
            if key is None or t_session is None:
                continue
            midi.append({"key": key, "t": round(max(0.0, t_session), 1)})
    if midi:
        out["midi"] = midi

    raw_refs = raw.get("refs") if isinstance(raw.get("refs"), list) else []
    derived_refs = [f"midi:{item['key']}@{item['t']:.1f}" for item in midi]
    derived_refs.extend(f"mix:{key}" for key in mix)
    refs = _clean_live_evidence_list([*raw_refs, *derived_refs], cap=_LIVE_EVIDENCE_REFS_CAP)
    if refs:
        out["refs"] = refs[:_LIVE_EVIDENCE_REFS_CAP]

    return out or None


def _merge_live_evidence(existing: Any, incoming: Any) -> dict[str, Any] | None:
    """Merge raw socket evidence with locally derived deck-context atoms."""
    old = existing if isinstance(existing, dict) else {}
    new = _live_evidence(incoming) if isinstance(incoming, dict) else None
    new = new or {}

    merged: dict[str, Any] = {}
    mix = _clean_live_evidence_list(
        [
            *(old.get("mix") if isinstance(old.get("mix"), list) else []),
            *(new.get("mix") if isinstance(new.get("mix"), list) else []),
        ]
    )
    if mix:
        merged["mix"] = mix

    midi: list[dict[str, Any]] = []
    seen_midi: set[tuple[str, float]] = set()
    for raw_list in (old.get("midi"), new.get("midi")):
        if not isinstance(raw_list, list):
            continue
        for item in raw_list:
            if not isinstance(item, dict):
                continue
            key = _clean_live_evidence_token(item.get("key"), max_len=96)
            t_session = _clean_live_float(item.get("t"))
            if key is None or t_session is None:
                continue
            rounded_t = round(max(0.0, t_session), 1)
            ident = (key, rounded_t)
            if ident in seen_midi:
                continue
            seen_midi.add(ident)
            midi.append({"key": key, "t": rounded_t})
    if midi:
        merged["midi"] = midi[-_LIVE_MIDI_EVIDENCE_CAP:]

    derived_refs = [f"midi:{item['key']}@{item['t']:.1f}" for item in merged.get("midi", [])]
    derived_refs.extend(f"mix:{key}" for key in mix)
    refs = _clean_live_evidence_list(
        [
            *(old.get("refs") if isinstance(old.get("refs"), list) else []),
            *(new.get("refs") if isinstance(new.get("refs"), list) else []),
            *derived_refs,
        ],
        cap=_LIVE_EVIDENCE_REFS_CAP,
    )
    if refs:
        merged["refs"] = refs

    return merged or None


def _live_deck_fields(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None

    deck: dict[str, Any] = {}
    for key in ("title", "track_id", "camelot", "key"):
        text = _clean_live_text(raw.get(key))
        if text:
            deck[key] = text

    bpm = _clean_live_float(raw.get("bpm"))
    if bpm is not None and bpm > 0:
        deck["bpm"] = bpm

    confidence = _clean_live_float(raw.get("confidence"))
    if confidence is not None:
        deck["confidence"] = max(0.0, min(1.0, confidence))

    source = _clean_live_evidence_token(raw.get("source"), max_len=32)
    if deck and source in _LIVE_DECK_SOURCES:
        deck["source"] = source

    return deck or None


def _clean_live_int_0_127(raw: Any, *, default: int | None = None) -> int | None:
    value = _clean_live_float(raw)
    if value is None:
        return default
    return max(0, min(127, int(value)))


def _live_deck_controls(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    out: dict[str, Any] = {}
    for key, default in (
        ("vol", 0),
        ("eq_low", 64),
        ("eq_mid", 64),
        ("eq_hi", 64),
        ("filter", 64),
    ):
        value = _clean_live_int_0_127(raw.get(key), default=default)
        if value is not None:
            out[key] = value
    if isinstance(raw.get("play"), bool):
        out["play"] = raw["play"]
    return out or None


def _live_deck_mixer(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    out: dict[str, Any] = {}
    if isinstance(raw.get("connected"), bool):
        out["connected"] = raw["connected"]
    xfader = _clean_live_int_0_127(raw.get("xfader"), default=None)
    if xfader is not None:
        out["xfader"] = xfader
    confidence = _clean_live_float(raw.get("deck_confidence"))
    if confidence is not None:
        out["deck_confidence"] = max(0.0, min(1.0, confidence))
    for side in ("A", "B"):
        controls = _live_deck_controls(raw.get(side))
        if controls:
            out[side] = controls
    return out or None


def _live_source_status(raw: Any) -> dict[str, str] | None:
    if not isinstance(raw, dict):
        return None
    out: dict[str, str] = {}
    for key in _LIVE_SOURCE_STATUS_KEYS:
        text = _clean_live_text(raw.get(key), max_len=96)
        if not text:
            continue
        token = re.sub(r"[^A-Za-z0-9_:.=@+-]+", "_", text.strip().lower()).strip("_")
        if token:
            out[key] = token[:96]
    return out or None


def _live_span_pair(raw: Any) -> list[float] | None:
    if not isinstance(raw, list) or len(raw) < 2:
        return None
    a = _clean_live_float(raw[0])
    b = _clean_live_float(raw[1])
    if a is None or b is None:
        return None
    return [round(a, 1), round(b, 1)]


def _live_audio_part_label(raw: Any) -> str | None:
    label = _clean_live_text(raw, max_len=8)
    if not label:
        return None
    label = label.upper()
    return label if re.fullmatch(r"P[2-9][0-9]?", label) else None


def _live_context_capabilities(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        token = _clean_live_evidence_token(item, max_len=48)
        if not token or token in seen:
            continue
        seen.add(token)
        out.append(token)
        if len(out) >= _LIVE_CONTEXT_CAP:
            break
    return out


def _live_audio_window_map(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    common_required = {
        "p1": "master_global_mix",
        "p1_heard": True,
        "timeline": "past_action_future",
        "together_audio": "P1_global_mix",
        "decks_together": True,
        "deck_separation": "deck_lanes_context",
        "lane_aliases": "deck1:A,deck2:B",
        "rule": "time_alignment_not_outcome_verdict",
    }
    if any(raw.get(key) != expected for key, expected in common_required.items()):
        return None

    deck_a = raw.get("deckA_audio")
    deck_b = raw.get("deckB_audio")
    per_deck_audio = raw.get("per_deck_audio")
    duplicate_audio = raw.get("duplicate_audio")
    deck_audio_separation: str | None = None
    deck_part_span_s: list[float] | None = None
    deck_part_activity: dict[str, str] = {}
    if (
        deck_a == "not_attached"
        and deck_b == "not_attached"
        and per_deck_audio == "structured_text_only"
        and duplicate_audio == "same_master_not_deck_split"
        and raw.get("deck_audio_separation") in {None, "not_attached"}
    ):
        deck_a_out = "not_attached"
        deck_b_out = "not_attached"
        deck_audio_separation = "not_attached"
    else:
        deck_a_label = _live_audio_part_label(deck_a)
        deck_b_label = _live_audio_part_label(deck_b)
        if not (
            deck_a_label
            and deck_b_label
            and deck_a_label != deck_b_label
            and per_deck_audio == "deck_pair_parts"
            and duplicate_audio == "separate_deck_pair_parts"
            and raw.get("deck_audio_separation") == "deck_audio_separation_context"
        ):
            return None
        deck_a_out = deck_a_label
        deck_b_out = deck_b_label
        deck_audio_separation = "deck_audio_separation_context"
        deck_part_span_s = _live_span_pair(raw.get("deck_part_span_s"))
        raw_activity = raw.get("deck_part_activity")
        if isinstance(raw_activity, dict):
            for side in ("A", "B"):
                value = _clean_live_evidence_token(raw_activity.get(side), max_len=16)
                if value in {"active", "silent"}:
                    deck_part_activity[side] = value

    pre_s = _live_span_pair(raw.get("pre_s"))
    current_s = _live_span_pair(raw.get("current_s"))
    action_s = _live_span_pair(raw.get("action_s"))
    if pre_s is None or current_s is None or action_s is None:
        return None
    anchors: list[dict[str, Any]] = []
    raw_anchors = raw.get("move_anchors")
    if isinstance(raw_anchors, list):
        for item in raw_anchors[-3:]:
            if not isinstance(item, dict):
                continue
            label = _clean_live_text(item.get("label"), max_len=72)
            token = _clean_live_evidence_token(item.get("token"), max_len=96)
            relation = _clean_live_evidence_token(item.get("relation"), max_len=32)
            if not label or not token or not relation:
                continue
            anchors.append(
                {
                    "label": label,
                    "token": token,
                    "age_s": _clean_live_float(item.get("age_s")),
                    "relation": relation,
                }
            )
    future_raw = raw.get("future")
    future = future_raw if isinstance(future_raw, dict) else {}
    if future.get("heard") is not False:
        return None
    out = {
        **common_required,
        "deckA_audio": deck_a_out,
        "deckB_audio": deck_b_out,
        "per_deck_audio": per_deck_audio,
        "duplicate_audio": duplicate_audio,
        "deck_audio_separation": deck_audio_separation,
        "pre_s": pre_s,
        "current_s": current_s,
        "action_s": action_s,
        "move_anchors": anchors,
        "future": {
            key: value
            for key, value in future.items()
            if key in {"heard", "span", "part", "source", "span_s", "rule"}
        },
    }
    if deck_part_span_s is not None:
        out["deck_part_span_s"] = deck_part_span_s
    if deck_part_activity:
        out["deck_part_activity"] = deck_part_activity
    return out


def _audio_part_deck_labels_for_viber(audio_part_context: str | None) -> dict[str, str]:
    if not audio_part_context or "per_deck_audio=deck_pair_parts" not in audio_part_context:
        return {}
    labels: dict[str, str] = {}
    for side in ("A", "B"):
        match = re.search(rf"\bdeck{side}_part=(P[2-9][0-9]?)\b", audio_part_context)
        if not match:
            return {}
        labels[side] = match.group(1)
    return labels if labels.get("A") != labels.get("B") else {}


def _audio_part_deck_activity_for_viber(
    audio_part_context: str | None,
    deck_labels: dict[str, str],
) -> dict[str, str]:
    if not audio_part_context or set(deck_labels) != {"A", "B"}:
        return {}
    activity: dict[str, str] = {}
    for side, label in deck_labels.items():
        match = re.search(
            rf"\b{re.escape(label)}_activity=deck{side}_(active|silent)\b",
            audio_part_context,
        )
        if match:
            activity[side] = match.group(1)
    return activity


def _audio_window_context_deck_labels_for_viber(audio_window_context: str | None) -> dict[str, str]:
    if not audio_window_context or "per_deck_audio=deck_pair_parts" not in audio_window_context:
        return {}
    labels: dict[str, str] = {}
    for side in ("A", "B"):
        match = re.search(rf"\bdeck{side}_audio=(P[2-9][0-9]?)\b", audio_window_context)
        if not match:
            return {}
        labels[side] = match.group(1)
    return labels if labels.get("A") != labels.get("B") else {}


def _audio_window_matches_audio_parts_for_viber(
    audio_window_context: str | None,
    deck_labels: dict[str, str],
) -> bool:
    window_labels = _audio_window_context_deck_labels_for_viber(audio_window_context)
    if deck_labels:
        return window_labels == deck_labels
    return not window_labels


def _audio_window_map_matches_audio_parts_for_viber(
    audio_window_map: dict[str, Any] | None,
    deck_labels: dict[str, str],
) -> bool:
    if not audio_window_map or audio_window_map.get("per_deck_audio") != "deck_pair_parts":
        return not deck_labels
    map_labels = {
        "A": str(audio_window_map.get("deckA_audio") or ""),
        "B": str(audio_window_map.get("deckB_audio") or ""),
    }
    return bool(
        deck_labels
        and map_labels == deck_labels
        and map_labels["A"] != map_labels["B"]
        and all(_live_audio_part_label(label) for label in map_labels.values())
    )


def normalize_live_source_status_for_viber(raw: Any) -> dict[str, str] | None:
    """Return the bounded structured deck-source status Viber may inspect."""
    return _live_source_status(raw)


def normalize_live_audio_window_map_for_viber(raw: Any) -> dict[str, Any] | None:
    """Return the bounded structured P1 audio-window map Viber may inspect."""
    return _live_audio_window_map(raw)


def _render_audio_window_map_line(audio_map: Any) -> str | None:
    if not isinstance(audio_map, dict):
        return None
    anchors = []
    raw_anchors = audio_map.get("move_anchors")
    if isinstance(raw_anchors, list):
        for item in raw_anchors[:3]:
            if not isinstance(item, dict):
                continue
            token = _clean_live_evidence_token(item.get("token"), max_len=96) or "move"
            relation = _clean_live_evidence_token(item.get("relation"), max_len=32) or "unknown"
            age = _clean_live_float(item.get("age_s"))
            anchors.append(
                f"{token}@-{age:.1f}s:{relation}" if age is not None else f"{token}:age_unknown"
            )
    future_text = "not_attached"
    future = audio_map.get("future") if isinstance(audio_map.get("future"), dict) else {}
    span = future.get("span_s")
    if future.get("part") and isinstance(span, list) and len(span) >= 2:
        try:
            future_text = f"{future.get('part')}:{float(span[0]):.1f}..+{float(span[1]):.1f}"
        except (TypeError, ValueError):
            future_text = str(future.get("part"))[:24]
    deck_a_audio = _clean_live_evidence_token(audio_map.get("deckA_audio"), max_len=24)
    deck_b_audio = _clean_live_evidence_token(audio_map.get("deckB_audio"), max_len=24)
    per_deck_audio = _clean_live_evidence_token(audio_map.get("per_deck_audio"), max_len=32)
    duplicate_audio = _clean_live_evidence_token(audio_map.get("duplicate_audio"), max_len=48)
    if not (deck_a_audio and deck_b_audio and per_deck_audio and duplicate_audio):
        return None
    return (
        "audio_window_map[P1=master_global_mix heard=true old=pre_s "
        f"current=current_s action=action_s future={future_text} "
        f"deckA_audio={deck_a_audio} deckB_audio={deck_b_audio} "
        f"per_deck_audio={per_deck_audio} duplicate_audio={duplicate_audio} anchors="
        + (",".join(anchors) if anchors else "none")
        + " rule=time_alignment_not_outcome_verdict]"
    )


def _normalize_live_context(raw: Any) -> dict[str, Any] | None:
    """Keep only the tiny live-deck fields Viber may safely reason from."""
    if not isinstance(raw, dict):
        return None

    out: dict[str, Any] = {}
    deck = _clean_live_text(raw.get("deck"), max_len=16)
    if deck:
        out["deck"] = deck
    if isinstance(raw.get("audible"), bool):
        out["audible"] = raw["audible"]
    phase = _clean_live_text(raw.get("phase"), max_len=48)
    if phase:
        out["phase"] = phase
    bpm = _clean_live_float(raw.get("bpm"))
    if bpm is not None and bpm > 0:
        out["bpm"] = bpm
    music = _clean_live_float(raw.get("music"))
    if music is not None and music >= 0:
        out["music"] = min(1.0, music)

    schema_version = _clean_live_float(raw.get("live_context_schema_version"))
    if schema_version is not None and schema_version >= 1:
        out["live_context_schema_version"] = int(schema_version)
    capabilities = _live_context_capabilities(raw.get("live_context_capabilities"))
    if capabilities:
        out["live_context_capabilities"] = capabilities

    deck_state: dict[str, dict[str, Any]] = {}
    raw_decks = raw.get("deck_state")
    has_deck_state_payload = isinstance(raw_decks, dict)
    if has_deck_state_payload:
        for side in _LIVE_DECK_SIDES:
            deck_fields = _live_deck_fields(raw_decks.get(side))
            if deck_fields:
                deck_state[side] = deck_fields
    if has_deck_state_payload:
        out["deck_state"] = deck_state

    has_deck_mixer_payload = isinstance(raw.get("deck_mixer"), dict)
    deck_mixer = _live_deck_mixer(raw.get("deck_mixer"))
    if deck_mixer:
        out["deck_mixer"] = deck_mixer
    elif has_deck_mixer_payload:
        out["deck_mixer"] = {}

    deck_source_status = _live_source_status(raw.get("deck_source_status"))
    if deck_source_status:
        out["deck_source_status"] = deck_source_status

    recent_moves: list[str] = []
    raw_moves = raw.get("recent_moves")
    if isinstance(raw_moves, list):
        for label in raw_moves[-_LIVE_RECENT_MOVE_CAP:]:
            text = _clean_live_text(label, max_len=72)
            if text:
                recent_moves.append(text)
    if recent_moves:
        out["recent_moves"] = recent_moves

    deck_lanes_context = _shared_normalize_deck_lanes_context_text(raw.get("deck_lanes_context"))
    if deck_lanes_context:
        out["deck_lanes_context"] = deck_lanes_context

    deck_reference_context = _shared_normalize_deck_reference_context_text(
        raw.get("deck_reference_context")
    )
    if deck_reference_context:
        out["deck_reference_context"] = deck_reference_context

    deck_source_context = _shared_normalize_deck_source_context_text(raw.get("deck_source_context"))
    if deck_source_context:
        out["deck_source_context"] = deck_source_context

    deck_audio_context = _shared_normalize_deck_audio_context_text(raw.get("deck_audio_context"))
    if deck_audio_context:
        out["deck_audio_context"] = deck_audio_context

    deck_audio_separation_context = _shared_normalize_deck_audio_separation(
        raw.get("deck_audio_separation_context")
    )
    if deck_audio_separation_context:
        out["deck_audio_separation_context"] = deck_audio_separation_context

    deck_audio_features_context = _shared_normalize_deck_audio_features_context(
        raw.get("deck_audio_features_context")
    )
    if deck_audio_features_context:
        out["deck_audio_features_context"] = deck_audio_features_context

    deck_audio_delta_context = _shared_normalize_deck_audio_delta_context(
        raw.get("deck_audio_delta_context")
    )
    if deck_audio_delta_context:
        out["deck_audio_delta_context"] = deck_audio_delta_context

    deck_audio_window_context = _shared_normalize_deck_audio_window_context(
        raw.get("deck_audio_window_context")
    )
    if deck_audio_window_context:
        out["deck_audio_window_context"] = deck_audio_window_context

    audio_part_context = _shared_normalize_audio_part_context_text(raw.get("audio_part_context"))
    if audio_part_context:
        out["audio_part_context"] = audio_part_context
    deck_part_labels = _audio_part_deck_labels_for_viber(audio_part_context)

    audio_window_context = _shared_normalize_audio_window_context_text(
        raw.get("audio_window_context")
    )
    if audio_window_context and not _audio_window_matches_audio_parts_for_viber(
        audio_window_context,
        deck_part_labels,
    ):
        audio_window_context = None
    if audio_window_context:
        out["audio_window_context"] = audio_window_context

    audio_window_map = _live_audio_window_map(raw.get("audio_window_map"))
    if audio_window_map and not _audio_window_map_matches_audio_parts_for_viber(
        audio_window_map,
        deck_part_labels,
    ):
        audio_window_map = None
    if audio_window_map:
        out["audio_window_map"] = audio_window_map

    audio_delta: list[str] = []
    raw_audio_delta = raw.get("audio_delta")
    if isinstance(raw_audio_delta, list):
        for item in raw_audio_delta[-_LIVE_AUDIO_DELTA_CAP:]:
            text = _clean_live_text(item, max_len=96)
            if text:
                audio_delta.append(text)
    if audio_delta:
        out["audio_delta"] = audio_delta

    evidence = _live_evidence(raw.get("live_evidence"))
    if evidence:
        out["live_evidence"] = evidence

    state = _music_state_from_live_context(out)
    derived_evidence = _shared_live_evidence_packet(
        state,
        _live_context_recent_moves(out),
        audio_delta_items=_live_context_audio_delta(out),
    )
    merged_evidence = _merge_live_evidence(out.get("live_evidence"), derived_evidence)
    if merged_evidence:
        out["live_evidence"] = merged_evidence

    return out or None


def normalize_live_context_for_viber(live_context: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return the bounded live context Viber will prompt against."""
    normalized = _normalize_live_context(live_context)
    return dict(normalized) if normalized else None


def _music_state_from_live_context(context: dict[str, Any]) -> MusicState:
    """Adapt Viber's raw live-context dict into the shared deck guard model."""
    # Import locally so the curator module never leaks MusicState as a top-level
    # attribute — the curate/Viber boundary stays decoupled from runtime state
    # (test_curate_unify::test_curator_does_not_import_musicstate).
    from vibemix.state.music_state import MusicState

    state = MusicState()
    deck = _clean_live_text(context.get("deck"), max_len=16)
    state.audible_deck = deck or "none"
    if isinstance(context.get("audible"), bool):
        state.audible = context["audible"]
    phase = _clean_live_text(context.get("phase"), max_len=48)
    if phase:
        state.phase = phase
    bpm = _clean_live_float(context.get("bpm"))
    if bpm is not None and bpm > 0:
        state.bpm = bpm

    mixer = context.get("deck_mixer")
    if isinstance(mixer, dict):
        state.controller_connected = bool(mixer.get("connected", False))
        state.xfader = _clean_live_int_0_127(mixer.get("xfader"), default=64) or 64
        state.deck_confidence = _clean_live_float(mixer.get("deck_confidence")) or 0.0
        for side, attr in (("A", "deck_a"), ("B", "deck_b")):
            controls = _live_deck_controls(mixer.get(side))
            if controls:
                setattr(state, attr, controls)

    decks: dict[str, DeckTrack] = {}
    raw_decks = context.get("deck_state")
    if isinstance(raw_decks, dict):
        for side in _LIVE_DECK_SIDES:
            row = raw_decks.get(side)
            if not isinstance(row, dict):
                continue
            source = row.get("source")
            source_text = str(source) if source in _LIVE_DECK_SOURCES else "live_context"
            track = DeckTrack(
                title=_clean_live_text(row.get("title")),
                track_id=_clean_live_text(row.get("track_id")),
                bpm=_clean_live_float(row.get("bpm")) or 0.0,
                key=_clean_live_text(row.get("key")),
                camelot=_clean_live_text(row.get("camelot")),
                confidence=_clean_live_float(row.get("confidence")) or 0.0,
                source=source_text,
            )
            decks[side] = track
    source_status = _live_source_status(context.get("deck_source_status")) or {}
    state.deck_state = DeckState(decks=decks, source_status=source_status)
    return state


def _live_context_recent_moves(context: dict[str, Any]) -> list[str]:
    moves = context.get("recent_moves")
    if not isinstance(moves, list):
        return []
    return [str(label) for label in moves if isinstance(label, str)][-_LIVE_RECENT_MOVE_CAP:]


def _live_context_audio_delta(context: dict[str, Any]) -> list[str]:
    items = context.get("audio_delta")
    if not isinstance(items, list):
        return []
    return [str(item) for item in items if isinstance(item, str)][-_LIVE_AUDIO_DELTA_CAP:]


def _memory_db_candidates() -> list[Path]:
    """Return local memory metadata DB paths, newest schema first."""
    try:
        from vibemix.runtime.config_store import app_data_dir

        root = app_data_dir()
    except Exception:
        return []
    return [root / "memory.db", root / "memory_moments.db"]


def _history_token(text: str) -> str | None:
    token = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return token[:48] if len(token) >= 2 else None


def _historical_move_query_tokens(
    moves: list[str],
    audio_delta: list[str],
    context: dict[str, Any] | None = None,
) -> list[str]:
    tokens: list[str] = []
    raw_sources: list[str] = [*moves[-3:], *audio_delta[:4]]
    if context is not None:
        state = _music_state_from_live_context(context)
        deck_source_context = _shared_render_deck_source_context(state, compact=True)
        if not deck_source_context:
            deck_source_context = (
                context.get("deck_source_context")
                if isinstance(context.get("deck_source_context"), str)
                else None
            )
        if deck_source_context:
            raw_sources.append(deck_source_context)
        deck_lane_context = _shared_render_deck_lane_context(state, compact=True)
        if deck_lane_context:
            raw_sources.append(deck_lane_context)
        deck_reference_context = _shared_render_deck_reference_context(state, compact=True)
        if deck_reference_context:
            raw_sources.append(deck_reference_context)
        audio_window_context = _shared_render_audio_window_context(state, moves)
        if audio_window_context:
            raw_sources.append(audio_window_context)
        evidence = context.get("live_evidence")
        if isinstance(evidence, dict):
            for key in ("mix", "refs"):
                values = evidence.get(key)
                if not isinstance(values, list):
                    continue
                for value in values:
                    text = str(value)
                    if (
                        "deck_lanes=" in text
                        or "deck_reference=" in text
                        or "deck_source=" in text
                        or "deck_audio_support=" in text
                    ):
                        raw_sources.append(text)
        context_feed_contract = _shared_render_context_feed_contract(
            state,
            moves,
            surface="viber_history_query",
        )
        if context_feed_contract:
            raw_sources.append(context_feed_contract)

    for raw in raw_sources:
        whole = _history_token(raw)
        if whole and whole not in tokens:
            tokens.append(whole)
        for part in re.split(r"[^A-Za-z0-9_]+", raw):
            token = _history_token(part)
            if token and token not in tokens:
                tokens.append(token)
    return tokens[:96]


def _compact_history_signature(signature: str, *, cap: int = 220) -> str:
    return _shared_sanitize_history_signature(signature, cap=cap)


def _score_historical_signature(signature: str, tokens: list[str]) -> int:
    low = signature.lower()
    normalized = re.sub(r"[^a-z0-9]+", "_", low)
    score = 0
    if "event=mix_move" in low:
        score += 4
    if "move_effect=" in low:
        score += 3
    if "audio_delta=" in low:
        score += 3
    if "audio_window=" in low or "audio_window_context[" in low:
        score += 2
    for token in tokens:
        if token and (token in low or token in normalized):
            score += 1
    return score


def _read_historical_move_rows(db_path: Path) -> list[tuple[str, str, float, str]]:
    if not db_path.exists():
        return []
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    except sqlite3.Error:
        return []
    try:
        rows = conn.execute(
            "SELECT record_id, session_id, ts, signature FROM moments "
            "WHERE kind = 'coach_line' AND signature LIKE '%event=MIX_MOVE%' "
            "ORDER BY ts DESC LIMIT ?",
            (_LIVE_HISTORY_SCAN_LIMIT,),
        ).fetchall()
    except sqlite3.Error:
        return []
    finally:
        conn.close()
    out: list[tuple[str, str, float, str]] = []
    for record_id, session_id, ts, signature in rows:
        if not isinstance(signature, str) or not signature.strip():
            continue
        out.append((str(record_id), str(session_id), float(ts or 0.0), signature))
    return out


def _render_historical_move_context(raw: Any) -> str | None:
    """Render cheap past move/effect memory for Viber chat.

    This is a raw memory scan, not a generation or audio call. It only activates
    when live_context has both recent controller moves and audio_delta, matching
    the live Gemini recall cost gate.
    """
    context = _normalize_live_context(raw)
    if not context:
        return None
    moves = _live_context_recent_moves(context)
    audio_delta = _live_context_audio_delta(context)
    if not moves or not audio_delta:
        return None

    tokens = _historical_move_query_tokens(moves, audio_delta, context)
    scored: list[tuple[int, float, str, str, str]] = []
    seen: set[str] = set()
    for db_path in _memory_db_candidates():
        for record_id, session_id, ts, signature in _read_historical_move_rows(db_path):
            if record_id in seen:
                continue
            seen.add(record_id)
            score = _score_historical_signature(signature, tokens)
            if score <= 0:
                continue
            scored.append((score, ts, record_id, session_id, signature))
    if not scored:
        return None

    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    lines = [
        "HISTORICAL MOVE CONTEXT (past-session raw memory; not live proof; no extra model call):"
    ]
    for score, _ts, record_id, session_id, signature in scored[:_LIVE_HISTORY_CAP]:
        lines.append(
            "history_move["
            f"id={_clean_live_evidence_token(record_id, max_len=96) or 'unknown'} "
            f"session={_clean_live_evidence_token(session_id, max_len=96) or 'unknown'} "
            f"match={score} "
            f"signature={_compact_history_signature(signature)!r}]"
        )
    lines.append(
        "Historical move context is comparison memory only. It can suggest what "
        "similar knob/fader moves sounded like before, but it cannot upgrade "
        "the current live claim policy or prove the current move was good, "
        "clean, successful, or a transition."
    )
    return "\n".join(lines)


def _render_live_evidence_context(context: dict[str, Any]) -> str | None:
    evidence = context.get("live_evidence")
    if not isinstance(evidence, dict):
        return None

    fields: list[str] = []
    refs = evidence.get("refs")
    if isinstance(refs, list):
        clean_refs = [str(item) for item in refs if isinstance(item, str)][:_LIVE_EVIDENCE_REFS_CAP]
        if clean_refs:
            fields.append("refs=" + ",".join(clean_refs))

    mix = evidence.get("mix")
    if isinstance(mix, list):
        clean_mix = [str(item) for item in mix if isinstance(item, str)][:_LIVE_EVIDENCE_CAP]
        if clean_mix:
            fields.append("mix=" + ",".join(clean_mix))

    midi = evidence.get("midi")
    if isinstance(midi, list):
        midi_refs: list[str] = []
        for item in midi[:_LIVE_MIDI_EVIDENCE_CAP]:
            if not isinstance(item, dict):
                continue
            key = item.get("key")
            t_session = item.get("t")
            if isinstance(key, str) and isinstance(t_session, (int, float)):
                midi_refs.append(f"{key}@{float(t_session):.1f}")
        if midi_refs:
            fields.append("midi=" + ",".join(midi_refs))

    if not fields:
        return None
    fields.append("rule=evidence_categories_not_quality_verdict")
    return "live_evidence[" + " ".join(fields) + "]"


def _transition_context_token(rendered: str | None) -> str | None:
    if not rendered:
        return None
    match = re.search(r"\btransition_(?:block|candidate|watch)=[^\]\s]+", rendered)
    return match.group(0) if match else None


def _policy_from_transition_context(*contexts: str | None) -> str:
    chunks = [context or "" for context in contexts]
    if any("transition_block=" in chunk for chunk in chunks):
        return "blocked"
    if any("transition_watch=" in chunk for chunk in chunks):
        return "watch_not_claim"
    if any("transition_candidate=" in chunk for chunk in chunks):
        return "candidate_not_verdict"
    return "requires_more_evidence"


def _strongest_live_policy(*policies: str | None) -> str:
    policy_set = {policy for policy in policies if policy}
    for policy in ("blocked", "watch_not_claim"):
        if policy in policy_set:
            return policy
    if "supported_verdict" in policy_set:
        return "supported_verdict"
    if "candidate_not_verdict" in policy_set:
        return "candidate_not_verdict"
    return "requires_more_evidence"


def _live_evidence_tokens(context: dict[str, Any]) -> list[str]:
    evidence = context.get("live_evidence")
    if not isinstance(evidence, dict):
        return []
    out: list[str] = []
    for key in ("mix", "refs"):
        values = evidence.get(key)
        if not isinstance(values, list):
            continue
        out.extend(str(item) for item in values if item)
    return out


def _live_context_has_trusted_deck_pair(context: dict[str, Any]) -> bool:
    rows = context.get("deck_state")
    if not isinstance(rows, dict):
        return False
    for side in ("A", "B"):
        row = rows.get(side)
        if not isinstance(row, dict):
            return False
        confidence = _clean_live_float(row.get("confidence")) or 0.0
        if confidence < _LIVE_CONTEXT_MIN_CONF:
            return False
        if not _clean_live_text(row.get("track_id")):
            return False
        if row.get("source") not in _LIVE_TRUSTED_DECK_SOURCES:
            return False
    return True


def _live_context_has_consistent_deck_pair_audio_parts(context: dict[str, Any]) -> bool:
    audio_part_context = (
        context.get("audio_part_context")
        if isinstance(context.get("audio_part_context"), str)
        else None
    )
    deck_labels = _audio_part_deck_labels_for_viber(audio_part_context)
    if set(deck_labels) != {"A", "B"}:
        return False
    audio_window_context = (
        context.get("audio_window_context")
        if isinstance(context.get("audio_window_context"), str)
        else None
    )
    if not _audio_window_matches_audio_parts_for_viber(audio_window_context, deck_labels):
        return False
    audio_window_map = context.get("audio_window_map")
    if not isinstance(audio_window_map, dict):
        return False
    return _audio_window_map_matches_audio_parts_for_viber(audio_window_map, deck_labels)


def _live_evidence_supports_verdict(context: dict[str, Any]) -> bool:
    tokens = _live_evidence_tokens(context)
    if not tokens or not _live_context_recent_moves(context):
        return False
    if not _live_context_has_trusted_deck_pair(context):
        return False
    required_packets = (
        "deck_audio_separation_context",
        "deck_audio_features_context",
        "deck_audio_delta_context",
        "deck_audio_window_context",
        "audio_part_context",
        "audio_window_context",
        "audio_window_map",
    )
    if not all(context.get(packet) for packet in required_packets):
        return False
    if not _live_context_has_consistent_deck_pair_audio_parts(context):
        return False
    text = " ".join(tokens)
    return (
        "transition_candidate=" in text
        and "deck_audio_capture=A_active+B_active" in text
        and "deck_audio_features=" in text
        and "A_active" in text
        and "B_active" in text
        and "deck_audio_delta=" in text
        and "deck_audio_window=" in text
    )


def _live_policy_strength(policy: str | None) -> int:
    return {
        "blocked": 3,
        "watch_not_claim": 2,
        "candidate_not_verdict": 1,
        "supported_verdict": 0,
    }.get(policy or "", 0)


def _live_evidence_policy(context: dict[str, Any]) -> str:
    if _live_evidence_supports_verdict(context):
        return "supported_verdict"
    return _policy_from_transition_context(_render_live_evidence_context(context))


def _live_context_transition_status(audible_deck: str | None, resolved_sides: list[str]) -> str:
    if not resolved_sides:
        return "transition_block=no_resolved_decks"
    if len(resolved_sides) == 1:
        return "transition_block=single_resolved_deck"
    if audible_deck == "mix":
        return "transition_candidate=two_resolved_decks_mixing"
    if audible_deck in ("A", "B"):
        return f"transition_watch=two_resolved_decks_single_audible_{audible_deck}"
    return "transition_watch=two_resolved_decks_audible_unknown"


def _live_move_sides(labels: list[str]) -> set[str]:
    sides: set[str] = set()
    for label in labels:
        sides.update(_LIVE_MOVE_RE.findall(label))
    return sides


def _live_move_controls(labels: list[str]) -> set[str]:
    controls: set[str] = set()
    for label in labels:
        if "xfader" in label:
            controls.add("xfader")
        if "_low:" in label:
            controls.add("low")
        if "_mid:" in label:
            controls.add("mid")
        if "_hi:" in label:
            controls.add("hi")
        if "_filter:" in label:
            controls.add("filter")
        if "_play" in label:
            controls.add("play")
        if "_volume:" in label:
            controls.add("volume")
        if "killed" in label:
            controls.add("eq_kill")
    return controls


def _live_move_scope(touched_sides: set[str], controls: set[str]) -> str:
    if "xfader" in controls or len(touched_sides) >= 2:
        return "cross_deck_move"
    if len(touched_sides) == 1:
        return f"single_deck_move_{next(iter(touched_sides))}"
    return "deck_unknown_move"


def _live_move_transition_status(
    audible_deck: str | None,
    resolved_sides: list[str],
    scope: str,
    controls: set[str],
) -> str:
    if not resolved_sides:
        return "transition_block=no_resolved_decks"
    if len(resolved_sides) < 2:
        return "transition_block=single_resolved_deck"
    if not (scope == "cross_deck_move" or "xfader" in controls):
        return "transition_block=single_deck_move"
    if audible_deck == "mix":
        return "transition_candidate=two_deck_move_audible_mix"
    return "transition_watch=two_deck_move_single_audible"


def _render_live_move_context(
    context: dict[str, Any],
    audible_deck: str | None,
    resolved_sides: list[str],
) -> str | None:
    raw_moves = context.get("recent_moves")
    if not isinstance(raw_moves, list) or not raw_moves:
        return None
    labels = [str(label) for label in raw_moves if isinstance(label, str)]
    if not labels:
        return None

    touched_sides = _live_move_sides(labels)
    controls = _live_move_controls(labels)
    scope = _live_move_scope(touched_sides, controls)
    transition = _live_move_transition_status(
        audible_deck,
        resolved_sides,
        scope,
        controls,
    )
    fields = [
        f"scope={scope}",
        f"sides={'+'.join(sorted(touched_sides)) if touched_sides else 'unknown'}",
        f"controls={'+'.join(sorted(controls)) if controls else 'unknown'}",
        f"audible={audible_deck or 'unknown'}",
        f"resolved={'+'.join(resolved_sides) if resolved_sides else 'none'}",
        transition,
    ]
    return "move_context[" + " ".join(fields) + "]"


def _live_policy_multi_deck_outcome(
    live_status: str,
    move_context: str | None,
    live_evidence_context: str | None = None,
) -> str:
    return _policy_from_transition_context(live_status, move_context, live_evidence_context)


def _render_live_claim_policy(
    live_status: str,
    move_context: str | None,
    resolved_sides: list[str],
    has_recent_moves: bool,
    *,
    shared_policy: str | None = None,
) -> str:
    resolved = "+".join(resolved_sides) if resolved_sides else "none"
    policy = shared_policy or _live_policy_multi_deck_outcome(live_status, move_context)
    audio_quality = (
        "deck_pair_audio_observed" if policy == "supported_verdict" else "not_observed_by_viber"
    )
    outcome_rule = (
        "grounded_by_live_deck_pair_audio" if policy == "supported_verdict" else "do_not_infer"
    )
    fields = [
        f"deck_reference=resolved_{resolved}",
        "control_reference=observed_recent_moves_only"
        if has_recent_moves
        else "control_reference=none",
        f"multi_deck_outcome={policy}",
        f"audio_quality={audio_quality}",
        f"control_to_music_outcome={outcome_rule}",
    ]
    return "claim_policy[" + " ".join(fields) + "]"


def _render_live_context_transport(context: dict[str, Any]) -> str | None:
    schema_version = _clean_live_float(context.get("live_context_schema_version"))
    capabilities = _live_context_capabilities(context.get("live_context_capabilities"))
    capability_set = set(capabilities)
    missing_capabilities = sorted(_LIVE_CONTEXT_REQUIRED_CAPABILITIES - capability_set)
    stale = (
        schema_version is None
        or schema_version < _LIVE_CONTEXT_SCHEMA_VERSION
        or bool(missing_capabilities)
    )
    fields: list[str] = []
    if schema_version is not None and schema_version >= 1:
        fields.append(f"schema={int(schema_version)}")
    else:
        fields.append("schema=missing")
    if capabilities:
        fields.append("capabilities=" + ",".join(capabilities[:_LIVE_CONTEXT_CAP]))
    if missing_capabilities:
        fields.append("missing=" + ",".join(missing_capabilities))
    fields.append(f"status={'stale_or_pre_schema_v2' if stale else 'fresh_schema_v2'}")
    fields.append("rule=transport_receipt_not_musical_evidence")
    return "live_context_transport[" + " ".join(fields) + "]"


def _render_live_context(raw: Any) -> str | None:
    context = _normalize_live_context(raw)
    if not context:
        return None
    state = _music_state_from_live_context(context)
    recent_moves = _live_context_recent_moves(context)

    decks = context.get("deck_state") if isinstance(context.get("deck_state"), dict) else {}
    resolved_sides: list[str] = []
    deck_lines: list[str] = []
    for side in _LIVE_DECK_SIDES:
        deck = decks.get(side) if isinstance(decks, dict) else None
        if not isinstance(deck, dict):
            continue
        confidence = _clean_live_float(deck.get("confidence")) or 0.0
        has_identity = any(deck.get(key) for key in ("title", "track_id", "camelot"))
        if confidence >= _LIVE_CONTEXT_MIN_CONF and has_identity:
            resolved_sides.append(side)

        parts = [f"{side}={deck.get('title')!r}" if deck.get("title") else f"{side}=unknown"]
        if deck.get("camelot"):
            parts.append(f"key={deck['camelot']}")
        elif deck.get("key"):
            parts.append(f"key={deck['key']}")
        bpm = _clean_live_float(deck.get("bpm"))
        if bpm is not None and bpm > 0:
            parts.append(f"bpm={bpm:.0f}")
        if confidence:
            parts.append(f"conf={confidence:.2f}")
        source = deck.get("source")
        if source:
            parts.append(f"src={source}")
        deck_lines.append(" ".join(parts))

    audible_deck = _clean_live_text(context.get("deck"), max_len=16)
    header_parts = []
    if audible_deck:
        header_parts.append(f"deck={audible_deck}")
    if isinstance(context.get("audible"), bool):
        header_parts.append(f"audible={str(context['audible']).lower()}")
    if context.get("phase"):
        header_parts.append(f"phase={context['phase']}")
    bpm = _clean_live_float(context.get("bpm"))
    if bpm is not None and bpm > 0:
        header_parts.append(f"bpm={bpm:.0f}")
    music = _clean_live_float(context.get("music"))
    if music is not None and music >= 0:
        header_parts.append(f"music={music:.3f}")
    header_parts.append(f"resolved={'+'.join(resolved_sides) if resolved_sides else 'none'}")
    deck_context = _shared_render_deck_context(state)
    live_status = _transition_context_token(deck_context) or _live_context_transition_status(
        audible_deck,
        resolved_sides,
    )
    header_parts.append(live_status)

    lines = [
        "CURRENT LIVE DECK CONTEXT (bounded app snapshot, read-only; no extra model call):",
        "live_context[" + " ".join(header_parts) + "]",
    ]
    transport_line = _render_live_context_transport(context)
    if transport_line:
        lines.append(transport_line)
    context_feed_contract = _shared_render_context_feed_contract(
        state,
        recent_moves,
        surface="viber_text",
        force=True,
    )
    if context_feed_contract:
        lines.append(context_feed_contract)
    audio_part_context = (
        context.get("audio_part_context")
        if isinstance(context.get("audio_part_context"), str)
        else None
    )
    if not audio_part_context:
        audio_part_context = _shared_render_audio_part_context(
            audio_seconds=6.0,
            surface="viber_live_context",
            p1_model_heard=False,
        )
    deck_part_labels = _audio_part_deck_labels_for_viber(audio_part_context)
    deck_part_activity = _audio_part_deck_activity_for_viber(audio_part_context, deck_part_labels)
    if audio_part_context:
        lines.append(audio_part_context)
    if deck_context:
        lines.append(deck_context)
    deck_lane_context = _shared_render_deck_lane_context(state)
    if not deck_lane_context:
        deck_lane_context = (
            context.get("deck_lanes_context")
            if isinstance(context.get("deck_lanes_context"), str)
            else None
        )
    if deck_lane_context:
        lines.append(deck_lane_context)
    deck_reference_context = _shared_render_deck_reference_context(state)
    if not deck_reference_context:
        deck_reference_context = (
            context.get("deck_reference_context")
            if isinstance(context.get("deck_reference_context"), str)
            else None
        )
    if deck_reference_context:
        lines.append(deck_reference_context)
    deck_source_context = _shared_render_deck_source_context(state)
    if deck_source_context:
        lines.append(deck_source_context)
    else:
        deck_source_context = (
            context.get("deck_source_context")
            if isinstance(context.get("deck_source_context"), str)
            else None
        )
        if deck_source_context:
            lines.append(deck_source_context)
    mixer_context = _shared_render_mixer_context(state)
    if mixer_context:
        lines.append(mixer_context)
    deck_audio_context = _shared_render_deck_audio_context(state)
    if not deck_audio_context:
        deck_audio_context = (
            context.get("deck_audio_context")
            if isinstance(context.get("deck_audio_context"), str)
            else None
        )
    if deck_audio_context:
        lines.append(deck_audio_context)
    deck_audio_separation_context = (
        context.get("deck_audio_separation_context")
        if isinstance(context.get("deck_audio_separation_context"), str)
        else None
    )
    if not deck_audio_separation_context:
        deck_audio_separation_context = _shared_render_deck_audio_separation()
    if deck_audio_separation_context:
        lines.append(deck_audio_separation_context)
    deck_audio_features_context = (
        context.get("deck_audio_features_context")
        if isinstance(context.get("deck_audio_features_context"), str)
        else None
    )
    if not deck_audio_features_context:
        deck_audio_features_context = _shared_render_deck_audio_features_context(
            context if isinstance(context, dict) else None
        )
    if deck_audio_features_context:
        lines.append(deck_audio_features_context)
    deck_audio_delta_context = (
        context.get("deck_audio_delta_context")
        if isinstance(context.get("deck_audio_delta_context"), str)
        else None
    )
    if not deck_audio_delta_context:
        deck_audio_delta_context = _shared_render_deck_audio_delta_context(
            context if isinstance(context, dict) else None
        )
    if deck_audio_delta_context:
        lines.append(deck_audio_delta_context)
    deck_audio_window_context = (
        context.get("deck_audio_window_context")
        if isinstance(context.get("deck_audio_window_context"), str)
        else None
    )
    if not deck_audio_window_context:
        deck_audio_window_context = _shared_render_deck_audio_window_context(
            context if isinstance(context, dict) else None
        )
    if deck_audio_window_context:
        lines.append(deck_audio_window_context)
    if deck_lines:
        lines.append("decks[" + " | ".join(deck_lines) + "]")
    if isinstance(recent_moves, list) and recent_moves:
        lines.append("recent_moves[" + " | ".join(str(label) for label in recent_moves) + "]")
    audio_window_context = (
        context.get("audio_window_context")
        if isinstance(context.get("audio_window_context"), str)
        else None
    )
    if not audio_window_context:
        audio_window_context = _shared_render_audio_window_context(
            state,
            recent_moves,
            deck_part_labels=deck_part_labels or None,
            deck_part_activity=deck_part_activity or None,
            force=True,
        )
    if audio_window_context:
        lines.append(audio_window_context)
    audio_window_map_line = _render_audio_window_map_line(context.get("audio_window_map"))
    if audio_window_map_line:
        lines.append(audio_window_map_line)
    move_context = _shared_render_move_context(state, recent_moves)
    if move_context:
        lines.append(move_context)
    deck_change_context = _shared_render_deck_change_context(state, recent_moves)
    if deck_change_context:
        lines.append(deck_change_context)
    move_effect_context = _shared_render_move_effect_context(
        state,
        recent_moves,
        audio_delta_items=_live_context_audio_delta(context),
    )
    if move_effect_context:
        lines.append(move_effect_context)
    live_evidence_context = _render_live_evidence_context(context)
    if live_evidence_context:
        lines.append(live_evidence_context)
    shared_policy, _reason = _shared_live_claim_policy(state, recent_moves)
    context_policy = _live_policy_multi_deck_outcome(
        live_status,
        move_context,
        live_evidence_context,
    )
    shared_policy = _strongest_live_policy(shared_policy, context_policy)
    lines.append(
        _render_live_claim_policy(
            live_status,
            move_context,
            resolved_sides,
            isinstance(recent_moves, list) and bool(recent_moves),
            shared_policy=shared_policy,
        )
    )
    lines.append(
        "Read this as labeled live context before reasoning: bind deck1/deck2, "
        "source/provenance, freshness/TTL, cache/static-vs-volatile boundaries, "
        "and history-as-comparison first. Then answer from those labels plus the "
        "grounded tools. If live_context_transport carries status=stale_or_pre_schema_v2, "
        "do not give live transition or move-outcome verdicts; ask for a restarted "
        "live session/resample. If live_context, deck_context, deck_lanes_context, "
        "deck_reference_context, deck_source_context, deck_audio_context, "
        "deck_audio_separation_context, deck_audio_features_context, "
        "deck_audio_delta_context, deck_audio_window_context, audio_window_context, "
        "deck_change_context, "
        "move_effect_context, live_evidence, or move_context carries "
        "transition_block/transition_watch, "
        "do not praise or claim a transition/blend/switch/segue/handoff/bridge/layer. "
        "If it carries transition_candidate, you may name it as a candidate but "
        "must not grade it as good/clean/successful. Treat move_effect_context, "
        "deck_audio_features_context, deck_audio_delta_context, deck_audio_window_context, "
        "and live_evidence "
        "as evidence category references, not causal proof or a skill grade. Use "
        "grounded tools for library tracks, cue timing, and mix-point claims."
    )
    return "\n".join(lines)


def _live_guard_summary(context: dict[str, Any]) -> str:
    deck = _clean_live_text(context.get("deck"), max_len=16) or "unknown deck"
    decks = context.get("deck_state") if isinstance(context.get("deck_state"), dict) else {}
    resolved: list[str] = []
    if isinstance(decks, dict):
        for side in _LIVE_DECK_SIDES:
            row = decks.get(side)
            if not isinstance(row, dict):
                continue
            confidence = _clean_live_float(row.get("confidence")) or 0.0
            if confidence >= _LIVE_CONTEXT_MIN_CONF and any(
                row.get(key) for key in ("title", "track_id", "camelot")
            ):
                resolved.append(side)
    moves = context.get("recent_moves")
    move_hint = ""
    if isinstance(moves, list) and moves:
        move_hint = f"; recent control evidence: {' | '.join(str(m) for m in moves[-3:])}"
    evidence_gate = _transition_context_token(_render_live_evidence_context(context))
    if evidence_gate:
        move_hint += f"; live evidence gate: {evidence_gate}"
    lane_hint = _live_guard_lane_hint(context)
    if lane_hint:
        move_hint += f"; deck lanes={lane_hint}"
    source_hint = _live_guard_source_hint(context)
    if source_hint:
        move_hint += f"; deck source={source_hint}"
    return f"audible deck {deck}; resolved decks={'+'.join(resolved) if resolved else 'none'}{move_hint}"


def _live_guard_lane_hint(context: dict[str, Any]) -> str | None:
    state = _music_state_from_live_context(context)
    rendered = _shared_render_deck_lane_context(state, compact=True)
    if not rendered:
        return None
    inner = rendered.removeprefix("deck_lanes_context[").removesuffix("]")
    inner = inner.replace(" rule=per_lane_identity_route_control_not_outcome", "")
    return inner.replace(" | ", " / ") or None


def _live_guard_source_hint(context: dict[str, Any]) -> str | None:
    state = _music_state_from_live_context(context)
    rendered = _shared_render_deck_source_context(state, compact=True)
    if not rendered:
        rendered = (
            context.get("deck_source_context")
            if isinstance(context.get("deck_source_context"), str)
            else None
        )
    if not rendered:
        return None
    inner = rendered.removeprefix("deck_source_context[").removesuffix("]")
    fields = [
        field
        for field in inner.split()
        if field.startswith(
            (
                "resolved=",
                "unresolved=",
                "sources=",
                "second_deck=",
                "rule=",
            )
        )
    ]
    return " ".join(fields) or None


def _apply_live_claim_guard(reply: str, live_context: dict[str, Any] | None) -> str:
    """Correct unsupported live outcome claims at the result boundary.

    This is intentionally category-based, not phrase-based: under a blocking
    live policy, Viber may reference the observed deck/control evidence, but it
    may not promote that evidence into a multi-deck musical outcome.
    """
    context = _normalize_live_context(live_context)
    if not context or not reply.strip():
        return reply
    outcome_claim = _shared_has_multi_deck_outcome_claim(reply)
    public_diagnostic = bool(_LIVE_CONTEXT_PUBLIC_DIAGNOSTIC_REPLY_RE.search(reply))
    audio_source_detail = _has_unsupported_audio_source_detail_claim(reply, context)
    stale_transport = _live_context_transport_is_stale(context)
    if stale_transport and (outcome_claim or public_diagnostic):
        return "Refresh the live session first, then I'll judge that transition."
    evidence_policy = _live_evidence_policy(context)
    state = _music_state_from_live_context(context)
    recent_moves = _live_context_recent_moves(context)
    shared_policy, _reason = _shared_live_claim_policy(state, recent_moves)
    active_policy = _strongest_live_policy(evidence_policy, shared_policy)
    evidence_overrides_shared = _live_policy_strength(evidence_policy) > _live_policy_strength(
        shared_policy
    )
    if public_diagnostic:
        if active_policy == "supported_verdict":
            return _LIVE_GROUNDED_PUBLIC_REPLY
        if active_policy == "candidate_not_verdict":
            return _SHARED_LIVE_CANDIDATE_HELD_REPLY
        return _SHARED_LIVE_TRANSITION_HELD_REPLY
    if audio_source_detail:
        return _LIVE_AUDIO_SOURCE_DETAIL_HELD_REPLY
    has_disclaimer = bool(outcome_claim and _shared_has_multi_deck_outcome_disclaimer(reply))
    if has_disclaimer and not _shared_has_unsafe_multi_deck_disclaimer_claim(reply):
        if active_policy in {"blocked", "watch_not_claim", "requires_more_evidence"}:
            return _SHARED_LIVE_TRANSITION_HELD_REPLY
        if active_policy == "candidate_not_verdict":
            return _SHARED_LIVE_CANDIDATE_HELD_REPLY
        return reply
    if has_disclaimer and active_policy not in {
        "blocked",
        "watch_not_claim",
        "candidate_not_verdict",
    }:
        return reply
    if (
        evidence_overrides_shared
        and evidence_policy in {"blocked", "watch_not_claim"}
        and outcome_claim
    ):
        return _SHARED_LIVE_TRANSITION_HELD_REPLY
    if (
        evidence_overrides_shared
        and evidence_policy == "candidate_not_verdict"
        and outcome_claim
        and _MULTI_DECK_VERDICT_RE.search(reply)
    ):
        return _SHARED_LIVE_CANDIDATE_HELD_REPLY
    if active_policy == "supported_verdict":
        return reply
    result = _shared_apply_live_claim_guard(
        reply,
        state,
        recent_moves,
        audio_delta_items=_live_context_audio_delta(context),
    )
    if result.corrected:
        return result.text

    rendered = _render_live_context(context) or ""
    if (
        "multi_deck_outcome=blocked" not in rendered
        and "multi_deck_outcome=watch_not_claim" not in rendered
    ):
        return reply
    if not _shared_has_multi_deck_outcome_claim(reply):
        return reply
    if _shared_has_multi_deck_outcome_disclaimer(reply):
        return reply
    return _SHARED_LIVE_TRANSITION_HELD_REPLY


def _has_unsupported_audio_source_detail_claim(reply: str, context: dict[str, Any] | None) -> bool:
    if not context:
        return False
    text = str(reply or "")
    if not text.strip() or _LIVE_AUDIO_SOURCE_DETAIL_BOUNDARY_RE.search(text):
        return False
    return bool(
        _LIVE_AUDIO_SOURCE_DETAIL_NOUN_RE.search(text)
        and _LIVE_AUDIO_SOURCE_DETAIL_CLAIM_RE.search(text)
    )


def _live_context_claim_policy(context: dict[str, Any] | None) -> str:
    if not context:
        return "requires_more_evidence"
    if _live_context_transport_is_stale(context):
        return "requires_more_evidence"
    evidence_policy = _live_evidence_policy(context)
    state = _music_state_from_live_context(context)
    shared_policy, _reason = _shared_live_claim_policy(state, _live_context_recent_moves(context))
    return _strongest_live_policy(evidence_policy, shared_policy)


def _live_context_allows_move_grades(live_context: dict[str, Any] | None) -> bool:
    """Return False when live deck evidence cannot support skill/transition grades."""
    context = _normalize_live_context(live_context)
    if not context:
        return True
    policy = _live_context_claim_policy(context)
    return policy not in {
        "blocked",
        "watch_not_claim",
        "candidate_not_verdict",
        "requires_more_evidence",
    }


def _sanitize_chat_history_text(
    text: str,
    *,
    role: str,
    live_context: dict[str, Any] | None,
) -> str:
    """Bound chat history and keep stale assistant live claims out of the prompt."""
    clean = " ".join(str(text).split())
    if not clean:
        return ""
    if len(clean) > _CHAT_HISTORY_TEXT_CAP:
        clean = clean[: _CHAT_HISTORY_TEXT_CAP - 3].rstrip() + "..."

    # User claims/questions are kept as dialogue. Assistant live outcome claims
    # are the dangerous priming source: an older hallucinated "great transition"
    # should not sit beside a current single-deck live_context packet.
    if role != "viber":
        return clean
    if not _shared_has_multi_deck_outcome_claim(clean):
        return clean

    policy = _live_context_claim_policy(live_context)
    if policy not in {
        "blocked",
        "watch_not_claim",
        "candidate_not_verdict",
        "requires_more_evidence",
    }:
        return clean
    return "[prior Viber live outcome claim omitted; re-check CURRENT LIVE DECK CONTEXT]"


def render_live_context_preview(live_context: dict[str, Any] | None) -> str:
    """Render the exact bounded live-context block Viber chat would receive."""
    return _render_live_context(live_context) or ""


def verify_live_reply_for_viber(
    reply: str,
    live_context: dict[str, Any] | None,
    *,
    move_grades: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return a deterministic verdict for a Viber reply against live proof.

    This is the same result-boundary guard used after Codex speaks, exposed as
    a proof/check helper so a captured live-context packet plus a chat result
    can be audited without another model call.
    """
    context = _normalize_live_context(live_context)
    text = " ".join(str(reply or "").split())
    audio_source_detail = _has_unsupported_audio_source_detail_claim(text, context)
    corrected_reply = _apply_live_claim_guard(text, context) if text else text
    corrected = corrected_reply != text
    grades = move_grades if isinstance(move_grades, list) else []
    grades_allowed = _live_context_allows_move_grades(context)
    violations: list[str] = []
    if not text:
        violations.append("empty_reply")
    if audio_source_detail:
        violations.append("unsupported_audio_source_detail_claim")
    elif corrected:
        violations.append("unsupported_live_outcome_claim")
    if grades and not grades_allowed:
        violations.append("move_grades_without_live_proof")
    transport_status = "none"
    if context:
        transport_status = (
            "stale_or_pre_schema_v2"
            if _live_context_transport_is_stale(context)
            else "fresh_schema_v2"
        )
    return {
        "ok": not violations,
        "violations": violations,
        "reply": text,
        "corrected": corrected,
        "corrected_reply": corrected_reply if corrected else None,
        "claim_policy": _live_context_claim_policy(context),
        "transport_status": transport_status,
        "move_grades_allowed": grades_allowed,
        "move_grades_seen": len(grades),
    }


def chat_prompt(
    message: str,
    history: list[dict[str, Any]] | None = None,
    *,
    live_context: dict[str, Any] | None = None,
) -> str:
    """Render the chat system prompt + the conversation so far + the new turn."""
    convo = ""
    normalized_live_context = _normalize_live_context(live_context)
    for turn in (history or [])[-_CHAT_HISTORY_TURNS_CAP:]:
        if not isinstance(turn, dict):
            continue
        role = str(turn.get("role") or "")
        text = _sanitize_chat_history_text(
            str(turn.get("text") or ""),
            role=role,
            live_context=normalized_live_context,
        )
        if not text:
            continue
        speaker = "Viber" if role == "viber" else "DJ"
        convo += f"{speaker}: {text}\n"
    convo += f"DJ: {message.strip()}"
    live_block = _render_live_context(normalized_live_context)
    history_block = _render_historical_move_context(normalized_live_context)
    context_parts = []
    if live_block:
        context_parts.append(live_block)
        context_parts.append(_live_context_use_instruction(message, normalized_live_context))
        context_parts.append(
            "CHAT HISTORY RULE: previous chat text is dialogue, not live evidence; "
            "CURRENT LIVE DECK CONTEXT and claim_policy override older Viber live reads."
        )
    if history_block:
        context_parts.append(history_block)
    context_block = "\n\n" + "\n\n".join(context_parts) if context_parts else ""
    return (
        f"{_chat_system_prompt()}{context_block}\n\nConversation so far:\n{convo}\n\n"
        "Reply to the DJ's last message."
    )


def _dedupe_ordered(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _normalize_chat_playlist(raw: Any, library: RekordboxLibrary) -> dict[str, Any] | None:
    """Validate a Codex-reported chat playlist artifact before surfacing it.

    The actual write happens inside the MCP process via ``create_playlist``.
    The final JSON merely echoes that tool result, so the wrapper re-checks the
    saved files and track ids at the process boundary. A missing file means no
    visible playlist card; the chat can still show its text and receipts.
    """
    if not isinstance(raw, dict):
        return None
    name = str(raw.get("name") or "").strip()
    raw_ids = [t for t in (raw.get("track_ids") or []) if isinstance(t, str)]
    track_ids = _validate_against_library(raw_ids, library)
    m3u_path = str(raw.get("m3u_path") or "").strip()
    json_path = str(raw.get("json_path") or "").strip()
    if not name or not track_ids or not m3u_path or not json_path:
        return None
    if not Path(m3u_path).exists() or not Path(json_path).exists():
        return None
    dropped_ids = [t for t in (raw.get("dropped_ids") or []) if isinstance(t, str)]
    return {
        "name": name,
        "track_ids": track_ids,
        "m3u_path": m3u_path,
        "json_path": json_path,
        "dropped_ids": dropped_ids,
    }


def _normalize_chat_tool_trace(raw_trace: Any, tools_used: list[str]) -> list[dict[str, Any]]:
    """Return UI-ready tool rows, falling back to legacy name-only receipts."""
    rows: list[dict[str, Any]] = []
    if isinstance(raw_trace, list):
        for item in raw_trace:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            arg = str(item.get("arg") or "").strip()
            ok = item.get("ok")
            rows.append({"name": name, "arg": arg, "ok": ok if isinstance(ok, bool) else True})
    if rows:
        return rows
    return [{"name": n, "arg": "", "ok": True} for n in tools_used]


def _library_request_fallback_reply(
    *,
    playlist: dict[str, Any] | None,
    track_ids: list[str],
    tools_used: list[str],
    tool_trace: list[dict[str, Any]],
) -> str:
    """Replace an irrelevant live correction with the grounded library outcome."""
    if playlist is not None:
        name = str(playlist.get("name") or "playlist").strip() or "playlist"
        count = len(playlist.get("track_ids") or track_ids)
        return f"Built a grounded playlist for that: {name} ({count} tracks)."
    if track_ids:
        return f"Found {len(track_ids)} grounded library candidates for that vibe."
    if tool_trace or tools_used:
        return "I searched the local library for that request; no grounded playlist came back."
    return "I kept that as a library request, but I do not have grounded results to show yet."


_MOVE_GRADE_SLUGS = {"negative", "mid", "clean", "sexy", "bomb", "lit_aff"}


def _optional_move_grade_int(raw: Any, *, lower: int, upper: int) -> int | None:
    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, float) and not raw.is_integer():
        return None
    try:
        value = int(raw)
    except (OverflowError, TypeError, ValueError):
        return None
    if value < lower:
        return None
    return min(value, upper)


def _normalize_chat_move_grades(raw: Any, library: RekordboxLibrary) -> list[dict[str, Any]]:
    """Return grounded move-grade receipts echoed from Viber's transition tools."""
    if not isinstance(raw, list):
        return []
    raw_track_ids = [
        str(item.get("track_id")).strip()
        for item in raw
        if isinstance(item, dict) and str(item.get("track_id") or "").strip()
    ]
    valid_ids = set(_validate_against_library(_dedupe_ordered(raw_track_ids), library))
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        track_id = str(item.get("track_id") or "").strip()
        if track_id not in valid_ids:
            continue
        candidate_id = str(item.get("candidate_id") or "").strip()
        slug = str(item.get("slug") or "").strip().lower()
        label = str(item.get("label") or "").strip().upper()
        if not candidate_id or slug not in _MOVE_GRADE_SLUGS or not label:
            continue
        try:
            xp = int(item.get("xp"))
        except (TypeError, ValueError):
            continue
        if xp < 0 or xp > 999:
            continue
        title = str(item.get("title") or "").strip() or track_id
        reason = str(item.get("reason") or "").strip() or "move grade"
        key = (candidate_id, track_id, slug)
        if key in seen:
            continue
        seen.add(key)
        level_up = item.get("level_up") is True
        levels_gained = _optional_move_grade_int(item.get("levels_gained"), lower=0, upper=999)
        if level_up and levels_gained is None:
            levels_gained = 1
        rows.append(
            {
                "candidate_id": candidate_id,
                "track_id": track_id,
                "title": title,
                "slug": slug,
                "label": label,
                "xp": xp,
                "reason": reason,
                "overdrive": bool(item.get("overdrive")),
                "streak": _optional_move_grade_int(item.get("streak"), lower=0, upper=999),
                "total_xp": _optional_move_grade_int(
                    item.get("total_xp"),
                    lower=0,
                    upper=999_999,
                ),
                "level": _optional_move_grade_int(item.get("level"), lower=1, upper=999),
                "level_xp": _optional_move_grade_int(item.get("level_xp"), lower=0, upper=999_999),
                "next_level_xp": _optional_move_grade_int(
                    item.get("next_level_xp"),
                    lower=1,
                    upper=999_999,
                ),
                "level_up": level_up,
                "levels_gained": levels_gained if level_up else 0,
            }
        )
    return rows


@dataclass(slots=True)
class CodexChatResult:
    """Outcome of one Codex chat turn (normalized to the shared ChatResult shape)."""

    reply: str = ""
    tools_used: list[str] = field(default_factory=list)
    tool_trace: list[dict[str, Any]] = field(default_factory=list)
    track_ids: list[str] = field(default_factory=list)
    move_grades: list[dict[str, Any]] = field(default_factory=list)
    live_verification: dict[str, Any] | None = None
    playlist: dict[str, Any] | None = None
    export_path: str | None = None
    stop_reason: str = "model_done"
    error: str | None = None
    question: str | None = None
    choices: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        # Match agent.ChatResult.to_dict so the Tauri bridge reads ONE shape
        # regardless of backend. tools_used → tool_trace rows; track_ids →
        # seen_track_ids. An error degrades into a spoken reply so the chat UI
        # always shows something honest.
        reply = self.reply or (self.error or "")
        tool_trace = self.tool_trace or _normalize_chat_tool_trace(None, self.tools_used)
        iterations = 0 if self.error else max(1, len(tool_trace))
        out = {
            "reply": reply,
            "tool_trace": tool_trace,
            "playlist": self.playlist,
            "export_path": self.export_path,
            "seen_track_ids": self.track_ids,
            "move_grades": self.move_grades,
            "iterations": iterations,
            "stop_reason": self.stop_reason,
        }
        if self.live_verification is not None:
            out["live_verification"] = self.live_verification
        if self.question is not None:
            out["question"] = self.question
        if self.choices is not None:
            out["choices"] = list(self.choices)
        return out


def _chat_clarification_reply(question: str | None, choices: list[str] | None) -> str:
    lines = [question or "I need one more detail before I can answer that."]
    for i, choice in enumerate(choices or [], start=1):
        lines.append(f"{i}. {choice}")
    return "\n".join(lines)


def _missing_live_context_reply() -> str:
    return "Start live monitoring first, then I'll read the live move from the decks."


def chat_with_codex(
    message: str,
    library: RekordboxLibrary,
    *,
    history: list[dict[str, Any]] | None = None,
    live_context: dict[str, Any] | None = None,
    timeout_s: float = CHAT_TIMEOUT_S,
    codex_path: str | None = None,
    mcp_command: str | None = None,
    mcp_args: list[str] | None = None,
    allow_shell: bool | None = None,
    _runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> CodexChatResult:
    """One conversational Viber turn via ``codex exec`` + the MCP grounded tools.

    Mirrors :func:`curate_with_codex` (same guards: not-installed / mcp-blocked /
    timeout / auth / parse / grounding re-validation), but the model returns a
    free-text ``reply`` plus the tools it used. ``library`` is read-only — only
    for re-validating any ``track_ids`` the reply referenced (Invariant #2 at the
    result boundary).
    """
    prompt_text: str | None = None

    def _finish(result: CodexChatResult) -> CodexChatResult:
        _record_codex_ai_message(
            surface="viber_chat",
            request=message,
            prompt=prompt_text,
            result=result,
            live_context=live_context,
        )
        return result

    if _live_context_use_mode(message) == "active_live_context" and not live_context:
        reply = _missing_live_context_reply()
        live_verification = {
            **verify_live_reply_for_viber(reply, None),
            "transport_status": "missing_live_context",
            "move_grades_allowed": False,
            "guard_applied": False,
            "guard_violations": [],
        }
        return _finish(
            CodexChatResult(
                reply=reply,
                tool_trace=[
                    {
                        "name": "live_context_required",
                        "arg": "waiting for live deck feed",
                        "ok": False,
                    }
                ],
                live_verification=live_verification,
                stop_reason="live_context_required",
            )
        )

    if allow_shell is None:
        allow_shell = os.environ.get("VIBEMIX_CODEX_ALLOW_SHELL", "").strip() not in (
            "",
            "0",
            "false",
            "no",
        )

    codex = find_codex(codex_path)
    if codex is None:
        return _finish(
            CodexChatResult(
                stop_reason="codex_not_installed",
                error=(
                    "Codex CLI not found. Install it (`npm i -g @openai/codex` or "
                    "`brew install codex`) and run `codex login`."
                ),
            )
        )
    if not allow_shell:
        return _finish(
            CodexChatResult(
                stop_reason="codex_mcp_blocked",
                error=(
                    "Codex's MCP tool calls are auto-cancelled in non-interactive "
                    "mode (upstream bug openai/codex#16685). Set "
                    "VIBEMIX_CODEX_ALLOW_SHELL=1 to use the Codex backend."
                ),
            )
        )

    command = mcp_command or sys.executable
    args = mcp_args if mcp_args is not None else ["-m", "vibemix.library.mcp_server"]

    with tempfile.TemporaryDirectory(prefix="viber-codex-chat-") as td:
        schema_path = str(Path(td) / "schema.json")
        out_path = str(Path(td) / "out.json")
        stop_reason_path = str(Path(td) / "stop_reason.json")
        # Live tool-tape side-channel. Passed to the MCP child as an ARG (see
        # build_argv mcp_args below), NOT via env: the boot-probe verified Codex
        # does not forward the parent's process env to MCP children, so the env
        # route silently no-ops. Args are part of the spawn command → always cross.
        tool_events_path = str(Path(td) / "tool_events.jsonl")
        Path(schema_path).write_text(json.dumps(_CHAT_SCHEMA), encoding="utf-8")

        prompt_text = chat_prompt(message, history, live_context=live_context)
        argv = build_argv(
            codex,
            mcp_command=command,
            mcp_args=[*args, "--vibemix-tool-events", tool_events_path],
            schema_path=schema_path,
            out_path=out_path,
            prompt=prompt_text,
            bypass_sandbox=allow_shell,
        )

        env = build_subprocess_env(codex)
        env["VIBEMIX_STOP_REASON_FILE"] = stop_reason_path
        # LIVE TOOL TAPE: the MCP child (LibraryToolset.dispatch) appends one
        # JSON record per tool call to this path; a daemon tailer echoes each to
        # STDERR as `[viber-tool] …` while the (blocking) Codex subprocess runs,
        # so the user watches Viber work instead of a frozen prompt. STDERR keeps
        # the stdout result-JSON channel pristine; the Rust layer tails these
        # `[viber-tool]` lines for the in-app tape.
        env["VIBEMIX_TOOL_EVENTS_FILE"] = tool_events_path
        _tape_stop = _start_tool_tape(tool_events_path)

        try:
            proc = _runner(
                argv,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                env=env,
                stdin=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            return _finish(
                CodexChatResult(
                    stop_reason="codex_not_installed",
                    error="Codex CLI disappeared at spawn time.",
                )
            )
        except subprocess.TimeoutExpired:
            return _finish(
                CodexChatResult(
                    stop_reason="timeout",
                    error=f"Codex did not finish within {timeout_s:.0f}s.",
                )
            )
        finally:
            _tape_stop()

        stderr = proc.stderr or ""
        if proc.returncode != 0:
            low = stderr.lower()
            if any(h in low for h in _AUTH_HINTS):
                return _finish(
                    CodexChatResult(
                        stop_reason="codex_auth_required",
                        error="Codex is not logged in. Run `codex login`.",
                    )
                )
            return _finish(
                CodexChatResult(
                    stop_reason="error",
                    error=f"codex exec failed (exit {proc.returncode}): {stderr.strip()[:400]}",
                )
            )

        if Path(stop_reason_path).exists():
            try:
                stop_payload = json.loads(Path(stop_reason_path).read_text(encoding="utf-8"))
                if (
                    isinstance(stop_payload, dict)
                    and stop_payload.get("reason") == "tool_starvation"
                ):
                    return _finish(
                        CodexChatResult(
                            stop_reason="tool_starvation",
                            error=str(
                                stop_payload.get("hint")
                                or "Viber stopped after repeated empty tool results."
                            ),
                        )
                    )
                if (
                    isinstance(stop_payload, dict)
                    and stop_payload.get("reason") == "clarification_needed"
                ):
                    raw_question = stop_payload.get("question")
                    raw_choices = stop_payload.get("choices")
                    question = raw_question if isinstance(raw_question, str) else None
                    choices = (
                        [str(choice) for choice in raw_choices]
                        if isinstance(raw_choices, list)
                        else None
                    )
                    return _finish(
                        CodexChatResult(
                            reply=_chat_clarification_reply(question, choices),
                            tools_used=["request_clarification"],
                            tool_trace=[
                                {
                                    "name": "request_clarification",
                                    "arg": question or "clarification",
                                    "ok": True,
                                }
                            ],
                            stop_reason="clarification_needed",
                            question=question,
                            choices=choices,
                        )
                    )
            except (OSError, json.JSONDecodeError):
                pass

        try:
            raw = Path(out_path).read_text(encoding="utf-8").strip()
        except OSError:
            raw = ""
        if not raw:
            return _finish(
                CodexChatResult(stop_reason="empty_output", error="Codex produced no output.")
            )
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return _finish(
                CodexChatResult(
                    stop_reason="empty_output", error="Codex output was not valid JSON."
                )
            )
        if not isinstance(payload, dict):
            return _finish(
                CodexChatResult(stop_reason="empty_output", error="Codex output was not an object.")
            )
        actual_tool_trace = _read_tool_event_trace(tool_events_path)

    raw_reply = str(payload.get("reply", "")).strip()
    tools_used = [t for t in (payload.get("tools_used") or []) if isinstance(t, str)]
    tool_trace = actual_tool_trace or _normalize_chat_tool_trace(
        payload.get("tool_trace"), tools_used
    )
    if not tools_used:
        tools_used = [str(row["name"]) for row in tool_trace]
    raw_ids = [t for t in (payload.get("track_ids") or []) if isinstance(t, str)]
    move_grades = _normalize_chat_move_grades(payload.get("move_grades"), library)
    if not _live_context_allows_move_grades(live_context):
        move_grades = []
    raw_ids.extend(row["track_id"] for row in move_grades if isinstance(row.get("track_id"), str))
    playlist = _normalize_chat_playlist(payload.get("playlist"), library)
    if playlist is not None:
        raw_ids.extend(playlist["track_ids"])
    # Grounding at the result boundary: keep only ids that resolve in the library.
    track_ids = _validate_against_library(_dedupe_ordered(raw_ids), library)

    live_context_mode = _live_context_use_mode(message) if live_context else "none"
    library_context_request = _is_library_context_request(message)
    library_live_leak = bool(
        live_context
        and live_context_mode != "active_live_context"
        and library_context_request
        and _looks_like_library_request_live_leak(raw_reply)
    )
    guarded_reply = _apply_live_claim_guard(raw_reply, live_context) if live_context else raw_reply
    if live_context_mode == "active_live_context":
        reply = guarded_reply
    elif live_context and (
        library_live_leak
        or _looks_like_unprompted_live_correction(raw_reply)
        or guarded_reply != raw_reply
    ):
        if (
            playlist is not None
            or track_ids
            or tools_used
            or tool_trace
            or library_context_request
        ):
            reply = _library_request_fallback_reply(
                playlist=playlist,
                track_ids=track_ids,
                tools_used=tools_used,
                tool_trace=tool_trace,
            )
        else:
            reply = guarded_reply
    else:
        reply = raw_reply

    live_verification = None
    if live_context:
        live_verification = verify_live_reply_for_viber(
            reply,
            live_context,
            move_grades=move_grades,
        )
        if raw_reply != reply:
            raw_verification = verify_live_reply_for_viber(
                raw_reply,
                live_context,
                move_grades=move_grades,
            )
            guard_violations = list(raw_verification.get("violations", []))
            if library_live_leak and "library_request_live_leak" not in guard_violations:
                guard_violations.append("library_request_live_leak")
            live_verification = {
                **live_verification,
                "guard_applied": True,
                "guard_violations": guard_violations,
            }
        else:
            live_verification = {
                **live_verification,
                "guard_applied": False,
                "guard_violations": [],
            }

    export_path = None
    raw_export_path = payload.get("export_path")
    if isinstance(raw_export_path, str) and raw_export_path.strip():
        candidate = raw_export_path.strip()
        if Path(candidate).exists():
            export_path = candidate

    if not reply and not tools_used:
        return _finish(
            CodexChatResult(stop_reason="empty_output", error="Codex returned an empty reply.")
        )
    stop_reason = "exported" if export_path else "created" if playlist else "model_done"
    return _finish(
        CodexChatResult(
            reply=reply,
            tools_used=tools_used,
            tool_trace=tool_trace,
            track_ids=track_ids,
            move_grades=move_grades,
            live_verification=live_verification,
            playlist=playlist,
            export_path=export_path,
            stop_reason=stop_reason,
        )
    )


__all__ = [
    "BUILD_SET_TIMEOUT_S",
    "CHAT_TIMEOUT_S",
    "DEFAULT_TIMEOUT_S",
    "CodexChatResult",
    "CodexCurateResult",
    "build_argv",
    "build_prompt",
    "build_set_prompt",
    "build_set_with_codex",
    "build_subprocess_env",
    "chat_prompt",
    "chat_with_codex",
    "curate_with_codex",
    "find_codex",
    "normalize_live_audio_window_map_for_viber",
    "normalize_live_context_for_viber",
    "normalize_live_source_status_for_viber",
    "render_live_context_preview",
    "verify_live_reply_for_viber",
]
