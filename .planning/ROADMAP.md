# vibemix — Roadmap

**Project:** vibemix — AI DJ Co-Host
**Last shipped:** v8.0 "Proof & Polish" — 2026-05-25 (tech_debt accepted; KAAN-ACTION §GH-BILLING / §GH-MAIN-MERGE / §SHIP-V4 / §V7-LIVE ride forward on Kaan's clock)
**Current milestone:** v8.1 "One Mind" — IN PROGRESS (Phases 77–82; started 2026-05-25) — connect the disconnected islands into ONE grounded product; `gsd-autonomous fully`
**Open alongside:** v4.0 "SHIP" — engineering-complete (8/8), publish gated on the external Apple Dev + SignPath signature clock (NOT archived) — **v7.0's OSS-04 discharges §SHIP-V4 for real; v4.0 closes alongside when the real cut fires**

---

## Milestones

- ✅ **v0.1.0 MVP Foundation** — Phases 1–14 (shipped 2026-05-13) — see `.planning/milestones/v0.1.0/`
- ✅ **v2.0 Research-Driven Ship** — Phases 15–26 (shipped 2026-05-14, tech_debt accepted) — see `.planning/milestones/v2.0-ROADMAP.md`
- ✅ **v2.1 The Unified Cut** — Phases 27–39 (shipped 2026-05-16, tech_debt accepted) — see `.planning/milestones/v2.1-ROADMAP.md`
- ✅ **v3.0 Clean OSS Ship** — Phases 40–45 (shipped 2026-05-17, tech_debt accepted) — see `.planning/milestones/v3.0-ROADMAP.md`
- ✅ **v3.1 Distribution-Ready Pass** — Phases 46–50 (shipped 2026-05-18, tech_debt accepted) — see `.planning/milestones/v3.1-ROADMAP.md`
- 🟡 **v4.0 SHIP** — Phases 51–58 (engineering-complete 8/8, publish on signature clock — NOT archived; closes alongside v7.0 OSS-04) — see `.planning/milestones/v4.0-ROADMAP.md`
- ✅ **v5.0 The Useful Cut** — Phases 59–62 (shipped 2026-05-22, tech_debt accepted) — see `.planning/milestones/v5.0-ROADMAP.md`
- ✅ **v6.0 The Memory Turn** — Phases 63–66 (shipped 2026-05-23, tech_debt accepted) — see `.planning/milestones/v6.0-ROADMAP.md`
- ✅ **v7.0 Open House** — Phases 67–70 (shipped 2026-05-24, tech_debt accepted) — see `.planning/milestones/v7.0-ROADMAP.md`
- ✅ **v8.0 Proof & Polish** — Phases 71–76 (shipped 2026-05-25, tech_debt accepted) — *this file, below* · audit `.planning/v8.0-MILESTONE-AUDIT.md`
- 🔨 **v8.1 One Mind** — Phases 77–82 (IN PROGRESS, started 2026-05-25) — *this file, below* · charter `.planning/research/one-mind-charter.md`

---

# v8.1 "One Mind" — IN PROGRESS (started 2026-05-25)

**Goal:** Connect vibemix's disconnected islands into ONE grounded product — *"an AI that hears music with you, and gets you."* The shallowness isn't a Gemini limit; it's a **wiring gap** + asking Gemini to be the ear. Make the DSP/MIDI/embedding stack the **EAR** (structured state + multi-scale trajectory + the DJ's moves + genre), Gemini the taste/culture **VOICE**, with a shared **taste layer** and **three lenses** (hype / critique / tutor) across both surfaces (live co-host + library curator).

**Anti-creep acid test (v8.1):** *"Does this CONNECT an existing-but-orphaned capability into the one grounded product, or make the grounded reaction measurably deeper / less-slop — WITHOUT adding a new AI/embedding provider, a new MIR library, a new ws port, or a new IPC envelope?"* If not, defer. Gemini-only holds. No CLAP/MERT/OpenL3/torch; no Mem0/Letta/Zep/Cognee.

**Hard constraints (locked, encoded in every phase):**
- **Ship, don't over-engineer** — each phase ships ONE connected, tested wire (the DSP rabbit-hole was the lesson).
- **Gemini-only** AI provider; **no new MIR libraries / no new DSP detectors** (GPL/AGPL/NC license wall vs Apache-2.0 + Bravoh reuse); no new ws ports; no new IPC envelopes; no managed-memory frameworks.
- **Four cardinal invariants hold by ADDITIVE design** (single-writer · citation-grounding · trust-the-audio · one-socket) — the gated-off cold path stays **byte-identical** to the v8.0 baseline.
- **Honest green** — unit-testable without the API; live e2e on the funded key (`...32u744`, project 709533190790). Never fake results.
- **`gsd-autonomous fully`** — blockers (Gemini billing — resolved; any live-hardware ear-pass) ride forward to KAAN-ACTION; never pause.

**Empirical grounding:** 3 frontier models returned 3 different genres for one track (raw-audio bench floor) → Gemini's raw ear isn't reliable; ground it. Genre-from-embeddings hit **86.5%** nearest-prototype accuracy at **€0** (cached vectors). An env-var ghost key shadowing `.env` was found + fixed (WIRE-06).

