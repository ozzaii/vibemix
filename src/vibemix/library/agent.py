# SPDX-License-Identifier: Apache-2.0
"""Viber Agent — Phase 1: bounded Gemini function-calling playlist curator.

A per-user, single-shot agent that turns a natural-language theme into a
playlist drawn from the user's OWN library. It plans in a few Gemini-Flash
turns, calls a small fixed tool surface (``search_vibe`` /
``get_track_features`` / ``create_playlist``), and emits a playlist of REAL
track IDs that the tools returned — never IDs it invented.

Design contract (see ``/tmp/audit/agent-harness-design.md`` §6 Phase 1):

* **Grounding (Cardinal Invariant #2).** A per-run "seen-set" records every
  ``track_id`` a ``search_vibe`` call returned in THIS run. ``create_playlist``
  rejects any id NOT in the seen-set, then re-validates each surviving id
  against the live library. The agent can never smuggle in a hallucinated
  track. Key/Camelot is deterministic (``state.harmonics.to_camelot``), never
  LLM-computed.
* **No-hang.** The dispatch loop is bounded (``MAX_TOOL_ITERATIONS``); every
  Gemini call and every tool handler runs under a hard timeout. Tool handlers
  RETURN error strings — they never raise — so a bad arg degrades to a
  message the model can recover from instead of wedging the loop. On
  max-iters the loop exits cleanly with whatever playlist was built.
* **No new dep / no framework.** Pure ``google-genai``
  ``client.models.generate_content(..., tools=[...])`` + manual dispatch,
  mirroring the ``generate_content`` style already in ``debrief/drills.py``.
  The model id is resolved through ``model_router`` — zero hardcoded literals.
"""

from __future__ import annotations

import concurrent.futures
import logging
from dataclasses import dataclass, field
from typing import Any, Callable

from google.genai import types

from vibemix.library.create_playlist import PlaylistResult
from vibemix.library.embed import LibraryEmbedder
from vibemix.library.rekordbox import RekordboxLibrary
from vibemix.library.store import LibraryStore
from vibemix.library.toolset import LibraryToolset
from vibemix.llm import model_router

logger = logging.getLogger(__name__)

# Bounds (anti-hang). 12 iterations is generous for a 2-3 turn curation —
# search → (optional feature peeks) → create_playlist — yet hard-caps a model
# that loops. One create_playlist per run is enforced by exiting on the first.
MAX_TOOL_ITERATIONS = 12
# Interactive mode needs more turns (1-3 ask_user rounds + searches + create),
# so it gets a higher cap — still hard-bounded so a chatty model can't loop.
MAX_INTERACTIVE_ITERATIONS = 24
# Hard wall-clock per Gemini call. A hung network can never park the loop.
# (Per-tool timeout lives in LibraryToolset.dispatch.)
GEMINI_CALL_TIMEOUT_S = 60.0

# WIRE-04 (Phase 77 Plan 02): the persona opener is sourced from the shared
# matrix seam (build_curator_instruction) instead of a hardcoded literal — the
# co-host's matrix vocabulary is now the single source of truth for voice. The
# grounding RULES below are PRESERVED VERBATIM (the seen-set / never-invent-id
# contract is the anti-slop invariant #2 and must never drift on a voice swap).
#
# The seam lives in ``vibemix.prompts.matrix`` and is imported LAZILY (inside
# the builder) — not at module top-level — so importing the curator does NOT
# drag ``vibemix.prompts`` into ``sys.modules``. This keeps the memory storage
# spine's no-live-path import boundary intact (tests/memory/
# test_no_live_path_import.py: ``vibemix.prompts`` is a forbidden surface).
# The constants are exposed via PEP 562 ``__getattr__`` (mirroring
# ``state/__init__``) so attribute access stays a plain string for callers/tests.
_RULES_BLOCK = (
    "RULES (non-negotiable):\n"
    "1. You may ONLY put a track in a playlist if a prior search_vibe call "
    "returned its track_id in THIS conversation. Never invent a track_id, a "
    "title, an artist, a BPM, or a key. If you need candidates, call "
    "search_vibe.\n"
    "2. Keys/BPM come from get_track_features (deterministic) — never compute "
    "or guess them yourself.\n"
    "3. When you have chosen the tracks, call create_playlist exactly once "
    "with the ordered track_ids. That ends the run.\n"
    "4. Keep it tight — a focused set beats a padded one."
)

