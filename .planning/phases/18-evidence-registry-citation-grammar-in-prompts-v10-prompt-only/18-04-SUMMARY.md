---
phase: 18-evidence-registry-citation-grammar-in-prompts-v10-prompt-only
plan: 04
subsystem: agent + state (telemetry)
tags: [GROUND-02, citation-telemetry, observability, phase-16-readiness, phase-20-prewire, evidence-registry]
requires:
  - "18-01: EvidenceRegistry + parse_citations + EVIDENCE_CITATION_RE"
  - "18-02: registry wired into refresh + EventDetector + AICoach"
  - "18-03: CITATION_GRAMMAR_BLOCK baked into Gemini system instruction; per-turn snapshot threading in llm_node"
provides:
  - "src/vibemix/state/evidence_registry.py: EvidenceRegistry.record_citation_count(n) + EvidenceRegistry.citation_telemetry()"
  - "src/vibemix/state/evidence_registry.py: deque(maxlen=50) rolling buffer + unbounded _total_turns counter"
  - "src/vibemix/agent/dj_cohost.py: post-stream citation_count telemetry block (events.jsonl line + registry buffer update)"
affects:
  - "events.jsonl gains one citation_count line per Gemini turn (including silence/slop suppressed turns)"
  - "EvidenceRegistry.clear() now also resets _citation_buffer + _total_turns (per-session reset semantic preserved)"
  - "Phase 16 ear-test gains a programmatic readiness signal: registry.citation_telemetry()['mean']"
  - "Phase 20 stripped_rate guard pre-wires off the same buffer (single state object, single lock, single import path)"
tech-stack:
  added: []
  patterns:
    - "Best-effort try/except: pass around every telemetry call — telemetry exceptions never escape into LLM response path (T-18-04-03 mitigation)"
    - "Telemetry fires BEFORE the silence/slop suppression gate so corpus signal reflects Gemini's TRUE emission rate, not the post-suppression rate"
    - "response_id = f'{invoke_n:04d}_{invoke_ts}' format matches per-invocation dump folder name → events.jsonl ↔ dump folder cross-reference is trivial"
key-files:
  created: []
  modified:
    - "src/vibemix/state/evidence_registry.py — record_citation_count + citation_telemetry + extended clear()"
    - "src/vibemix/agent/dj_cohost.py — parse_citations import + post-stream telemetry block in llm_node"
    - "tests/state/test_evidence_registry.py — Tests Z–AD (5 new test cases)"
    - "tests/agent/test_dj_cohost.py — Tests AE–AK (7 new test cases: 6 unit + 1 integration smoke)"
decisions:
  - "Rolling buffer lives on EvidenceRegistry (not AICoach) because AICoach is a static-method namespace with no instance state — keeps state centralized and lets Phase 20's linter read the SAME buffer for the stripped_rate guard pre-wire."
  - "Telemetry fires BEFORE the suppression gate (not inside the clean-turn branch) — corpus signal integrity for Phase 16 readiness threshold tuning. Test AF locks this contract."
  - "Best-effort guarantee: parse_citations failure → count=0 fallback; recorder write failure → silently swallowed; registry write failure → silently swallowed. Test AI is the gate — telemetry exceptions MUST NOT break the LLM response stream."
  - "response_id field is the synthetic NNNN_TS pattern (not a UUID, not the LiveKit message id) so it cross-references the per-invocation dump folder name 1:1."
  - "Mean is a Python float with NO rounding at the registry layer — Phase 16 ear-test and Phase 20 stripped_rate guard own display rounding; locking precision now would force a v2 API change later."
  - "Empty-buffer mean returns 0.0 (not NaN, not None) — Test AB locks the no-NaN contract so callers don't have to special-case the cold-start state."
metrics:
  duration_minutes: ~12
  completed: 2026-05-14
  tests_added: 12  # 5 EvidenceRegistry + 6 dj_cohost unit + 1 dj_cohost integration
  tests_repo_total: "1619 passing (was 1607 pre-Plan-18-04; +12 net, exact match)"
  tests_repo_failing: "9 pre-existing failures unchanged"
---

# Phase 18 Plan 04: citation_count telemetry shipped — Summary

ROADMAP success criterion #4 closed: every Gemini turn writes a `citation_count` line to `events.jsonl` with the integer count of citations parsed from the full response text. The same count flows into a `deque(maxlen=50)` rolling buffer on `EvidenceRegistry`, exposed as `citation_telemetry()` for Phase 16 ear-test consumption and Phase 20 stripped_rate guard pre-wire.

