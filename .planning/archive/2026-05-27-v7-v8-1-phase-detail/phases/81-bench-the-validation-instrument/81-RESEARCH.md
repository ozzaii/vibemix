# Phase 81: BENCH — The Validation Instrument - Research

**Researched:** 2026-05-26
**Domain:** Dev/eval instrument — multi-dimensional Gemini prompt-bench over the live vibemix stack, offline-testable harness + pure scorers + human review surface
**Confidence:** HIGH (all integration seams read in the live tree; no external library research needed — Gemini-only, no new deps)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**BENCH-01 — the harness (offline-tested code + live produce path)**
- A bench harness module in the package (fold in the proven `/tmp/truthtest/bench_models.py` + `run_test.py` intuition + the 6 real track excerpts + the floor `bench_results.json`). Parameterized over the 6 dimensions; records each cell's full output to a results artifact.
- **Scope sanely (not the full cartesian explosion):** the charter's TWO focused studies — (A) architecture-axis with ONE fixed model (sweep grounding × prompting × contexting × lens × taste); (B) model-axis with the best architecture from (A). Plus the decisive "no-audio" cell. The harness CAN express the full matrix; the runs are the two studies.
- **Offline-green:** the harness is unit-testable with a FAKE genai client returning fixture cells — the cell-assembly, dimension-sweep, and results-recording logic prove out with zero API calls (honest green). The real run is a separate, documented invocation.
- Reuse the real grounding/evidence stack (Phase 77-80 wiring) to build the per-cell prompts so the bench measures the ACTUAL product, not a toy.

**BENCH-02 — automated first-pass eval (pure, offline)**
- Pure scoring functions over a recorded cell: **groundedness** (every citation/claim resolves in the cell's `EvidenceRegistry`/DSP-fact snapshot — reuse the `CitationLinter` logic), **specificity** (concreteness vs generic-AI-slop heuristics), **mode/lens-fidelity** (does a hype cell sound hype, a tutor cell teach, etc.).
- Unit-tested on FIXTURE cells (no live API) — deterministic scores. The auto-score RANKS cells; it does NOT decide (Kaan's ear decides).

**BENCH-03 — Kaan's-ear review surface (HARD HUMAN GATE — produce-and-park)**
- Generate a clean, human-readable **review surface** (a `KAAN-ACTION` artifact: ranked cells with their auto-scores + the per-cell prompt/output, grouped by study/dimension) so Kaan can read + judge "did it click / is it slop / which architecture + model wins".
- **The verdict is Kaan's, parked.** Autonomous produces the surface + the auto-ranking; it does NOT fill in the verdict, does NOT pick the winner, does NOT fake any cell output. The winning architecture + model selection (which feeds GROUND-02's `live_coach` alias + the default architecture) is a KAAN-ACTION.

**Real-cell run (the produce step)**
- **Documented live e2e path** on the funded key (`...32u744`, in `.env`; `load_dotenv(override=True)` from Phase 77 ensures it wins). One command runs the bounded study.
- **Cost-bounded:** a representative subset (the two focused studies on a few real tracks, Gemini Flash pricing) — not the full cartesian product across all tracks. Within the ~50€/mo dev budget; a few cents-to-low-€ one-time.
- **Fail-safe:** if the API errors / rate-limits / the key has issues, the run parks gracefully as KAAN-ACTION (the offline harness + eval + the existing floor data still ship the capability) — it NEVER blocks the autonomous milestone and NEVER fabricates cells to fill gaps.

### Claude's Discretion
- Harness module location + the results-artifact format (JSON cells + a generated Markdown review surface), the specificity/mode-fidelity heuristics, whether the autonomous pass runs fresh real cells vs reuses the floor data + a small fresh sample, the exact track subset — planner's call, smallest useful instrument, follow `library/`/`llm/` + the existing `/tmp/truthtest` shapes.

### Deferred Ideas (OUT OF SCOPE)
- Kaan's-ear verdict + the winning-architecture/model SELECTION → KAAN-ACTION (the BENCH-03 gate; never automated).
- Acting on the verdict (setting `live_coach` to the winning model, making the winning architecture the default) → follow-up after Kaan judges.
- A full cartesian run across the entire library → out (cost + not needed; the two focused studies + the no-audio cell answer the question).
- Curator+co-host engine/taste unification → Phase 82.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BENCH-01 | A multi-dimensional bench harness runs model × grounding × prompting × contexting × lens × taste on real tracks. | The 6 dimensions each map to a real product seam (see §Dimension→Seam Map). The harness = a `BenchCell` spec → prompt assembler → `generate_content` runner → JSON recorder. Folds `/tmp/truthtest` (the audio-Part + `model_router.resolve` pattern). Offline-testable with a fake client. |
| BENCH-02 | An automated first-pass eval scores groundedness (vs DSP facts), specificity, mode-fidelity per cell. | Groundedness reuses `CitationLinter.check(text, snapshot)` verbatim against the cell's own DSP-fact snapshot. Specificity + mode-fidelity = pure deterministic heuristics over `NEGATIVE_PHRASES` + per-lens vocabulary anchors. All unit-testable on fixture cells, zero API. |
| BENCH-03 | Bench cells surfaced for Kaan's-ear final judgment (KAAN-ACTION review surface). | A pure JSON→Markdown renderer groups ranked cells by study/dimension with prompt+output+auto-scores. Renderer is offline-testable (deterministic). The verdict field stays EMPTY — produce-and-park. |
</phase_requirements>

## Summary

Phase 81 builds a **dev/eval instrument**, not a runtime feature. The work is three pure-Python pieces plus one documented live invocation:

1. **The harness (BENCH-01)** — a `BenchCell` dataclass (one point in the 6-D matrix) → a **prompt assembler** that composes the cell's prompt by calling the *real* product seams (`build_lens_instruction`, `AICoach.build_prompt`, `build_parts_description`, `model_router.resolve`) → a **runner** that issues one `generate_content` call (audio Part optional, per the grounding axis) → a **recorder** that writes each cell verbatim to a JSON artifact. The runner takes an injected client, so a fake client returning canned text makes the whole sweep offline-green.

2. **The eval (BENCH-02)** — three pure scoring functions over a recorded cell. Groundedness *reuses the existing `CitationLinter`* against the cell's own DSP-fact snapshot (the cell carries its `EvidenceRegistry` snapshot, so "do the claims resolve?" is the linter's exact job). Specificity + mode/lens-fidelity are deterministic heuristics (negative-dictionary hits, lens-vocabulary anchors, length, number-density). Auto-score produces a *ranking*, never a verdict.