_INTERACTIVE_FLOW_BLOCK = (
    "FLOW:\n"
    "1. Open by asking 1-3 SHORT clarifying questions with ask_user (e.g. the "
    "mood/occasion, how long the set is, the energy arc). Ask ONE at a time. "
    "Don't over-interrogate — 3 questions max, then build.\n"
    "2. search_vibe their library for the vibe you heard (the ONLY way to find "
    "tracks). Every track_id you use MUST come from a search_vibe result — "
    "never invent a track, title, artist, BPM, or key.\n"
    "3. Keys/BPM come from get_track_features (deterministic) — never guess.\n"
    "4. Call create_playlist ONCE with the ordered track_ids. That ends the "
    "run. Keep it tight — a focused set beats a padded one."
)

# Lazily-built + cached so the seam import fires only on first real use.
_SYSTEM_INSTRUCTION_CACHE: str | None = None
_INTERACTIVE_SYSTEM_INSTRUCTION_CACHE: str | None = None
# Phase 79 LENS-02 — the lens each cache was built under. A lens change between
# requests (the same process) must rebuild, not serve the stale voice (Flag #3).
_SYSTEM_INSTRUCTION_LENS: str | None = None
_INTERACTIVE_SYSTEM_INSTRUCTION_LENS: str | None = None


def _shared_lens() -> str:
    """Read the ONE shared lens (LENS-02), defaulting to ``"tutor"`` when unset.

    Per-surface default-when-unset: the curator cold path is byte-identical to
    the ``build_curator_instruction("tutor")`` it shipped with. When the user
    sets a lens once (via the settings bus ``_apply_lens``), that SAME value
    drives both the curator and the live co-host. Lazy-imported so the seam
    keeps the import-time no-live-path boundary clean (matrix-seam pattern).

    WR-03: the read is guarded (mirrors the co-host ``_resolve_prompt_cell``
    guard). ``load_config`` already swallows OSError/JSONDecodeError, but any
    OTHER read failure must NOT break curation — fall back to the ``"tutor"``
    cold-path default on any exception so the curator seam degrades gracefully.
    """
    try:
        from vibemix.runtime.config_store import load_config
        from vibemix.runtime.settings import read_shared_lens

        return read_shared_lens(load_config(), default="tutor") or "tutor"
    except Exception:  # pragma: no cover — guard: any read fail = cold default
        return "tutor"


def _system_instruction() -> str:
    """Build (and cache) the one-shot curator system instruction from the seam."""
    global _SYSTEM_INSTRUCTION_CACHE, _SYSTEM_INSTRUCTION_LENS
    lens = _shared_lens()
    if _SYSTEM_INSTRUCTION_CACHE is None or _SYSTEM_INSTRUCTION_LENS != lens:
        from vibemix.prompts.matrix import build_curator_instruction

        _SYSTEM_INSTRUCTION_CACHE = (
            build_curator_instruction(lens) + "\n" + _RULES_BLOCK
        )
        _SYSTEM_INSTRUCTION_LENS = lens
    return _SYSTEM_INSTRUCTION_CACHE


def _interactive_system_instruction() -> str:
    """Build (and cache) the interactive curator system instruction."""
    global _INTERACTIVE_SYSTEM_INSTRUCTION_CACHE, _INTERACTIVE_SYSTEM_INSTRUCTION_LENS
    lens = _shared_lens()
    if (
        _INTERACTIVE_SYSTEM_INSTRUCTION_CACHE is None
        or _INTERACTIVE_SYSTEM_INSTRUCTION_LENS != lens
    ):
        from vibemix.prompts.matrix import build_curator_instruction

        _INTERACTIVE_SYSTEM_INSTRUCTION_CACHE = (
            build_curator_instruction(lens) + "\n" + _INTERACTIVE_FLOW_BLOCK
        )
        _INTERACTIVE_SYSTEM_INSTRUCTION_LENS = lens
    return _INTERACTIVE_SYSTEM_INSTRUCTION_CACHE


def __getattr__(name: str) -> str:
    # PEP 562 — expose the system instructions as module attributes that build
    # the matrix seam on first access (keeps the import-time boundary clean).
    if name == "_SYSTEM_INSTRUCTION":
        return _system_instruction()
    if name == "_INTERACTIVE_SYSTEM_INSTRUCTION":
        return _interactive_system_instruction()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


@dataclass(slots=True)
class CurateResult:
    """Outcome of one curation run."""

    theme: str
    playlist: PlaylistResult | None
    rationale: str
    iterations: int
    stop_reason: str  # "created" | "max_iters" | "no_create" | "model_done"
    seen_track_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "theme": self.theme,
            "playlist": self.playlist.to_dict() if self.playlist else None,
            "rationale": self.rationale,
            "iterations": self.iterations,
            "stop_reason": self.stop_reason,
            "seen_track_ids": self.seen_track_ids,
        }


