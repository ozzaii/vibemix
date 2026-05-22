# Phase 65: Memory Retrieval Seam (ANTI-SLOP RELEASE GATE) - Context

**Gathered:** 2026-05-22
**Status:** Ready for planning
**Mode:** Smart-discuss (autonomous `fully` — grey areas auto-resolved with recommended answers; no human pause). The cosine-vs-time-weight blend + decay half-life + exact recall threshold are intentionally LEFT for in-phase research/tuning per the ROADMAP flag (`/gsd:plan-phase --research-phase 65`); a **Kaan-ear veto** on retrieval relevance is the hard quality gate (mirrors the Phase 60 harmonic veto).

<domain>
## Phase Boundary

At reaction time, ground the coach prompt with **top-k past "moments"** retrieved from `memory.db` (Phase 63/64) — **citable-by-construction, fenced past-tense, subordinate to the live audio, and structurally anti-poisoning**. This is the **one** phase that touches the live reaction path, and it is the milestone's **anti-slop release gate**: the headline hallucination class is **retrieval poisoning** (an irrelevant past moment injected into the live prompt → the AI references something that didn't happen). The mitigation is **structural, not a prompt plea**.

What this phase delivers:
1. A new **existence-only `recall` evidence source** added to `EVIDENCE_SOURCES`, flowing through the **existing** `CitationLinter` with **ZERO new linter code** (à la the Phase 59 `key:` source) — each retrieved `record_id` is registered before the LLM call; a fabricated `[recall:<id>]` the registry never saw strips the whole turn.
2. A **gated `recall[…]` block** in `state/coach.py::evidence_line`, copying the Phase 59 `decks[…]` gate **verbatim** so the cold/empty-memory golden stays **byte-identical** (no "I don't remember anything" filler).
3. Retrieval wiring: embed the live query → `MemoryStore.query_topk(query_embedding, k, exclude_session=<current>)` → similarity-floor filter → past-tense fence → register record_ids → inject.

**Hard out-of-scope / deferred:**
- NO copilot move surfacing (Phase 66 builds the visible callbacks ON this seam).
- NO new ws port / IPC change (one-socket invariant; recall rides existing envelopes + the citation strip).
- NO new dependency, NO new linter code, NO LLM-extraction (retrieval reads raw stored signatures).
- The exact cosine-vs-time blend / half-life / threshold value = in-phase research + Kaan-ear tuning (ship conservative defaults).

</domain>

<decisions>
## Implementation Decisions

### Area 1 — Citability by construction (the anti-slop core)
- **`recall` is an existence-only evidence source** added to `EVIDENCE_SOURCES` (`src/vibemix/state/__init__.py` / wherever the set lives) and registered in the `EvidenceRegistry` exactly like `key:` (Phase 59) and `track:`/`aud:` etc. The retrieved `record_id`s are registered **before** the LLM call. A `[recall:<id>]` the registry never saw → the **existing** `CitationLinter` strips the **whole turn**. **ZERO new linter code** — reuse the binary response-level strip verbatim.
- The recall citation token format mirrors the existing sources (`[recall:<record_id>]`, where `record_id` is the Phase 63 `f"{session_id}:{seq}"`). Confirm the registry/linter regex (`EVIDENCE_CITATION_RE`) already matches this shape or extend the source list only (not the linter logic).

### Area 2 — The gated prompt block (byte-identical when cold)
- Add a **`recall[…]` block to `state/coach.py::evidence_line`**, **copying the Phase 59 `decks[…]` gate structure verbatim**: when there are no retrieved moments (cold / empty / all-below-floor), inject **nothing** — the prompt is **byte-identical** to the v5.0 baseline (a golden test pins this; empty retrieval is the correct, frequent state).
- Retrieved moments are fenced **PAST-tense**: an explicit **"FROM A PAST SESSION"** header so they can **never** be read as live evidence. The live audio/deck/now-playing evidence remains primary; recall is clearly subordinate.

### Area 3 — Retrieval policy (anti-poisoning by construction)
- **Top-k cap = 2–3** (one good callback beats ten weak ones).
- **Similarity floor ≈ 0.7** (mirror `CITATION_THRESHOLD`) — below floor → inject **nothing**. Exact value tuned in-phase on Kaan's real corpus (research flag).
- **Event-gated** to track-aware events (e.g. TRACK_CHANGE / PHASE / LAYER_ARRIVAL) — **never** HEARTBEAT. Reuse the existing event taxonomy / gate.
- **Current session excluded** from its own retrieval via the Phase 63 `query_topk(..., exclude_session=<current_session_id>)` parameter (already shipped, unused until now).
- **Cosine-only vs cosine+time-weight blend + decay half-life** (in *sessions*, not hours) is the in-phase tuning question — ship a conservative default (recommend: start cosine-only or a light two-term exp-decay with the relevance floor dominating) and let the Kaan-ear veto decide.

