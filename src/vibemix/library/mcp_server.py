# SPDX-License-Identifier: Apache-2.0
"""vibemix-library MCP server — the grounded tool surface for Codex.

This is the Codex backend of the Viber agent (the Hermes pattern, native CLI):
the native ``codex exec`` runtime is the bounded reasoning harness; this STDIO
MCP server exposes the grounded tool core, backed by the shared
:class:`~vibemix.library.toolset.LibraryToolset`. The core discovery/write
tools are ``search_vibe`` / ``discover_pool`` / ``create_playlist`` /
``ingest_source`` / ``export_set``; additional tools add batch inspection,
energy, sequencing, web, quote, knowledge, and cue-export capabilities. Codex plans the curation and calls
these tools; the seen-set grounding gate (Cardinal Invariant #2) and the
write/export re-validation are enforced here at the tool boundary — NOT in the
prompt — so the model can never smuggle in an invented track regardless of what
it reasons.

Lifecycle: Codex spawns ONE instance of this server (as a STDIO subprocess) per
``codex exec`` run, so the module-level ``LibraryToolset`` (and its per-run
``seen`` set) lives exactly as long as one curation run — the correct grounding
scope. The embedder / store / library are allocated once at startup (DI,
mirroring ``main()``).

Run standalone (what Codex's config points at):

    python -m vibemix.library.mcp_server

Library search/build-set is local and keyless through CLAP ONNX. The shipped
Codex/Viber MCP surface does not resolve a Gemini client or expose Gemini-backed
media tools.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

# WIRE-04 (Phase 77 Plan 02) — voice inherited via the codex_curate seam
# (verified — no own prompt). This server carries NO system prompt / persona of
# its own: it only exposes grounded tools over STDIO, and grounding lives at
# the tool boundary (LibraryToolset seen-set gate), not in a prompt. The
# curator voice reaches Codex through ``library.codex_curate._SYSTEM_PROMPT``,
# which now sources its persona from ``prompts.matrix.build_curator_instruction``
# — so this backend is provably NOT persona-blind (CURATE acid test), with no
# change needed here.

logger = logging.getLogger(__name__)


def build_toolset() -> Any:
    """Allocate the shared grounded tool core once (embedder + store + library).

    Loads the on-disk Rekordbox/folder library cache. If it is missing the
    server still starts; ``search_vibe`` then honestly returns no candidates
    (better than refusing to boot — the failure is visible in tool output).
    """
    # Phase 99 HARDEN-RETRY Plan 99-04 Task 5 — B1 Option A env-var
    # propagation probe. Logs whether the stop-reason env var (see the
    # ``os.environ.get`` call below) crossed both process boundaries
    # (wrapper → Codex CLI subprocess → this MCP child).
    # If the log shows a real temp-dir path: Channel A is healthy end-to-end
    # for real Codex runs. If it shows <absent>: Codex CLI stripped the env
    # var when spawning the MCP child, and the side-channel write inside the
    # toolset silently no-ops — fix lands as HARDEN-FUTURE (Codex MCP harness
    # config / `passthrough_env` knob / Codex CLI version bump / direct
    # mcp_servers.<name>.env override). Plan 99-08's
    # §HARDEN-PHASE-A-ENV-PROPAGATION-VERIFY checkpoint observes the FIRST
    # real Codex run output. Local `import os` (not module-top) keeps the
    # edit surface to this one function — sys is already imported up top.
    import os

    print(
        f"[viber-mcp] VIBEMIX_STOP_REASON_FILE="
        f"{os.environ.get('VIBEMIX_STOP_REASON_FILE', '<absent>')}",
        file=sys.stderr,
        flush=True,
    )

    # .env is not auto-loaded in a bare subprocess — load it like __main__ does.
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:
        # dotenv is optional; env may already be set.
        pass

    from vibemix.library.embed_factory import build_embedder
    from vibemix.library.rekordbox import RekordboxLibrary
    from vibemix.library.staleness import library_freshness_status
    from vibemix.library.store import open_store
    from vibemix.library.toolset import LibraryToolset

    library = RekordboxLibrary()
    if not library.try_load_cache():
        print(
            "[viber-mcp] WARNING: no library cache "
            "(~/.cache/vibemix/library.pkl) — search will return nothing. "
            "Import a Rekordbox XML or run `library embed-folder` first.",
            file=sys.stderr,
            flush=True,
        )
    embedder = build_embedder()
    store = open_store()
    return LibraryToolset(
        embedder,
        store,
        library,
        freshness_provider=library_freshness_status,
    )


class _ToolTapProxy:
    """Route every MCP tool call through ``LibraryToolset.dispatch``.

    The FastMCP tool wrappers in ``build_server`` used to call handlers
    DIRECTLY (``toolset.search_vibe(...)``) — which bypassed everything
    ``dispatch()`` owns: the per-tool hard timeouts, the Phase-99 starvation
    counter + terminal short-circuit, the freshness guard, and the live
    tool-tape emit. The machinery existed but never protected real Codex runs.
    Now any attribute named in the dispatch registry routes through
    ``dispatch`` (one tape row per call lands there); non-tool callables
    (e.g. ``seed_working_set``) pass straight to the toolset.
    """

    def __init__(self, inner: Any) -> None:
        self._inner = inner

    def __getattr__(self, name: str) -> Any:
        # Only triggered for attrs not on the proxy itself (i.e. the handlers).
        attr = getattr(self._inner, name)
        if name.startswith("_") or not callable(attr):
            return attr
        registry = getattr(self._inner, "_dispatch_handlers", None)
        if not callable(registry) or name not in registry():
            return attr

        def _dispatched(*args: Any, **kwargs: Any) -> Any:
            # Every FastMCP wrapper passes exactly one positional dict; accept
            # kwargs too so a future wrapper style cannot silently skip dispatch.
            tool_args = args[0] if args and isinstance(args[0], dict) else dict(kwargs)
            return self._inner.dispatch(name, tool_args)

        return _dispatched


def build_server(toolset: Any) -> Any:
    """Wrap ``toolset`` in a FastMCP STDIO server exposing Viber tools.

    Each tool delegates to the shared toolset, so the grounding gate stays
    single-sourced. Tools return plain dicts
    (FastMCP serializes them); errors come back as ``{"error": ...}`` rather
    than raising — the no-hang contract.
    """
    from mcp.server.fastmcp import FastMCP

    # The tool wrappers below call handlers directly (not via dispatch), so wrap
    # the toolset to emit a live tool-tape record per call — the only chokepoint
    # the Codex MCP path flows through.
    toolset = _ToolTapProxy(toolset)

    mcp = FastMCP("vibemix-library")

    @mcp.tool()
    def search_vibe(query: str, k: int = 15) -> dict[str, Any]:
        """Semantic vibe-search the user's library. Returns real track_ids
        (title/artist/bpm/confidence). A grounded discovery path: every id it
        returns may be sequenced/exported."""
        return toolset.search_vibe({"query": query, "k": k})

    @mcp.tool()
    def get_track_features(track_id: str) -> dict[str, Any]:
        """Deterministic facts for one track_id: bpm, key (Camelot), duration.
        Honest null when the library lacks a field. Use to reason about
        ordering — never to invent values."""
        return toolset.get_track_features({"track_id": track_id})

    @mcp.tool()
    def get_track_sections(track_id: str) -> dict[str, Any]:
        """Issue grounded section records for a discovered track. track_id must
        come from search_vibe/discover_pool this run. Returns section_ids the
        agent may later use in transition_slate."""
        return toolset.get_track_sections({"track_id": track_id})

    @mcp.tool()
    def inspect_candidates(track_ids: list[str]) -> dict[str, Any]:
        """Batch inspect discovered candidates in one call: deterministic
        features, grounded sections, and perceived energy for each track_id.
        Every track_id must have come from search_vibe/discover_pool this run;
        unseen ids return per-row errors. Use this ONCE for a candidate pool
        instead of looping get_track_features / get_track_sections /
        get_track_energy per track."""
        return toolset.inspect_candidates({"track_ids": track_ids})

    @mcp.tool()
    def transition_slate(
        candidate_track_ids: list[str],
        source_section_id: str | None = None,
        source_track_id: str | None = None,
        mode: str = "prep",
        max_candidates: int | None = None,
        genre_profile: str | None = None,
        remaining_bars: int | None = None,
        playhead_confidence: float | None = None,
        blend_active: bool = False,
        played_track_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Rank grounded section-to-section mix points. The source section or
        source track and every candidate_track_id must already be grounded by
        prior tools. Emits tr_* candidate ids with cue slots, score components,
        risk flags, and timing only when confidence allows it."""
        return toolset.transition_slate(
            {
                "source_section_id": source_section_id,
                "source_track_id": source_track_id,
                "candidate_track_ids": candidate_track_ids,
                "mode": mode,
                "max_candidates": max_candidates,
                "genre_profile": genre_profile,
                "remaining_bars": remaining_bars,
                "playhead_confidence": playhead_confidence,
                "blend_active": blend_active,
                "played_track_ids": played_track_ids,
            }
        )

    @mcp.tool()
    def compile_musical_context(
        candidate_ids: list[str],
        mode: str = "prep",
        intent: str | None = None,
        current: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Compile already-issued transition candidates into a bounded,
        redacted context packet. The agent may choose/explain only inside this
        packet; invented tr_* ids are rejected."""
        return toolset.compile_musical_context(
            {
                "candidate_ids": candidate_ids,
                "mode": mode,
                "intent": intent,
                "current": current,
            }
        )

    @mcp.tool()
    def smart_hot_cues(
        track_ids: list[str] | None = None,
        track_id: str | None = None,
        genre: str | None = None,
    ) -> dict[str, Any]:
        """Generate reviewable smart hot-cue proposals for discovered tracks.
        Emits proposal/cue ids; the agent may select ids but never raw cue
        payloads. Every track_id must come from search_vibe/discover_pool."""
        return toolset.smart_hot_cues(
            {"track_ids": track_ids, "track_id": track_id, "genre": genre}
        )

    @mcp.tool()
    def export_smart_cues(
        proposal_id: str,
        selected_cue_ids: list[str] | None = None,
        out_path: str | None = None,
        include_review: bool = False,
    ) -> dict[str, Any]:
        """Export selected cue ids from an issued smart-cue proposal.
        Preserves A-H slot numbers and rejects raw cue payloads or arbitrary
        track paths. The proposal must have been issued by smart_hot_cues."""
        return toolset.export_smart_cues(
            {
                "proposal_id": proposal_id,
                "selected_cue_ids": selected_cue_ids,
                "out_path": out_path,
                "include_review": include_review,
            }
        )

    @mcp.tool()
    def create_playlist(name: str, track_ids: list[str]) -> dict[str, Any]:
        """Persist the curated playlist (M3U + JSON). Every track_id must have
        come from a prior search_vibe/discover_pool result this run, or the
        call is rejected. Call once, with the tracks in play order. This ends
        the run."""
        return toolset.create_playlist({"name": name, "track_ids": track_ids})

    @mcp.tool()
    def request_clarification(question: str, choices: list[str]) -> dict[str, Any]:
        """Ask the user for disambiguation when the theme is materially ambiguous.

        Call this when the user theme is materially ambiguous and a single
        sensible default cannot be picked. Provide 2-5 specific choices that
        cover the disambiguation space. Examples of when to call:

          * "uplifting" — for whom? Provide choices like:
            ["bedroom-headphones", "peak-time-club", "festival-main-stage"]
          * BPM range when the brief is silent on tempo:
            ["slow (90-110)", "mid (118-128)", "fast (130-140)", "mixed"]
          * Mood register when "energetic" could mean many things:
            ["chill-energetic", "driving-energetic", "dark-energetic", "euphoric-energetic"]

        Calling this tool ends the current curation run. The CLI / Telegram
        surfaces render the question + numbered choices to the user, who then
        re-runs the command with the augmented theme. vibemix retains NO
        state across the clarification cycle (single-turn semantics) — this
        is a structured way to request human input, not a multi-turn
        dialogue.

        Constraints (validated at the toolset boundary; invalid args rejected
        without terminating the run):
          * ``question`` MUST be a non-empty string.
          * ``choices`` MUST be a list of 2-5 non-empty strings (0/1 = no real
            disambiguation; 6+ = choice paralysis per Hick's-law consensus).
        """
        return toolset.request_clarification({"question": question, "choices": choices})

    # -- set-prep tools (Vibe Mix engine; grounding identical to above) ----- #

    @mcp.tool()
    def get_track_energy(track_id: str) -> dict[str, Any]:
        """Deterministic perceived dancefloor energy (0-100), computed from the
        audio. Honest null when no file / undecodable. Reason about the energy
        arc with it — never invent an energy value."""
        return toolset.get_track_energy({"track_id": track_id})

    @mcp.tool()
    def discover_pool(
        query: str | None = None,
        ref_track_ids: list[str] | None = None,
        k: int = 50,
        bpm_min: float | None = None,
        bpm_max: float | None = None,
        min_duration_s: float | None = None,
        max_duration_s: float | None = None,
        exclude_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Build a diverse candidate POOL from the DJ's library for a vibe and/or
        reference tracks. A grounded discovery path like search_vibe — every
        track_id it returns may be sequenced/exported, none is invented."""
        return toolset.discover_pool(
            {
                "query": query,
                "ref_track_ids": ref_track_ids,
                "k": k,
                "bpm_min": bpm_min,
                "bpm_max": bpm_max,
                "min_duration_s": min_duration_s,
                "max_duration_s": max_duration_s,
                "exclude_ids": exclude_ids,
            }
        )

    @mcp.tool()
    def sequence_set(
        track_ids: list[str],
        curve: str,
        n_slots: int | None = None,
        novelty: float | None = None,
    ) -> dict[str, Any]:
        """Order grounded track_ids into a set following an energy CURVE preset
        (opener / peak_time / after_hours / festival). Returns 3-5 ranked
        candidates with energy_fit / avg_coherence / relaxed_transitions.
        Optional novelty 0..1 nudges toward lower-similarity deep cuts from the
        already-grounded discovery pool. Every track_id must come from a prior
        search_vibe/discover_pool result."""
        return toolset.sequence_set(
            {"track_ids": track_ids, "curve": curve, "n_slots": n_slots, "novelty": novelty}
        )

    if hasattr(toolset, "ingest_source"):

        @mcp.tool()
        def ingest_source(
            source: str = "auto",
            path: str | None = None,
            compute_key: bool = True,
            compute_bpm: bool = True,
        ) -> dict[str, Any]:
            """Import a DJ library or music folder into Viber's searchable library.

            source may be "auto", "folder", "rekordbox", "traktor", "serato",
            "virtualdj", or "engine". Pass path for an explicit collection.xml,
            collection.nml, Serato database V2, VirtualDJ database.xml,
            Engine m.db, or a raw music folder. The ingest is local/keyless and
            refreshes the loaded library so later search_vibe/discover_pool
            calls can use it."""
            return toolset.ingest_source(
                {
                    "source": source,
                    "path": path,
                    "compute_key": compute_key,
                    "compute_bpm": compute_bpm,
                }
            )

    @mcp.tool()
    def export_set(
        name: str,
        track_ids: list[str],
        out_path: str | None = None,
        cue: bool = True,
        target: str = "both",
        tag_write_granted: bool = False,
    ) -> dict[str, Any]:
        """Export the chosen ordered set to DJ-software handoff files.

        Default target "both" writes Rekordbox XML (order + key + BPM +
        VM-stamped auto cues) plus M3U8 (order-only crate for other DJ apps).
        Target "all" also writes Serato/Mixxx-compatible Markers2 tags.
        Serato/Mixxx tag targets require tag_write_granted=True because they
        mutate audio file tags.
        Every track_id must have come from a prior discovery result. Call once
        when the DJ accepts a set."""
        return toolset.export_set(
            {
                "name": name,
                "track_ids": track_ids,
                "out_path": out_path,
                "cue": cue,
                "target": target,
                "tag_write_granted": tag_write_granted,
            }
        )

    # -- DJ-knowledge / source capability tools (grounding identical above) -- #

    @mcp.tool()
    def web_search(query: str, k: int = 5) -> dict[str, Any]:
        """Web-search for DJ knowledge the library can't supply (track/label/
        artist facts, releases, scene context). Returns real {title, url,
        snippet, score} hits. Needs TAVILY_API_KEY. Cite the url — never present
        a snippet as established fact without it."""
        return toolset.web_search({"query": query, "k": k})

    @mcp.tool()
    def fetch_url(url: str) -> dict[str, Any]:
        """Fetch one page's readable text (a url from a prior web_search).
        Returns {url, title, text}. http(s) only. Read sources you cite —
        never invent page contents."""
        return toolset.fetch_url({"url": url})

    @mcp.tool()
    def quote_moment(
        track_id: str,
        start_s: float,
        end_s: float,
        label: str | None = None,
        caption: str | None = None,
    ) -> dict[str, Any]:
        """Point at a specific moment in a library track ("this is the breakdown
        I'm talking about") with a grounded, resolvable [start,end] reference.
        track_id must come from a prior search_vibe/discover_pool result."""
        return toolset.quote_moment(
            {
                "track_id": track_id,
                "start_s": start_s,
                "end_s": end_s,
                "label": label,
                "caption": caption,
            }
        )

    @mcp.tool()
    def retrieve_dj_knowledge(
        query: str,
        topic: str | None = None,
        skill_level: str | None = None,
        k: int = 4,
    ) -> dict[str, Any]:
        """Ground a DJ-technique answer with cited, link-out knowledge-base
        snippets (EQ-ing, phrasing, harmonic mixing). Never invent technique
        facts — honest empty when the knowledge base has no match."""
        return toolset.retrieve_dj_knowledge(
            {"query": query, "topic": topic, "skill_level": skill_level, "k": k}
        )

    @mcp.tool()
    def list_past_sessions(limit: int = 10) -> dict[str, Any]:
        """Enumerate the DJ's recorded vibemix sessions worth analyzing
        (boot-noise filtered: needs track changes + real duration). Returns
        session_id rows for analyze_past_set. Honest-empty when none."""
        return toolset.list_past_sessions({"limit": limit})

    @mcp.tool()
    def analyze_past_set(session_id: str) -> dict[str, Any]:
        """Retrospective read of one recorded session: track sequence, phase
        arc, mix-move timing, speak-gate reasons. Tape titles resolve against
        the live library (honest-null on miss); bpm/camelot are library joins,
        never tape facts. Resolved ids become grounded for follow-up tools."""
        return toolset.analyze_past_set({"session_id": session_id})

    @mcp.tool()
    def similar_tracks(track_id: str, k: int = 8) -> dict[str, Any]:
        """Find library tracks that SOUND like a grounded track_id (centered
        cosine + harmonic/tempo relation). The seed must be grounded this run
        (discovery, working set, or past-set resolution)."""
        return toolset.similar_tracks({"track_id": track_id, "k": k})

    return mcp


def _promote_arg_paths_to_env() -> None:
    """Promote side-channel paths passed as ARGS into ``os.environ``.

    Codex spawns this server with an explicit argv but does NOT forward the
    parent's process env to MCP children (boot-probe verified). So the live
    tool tape's path arrives as ``--vibemix-tool-events <path>`` and the
    cross-turn ground ledger's path as ``--vibemix-ground-ledger <path>``;
    both are promoted here, before the toolset is built, so the env-gated
    consumers (``LibraryToolset.dispatch``'s tape writer, the working-set
    seeding in ``main``) fire. ``setdefault`` lets a real env var (if one
    ever crosses) win. Unknown extra args are ignored — FastMCP never parses
    argv."""
    import os

    argv = sys.argv[1:]
    for flag, key in (
        ("--vibemix-tool-events", "VIBEMIX_TOOL_EVENTS_FILE"),
        ("--vibemix-ground-ledger", "VIBEMIX_GROUND_LEDGER_FILE"),
    ):
        if flag in argv:
            i = argv.index(flag)
            if i + 1 < len(argv):
                os.environ.setdefault(key, argv[i + 1])


def _seed_working_set_from_env(toolset: Any) -> None:
    """Seed the prior-turn working set (the ground ledger) into the toolset.

    The chat wrapper passes the ledger path as ``--vibemix-ground-ledger``
    (promoted to ``VIBEMIX_GROUND_LEDGER_FILE`` above) only when a continuing
    conversation has a validated working set. Persisted ids are HINTS:
    ``LibraryToolset.seed_working_set`` re-validates each one against the
    live library in THIS process and drops dead ids silently, so the seeded
    grounding surface can never be wider than the live store (Cardinal
    Invariant #2). Best-effort — continuity plumbing must never block the
    grounded tool surface from booting.
    """
    import os

    path = os.environ.get("VIBEMIX_GROUND_LEDGER_FILE", "").strip()
    if not path:
        return
    try:
        from vibemix.library.ground_ledger import load_working_set

        ids = load_working_set(path)
        seed = getattr(toolset, "seed_working_set", None)
        if not ids or not callable(seed):
            return
        survivors = seed(ids)
        if survivors:
            print(
                f"[viber-mcp] ground ledger seeded {len(survivors)}/{len(ids)} "
                "working-set ids (re-validated against the live library)",
                file=sys.stderr,
                flush=True,
            )
    except Exception:
        # A torn ledger or a surprise toolset shape degrades to "no memory",
        # never to a failed MCP boot.
        pass


def main() -> None:
    logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
    _promote_arg_paths_to_env()
    toolset = build_toolset()
    _seed_working_set_from_env(toolset)
    server = build_server(toolset)
    server.run()  # STDIO transport


if __name__ == "__main__":
    main()
