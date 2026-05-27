# Phase 78: PERCEIVE — Deeper, Generalized Ear - Context

**Gathered:** 2026-05-26
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous; grey areas auto-resolved with charter-recommended answers per Kaan's overnight authorization)

<domain>
## Phase Boundary

Make the *existing* ear speak in **change, not snapshots** — without adding any new DSP detector or MIR library. Three additive enrichments to the single-writer `MusicState` → prompt evidence:

- **PERCEIVE-01** — each prompt fact carries a **delta from prior** + a **calibrated per-fact confidence**, so Gemini reads "kick density rose 18%" instead of a bare scalar, and can **abstain** when confidence is low.
- **PERCEIVE-02** — a **multi-scale trajectory** (phrase position / energy-arc / recent DJ moves) so a reaction can reference where the set has *been* and is *going*, not just the current bar.
- **PERCEIVE-03** — `detected_genre` driven by a **mean-centered nearest-prototype cosine** lookup over cached library embeddings (86.5%-validated, €0), confidence-floored.

**Out:** NO new DSP detectors, NO MIR libs (madmom/aubio/Essentia/KeyFinder — license wall), NO new embedding/AI provider, NO new ws ports. The cold path (signal below confidence floor / trajectory not yet warm) must be **byte-identical** to the v8.0 baseline.
</domain>

<decisions>
## Implementation Decisions

### PERCEIVE-01 — deltas + calibrated confidence
- The evidence packet is extended **additively**: each surfaced fact gains a delta-from-prior and a calibrated confidence. Raw scalars are NOT removed (other consumers may read them); the *prompt rendering* prefers the delta phrasing.
- Display is **confidence-gated**: facts below a floor are omitted/abstained rather than asserted (anti-slop, invariant #2/#3 spirit).
- Delta computation reads the prior `MusicState` snapshot; the single-writer refresh loop owns the write (invariant #1). No second writer.

### PERCEIVE-02 — multi-scale trajectory
- A rolling trajectory is maintained in `MusicState` across scales: bar → phrase → track → set, plus a short **recent-moves** list (MIDI/EQ/fader/blend events already detected).
- Surfaced to the prompt as a **compact narrative string** (e.g., "3rd phrase of an energy build; last move: bass-swap 20s ago"), not a raw array dump.
- Written ONLY by the refresh loop (invariant #1). Bounded ring/window — no unbounded growth.

### PERCEIVE-03 — mean-centered nearest-prototype genre
- Build a **genre-prototype table** from the existing cached 1536-dim library embeddings (mean of each genre cluster).
- `detected_genre` = nearest prototype by **mean-centered cosine** (query-side centering only — the anisotropy fix; persisted vectors untouched). €0 (cached vectors, no new API calls).
- The lookup **feeds the single-writer refresh loop's `detected_genre`/`genre_confidence`** (already fields in `music_state.py:55-56`) — it does NOT introduce a second writer. Confidence-floored: never assert a genre the audio/embedding doesn't support.
- This augments (not replaces wholesale) the existing genre-chain detector path; reconcile so there's one coherent `detected_genre` source per refresh tick.

### Claude's Discretion
- Exact delta/confidence struct shape, calibration function (e.g., logistic over normalized distance), trajectory window sizes, prototype-table storage location (cache under `~/.cache/vibemix/`) — planner's call, smallest additive diff, follow `state/` + `library/` conventions.
- Whether prototype table is precomputed once + cached vs lazy-built on first genre query.
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `state/music_state.py` — `MusicState` single source of truth; already has `detected_genre` (str) + `genre_confidence` (float) at ~lines 55-56.
- `state/refresh.py` — the ONLY writer of `MusicState` (invariant #1); trajectory + genre writes must live here.
- `state/coach.py` — `evidence_line` / `task_for_event` build the prompt evidence (the Phase-77 wired surface this enriches).
- `state/event_detector.py` — emits typed events with cooldowns; recent-moves source for trajectory.
- `library/` — cached 1536-dim Gemini embeddings (`library.db` sqlite-vec) + `library_centroid.npy` (already a cached query centroid — the mean-centering precedent). Genre-from-embeddings research validated 86.5% at €0.
- The genre-from-embeddings research report: `.planning/archive/2026-05-27-stale-one-mind-research/genre-from-embeddings.md` (mean-centering is decisive: raw avg cosine 0.78 → centered 0.06).

### Established Patterns
- Single-writer discipline; additive gated design; cold-path byte-identity; `from __future__ import annotations`; numpy for DSP/vector math (no torch).
- Query-side mean-centering already used for library ranking (anisotropy fix) — persisted vectors never mutated.

### Integration Points
- `refresh.py` state-refresh loop (trajectory + genre single-writer).
- `coach.py` evidence rendering (delta/confidence phrasing + trajectory narrative + genre).
- `library/` embedding store + centroid cache (prototype table source).

### Verification reality
- Unit-testable WITHOUT the API (genre prototypes from cached vectors = €0; deltas/trajectory from synthetic MusicState sequences). Live-set "does it feel deeper" is a Phase-81 BENCH + Kaan's-ear item (parked).
</code_context>

<specifics>
## Specific Ideas
- The mean-centering is the quality unlock (per memory + research) — without it nearest-prototype is near-useless (anisotropy). Centering must be query-side.
- "Speak in change" = the core fix for the shallowness Kaan felt: Gemini interprets deltas/trajectory well (its strength), but was fed bare snapshots.
</specifics>

<deferred>
## Deferred Ideas
- The three lenses (hype/critique/tutor) interpreting this deepened evidence → Phase 79.
- Gemini hearing the audio as a secondary ear → Phase 80.
- Proving the depth measurably (bench) + Kaan's-ear verdict → Phase 81.
- Any NEW DSP detector or MIR lib — permanently out (license wall + scope).
</deferred>