**Charter + research:** `.planning/research/one-mind-charter.md` · `connection-map.md` (top-5 wires, file:line) · `genre-from-embeddings.md` (the 86.5% win) · `gemini-audio-truth-test.md` (floor data) · `gsd-operational-playbook.md`.

**Dependency spine:** P77 (WIRE — connect the islands; the grounding→agent wire is highest leverage) → P78 (PERCEIVE — deltas/confidence/trajectory/genre-prototype, riding on the wired evidence) → P79 (LENS) ‖ P80 (GROUND) [both build on the wired+deepened prompt] → P81 (BENCH — the instrument that benches model × grounding × prompting × contexting × lens × taste; depends on GROUND + LENS being in place to bench them) → P82 (CURATE — unify curator + co-host on the proven shared engine / taste / lens).

## Phases

- [ ] **Phase 77: WIRE — Connect the Islands** — Grounding→live agent + persona/lens unify + memory ingest on live path + env-key override fix (WIRE-02/03 already shipped).
- [ ] **Phase 78: PERCEIVE — Deeper, Generalized Ear** — deltas + calibrated confidence + multi-scale trajectory + mean-centered genre-prototype lookup (no new DSP, no MIR libs). **4 plans, 3 waves.**
- [ ] **Phase 79: LENS — Three Grounded Modes** — hype / critique / tutor as prompt lenses over one structured state, lens selection shared across surfaces.
- [ ] **Phase 80: GROUND — Gemini as Secondary Ear** — audio part fed alongside structured evidence, hallucination-guarded; reaction model config-resolved by the bench.
- [ ] **Phase 81: BENCH — The Validation Instrument** — multi-dimensional bench (model × grounding × prompting × contexting × lens × taste) + auto first-pass eval + Kaan's-ear review surface.
- [ ] **Phase 82: CURATE — Unify Curator + Co-Host** — both surfaces share the perception engine + structured-state contract + taste layer + persona.

| # | Phase | Goal | REQ-IDs | SC count |
|---|-------|------|---------|----------|
| 77 | WIRE — Connect the Islands | 4/4 | Complete    | 2026-05-25 |
| 78 | PERCEIVE — Deeper, Generalized Ear | 4/4 | Complete    | 2026-05-26 |
| 79 | LENS — Three Grounded Modes | 2/3 | In Progress|  |
| 80 | GROUND — Gemini as Secondary Ear | Gemini hears the audio alongside the structured evidence, hallucination-guarded, with the reaction model config-resolved | GROUND-01, GROUND-02 | 3 |
| 81 | BENCH — The Validation Instrument | A multi-dimensional bench runs the architecture/model axes on real tracks, auto-scores each cell, and surfaces cells for Kaan's-ear final judgment | BENCH-01, BENCH-02, BENCH-03 | 4 |
| 82 | CURATE — Unify Curator + Co-Host | Curator and co-host are two facets of one engine — shared perception/state contract + shared taste/persona | CURATE-01, CURATE-02 | 3 |

## Phase Details

### Phase 77: WIRE — Connect the Islands
**Goal:** Turn the strongest islands into one grounded mind — the live co-host references what is actually playing (via the already-armed-but-orphaned Grounding engine), both surfaces speak with one persona/lens, the recall store actually fills on a real session, and the app loads its API key without a ghost env var shadowing `.env`.
**Depends on:** Nothing (first v8.1 phase). Builds additively on the v8.0 reaction path.
**Requirements:** WIRE-01, WIRE-02 (✅ shipped `ccf4930` — NO new work), WIRE-03 (✅ shipped `a9979b8` — NO new work), WIRE-04, WIRE-05, WIRE-06
**Success Criteria** (what must be TRUE):
  1. On a track-aware event, the live co-host cites the actual track from `library.db` — `DJCoHostAgent` now takes a `grounding` kwarg, the armed `Grounding` object is passed in, and `identify_playing` injects a `[track:<id>]` citation that survives the citation-grounding gate (WIRE-01).
  2. The 8 genre-chain detectors' measured evidence appears in the prompt and registers in `EvidenceRegistry` (WIRE-02 — already TRUE via `ccf4930`; pinned by a regression test, no new work), and `detected_genre` is surfaced confidence-gated in the prompt evidence (WIRE-03 — already TRUE via `a9979b8`; pinned, no new work).
  3. The hype/critique/tutor persona is resolved from `prompts/matrix.py` by BOTH the live co-host and the library curator — `ViberAgent` stops hardcoding `_SYSTEM_INSTRUCTION` and reads a curator-context variant of the same lens (WIRE-04).
  4. `memory.db` is populated on the live `main()` path — the boot + session-close ingest sweeps fire in a real session (lifted out of the never-called `SessionLoop.run()`), so recall has fuel to retrieve (WIRE-05).
  5. The app loads `GEMINI_API_KEY` from `.env` even when a stale shell env var is present — `.env` wins (override or clear the ghost key), verified by a test that sets a decoy env var (WIRE-06).
**Plans**: 4 plans
Plans:
- [x] 77-01-PLAN.md — Wave 0: failing test scaffolds for WIRE-01/04/05/06 + WIRE-02/03 regression pins
- [x] 77-02-PLAN.md — Wave 1: WIRE-04 — build_curator_instruction seam; both curator backends read it
- [x] 77-03-PLAN.md — Wave 1: WIRE-06 — .env override=True (funded key wins over ghost shell var)
- [x] 77-04-PLAN.md — Wave 2: WIRE-01 (grounding→agent off-loop seam) + WIRE-05 (gated memory.db ingest on live path)