# --------------------------------------------------------------------------- #
# Tool declarations (typed, JSON-schema). The list IS the scope contract.     #
# --------------------------------------------------------------------------- #


def _tool_declarations(interactive: bool = False) -> list[types.FunctionDeclaration]:
    decls = [
        types.FunctionDeclaration(
            name="search_vibe",
            description=(
                "Semantic vibe-search the user's library. Returns real "
                "track_ids with title/artist/bpm/confidence. The ONLY way to "
                "discover tracks — every id you later use must come from here."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "query": types.Schema(
                        type=types.Type.STRING,
                        description="natural-language vibe description",
                    ),
                    "k": types.Schema(
                        type=types.Type.INTEGER,
                        description="number of candidates (1-50)",
                    ),
                },
                required=["query"],
            ),
        ),
        types.FunctionDeclaration(
            name="get_track_features",
            description=(
                "Deterministic facts for one track_id: bpm, key (Camelot), "
                "genre, duration. Honest null when the library lacks a field. "
                "Use to reason about ordering — never to invent values."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "track_id": types.Schema(type=types.Type.STRING),
                },
                required=["track_id"],
            ),
        ),
        types.FunctionDeclaration(
            name="create_playlist",
            description=(
                "Persist the curated playlist (M3U + JSON). Every track_id "
                "must have come from a prior search_vibe result. Call once, "
                "with the tracks in play order. This ends the run."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "name": types.Schema(type=types.Type.STRING),
                    "track_ids": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(type=types.Type.STRING),
                        description="ordered list of real track_ids",
                    ),
                },
                required=["name", "track_ids"],
            ),
        ),
    ]
    if interactive:
        # Conversational mode only: let the agent ask the DJ short clarifying
        # questions before/while curating. Dispatched to the injected ask_fn
        # (CLI stdin), NOT the grounded toolset — it touches no library state.
        decls.append(
            types.FunctionDeclaration(
                name="ask_user",
                description=(
                    "Ask the DJ ONE short clarifying question (mood, set length, "
                    "energy arc, genre, BPM range, occasion). Use this when the "
                    "brief is vague — but keep it to 1-3 questions total, then "
                    "build. Returns the DJ's answer."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "question": types.Schema(
                            type=types.Type.STRING,
                            description="a single, short, concrete question",
                        )
                    },
                    required=["question"],
                ),
            )
        )
    return decls


# --------------------------------------------------------------------------- #
# The agent.                                                                  #
# --------------------------------------------------------------------------- #


