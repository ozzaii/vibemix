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
from typing import Any

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
# Hard wall-clock per Gemini call. A hung network can never park the loop.
# (Per-tool timeout lives in LibraryToolset.dispatch.)
GEMINI_CALL_TIMEOUT_S = 60.0

_SYSTEM_INSTRUCTION = (
    "You are Viber, a DJ's crate-digging co-pilot. Build a playlist from the "
    "user's OWN library that fits their theme.\n"
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


def _tool_declarations() -> list[types.FunctionDeclaration]:
    return [
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
        """Run the bounded curation loop for ``theme``."""
        tools = [types.Tool(function_declarations=_tool_declarations())]
        cfg: dict[str, Any] = {
            "system_instruction": _SYSTEM_INSTRUCTION,
            "tools": tools,
            # Manual dispatch — disable the SDK's automatic function calling so
            # the seen-set / validation gate runs on every tool call.
            "automatic_function_calling": {"disable": True},
        }
        contents: list[types.Content] = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=f"Theme: {theme}")],
            )
        ]

        stop_reason = "max_iters"
        rationale = ""
        for i in range(MAX_TOOL_ITERATIONS):
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
            # Loop exhausted MAX_TOOL_ITERATIONS without breaking.
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
    "CurateResult",
    "ViberAgent",
]
