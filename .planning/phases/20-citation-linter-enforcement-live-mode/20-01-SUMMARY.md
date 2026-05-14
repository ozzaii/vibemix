---
phase: 20-citation-linter-enforcement-live-mode
plan: 01
subsystem: coach
tags: [anti-slop, citation-linter, telemetry-guard, ack-bank, ground-04, ground-05, ground-06, ground-07]
requires:
  - phase: 18
    plan: 01
    why: "EvidenceRegistry.snapshot + EVIDENCE_SOURCES + parse_citations EBNF parser — linter walks the snapshot for every parsed atom"
  - phase: 19
    plan: 04
    why: "AckBank.pick_for_event + BUCKET_FOR_EVENT — strip-path fallback PCM source"
  - phase: 19
    plan: 05
    why: "wired/legacy guard pattern (4 kwargs default None → byte-identity preserved)"
provides:
  - "vibemix.coach package — CitationLinter, LintResult, StrippedRateTracker, 4 locked constants"
  - "DJCoHostAgent.llm_node post-stream binary citation gate (response-level, never token/partial)"
  - "Telemetry guard — one-shot bypass at stripped_rate > 0.4 over rolling 15s window"
  - "Ack-bank fallback on strip — silence > invented citation per anti-slop thesis"
  - "events.jsonl audit rows: citation_strip + citation_bypass with response_id + raw_text + missing + reason"
affects:
  - "src/vibemix/agent/dj_cohost.py — 4 new optional kwargs + post-stream gate ladder + meta.json fields"
tech-stack:
  added: []
  patterns:
    - "wired/legacy guard via _linter_wired flag computed once at __init__"
    - "deque-based rolling window with O(1)-amortized eviction"
    - "one-shot latch with recovery re-arm (_bypass_consumed)"
    - "stateless validator class — single instance shareable across agents"
key-files:
  created:
    - src/vibemix/coach/__init__.py
    - src/vibemix/coach/constants.py
    - src/vibemix/coach/citation_linter.py
    - src/vibemix/coach/stripped_rate.py
    - tests/coach/__init__.py
    - tests/coach/test_citation_linter.py
    - tests/coach/test_stripped_rate_tracker.py
    - tests/coach/test_linter_silence_streak.py
    - tests/agent/test_dj_cohost_linter.py
  modified:
    - src/vibemix/agent/dj_cohost.py
decisions:
  - "LintResult is frozen+slots dataclass with reason: str field — single source of truth for the decision tag, removes log-site re-inference"
  - "Untyped module-level floats in constants.py — satisfies grep-gate value lock literally; convention diverges from ack_bank.py's typed constants"
  - "4-kwarg all-or-nothing wiring (citation_linter / stripped_rate_tracker / ack_bank / playback) — preserves byte-identity for the entire Phase 4/10/18/19 dj_cohost test suite"
  - "Strip path NEVER fires ack when ev.type ∉ BUCKET_FOR_EVENT — silent strip recorded with ack_bucket=None; logged for ear-test review"
  - "Track-atom test uses spaceless slug form — EBNF body charset [^\\s,\\]]+ rejects whitespace at parse; plan narrative example was shorthand"
metrics:
  duration: "~50min"
  completed: "2026-05-14"
  tasks: 2
  test-cases-added: 33
  files-created: 9
  files-modified: 1
---

# Phase 20 Plan 01: CitationLinter Core + Telemetry Guard Summary

Anti-slop response-level binary citation linter ships LIVE with a rolling-window telemetry guard (one-shot bypass) and an ack-bank PCM fallback — wired into `DJCoHostAgent.llm_node` as the post-stream chokepoint after the silence/slop gate.

## What Shipped

### `vibemix.coach` package (new)