### Area 4 — Off-hot-path / budget / invariants / veto
- Retrieval stays **within the €50/mo budget**: event-gate + the Phase 64 signature embed cache + a **hard deadline** (late memory is worse than no memory — if retrieval misses the deadline, inject nothing). The live query embedding reuses `library/embed.py` (router-resolved, FLEX).
- **TTFT p95 unchanged feature-on vs feature-off** (the retrieval must not regress time-to-first-token; offload the embed+query, bound it).
- **Four cardinal invariants hold:** single-writer (retrieval never writes `MusicState`), citation-grounding (the `recall` source + linter), trust-the-audio (recall is subordinate, past-tense, floored), one-socket (no new port — recall surfaces on existing envelopes + the citation strip).
- **Kaan-ear veto** on retrieval relevance is the hard quality gate (mirrors the Phase 60 harmonic-clash veto): ships behind a flag so a callback that references a moment Kaan's ear says didn't matter can be vetoed. **Default posture (autonomous `fully`):** ship the seam wired + tested with conservative thresholds; the live-relevance veto flip + threshold/blend tuning are **KAAN-ACTION** (do not block engineering close).

### Claude's Discretion
- Exact module placement of the retrieval helper (a `recall`-builder in `state/coach.py` vs a sibling `memory/retrieval.py` that coach imports), the conservative default blend (cosine-only vs light decay), and the precise event-gate set — planner's discretion guided by the Phase 59 `decks[…]`/`key:` precedent and the event taxonomy. The retrieval helper must NOT import anything that breaks the single-writer/one-socket invariants.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets (the whole point — copy the Phase 59 shape)
- `src/vibemix/state/coach.py::evidence_line` — the Phase 59 `decks[…]` GATE + the `[key:…]` existence-only source (lines ~264/286/313). **Copy the `decks[…]` gate verbatim** for `recall[…]` → cold golden byte-identical.
- `src/vibemix/state/evidence_registry.py` — `EvidenceRegistry`; register `recall` record_ids before the LLM call (like `key:`).
- `src/vibemix/coach/citation_linter.py` — `CitationLinter` binary response-level strip; `recall` flows through it with ZERO new code.
- `src/vibemix/state/__init__.py` — `EVIDENCE_SOURCES` (add `recall`).
- `src/vibemix/memory/store.py` — `MemoryStore.query_topk(query_embedding, k, *, exclude_session=None)` (Phase 63 read seam; `exclude_session` shipped, unused until now) + `cosine_topk` ranking.
- `src/vibemix/library/embed.py` — `embed_query` for the live query embedding (router-resolved, FLEX, the budget-safe call).
- `CITATION_THRESHOLD` — mirror it for the ~0.7 recall similarity floor.

### Established Patterns
- Existence-only evidence source + `EvidenceRegistry` registration + `CitationLinter` whole-turn strip (Phase 59 `key:`) — the citability-by-construction pattern.
- Gated `evidence_line` block that injects nothing when empty → byte-identical cold golden (Phase 59 `decks[…]`).
- Conservative-default + Kaan-ear veto flag (Phase 60 harmonic clash).
- Event-gated reaction taxonomy (track-aware events).

### Integration Points
- READ: `MemoryStore.query_topk` (Phase 63) over the records `ingest.py` wrote (Phase 64).
- PROMPT: `coach.py::evidence_line` recall block.
- LINT: `CitationLinter` (existing) strips fabricated `[recall:…]`.
- SURFACE: Phase 66 builds the visible copilot callbacks on this seam (no new socket).

</code_context>

<specifics>
## Specific Ideas

- This is the milestone's hard hallucination gate: a poisoned memory footer is an existential, release-blocking failure for a product whose thesis is "no AI slop". Every retrieval decision is **structural** (floor / cap / event-gate / past-tense fence / current-session-exclusion / citable-by-construction), never a prompt plea.
- The cold/empty path MUST be byte-identical to v5.0 (golden test) — empty retrieval is the correct, frequent state, and the seam must add zero behavior when memory is cold.
- Anti-poisoning trio held by construction: below-floor → nothing; past-tense fence; current-session excluded.

</specifics>

<deferred>
## Deferred Ideas

- **Visible copilot moves** (transition-shape callback, vocabulary/register callback) → Phase 66 (built ON this seam).
- **Exact cosine-vs-time blend / half-life / threshold tuning + the live-relevance veto flip** → in-phase research + Kaan-ear pass (KAAN-ACTION; ship conservative defaults).
- **`audio_moment` retrieval** → future milestone (text-signature retrieval only in v6.0).

</deferred>
