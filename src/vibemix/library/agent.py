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
import threading
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
# Transient-overload retry (503/UNAVAILABLE/"high demand" on the Flash preview
# tier). Bounded so a wedged backend still surfaces an error promptly.
_GEMINI_RETRIES = 3
_GEMINI_BACKOFF_S = 2.0

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

_SET_PREP_BLOCK = (
    "SET-PREP FLOW (you are prepping a full DJ set, not a flat playlist):\n"
    "1. discover_pool a candidate pool from the DJ's library for the brief "
    "(use the vibe and/or any reference tracks). This is a grounded discovery "
    "path on par with search_vibe — every track_id you later use MUST come "
    "from discover_pool or search_vibe, NEVER invent one.\n"
    "2. Pick an energy CURVE that fits the brief: opener (warm-up climb), "
    "peak_time (prime-time plateau), after_hours (hypnotic high), or festival "
    "(multi-peak). Peek get_track_energy / get_track_features when it helps "
    "you reason — energy/key/BPM are deterministic facts from the tools, never "
    "your guesses.\n"
    "3. sequence_set the pool into the curve. It returns 3-5 ranked candidates; "
    "choose the best one (lowest cost / cleanest transitions).\n"
    "4. In 1-2 sentences explain WHY the critical transitions work — name the "
    "key/BPM/energy/vibe reason. Surface any relaxed_transitions honestly "
    "(a BPM jump or key bridge is a warning, not a hidden flaw).\n"
    "5. Offer to export_set (Rekordbox XML) when the DJ is happy. Keep it tight "
    "— a focused, well-sequenced set beats a padded one."
)