| Module | Public surface | Purpose |
|--------|---------------|---------|
| `constants.py` | `LIVE_TOLERANCE_S=1.0`, `DEBRIEF_TOLERANCE_S=2.0`, `STRIPPED_RATE_THRESHOLD=0.4`, `STRIPPED_RATE_WINDOW_S=15.0` | Locked floats; tolerance bands + rate-guard thresholds |
| `citation_linter.py` | `CitationLinter`, `LintResult` | Stateless response-level grounding validator |
| `stripped_rate.py` | `StrippedRateTracker` | Rolling-window stripped-rate + one-shot bypass |
| `__init__.py` | re-exports of all 7 names above | Package root import surface |

### `CitationLinter` API

```python
class CitationLinter:
    def __init__(self) -> None: ...  # stateless

    def check(
        self,
        text: str,
        registry_snapshot: dict[str, dict[str, tuple[float, ...]]] | None,
        *,
        mode: str = "live",  # or "debrief"; raises ValueError otherwise
    ) -> LintResult: ...
```

`LintResult` is a frozen+slots dataclass: `valid: bool`, `citations_found: int`, `missing: tuple[tuple[str, str], ...]`, `reason: str`. The reason field is a one-word tag — `"valid"` / `"no_citations"` / `"invalid_atoms"` / `"malformed_atom"` — and is the single source of truth for the decision (planner deviation #6, removes log-site re-inference).

**Decision ladder (response-level binary):**
1. `citations_found == 0` → `LintResult(False, 0, (), "no_citations")` — uncited reply == slop in live mode.
2. Any atom MALFORMED (time-keyed atom missing `@` or non-numeric `t`) → `reason="malformed_atom"`.
3. Any atom invalid against registry → `reason="invalid_atoms"`; `missing` lists every miss.
4. All atoms valid → `LintResult(True, n, (), "valid")`.

**Atom dispatch:** time-keyed sources (`ev` / `aud` / `midi`) split body on first `@` and validate `(source, key, t)` against `registry_snapshot[source][key]` within `±tol`. Existence-only sources (`track` / `screen` / `mix` / `tend`) check key presence only — no `@t`. Unknown sources never reach the linter (the EVIDENCE_CITATION_RE regex whitelists the 7 sources at parse time); defensive branch in `_validate_atom` treats them as malformed.

**Mode dispatch:** `"live"` → ±1.0s tolerance band; `"debrief"` → ±2.0s (Phase 25 architectural slot). Unknown modes raise `ValueError` — fail loud.

**Defensive:** `registry_snapshot=None` returns `no_citations` regardless of text. Cold-start state where nothing can be grounded → strip the response.

### `StrippedRateTracker` API

```python
class StrippedRateTracker:
    def __init__(
        self,
        *,
        window_s: float = STRIPPED_RATE_WINDOW_S,
        threshold: float = STRIPPED_RATE_THRESHOLD,
        time_fn: Callable[[], float] = time.monotonic,
    ) -> None: ...

    def record(self, stripped: bool) -> None: ...  # append + evict + maybe re-arm
    def rate(self) -> float: ...                   # 0.0 on empty buffer
    def should_bypass(self) -> bool: ...           # one-shot latch
```

**Internal state:** `collections.deque[(t, stripped_bool)]` for O(1)-amortized head eviction; `_bypass_consumed` boolean latch.

**One-shot semantics:** `should_bypass()` returns `True` exactly once when `rate() > threshold` AND `_bypass_consumed` is False. The latch flips True on firing and re-arms only when `record()` observes the post-eviction rate dropping back to `<= threshold`. This is the load-bearing T-20-01-02 mitigation: without one-shot semantics every response in a sustained breach window would emit `[unverified]` and the strip mechanism would be functionally disabled.

**Pitfall 2 lock:** synthetic 10-invalid-responses-in-12s burst (`tests/coach/test_linter_silence_streak.py`) verifies the bypass trips at t=3.6s, well before the 8.0s silence-streak ceiling.

### `DJCoHostAgent.llm_node` wiring

Four new optional kwargs on `__init__`, all default `None`:

```python
DJCoHostAgent(
    ...,
    citation_linter: CitationLinter | None = None,
    stripped_rate_tracker: StrippedRateTracker | None = None,
    ack_bank: AckBank | None = None,
    playback: PlaybackQueue | None = None,
)
```

`_linter_wired = all(x is not None for x in (...))` is computed once at `__init__`. The wired path runs iff all four are non-None — matches the Plan 19-05 wired/legacy guard pattern. Default-None preserves byte-identity for the Phase 4/10/18/19 dj_cohost test suite (88-test regression suite still green unchanged).

**Insertion point:** AFTER the existing silence/slop gate, replacing the `else` branch that previously emitted `buffered_chunks` unconditionally. Silence-suppressed and slop-suppressed turns are already non-emitting; layering the linter on top would mis-record the stripped rate.

**Post-stream gate ladder (when wired AND `suppression is None`):**

| Outcome | Yield chunks | Tracker.record | Ack played | Recorder log | History append |
|---------|--------------|----------------|------------|--------------|----------------|
| valid | yes | False | no | `ai_text` | yes |
| invalid + bypass (one-shot) | yes | False | no | `citation_bypass` | yes |
| invalid + strip + known event | no | True | yes (PCM via `pick_for_event(ev) → playback.push(pcm.tobytes())`) | `citation_strip` (`ack_bucket=<name>`) | no |
| invalid + strip + unknown event | no | True | no | `citation_strip` (`ack_bucket=None`) | no |

History append on bypass — the user heard the unverified text, so the no-repeat memory must reflect it. History NOT appended on strip — nothing was emitted.

**Snapshot reuse:** the linter receives the same `EvidenceRegistry.snapshot()` already taken at line ~216 for `AICoach.build_prompt`. No second `snapshot()` call per turn — eliminates a race window AND keeps the per-turn cost flat.

**Telemetry payload:**

`citation_strip` event:
```json
{
  "kind": "citation_strip",
  "response_id": "0001_HHMMSS",
  "raw_text": "<full LLM response>",
  "missing": [["ev", "UNKNOWN@99.0"]],
  "reason": "invalid_atoms",
  "ack_bucket": "generic_filler",
  "ack_sample_index": 3,
  "latency_s": 1.42
}
```

`citation_bypass` event:
```json
{
  "kind": "citation_bypass",
  "response_id": "0001_HHMMSS",
  "raw_text": "<full LLM response>",
  "missing": [["ev", "NONE@1.0"]],
  "reason": "invalid_atoms",
  "latency_s": 1.41
}
```

`meta.json` extended with 4 fields: `citation_lint_valid` / `citation_lint_reason` / `citation_lint_missing` / `citation_action` (`"emit"` | `"bypass"` | `"strip"` | `"skip"`). All None on the legacy path (`citation_action="skip"`).

`[llm ...]` console line gets a `linter=wired|skip` token next to `cache=` for coach-loop tail visibility.

## Verification

- `pytest tests/coach/ tests/agent/test_dj_cohost_linter.py` — **33/33 passed** (16 linter + 9 stripped-rate + 7 dj_cohost integration + 2 silence-streak pitfall + spillover assertions).
- `pytest tests/agent/test_dj_cohost*.py tests/coach/` — **88 + 33 = 121 passed**, no regressions on the legacy-path byte-identity suite.
- Full `pytest -q` — **1766 passed / 9 pre-existing failures unchanged** (was 1733 baseline; +33 net new tests).
- POC files (`cohost.py` / `cohost_v2.py` / `cohost_v4.py` / `cohost_lk.py`) untouched — `git diff --name-only HEAD~3 cohost*.py` returns empty.
- All `<done>` grep gates passed: `LIVE_TOLERANCE_S = 1.0` / `STRIPPED_RATE_THRESHOLD = 0.4` / `class CitationLinter` / `class StrippedRateTracker` count == 1; no third-party regex imports; no `token.level` / `partial.strip` substrings in citation_linter.py source; `from vibemix.coach import ...` exits 0.
- `self._linter` usage count in dj_cohost.py = 5 (≥3); `citation_strip|citation_bypass` count = 4 (≥2); `ack_bank.pick_for_event` call site count = 1 exactly (the strip-path call site, no other reference).

## Deviations from Plan

None — plan executed exactly as written.

**Two minor adjustments documented inline (already pinned in commit messages, not behavioral deviations):**

1. **Track-atom test example uses spaceless slug** (`MarlonHoffstadt-Atlas`) instead of the plan's narrative `Marlon Hoffstadt - Atlas`. The `EVIDENCE_CITATION_RE` body charset is `[^\s,\]]+` — whitespace is rejected at parse time. The narrative example was shorthand; Gemini emits the slug form at the citation boundary.

2. **`constants.py` constants are untyped module-level floats** (`LIVE_TOLERANCE_S = 1.0`) instead of `LIVE_TOLERANCE_S: float = 1.0`. The planner's grep-gate value lock (`grep -c "LIVE_TOLERANCE_S = 1.0"`) checks for the literal `name = value` substring. Type-annotated form would not match. Convention diverges slightly from `ack_bank.py`'s typed constants.

## Authentication Gates

None encountered. Pure Python implementation, no external API calls.

## Threat Coverage

| Threat | Disposition | Implementation |
|--------|-------------|----------------|
| T-20-01-01 (atom tampering) | mitigate | `_validate_atom` uses `body.partition("@")` + `float(...)` with try/except → MALFORMED. No eval/exec/shell. |
| T-20-01-02 (linter-induced silence DoS) | mitigate | `StrippedRateTracker` one-shot bypass; pinned by `test_should_bypass_above_threshold_fires_once` + `test_pitfall2_stripped_burst_trips_bypass_before_8s_silence`. |
| T-20-01-03 (false-positive cascade) | mitigate | Bypass fires < 8s on 10-invalid-in-12s burst (Pitfall 2 test). |
| T-20-01-04 (audit trail) | mitigate | Every strip + bypass writes `response_id` + `raw_text` + `missing` + `reason` to events.jsonl. |
| T-20-01-05 (raw_text disclosure) | accept | Local-only audit trail; UI surface (Plan 20-04) shows counts only. |
| T-20-01-06 (mode tampering) | mitigate | `mode` arg validated → `ValueError` on unknown. |
| T-20-01-07 (ack exhaustion) | accept | AckBank rotation deque maxlen=10 (Phase 19 mitigation). |

## Self-Check: PASSED

Files created:
- `src/vibemix/coach/__init__.py` — FOUND
- `src/vibemix/coach/constants.py` — FOUND
- `src/vibemix/coach/citation_linter.py` — FOUND
- `src/vibemix/coach/stripped_rate.py` — FOUND
- `tests/coach/__init__.py` — FOUND
- `tests/coach/test_citation_linter.py` — FOUND
- `tests/coach/test_stripped_rate_tracker.py` — FOUND
- `tests/coach/test_linter_silence_streak.py` — FOUND
- `tests/agent/test_dj_cohost_linter.py` — FOUND

File modified:
- `src/vibemix/agent/dj_cohost.py` — FOUND (4 kwargs + post-stream gate + meta.json fields + linter= log token)

Commits:
- `9268664` test(20-01): RED — CitationLinter + StrippedRateTracker contract — FOUND
- `6d50efb` feat(20-01): GREEN — vibemix.coach package — FOUND
- `51f2819` test(20-01): RED — DJCoHostAgent linter wiring + Pitfall 2 — FOUND
- `1d24992` feat(20-01): GREEN — wire CitationLinter + ack-bank fallback into llm_node — FOUND

## TDD Gate Compliance

- RED commit (`test(20-01): ...`) for Task 1 ✅ (commit `9268664`)
- GREEN commit (`feat(20-01): ...`) for Task 1 ✅ (commit `6d50efb`)
- RED commit (`test(20-01): ...`) for Task 2 ✅ (commit `51f2819`)
- GREEN commit (`feat(20-01): ...`) for Task 2 ✅ (commit `1d24992`)
- No REFACTOR commit needed — implementation landed clean against the test contract.