class ViberAgent:
    """Bounded Gemini function-calling playlist curator (Phase 1)."""

    def __init__(
        self,
        client: Any,
        embedder: LibraryEmbedder,
        store: LibraryStore,
        library: RekordboxLibrary,
        *,
        model: str | None = None,
    ) -> None:
        self._client = client
        # Resolve the model through the router — never a hardcoded literal.
        self._model = model or model_router.resolve("library_agent")[0]
        # The grounded tool core (handlers + seen-set gate + per-tool timeout),
        # shared verbatim with the Codex MCP server so grounding never drifts.
        self._toolset = LibraryToolset(embedder, store, library)

    # -- grounding state lives on the shared toolset ------------------------ #

    @property
    def _seen(self) -> set[str]:
        return self._toolset.seen

    @property
    def _created(self) -> PlaylistResult | None:
        return self._toolset.created

    def _dispatch(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        return self._toolset.dispatch(name, args)

    def _gemini_call(self, contents: list[types.Content], cfg: dict[str, Any]):
        """One generate_content call under a hard wall-clock timeout."""
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(
                self._client.models.generate_content,
                model=self._model,
                contents=contents,
                config=cfg,
            )
            return fut.result(timeout=GEMINI_CALL_TIMEOUT_S)

    def curate(self, theme: str) -> CurateResult:
        """Run the bounded one-shot curation loop for ``theme``."""
        contents: list[types.Content] = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=f"Theme: {theme}")],
            )
        ]
        return self._run_loop(
            theme=theme,
            contents=contents,
            system_instruction=_system_instruction(),
            interactive=False,
            ask_fn=None,
            max_iters=MAX_TOOL_ITERATIONS,
        )

    def curate_interactive(
        self,
        ask_fn: Callable[[str], str],
        *,
        opening: str | None = None,
        max_iters: int = MAX_INTERACTIVE_ITERATIONS,
    ) -> CurateResult:
        """Conversational curation: the agent asks the DJ clarifying questions
        (via ``ask_fn``) and builds from their library.

        ``ask_fn(question) -> answer`` is injected — the CLI passes ``input()``;
        tests pass a scripted answerer. The grounding contract is unchanged
        (every track still comes from a search_vibe result; ask_user touches no
        library state). The first user turn is ``opening`` (a seed brief) or a
        generic "build me a set" nudge so the agent opens with a question.
        """
        seed = (opening or "").strip() or (
            "Help me build a set from my library. Ask me what you need to know."
        )
        contents: list[types.Content] = [
            types.Content(role="user", parts=[types.Part.from_text(text=seed)])
        ]
        return self._run_loop(
            theme=opening or "(interactive)",
            contents=contents,
            system_instruction=_interactive_system_instruction(),
            interactive=True,
            ask_fn=ask_fn,
            max_iters=max_iters,
        )

    def _run_loop(
        self,
        *,
        theme: str,
        contents: list[types.Content],
        system_instruction: str,
        interactive: bool,
        ask_fn: Callable[[str], str] | None,
        max_iters: int,
    ) -> CurateResult:
        """The shared bounded tool-dispatch loop (one-shot + interactive)."""
        tools = [
            types.Tool(function_declarations=_tool_declarations(interactive))
        ]
        cfg: dict[str, Any] = {
            "system_instruction": system_instruction,
            "tools": tools,
            # Manual dispatch — disable the SDK's automatic function calling so
            # the seen-set / validation gate runs on every tool call.
            "automatic_function_calling": {"disable": True},
        }

        stop_reason = "max_iters"
        rationale = ""
        i = 0
        for i in range(max_iters):
            try:
                response = self._gemini_call(contents, cfg)
            except concurrent.futures.TimeoutError:
                logger.warning("[viber] Gemini call timed out at iter %d", i)
                stop_reason = "max_iters"
                break
            except Exception as e:  # noqa: BLE001
                logger.warning("[viber] Gemini call failed: %s", e)
                stop_reason = "max_iters"
                break

            calls = list(getattr(response, "function_calls", None) or [])
            # Append the model's turn so the conversation stays coherent.
            cand_content = _first_candidate_content(response)
            if cand_content is not None:
                contents.append(cand_content)

            if not calls:
                # Model produced text instead of a tool call → it's done.
                rationale = (getattr(response, "text", "") or "").strip()
                stop_reason = "created" if self._created else "model_done"
                break

            # Execute each requested call, feed responses back.
            tool_parts: list[types.Part] = []
            for call in calls:
                args = dict(call.args or {})
                if call.name == "ask_user" and ask_fn is not None:
                    # Interactive-only — dispatched to the injected answerer
                    # (CLI stdin), never the grounded toolset.
                    question = str(args.get("question", "")).strip() or "?"
                    try:
                        answer = ask_fn(question)
                    except (EOFError, KeyboardInterrupt):
                        answer = ""  # user bailed → let the model wrap up
                    result: dict[str, Any] = {"answer": answer}
                else:
                    result = self._dispatch(call.name, args)
                tool_parts.append(
                    types.Part.from_function_response(
                        name=call.name, response=result
                    )
                )
            contents.append(types.Content(role="user", parts=tool_parts))

            if self._created is not None:
                # create_playlist succeeded — one write per run, we're done.
                stop_reason = "created"
                break
        else:
            # Loop exhausted max_iters without breaking.
            stop_reason = "max_iters"

        # Normalize: stop_reason reflects reality. self._created (set only by
        # a successful create_playlist) is the single source of truth — if a
        # playlist exists the run "created" one, otherwise keep whatever the
        # loop decided (model_done / max_iters).
        if self._created is not None:
            stop_reason = "created"

        return CurateResult(
            theme=theme,
            playlist=self._created,
            rationale=rationale,
            iterations=i + 1,
            stop_reason=stop_reason,
            seen_track_ids=sorted(self._seen),
        )


def _first_candidate_content(response: Any) -> types.Content | None:
    """Extract the model turn's Content for transcript continuity."""
    candidates = getattr(response, "candidates", None)
    if candidates:
        content = getattr(candidates[0], "content", None)
        if isinstance(content, types.Content):
            return content
    return None


__all__ = [
    "MAX_TOOL_ITERATIONS",
    "MAX_INTERACTIVE_ITERATIONS",
    "CurateResult",
    "ViberAgent",
]