_CHAT_BLOCK = (
    "CHAT MODE (you are a DJ co-host in an ongoing conversation, not a one-shot "
    "playlist bot):\n"
    "1. Talk like a real DJ friend in their ear — warm, concrete, never generic "
    "AI filler. Answer the actual question; keep it tight.\n"
    "2. You have grounded tools and SHOULD use them when they help: search_vibe "
    "/ discover_pool (find tracks in their library), get_track_features / "
    "get_track_energy (deterministic facts), quote_moment (point at a [start,end] "
    "moment in a library track), web_search / fetch_url (facts the library can't "
    "supply — cite the url), ingest_youtube (listen to a YouTube link), "
    "retrieve_dj_knowledge (technique with citations), sequence_set + export_set "
    "(prep a full set), create_playlist (save a curated list).\n"
    "3. GROUNDING (non-negotiable): only ever name a track that a search_vibe / "
    "discover_pool call returned THIS conversation. Never invent a track, title, "
    "artist, BPM, or key. Keys/BPM/energy come from the tools, not your memory. "
    "When you state a web/technique fact, ground it with a tool and let the "
    "source show.\n"
    "4. You do NOT have to call a tool every turn — if they're just chatting, "
    "chat back. End your turn with a normal spoken reply (not a tool call)."
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
_SET_PREP_SYSTEM_INSTRUCTION_CACHE: str | None = None
_SET_PREP_SYSTEM_INSTRUCTION_LENS: str | None = None
# Phase 79 LENS-02 — the lens each cache was built under. A lens change between
# requests (the same process) must rebuild, not serve the stale voice (Flag #3).
_SYSTEM_INSTRUCTION_LENS: str | None = None
_INTERACTIVE_SYSTEM_INSTRUCTION_LENS: str | None = None
# WR-04: the gemini agent runs the model call under a ThreadPoolExecutor, so two
# threads can enter the check-then-set on a concurrent lens change, both rebuild,
# and interleave the (_CACHE, _LENS) writes — leaving _CACHE built under lens A
# while _LENS records lens B (wrong voice served until the next change). Guard the
# whole check-rebuild-store under one module lock. The build is cheap and only on
# the cache-miss path, so the lock is uncontended in the steady state.
_CACHE_LOCK = threading.Lock()


def _shared_lens() -> str:
    """Read the ONE shared lens (LENS-02) — delegates to the shared seam.

    IN-01: the lens read is single-sourced in ``library._curator_seams`` so the
    gemini and codex backends can never diverge. Lazy-imported so importing this
    module does not drag the seam's runtime readers into ``sys.modules`` at
    import time (no-live-path boundary).
    """
    from vibemix.library._curator_seams import shared_lens

    return shared_lens()


def _taste_hint() -> str:
    """SEAM #2 (CURATE-02) taste hint — delegates to the shared seam.

    IN-01 + WR-01: the consent-gated profile read is single-sourced in
    ``library._curator_seams.taste_hint`` so the consent contract lands in BOTH
    backends from one place (the codex twin calls the same helper). Returns
    ``""`` when consent is OFF or the profile is absent → cold-path byte-identity
    holds even when a stale ``profile.json`` outlives a consent toggle-OFF.
    """
    from vibemix.library._curator_seams import taste_hint

    return taste_hint()


def _system_instruction() -> str:
    """Build (and cache) the one-shot curator system instruction from the seam."""
    global _SYSTEM_INSTRUCTION_CACHE, _SYSTEM_INSTRUCTION_LENS
    lens = _shared_lens()
    # WR-04: serialize the check-then-set so concurrent lens-change rebuilds can't
    # interleave the (_CACHE, _LENS) writes and serve the wrong voice.
    with _CACHE_LOCK:
        if _SYSTEM_INSTRUCTION_CACHE is None or _SYSTEM_INSTRUCTION_LENS != lens:
            from vibemix.prompts.matrix import build_curator_instruction

            _SYSTEM_INSTRUCTION_CACHE = (
                build_curator_instruction(lens) + "\n" + _RULES_BLOCK
            )
            _SYSTEM_INSTRUCTION_LENS = lens
        base = _SYSTEM_INSTRUCTION_CACHE
    # SEAM #2: append the profile taste hint OUTSIDE the lens-keyed cache so a
    # profile change is reflected per call; "" on the cold path → byte-identical.
    return base + _taste_hint()


def _chat_system_instruction() -> str:
    """Build the conversational chat system instruction (curator voice + CHAT).

    Reuses the SAME shared curator voice (build_curator_instruction(lens)) plus
    the CHAT flow block. Computed per call (cheap string build; a chat turn is
    already gated by a network call) so a lens/profile change is always live —
    no separate cache to invalidate. Grounding lives at the toolset boundary.
    """
    from vibemix.prompts.matrix import build_curator_instruction

    return build_curator_instruction(_shared_lens()) + "\n" + _CHAT_BLOCK + _taste_hint()


def _interactive_system_instruction() -> str:
    """Build (and cache) the interactive curator system instruction."""
    global _INTERACTIVE_SYSTEM_INSTRUCTION_CACHE, _INTERACTIVE_SYSTEM_INSTRUCTION_LENS
    lens = _shared_lens()
    # WR-04: same check-then-set guard as _system_instruction.
    with _CACHE_LOCK:
        if (
            _INTERACTIVE_SYSTEM_INSTRUCTION_CACHE is None
            or _INTERACTIVE_SYSTEM_INSTRUCTION_LENS != lens
        ):
            from vibemix.prompts.matrix import build_curator_instruction

            _INTERACTIVE_SYSTEM_INSTRUCTION_CACHE = (
                build_curator_instruction(lens) + "\n" + _INTERACTIVE_FLOW_BLOCK
            )
            _INTERACTIVE_SYSTEM_INSTRUCTION_LENS = lens
        base = _INTERACTIVE_SYSTEM_INSTRUCTION_CACHE
    # SEAM #2: interactive curation must not be orphaned — same taste append.
    return base + _taste_hint()


def _set_prep_system_instruction() -> str:
    """Build (and cache) the set-prep curator system instruction.

    Reuses the SAME shared curator voice (build_curator_instruction(lens)) the
    plain curator uses + the SET-PREP flow block. The grounding contract is
    enforced at the toolset boundary (seen-set gate), but the flow block keeps
    the never-invent-id discipline front-of-mind for the model too.
    """
    global _SET_PREP_SYSTEM_INSTRUCTION_CACHE, _SET_PREP_SYSTEM_INSTRUCTION_LENS
    lens = _shared_lens()
    with _CACHE_LOCK:
        if (
            _SET_PREP_SYSTEM_INSTRUCTION_CACHE is None
            or _SET_PREP_SYSTEM_INSTRUCTION_LENS != lens
        ):
            from vibemix.prompts.matrix import build_curator_instruction

            _SET_PREP_SYSTEM_INSTRUCTION_CACHE = (
                build_curator_instruction(lens) + "\n" + _SET_PREP_BLOCK
            )
            _SET_PREP_SYSTEM_INSTRUCTION_LENS = lens
        base = _SET_PREP_SYSTEM_INSTRUCTION_CACHE
    return base + _taste_hint()


def __getattr__(name: str) -> str:
    # PEP 562 — expose the system instructions as module attributes that build
    # the matrix seam on first access (keeps the import-time boundary clean).
    if name == "_SYSTEM_INSTRUCTION":
        return _system_instruction()
    if name == "_INTERACTIVE_SYSTEM_INSTRUCTION":
        return _interactive_system_instruction()
    if name == "_SET_PREP_SYSTEM_INSTRUCTION":
        return _set_prep_system_instruction()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


@dataclass(slots=True)
class ChatResult:
    """Outcome of one conversational chat turn.

    The chat surface (the "normal Viber AI chat") is multi-turn and tool-using:
    the model may call any grounded tool (search/discover/quote/web/youtube/
    knowledge/curate/build) before it replies. ``reply`` is Viber's spoken text;
    ``tool_trace`` is the ordered list of tools it ran THIS turn (name + a short
    arg echo + whether it succeeded) so the UI can "show its work" honestly;
    ``playlist`` / ``export_path`` carry a terminal artifact when the turn
    produced one. Grounding is unchanged — the trace reflects real tool calls,
    never narration.
    """

    reply: str
    tool_trace: list[dict[str, Any]] = field(default_factory=list)
    playlist: PlaylistResult | None = None
    export_path: str | None = None
    seen_track_ids: list[str] = field(default_factory=list)
    iterations: int = 0
    stop_reason: str = "model_done"  # "model_done" | "created" | "exported" | "max_iters"

    def to_dict(self) -> dict[str, Any]:
        return {
            "reply": self.reply,
            "tool_trace": self.tool_trace,
            "playlist": self.playlist.to_dict() if self.playlist else None,
            "export_path": self.export_path,
            "seen_track_ids": self.seen_track_ids,
            "iterations": self.iterations,
            "stop_reason": self.stop_reason,
        }


@dataclass(slots=True)
class CurateResult:
    """Outcome of one curation run."""

    theme: str
    playlist: PlaylistResult | None
    rationale: str
    iterations: int
    # "created" | "exported" | "max_iters" | "no_create" | "model_done"
    stop_reason: str
    seen_track_ids: list[str] = field(default_factory=list)
    # BL-02: the Rekordbox XML path a set-prep run exported, when export_set
    # ran. ``None`` for plain curation / a run that never exported.
    export_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "theme": self.theme,
            "playlist": self.playlist.to_dict() if self.playlist else None,
            "rationale": self.rationale,
            "iterations": self.iterations,
            "stop_reason": self.stop_reason,
            "seen_track_ids": self.seen_track_ids,
            "export_path": self.export_path,
        }


