---
phase: 81-bench-the-validation-instrument
reviewed: 2026-05-26T00:00:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - src/vibemix/bench/assemble.py
  - src/vibemix/bench/cell.py
  - src/vibemix/bench/eval.py
  - src/vibemix/bench/fixtures.py
  - src/vibemix/bench/matrix.py
  - src/vibemix/bench/review.py
  - src/vibemix/bench/run.py
  - src/vibemix/bench/__init__.py
  - src/vibemix/__main__.py
findings:
  critical: 0
  warning: 4
  info: 3
  total: 7
status: issues_found
---

# Phase 81: Code Review Report

**Reviewed:** 2026-05-26
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

Reviewed the new `src/vibemix/bench/` subpackage (the multi-dimensional reaction-quality bench) and the `vibemix bench` CLI dispatch in `__main__.py`.

The load-bearing contracts hold up under adversarial reading:

- **NEVER-FAKE / produce-and-park:** `run.py`'s per-cell `try/except Exception` (lines 159-169) records `output=""` + `error=repr(e)[:160]`, appends the parked `BenchResult`, and the `for` loop continues — it never aborts and never fabricates a cell output. Confirmed against `_RaisingClient` in the test suite (16/16 bench tests pass). Verified the catch is intentionally broad (`# noqa: BLE001`).
- **Eval RANKS, never DECIDES:** `eval.py` has no `winner`/`verdict`/`decision` field on `CellScore` and `rank_cells` is a pure `sorted()`. No code path selects an architecture.
- **Empty verdict:** `review.py` renders `_VERDICT_PLACEHOLDER` with no code path writing a winner; errored cells render `**ERRORED — parked:**`, never fabricated output.
- **No model literals:** the model axis flows through `model_router.resolve(alias)`; `STUDY_*` stores router aliases only. Verified `library_auto_tag` / `live_coach` resolve in `_router_config._ROUTES`.
- **No key logging:** `results_to_json` serializes prompt/output/usage/error/axes only; `_library_genai_client` constructs the client from `GEMINI_API_KEY` but never logs the value.
- **Path scrubbing:** `review.py` routes prompts/outputs/track through `strip_leaks` (`_PATH_RE`), which scrubs unix/Windows/`~` absolute paths.

No BLOCKERS found. The defects below are correctness/robustness gaps that should be fixed before the live produce run, the most material being a silent cost-bounding miss on the entire STUDY_A sweep (WR-01) and an unguarded `resp.text` that can violate the `output==""` contract on a blocked real-API response (WR-02).

## Narrative Findings (AI reviewer)

## Warnings

### WR-01: Cost bounding is a silent no-op for the entire STUDY_A architecture sweep

**File:** `src/vibemix/bench/run.py:153-158`
**Issue:** The runner bounds cost via `meter.record(cell.model_path, ...)`. But `cell.model_path` is a **router alias** (`"library_auto_tag"` for all 10 STUDY_A cells and `NO_AUDIO_CELL`), while `SessionMeter.record` looks up pricing by `ROUTE_PRICING.get(path)`. The `ROUTE_PRICING` table (`library/budget.py:173-180`) keys on `"live_coach"`, `"debrief"`, `"embedding"` etc. — **`library_auto_tag` is not a key.** So `record()` falls into the `rate is None` branch: `cost_usd = 0.0`, `known = 0`. The "Cost is bounded via SessionMeter.record" claim in the module docstring is false for the arch study — every STUDY_A / no-audio cell bills $0.00 and the printed summary under-reports the real spend. STUDY_B happens to bill correctly only because one of its aliases (`live_coach`) coincides with a pricing key. This defeats the stated cost-bounding guardrail (the documented launch gate is "bound worst-case spend"). It does not over-bill or block, so it is not a BLOCKER, but the summary silently lies about cost.
**Fix:** Map the router alias to a pricing path before recording, or add `library_auto_tag` to `ROUTE_PRICING`. Minimal:
```python
# bench/run.py — map the bench alias to a pricing key (default to live_coach
# rates as the conservative reaction-model proxy).
_BENCH_PRICING_PATH = {"library_auto_tag": "live_coach", "live_coach": "live_coach"}
...
meter.record(
    _BENCH_PRICING_PATH.get(cell.model_path, "live_coach"),
    prompt=int(usage.get("prompt_token_count") or 0),
    cached=int(usage.get("cached_content_token_count") or 0),
    output=int(usage.get("candidates_token_count") or 0),
)
```
Alternatively add a `"library_auto_tag"` row to `ROUTE_PRICING` so the meter recognizes it (verify the printed summary shows non-zero `known` cost after a live run).

### WR-02: Unguarded `resp.text` can record `output=None`, violating the `output==""` contract

**File:** `src/vibemix/bench/run.py:146`
**Issue:** On the success path the runner does `output=resp.text`. With the real `google-genai` SDK, `response.text` returns **`None`** when the candidate has no text part (safety-blocked, `MAX_TOKENS` finish, function-call-only candidate). It can also *raise* on a multi-candidate/blocked response — that case is caught by the broad `except` and parked (fine). But the `None` case is NOT caught: it records a successful `BenchResult` with `output=None`, `error=None`. This violates the phase's "errored cells carry `output==""`" invariant and the never-fabricate framing (a None output is neither a real output nor a parked error). Downstream, `eval._text_of` coerces with `or ""` so it won't crash, but `review._output_of` renders `> None`, and the success/parked distinction is corrupted. The offline `_FakeClient` always returns a string, so the gate cannot catch this — it only surfaces on a real blocked response.
**Fix:** Coerce to a string and treat an empty/blocked candidate as a parked cell, not a fabricated success:
```python
text = resp.text or ""
if not text:
    results.append(BenchResult(
        cell=cell, prompt=prompt_text, output="",
        dsp_snapshot=fixture_snapshot_for(cell), usage=usage,
        error="empty_candidate (blocked/no-text response)",
    ))
    continue
results.append(BenchResult(cell=cell, prompt=prompt_text, output=text, ...))
```