### Phase 78: PERCEIVE — Deeper, Generalized Ear
**Goal:** Make the existing ear *speak in change, not snapshots* — the prompt evidence carries deltas + calibrated per-fact confidence (so Gemini can abstain), a multi-scale trajectory (phrase / energy-arc / recent-moves) so it reasons over time, and an embedding-driven mean-centered genre prototype lookup (86.5%-validated, €0). All additive to the single-writer `MusicState`; **NO new DSP, NO MIR libs.**
**Depends on:** Phase 77 (the wired evidence_line + grounding are the surface these enrich)
**Requirements:** PERCEIVE-01, PERCEIVE-02, PERCEIVE-03
**Success Criteria** (what must be TRUE):
  1. Prompt evidence carries deltas + a calibrated confidence per fact (not raw absolute scalars) — Gemini reads "kick density rose 18%" rather than a bare number, and can abstain when confidence is low (PERCEIVE-01).
  2. The prompt carries a multi-scale trajectory (phrase position / energy-arc / recent DJ moves) so a reaction can reference where the set has been and is going, not just the current bar (PERCEIVE-02).
  3. `detected_genre` is driven by a mean-centered nearest-prototype cosine lookup over cached embeddings — written ONLY by the single-writer refresh loop, confidence-floored so a genre is never asserted the audio doesn't support (PERCEIVE-03).
  4. When trajectory/genre signal is cold or below the confidence floor, the prompt is byte-identical to the v8.0 baseline (additive-design invariant holds; the cold path adds nothing).
**Plans:** 4 plans (3 waves)
- [x] 78-01-PLAN.md — Wave-0 RED scaffolds (xfail-strict) for PERCEIVE-01/02/03 + the cold-path byte-identity REAL-GREEN pin [wave 1]
- [x] 78-02-PLAN.md — PERCEIVE-01 deltas + calibrated confidence & PERCEIVE-02 multi-scale trajectory (additive MusicState fields, deltas.py, single-writer + gated render) [wave 2]
- [x] 78-03-PLAN.md — PERCEIVE-03 mechanism: library/genre_prototypes.py (mean-centered nearest-prototype build/classify + thread-safe holder, no state writes) [wave 2, parallel with 78-02]
- [x] 78-04-PLAN.md — PERCEIVE-03 wiring: genre_reconcile.py (centered-cosine→0.5-render-band normalization, the flagged risk) + single-writer refresh feed [wave 3]

### Phase 79: LENS — Three Grounded Modes
**Goal:** Make hype / critique / tutor three real grounded lenses over the SAME structured state — not three separate brains — with lens selection shared across the co-host and the curator. The tutor lens explains DJing based on who you are + the semantics + reality + taste; the critique lens says what to fix; hype is the party voice. All three read the same wired+deepened evidence.
**Depends on:** Phase 77 (unified persona seam), Phase 78 (the deepened evidence the lenses interpret)
**Requirements:** LENS-01, LENS-02
**Success Criteria** (what must be TRUE):
  1. hype / critique / tutor exist as three grounded prompt lenses over the same structured state — switching lens changes the voice/intent, not the underlying grounded facts (LENS-01).
  2. Lens selection is shared across the co-host and curator surfaces — choosing "tutor" once flows to both (LENS-02).
  3. Each lens still passes the citation-grounding gate — a lens may change tone but cannot fabricate evidence; un-cited output strips to the ack-bank fallback regardless of lens.
**Plans:** 3 plans, 3 waves
  - [x] 79-01-PLAN.md — Wave-0 RED scaffolds (xfail-strict for LENS-01/02) + default-lens / cold-path byte-identity pin
  - [x] 79-02-PLAN.md — LENS-01: LENS_TO_MODE_MOOD map + build_lens_instruction selector over the untouched build_system_instruction
  - [ ] 79-03-PLAN.md — LENS-02: shared ConfigStore.extra["lens"] selection (_apply_lens) read by both co-host + curator, no IPC/schema bump

### Phase 80: GROUND — Gemini as Secondary Ear
**Goal:** Let Gemini *also* hear the audio as a secondary grounding input ("if it can hear in hollow space, use it") — fed alongside the structured DSP evidence, never as the primary perceiver — hallucination-guarded throughout. The reaction model is config-resolved via `model_router` (zero hardcoded literals) and the actual choice is decided by the bench (P81).
**Depends on:** Phase 77 (wired evidence), Phase 78 (deepened evidence the audio rides alongside)
**Requirements:** GROUND-01, GROUND-02
**Success Criteria** (what must be TRUE):
  1. The audio part is fed to Gemini alongside the structured evidence — and a Gemini claim that contradicts or isn't backed by the DSP evidence is hallucination-guarded (strips / abstains), so trust-the-audio still wins (GROUND-01).
  2. The reaction model is resolved via `model_router.resolve(...)` with zero hardcoded model literals (CI grep-gate holds), so the bench's winning model can be swapped in by config alone (GROUND-02).
  3. With the audio-secondary path gated off, the prompt + reaction are byte-identical to the v8.0 baseline (additive design).
