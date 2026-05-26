# Requirements — v8.2 "Set Builder"

> Library-local (Mode A) DJ set-prep, wired into the Viber agent engine. Each requirement is
> user-centric, atomic, testable. Phases 83+. Source: Francesco's Vibe Mix spec, reconciled to
> vibemix's locked constraints (see `.planning/research/vibe-mix-agent-engine-synthesis.md`).

## v8.2 Requirements

### ENERGY — perceived-dancefloor-energy model
- [x] **ENERGY-01**: A DJ gets a 0-100 perceived-energy score for any track in their library, computed offline from the local audio file (reusing the existing hand-rolled DSP — `decode_to_mono` + band split + onset + crest — plus a new spectral-flux term), so that the energy curve in sequencing reflects how hard a track *hits the floor*, not just its loudness.
- [x] **ENERGY-02**: The energy score is genre-robust — a quiet hypnotic after-hours track does NOT read as low-energy, and a loud-but-sparse intro does NOT read as high (verified by a pairwise-ranking + hypnotic-regression unit test), so the curve is trustworthy across the DJ's whole crate.
- [x] **ENERGY-03**: Energy scores are cached by content hash (re-runs are free) and exposed through a `get_track_energy` agent tool that returns an honest null when a track has no decodable audio.

### DISCOVER — pool building (library-local)
- [x] **DISCOVER-01**: A DJ provides reference tracks and/or a text vibe prompt and gets a candidate pool from their OWN library, ranked by coherence with a single computed intent centroid (weighted multi-reference blend + α-blended text embedding) over the local mean-centered store.
- [x] **DISCOVER-02**: The pool is hard-filtered to what's actually mixable for tonight — BPM range, Camelot compatibility against the references, usable duration, recently-played exclusion, and explicit DJ excludes — then MMR-diversified so it is a varied pool, not 50 near-identical tracks.
- [x] **DISCOVER-03**: Discovery is exposed through a `discover_pool` agent tool whose every returned track_id flows through the grounding seen-set (Cardinal Invariant #2), so the agent can never sequence a track the discovery step didn't surface.

### SEQUENCE — energy-curved, harmonically-valid ordering
- [x] **SEQUENCE-01**: A DJ picks an energy-curve preset (opener / peak-time / after-hours / festival) or supplies a custom curve, and the candidate pool is ordered into an N-slot set that follows that curve (curve parameterized by normalized set-position so it works for any set length).
- [x] **SEQUENCE-02**: Every transition in the produced set is technically valid — harmonically compatible (Camelot same/±1/relative) and BPM within ±6% — degrading gracefully when a track is missing key/BPM (never dropped for missing metadata), with any relaxed transition tagged honestly (e.g. "BPM jump here"), never silently fabricated.
- [x] **SEQUENCE-03**: Sequencing returns 3-5 ranked, genuinely-different candidate sets (Jaccard-diverse) each with honest fit labels (energy fit, average coherence) for DJ optionality, exposed through a `sequence_set` agent tool.

### EXPORT — one-click to Rekordbox
- [x] **EXPORT-01**: A DJ exports a sequenced set to a Rekordbox-importable XML file in one action, and on import into Rekordbox the playlist appears with track ORDER preserved plus per-track key/BPM/genre/colour/rating and memory + hot cues + beatgrid.
- [x] **EXPORT-02**: Internal Camelot keys are converted deterministically to classical notation for Rekordbox's `Tonality` field (`harmonics.to_classical`, honest-null on unknown), and export is exposed through an `export_set` agent tool + a `vibemix library export-set` CLI command.

### AGENT — the set-prep co-host flow
- [x] **AGENT-01**: A DJ can ask the co-host (CLI `vibemix library build-set "<brief>"`, Gemini agent) to build a full set from a natural-language brief; the agent discovers → sequences → and explains in 1-2 sentences why each critical transition works (key/BPM/energy/vibe), acting as a mentor rather than a black box, with every track grounded (never invented).
- [x] **AGENT-02**: The set-prep flow reuses the existing bounded, no-hang agent harness (iteration cap, per-call + per-tool timeouts, handlers return errors never raise) and the shared persona/lens seam, so it can never wedge and its voice matches the co-host's.

### UI — "Build a Set" path
- [ ] **UI-01**: The app exposes a "Build a Set" path (brief input + energy-curve preset picker → a sequenced result list showing each slot's track, key/BPM/energy, and the per-transition reasoning → an Export-to-Rekordbox button) in the CDJ-Whisper aesthetic.
- [ ] **UI-02**: Every control in the "Build a Set" path works live end-to-end (verified in the real `cargo tauri dev` app via `ui.log`, not just green vitest), with no dead/no-op buttons, and the result is a downloaded Rekordbox file + clear next-step instructions.

## Future Requirements (deferred — later vibemix milestones)
- XGBoost learned energy regressor (the 7-feature vector is kept as its future input → swap the linear combiner for a trained model with zero re-extraction).
- Serato (binary GEOB via `serato-tools`) and Engine DJ (SQLite) export — Rekordbox proves the value first.
- Cue-anchored sequencing/export consuming the staged `CueAnchor` contract once it lands (structural mixability beyond the v1 placeholder).
- Live in-session "build the rest of tonight from here" (the set-prep flow seeded by the live now-playing track).

## Out of Scope (explicit — DEFER to Bravoh commercial / never in OSS)
- **Public catalog** (Beatport / Spotify / SoundCloud APIs), external discovery (Modes B/C), purchase deep-links, affiliate revenue — network catalog + monetization is the Bravoh commercial product, not the local OSS utility.
- **Fingerprinting** (Chromaprint / AcoustID) — only needed to inherit public-catalog embeddings, which are out of scope.
- **1001Tracklists / Mixcloud scraping** energy "moat" — scraping + proprietary-dataset IP is commercial Bravoh work.
- **Non-Gemini LLM** (the spec names Claude Sonnet for reasoning) — vibemix is Gemini-only; reasoning is the existing Gemini agent.
- **Mem0 / managed memory frameworks** — rejected; recency uses the local store / played-ids.
- **New heavy deps** (essentia = AGPL poison; librosa unnecessary; torch/Pinecone/pgvector) — pure-compute over the existing numpy/scipy + ffmpeg stack only.

## Traceability
> Each v8.2 REQ-ID maps to exactly one phase (100% coverage, no orphans, no duplicates). Phases continue from v8.1 (77–82) — start at 83, no reset.

| Requirement | Phase | Status |
|-------------|-------|--------|
| ENERGY-01 | Phase 83 — ENERGY | Done |
| ENERGY-02 | Phase 83 — ENERGY | Done |
| ENERGY-03 | Phase 83 — ENERGY | Done |
| DISCOVER-01 | Phase 84 — DISCOVER | Done |
| DISCOVER-02 | Phase 84 — DISCOVER | Done |
| DISCOVER-03 | Phase 84 — DISCOVER | Done |
| SEQUENCE-01 | Phase 85 — SEQUENCE | Done |
| SEQUENCE-02 | Phase 85 — SEQUENCE | Done |
| SEQUENCE-03 | Phase 85 — SEQUENCE | Done |
| EXPORT-01 | Phase 86 — EXPORT | Done |
| EXPORT-02 | Phase 86 — EXPORT | Done |
| AGENT-01 | Phase 87 — AGENT | Done |
| AGENT-02 | Phase 87 — AGENT | Done |
| UI-01 | Phase 88 — UI | Pending |
| UI-02 | Phase 88 — UI | Pending |

**Coverage:** 13/13 mapped ✓ — no orphans, no duplicates.

**Dependency spine:** (P83 ENERGY ∥ P84 DISCOVER, independent) → P85 SEQUENCE (needs DISCOVER pool + optionally ENERGY curve fidelity; degrades to BPM proxy) ‖ P86 EXPORT (independent of SEQUENCE internals) → P87 AGENT (orchestrates the three tools) → P88 UI (consumes the AGENT/CLI surface).