### WR-03: No per-call wall-clock timeout — a hung real-API call blocks the whole sweep indefinitely

**File:** `src/vibemix/bench/run.py:135-140`
**Issue:** The phase brief calls for "timeout/wall-clock" bounding on the real-API path (the Viber/Telegram surface already runs each Gemini request under a wall-clock timeout per the no-hang checklist). The bench `generate_content` call has **no timeout** — no `config` with `http_options.timeout`, no `concurrent.futures` wall-clock guard. A single stalled connection (network wedge, server hang short of an HTTP error) blocks the entire study sweep forever with no recovery, defeating the "sweep always completes / parks-and-continues" guarantee. The 429 fail-safe only fires on an *exception*; a silent hang is not an exception.
**Fix:** Pass a request timeout via the genai config so a stall raises (then the existing fail-safe parks it):
```python
from google.genai import types
resp = client.models.generate_content(
    model=model,
    contents=call_contents,
    config=types.GenerateContentConfig(
        http_options=types.HttpOptions(timeout=60_000)  # ms — stall -> exception -> parked
    ),
)
```
Note this also resolves the `config=None` (WR-related) call shape — currently every cell passes `config=None`, so any per-cell generation config (temperature, safety, response budget) is unset and not part of the bench axes.

### WR-04: Dict-stand-in support is half-implemented — scoring/grouping a JSON-reloaded cell silently mis-scores

**File:** `src/vibemix/bench/eval.py:84-90` and `src/vibemix/bench/review.py:62-94`
**Issue:** Both `eval._lens_of` and `review._group_key` / `_coordinates_line` advertise "dict stand-in" support, and `results_to_json` serializes the cell as a **nested dict** (`r["cell"]["lens"]`, `r["cell"]["grounding"]`, …). But the dict handling only inspects top-level keys: `_lens_of` does `getattr(cell, "lens", None)` then `result.get("lens")` — neither reaches `result["cell"]["lens"]`, so a reloaded JSON cell **always scores lens as `"hype"`** (the default). Likewise `_group_key` reads `getattr(cell, "grounding", None)` on a dict (always None) → every reloaded cell falls under `_UNGROUPED`, and `_coordinates_line` renders `model=`?`` for every field. This is latent today (no `results_from_json` loader exists and no CLI re-scores the artifact — eval/review have zero production callers; see IN-01), but the moment anyone scores/renders the persisted JSON, lens-fidelity and the grounding grouping (the milestone's headline axis) are silently wrong.
**Fix:** Read the nested cell dict consistently. Centralize a `_cell_of(result)` helper that handles both the object and the nested-dict shapes, then read axes off it:
```python
def _cell_of(result):
    if isinstance(result, dict):
        return result.get("cell")
    return getattr(result, "cell", None)

def _axis(cell, name, default):
    if isinstance(cell, dict):
        return cell.get(name, default)
    return getattr(cell, name, default)
```
Use `_axis(_cell_of(result), "lens", "hype")` / `"grounding"` in both modules.

## Info

### IN-01: `eval.py` and `review.py` have no production caller — the produce → score → review loop is not wired

**File:** `src/vibemix/__main__.py:1719-1750` (only `bench run` is wired)
**Issue:** The CLI exposes only `bench run` (the producer). There is no `bench score` / `bench review` subcommand and no `results_from_json` loader, so `score_cell` / `rank_cells` / `render_review` are reachable only from unit tests. The recorded JSON artifact cannot be turned into the KAAN-ACTION review surface without manual scripting. This is consistent with "review is a parked KAAN-ACTION", but the eval/review modules are effectively dead from the shipped CLI's perspective, and WR-04's dict bug stays hidden because of it.
**Fix:** Add a `bench review --in bench_run.json --out 81-REVIEW-cells.md` subcommand that loads the artifact, scores via `score_cell`, and writes `render_review(...)`. This also forces WR-04 to be exercised end-to-end.

### IN-02: Markdown blockquote only prefixes the first line of a multi-line reaction

**File:** `src/vibemix/bench/review.py:152`
**Issue:** `f"> {_scrub(_output_of(result))}"` wraps the whole (possibly multi-line) output in a single `> ` prefix. A reaction containing `\n` renders only its first line as a blockquote; the rest drops out of the quote block. Cosmetic only (the full output is in the JSON artifact), but the review surface is the human-judgment surface, so readability matters.
**Fix:** Prefix every line: `"\n".join(f"> {ln}" for ln in _scrub(_output_of(result)).split("\n"))`.

### IN-03: `strip_leaks` scrubs paths but not API-key-shaped tokens

**File:** `src/vibemix/bench/review.py:49-51` (via `telegram_bridge._PATH_RE`)
**Issue:** The T-81-11 framing is "never a key or a personal path". `strip_leaks`/`_PATH_RE` only scrubs filesystem paths — an `AIzaSy…`-shaped Gemini key would pass through untouched. In practice the bench prompt/output bodies never contain the key (the key lives only in client construction, never in prompt text), so there is no actual leak vector today. Flagging for defense-in-depth: if a future prompt ever echoes env/config, the scrubber would not catch a key.
**Fix:** Optionally extend the scrub with a key pattern (e.g. `AIza[0-9A-Za-z_\-]{35}` → `[key]`) for the review surface, or document that key-scrubbing relies on keys never entering prompt bodies.

---

_Reviewed: 2026-05-26_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