v1.0 is **pure observability** — zero behavior change to the LLM response path. Suppression gates, prompt construction, persona rendering, and TTS streaming are byte-identical to Plan 18-03. Telemetry is bolted on AFTER `full_text.strip()` and BEFORE the silence/slop gate so suppressed turns are also counted.

## events.jsonl line shape (real sample)

```jsonl
{"t": 12.456, "kind": "citation_count", "count": 2, "response_id": "0001_153012"}
{"t": 18.221, "kind": "citation_count", "count": 0, "response_id": "0002_153018"}
```

- `kind`: literal `"citation_count"`
- `count`: integer ≥ 0; result of `len(parse_citations(full_text))` over the full Gemini response
- `response_id`: `f"{invoke_n:04d}_{invoke_ts}"` — matches the per-invocation dump folder name (`<session_dir>/invocations/0001_153012_HEARTBEAT/`) so a `jq` over `events.jsonl` can join 1:1 with `prompt.txt` / `response.txt` / `meta.json` in the dump folder
- `t`: seconds-since-session-start, auto-injected by `VoiceRecorder.log_event` (recorder.py:303) — matches CONTEXT.md §Telemetry convention

## EvidenceRegistry.citation_telemetry() return shape

```python
>>> from vibemix.state import EvidenceRegistry
>>> r = EvidenceRegistry()
>>> r.record_citation_count(3)
>>> r.record_citation_count(5)
>>> r.citation_telemetry()
{'window_size': 2, 'mean': 4.0, 'total_turns_observed': 2}
```

- `window_size`: `len(deque)` — bounded at 50; cold-start = 0
- `mean`: average of the **last 50** counts (or all counts if fewer than 50); empty-buffer = `0.0` (not NaN, not None — Test AB locks this)
- `total_turns_observed`: unbounded counter — Phase 16 reads as the "turns observed" denominator

## Where the telemetry is emitted

`src/vibemix/agent/dj_cohost.py::DJCoHostAgent.llm_node`, post-stream:

1. Stream completes → `full_text` accumulated, `stripped = full_text.strip()` runs
2. **Plan 18-04 telemetry block** (~lines 287–321):
   - `parse_citations(full_text)` → `citation_count = len(...)` (try/except → 0 on failure)
   - `recorder.log_event("citation_count", count=..., response_id=...)` (try/except → silently swallowed)
   - `registry.record_citation_count(count)` IFF registry wired (try/except → silently swallowed)
3. Silence/slop suppression gate runs unchanged

The block is positioned BEFORE the suppression branches so silence/slop turns ALSO emit telemetry — Phase 16 needs Gemini's TRUE emission rate, not the post-suppression rate, to gate Phase 20 enforcement readiness.

## Phase 16 ear-test consumption pattern

**Live-session jq one-liner** to compute mean from a session's `events.jsonl`:

```bash
jq -s '[.[] | select(.kind=="citation_count") | .count] | (add / length)' \
    recordings/<session_dir>/events.jsonl
```

**In-process polling** (Phase 16 dashboard / readiness check):

```python
from vibemix.state import EvidenceRegistry

# Same registry instance the DJCoHostAgent + EventDetector share.
tel = registry.citation_telemetry()
print(f"Citations: mean={tel['mean']:.2f} over last {tel['window_size']} turns "
      f"({tel['total_turns_observed']} total)")
```

**Phase 20 readiness signal** — the rolling-50-turn `mean` is the gate. Threshold tuning happens in Phase 16 against real DJ-set data; current rough target is `mean ≥ 1.5` over 50 turns sustained across 5+ sessions before flipping Phase 20's stripped_rate enforcement on.

## Phase 20 hand-off

The SAME `EvidenceRegistry` instance now holds:

- (a) **source-dict** for `has(source, key, t_target, tol)` lookups — Plan 18-01's evidence-grounding lookup the Phase 20 linter calls per parsed citation
- (b) **rolling buffer** for stripped_rate guard pre-wire — Plan 18-04's `citation_telemetry()` the Phase 20 enforcement layer reads to decide whether enforcement is "ready" (rolling mean above threshold for sustained N turns)

Single state object → single lock → single import path. Phase 20's linter constructor takes a single `EvidenceRegistry` arg and reads both surfaces; no cross-module state coupling.

## Test plan delta

