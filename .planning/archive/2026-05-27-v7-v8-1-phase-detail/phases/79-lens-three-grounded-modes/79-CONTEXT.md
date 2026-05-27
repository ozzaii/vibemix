# Phase 79: LENS — Three Grounded Modes - Context

**Gathered:** 2026-05-26
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous; grey areas auto-resolved with charter-recommended answers per Kaan's overnight authorization)

<domain>
## Phase Boundary

Make **hype / critique / tutor** three real grounded lenses over the SAME structured state — one being, three voices — NOT three separate brains. Switching lens changes voice/intent, never the underlying grounded facts. Lens selection is shared across the co-host and the curator (choose "tutor" once → flows to both). Every lens still passes the citation-grounding gate (invariant #2): a lens may change tone but cannot fabricate evidence; un-cited output strips to the ack-bank fallback regardless of lens.

- **LENS-01** — hype / critique / tutor exist as three grounded prompt lenses over the same structured state.
- **LENS-02** — lens selection is shared across co-host + curator surfaces.

**Out:** NO new AI/embedding provider, NO new ws ports, NO new IPC envelope, NO new evidence/grounding mechanics (lenses reuse the Phase-77 wired + Phase-78 deepened evidence). Additive — the existing default lens path stays byte-identical.
</domain>

<decisions>
## Implementation Decisions

### LENS-01 — three grounded lenses over the same state
- Introduce the three **canonical lens names**: `hype` (party hype-man), `critique` (coach — "what would've been better / what to fix"), `tutor` (teaches DJing through who YOU are — semantics, reality, taste).
- A lens is a **prompt variant** that reads the SAME structured evidence (wired grounding + deltas/trajectory/genre). It changes the *intent/voice framing*, not the facts. Implemented as an additive lens layer over the existing `prompts/matrix.py` persona seam.
- **Resolve the `critique` vs `coach` naming** (deferred from Phase-77 IN-02): `critique` is the canonical charter name; map it onto the existing matrix coach mode/mood additively (alias/lens-layer mapping) — do NOT rename the matrix internals in a way that breaks the v4 `build_system_instruction` golden. The lens layer is the canonical surface; matrix modes/moods are the substrate it maps onto.
- `tutor` is the genuinely new lens (matrix has no tutor mode yet) — add it as a grounded teaching voice that explains based on the DJ's taste/semantics/reality.

### LENS-02 — shared lens selection
- ONE shared lens-selection source of truth that BOTH surfaces read: the live co-host (`build_system_instruction` path) and the curator (`build_curator_instruction`, added in Phase 77). Choosing a lens once flows to both.
- Reuse the Phase-77 unified persona seam — extend it with lens selection rather than adding a second mechanism. No new ws port / IPC envelope; if a runtime selector is needed it rides the existing settings/skill bus.
- Default lens preserves current behavior (cold-path byte-identity): the default selection produces a prompt byte-identical to today's.

### Citation grounding per lens (invariant #2)
- Each lens output goes through the SAME citation-grounding gate. A lens cannot fabricate evidence; un-cited output strips to the ack-bank fallback regardless of lens. Pin this with a test that runs all three lenses through the gate.

### Claude's Discretion
- Exact lens→(mode,mood) mapping table, where the shared lens-selection state lives (profile vs a small shared module vs settings), and the lens enum/string representation — planner's call, smallest additive diff, follow `prompts/` + `profile/` conventions.
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `prompts/matrix.py` — `build_system_instruction` (co-host) + `build_curator_instruction` (curator, added Phase 77); `MOOD_PERSONAS`, `_CELLS`, existing modes (`hype`/`coach`) + moods (`hype-man`/`teacher`/`coach`). The v4 byte-identity golden must stay green.
- `coach/`, `prompts/`, `profile/` — persona/prompt templates per user level; long-term DJ profile (candidate home for shared lens selection).
- The Phase-77 shared persona seam — both surfaces already read one persona source; LENS-02 extends it with lens selection.
- `evidence_registry.py` + the citation-grounding gate (invariant #2) — un-cited reactions strip to ack-bank.

### Established Patterns
- Additive gated design; cold-path byte-identity (default lens == today's prompt); `from __future__ import annotations`.
- The persona/mood matrix is data-driven (`_CELLS`/`MOOD_PERSONAS`) — add lenses by extending the data + a mapping layer, not by forking the builder.

### Integration Points
- `prompts/matrix.py` (lens layer over the seam, both builders).
- The shared lens-selection state (profile/shared module) read by co-host + curator.
- The citation-grounding gate (per-lens grounding test).

### Verification reality
- Unit-testable WITHOUT the API (lens → prompt-shape assertions; all-three-lenses-through-the-gate; shared-selection flows to both builders; default-lens byte-identity). The "does each lens FEEL right / did the tutor teach well" judgment is Phase-81 BENCH (lens dimension) + Kaan's-ear (parked).
</code_context>

<specifics>
## Specific Ideas
- The three lenses are the charter's "SPEAKS IN THREE VOICES" faculty — one being, three lenses, same grounded perception. This is the emotional core: hype rides the party, critique coaches, tutor teaches through who you are.
- The bench (Phase 81) has an explicit **lens dimension** (hype/critique/tutor) — these lenses are what it benches.
</specifics>

<deferred>
## Deferred Ideas
- Gemini hearing the audio as a secondary ear → Phase 80.
- The multi-dimensional bench that tests lens-fidelity → Phase 81 (this phase builds the lenses; the bench measures them).
- Curator+co-host engine/taste unification → Phase 82 (this phase shares the lens *selection*; full engine unification is 82).
- A polished UI control to pick the lens — out unless trivially riding the existing settings bus; the phase goal is the grounded lenses + shared selection, not new UI.
</deferred>