**Plans**: TBD

### Phase 81: BENCH — The Validation Instrument
**Goal:** Build the experiment that PROVES the architecture — a multi-dimensional bench over model × input-grounding (raw audio | DSP-evidence-only/no-audio | audio+DSP | audio+DSP+trajectory+genre) × prompting (generic | structured) × contexting (snapshot | trajectory) × lens (hype/critique/tutor) × taste (with/without rubric), run on real tracks. An automated first-pass scores each cell (groundedness vs DSP facts, specificity, mode-fidelity); the cells are then surfaced for **Kaan's ear as the final judge** (Phase-16 rule). The "no-audio" cell tests "does the intelligence reside elsewhere."
**Depends on:** Phase 80 (the GROUND audio-secondary path) + Phase 79 (the three lenses) must exist to be benched; Phase 78 (trajectory/genre) supplies the grounding axes.
**Requirements:** BENCH-01, BENCH-02, BENCH-03
**Success Criteria** (what must be TRUE):
  1. A multi-dimensional bench harness runs model × grounding × prompting × contexting × lens × taste on real tracks and records each cell's output (BENCH-01).
  2. An automated first-pass eval scores groundedness (vs DSP facts), specificity, and mode-fidelity per cell — unit-testable on fixtures without the live API (BENCH-02).
  3. Bench cells are surfaced for Kaan's-ear final judgment via a KAAN-ACTION review surface — the automated score ranks, Kaan's ear decides the winning architecture + model (BENCH-03).
  4. The bench runs honest-green offline (mocked/fixture cells unit-testable) AND has a documented live e2e path on the funded key — results are never faked.
**Plans**: TBD

### Phase 82: CURATE — Unify Curator + Co-Host
**Goal:** Close the diamond — the agentic library/Viber curator and the live co-host become two facets of "AI that hears music with you," sharing ONE perception engine + structured-state contract and ONE taste layer + persona. The curator can curate "for this DJ"; the co-host can lean on what the DJ's library says about their taste.
**Depends on:** Phase 77 (unified persona seam + shared grounding), Phase 78 (shared perception/state contract), Phase 79 (shared lens), Phase 81 (the bench-proven engine choice)
**Requirements:** CURATE-01, CURATE-02
**Success Criteria** (what must be TRUE):
  1. Curator and co-host share the perception engine + the structured-state contract — both read one "what is true about this music / track" representation, not two parallel ones (CURATE-01).
  2. Curator and co-host share the taste layer + persona — the long-term DJ profile + the hype/critique/tutor lens reach both surfaces (CURATE-02).
  3. The unification is additive — the existing `library curate` / Telegram CLI surfaces keep working, and the four cardinal invariants still hold (no new ws port, no new IPC envelope, single-writer untouched).
**Plans**: TBD

### v8.1 Coverage