3. **The review surface (BENCH-03)** — a pure JSON→Markdown renderer that lays ranked cells out by study and dimension, each with its prompt, output, and auto-scores, plus an explicit empty **VERDICT (Kaan fills this)** section. This is the KAAN-ACTION artifact.

The **real run** is one documented command (`uv run python -m vibemix bench run --study A`) that swaps the fake client for a real `genai.Client` on the funded key, wrapped in a per-call fail-safe so any 429/auth/network error parks the cell as `{"error": ...}` and never fabricates output or blocks the milestone.

**Primary recommendation:** Create a new `src/vibemix/bench/` subpackage (the matrix is bench-specific orchestration, not library or llm concern). Reuse — never re-implement — `build_lens_instruction`, `AICoach.build_prompt`, `build_parts_description`, `CitationLinter`, `model_router.resolve`, and `SessionMeter`. The harness *expresses* the full 6-D matrix but the autonomous pass *runs* only the two focused studies + the no-audio cell on a 3-4 track subset. The cells in `/tmp/truthtest/` are the floor baseline; copy the 6-8 `.mp3` excerpts into a test/data home so the run is reproducible in-repo.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Matrix spec + dimension sweep | New `bench/` orchestration | — | Bench-specific; not a runtime concern. Belongs in its own dev-instrument home, parallel to how `runtime/soak.py` + `runtime/ttft.py` are dev instruments. |
| Per-cell prompt assembly | `bench/` (composes) | `prompts/matrix.py` + `state/coach.py` (owns the strings) | The bench must REUSE the real prompt builders, never re-author prompt text (that would measure a toy). The assembler is a thin composition layer over the product seams. |
| Model resolution | `llm/model_router.py` | — | Model axis sweeps router aliases (`live_coach`, `library_auto_tag`, etc.). No hardcoded literals — CI grep-gate enforced. |
| Gemini call | `bench/` runner | `google-genai` (injected client) | The runner owns the call shape (audio Part on/off per grounding axis) but takes the client by injection so the fake client makes it offline-green. |
| Groundedness scoring | `coach/citation_linter.py` (reused) | `state/evidence_registry.py` (snapshot type) | The linter ALREADY answers "do this text's citations resolve in this snapshot?" — exactly the groundedness question. Reuse verbatim; do not re-implement. |
| Specificity / lens-fidelity scoring | `bench/` (new pure heuristics) | `prompts/negative_dict.py` + `prompts/matrix.py` vocab | New deterministic functions; pull the ban-list + lens-vocabulary anchors from the existing prompt surface so the scorer measures the same slop the product bans. |
| Review surface render | `bench/` (pure JSON→MD) | — | A deterministic renderer; offline-testable, no API. |
| Cost bounding / reporting | `library/budget.py` `SessionMeter` (reused) | — | `SessionMeter.record(path, prompt=, output=)` already bills per router-path; the bench feeds it the real `usage_metadata` to report spend. |

## Standard Stack

No new dependencies. Everything is already pinned in `pyproject.toml`.

### Core (all existing)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `google-genai` | pinned | The sole AI provider — `client.models.generate_content(model, contents=[prompt, audio_part])` | Gemini-only is locked; `/tmp/truthtest` already uses this exact call shape `[CITED: /tmp/truthtest/run_test.py]` |
| Python stdlib `dataclasses` | 3.12 | `BenchCell` / `BenchResult` value types | Matches the project's frozen-dataclass convention (`LintResult`, `CostProjection`) `[VERIFIED: codebase grep]` |
| Python stdlib `json` | 3.12 | Results artifact + floor `bench_results.json` shape | `/tmp/truthtest` already writes `json.dumps(..., indent=2, ensure_ascii=False)` `[CITED: /tmp/truthtest/run_test.py]` |

