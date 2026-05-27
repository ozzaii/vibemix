# Phase 81: BENCH — The Validation Instrument - Pattern Map

**Mapped:** 2026-05-26
**Files analyzed:** 13 new files (7 `bench/` modules + 6 test/data items) + 1 verification (no source mods)
**Analogs found:** 13 / 13 (every new file has a strong in-tree analog)

> This phase is COMPOSITION + REUSE over existing seams in a NEW `src/vibemix/bench/` subpackage.
> The harness re-wires verified pure functions; the only genuinely-new authored content is the tiny
> fixed taste-rubric string and the deterministic specificity/lens-fidelity heuristics.
> **No source files are modified** — `bench/` is purely additive (the model-literal grep-gate must NOT
> add `bench/` to its allowlist; see Shared Pattern: Model resolution).

---

## File Classification

| New File | Role | Data Flow | Closest Analog | Match Quality |
|----------|------|-----------|----------------|---------------|
| `src/vibemix/bench/__init__.py` | package | — | `src/vibemix/runtime/__init__.py` | exact |
| `src/vibemix/bench/cell.py` | model (dataclass) | transform | `coach/citation_linter.py` `LintResult` (frozen dataclass) | exact |
| `src/vibemix/bench/matrix.py` | config | transform | `prompts/matrix.py` `LENS_TO_MODE_MOOD` (fixed study/lens tables) | role-match |
| `src/vibemix/bench/assemble.py` | service (composer) | transform | `prompts/matrix.py` `build_lens_instruction` (thin composition over seams) | exact |
| `src/vibemix/bench/fixtures.py` | utility (builders) | transform | `state/coach.py` `evidence_line` callers / `MusicState` ctor | role-match |
| `src/vibemix/bench/run.py` | service (runner) + CLI | request-response (injected client) | `library/agent.py` `_gemini_call` + `/tmp/truthtest/bench_models.py` | exact |
| `src/vibemix/bench/eval.py` | service (scorers) | transform (pure) | `coach/citation_linter.py` `CitationLinter.check` | exact |
| `src/vibemix/bench/review.py` | utility (renderer) | transform (JSON→MD) | `runtime/soak.py` (dev-instrument report render) | role-match |
| `tests/bench/conftest.py` | test (fixtures) | — | `/tmp/truthtest/run_test.py` (`_FakeClient` + state builders) | role-match |
| `tests/bench/test_assemble.py` | test | — | `tests/prompts/test_matrix.py` | role-match |
| `tests/bench/test_run_fake.py` | test | — | `library/agent.py` injected-client tests | role-match |
| `tests/bench/test_eval.py` | test | — | existing `CitationLinter` tests | role-match |
| `tests/bench/test_review.py` | test | — | deterministic-render tests | role-match |
| `tests/bench/test_no_model_literal.py` | test (repo-guard) | — | `tests/repo/test_repo_scrub.py` | role-match |
| `tests/bench/data/*.mp3` | fixture data | file-I/O | `/tmp/truthtest/t1..t8.mp3` (copy in) | exact |

---

## Pattern Assignments

### `src/vibemix/bench/cell.py` (model, transform)

**Analog:** `src/vibemix/coach/citation_linter.py` lines 56-77 (`LintResult` frozen dataclass)

