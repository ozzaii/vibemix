# Phase 81: BENCH — The Validation Instrument - Context

**Gathered:** 2026-05-26
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous; grey areas auto-resolved with charter-recommended answers per Kaan's overnight authorization)

<domain>
## Phase Boundary

Build the experiment that PROVES the architecture — a multi-dimensional bench over **model × input-grounding (raw audio | DSP-only/no-audio | audio+DSP | audio+DSP+trajectory+genre) × prompting (generic | structured) × contexting (snapshot | trajectory) × lens (hype/critique/tutor) × taste (with/without rubric)**, run on real tracks. An automated first-pass scores each cell (groundedness vs DSP facts, specificity, mode/lens-fidelity); the cells are surfaced for **Kaan's ear as the final judge** (Phase-16 rule). The "no-audio" cell tests "does the intelligence reside elsewhere."

- **BENCH-01** — the multi-dimensional harness runs the cells on real tracks and records each cell's output.
- **BENCH-02** — an automated first-pass eval scores groundedness / specificity / mode-fidelity per cell, unit-testable on fixtures WITHOUT the live API.
- **BENCH-03** — cells surfaced for Kaan's-ear final judgment via a KAAN-ACTION review surface; the auto-score ranks, **Kaan's ear decides** the winning architecture + model.

**THE HARD HUMAN GATE:** BENCH-03 (the "did it click / is it slop" verdict) CANNOT run in the autonomous pass. Autonomous must **PRODUCE-AND-PARK**: build the harness (BENCH-01) + auto-eval (BENCH-02), run a BOUNDED real-cell sample on the funded key to produce real cells, lay them on a clean review surface — then DEFER the verdict to KAAN-ACTION. **NEVER synthesize, fake, or stand in for Kaan's verdict.** Honest results only.

**Out (historical v8.1 live-reaction scope):** no new live-reaction AI provider,
no new ws port/IPC envelope; the bench is a dev/eval instrument, not a shipped
runtime feature. Phase 90 later superseded library embeddings with local CLAP
ONNX, and Viber set-prep/chat now uses local Codex for the current product path.
</domain>

<decisions>
## Implementation Decisions

### BENCH-01 — the harness (offline-tested code + live produce path)
- A bench harness module in the package (fold in the proven `/tmp/truthtest/bench_models.py` + `run_test.py` intuition + the 6 real track excerpts + the floor `bench_results.json`). Parameterized over the 6 dimensions; records each cell's full output to a results artifact.
- **Scope sanely (not the full cartesian explosion):** the charter's TWO focused studies — (A) architecture-axis with ONE fixed model (sweep grounding × prompting × contexting × lens × taste); (B) model-axis with the best architecture from (A). Plus the decisive "no-audio" cell. The harness CAN express the full matrix; the runs are the two studies.
- **Offline-green:** the harness is unit-testable with a FAKE genai client returning fixture cells — the cell-assembly, dimension-sweep, and results-recording logic prove out with zero API calls (honest green). The real run is a separate, documented invocation.
- Reuse the real grounding/evidence stack (Phase 77-80 wiring) to build the per-cell prompts so the bench measures the ACTUAL product, not a toy.