### Supporting (reused product seams — NOT new code)
| Seam | Location | Purpose | Used By Dimension |
|------|----------|---------|-------------------|
| `build_lens_instruction(lens, skill, **kw)` | `prompts/matrix.py:964` | System instruction for hype/critique/tutor | **lens** axis |
| `build_system_instruction(skill, mode, mood, *, include_citation_grammar=, include_tag_dsl=, ...)` | `prompts/matrix.py:737` | Underlying prompt builder; toggling the `include_*` flags is the **prompting (generic vs structured)** knob | **prompting** axis |
| `AICoach.build_prompt(ev, *, registry_snapshot=, recall_moments=, diet=)` | `state/coach.py:730` | Per-event evidence packet body (the structured grounding) | **contexting** + **grounding** axes |
| `AICoach.evidence_line(state, *, registry_snapshot=)` | `state/coach.py:256` | The DSP-fact / trajectory / genre grounding string | **grounding** + **contexting** axes |
| `build_parts_description(audio_s, has_mic, has_lookahead, secondary_ear=)` | `prompts/matrix.py:599` | The audio-Part framing suffix; `secondary_ear=True` = the Phase-80 secondary-ear framing | **grounding** axis (audio+DSP framing) |
| `model_router.resolve(path)` | `llm/model_router.py:44` | `(model_id, ServiceTier)` per alias — the model axis | **model** axis |
| `CitationLinter().check(text, snapshot, mode=)` | `coach/citation_linter.py:94` | Groundedness verdict (citations resolve in snapshot?) | **BENCH-02 groundedness** |
| `EvidenceRegistry().snapshot()` | `state/evidence_registry.py:322` | The frozen DSP-fact snapshot each cell is scored against | **BENCH-02 groundedness** |
| `NEGATIVE_PHRASES` | `prompts/negative_dict.py:24` | The slop ban-list — the specificity scorer's negative signal | **BENCH-02 specificity** |
| `LENS_TO_MODE_MOOD` / `MOOD_PERSONAS` | `prompts/matrix.py:950 / 51` | Per-lens vocabulary anchors for mode-fidelity scoring | **BENCH-02 mode-fidelity** |
| `SessionMeter.record(path, prompt=, output=)` / `.summary()` | `library/budget.py:206` | Per-router-path cost bounding + report for the real run | **real-run cost cap** |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| New `bench/` subpackage | `library/bench.py` or `llm/bench.py` | Rejected: the matrix is neither a library nor an llm concern. It orchestrates BOTH plus `state/` + `prompts/`. A dedicated `bench/` home matches the dev-instrument precedent (`runtime/soak.py`, `runtime/ttft.py`) and keeps imports honest. |
| Reuse `CitationLinter` for groundedness | A new bench-only groundedness scorer | Rejected: the linter IS the groundedness question, already battle-tested + unit-covered. Re-implementing it would drift from the product's actual anti-slop gate (Invariant #2). |
| Copy the 6 `.mp3` excerpts in-repo | Reference them at `/tmp/truthtest` | Recommend copy: `/tmp` is volatile (cleared on reboot); the real run must be reproducible. Put them under a non-packaged test-data dir (excluded from the wheel) — see Pitfall 3. |

**Installation:** None — no new packages. (Slopcheck audit below confirms zero new external installs.)

**Version verification:** No registry verification needed — this phase installs nothing. All seams are first-party (`src/vibemix/`). The only third-party call is `google-genai`, already pinned + in active use across `library/agent.py`, `agent/dj_cohost.py`, and `/tmp/truthtest`.

## Package Legitimacy Audit

> This phase installs **no external packages**. The harness composes existing first-party seams and calls the already-pinned `google-genai`.

| Package | Registry | Disposition |
|---------|----------|-------------|
| (none) | — | No new installs — phase reuses existing pins |

**Packages removed due to slopcheck [SLOP] verdict:** none (no new packages proposed)
**Packages flagged as suspicious [SUS]:** none

*slopcheck not run because there is nothing to check — the phase adds zero dependencies. The single third-party dependency in play (`google-genai`) is an existing, in-use, pinned project dependency.*

## Dimension → Seam Map (the heart of BENCH-01)

The six dimensions each map to a real product knob. A `BenchCell` is one point in this space; the assembler composes them into ONE prompt + call config.