The project convention is small frozen value dataclasses. `BenchCell` = the 6-D point;
`BenchResult` = recorded output + the DSP snapshot it was scored against (so the eval can re-run
`CitationLinter.check` against the cell's OWN snapshot).

**Convention to copy** (from `citation_linter.py:56`):
```python
@dataclass(frozen=True)
class LintResult:
    valid: bool
    citations_found: int
    missing: tuple[tuple[str, str], ...]
    reason: str
```

`BenchResult` MUST carry the `dsp_snapshot: dict[str, dict[str, tuple[float, ...]]] | None`
(the exact `EvidenceRegistry.snapshot()` shape — see `evidence_registry.py:322`) plus
`prompt: str`, `output: str`, `usage: dict`, and `error: str | None` (the fail-safe field).

---

### `src/vibemix/bench/assemble.py` (service/composer, transform) — THE HEART

**Analog:** `src/vibemix/prompts/matrix.py:964` `build_lens_instruction` (a thin layer that VALIDATES
then DELEGATES to the real builder — never re-authors prompt text).

This module composes ONE prompt per cell by calling the real product seams in sequence. **Verified
signatures** (all confirmed against live source):

**Seam: lens axis** (`prompts/matrix.py:964`):
```python
def build_lens_instruction(lens: str = "hype", skill: str = "intermediate", **kw: object) -> str:
```
`build_lens_instruction("hype", "intermediate")` is byte-identical to the v4 golden — the lens layer
sits strictly ABOVE `build_system_instruction`. Use `cell.lens` ∈ {`hype`, `critique`, `tutor`}
(validated against `LENS_TO_MODE_MOOD`, `matrix.py:950`).

**Seam: prompting axis (generic vs structured)** (`prompts/matrix.py:737`):
```python
def build_system_instruction(
    skill: str = "intermediate", mode: str = "hype", mood: str = "hype-man",
    *, include_citation_grammar: bool = True,
    include_listening_fallback: bool = True, include_tag_dsl: bool = True,
) -> str:
```
`structured` cell = all `include_*=True` (the live default, full anti-slop stack).
`generic` cell = `include_*=False` (byte-identical to the bare constant) OR the documented bare
`/tmp/truthtest` `PROMPT` literal — **the ONLY cell allowed a prompt literal** (the no-structure control).

**Seam: grounding-framing axis** (`prompts/matrix.py:599`):
```python
def build_parts_description(
    audio_seconds: float, has_mic_part: bool, has_lookahead_part: bool,
    secondary_ear: bool = False,
) -> str:
```
`secondary_ear=True` = the Phase-80 secondary-ear framing (only on the `audio+dsp` grounding cells).
Flag-OFF is byte-identical to the v8.0 baseline.

**Seam: contexting + grounding axes** (`state/coach.py:730`):
```python
def build_prompt(ev: Event, *, registry_snapshot=None, recall_moments=None, diet=False) -> str:
```
`structured` → pass `registry_snapshot=snap`; `generic` → pass `None`. The fixture `MusicState`
carries/omits trajectory fields for the `snapshot` vs `trajectory` contexting axis.

**Composition order** (verified all four are pure, no shared mutable state — from RESEARCH §141):
```python
system = build_lens_instruction(lens, skill, include_citation_grammar=structured, ...) \
       + (TASTE_RUBRIC if taste == "with_rubric" else "")
ev = Event(type="HEARTBEAT", state=fixture_state_for(contexting, grounding))
user_body = build_prompt(ev, registry_snapshot=(snap if structured else None))
parts_suffix = build_parts_description(audio_s, False, False, secondary_ear=(grounding in audio_dsp_set))
contents = [system + user_body + parts_suffix] + ([audio_part] if grounding_uses_audio else [])
model, tier = model_router.resolve(cell.model_path)   # NO literal
```

**THE NO-AUDIO CELL** (`dsp_only`, the milestone's empirical heart): NO audio Part is appended, but
`evidence_line`/`registry_snapshot` is fully populated. Tests `test_no_audio_cell` assert the contents
list has zero audio Parts yet a non-empty evidence body.

**Anti-pattern (Pitfall 1):** a prompt literal in `assemble.py` that isn't the documented generic control.

---

### `src/vibemix/bench/fixtures.py` (utility/builders, transform)

**Analog:** `state/coach.py:257` `evidence_line` (the field-driven additive grounding string) +
the real `MusicState` dataclass.

`fixture_state_for(contexting, grounding) -> (MusicState, snapshot)`. **Don't hand-roll dicts** — build a
real `MusicState` so the `evidence_line` additive gating (it gates trajectory/genre fields by presence)
exercises the real grounding paths. `snapshot` from `EvidenceRegistry().snapshot()` (`evidence_registry.py:322`):
```python
def snapshot(self) -> dict[str, dict[str, tuple[float, ...]]]:
```
- `snapshot` contexting = `MusicState(trajectory_narrative="", ...)` (cold, no `phase_history`/`long_arc`).
- `trajectory` contexting = same state with the multi-scale PERCEIVE-02 fields populated.

---

### `src/vibemix/bench/run.py` (service/runner + CLI, request-response with injected client)

**Analog A — injected client + wall-clock timeout:** `library/agent.py:335` `_gemini_call`:
```python
def _gemini_call(self, contents: list[types.Content], cfg: dict[str, Any]):
    """One generate_content call under a hard wall-clock timeout."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(self._client.models.generate_content, model=self._model, contents=contents, config=cfg)
        return fut.result(timeout=GEMINI_CALL_TIMEOUT_S)
```
`__init__(self, client: Any, ...)` (`agent.py:306`) — **client by injection** = the offline-green seam.

**Analog B — call shape + per-cell fail-safe + JSON record:** `/tmp/truthtest/bench_models.py:31-61`:
```python
def ask(model, path):
    data = Path(path).read_bytes()
    audio_part = types.Part.from_bytes(data=data, mime_type="audio/mp3")
    resp = client.models.generate_content(model=model, contents=[PROMPT, audio_part])
    u = resp.usage_metadata
    return resp.text, ..., getattr(u, "total_token_count", None)

for model in MODELS:
    for t in TRACKS:
        try:
            text, dt, tok = ask(model, f"/tmp/truthtest/{t}.mp3")
            per_model[t] = {"text": text, "latency_s": dt, "total_tokens": tok}
        except Exception as e:
            per_model[t] = {"error": repr(e)[:160]}   # <-- THE 429 FAIL-SAFE (Pitfall 2)
Path("...bench_results.json").write_text(json.dumps(bench, indent=2, ensure_ascii=False))
```
**The `except → {"error": repr(e)[:160]}` per-cell wrapper is MANDATORY** — the floor study's 429
billing block is the documented reason (Pitfall 2). A failed cell parks; the sweep continues.

**Cost feed (Shared Pattern below):** after each successful call, `SessionMeter.record(cell.model_path,
prompt=usage.prompt_token_count, cached=usage.cached_content_token_count, output=usage.candidates_token_count)`.

**CLI entry:** `uv run python -m vibemix bench run --study A` (documented produce step; real `genai.Client`
swapped for the fake client). Do NOT make it gate the autonomous suite — the offline path is the green proof.

---

### `src/vibemix/bench/eval.py` (service/scorers, pure transform)

**Analog — groundedness REUSES the linter verbatim:** `coach/citation_linter.py:94`:
```python
def check(self, text, registry_snapshot, *, mode: str = "live") -> LintResult:
    ...   # mode "live" (±1.0s) | "debrief" (±2.0s); reason ∈ {valid, no_citations, malformed_atom, invalid_atoms}
```
Groundedness scoring (RESEARCH §253), use `mode="debrief"` (looser ±2s, offline-appropriate — A3):
```python
res = linter.check(result.output, result.dsp_snapshot, mode="debrief")
groundedness = 1.0 if res.reason == "valid" else (0.5 if res.reason == "no_citations" else 0.0)
```
**Don't re-implement** — the linter IS the product's anti-slop gate (Invariant #2).

**Specificity scorer** (new pure heuristic over `prompts/negative_dict.py:24` `NEGATIVE_PHRASES`):
```python
from vibemix.prompts.negative_dict import NEGATIVE_PHRASES
# penalize ban-list hits, reward concrete numbers/named-elements, clamp
```
**Lens-fidelity scorer** (new pure heuristic, per-lens vocab anchors keyed to `LENS_TO_MODE_MOOD`).

Keep both deterministic + simple (RESEARCH §278) — **the eval RANKS, it does NOT decide** (Pitfall 5).

---

### `src/vibemix/bench/review.py` (utility/renderer, JSON→MD pure transform)

**Analog:** `runtime/soak.py` (the dev-instrument report-render precedent).

Pure `render_review(results, scores) -> str` (markdown). Groups ranked cells by study/dimension with
prompt + output + auto-scores. **Error cells render as `ERRORED — parked`, never as fake output.**

**Pitfall 5 (the cardinal rule):** the VERDICT section is literally empty:
```markdown
## VERDICT (Kaan fills this)
> _Kaan fills this in — the auto-rank is a sort, not a decision._
```
No code path writes a winner. Output → `KAAN-ACTION-BENCH.md` (the HARD HUMAN GATE artifact, BENCH-03).

---

### `tests/bench/conftest.py` (test fixtures)

**Analog:** `/tmp/truthtest/run_test.py` call shape + `library/agent.py` injected-client tests.

`_FakeClient` pattern (RESEARCH §234 — returns canned `text` + synthetic `usage_metadata`):
```python
class _FakeClient:
    def __init__(self, canned): self.models = self; self._canned = canned
    def generate_content(self, *, model, contents, config=None):
        text = self._canned.get(model, "that 303 line opened up [aud:bpm@0.0]")
        return SimpleNamespace(text=text, usage_metadata=SimpleNamespace(
            prompt_token_count=1900, candidates_token_count=40,
            total_token_count=1940, cached_content_token_count=0))
```
Plus `MusicState` fixture builders (delegate to `bench/fixtures.py`).

---

### `tests/bench/test_no_model_literal.py` (repo-guard)

**Analog:** `tests/repo/test_repo_scrub.py::test_retired_poc_files_stay_gone` (the repo-scrub guard idiom).

Assert no Gemini model literal appears anywhere under `src/vibemix/bench/` (Pitfall 4). Mirror the
existing CI grep `scripts/release/check_no_hardcoded_model.sh`; confirm `bench/` is NOT added to that
grep's allowlist.

---

### `tests/bench/data/*.mp3` (fixture data, file-I/O)

**Analog:** `/tmp/truthtest/t1..t8.mp3` (8 excerpts present now; copy 6-8 in).

Copy from `/tmp/truthtest/` into `tests/bench/data/` (outside `src/`, Pitfall 3 — `/tmp` is volatile +
the tracks must never enter the wheel). Reference via an env-overridable path (`VIBEMIX_BENCH_DATA_DIR`).
**Verify hatchling's wheel include list excludes the dir** (they live outside `src/`, so default-excluded —
confirm). The floor `/tmp/truthtest/bench_results.json` (70k, 4-model × 8-track) folds in as the read-only
baseline reference.

---

## Shared Patterns

### Model resolution (NO literals — CI grep-gated)
**Source:** `llm/model_router.py:44`
**Apply to:** `bench/assemble.py`, `bench/run.py`, `bench/matrix.py` (every model reference)
```python
def resolve(path: str) -> tuple[str, ServiceTier | None]:
```
Always `model, tier = model_router.resolve(cell.model_path)`. The model axis sweeps router aliases
(`live_coach`, `library_auto_tag`). `/tmp/truthtest/run_test.py:11` already does this:
`MODEL, TIER = model_router.resolve("library_auto_tag")`. A literal trips
`scripts/release/check_no_hardcoded_model.sh`. **Confirm `bench/` is not allowlisted.**

### Cost bounding / report
**Source:** `library/budget.py:206` `SessionMeter.record` + `:276` `.summary()` + `:329` `get_session_meter()`
**Apply to:** `bench/run.py` (real run only — the produce step)
```python
def record(self, path: str, *, prompt: int = 0, cached: int = 0, output: int = 0) -> None:
```
Feed it the real `usage_metadata` per cell; `get_session_meter().summary()` reports € per router-path
post-run (RESEARCH §354). Floor study: ~37 Flash calls ≈ low single-digit euro-cents.

### Frozen-dataclass value types
**Source:** `coach/citation_linter.py:56` `LintResult`
**Apply to:** `bench/cell.py` (`BenchCell`, `BenchResult`, `CellScore`) — `@dataclass(frozen=True)`,
matches `LintResult` / `CostProjection` convention.

### Fixed-constant prompt fragments (anti-prompt-injection)
**Source:** `prompts/matrix.py:51` `MOOD_PERSONAS` + `:950` `LENS_TO_MODE_MOOD`
**Apply to:** the new `TASTE_RUBRIC` string in `bench/matrix.py` (the taste axis) + `LENS_ANCHORS`.
Keep lens + taste as FIXED module constants, never user input (V5 Input Validation, T-77-02-01).
**Open Q1:** the final taste-rubric wording is a KAAN-ACTION — planner ships a tiny placeholder, marks
the real wording deferred. Do NOT block on it.

### Snapshot type contract (groundedness)
**Source:** `state/evidence_registry.py:322` `snapshot()` returns `dict[str, dict[str, tuple[float, ...]]]`
**Apply to:** `BenchResult.dsp_snapshot` field type — the EXACT shape `CitationLinter.check` consumes.
`parse_citations` (`evidence_registry.py:491`) is the atom parser the linter uses internally.

---

## No Analog Found

None. Every file maps to a strong in-tree analog. The only genuinely-new authored content (per
RESEARCH §296) is non-structural: (1) the tiny fixed `TASTE_RUBRIC` string, (2) the deterministic
`specificity`/`lens_fidelity` heuristics. Both are small constant/pure-function additions inside
the analog-backed module shells above.

---

## Metadata

**Analog search scope:** `src/vibemix/{prompts,state,coach,llm,library,runtime}/`, `/tmp/truthtest/`,
`tests/repo/`
**Files scanned:** 9 source files read/grepped; all RESEARCH line anchors re-verified against live tree
**Line-number corrections vs RESEARCH:** `evidence_line` is `coach.py:257` (RESEARCH said 256, off-by-one);
all other anchors confirmed exact (`build_parts_description:599`, `build_system_instruction:737`,
`build_lens_instruction:964`, `LENS_TO_MODE_MOOD:950`, `build_prompt:730`, `snapshot:322`,
`CitationLinter.check:94`, `resolve:44`, `SessionMeter.record:206`, `NEGATIVE_PHRASES:24`,
`_gemini_call:335`)
**Pattern extraction date:** 2026-05-26