# --------------------------------------------------------------------------- #
# Tool declarations (typed, JSON-schema). The list IS the scope contract.     #
# --------------------------------------------------------------------------- #


def _set_prep_declarations() -> list[types.FunctionDeclaration]:
    """The 4 extra set-prep tools (Vibe Mix engine) layered on the base 3.

    These mirror the toolset handlers. They keep grounding identical: every
    track_id sequenced/exported MUST have come from discover_pool / search_vibe.
    """
    return [
        types.FunctionDeclaration(
            name="discover_pool",
            description=(
                "Build a diverse candidate POOL from the DJ's library for a "
                "vibe and/or reference tracks. Like search_vibe it is a "
                "grounded discovery path — every track_id it returns may be "
                "sequenced/exported. Returns track_id/title/artist/bpm/camelot/"
                "similarity. Prefer this over search_vibe for a full set."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "query": types.Schema(
                        type=types.Type.STRING,
                        description="natural-language vibe (optional if refs given)",
                    ),
                    "ref_track_ids": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(type=types.Type.STRING),
                        description="seed track_ids to anchor the pool (optional)",
                    ),
                    "k": types.Schema(type=types.Type.INTEGER),
                    "bpm_min": types.Schema(type=types.Type.NUMBER),
                    "bpm_max": types.Schema(type=types.Type.NUMBER),
                    "min_duration_s": types.Schema(type=types.Type.NUMBER),
                    "max_duration_s": types.Schema(type=types.Type.NUMBER),
                    "exclude_ids": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(type=types.Type.STRING),
                    ),
                },
            ),
        ),
        types.FunctionDeclaration(
            name="get_track_energy",
            description=(
                "Deterministic perceived dancefloor energy (0-100) computed "
                "from the audio for one track_id. Honest null when no file / "
                "undecodable. Use to reason about the energy arc — never invent."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={"track_id": types.Schema(type=types.Type.STRING)},
                required=["track_id"],
            ),
        ),
        types.FunctionDeclaration(
            name="sequence_set",
            description=(
                "Order grounded track_ids into a set that follows an energy "
                "CURVE preset (opener / peak_time / after_hours / festival). "
                "Returns 3-5 ranked candidates with energy_fit, avg_coherence, "
                "and any relaxed_transitions (BPM/key warnings). Every track_id "
                "must come from a prior discover_pool/search_vibe result."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "track_ids": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(type=types.Type.STRING),
                        description="grounded candidate track_ids to order",
                    ),
                    "curve": types.Schema(
                        type=types.Type.STRING,
                        description=(
                            "energy curve preset: opener | peak_time | "
                            "after_hours | festival"
                        ),
                    ),
                    "n_slots": types.Schema(
                        type=types.Type.INTEGER,
                        description="set length (default = number of track_ids)",
                    ),
                },
                required=["track_ids", "curve"],
            ),
        ),
        types.FunctionDeclaration(
            name="export_set",
            description=(
                "Export the chosen ordered set to a Rekordbox-importable XML "
                "(order + key + BPM + cues). Every track_id must have come from "
                "a prior discovery result. Call once when the DJ accepts a set."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "name": types.Schema(type=types.Type.STRING),
                    "track_ids": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(type=types.Type.STRING),
                        description="ordered set track_ids (the chosen sequence)",
                    ),
                    "out_path": types.Schema(
                        type=types.Type.STRING,
                        description="optional XML destination path",
                    ),
                },
                required=["name", "track_ids"],
            ),
        ),
        types.FunctionDeclaration(
            name="export_cues",
            description=(
                "Write AI-placed structural hot cues (intro/build/breakdown/"
                "drop/outro, from the auto-cue engine) back to a Rekordbox-"
                "importable XML for one track. Non-destructive: the DJ imports "
                "the produced tree. 'cues' is a serialized CueAnchor list."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "track_path": types.Schema(type=types.Type.STRING),
                    "cues": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "label": types.Schema(type=types.Type.STRING),
                                "start_s": types.Schema(type=types.Type.NUMBER),
                                "end_s": types.Schema(type=types.Type.NUMBER),
                                "confidence": types.Schema(type=types.Type.NUMBER),
                                "source": types.Schema(type=types.Type.STRING),
                            },
                            required=["label", "start_s"],
                        ),
                        description="serialized CueAnchor list from the auto-cue engine",
                    ),
                    "out_path": types.Schema(
                        type=types.Type.STRING,
                        description="optional XML destination path",
                    ),
                    "title": types.Schema(type=types.Type.STRING),
                    "artist": types.Schema(type=types.Type.STRING),
                    "bpm": types.Schema(type=types.Type.NUMBER),
                },
                required=["track_path", "cues"],
            ),
        ),
    ]


