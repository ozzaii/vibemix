# SPDX-License-Identifier: Apache-2.0
"""Codex curate backend — spawn ``codex exec`` against the vibemix MCP server.

The Hermes pattern, native CLI: Codex (``provider: openai-codex``, the owner's
flat-rate ChatGPT subscription) is the bounded reasoning harness; vibemix's
:mod:`vibemix.library.mcp_server` exposes the 3 grounded tools over STDIO.
Codex's own harness owns the agentic loop, per-tool timeouts, and sandboxing
(see ``.planning/research/viber-direction-2026-05-25/codex-agent-design.md`` §5).

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

import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

from vibemix.library.rekordbox import RekordboxLibrary

logger = logging.getLogger(__name__)

# Outer wall-clock guard. Codex bounds tool calls (tool_timeout_sec) and its
# own loop; this is the belt-and-braces kill for a wedged process.
DEFAULT_TIMEOUT_S = 120.0
# MCP tool/startup timeouts handed to Codex via -c overrides (its harness owns
# enforcement; we only set the values).
_MCP_STARTUP_TIMEOUT_S = 15
_MCP_TOOL_TIMEOUT_S = 30

# Substrings in Codex stderr that mean "not authenticated" rather than a
# genuine runtime error — used to surface the actionable `codex login` hint.
_AUTH_HINTS = ("login", "log in", "auth", "sign in", "not authenticated", "401")

# WIRE-04 (Phase 77 Plan 02): persona opener sourced from the shared matrix
# seam (build_curator_instruction) — the same voice the gemini backend and the
# live co-host speak. The "Use ONLY the provided tools" bridge is codex-specific
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
# gemini agent seam; uncontended on the steady-state cache hit.
_CACHE_LOCK = threading.Lock()


def _shared_lens() -> str:
    """Read the ONE shared lens (LENS-02), defaulting to ``"tutor"`` when unset.

    Same per-surface default-when-unset as the gemini curator seam — the codex
    backend reads the SAME ``ConfigStore.extra["lens"]`` selection, so choosing a
    lens once drives every curator backend AND the live co-host. Lazy-imported to
    keep the import-time no-live-path boundary clean.

    WR-03: guarded read (mirrors the gemini curator seam + the co-host
    ``_resolve_prompt_cell`` guard). Any read failure falls back to ``"tutor"``
    so a malformed ``extra`` can never break curation.
    """
    try:
        from vibemix.runtime.config_store import load_config
        from vibemix.runtime.settings import read_shared_lens

        return read_shared_lens(load_config(), default="tutor") or "tutor"
    except Exception:  # pragma: no cover — guard: any read fail = cold default
        return "tutor"


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
        return _SYSTEM_PROMPT_CACHE


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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# created            — a grounded playlist came back
# codex_not_installed — no `codex` binary on PATH
# codex_auth_required — codex ran but is not logged in
# timeout            — outer wall-clock kill
# empty_output       — codex produced nothing parseable
# no_playlist        — output had no track_ids surviving library validation
# error              — any other non-zero exit / failure


def find_codex(codex_path: str | None = None) -> str | None:
    """Locate the ``codex`` binary, honoring an explicit override."""
    if codex_path:
        return codex_path if Path(codex_path).exists() else None
    return shutil.which("codex")


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
        f'{server}.command={json.dumps(mcp_command)}',
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


def _validate_against_library(
    track_ids: list[str], library: RekordboxLibrary
) -> list[str]:
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
    if allow_shell is None:
        allow_shell = os.environ.get("VIBEMIX_CODEX_ALLOW_SHELL", "").strip() not in (
            "",
            "0",
            "false",
            "no",
        )

    codex = find_codex(codex_path)
    if codex is None:
        return CodexCurateResult(
            theme=theme,
            stop_reason="codex_not_installed",
            error=(
                "Codex CLI not found. Install it (`npm i -g @openai/codex` or "
                "`brew install codex`) and run `codex login` to enable AI "
                "playlists."
            ),
        )

    # Upstream regression gate: without the bypass, codex exec auto-cancels
    # every MCP tool call (openai/codex#16685) → curation can't run. Rather than
    # fail cryptically, surface the honest choice up-front. The user opts into
    # the bypass (which grants codex shell access) consciously.
    if not allow_shell:
        return CodexCurateResult(
            theme=theme,
            stop_reason="codex_mcp_blocked",
            error=(
                "Codex's MCP tool calls are auto-cancelled in non-interactive "
                "mode (upstream bug openai/codex#16685). Running them needs "
                "`--dangerously-bypass-approvals-and-sandbox`, which also grants "
                "codex shell access. To use the Codex backend anyway, set "
                "VIBEMIX_CODEX_ALLOW_SHELL=1. Otherwise use the default Gemini "
                "backend (no bypass needed): `library curate \"<theme>\"`."
            ),
        )

    # The MCP server is launched by Codex as a STDIO child: this interpreter
    # running `-m vibemix.library.mcp_server`. Absolute interpreter path so it
    # works regardless of Codex's cwd / PATH.
    command = mcp_command or sys.executable
    args = mcp_args if mcp_args is not None else ["-m", "vibemix.library.mcp_server"]

    with tempfile.TemporaryDirectory(prefix="viber-codex-") as td:
        schema_path = str(Path(td) / "schema.json")
        out_path = str(Path(td) / "out.json")
        Path(schema_path).write_text(json.dumps(_OUTPUT_SCHEMA), encoding="utf-8")

        argv = build_argv(
            codex,
            mcp_command=command,
            mcp_args=args,
            schema_path=schema_path,
            out_path=out_path,
            prompt=build_prompt(theme),
            bypass_sandbox=allow_shell,
        )

        try:
            proc = _runner(
                argv,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                # `codex exec` reads extra instructions from stdin when it's
                # piped/inherited; a non-TTY child stdin makes it block/err with
                # "Reading additional input from stdin...". DEVNULL = the prompt
                # is the positional arg, full stop.
                stdin=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            # Race: binary vanished between which() and spawn.
            return CodexCurateResult(
                theme=theme,
                stop_reason="codex_not_installed",
                error="Codex CLI disappeared at spawn time.",
            )
        except subprocess.TimeoutExpired:
            return CodexCurateResult(
                theme=theme,
                stop_reason="timeout",
                error=f"Codex did not finish within {timeout_s:.0f}s.",
            )

        stderr = (proc.stderr or "")
        if proc.returncode != 0:
            low = stderr.lower()
            if any(h in low for h in _AUTH_HINTS):
                return CodexCurateResult(
                    theme=theme,
                    stop_reason="codex_auth_required",
                    error="Codex is not logged in. Run `codex login`.",
                )
            return CodexCurateResult(
                theme=theme,
                stop_reason="error",
                error=f"codex exec failed (exit {proc.returncode}): {stderr.strip()[:400]}",
            )

        # Parse the schema-enforced final message.
        try:
            raw = Path(out_path).read_text(encoding="utf-8").strip()
        except OSError:
            raw = ""
        if not raw:
            return CodexCurateResult(
                theme=theme,
                stop_reason="empty_output",
                error="Codex produced no output.",
            )
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return CodexCurateResult(
                theme=theme,
                stop_reason="empty_output",
                error="Codex output was not valid JSON.",
            )
        # --output-schema enforces an object, but never trust it on faith — a
        # bare array/scalar would AttributeError on .get() below (and that line
        # is outside the try, so it would escape "never raises").
        if not isinstance(payload, dict):
            return CodexCurateResult(
                theme=theme,
                stop_reason="empty_output",
                error="Codex output was not a JSON object.",
            )

    raw_ids = payload.get("track_ids")
    if not isinstance(raw_ids, list) or not raw_ids:
        return CodexCurateResult(
            theme=theme,
            stop_reason="no_playlist",
            rationale=str(payload.get("rationale", "")),
            error="Codex returned no track_ids.",
        )

    # GROUNDING re-validation at the result boundary.
    validated = _validate_against_library(raw_ids, library)
    if not validated:
        return CodexCurateResult(
            theme=theme,
            stop_reason="no_playlist",
            rationale=str(payload.get("rationale", "")),
            error="No returned track_id resolved in the library (grounding).",
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
    except Exception as e:  # noqa: BLE001 — never raise; report what we have
        logger.warning("[codex] persist failed: %s", e)

    return CodexCurateResult(
        theme=theme,
        stop_reason="created",
        playlist_name=playlist_name,
        track_ids=validated,
        m3u_path=m3u_path,
        json_path=json_path,
        rationale=str(payload.get("rationale", "")),
    )


__all__ = [
    "DEFAULT_TIMEOUT_S",
    "CodexCurateResult",
    "build_argv",
    "build_prompt",
    "curate_with_codex",
    "find_codex",
]