✓ All 18 v8.1 REQ-IDs mapped to exactly one phase (WIRE-01..06 → P77 · PERCEIVE-01..03 → P78 · LENS-01..02 → P79 · GROUND-01..02 → P80 · BENCH-01..03 → P81 · CURATE-01..02 → P82). No orphans, no duplicates.
✓ WIRE-02 (`ccf4930`) + WIRE-03 (`a9979b8`) already satisfied — placed in P77, marked DONE, no new work planned (P77's remaining work is WIRE-01/04/05/06).

### v8.1 Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 77. WIRE — Connect the Islands | 0/TBD | Not started | - |
| 78. PERCEIVE — Deeper, Generalized Ear | 0/4 | Planned | - |
| 79. LENS — Three Grounded Modes | 0/TBD | Not started | - |
| 80. GROUND — Gemini as Secondary Ear | 0/TBD | Not started | - |
| 81. BENCH — The Validation Instrument | 0/TBD | Not started | - |
| 82. CURATE — Unify Curator + Co-Host | 0/TBD | Not started | - |

---

# v8.0 "Proof & Polish" — SHIPPED 2026-05-25 (tech_debt accepted)

**Goal:** Take the system from "engineering-sound on paper" to **proven, easy, and live on GitHub** — everything logged · simulated · reported · tested · fixed · re-tested · verified · GitHub-done, plus real **ease of use** and a **whole-design level-up loop**. The deep audit (`.planning/ALL-MILESTONES-DEEP-AUDIT.md`) already finds the system **sound** (4256 tests green at branch HEAD, 4 cardinal invariants hold); v8.0 *proves and polishes* — it does not rescue.

**Anti-creep acid test:** *"Does this make an existing capability genuinely logged / simulated / reported / tested / fixed / verified / pushed — or easier to use / better-looking — WITHOUT a new product capability, AI/embedding provider, managed framework, ws port, or IPC envelope?"* If not, defer. Gemini-only holds; the four cardinal invariants hold by zero-touch on the reaction path.

**Dependency spine:** P71 (land in-flight branch work) → P72 (log everything + simulate hardware) → P73 (report + full-grid test + fix loop + verify + close audit findings) → P74 (ease of use) ‖ P75 (design level-up) [both depend on P71-landed UI, run after P73 green] → P76 (GitHub done: push backlog, CI green; signed-release + social stay KAAN-ACTION).

| # | Phase | Goal | REQ-IDs |
|---|-------|------|---------|
| 71 | Land & Verify | Finish + verify + commit the uncommitted live-tuning + observability branch work; green its new Py/TS/Rust tests | LOG-01, LOG-03 |
| 72 | Logged & Simulated | Unified structured logging end-to-end; simulation/replay harness for hardware-gated paths (BlackHole/FLX4/device-select) | LOG-02, LOG-04, SIM-01..03 |
| 73 | Reported · Tested · Fixed · Verified | Reports (test/coverage/session); full marker-grid run + fix loop to green; close deep-audit findings #1–#4; verify | RPT-01..03, TEST-01..05 |
| 74 | Ease of Use | First-run/onboarding friction, device-select UX, settings clarity, actionable failure states | UX-01..04 |
| 75 | Design Level-Up Loop | Whole-design CDJ-Whisper glow-up (impeccable + frontend-enforcement) across all surfaces; review→fix→re-review to zero HIGH | DESIGN-01..04 |
| 76 | GitHub Done | Push the ~528-commit backlog + branch; origin/main current; CI green on full matrix; repo presence finalized | GH-01..03 (GH-04 = KAAN-ACTION) |

### Phase 71 — Land & Verify
**Goal:** The in-flight `live-tuning-or-brain` work (device_select, the debug-log surface, tray-mood, audio/sidecar/session changes) is finished, verified, and committed in clean atomic commits.
**Success criteria:** (1) `device_select.py` + new audio backend changes land with `test_device_select` + `test_audio_macos` additions green; (2) debug-log surface (`debug_log.rs` + `debug-log.ts` + `debug-log-ws.ts` + `debug-log.spec`) wired one-socket-safe and green; (3) `tray-mood` + `test_proxy_fallback` land green; (4) default `pytest -q` stays 0-red (≥4256 passed); (5) TS + Rust suites run for the changed files.

### Phase 72 — Logged & Simulated
**Goal:** Everything important is logged through one structured surface, and the hardware-gated paths are simulatable headlessly.
**Success criteria:** (1) reaction turns log evidence packet + citation-gate decision (LOG-02); (2) a log-level switch gates verbosity without changing default UX (LOG-04); (3) a sim harness replays a session end-to-end with no hardware + no live Gemini (SIM-01); (4) synthetic BlackHole/FLX4/device fixtures verify the §V7-LIVE paths in CI (SIM-02); (5) the sim emits a deterministic artifact (SIM-03).

### Phase 73 — Reported · Tested · Fixed · Verified
**Goal:** The whole suite is run, reported, every red driven green, and the result verified; the deep-audit housekeeping is closed.
**Success criteria:** (1) saved test+coverage report artifact (RPT-01); (2) sim-session report (RPT-02); (3) full default suite 0-red + opt-in marker grid exercised (TEST-01/02); (4) TS+Rust green (TEST-03); (5) audit findings #1–#4 closed (TEST-04); (6) fix→re-test loop ends green + committed, no new skip/xfail graveyards (TEST-05); (7) v8.0 verification report ties each REQ to evidence (RPT-03).

### Phase 74 — Ease of Use
**Goal:** A stranger's path from install to first reaction is effortless and forgiving.
**Success criteria:** (1) guided first-run with clear empty/loading/permission states (UX-01); (2) self-explanatory device selection + routing, no BlackHole guesswork (UX-02); (3) clear, reversible mode/level/settings controls (UX-03); (4) every failure mode (no audio/key/proxy/MIDI) gives actionable guidance (UX-04).

### Phase 75 — Design Level-Up Loop
**Goal:** Every surface is leveled up to the CDJ-Whisper bar through an auditor-driven loop, no AI slop.
**Success criteria:** (1) session UI + pill zero HIGH findings (DESIGN-01); (2) mascot overlay + debrief + wizard + settings pass the bar (DESIGN-02); (3) review→fix→re-review loop run to zero HIGH (DESIGN-03); (4) consistent design tokens across surfaces (DESIGN-04).

### Phase 76 — GitHub Done
**Goal:** GitHub reflects the verified reality; the only thing left is Kaan's signature-gated public publish.
**Success criteria:** (1) ~528-commit backlog + branch pushed; origin/main current (GH-01); (2) CI green on full matrix for the pushed state (GH-02); (3) repo presence finalized, no stale claims (GH-03); (4) §SHIP-V4 signed-release + social documented as the sole KAAN-ACTION carveout, NOT auto-fired (GH-04).

---

# v7.0 "Open House" — SHIPPED 2026-05-24 (tech_debt accepted)

<details>
<summary>✅ v7.0 Open House (Phases 67–70) — SHIPPED 2026-05-24 (tech_debt accepted)</summary>

4 phases shipped engineering-green under `gsd-autonomous fully` mode. 20 plans, 37 tasks, 19/19 v7.0 REQ-IDs satisfied (engineering-side), 6/6 cross-phase wirings sound, UI-review PASS 23/24 on the landing. A **WIRING + DISCHARGE + POLISH milestone with ZERO new product capability** — zero net-new dependencies, zero new ws ports, zero new IPC envelopes. The four cardinal invariants (single-writer / citation-grounding / trust-the-audio / one-socket) held by zero-touch (only Phase 69 touched `src/vibemix/agent/` for the client-side proxy fallback).

- [x] Phase 67: All Tests Pass (5/5 plans) — 2026-05-23 (TEST-01..04; default `pytest -q` 0-red, 21-job `full-test-matrix.yml` CI, static skip/flake gates, 10× flake-hunt baseline)
- [x] Phase 68: All Devices Ready (5/5 plans) — 2026-05-23 (DEV-01..05; 10 profile contracts + synthetic-MIDI smokes, catalog reconciled to single `profiles/` source, hot-plug + audio-backend matrices, contributor recipe)
- [x] Phase 69: OSS Fully Integrated (5/5 plans) — 2026-05-24 (OSS-01..05; 4 OSS docs + presence test, client-side proxy fallback "Co-host unavailable this session", BYO-key doc, Homebrew+Scoop scaffolds, §SHIP-V4 publish pre-staged)
- [x] Phase 70: GitHub Sexified, Generated, Tested (5/5 plans) — 2026-05-24 (GH-01..05; asset reproducibility pipeline + auto-gen og-card, CDJ-Whisper Pages landing, demo poster, one-stop `test_github_presence.py`)

**KAAN-ACTION (live-confirm / external-clock, rides forward):** §V7-LIVE-01..11 (live hardware + first-CI-green + BYO walk) + §V7-PROXY (Bravoh server-side hardening) + §V7-LANDING (Pages-live + Kaan-felt aesthetic sign-off + real waitlist URL) + §ASSETS-DEMO-CUT (real 30-sec demo film, Francesco capture) + **§SHIP-V4 (HARD external clock — OSS-04 real `cut_release.sh v0.1.0-rc1` publish, gated on Apple Dev + SignPath; v4.0 "SHIP" closes alongside when it fires)**. All in `KAAN-ACTION-LEGAL.md`.

**Git tag + branch merge deferred** (consistent with v4.0 + v5.0 + v6.0): the `v7.0` tag + `live-tuning-or-brain` → main merge are Kaan's call on his clock (the OSS-04 publish + v4.0 close ride the same signature clock).

Full archive: `.planning/milestones/v7.0-ROADMAP.md` · Requirements: `.planning/milestones/v7.0-REQUIREMENTS.md` · Audit: `.planning/milestones/v7.0-MILESTONE-AUDIT.md`

</details>

---

# v6.0 "The Memory Turn" — SHIPPED 2026-05-23 (tech_debt accepted)

<details>
<summary>✅ v6.0 The Memory Turn (Phases 63–66) — SHIPPED 2026-05-23 (tech_debt accepted)</summary>

4 phases shipped engineering-green under `gsd-autonomous fully` mode. 12 plans, 14/14 v6.0 REQ-IDs satisfied, 6/6 cross-phase integration seams WIRED, 53/53 must-haves verified, 247/247 v6.0 surface tests GREEN. A **WIRING / REUSE milestone with ZERO net-new dependencies** — built entirely on the shipped `src/vibemix/library/` primitives (sqlite-vec, cosine_topk, embed-cache, grounding pattern, EVIDENCE_SOURCES schema).

- [x] Phase 63: Memory Store (3/3 plans) — 2026-05-22 (STORE-01..04 GREEN; 19/19 tests/memory/)
- [x] Phase 64: Session Ingest (3/3 plans) — 2026-05-22 (INGEST-01..03 GREEN; one v1 moment kind = `coach_line`; `moment` cut, `audio_moment` deferred)
- [x] Phase 65: Memory Retrieval Seam — ANTI-SLOP RELEASE GATE (4/4 plans) — 2026-05-22 (RECALL-01..04 GREEN; existence-only `recall` source à la P59 `key:`, fabricated `[recall:<id>]` strips whole turn)
- [x] Phase 66: Visible Copilot Move (2/2 plans) — 2026-05-22 (COPILOT-01..03 GREEN; transition-shape + vocabulary callbacks; ships behind `VIBEMIX_RECALL_ENABLED=0` until §RECALL-EAR Kaan-ear pass)

**KAAN-ACTION (live-confirm, rides forward):** §RECALL-EAR felt-quality discharge (4 ear items) + §LIVE-EMBED real-session FLEX-tier round-trip + two doc-drifts (code correct) + STORE-03 recordings-UI call-site (out of v6.0 scope; future recordings-UI phase). All in `KAAN-ACTION-LEGAL.md §RECALL-EAR` + `66-HUMAN-UAT.md`.

**Git tag deferred** (consistent with v4.0 + v5.0): the `v6.0` tag + branch merge are Kaan's call on his clock.

Full archive: `.planning/milestones/v6.0-ROADMAP.md` · Requirements: `.planning/milestones/v6.0-REQUIREMENTS.md` · Audit: `.planning/milestones/v6.0-MILESTONE-AUDIT.md`

</details>

---

# v5.0 "The Useful Cut" — SHIPPED 2026-05-22 (tech_debt accepted)

<details>
<summary>✅ v5.0 The Useful Cut (Phases 59–62) — SHIPPED 2026-05-22 (tech_debt accepted)</summary>

Deck-aware, actionable, unobtrusive. Full session-wide deck-state (pyrekordbox XML → Gemini-vision → numpy ladder) with a citable `key:` evidence source; a deterministic Camelot harmonic key-clash gate the LLM only narrates (ships **default-OFF** behind the Kaan-ear veto); an actionable-not-hype coach persona extending the `live-tuning-or-brain` branch (hype goldens regression-fenced); and a transparent, draggable, non-focus-stealing **floating pill** as the primary live surface (Three.js mascot kept opt-in/secondary, mascot-audit green). 4/4 phases, 17/17 requirements satisfied, 4/4 cross-phase integration seams WIRED.

- [x] Phase 59: Full Deck Awareness + Grounding (5/5 plans) — 2026-05-21
- [x] Phase 60: Harmonic-Feedback Confidence Gate (4/4 plans) — 2026-05-21 (detector default-OFF until the Kaan-ear veto flip)
- [x] Phase 61: Actionable-Not-Hype Coach Persona (2/2 plans) — 2026-05-21
- [x] Phase 62: Floating Pill UI (5/5 plans) — 2026-05-22

Full archive: `.planning/milestones/v5.0-ROADMAP.md` · Requirements: `.planning/milestones/v5.0-REQUIREMENTS.md` · Audit: `.planning/milestones/v5.0-MILESTONE-AUDIT.md`

</details>

---

# v4.0 SHIP — OPEN (engineering-complete 8/8, publish on signature clock — NOT archived)

> **Status:** All 8 phases (51–58) are engineering-complete. The milestone is deliberately **left open and unarchived** — its public RC publish stays gated on the external signature clock (Apple Dev Agreement via Francesco + SignPath OSS cert). **v7.0's OSS-04 actually consumes this publish** (closes alongside §SHIP-V4 discharge). Do not delete or archive this section until OSS-04 fires.

<details>
<summary>🟡 v4.0 SHIP (Phases 51–58) — engineering-complete 2026-05-21, publish on signature clock</summary>

- [x] Phase 51: Real-Hardware Bring-Up (3/3 plans) — 2026-05-21
- [x] Phase 52: Audio Path + Feature Grounding (4/4 plans) — 2026-05-21
- [x] Phase 53: Controller Live + Graceful Fallback (2/2 plans) — 2026-05-21
- [x] Phase 54: Hype Mode Live (4/4 plans) — 2026-05-20
- [x] Phase 55: Feedback Mode Live + Citation Integrity (3/3 plans) — 2026-05-21
- [x] Phase 56: Performance + Live Mascot (3/3 plans) — 2026-05-21
- [x] Phase 57: Sexify Finish (3/3 plans) — 2026-05-21
- [x] Phase 58: Ship Readiness (4/4 plans) — 2026-05-21 (`cut_release.sh --dry-run v0.1.0-rc1` GREEN; publish hard-guard regression-pinned)

**Critical path at close:** External clock — Apple Dev Agreement (Francesco) + SignPath OSS Foundation (Kaan, ~1-week SLA). `KAAN-ACTION-LEGAL.md §SHIP-V4` documents the one-button SHIP-CUT sequence. **v4.0 closes alongside v7.0 OSS-04.**

Full archive: `.planning/milestones/v4.0-ROADMAP.md`

</details>

---

## Phase History (Archived)

<details>
<summary>✅ v0.1.0 MVP Foundation (Phases 1–14) — SHIPPED 2026-05-13</summary>

See `.planning/milestones/v0.1.0/` for full archive.

</details>

<details>
<summary>✅ v2.0 Research-Driven Ship (Phases 15–26) — SHIPPED 2026-05-14 (tech_debt accepted)</summary>

12 phases shipped — 10 Claude-side end-to-end + 2 deferred to Kaan-action (Phase 15 Plan 04 UAT + entire Phase 16 ear-test gate). 38 plans, 1961 passing tests, 220 commits since `v0.1.0-rc1`, ~45.7k LOC across `src/vibemix/`, `tauri/`, `scripts/`, `tests/`.

Full archive: `.planning/milestones/v2.0-ROADMAP.md` · Requirements: `.planning/milestones/v2.0-REQUIREMENTS.md` · Audit: `.planning/milestones/v2.0-MILESTONE-AUDIT.md`

</details>

<details>
<summary>✅ v2.1 The Unified Cut (Phases 27–39) — SHIPPED 2026-05-16 (tech_debt accepted)</summary>

13 phases shipped engineering-green under `gsd-autonomous fully` mode. 96 plans, 633 phase-scope tests added, 225 commits since `v2.0` tag, net ~+45k LOC. 105/105 v2.1 REQ-IDs engineering-satisfied. All 5 cross-phase integration seams audited WIRED.

Full archive: `.planning/milestones/v2.1-ROADMAP.md` · Requirements: `.planning/milestones/v2.1-REQUIREMENTS.md` · Audit: `.planning/milestones/v2.1-MILESTONE-AUDIT.md`

</details>

<details>
<summary>✅ v3.0 Clean OSS Ship (Phases 40–45) — SHIPPED 2026-05-17 (tech_debt accepted)</summary>

6 phases shipped engineering-green under `gsd-autonomous fully` mode. 41 plans, 250 commits since `v2.1.0` tag, net ~+61k LOC. 57/57 v3.0 REQ-IDs engineering-satisfied. All 3 integration seams + 5 flows audited.

Full archive: `.planning/milestones/v3.0-ROADMAP.md` · Requirements: `.planning/milestones/v3.0-REQUIREMENTS.md` · Audit: `.planning/milestones/v3.0-MILESTONE-AUDIT.md`

</details>

<details>
<summary>✅ v3.1 Distribution-Ready Pass (Phases 46–50) — SHIPPED 2026-05-18 (tech_debt accepted)</summary>

5 phases shipped engineering-green under `gsd-autonomous fully` mode. 32 plans, 61 commits since `v3.0` tag, net ~+57.5k LOC. 44/44 v3.1 REQ-IDs engineering-satisfied. All 5 cross-phase integration seams audited WIRED.

Full archive: `.planning/milestones/v3.1-ROADMAP.md` · Requirements: `.planning/milestones/v3.1-REQUIREMENTS.md` · Audit: `.planning/milestones/v3.1-MILESTONE-AUDIT.md`

</details>

---

## Milestone-Level Progress

| Milestone | Phases | Status | Shipped |
|-----------|--------|--------|---------|
| v0.1.0 MVP Foundation | 1–14 | ✅ Shipped | 2026-05-13 |
| v2.0 Research-Driven Ship | 15–26 | ✅ Shipped (tech_debt) | 2026-05-14 |
| v2.1 The Unified Cut | 27–39 | ✅ Shipped (tech_debt) | 2026-05-16 |
| v3.0 Clean OSS Ship | 40–45 | ✅ Shipped (tech_debt) | 2026-05-17 |
| v3.1 Distribution-Ready Pass | 46–50 | ✅ Shipped (tech_debt) | 2026-05-18 |
| v4.0 SHIP | 51–58 | 🟡 Engineering-complete (8/8) — publish on signature clock; closes alongside v7.0 OSS-04 | - |
| v5.0 The Useful Cut | 59–62 | ✅ Shipped (tech_debt) | 2026-05-22 |
| v6.0 The Memory Turn | 63–66 | ✅ Shipped (tech_debt) | 2026-05-23 |
| v7.0 Open House | 67–70 | ✅ Shipped (tech_debt) | 2026-05-24 |
| v8.0 Proof & Polish | 71–76 | ✅ Shipped (tech_debt) | 2026-05-25 |
| v8.1 One Mind | 77–82 | 🔨 In progress | - |

---

*Roadmap extended 2026-05-23 for v7.0 "Open House" — **4 phases (67–70)** continuing numbering from v6.0 (which ran 63–66). v4.0 "SHIP" stays OPEN and unarchived above — its publish closes alongside v7.0's OSS-04 (KAAN-ACTION §SHIP-V4 discharge fires `cut_release.sh v0.1.0-rc1` for real). v7.0 derives from 19 requirements across 4 pillars (TEST · DEV · OSS · GH), one phase per pillar, sized by `.planning/REQUIREMENTS.md` Traceability — 4/5/5/5 REQ-IDs per phase, zero orphans, zero duplicates. **Hard scope rule (locked):** v7.0 is WIRING + DISCHARGE + POLISH — zero new product capability, zero new AI providers, zero new managed-memory frameworks, zero new ws ports, zero new IPC envelopes. The four cardinal invariants (single-writer / citation grounding / "trust the audio" / one socket) hold by zero-touch — no phase modifies the reaction path. The v4.0 external signature clock is unchanged. Critical path: P67 (test infrastructure, dependency-free) → P68 (controller catalog reconciliation + audio backends, lands on P67's CI matrix) → P69 (OSS surface + actual publish gated on §SHIP-V4) → P70 (GitHub front-porch + Kaan-felt landing-page sign-off). Under `gsd-autonomous fully`, OSS-04 routes to §SHIP-V4 if signatures haven't landed at execution; the other 18 REQ-IDs ship unblocked.*

