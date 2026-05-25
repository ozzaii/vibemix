# vibemix — Requirements (v8.1 "One Mind")

**Milestone:** v8.1 "One Mind" — Phases 77+
**Goal:** Connect vibemix's disconnected islands into ONE grounded product — *"an AI that hears music with you, and gets you."* The DSP/MIDI/embedding stack is the **EAR** (structured state + multi-scale trajectory + the DJ's moves + genre); Gemini is the taste/culture **VOICE**; a shared **taste layer** + **three lenses** (hype/critique/tutor) span both surfaces (live co-host + library curator).
**Mode:** `gsd-autonomous fully`. Blockers (Gemini billing — resolved; any live-hardware ear-pass) ride forward to KAAN-ACTION — they never block.
**Charter:** `.planning/research/one-mind-charter.md`. Research: `connection-map.md` · `genre-from-embeddings.md` · `gemini-audio-truth-test.md` · `gsd-operational-playbook.md`.

**Anti-creep acid test (v8.1):** *"Does this CONNECT an existing-but-orphaned capability into the one grounded product, or make the grounded reaction measurably deeper / less-slop — WITHOUT adding a new AI/embedding provider, a new MIR library, a new ws port, or a new IPC envelope?"* If not, defer. Gemini-only holds. No CLAP/MERT/OpenL3/torch; no Mem0/Letta/Zep/Cognee.

**Why this milestone (empirical):** 3 frontier models returned 3 different genres for one track (raw-audio bench floor) → Gemini's raw ear is not reliable; ground it. Genre-from-embeddings hit **86.5%** nearest-prototype accuracy at **€0** (cached vectors). The "shallowness" is a wiring gap + mis-asking Gemini to perceive, not a model limit.

---

## v8.1 Requirements

### WIRE — connect the islands
- [ ] **WIRE-01**: The live co-host's reactions are grounded by the audio→library Grounding engine (passed into `DJCoHostAgent`), so it references what is actually playing.
- [x] **WIRE-02**: The 8 genre-chain detectors surface their measured evidence to the prompt and register in the `EvidenceRegistry` (shipped `ccf4930`).
- [x] **WIRE-03**: `detected_genre` is surfaced in the prompt evidence, confidence-gated against hallucination (shipped `a9979b8`).
- [ ] **WIRE-04**: The hype/critique/tutor persona is shared across the live co-host and the library curator (curator stops hardcoding its voice).
- [ ] **WIRE-05**: `memory.db` ingest runs on the live `main()` path so recall personalization works in a real session.
- [ ] **WIRE-06**: The app loads its API key without a stale shell env var shadowing `.env` (override the ghost key, or clear it).

### PERCEIVE — deeper, generalized ear (no new DSP, no MIR libs)
- [ ] **PERCEIVE-01**: Prompt evidence carries deltas + calibrated confidence per fact (not raw absolute scalars), so Gemini reads changes and can abstain.
- [ ] **PERCEIVE-02**: The prompt carries a multi-scale trajectory (phrase / energy-arc / recent-moves) so Gemini reasons over time, not a single snapshot.
- [ ] **PERCEIVE-03**: `detected_genre` is driven by a mean-centered nearest-prototype lookup over cached embeddings (86.5%-validated, €0).

### LENS — three modes
- [ ] **LENS-01**: hype / critique / tutor exist as three grounded prompt lenses over the same structured state.
- [ ] **LENS-02**: Lens selection is shared across the co-host and curator surfaces.

### GROUND — Gemini as secondary ear
- [ ] **GROUND-01**: The audio part is fed to Gemini alongside the structured evidence, hallucination-guarded.
- [ ] **GROUND-02**: The reaction model is config-resolved via `model_router` and chosen by the bench result.

### BENCH — validation instrument
- [ ] **BENCH-01**: A multi-dimensional bench harness runs model × grounding × prompting × contexting × lens × taste on real tracks.
- [ ] **BENCH-02**: An automated first-pass eval scores groundedness (vs DSP facts), specificity, and mode-fidelity per cell.
- [ ] **BENCH-03**: Bench cells are surfaced for Kaan's-ear final judgment (KAAN-ACTION review surface).

### CURATE — unify curator + co-host
- [ ] **CURATE-01**: Curator and co-host share the perception engine + the structured-state contract.
- [ ] **CURATE-02**: Curator and co-host share the taste layer + persona.

---

## Future Requirements (deferred)
- ONNX-exported local semantic tagger — ONLY if the bench proves Gemini's ear insufficient AND a permissively-licensed model exists.
- Set-prep / sequencing (the €4.99 Pro feature) once the core engine is unified.
- Gemini live-audio (`native-audio` Live API) path — separate from `generate_content`; out until the bench justifies it.

## Out of Scope (explicit)
- New DSP detectors / MIR libraries (madmom / aubio / Essentia / KeyFinder — GPL/AGPL/NC license wall vs Apache-2.0 + Bravoh commercial reuse).
- New AI / embedding providers (Gemini-only, locked).
- New ws ports / IPC envelopes / managed-memory frameworks.
- The reaction-path rewrite — the four cardinal invariants hold by additive design.

---

## Traceability

(filled by roadmap — every REQ-ID maps to exactly one phase; WIRE-02 + WIRE-03 already satisfied via `ccf4930` + `a9979b8`)