- **EvidenceRegistry** (5 new tests Z–AD):
  - Z: basic record + telemetry round-trip
  - AA: `deque(maxlen=50)` auto-evicts oldest beyond 50 records
  - AB: empty-buffer + zero-count both return `mean=0.0` (no NaN)
  - AC: 8-thread × 100-record concurrency under same single-Lock contract (closes P12 for the new buffer too)
  - AD: `clear()` resets buffer + `_total_turns` counter
- **dj_cohost** (6 new unit tests AE–AJ):
  - AE: `citation_count` events.jsonl line written per turn with `response_id` `NNNN_TS` pattern
  - AF: silence-suppressed turn STILL emits `citation_count` (corpus signal integrity)
  - AG: zero-citation response → `count=0`
  - AH: `registry.record_citation_count` called per turn → `total_turns_observed` advances by 1
  - AI: `parse_citations` raising MUST NOT break LLM response path — chunks still yielded, `ai_text` event still written (T-18-04-03 gate)
  - AJ: `evidence_registry=None` (default) path still writes recorder-side `events.jsonl` event
- **dj_cohost integration** (1 new smoke AK):
  - AK: 10 mock LLM turns with counts `[3,0,2,1,4,0,2,5,1,3]` → `registry.citation_telemetry()` returns `mean=2.1`. End-to-end Phase 16 readiness signal contract locked.

## Threat register status (post-Plan)

| Threat ID | Status | Notes |
|---|---|---|
| T-18-04-01 (DoS via adversarial Gemini output) | **mitigated** | Plan 18-01 regex bounded by `[^\s\]]+`; Gemini `max_output_tokens=220` caps input size at the source. |
| T-18-04-02 (rolling-buffer growth) | **mitigated** | `deque(maxlen=50)` — bounded memory by construction. |
| T-18-04-03 (telemetry breaking LLM stream) | **mitigated** | All three telemetry calls wrapped in `try/except: pass`. Test AI is the gate. |
| T-18-04-04 (citation_count line missing on recorder failure) | **accepted** | Best-effort matches v4 recorder pattern; `<dump>/response.txt` retains the raw response so Phase 16 can recompute counts offline. |
| T-18-04-05 (response_id leaks invoke counter) | **accepted** | response_id is local to events.jsonl + dump folder; both are session-private (recorder dirs are `0o700`). |

## Post-Plan repo state

- **Plan 18 complete.** Phase 18's full prompt-only seeding loop (registry → corpus footer → grammar block in system instruction → telemetry) is shipped end-to-end.
- **Tests:** 1619 passing (was 1607), 9 pre-existing failures unchanged. POC files (`cohost.py`, `cohost_v2.py`, `cohost_lk.py`, `cohost.streaming.py.bak`) untouched per CLAUDE.md.
- **Hand-off to Phase 20:** the registry's twin-surface design (source-dict + rolling buffer behind a single lock) means Phase 20 can land its linter + stripped_rate guard without cross-module rewiring.
- **Hand-off to Phase 16:** the readiness signal is a single `registry.citation_telemetry()["mean"]` call; ear-test can poll it during a live DJ set or post-hoc via the documented `jq` one-liner.

## Self-Check: PASSED

- `src/vibemix/state/evidence_registry.py` — verified modified (record_citation_count + citation_telemetry + clear() extension present)
- `src/vibemix/agent/dj_cohost.py` — verified modified (parse_citations import + telemetry block present at expected position)
- `tests/state/test_evidence_registry.py` — 5 new tests (Z, AA, AB, AC, AD) verified added + green
- `tests/agent/test_dj_cohost.py` — 7 new tests (AE, AF, AG, AH, AI, AJ, AK) verified added + green
- Plan-level pytest: `tests/state/test_evidence_registry.py tests/agent/test_dj_cohost.py` → 52 passing
- Full-suite pytest: 1619 passing (1607 → 1619, +12 exact match), 9 pre-existing failures unchanged
- POC files untouched: `git status --short cohost.py cohost_v2.py cohost_lk.py cohost.streaming.py.bak` empty
- Contract sanity: `python -c "from vibemix.state import EvidenceRegistry; r = EvidenceRegistry(); r.record_citation_count(3); r.record_citation_count(5); print(r.citation_telemetry())"` → `{'window_size': 2, 'mean': 4.0, 'total_turns_observed': 2}` (matches plan verification block exactly)
- Commits exist: `dd19635` (test Z-AD RED), `b0e7941` (registry GREEN), `3ff27c0` (test AE-AK RED), `6474344` (dj_cohost GREEN)
