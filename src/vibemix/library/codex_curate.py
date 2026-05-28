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
import shutil
import subprocess
import sys
import tempfile
import threading
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from vibemix.library.rekordbox import RekordboxLibrary

logger = logging.getLogger(__name__)

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
                "codex shell access. Set VIBEMIX_CODEX_ALLOW_SHELL=1 for the "
                "current local Codex path."
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
        # Plan 99-04: side-channel file the MCP-side LibraryToolset writes on
        # threshold-trip. Allocated INSIDE the TemporaryDirectory `with` block
        # (Pitfall 4): the temp dir is cleaned up at `with` exit, so the read
        # MUST happen before this block ends or the file disappears.
        stop_reason_path = str(Path(td) / "stop_reason.json")
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

        # Plan 99-04: inject the side-channel path on the subprocess env arg
        # (NOT os.environ — test isolation, the wrapper never mutates the
        # parent process's env). Codex CLI passes env to its MCP children;
        # build_toolset() in mcp_server logs presence/absence at boot
        # (Plan 99-04 Task 5, B1 Option A probe).
        env = build_subprocess_env(codex)
        env["VIBEMIX_STOP_REASON_FILE"] = stop_reason_path

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

        stderr = proc.stderr or ""
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
                payload = json.loads(
                    Path(stop_reason_path).read_text(encoding="utf-8")
                )
                if (
                    isinstance(payload, dict)
                    and payload.get("reason") == "tool_starvation"
                ):
                    return CodexCurateResult(
                        theme=theme,
                        stop_reason="tool_starvation",
                        error=str(
                            payload.get("hint")
                            or "no playlist — tool starvation, no hint available"
                        ),
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
                if (
                    isinstance(payload, dict)
                    and payload.get("reason") == "clarification_needed"
                ):
                    q = payload.get("question")
                    cs = payload.get("choices")
                    return CodexCurateResult(
                        theme=theme,
                        stop_reason="clarification_needed",
                        question=str(q) if isinstance(q, str) else None,
                        choices=(
                            [str(c) for c in cs] if isinstance(cs, list) else None
                        ),
                    )
            except (OSError, json.JSONDecodeError):
                pass  # fall through to existing parse logic

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
    except Exception as e:
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
    "Pass ONLY track_ids returned by discover_pool this run.\n"
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
            theme=brief,
            stop_reason="codex_not_installed",
            error=(
                "Codex CLI not found. Install it (`npm i -g @openai/codex` or "
                "`brew install codex`) and run `codex login` to enable AI sets."
            ),
        )

    if not allow_shell:
        return CodexCurateResult(
            theme=brief,
            stop_reason="codex_mcp_blocked",
            error=(
                "Codex's MCP tool calls are auto-cancelled in non-interactive "
                "mode (upstream bug openai/codex#16685). Running them needs "
                "`--dangerously-bypass-approvals-and-sandbox`. To use the Codex "
                "backend, set VIBEMIX_CODEX_ALLOW_SHELL=1."
            ),
        )

    command = mcp_command or sys.executable
    args = mcp_args if mcp_args is not None else ["-m", "vibemix.library.mcp_server"]

    with tempfile.TemporaryDirectory(prefix="viber-codex-set-") as td:
        schema_path = str(Path(td) / "schema.json")
        out_path = str(Path(td) / "out.json")
        # Plan 99-04: parallel propagation for set-prep. Same Pitfall-4
        # discipline as curate_with_codex — read INSIDE the `with` block.
        stop_reason_path = str(Path(td) / "stop_reason.json")
        Path(schema_path).write_text(json.dumps(_BUILD_SET_SCHEMA), encoding="utf-8")

        argv = build_argv(
            codex,
            mcp_command=command,
            mcp_args=args,
            schema_path=schema_path,
            out_path=out_path,
            prompt=build_set_prompt(
                brief,
                curve=curve,
                name=name,
                n_slots=n_slots,
                export=export,
            ),
            bypass_sandbox=allow_shell,
        )

        # Plan 99-04: inject side-channel path on subprocess env (uniform
        # with curate_with_codex; see that wrapper's comment for the test-
        # isolation rationale).
        env = build_subprocess_env(codex)
        env["VIBEMIX_STOP_REASON_FILE"] = stop_reason_path

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
            return CodexCurateResult(
                theme=brief,
                stop_reason="codex_not_installed",
                error="Codex CLI disappeared at spawn time.",
            )
        except subprocess.TimeoutExpired:
            return CodexCurateResult(
                theme=brief,
                stop_reason="timeout",
                error=f"Codex did not finish within {timeout_s:.0f}s.",
            )

        stderr = proc.stderr or ""
        if proc.returncode != 0:
            low = stderr.lower()
            if any(h in low for h in _AUTH_HINTS):
                return CodexCurateResult(
                    theme=brief,
                    stop_reason="codex_auth_required",
                    error="Codex is not logged in. Run `codex login`.",
                )
            return CodexCurateResult(
                theme=brief,
                stop_reason="error",
                error=f"codex exec failed (exit {proc.returncode}): {stderr.strip()[:400]}",
            )

        # Plan 99-04: Channel A side-channel SHORT-CIRCUIT (parallel of
        # curate_with_codex). Phase 100 forward-compat: branch on
        # ``payload.get("reason") == "tool_starvation"`` so the sibling
        # ``clarification_needed`` extension lands cleanly. Fallback string
        # is structurally UNREACHABLE in production (Plan 99-03's
        # _build_starvation_payload always seeds 'hint').
        if Path(stop_reason_path).exists():
            try:
                payload = json.loads(
                    Path(stop_reason_path).read_text(encoding="utf-8")
                )
                if (
                    isinstance(payload, dict)
                    and payload.get("reason") == "tool_starvation"
                ):
                    return CodexCurateResult(
                        theme=brief,
                        stop_reason="tool_starvation",
                        error=str(
                            payload.get("hint")
                            or "no playlist — tool starvation, no hint available"
                        ),
                    )
                # Plan 100-03: parallel of the curate_with_codex sibling
                # branch. Uniform propagation across both wrappers — the
                # set-prep code path also surfaces clarification_needed via
                # the same dataclass shape (theme=brief substitution).
                if (
                    isinstance(payload, dict)
                    and payload.get("reason") == "clarification_needed"
                ):
                    q = payload.get("question")
                    cs = payload.get("choices")
                    return CodexCurateResult(
                        theme=brief,
                        stop_reason="clarification_needed",
                        question=str(q) if isinstance(q, str) else None,
                        choices=(
                            [str(c) for c in cs] if isinstance(cs, list) else None
                        ),
                    )
            except (OSError, json.JSONDecodeError):
                pass  # fall through to existing parse logic

        try:
            raw = Path(out_path).read_text(encoding="utf-8").strip()
        except OSError:
            raw = ""
        if not raw:
            return CodexCurateResult(
                theme=brief, stop_reason="empty_output", error="Codex produced no output."
            )
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return CodexCurateResult(
                theme=brief,
                stop_reason="empty_output",
                error="Codex output was not valid JSON.",
            )
        if not isinstance(payload, dict):
            return CodexCurateResult(
                theme=brief,
                stop_reason="empty_output",
                error="Codex output was not a JSON object.",
            )

    raw_ids = payload.get("track_ids")
    if not isinstance(raw_ids, list) or not raw_ids:
        return CodexCurateResult(
            theme=brief,
            stop_reason="no_playlist",
            rationale=str(payload.get("rationale", "")),
            error="Codex returned no track_ids.",
        )

    validated = _validate_against_library(raw_ids, library)
    if not validated:
        return CodexCurateResult(
            theme=brief,
            stop_reason="no_playlist",
            rationale=str(payload.get("rationale", "")),
            error="No returned track_id resolved in the library (grounding).",
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

    return CodexCurateResult(
        theme=brief,
        stop_reason="exported" if export_path is not None else "created",
        playlist_name=playlist_name,
        track_ids=validated,
        m3u_path=m3u_path,
        json_path=json_path,
        rationale=str(payload.get("rationale", "")),
        export_path=export_path,
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
    "track_ids, playlist, export_path}: reply is your spoken answer to the DJ; "
    "tools_used lists the tool names you called this turn. tool_trace lists the "
    "same calls as {name, arg, ok}, where arg is the shortest useful argument "
    "or intent the DJ should see and ok is false only if the tool failed. "
    "track_ids is any library track you referenced (in order, empty if none). "
    "If you call create_playlist, "
    "copy its returned {name, track_ids, m3u_path, json_path, dropped_ids} into "
    "playlist; otherwise playlist=null. If you call export_set, copy its "
    "returned path into export_path; otherwise export_path=null."
)


def _chat_system_prompt() -> str:
    """Codex chat system prompt — shared curator voice + chat rules + taste."""
    from vibemix.prompts.matrix import build_curator_instruction

    return build_curator_instruction(_shared_lens()) + "\n" + _CHAT_RULES_BLOCK + _taste_hint()


def chat_prompt(message: str, history: list[dict[str, Any]] | None = None) -> str:
    """Render the chat system prompt + the conversation so far + the new turn."""
    convo = ""
    for turn in history or []:
        if not isinstance(turn, dict):
            continue
        text = str(turn.get("text") or "").strip()
        if not text:
            continue
        speaker = "Viber" if turn.get("role") == "viber" else "DJ"
        convo += f"{speaker}: {text}\n"
    convo += f"DJ: {message.strip()}"
    return (
        f"{_chat_system_prompt()}\n\nConversation so far:\n{convo}\n\n"
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


@dataclass(slots=True)
class CodexChatResult:
    """Outcome of one Codex chat turn (normalized to the shared ChatResult shape)."""

    reply: str = ""
    tools_used: list[str] = field(default_factory=list)
    tool_trace: list[dict[str, Any]] = field(default_factory=list)
    track_ids: list[str] = field(default_factory=list)
    playlist: dict[str, Any] | None = None
    export_path: str | None = None
    stop_reason: str = "model_done"
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        # Match agent.ChatResult.to_dict so the Tauri bridge reads ONE shape
        # regardless of backend. tools_used → tool_trace rows; track_ids →
        # seen_track_ids. An error degrades into a spoken reply so the chat UI
        # always shows something honest.
        reply = self.reply or (self.error or "")
        tool_trace = self.tool_trace or _normalize_chat_tool_trace(None, self.tools_used)
        iterations = 0 if self.error else max(1, len(tool_trace))
        return {
            "reply": reply,
            "tool_trace": tool_trace,
            "playlist": self.playlist,
            "export_path": self.export_path,
            "seen_track_ids": self.track_ids,
            "iterations": iterations,
            "stop_reason": self.stop_reason,
        }


def chat_with_codex(
    message: str,
    library: RekordboxLibrary,
    *,
    history: list[dict[str, Any]] | None = None,
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
    if allow_shell is None:
        allow_shell = os.environ.get("VIBEMIX_CODEX_ALLOW_SHELL", "").strip() not in (
            "",
            "0",
            "false",
            "no",
        )

    codex = find_codex(codex_path)
    if codex is None:
        return CodexChatResult(
            stop_reason="codex_not_installed",
            error=(
                "Codex CLI not found. Install it (`npm i -g @openai/codex` or "
                "`brew install codex`) and run `codex login`."
            ),
        )
    if not allow_shell:
        return CodexChatResult(
            stop_reason="codex_mcp_blocked",
            error=(
                "Codex's MCP tool calls are auto-cancelled in non-interactive "
                "mode (upstream bug openai/codex#16685). Set "
                "VIBEMIX_CODEX_ALLOW_SHELL=1 to use the Codex backend."
            ),
        )

    command = mcp_command or sys.executable
    args = mcp_args if mcp_args is not None else ["-m", "vibemix.library.mcp_server"]

    with tempfile.TemporaryDirectory(prefix="viber-codex-chat-") as td:
        schema_path = str(Path(td) / "schema.json")
        out_path = str(Path(td) / "out.json")
        Path(schema_path).write_text(json.dumps(_CHAT_SCHEMA), encoding="utf-8")

        argv = build_argv(
            codex,
            mcp_command=command,
            mcp_args=args,
            schema_path=schema_path,
            out_path=out_path,
            prompt=chat_prompt(message, history),
            bypass_sandbox=allow_shell,
        )

        try:
            proc = _runner(
                argv,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                env=build_subprocess_env(codex),
                stdin=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            return CodexChatResult(
                stop_reason="codex_not_installed",
                error="Codex CLI disappeared at spawn time.",
            )
        except subprocess.TimeoutExpired:
            return CodexChatResult(
                stop_reason="timeout",
                error=f"Codex did not finish within {timeout_s:.0f}s.",
            )

        stderr = proc.stderr or ""
        if proc.returncode != 0:
            low = stderr.lower()
            if any(h in low for h in _AUTH_HINTS):
                return CodexChatResult(
                    stop_reason="codex_auth_required",
                    error="Codex is not logged in. Run `codex login`.",
                )
            return CodexChatResult(
                stop_reason="error",
                error=f"codex exec failed (exit {proc.returncode}): {stderr.strip()[:400]}",
            )

        try:
            raw = Path(out_path).read_text(encoding="utf-8").strip()
        except OSError:
            raw = ""
        if not raw:
            return CodexChatResult(stop_reason="empty_output", error="Codex produced no output.")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return CodexChatResult(
                stop_reason="empty_output", error="Codex output was not valid JSON."
            )
        if not isinstance(payload, dict):
            return CodexChatResult(
                stop_reason="empty_output", error="Codex output was not an object."
            )

    reply = str(payload.get("reply", "")).strip()
    tools_used = [t for t in (payload.get("tools_used") or []) if isinstance(t, str)]
    tool_trace = _normalize_chat_tool_trace(payload.get("tool_trace"), tools_used)
    if not tools_used:
        tools_used = [str(row["name"]) for row in tool_trace]
    raw_ids = [t for t in (payload.get("track_ids") or []) if isinstance(t, str)]
    playlist = _normalize_chat_playlist(payload.get("playlist"), library)
    if playlist is not None:
        raw_ids.extend(playlist["track_ids"])
    # Grounding at the result boundary: keep only ids that resolve in the library.
    track_ids = _validate_against_library(_dedupe_ordered(raw_ids), library)

    export_path = None
    raw_export_path = payload.get("export_path")
    if isinstance(raw_export_path, str) and raw_export_path.strip():
        candidate = raw_export_path.strip()
        if Path(candidate).exists():
            export_path = candidate

    if not reply and not tools_used:
        return CodexChatResult(stop_reason="empty_output", error="Codex returned an empty reply.")
    stop_reason = "exported" if export_path else "created" if playlist else "model_done"
    return CodexChatResult(
        reply=reply,
        tools_used=tools_used,
        tool_trace=tool_trace,
        track_ids=track_ids,
        playlist=playlist,
        export_path=export_path,
        stop_reason=stop_reason,
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
]
