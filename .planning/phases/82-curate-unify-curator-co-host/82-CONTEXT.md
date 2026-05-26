# Phase 82: CURATE — Unify Curator + Co-Host - Context

**Gathered:** 2026-05-26
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous; grey areas auto-resolved with charter-recommended answers per Kaan's overnight authorization)

<domain>
## Phase Boundary

Close the diamond — the library/Viber **curator** and the live **co-host** become two facets of one mind, sharing ONE perception engine + structured-state contract (CURATE-01) and ONE taste layer + persona/lens (CURATE-02). The curator can curate "for this DJ"; the co-host can lean on what the DJ's library says about their taste. Covers BOTH curator backends — gemini (`library/agent.py`) and codex (`library/codex_curate.py` + `library/mcp_server.py`) — plus the Telegram + `next_suggestion` transports; nothing orphaned.

- **CURATE-01** — curator + co-host share the perception engine + structured-state contract: both read ONE "what is true about this music/track" representation, not two parallel ones.
- **CURATE-02** — curator + co-host share the taste layer + persona: the long-term DJ profile + the hype/critique/tutor lens reach both surfaces.

**Out:** NO new AI/embedding provider (Gemini-only); NO new ws port; NO new IPC envelope; single-writer `MusicState` untouched (invariant #1). Additive — the existing `library curate` / Telegram CLI surfaces keep working; the four cardinal invariants hold. **Ship, don't over-engineer:** the unification is CONCRETE shared wiring (a module both surfaces import), not an abstract rewrite.
</domain>

<decisions>
## Implementation Decisions

### CURATE-01 — shared perception engine + structured-state contract
- The shared perception bridge is the **Phase-78 `library/genre_prototypes.py`** (mean-centered nearest-prototype over the cached library embeddings) + the library's per-track features (key/BPM/energy/vibe-embedding). It already serves the co-host's `detected_genre`; expose it as the ONE perception representation the curator's grounded core (`library/toolset.py`) also reads — so both surfaces share "what is true about this track", not two parallel notions.
- Define/affirm a small **structured-state contract** (the shared track-perception shape both conform to) so the curator and co-host read one representation. Reuse the existing dataclasses where possible (don't invent a parallel one).
- The co-host can QUERY the library's taste representation (what the DJ's library says about their taste); the curator can curate "for this DJ" by reading the same profile/perception. Concrete, additive — no new provider, no new port.

### CURATE-02 — shared taste layer + persona/lens
- The **taste layer** = the long-term DJ **`profile/`** (the DJ profile) + the Phase-81 `TASTE_RUBRIC` seam. Both the curator and the co-host read the shared profile/taste — so "what this DJ likes / what clicked" is one source feeding both.
- The **persona/lens** is ALREADY shared (Phase 79: `build_lens_instruction` + `ConfigStore.extra["lens"]`, read by both `build_system_instruction` and `build_curator_instruction`). This phase confirms it reaches BOTH curator backends + the transports, and adds the profile/taste sharing on top.

### Additive / invariants (CURATE SC #3)
- The existing `library curate` + Telegram + `next_suggestion` (pill) surfaces keep working unchanged — pin them with a regression test.
- No new ws port (one socket, invariant #4); no new IPC envelope; single-writer `MusicState` untouched (invariant #1); citation grounding holds (invariant #2).
- Both curator backends (gemini + codex) + transports reach the shared perception + taste + lens — neither orphaned (the CURATE acid test).

### Claude's Discretion
- The exact shared-contract module location + shape (reuse vs a thin shared interface over existing dataclasses), whether the co-host's library-taste query is a new helper or reuses an existing `library/` entrypoint, how the profile is surfaced to the curator — planner's call after research maps the real seams, smallest additive diff, ship-not-over-engineer.
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `library/toolset.py` — the shared grounded tool core driving BOTH curator backends (gemini `agent.py` + codex `codex_curate.py`/`mcp_server.py`); the home of the curator's perception/grounding.
- `library/genre_prototypes.py` (Phase 78) — mean-centered nearest-prototype genre over the cached library embeddings; already feeds the co-host's `detected_genre` — the natural shared perception bridge.
- `library/` embedding store (`library.db`, 1536-dim) + `next_suggestion.py` (the pill engine) + `telegram_bridge.py` (mobile transport).
- `profile/` — the long-term DJ profile (the taste layer's home).
- `prompts/matrix.py` `build_lens_instruction` + `ConfigStore.extra["lens"]` (Phase 79 — persona/lens ALREADY shared across both surfaces).
- `bench/matrix.py` `TASTE_RUBRIC` (Phase 81 — the taste-rubric seam; Kaan authors the wording).
- `state/music_state.py` `MusicState` (the live structured state — the co-host side of the contract).

### Established Patterns
- Gemini-only; additive gated design; single-writer `MusicState`; one socket; the shared-seam pattern (Phase 77/79 — one source both surfaces read); lazy imports to respect the memory storage-spine import boundary (Phase-77 `test_no_live_path_import`).

### Integration Points
- `library/toolset.py` ↔ `library/genre_prototypes.py` (shared perception); `profile/` ↔ both surfaces (shared taste); the Phase-79 lens seam (already shared) ↔ both backends + transports.

### Verification reality
- Unit-testable WITHOUT the API: both surfaces import the ONE perception/contract module (no parallel duplicate); both read the shared profile/taste + lens; the existing curate/Telegram/pill surfaces still work (regression); invariants hold (no new port/envelope, single-writer untouched). The "does curating-for-this-DJ / co-host-leaning-on-library actually feel personal" judgment is a KAAN-ACTION live item (parked).
</code_context>

<specifics>
## Specific Ideas
- This closes the milestone's thesis: ONE product = two surfaces sharing ONE engine + ONE taste layer + THREE lenses. After 77 (wire) → 78 (deepen) → 79 (lens) → 80 (ground) → 81 (prove), this is where the curator and co-host stop being islands and become one mind.
- "Curate for this DJ" + "co-host leans on the library's taste" = the emotional payoff — the AI that hears music WITH you AND gets you, across both surfaces.
- Ship-not-over-engineer is paramount here: resist a grand abstraction. The win is the concrete shared module(s) + the regression proving both surfaces read one source.
</specifics>

<deferred>
## Deferred Ideas
- The felt "does it curate like it knows me" judgment → KAAN-ACTION live (parked).
- Acting on the Phase-81 bench verdict (winning arch/model) → KAAN-ACTION (Phase 81's gate).
- Set-prep / sequencing (the €4.99 Pro feature) → Future Requirements (after the engine is unified).
- Any new transport / surface → out (the unification reaches the EXISTING surfaces; no new ones).
</deferred>
