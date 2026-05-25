---
gsd_state_version: 1.0
milestone: v8.1
milestone_name: One Mind
status: executing
last_updated: "2026-05-26T00:00:00.000Z"
last_activity: 2026-05-26
progress:
  total_phases: 6
  completed_phases: 0
  total_plans: 4
  completed_plans: 2
  percent: 0
---

# vibemix — State

**Last updated:** 2026-05-25 — **v8.1 "One Mind" ROADMAPPED** under `gsd-autonomous fully`. 6 phases (77–82) continuing numbering from v8.0 (ran 71–76) — NO reset. 18/18 v8.1 REQ-IDs mapped to exactly one phase (100% coverage, no orphans, no duplicates). WIRE-02 (`ccf4930`) + WIRE-03 (`a9979b8`) already SHIPPED — placed in P77, marked DONE, no new work. Next: `/gsd:plan-phase 77`.

---

## Project Reference

See: .planning/PROJECT.md (Current Milestone: v8.1 "One Mind")

- **Project:** vibemix — open-source AI DJ co-host (Bravoh's first OSS release).
- **Core value:** "Real DJ friend in your ear" — never hallucinating, never breaking flow, never AI slop.
- **v8.1 thesis:** Connect the disconnected islands into ONE grounded product — *"an AI that hears music with you, and gets you."* The DSP/MIDI/embedding stack is the **EAR** (structured state + multi-scale trajectory + the DJ's moves + genre); Gemini is the taste/culture **VOICE**; a shared **taste layer** + **three lenses** (hype/critique/tutor) span both surfaces (live co-host + library curator). The shallowness is a **wiring gap** + asking Gemini to be the ear — NOT a model limit (proven: 3 frontier models gave 3 genres for one track; genre-from-embeddings hit 86.5% at €0).
- **Six categories → six phases:** WIRE (P77) · PERCEIVE (P78) · LENS (P79) · GROUND (P80) · BENCH (P81) · CURATE (P82). Dependency spine: WIRE → PERCEIVE → (LENS ‖ GROUND) → BENCH → CURATE.
- **Hard constraints (locked, every phase):** ship-not-over-engineer (one connected, tested wire per phase) · Gemini-only AI/embedding provider · **NO new MIR libraries / NO new DSP detectors** (GPL/AGPL/NC license wall vs Apache-2.0 + Bravoh reuse) · no new ws ports / no new IPC envelopes / no managed-memory frameworks · four cardinal invariants hold by **ADDITIVE design** (gated-off cold path byte-identical to v8.0 baseline) · honest green (unit-testable without the API; live e2e on the funded key `...32u744`, project 709533190790) — never fake results.
- **Cardinal invariants:** single-writer (only the refresh loop writes `MusicState`; embedding-genre must write THERE) · citation-grounding (every emitted citation resolves in `EvidenceRegistry`; un-cited strips to ack-bank — the anti-slop gate) · trust-the-audio (live evidence is authoritative; Gemini's audio is SECONDARY, hallucination-guarded) · one-socket (mascot/wizard bus = `127.0.0.1:8765`, debrief = `8766`; no new port).
- **Current focus:** Phase 77 — WIRE — Connect the Islands
- **Project mode:** standard. **Granularity:** fine. **Model profile:** quality (all agents on Opus, all checkpoints on).
- **Autonomy mode:** `gsd-autonomous fully` — blockers (Gemini billing — resolved; any live-hardware ear-pass) ride forward to KAAN-ACTION; only the privacy rule + destructive risk still pause.

---

## Current Position

Phase: 77 (WIRE — Connect the Islands) — EXECUTING
Plan: 3 of 4 (Plans 01–02 complete)
Status: Ready to execute
Last activity: 2026-05-26

### Plan 77-02 — WIRE-04 shared curator persona seam (complete 2026-05-26)

- NEW `build_curator_instruction(lens="tutor")` sibling in `prompts/matrix.py` — the single curator-voice source. Draws persona from the fixed `MOOD_PERSONAS` dict (anti-injection); omits the co-host-runtime blocks (TTS tag DSL / citation grammar / fail-soft fragment). Lens map: tutor→teacher / hype→hype-man / critique→coach.
- Both curator backends consume the seam: `library/agent.py` (`_SYSTEM_INSTRUCTION` + `_INTERACTIVE_SYSTEM_INSTRUCTION`) + `library/codex_curate.py` (`_SYSTEM_PROMPT`). Grounding RULES (seen-set / never-invent-id) + codex `_OUTPUT_SCHEMA` preserved VERBATIM. `model_router.resolve("library_agent")` untouched (no model literal).
- `mcp_server.py` verified persona-blind-free: no own system prompt; voice inherited via the codex path (LibraryToolset grounding at the tool boundary). Documented with a code comment.
- **Deviation (Rule 1):** the eager seam import regressed `tests/memory/test_no_live_path_import.py` (`vibemix.prompts` is a forbidden surface on the memory storage-spine boundary). Fixed by importing the seam LAZILY inside cached builders + exposing the constants via PEP 562 `__getattr__` — the curators consume the seam without dragging `vibemix.prompts` into `sys.modules` on import.
- Honest green: no `genai.Client`, no `GEMINI_API_KEY`. Full suite **4445 passed / 0 failed / 7 xfailed** (4 WIRE-04 xfails flipped to real passes). Commits `18f9b61` (Task 1), `556b9c2` (Task 2).

### Plan 77-01 — WIRE test scaffolds (complete 2026-05-26)

Wave-0 RED scaffolds for the four unimplemented wires + green pins for the two shipped ones:

- **WIRE-01/04/05/06** → `xfail(strict=True)` failing tests that flip to a real pass when their implementation plan lands (04 / 02 / 04 / 03). Files: `tests/agent/test_dj_cohost_grounding.py`, `tests/memory/test_ingest_wiring.py` (extended), `tests/library/test_curator_persona_seam.py`, `tests/runtime/test_load_env_override.py`.
- **WIRE-02/03** → green regression pins in `tests/repo/test_wire_regression_pins.py` (8 genre-chain detectors yield real tasks; `genre=<name>` evidence confidence-gated at 0.5 floor).
- Green now: cold-path byte-identity, citation-gate `[track:<id>]`→registry, env-key-not-logged security pin (V7).
- Honest green: no `genai.Client`, no `GEMINI_API_KEY`. Full suite **4441 passed / 0 failed / 11 xfailed** (5 new). Commits `caa4ada`, `a560e29`, `07e400e`.
- Decisions: WIRE-03 pin matches the *shipped* `genre=<name>` format (not `(conf)` as plan text said); WIRE-02 genre-chain measurements are narrate-only (not registry-citable per `coach.py:594`) so the pin asserts payload-in-task.

### Quick Tasks Completed

| # | Description | Date | Commit | Status | Directory |
|---|-------------|------|--------|--------|-----------|
| 260525-fuv | Token + cost counter for live sessions (SessionMeter + ROUTE_PRICING + session.json cost block + stderr recap; cache-hit savings) | 2026-05-25 | 4799730 | Verified (full suite 4284/0) | [260525-fuv-token-and-cost-counter-for-live-sessions](./quick/260525-fuv-token-and-cost-counter-for-live-sessions/) |

## v8.1 Phase Map

| Phase | Goal | Requirements (count) | Depends on | UI |
|-------|------|----------------------|-----------|----|
| 77 — WIRE: Connect the Islands | Live co-host shares the curator's grounding brain (`Grounding`→`DJCoHostAgent`), unified persona/lens across surfaces, `memory.db` ingest on the live `main()` path, env-key override fix. WIRE-02 (`ccf4930`) + WIRE-03 (`a9979b8`) already SHIPPED — pinned, no new work. | WIRE-01, WIRE-02 ✅, WIRE-03 ✅, WIRE-04, WIRE-05, WIRE-06 (6) | — (first v8.1 phase) | — |
| 78 — PERCEIVE: Deeper, Generalized Ear | Prompt evidence carries deltas + calibrated per-fact confidence (abstain-capable), multi-scale trajectory (phrase/energy-arc/recent-moves), and mean-centered nearest-prototype genre from cached embeddings (86.5%, €0). **NO new DSP, NO MIR libs.** Cold path byte-identical. | PERCEIVE-01, PERCEIVE-02, PERCEIVE-03 (3) | P77 (wired evidence_line + grounding) | — |
| 79 — LENS: Three Grounded Modes | hype / critique / tutor as three grounded prompt lenses over ONE structured state; lens selection shared across co-host + curator. Each lens still passes the citation gate. | LENS-01, LENS-02 (2) | P77 (persona seam) + P78 (deepened evidence) | — |
| 80 — GROUND: Gemini as Secondary Ear | Audio part fed to Gemini ALONGSIDE the structured evidence (secondary, never primary perceiver), hallucination-guarded; reaction model config-resolved via `model_router` (zero literals), choice decided by the bench. Gated-off = byte-identical. | GROUND-01, GROUND-02 (2) | P77 + P78 | — |
| 81 — BENCH: The Validation Instrument | Multi-dimensional bench: model × grounding × prompting × contexting × lens × taste on real tracks; automated first-pass eval (groundedness vs DSP facts, specificity, mode-fidelity); cells surfaced for **Kaan's ear = final judge** (Phase-16 rule). Honest-green offline + documented live e2e. | BENCH-01, BENCH-02, BENCH-03 (3) | P80 (GROUND) + P79 (LENS) in place to bench; P78 supplies grounding axes | — |
| 82 — CURATE: Unify Curator + Co-Host | Curator + co-host become two facets of one engine — shared perception engine + structured-state contract (CURATE-01) and shared taste layer + persona (CURATE-02). Additive: existing `library curate`/Telegram CLI keeps working; invariants hold. | CURATE-01, CURATE-02 (2) | P77 + P78 + P79 + P81 (bench-proven engine) | — |

**Build-order rationale (dependency-correct):** WIRE first because the grounding→agent wire (#1 in `connection-map.md`) is the single highest-leverage island connection and everything downstream enriches the wired evidence surface. PERCEIVE deepens that surface (deltas/confidence/trajectory/genre) before LENS interprets it and GROUND adds the audio-secondary ear. BENCH can only bench LENS + GROUND once they exist, and uses PERCEIVE's grounding axes. CURATE unifies last, on the bench-proven shared engine. WIRE-02/03 are already shipped — P77's real work is WIRE-01/04/05/06.

## Performance Metrics

| Metric | Value |
|--------|-------|
| Phases complete (v0.1.0) | 14 / 14 |
| Phases complete (v2.0) | 10 / 12 code-shipped (2 deferred to Kaan-action) |
| Phases complete (v2.1) | 13 / 13 engineering-green |
| Phases complete (v3.0) | 6 / 6 engineering-green |
| Phases complete (v3.1) | 5 / 5 engineering-green |
| Phases complete (v4.0) | 8 / 8 engineering-green (publish on external signature clock) |
| Phases complete (v5.0) | 4 / 4 engineering-green |
| Phases complete (v6.0) | 4 / 4 engineering-green |
| Phases complete (v7.0) | 4 / 4 engineering-green |
| Phases complete (v8.0) | 6 / 6 engineering-green (KAAN-ACTION §GH-BILLING / §SHIP-V4 ride forward) |
| v8.1 phase count | 6 (Phases 77–82) |
| Phases complete (v8.1) | 0 / 6 (roadmapped; not started) |
| Plans complete (v8.1) | 2 / 4 in P77 (Plan 01 scaffolds + Plan 02 WIRE-04 seam) |
| v8.1 REQ-IDs mapped | 18 / 18 ✓ (100% coverage, no orphans, no duplicates) |
| v8.1 REQ-IDs complete | 3 / 18 (WIRE-02 `ccf4930` + WIRE-03 `a9979b8` shipped; WIRE-04 `556b9c2` Plan 02) |
| v8.1 per-phase REQ counts | P77=6 (WIRE) · P78=3 (PERCEIVE) · P79=2 (LENS) · P80=2 (GROUND) · P81=3 (BENCH) · P82=2 (CURATE) |
| v8.1 net-new AI/embedding providers | 0 (Gemini-only, locked) |
| v8.1 net-new MIR libs / DSP detectors | 0 (license wall — additive perception only) |
| v8.1 net-new ws ports / IPC envelopes | 0 (one-socket + zero-envelope invariants held) |
| Default `pytest -q` baseline (carried in) | ~4284/0 (post quick-task 260525-fuv); each v8.1 phase holds green additively |

---

## Accumulated Context

### v8.1 Roadmap Decisions Locked (2026-05-25)

v8.1 "One Mind" roadmapped into **6 phases (77–82)** continuing numbering from v8.0 (ran 71–76) — NO reset. 18/18 REQ-IDs mapped to exactly one phase. The 6 categories (WIRE/PERCEIVE/LENS/GROUND/BENCH/CURATE) are the charter's pre-decided cut; the roadmap keeps "one connected wire per phase" + dependency order. Derived from `.planning/REQUIREMENTS.md` (the v8.1 REQ-IDs) cross-checked against `one-mind-charter.md` (vision + "Requirement Categories → Phases") and `connection-map.md` (top-5 wires, file:line evidence).

**Already shipped (no new work, pinned in P77):** WIRE-02 (`ccf4930` — 8 genre-chain detectors surface measured evidence to prompt + register in `EvidenceRegistry`) + WIRE-03 (`a9979b8` — `detected_genre` surfaced in prompt evidence, confidence-gated). Both are TRUE today; P77 places them in its WIRE phase marked DONE and pins them with regression tests. P77's remaining real work is WIRE-01 (grounding→agent), WIRE-04 (persona/lens unify), WIRE-05 (memory ingest on live path), WIRE-06 (env-key override).

**Top-5 wires (from `connection-map.md`, ranked by leverage):**

1. ⭐ Wire `Grounding` ("what's playing") into the live agent — built + armed at boot (`__main__.py:1147`) but `DJCoHostAgent.__init__` has no `grounding` kwarg → fully orphaned. Highest leverage. → WIRE-01 / P77.
2. 8 genre-chain detectors → evidence + real task (`event_detector.py:444-447` returns without `_fire`; `coach.py task_for_event` has no branch → "React naturally."). → WIRE-02 (DONE `ccf4930`).
3. Unify persona/lens across surfaces (`library/agent.py:58,189` hardcodes its voice; doesn't import `prompts`/`coach`/`profile`). → WIRE-04 / P77 (+ LENS P79, CURATE P82).
4. Feed `detected_genre` into the prompt (`coach.py evidence_line` never reads it). → WIRE-03 (DONE `a9979b8`) + PERCEIVE-03 (embedding-driven upgrade) / P78.
5. Populate `memory.db` on the live path (`SessionLoop.run()` never called from `main()` → ingest never fires). → WIRE-05 / P77.

**Genre-from-embeddings (the win, `genre-from-embeddings.md`):** mean-centering is MANDATORY (raw avg pairwise cosine 0.779 → centered 0.058; restores separation). Nearest-prototype accuracy 86.5% on 378 labelable tracks, €0 (cached vectors). Live mechanism: identified track's stored embedding → center with the SAME corpus centroid (`centering.load_or_compute_centroid` + `center_and_renorm`) → cosine-rank to ~7 genre prototypes → argmax with a confidence floor (anti-hallucination, Invariant #3). Written ONLY by the single-writer refresh loop into `MusicState.detected_genre`/`genre_confidence`; `evidence_line` gains one gated `genre=<name>(conf)` field exactly like the existing `track=`/`deck=` pattern. → PERCEIVE-03 / P78.

**Empirical floor (`gemini-audio-truth-test.md`):** 3 frontier models returned 3 different genres for one track → Gemini's raw ear is unreliable → ground it (the thesis). This is also why GROUND (P80) feeds audio only as a SECONDARY input and BENCH (P81) includes a no-audio cell ("intelligence resides elsewhere").

**Why 6 phases (not finer under fine-granularity).** The 6-category cut is pre-decided in the charter + REQUIREMENTS.md and each category is internally coherent (one connected wire). Dependencies are near-linear (WIRE → PERCEIVE → LENS ‖ GROUND → BENCH → CURATE). Finer phase count would manufacture seams; fine granularity applies WITHIN each phase via plan decomposition.

### v8.1 KAAN-ACTION / soft-discharge flags (carry into planning)

- **BENCH-03 — Kaan's-ear final judgment (KAAN-ACTION, soft):** the bench's automated first-pass score RANKS cells; Kaan's ear DECIDES the winning architecture + model (Phase-16 rule). Surface a KAAN-ACTION review surface; engineering closes when the harness + auto-eval + review surface are green. Does NOT block forward progress under `gsd-autonomous fully`.
- **Live e2e on the funded key (soft):** every phase ships honest-green offline (unit-testable without API); the live confirmation rides the funded key (`...32u744`). Gemini billing blocker is RESOLVED.
- **Inherited external-clock items unchanged:** v8.0 §GH-BILLING (resolve GitHub billing → CI green), §GH-MAIN-MERGE (PR #8, no squash), §SHIP-V4 (signed release — Apple Dev + SignPath; v4.0 closes alongside), §V7-LIVE (real-hardware ear-passes), §RECALL-EAR (v6.0 felt-quality). All ride Kaan's clock; none block v8.1 engineering.

### Anti-slop / additive-design invariants baked into v8.1 success criteria

- **Grounding citation (WIRE-01):** the injected `[track:<id>]` must resolve in `EvidenceRegistry`; an un-resolvable track citation strips the turn (citation-grounding gate).
- **Genre confidence floor (PERCEIVE-03 / WIRE-03):** never assert a genre the audio doesn't support — below floor → omit the field (NOT `genre=unknown` spam). Trust-the-audio (Invariant #3).
- **Single-writer (PERCEIVE-03):** embedding-genre writes ONLY in the refresh loop, never elsewhere (Invariant #1).
- **Cold-path byte-identical (PERCEIVE / GROUND):** when trajectory/genre is cold or the audio-secondary path is gated off, the prompt is byte-identical to the v8.0 baseline — additive design, gated-off cold path adds nothing.
- **Lens cannot fabricate (LENS):** a lens changes tone/intent, never the grounded facts; un-cited output strips to ack-bank regardless of lens.
- **Audio is secondary (GROUND-01):** a Gemini audio claim unbacked by DSP evidence is hallucination-guarded; the DSP ear stays authoritative.
- **One socket / zero envelope (CURATE):** unifying the surfaces adds no ws port + no IPC envelope; `library curate`/Telegram CLI keeps working.

---

## Session Continuity

**Next command:** `/gsd:plan-phase 77` (WIRE — Connect the Islands). Optionally `/gsd:explore 77` first if the grounding-kwarg + memory-ingest-lift seams need a phase research pass — but `connection-map.md` already gives file:line evidence for all four remaining WIRE wires, so planning can likely proceed directly.

**What's done:** **v8.1 "One Mind" ROADMAPPED** — 6 phases (77–82), 18/18 REQ-IDs mapped (no orphans, no duplicates). ROADMAP.md v8.1 section appended (summary checklist + REQ table + per-phase detail with 2–5 goal-backward success criteria each + v8.1 progress table); Milestone-Level Progress table got v8.0 + v8.1 rows; REQUIREMENTS.md Traceability filled (WIRE-02/03 marked ✅ Done, rest Pending); STATE.md updated to v8.1. WIRE-02 (`ccf4930`) + WIRE-03 (`a9979b8`) already satisfied — placed in P77, DONE, no new work.

**What's next:** Phase 77 (WIRE) — WIRE-01 (grounding→`DJCoHostAgent` kwarg), WIRE-04 (curator reads `prompts/matrix.py` lens), WIRE-05 (lift boot+close ingest sweeps into `main()`), WIRE-06 (`.env` override over ghost env var). WIRE-02/03 pin-only. Then P78 (PERCEIVE) → P79 (LENS) ‖ P80 (GROUND) → P81 (BENCH) → P82 (CURATE).

**Open before next execution:** none blocking. Gemini billing resolved; funded key in `.env`. Bench floor data captured (3-model genre disagreement = thesis proof).

---

## Deferred Items

**v8.1 (this milestone) — soft KAAN-ACTION (ride forward under `gsd-autonomous fully`, do NOT block):**

| Category | Phase | Status | Note |
|----------|-------|--------|------|
| ear-judgment | 81 | to create in plan | BENCH-03 — Kaan's-ear final judgment over the bench cells (Phase-16 rule). Auto-eval ranks; Kaan decides winning architecture + model. KAAN-ACTION review surface to create during P81 plan. |
| live-confirm | 77–82 | soft | Live e2e on the funded key per phase (honest-green offline ships first). Gemini billing RESOLVED — not a blocker. |

**Inherited from prior milestones (unchanged; all on Kaan's external clock — none block v8.1 engineering):**

| Category | Milestone | Status | Note |
|----------|-----------|--------|------|
| ci/billing | v8.0 | human_needed | §GH-BILLING (resolve GitHub billing → CI green) + §GH-MAIN-MERGE (merge PR #8, no squash) |
| signature | v4.0 / v8.0 | human_needed | §SHIP-V4 — signed release (Apple Dev + SignPath); v4.0 SHIP closes alongside |
| live-hardware | v7.0 | human_needed | §V7-LIVE-01..10 — real-hardware ear-passes (BlackHole / FLX4 / WASAPI / contributor smoke); engineering mock-pinned green |
| felt-quality | v6.0 | human_needed | §RECALL-EAR — `VIBEMIX_RECALL_ENABLED=1` flip after Kaan-ear pass (independent clock; v8.1 WIRE-05 fills the store so recall finally has fuel) |
| ux | v8.0 | surfaced | user-level (BEG/INT/PRO) UI control — cross-stack follow-up surfaced, not half-built |

---

## Historical Audit Annotations

Retained for audit-trail continuity (pinned by `tests/repo/test_gate_42_hybrid_in_force.py::test_state_md_phase_16_line_is_annotated_retired`):

- **Phase 16 ear-test memory override — RETIRED.** The v2.1 P85 autonomous-only override is formally retired as of Plan 42-05 (2026-05-16). Replaced by the v3.0 hybrid hallucination gate (`scripts/release/check_gate.sh` + `check_ear_test.sh`) wired into `cut_release.sh` at Gate 2b. Cross-reference: `.planning/decisions/P85-OVERRIDE-RETIRED.md`. (Note: v8.1 BENCH-03 explicitly RE-INVOKES the Phase-16 "Kaan's ear is final judge" rule for the bench — consistent with the hybrid gate, the auto-eval is the fast-lane rank and Kaan's ear is the veto.)

## Operator Next Steps

- Plan Phase 77 (WIRE) with `/gsd:plan-phase 77`.
