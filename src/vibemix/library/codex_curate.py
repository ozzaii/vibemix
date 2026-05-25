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
import shutil
import subprocess
import sys
import tempfile
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

_SYSTEM_PROMPT = (
    "You are Viber, a DJ's crate-digging co-pilot. Build a playlist from the "
    "user's OWN library that fits the theme below, using ONLY the provided "
    "tools.\n"
    "RULES (non-negotiable):\n"
    "1. You may ONLY put a track in a playlist if a prior search_vibe call "
    "returned its track_id in THIS run. Never invent a track_id, title, "
    "artist, BPM, or key. Call search_vibe to find candidates.\n"
    "2. Keys/BPM come from get_track_features (deterministic) — never compute "
    "or guess them.\n"
    "3. When you have chosen the tracks, call create_playlist exactly once "
    "with the ordered track_ids. That ends the run.\n"
    "4. Keep it tight — a focused set beats a padded one.\n"
    "Return a final JSON object: {name, track_ids, rationale}."
)

# JSON Schema enforced on Codex's final message (--output-schema).
_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "track_ids": {"type": "array", "items": {"type": "string"}},
        "rationale": {"type": "string"},
        "m3u_path": {"type": "string"},
        "json_path": {"type": "string"},
    },
    "required": ["name", "track_ids"],
    "additionalProperties": True,
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
    return f"{_SYSTEM_PROMPT}\n\nTheme: {theme.strip()}"


def build_argv(
    codex_path: str,
    *,
    mcp_command: str,
    mcp_args: list[str],
    schema_path: str,
    out_path: str,
    prompt: str,
) -> list[str]:
    """Build the ``codex exec`` argv.

    MCP-server config is injected via ``-c`` overrides (TOML/JSON values) so we
    never touch the user's global ``~/.codex/config.toml``. Auth still comes
    from the default ``~/.codex`` (the user's own ``codex login``); only the
    server wiring is overridden per-invocation.
    """
    server = "mcp_servers.vibemix_library"
    return [
        codex_path,
        "exec",
        "--sandbox",
        "read-only",  # tools do the writing, not the shell
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
        f'{server}.default_tools_approval_mode="auto"',  # headless: no prompts
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
    _runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> CodexCurateResult:
    """Run one curation via ``codex exec`` against the MCP server.

    ``_runner`` is injectable so tests exercise every guard branch without
    Codex installed. ``library`` is used only for the result-boundary
    grounding re-validation (read-only).
    """
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
        )

        try:
            proc = _runner(
                argv,
                capture_output=True,
                text=True,
                timeout=timeout_s,
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

    m3u = payload.get("m3u_path")
    jsn = payload.get("json_path")
    return CodexCurateResult(
        theme=theme,
        stop_reason="created",
        playlist_name=name or str(payload.get("name") or theme),
        track_ids=validated,
        m3u_path=m3u if (isinstance(m3u, str) and Path(m3u).exists()) else None,
        json_path=jsn if (isinstance(jsn, str) and Path(jsn).exists()) else None,
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