*Roadmap extended 2026-05-25 for v8.1 "One Mind" — **6 phases (77–82)** continuing numbering from v8.0 (which ran 71–76) — NO reset. 18 v8.1 REQ-IDs mapped to exactly one phase (100% coverage, no orphans, no duplicates): WIRE-01..06 → P77 (6; WIRE-02 `ccf4930` + WIRE-03 `a9979b8` already SHIPPED — placed in P77, marked DONE, no new work) · PERCEIVE-01..03 → P78 (3) · LENS-01..02 → P79 (2) · GROUND-01..02 → P80 (2) · BENCH-01..03 → P81 (3) · CURATE-01..02 → P82 (2). **Hard scope rule (locked):** ship-not-over-engineer (one connected, tested wire per phase) · Gemini-only · NO new MIR libraries / NO new DSP detectors · no new ws ports / no new IPC envelopes · the four cardinal invariants (single-writer / citation-grounding / trust-the-audio / one-socket) hold by ADDITIVE design (gated-off cold path byte-identical to the v8.0 baseline) · honest green (unit-testable without the API; live e2e on the funded key). Dependency spine: P77 (WIRE) → P78 (PERCEIVE) → P79 (LENS) ‖ P80 (GROUND) → P81 (BENCH — depends on GROUND + LENS being in place to bench them) → P82 (CURATE). Under `gsd-autonomous fully`, blockers (Gemini billing — resolved; any live-hardware ear-pass) ride forward to KAAN-ACTION — they never block. Charter: `.planning/research/one-mind-charter.md`.*