| Dimension | Values | Real seam(s) | How the assembler sets it |
|-----------|--------|--------------|---------------------------|
| **model** | router aliases (e.g. `live_coach`, `library_auto_tag`) + the candidates Kaan named | `model_router.resolve(path)` → `(model_id, tier)` | `model, tier = resolve(cell.model_path)`; pass `model=model` to `generate_content`. **NO literal.** |
| **input-grounding** | `raw_audio` \| `dsp_only` (no-audio) \| `audio+dsp` \| `audio+dsp+traj+genre` | audio Part on/off + `evidence_line` richness + `build_parts_description(secondary_ear=)` | `raw_audio` = audio Part only, generic prompt, no evidence. `dsp_only` = NO audio Part, evidence_line present (**the decisive "intelligence resides elsewhere" cell**). `audio+dsp` = audio Part + evidence + `secondary_ear=True` framing. `+traj+genre` = same but the fixture `MusicState` carries `trajectory_narrative` + `detected_genre`. |
| **prompting** | `generic` \| `structured` | `build_system_instruction(..., include_citation_grammar=, include_listening_fallback=, include_tag_dsl=)` | `generic` = the bare DJ prompt (like `/tmp/truthtest`'s `PROMPT`, or `include_*=False`). `structured` = the full anti-slop stack (`include_*=True`, the live default). |
| **contexting** | `snapshot` \| `trajectory` | `AICoach.build_prompt(ev, diet=)` over a `MusicState` with/without trajectory fields | `snapshot` = a `MusicState` with `trajectory_narrative=""`, no `phase_history`/`long_arc` (cold). `trajectory` = the same state populated with multi-scale fields (PERCEIVE-02). The `evidence_line` already gates these additively. |
| **lens** | `hype` \| `critique` \| `tutor` | `build_lens_instruction(lens, skill)` → resolves `(mode, mood)` via `LENS_TO_MODE_MOOD` | `instruction = build_lens_instruction(cell.lens, cell.skill)`. This is the system instruction; the evidence packet is the user content. |
| **taste** | `with_rubric` \| `without_rubric` | **A new small taste-rubric fragment** (see Open Q1) appended to the system instruction | `without` = base instruction. `with` = base + a short rubric string ("what 'clicked' means" — Kaan's lived-experience reward signal). **There is no existing taste-rubric layer in the tree** — this is the one genuinely-new authored string; keep it tiny + fixed (anti-prompt-injection: never user input). |

**Composability confirmed:** all of `build_lens_instruction`, `build_system_instruction`, `AICoach.build_prompt`, and `build_parts_description` are pure functions with no shared mutable state. The assembler calls them in sequence:

```
system_instruction = build_lens_instruction(lens, skill, include_citation_grammar=structured, ...)
                     + (TASTE_RUBRIC if taste=="with_rubric" else "")
ev = Event(type="HEARTBEAT", state=fixture_state_for(contexting, grounding))
user_body = AICoach.build_prompt(ev, registry_snapshot=snap if structured else None)
parts_suffix = build_parts_description(audio_s, False, False, secondary_ear=(grounding in audio_dsp_set))
contents = [system + user_body + parts_suffix] + ([audio_part] if grounding_uses_audio else [])
model, tier = model_router.resolve(model_path)
```

This is exactly the `/tmp/truthtest/run_test.py` shape, but the prompt is built from the product instead of a hardcoded `PROMPT` literal.

## Architecture Patterns

### System Architecture Diagram

```
              ┌─────────────── BenchCell (one matrix point) ───────────────┐
              │ model_path · grounding · prompting · contexting · lens · taste │
              └───────────────────────────┬────────────────────────────────┘
                                          │
                       ┌──────────────────▼───────────────────┐
                       │     PROMPT ASSEMBLER (bench/assemble)  │
                       │  reuses REAL product seams:            │
                       │   build_lens_instruction ─────┐        │
                       │   build_system_instruction ───┤        │
                       │   AICoach.build_prompt ───────┼─► prompt + parts
                       │   build_parts_description ─────┘        │
                       │   model_router.resolve ─► (model,tier)  │
                       └──────────────────┬─────────────────────┘
                                          │
              fixture client ◄────────────┤────────────► real genai.Client (funded key)
              (offline-green test)        │              (the documented produce run)
                                          ▼
                       ┌──────────────────────────────────────┐
                       │   RUNNER (bench/run)                   │
                       │   client.models.generate_content(...)  │
                       │   per-call try/except → park on error  │  ──► SessionMeter.record()
                       └──────────────────┬─────────────────────┘        (cost cap/report)
                                          │ each cell: {prompt, output, dsp_snapshot, usage}
                                          ▼
                       ┌──────────────────────────────────────┐
                       │   RECORDER  →  bench_run.json          │  (verbatim cells; floor = bench_results.json)
                       └──────────────────┬─────────────────────┘
                                          │
                       ┌──────────────────▼─────────────────────┐
                       │   EVAL (bench/eval) — PURE, OFFLINE      │
                       │   groundedness = CitationLinter.check()  │  ◄─ reuse
                       │   specificity  = neg-dict + num-density  │
                       │   lens_fidelity= per-lens vocab anchors  │
                       │   → per-cell auto-score (RANK only)      │
                       └──────────────────┬─────────────────────┘
                                          │
                       ┌──────────────────▼─────────────────────┐
                       │  REVIEW SURFACE (bench/review) PURE→MD   │
                       │  ranked cells by study/dimension +       │
                       │  prompt+output+scores + EMPTY VERDICT    │  ──► KAAN-ACTION-BENCH.md
                       └──────────────────────────────────────────┘
                                          │
                                  ┌───────▼────────┐
                                  │  KAAN'S EAR     │  (HARD HUMAN GATE — parked, never faked)
                                  └─────────────────┘
```

### Recommended Project Structure
```
src/vibemix/bench/
├── __init__.py
├── cell.py          # BenchCell + BenchResult dataclasses (the 6-D point + recorded output)
├── matrix.py        # study definitions: STUDY_A (arch-axis, 1 model), STUDY_B (model-axis), NO_AUDIO_CELL
├── assemble.py      # build_cell_prompt(cell) -> (system, contents, model, tier) — composes the real seams
├── fixtures.py      # fixture_state_for(contexting, grounding) -> MusicState + its EvidenceRegistry snapshot
├── run.py           # run_study(cells, client) -> list[BenchResult]; CLI entry; per-call fail-safe + SessionMeter
├── eval.py          # score_cell(result) -> CellScore (groundedness/specificity/lens_fidelity); pure
└── review.py        # render_review(results, scores) -> markdown str; pure

tests/bench/
├── test_assemble.py     # cell → prompt composition, dimension knobs, NO literal model names
├── test_run_fake.py     # full sweep with a FAKE client → results recorded (zero API)
├── test_eval.py         # scorers on fixture cells (deterministic)
└── test_review.py       # JSON → markdown render (deterministic, verdict-empty)

tests/bench/data/         # the 6-8 .mp3 excerpts copied from /tmp/truthtest (NOT packaged into the wheel)
```

### Pattern 1: Inject-the-client for offline-green
**What:** The runner takes `client` as a parameter; the fake client returns a canned `resp.text` + a synthetic `usage_metadata`.
**When to use:** Every test of the sweep/assembly/recording logic.
**Example:**
```python
# Source: pattern lifted from /tmp/truthtest/run_test.py + library/agent.py:_gemini_call
class _FakeClient:
    def __init__(self, canned: dict[str, str]): self.models = self; self._canned = canned
    def generate_content(self, *, model, contents, config=None):
        text = self._canned.get(model, "that 303 line opened up [aud:bpm@0.0]")
        return SimpleNamespace(text=text, usage_metadata=SimpleNamespace(
            prompt_token_count=1900, candidates_token_count=40, total_token_count=1940,
            cached_content_token_count=0))
# test: run_study(STUDY_A, client=_FakeClient({...})) → asserts N cells recorded, no network.
```

### Pattern 2: Groundedness = the existing linter against the cell's own snapshot
**What:** Each `BenchResult` carries the `EvidenceRegistry` snapshot used to build its prompt. Groundedness re-runs `CitationLinter.check(result.output, result.dsp_snapshot)`.
**When to use:** BENCH-02 groundedness score.
**Example:**
```python
# Source: coach/citation_linter.py:94 — reused verbatim
from vibemix.coach.citation_linter import CitationLinter
linter = CitationLinter()
res = linter.check(result.output, result.dsp_snapshot, mode="debrief")  # ±2s tol for offline scoring
groundedness = 1.0 if res.reason == "valid" else (0.5 if res.reason == "no_citations" else 0.0)
# A cell that cites a DSP fact present in its snapshot scores high; a fabricated [aud:..] scores 0.
```
Note: the no-audio (`dsp_only`) cell is the one where groundedness is *most* meaningful — if Gemini can ground a sharp reaction on the DSP snapshot alone (no audio Part), the intelligence resided in the EAR, not the raw ear. That is the empirical heart of the milestone.

### Pattern 3: Specificity + lens-fidelity as deterministic heuristics
**What:** Pure functions over the output text, scored against the existing slop ban-list + per-lens vocabulary.
**Example:**
```python
# specificity: penalize ban-list hits, reward concrete numbers/named-elements, cap on length
from vibemix.prompts.negative_dict import NEGATIVE_PHRASES
def specificity(text: str) -> float:
    slop = sum(1 for p in NEGATIVE_PHRASES if p.lower() in text.lower())
    nums = len(re.findall(r"\d+\s?(?:hz|bpm|db|bar|s)\b", text.lower()))   # concrete measures
    named = sum(t in text.lower() for t in ("kick","303","sub","hat","reese","pad","filter"))
    return clamp(0.4 + 0.15*nums + 0.1*named - 0.5*slop, 0.0, 1.0)

# lens-fidelity: does a hype cell read hype, a tutor cell teach? anchor vocab per lens
LENS_ANCHORS = {"hype": ("drop","sick","cooking","energy"),
                "critique": ("try","muddied","tighten","clashing","kill"),
                "tutor": ("because","technique","phrase","structure","that's why")}
def lens_fidelity(text: str, lens: str) -> float:
    hits = sum(a in text.lower() for a in LENS_ANCHORS[lens])
    return clamp(hits / 2.0, 0.0, 1.0)
```
These are intentionally simple + deterministic — the auto-score RANKS; Kaan's ear DECIDES. Do not over-engineer the heuristics into a pseudo-judge.

### Anti-Patterns to Avoid
- **Re-authoring prompt text in the bench.** The whole point is to measure the *real* product. Always call `build_lens_instruction` / `AICoach.build_prompt`, never paste a prompt literal (except the `generic`-prompting cell, which deliberately uses the bare `/tmp/truthtest` DJ prompt as the no-structure control).
- **Hardcoding a Gemini model literal.** The model axis MUST be router aliases. A literal trips `scripts/release/check_no_hardcoded_model.sh`. (Confirm `bench/` is NOT added to that grep's allowlist.)
- **The auto-score "deciding."** The eval ranks. The review surface's VERDICT section stays empty. Synthesizing a winner is the one forbidden move (Invariant: BENCH-03 is Kaan's).
- **Cartesian explosion.** The matrix has 4×2×2×3×2 = 96 cells per model before the model axis. Running all of it on all tracks is cost + time waste. Run the two focused studies (A: ~12-24 arch cells × 1 model × 3-4 tracks; B: best-arch × 3-4 models × 3-4 tracks) + the single no-audio cell.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Groundedness scoring | A new citation/claim resolver | `CitationLinter.check()` | It IS the product's anti-slop gate; reuse keeps the bench honest to Invariant #2 |
| Model name resolution | A model-name table in `bench/` | `model_router.resolve()` | CI grep-gate forbids literals; the router is the single source of truth |
| Cost bounding/report | A cost calculator | `SessionMeter.record()/.summary()` | Already bills per router-path with cache split; feed it `usage_metadata` |
| Prompt assembly | A bench prompt template | `build_lens_instruction` + `AICoach.build_prompt` + `build_parts_description` | Measure the real product, not a toy |
| Fixture `MusicState` | Ad-hoc dicts | `MusicState(...)` dataclass with the real additive fields | The `evidence_line` gating is field-driven; a real dataclass exercises the real grounding paths |

**Key insight:** This phase is almost entirely *composition + reuse*. The only genuinely-new authored content is (1) the tiny fixed taste-rubric string and (2) the deterministic specificity/lens-fidelity heuristics. Everything else wires existing, tested seams together.

## Common Pitfalls

### Pitfall 1: Measuring a toy instead of the product
**What goes wrong:** The bench bakes its own prompt strings, so the result tells you nothing about the shipped co-host.
**Why it happens:** It's faster to paste a prompt than to compose the real builders.
**How to avoid:** The assembler imports and calls the real seams. The `generic`-prompting control is the ONLY cell allowed a bare prompt, and it's labeled as the no-structure baseline.
**Warning signs:** A prompt literal in `bench/assemble.py` that isn't the documented generic control.

### Pitfall 2: A 429/auth error blocks the autonomous milestone
**What goes wrong:** The funded key hits a rate limit mid-run and the whole phase fails (this exact 429 already blocked the floor-data study — see `.planning/archive/2026-05-27-stale-one-mind-research/gemini-audio-truth-test.md`).
**Why it happens:** No per-call fail-safe.
**How to avoid:** Wrap each `generate_content` in try/except (mirror `/tmp/truthtest`'s `per_model[t] = {"error": repr(e)[:160]}`). A failed cell records `{"error": ...}` and the run continues + parks gracefully. The offline harness + eval + the existing `bench_results.json` floor data still ship the capability regardless of whether the live run completes.
**Warning signs:** No `try/except` around the call; a single failure aborting the sweep.

### Pitfall 3: `/tmp` excerpts vanish; or test-data ships in the wheel
**What goes wrong:** `/tmp/truthtest/*.mp3` is cleared on reboot → the real run can't find tracks. Or the excerpts get bundled into the distributed binary (bloat + the tracks are Kaan's, not redistributable).
**How to avoid:** Copy the 6-8 excerpts into `tests/bench/data/` (or `.planning/phases/81-.../assets/`), and confirm hatchling's wheel `[tool.hatch.build]` does NOT include them (they live outside `src/`). Reference them by an env-overridable path so CI/other machines can point elsewhere.
**Warning signs:** A hardcoded `/tmp/truthtest/...` path in committed code; `.mp3` files appearing under `src/vibemix/`.

### Pitfall 4: The grep-gate trips on a model literal
**What goes wrong:** Someone writes `model="gemini-3-flash-preview"` in the bench for convenience.
**How to avoid:** Always `model, tier = model_router.resolve(alias)`. Add a `tests/bench/` assertion that no module under `bench/` contains a Gemini literal, mirroring the existing CI gate.
**Warning signs:** `check_no_hardcoded_model.sh` failing on a `bench/` path.

### Pitfall 5: The auto-score creeps into a verdict
**What goes wrong:** The ranking gets presented as "the winner is X," pre-empting Kaan's ear.
**How to avoid:** `review.py` renders a VERDICT section that is literally empty (`> _Kaan fills this in — the auto-rank is a sort, not a decision._`). No code path writes a winner.
**Warning signs:** A `winner` field populated by anything other than a human edit.

## Runtime State Inventory

> This is a greenfield dev-instrument phase (new `bench/` subpackage + test data). No rename/refactor/migration. The only stored artifact is the bench results JSON, which is freshly written, not migrated.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — the bench writes a fresh `bench_run.json`; the floor `bench_results.json` is read-only reference. No DB/datastore keys change. | None |
| Live service config | None | None |
| OS-registered state | None | None |
| Secrets/env vars | `GEMINI_API_KEY` (already loaded via Phase-77 `load_dotenv(override=True)`); optional new `VIBEMIX_BENCH_DATA_DIR` to override the excerpt path (read-only, no rename) | None — reuse existing key |
| Build artifacts | The `.mp3` excerpts must NOT enter the wheel (live outside `src/`) | Verify hatchling include list excludes `tests/bench/data/` |

## Code Examples

### The real-run command (the documented produce step)
```python
# Source: composed from /tmp/truthtest/run_test.py + library/agent.py:_gemini_call pattern
# `uv run python -m vibemix bench run --study A`
import os
from google import genai
from vibemix.bench.run import run_study
from vibemix.bench.matrix import STUDY_A
from vibemix.library.budget import get_session_meter

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])  # funded key, override=True from Phase 77
results = run_study(STUDY_A, client=client, tracks=("t1_pyrez_darkside", "t3_igda_runthehill"))
# run_study feeds SessionMeter.record(cell.model_path, prompt=usage.prompt_token_count, output=...)
print(get_session_meter().summary())   # bounded spend report, € per router-path
```

### Cost reality (from `budget.py` + the floor study)
Per `.planning/archive/2026-05-27-stale-one-mind-research/gemini-audio-truth-test.md`: 9 audio calls on Flash ≈ "single-digit euro-cents total." A bounded two-study run (~24 arch cells + ~12 model cells + 1 no-audio = ~37 calls × ~2k audio tokens in + ~400 out) on Flash is on the order of **low single-digit euro-cents** — trivially within the €50/mo dev budget. `SessionMeter.summary()` reports the exact figure post-run.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `/tmp/truthtest` standalone scripts (hardcoded `PROMPT`, raw audio only) | In-package `bench/` composing the real Phase 77-80 stack across 6 dimensions | This phase | The bench measures the shipped product, not a one-off probe |
| Floor study = 1 prompt × N models × raw audio (the 3-model-3-genre disagreement) | Multi-dimensional matrix incl. the no-audio / DSP-only cell | This phase | Tests the milestone thesis ("intelligence resides in the EAR"), not just raw-ear reliability |

**Deprecated/outdated:** nothing in the live tree — this is additive. `/tmp/truthtest` remains the floor baseline; its intuition + tracks fold in.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | No existing taste/rubric layer exists in the tree; the bench must author a small fixed taste-rubric fragment for the **taste** axis. | Dimension→Seam Map | LOW — verified by grep (no `rubric`/`taste` module). If a layer is added later, the bench points at it instead. The rubric string is tiny + fixed; planner confirms wording with Kaan or marks it KAAN-ACTION. |
| A2 | The two focused studies + no-audio cell are the right RUN scope (harness still expresses the full matrix). | Matrix scope | LOW — directly from CONTEXT.md locked decision + charter. |
| A3 | `CitationLinter` in `debrief` mode (±2s) is the right tolerance for offline groundedness scoring of static cells. | BENCH-02 | LOW — debrief tolerance is the looser, offline-appropriate band; live ±1s assumes a running clock the bench doesn't have. |
| A4 | Copying the `.mp3` excerpts into `tests/bench/data/` (outside `src/`) is acceptable re: redistribution (test-only, not packaged). | Pitfall 3 | LOW — they're Kaan's own tracks used as fixtures, never shipped in the wheel. Confirm hatchling excludes the dir. |

## Open Questions

1. **The taste-rubric fragment wording.**
   - What we know: there's no taste layer in the tree; the **taste** axis needs a small fixed "what clicked means" rubric string (Kaan's lived-experience reward signal — the charter's SOUL).
   - What's unclear: the exact wording. It's load-bearing IP, like the HYPE_INTERMEDIATE prompt.
   - Recommendation: planner drafts a minimal placeholder rubric, marks the *final* wording a KAAN-ACTION (Kaan authors his own taste). The bench works with the placeholder; the real verdict run can use Kaan's wording when he supplies it. Do NOT block on it.

2. **Which model aliases populate the model axis (Study B).**
   - What we know: `model_router` exposes `live_coach` (gemini-3.5-flash), `library_auto_tag` (gemini-3-flash-preview), `debrief` (gemini-3-pro-preview). The floor study probed 2.5-flash / 3-flash-preview / 3.5-flash / native-audio.
   - What's unclear: whether to add new router aliases for bench-only candidates (e.g. a `bench_2_5_flash` alias) or sweep the existing ones.
   - Recommendation: sweep the existing aliases that are plausible reaction-model candidates (`live_coach`, `library_auto_tag`). If Kaan wants a model not in the router, add it as a router alias (one-line edit in `_router_config.py`) — never a literal in `bench/`.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `google-genai` | the real run only | ✓ (pinned, in use) | per `uv.lock` | offline harness + eval + floor data ship without it |
| Funded `GEMINI_API_KEY` | the real run only | ✓ in `.env` (`...32u744`, override=True) | — | per-call fail-safe → park as KAAN-ACTION; offline gate still green |
| `/tmp/truthtest/*.mp3` (6-8 excerpts) | the real run | ✓ present now (volatile) | — | copy into `tests/bench/data/`; env-override path |
| `ffmpeg` | only if re-cutting excerpts | (excerpts already cut) | — | not needed — reuse existing excerpts |

**Missing dependencies with no fallback:** none. The offline-green gate (harness + eval + review render with a fake client) requires zero external dependencies.
**Missing dependencies with fallback:** the live run depends on a funded key + network; both fail-safe into a parked KAAN-ACTION without blocking.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (already configured; `[tool.pytest.ini_options]` in `pyproject.toml`) |
| Config file | `pyproject.toml` (`addopts = "-ra --strict-markers"`) |
| Quick run command | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q tests/bench/` |
| Full suite command | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BENCH-01 | A `BenchCell` assembles into a prompt that reuses the real seams; no model literal | unit | `pytest tests/bench/test_assemble.py -x` | ❌ Wave 0 |
| BENCH-01 | Full study sweep records N cells via a FAKE client, zero API | unit | `pytest tests/bench/test_run_fake.py -x` | ❌ Wave 0 |
| BENCH-01 | The no-audio (`dsp_only`) cell sends NO audio Part but a populated evidence line | unit | `pytest tests/bench/test_assemble.py::test_no_audio_cell -x` | ❌ Wave 0 |
| BENCH-02 | Groundedness = `CitationLinter` against the cell's snapshot (cited-resolves → high; fabricated → 0) | unit | `pytest tests/bench/test_eval.py::test_groundedness -x` | ❌ Wave 0 |
| BENCH-02 | Specificity penalizes ban-list hits, rewards concrete measures (deterministic) | unit | `pytest tests/bench/test_eval.py::test_specificity -x` | ❌ Wave 0 |
| BENCH-02 | Lens-fidelity scores per-lens vocab anchors (deterministic) | unit | `pytest tests/bench/test_eval.py::test_lens_fidelity -x` | ❌ Wave 0 |
| BENCH-03 | Review render produces ranked Markdown with an EMPTY verdict section (no winner written) | unit | `pytest tests/bench/test_review.py -x` | ❌ Wave 0 |
| BENCH-01 | No Gemini model literal anywhere under `bench/` | repo-guard | `pytest tests/bench/test_no_model_literal.py -x` (or extend the CI grep) | ❌ Wave 0 |
| (parked) | The real two-study run on the funded key | manual / produce | `uv run python -m vibemix bench run --study A` | live — KAAN-ACTION |
| (parked) | BENCH-03 verdict — did it click / which wins | manual / human gate | (Kaan reads `KAAN-ACTION-BENCH.md`) | HARD HUMAN GATE — never automated |

### Sampling Rate
- **Per task commit:** `pytest -q tests/bench/`
- **Per wave merge:** full suite `pytest -q`
- **Phase gate:** full suite green before `/gsd:verify-work`; the offline gate is the honest-green proof. The live run + Kaan's verdict are parked KAAN-ACTIONs and do NOT gate the autonomous merge.

### Wave 0 Gaps
- [ ] `tests/bench/test_assemble.py` — covers BENCH-01 (cell→prompt composition, no-audio cell, no literal)
- [ ] `tests/bench/test_run_fake.py` — covers BENCH-01 (fake-client sweep, zero API)
- [ ] `tests/bench/test_eval.py` — covers BENCH-02 (groundedness/specificity/lens-fidelity scorers)
- [ ] `tests/bench/test_review.py` — covers BENCH-03 (deterministic render, empty verdict)
- [ ] `tests/bench/test_no_model_literal.py` — guards the model-literal grep over `bench/`
- [ ] `tests/bench/data/` — the 6-8 `.mp3` excerpts copied from `/tmp/truthtest` (test-only, not packaged)
- [ ] `tests/bench/conftest.py` — the `_FakeClient` fixture + `MusicState` fixture builders

## Security Domain

> This is an internal dev/eval instrument — no network surface beyond the existing `google-genai` call, no user input at runtime (the studies are fixed code-defined cells), no new ws port/IPC. `security_enforcement` applies lightly.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | n/a — no auth surface; reuses the existing `.env` key |
| V3 Session Management | no | n/a |
| V4 Access Control | no | n/a — local dev instrument |
| V5 Input Validation | partial | The taste-rubric + lens are FIXED constants, never user input (anti-prompt-injection — mirrors `MOOD_PERSONAS` / `LENS_TO_MODE_MOOD`). Track paths are env-overridable but read-only. |
| V6 Cryptography | no | n/a — never hand-roll; not in scope |

### Known Threat Patterns for this instrument
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Prompt-injection via a dynamic lens/taste string | Tampering | Keep lens + taste as fixed module constants; user theme (if any) never enters the system voice — same pattern as `build_curator_instruction` T-77-02-01 |
| API key leak into the results artifact | Info disclosure | The recorder writes prompt+output+usage only — never the key; path-scrub any track filenames if they carry personal paths (mirror the Telegram path-scrub) |
| Fabricated cell filling a gap (the cardinal sin) | Repudiation / integrity | Per-call fail-safe records `{"error": ...}`; the eval + review render error cells as `ERRORED — parked`, never as fake output. BENCH-03 verdict stays empty. |

## Sources

### Primary (HIGH confidence)
- `src/vibemix/prompts/matrix.py` — `build_lens_instruction`, `build_system_instruction`, `build_parts_description`, `LENS_TO_MODE_MOOD`, `MOOD_PERSONAS` (the lens/prompting/grounding-framing seams)
- `src/vibemix/state/coach.py` — `AICoach.build_prompt`, `evidence_line` (the contexting/grounding evidence packet)
- `src/vibemix/state/evidence_registry.py` — `EvidenceRegistry.snapshot()`, `parse_citations` (the groundedness snapshot type)
- `src/vibemix/coach/citation_linter.py` — `CitationLinter.check()` (groundedness reuse)
- `src/vibemix/llm/model_router.py` + `_router_config.py` — `resolve()` + the alias table (model axis; `live_coach` = the GROUND-02 swap point)
- `src/vibemix/library/budget.py` — `SessionMeter` (cost bounding/report)
- `src/vibemix/prompts/negative_dict.py` — `NEGATIVE_PHRASES` (specificity scorer)
- `/tmp/truthtest/run_test.py` + `bench_models.py` — the call-shape + audio-Part + fail-safe + JSON-record pattern to fold in
- `.planning/archive/2026-05-27-stale-one-mind-research/one-mind-charter.md` — the multi-dimensional bench spec + two-study scope + no-audio cell
- `.planning/archive/2026-05-27-stale-one-mind-research/gemini-audio-truth-test.md` — the floor study (3-model genre disagreement; the 429 billing block lesson → fail-safe requirement)
- `.planning/phases/81-bench-the-validation-instrument/81-CONTEXT.md` — locked decisions
- `pyproject.toml` — pytest markers + dependency pins

### Secondary (MEDIUM confidence)
- (none — all claims verified against the live tree)

### Tertiary (LOW confidence)
- (none)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every seam read directly in `src/vibemix/`; zero new deps; Gemini-only locked.
- Architecture: HIGH — the harness is composition over verified pure functions; the offline-green pattern is already proven (`library/agent.py` injected client + `/tmp/truthtest` call shape).
- Pitfalls: HIGH — the 429 fail-safe lesson is documented in the floor study; the model-literal grep-gate is an existing CI control.
- Taste-rubric wording: MEDIUM — the only genuinely-new authored string; flagged as Open Q1 / KAAN-ACTION.

**Research date:** 2026-05-26
**Valid until:** 2026-06-25 (stable — first-party seams; only Gemini model SKUs in `_router_config.py` drift, and those are isolated behind the router)