def _tool_declarations(
    interactive: bool = False, set_prep: bool = False
) -> list[types.FunctionDeclaration]:
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
        types.FunctionDeclaration(
            name="web_search",
            description=(
                "Web-search for DJ knowledge the user's library can't supply "
                "(track/label/artist facts, releases, scene context). Returns "
                "real {title, url, snippet, score} hits. Cite the url — never "
                "state a snippet as fact without its source."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "query": types.Schema(
                        type=types.Type.STRING,
                        description="natural-language web query",
                    ),
                    "k": types.Schema(
                        type=types.Type.INTEGER,
                        description="number of results (1-10)",
                    ),
                },
                required=["query"],
            ),
        ),
        types.FunctionDeclaration(
            name="fetch_url",
            description=(
                "Fetch one web page's readable text — pass a url returned by a "
                "prior web_search. Returns {url, title, text}. http(s) only. "
                "Read sources you cite; never invent page contents."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "url": types.Schema(
                        type=types.Type.STRING,
                        description="http(s) url from a web_search result",
                    ),
                },
                required=["url"],
            ),
        ),
        types.FunctionDeclaration(
            name="ingest_youtube",
            description=(
                "Listen to a YouTube track or mix and get a coarse description "
                "(genre, energy, mood, structure: intro/build/drop/breakdown/"
                "outro, notable moments). Deep-link only — nothing is "
                "downloaded. Any timestamps in the summary are APPROXIMATE "
                "HINTS, not precise cut points."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "url": types.Schema(
                        type=types.Type.STRING,
                        description="A YouTube watch / youtu.be / shorts URL.",
                    ),
                    "prompt": types.Schema(
                        type=types.Type.STRING,
                        description="Optional custom question about the track.",
                    ),
                },
                required=["url"],
            ),
        ),
        types.FunctionDeclaration(
            name="quote_moment",
            description=(
                "Point at a specific moment inside a library track with a "
                "grounded, resolvable reference (e.g. 'this is the breakdown I'm "
                "talking about'). Returns a quote with a [start_s, end_s] window "
                "and a human caption. track_id MUST be an id returned by a prior "
                "search_vibe/discover_pool result this run — never invent one."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "track_id": types.Schema(
                        type=types.Type.STRING,
                        description="A track_id from a prior search result.",
                    ),
                    "start_s": types.Schema(
                        type=types.Type.NUMBER,
                        description="Window start in seconds (>= 0).",
                    ),
                    "end_s": types.Schema(
                        type=types.Type.NUMBER,
                        description="Window end in seconds (> start_s).",
                    ),
                    "label": types.Schema(
                        type=types.Type.STRING,
                        description="Optional: intro|build|breakdown|drop|outro.",
                    ),
                    "caption": types.Schema(
                        type=types.Type.STRING,
                        description="Optional caption; auto-synthesized when omitted.",
                    ),
                },
                required=["track_id", "start_s", "end_s"],
            ),
        ),
        types.FunctionDeclaration(
            name="retrieve_dj_knowledge",
            description=(
                "Retrieve grounded DJ-technique knowledge (EQ-ing, phrasing, "
                "harmonic mixing, gain staging) with attributed link-out "
                "citations. Use for the TUTOR lens to ground technique answers; "
                "never invent technique facts."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "query": types.Schema(
                        type=types.Type.STRING,
                        description="The technique question.",
                    ),
                    "topic": types.Schema(
                        type=types.Type.STRING,
                        description="Optional topic filter, e.g. 'eq', 'phrasing'.",
                    ),
                    "skill_level": types.Schema(
                        type=types.Type.STRING,
                        description="Optional: beginner | intermediate | pro.",
                    ),
                    "k": types.Schema(
                        type=types.Type.INTEGER,
                        description="Number of results, 1-10 (default 4).",
                    ),
                },
                required=["query"],
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
    if set_prep:
        decls.extend(_set_prep_declarations())
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
        # The raw client is threaded in so capability tools (ingest_youtube) can
        # reason directly through Gemini.
        self._toolset = LibraryToolset(embedder, store, library, client=client)

    # -- grounding state lives on the shared toolset ------------------------ #

    @property
    def _seen(self) -> set[str]:
        return self._toolset.seen

    @property
    def _created(self) -> PlaylistResult | None:
        return self._toolset.created

    @property
    def _exported(self) -> Any | None:
        # BL-02: the set-prep export terminal signal (ExportResult | None).
        return self._toolset.exported

    def _dispatch(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        return self._toolset.dispatch(name, args)

    def _gemini_call(self, contents: list[types.Content], cfg: dict[str, Any]):
        """One generate_content call under a hard wall-clock timeout.

        Transient server overload (503 / UNAVAILABLE / "high demand") is common
        on the Flash preview tier and would otherwise leave a turn with an empty
        reply — so retry a few times with short backoff. Non-transient errors
        (and the wall-clock timeout) are re-raised to the caller's per-loop
        handler unchanged.
        """
        import time as _time

        last_exc: Exception | None = None
        for attempt in range(_GEMINI_RETRIES + 1):
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                fut = ex.submit(
                    self._client.models.generate_content,
                    model=self._model,
                    contents=contents,
                    config=cfg,
                )
                try:
                    return fut.result(timeout=GEMINI_CALL_TIMEOUT_S)
                except concurrent.futures.TimeoutError:
                    raise  # wall-clock — do not retry, the caller decides
                except Exception as e:  # noqa: BLE001
                    msg = str(e).lower()
                    transient = any(
                        h in msg
                        for h in ("503", "unavailable", "overloaded", "high demand", "rate")
                    )
                    if not transient or attempt == _GEMINI_RETRIES:
                        raise
                    last_exc = e
                    _time.sleep(_GEMINI_BACKOFF_S * (attempt + 1))
        if last_exc is not None:  # pragma: no cover — loop returns or raises above
            raise last_exc

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

    def build_set(self, brief: str) -> CurateResult:
        """Run the bounded SET-PREP loop: discover → sequence → (offer) export.

        Same bounded no-hang harness as ``curate`` (``MAX_TOOL_ITERATIONS``,
        per-call timeouts, handlers-return-errors), but with the full set-prep
        tool surface (the 3 base tools + discover_pool / get_track_energy /
        sequence_set / export_set) and the SET-PREP system instruction. Grounding
        is unchanged — every track_id is gated through the shared seen-set.

        The set-prep loop may need a couple of extra turns (discover → energy
        peeks → sequence → export), so it runs at the higher interactive cap.
        """
        contents: list[types.Content] = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=f"Set brief: {brief}")],
            )
        ]
        return self._run_loop(
            theme=brief,
            contents=contents,
            system_instruction=_set_prep_system_instruction(),
            interactive=False,
            ask_fn=None,
            max_iters=MAX_INTERACTIVE_ITERATIONS,
            set_prep=True,
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

    def chat(
        self, message: str, history: list[dict[str, Any]] | None = None
    ) -> ChatResult:
        """One conversational turn of the Viber chat (multi-turn, tool-using).

        ``history`` is the prior conversation as ``[{"role": "you"|"viber",
        "text": ...}, ...]`` (oldest first); ``message`` is the new user turn.
        The model may call any grounded tool before replying. Returns a
        :class:`ChatResult` with the spoken reply, the ordered tool trace (for
        the UI to show its work), and any terminal artifact (playlist / export).
        Grounding is enforced at the toolset boundary exactly as in curate.
        """
        contents: list[types.Content] = []
        for turn in history or []:
            text = str(turn.get("text") or "").strip()
            if not text:
                continue
            # Gemini roles: the model's prior turns are role="model".
            role = "model" if turn.get("role") == "viber" else "user"
            contents.append(
                types.Content(role=role, parts=[types.Part.from_text(text=text)])
            )
        contents.append(
            types.Content(role="user", parts=[types.Part.from_text(text=message)])
        )
        return self._chat_loop(contents)

    def _chat_loop(self, contents: list[types.Content]) -> ChatResult:
        """Bounded conversational tool-dispatch loop (no forced create)."""
        # Full capability surface: base 3 + web/youtube/quote/knowledge (base)
        # + discover/energy/sequence/export/export_cues (set_prep).
        tools = [
            types.Tool(function_declarations=_tool_declarations(set_prep=True))
        ]
        cfg: dict[str, Any] = {
            "system_instruction": _chat_system_instruction(),
            "tools": tools,
            "automatic_function_calling": {"disable": True},
        }

        trace: list[dict[str, Any]] = []
        reply = ""
        stop_reason = "max_iters"
        i = 0
        for i in range(MAX_INTERACTIVE_ITERATIONS):
            try:
                response = self._gemini_call(contents, cfg)
            except concurrent.futures.TimeoutError:
                logger.warning("[viber] chat Gemini call timed out at iter %d", i)
                break
            except Exception as e:  # noqa: BLE001
                logger.warning("[viber] chat Gemini call failed: %s", e)
                break

            calls = list(getattr(response, "function_calls", None) or [])
            cand_content = _first_candidate_content(response)
            if cand_content is not None:
                contents.append(cand_content)

            if not calls:
                # Model spoke — that's the turn's reply.
                reply = (getattr(response, "text", "") or "").strip()
                stop_reason = "model_done"
                break

            tool_parts: list[types.Part] = []
            for call in calls:
                args = dict(call.args or {})
                result = self._dispatch(call.name, args)
                trace.append(
                    {
                        "name": call.name,
                        "arg": _short_arg(args),
                        "ok": isinstance(result, dict) and "error" not in result,
                    }
                )
                tool_parts.append(
                    types.Part.from_function_response(
                        name=call.name, response=result
                    )
                )
            contents.append(types.Content(role="user", parts=tool_parts))
        else:
            stop_reason = "max_iters"

        # Terminal artifacts (if the turn produced one) override the stop reason.
        if self._created is not None:
            stop_reason = "created"
        elif self._exported is not None:
            stop_reason = "exported"

        export_path = (
            str(self._exported.path) if self._exported is not None else None
        )
        return ChatResult(
            reply=reply,
            tool_trace=trace,
            playlist=self._created,
            export_path=export_path,
            seen_track_ids=sorted(self._seen),
            iterations=i + 1,
            stop_reason=stop_reason,
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
        set_prep: bool = False,
    ) -> CurateResult:
        """The shared bounded tool-dispatch loop (one-shot + interactive + set-prep)."""
        tools = [
            types.Tool(
                function_declarations=_tool_declarations(interactive, set_prep)
            )
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
            # BL-02: in set-prep, a successful export_set is the terminal write —
            # break with "exported" so the loop stops instead of running to the
            # cap. (Plain curation never exports, so this only fires on set-prep.)
            if set_prep and self._exported is not None:
                stop_reason = "exported"
                break
        else:
            # Loop exhausted max_iters without breaking.
            stop_reason = "max_iters"

        # Normalize: stop_reason reflects reality. self._created (set only by
        # a successful create_playlist) is the single source of truth — if a
        # playlist exists the run "created" one. A set-prep export is the next
        # terminal signal; otherwise keep whatever the loop decided.
        if self._created is not None:
            stop_reason = "created"
        elif self._exported is not None:
            stop_reason = "exported"

        export_path = (
            str(self._exported.path) if self._exported is not None else None
        )
        return CurateResult(
            theme=theme,
            playlist=self._created,
            rationale=rationale,
            iterations=i + 1,
            stop_reason=stop_reason,
            seen_track_ids=sorted(self._seen),
            export_path=export_path,
        )


def _short_arg(args: dict[str, Any]) -> str:
    """A short, human arg echo for the chat tool-trace (UI 'shows its work').

    Picks the most telling field (query / track_id / url / theme / name / brief)
    and truncates — never dumps the whole arg dict into the UI.
    """
    for key in ("query", "url", "theme", "brief", "name", "track_id", "curve"):
        v = args.get(key)
        if isinstance(v, str) and v.strip():
            v = v.strip()
            return v[:40] + "…" if len(v) > 40 else v
    return ""


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
    "ChatResult",
    "CurateResult",
    "ViberAgent",
]