### BENCH-02 — automated first-pass eval (pure, offline)
- Pure scoring functions over a recorded cell: **groundedness** (every citation/claim resolves in the cell's `EvidenceRegistry`/DSP-fact snapshot — reuse the `CitationLinter` logic), **specificity** (concreteness vs generic-AI-slop heuristics), **mode/lens-fidelity** (does a hype cell sound hype, a tutor cell teach, etc.).
- Unit-tested on FIXTURE cells (no live API) — deterministic scores. The auto-score RANKS cells; it does NOT decide (Kaan's ear decides).

### BENCH-03 — Kaan's-ear review surface (HARD HUMAN GATE — produce-and-park)
- Generate a clean, human-readable **review surface** (a `KAAN-ACTION` artifact: ranked cells with their auto-scores + the per-cell prompt/output, grouped by study/dimension) so Kaan can read + judge "did it click / is it slop / which architecture + model wins".
- **The verdict is Kaan's, parked.** Autonomous produces the surface + the auto-ranking; it does NOT fill in the verdict, does NOT pick the winner, does NOT fake any cell output. The winning architecture + model selection (which feeds GROUND-02's `live_coach` alias + the default architecture) is a KAAN-ACTION.

### Real-cell run (the produce step)
- **Documented live e2e path** on the funded key (`...32u744`, in `.env`; `load_dotenv(override=True)` from Phase 77 ensures it wins). One command runs the bounded study.
- **Cost-bounded:** a representative subset (the two focused studies on a few real tracks, Gemini Flash pricing) — not the full cartesian product across all tracks. Within the ~50€/mo dev budget; a few cents-to-low-€ one-time.
- **Fail-safe:** if the API errors / rate-limits / the key has issues, the run parks gracefully as KAAN-ACTION (the offline harness + eval + the existing floor data still ship the capability) — it NEVER blocks the autonomous milestone and NEVER fabricates cells to fill gaps.

### Claude's Discretion
- Harness module location + the results-artifact format (JSON cells + a generated Markdown review surface), the specificity/mode-fidelity heuristics, whether the autonomous pass runs fresh real cells vs reuses the floor data + a small fresh sample, the exact track subset — planner's call, smallest useful instrument, follow `library/`/`llm/` + the existing `/tmp/truthtest` shapes.
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `/tmp/truthtest/` — the floor-data harness: `bench_models.py` (4-model bench), `run_test.py` (truth-test), `bench_results.json` (3-model-3-genre disagreement = the raw-ear-unreliable proof), 6 real track excerpts (`t1..t6`). The intuition + tracks to fold in.
- The Phase 77-80 stack: `state/coach.py` (prompt/evidence), `state/evidence_registry.py` + `CitationLinter` (groundedness scoring reuse), `prompts/matrix.py` `build_lens_instruction` (the lens dimension), the gated secondary-ear framing (the audio+DSP grounding axis), `llm/model_router.py` (`resolve` — the model dimension; `live_coach` alias is GROUND-02's swap point).
- `library/budget.py` / the cost telemetry (`library budget --json`) — bound + report the bench spend.

### Established Patterns
- Gemini-only; `model_router.resolve(...)` for every model (the bench's model axis sweeps router aliases, no hardcoded literals); offline-testable with fake clients; honest green (never fake results).
- The earlier session already made real bench calls on the funded key (precedent for the produce step).

### Integration Points
- `llm/model_router.py` (model axis), `prompts/matrix.py` + `state/coach.py` (grounding/prompting/contexting/lens axes), `CitationLinter`/`EvidenceRegistry` (groundedness eval), the bench results artifact → the BENCH-03 review surface.

### Verification reality
- Honest green OFFLINE: the harness sweep + cell assembly + the eval scorers are unit-tested with fixture cells + a fake client — zero API calls. The real-cell RUN is the live produce step on the funded key (documented, bounded, fail-safe). BENCH-03 (Kaan's verdict) is the HARD HUMAN GATE — parked, never faked.
</code_context>

<specifics>
## Specific Ideas
- This is the phase that PROVES the milestone thesis: the "no-audio / DSP-evidence-only" cell tests whether the intelligence resides in the structured evidence (the EAR) rather than Gemini's raw ear — the empirical heart of "One Mind". The 3-model-3-genre floor (already captured) is the baseline.
- The bench is multi-DIMENSIONAL by Kaan's explicit instruction (model × DSP-grounding × prompting × contexting × lens × taste) — he was emphatic this is not one cell. Honor the full dimensionality in the harness; scope the RUNS to the two focused studies.
- The auto-eval RANKS; Kaan's ear DECIDES. Keep that separation sacred.
</specifics>

<deferred>
## Deferred Ideas
- Kaan's-ear verdict + the winning-architecture/model SELECTION → KAAN-ACTION (the BENCH-03 gate; never automated).
- Acting on the verdict (setting `live_coach` to the winning model, making the winning architecture the default) → follow-up after Kaan judges.
- A full cartesian run across the entire library → out (cost + not needed; the two focused studies + the no-audio cell answer the question).
- Curator+co-host engine/taste unification → Phase 82.
</deferred>
