---
phase: 18-evidence-registry-citation-grammar-in-prompts-v10-prompt-only
plan: 02
subsystem: state
tags: [evidence, citations, threading, anti-hallucination, wiring, single-writer]
requires:
  - vibemix.state.EvidenceRegistry (Plan 18-01)
  - vibemix.state.refresh._tick_once (the SINGLE writer of MusicState)
  - vibemix.state.event_detector.EventDetector._fire
  - vibemix.state.coach.AICoach (read-only consumer)
provides:
  - state_refresh_loop / _tick_once with optional `evidence_registry` kwarg
  - EventDetector(audio_buf=, *, evidence_registry=) constructor surface
  - EventDetector._fire(ev_type, now, state, *, cooldown_key=) refactored signature
  - AICoach.evidence_line(state, *, registry_snapshot=) extension
  - AICoach.build_prompt(ev, *, registry_snapshot=) extension
affects:
  - Plan 18-03 (prompt grammar bake) — passes registry.snapshot() to build_prompt
  - Plan 18-04 (citation telemetry) — reads `ev`/`aud`/`mix` corpus shape
  - Phase 20 (linter + ack-bank) — consumes EvidenceRegistry.has() against the
    runtime corpus produced by this plan's wiring
tech_stack:
  added: []
  patterns:
    - "single-writer-per-source: state_refresh_loop owns aud+mix; EventDetector._fire owns ev"
    - "lock-nested-write: state._lock OUTER, EvidenceRegistry._lock INNER"
    - "best-effort registry write: try/except wraps every call, downstream
      registry failure cannot kill the tick or corrupt cooldown gates"
    - "change-only mix observations: phase + audible_deck change-detection
      gates avoid per-tick noise the way phase_history already debounces phase"
    - "audible-only aud observations: silent ticks NOT registered → closes
      'cite RMS at silent moment' hallucination class (cohost_v4 trust-the-audio rule)"
key_files:
  created: []
  modified:
    - src/vibemix/state/refresh.py
    - src/vibemix/state/event_detector.py
    - src/vibemix/state/coach.py
    - tests/state/test_refresh.py
    - tests/state/test_event_detector.py
    - tests/state/test_coach.py
decisions:
  - "ev observation key is the EVENT TYPE (KAAN_SPOKE / MANUAL / TRACK_CHANGE / PHASE / LAYER_ARRIVAL / MIX_MOVE / HEARTBEAT) — not the cooldown bucket. _fire signature gained explicit `state` arg + optional `cooldown_key` kwarg so KAAN_SPOKE preserves v4's MIC cooldown bucket while exposing the externally visible event name to the prompt grammar + Phase 20 linter."
  - "Per-tick aud writes happen INSIDE the same `with state._lock:` block as MusicState writes — Test J pins this via AST inspection. Lock ordering: state._lock OUTER, EvidenceRegistry._lock INNER, consistent across all writers."
  - "Mix writes are change-only (phase + audible_deck) — phase change branch already exists in v4-ported code, deck change required prev_deck capture before the assignment."
  - "AICoach byte-identical-to-v4 default path preserved: `registry_snapshot=None` produces the SAME string as v4. Only when snapshot is non-empty AND has at least one observation does the `evidence_corpus[ev=N,aud=M,mix=K]` footer appear."
  - "Three sources only in v1.0 (ev / aud / mix) — midi / track / screen / tend deferred per CONTEXT.md (their producers live outside the state package; will land in their respective phases)."
  - "All registry writes are best-effort (try/except: pass). Cooldown bookkeeping in `_fire` runs FIRST — a registry failure cannot corrupt cooldown gates (T-18-02-04 mitigation, Test D pin)."
metrics:
  duration: ~25 min
  completed: 2026-05-14
---

# Phase 18 Plan 02: EvidenceRegistry wired into refresh + EventDetector — Summary

**One-liner:** Wired the Plan 18-01 `EvidenceRegistry` into the two source-of-truth writers (`state_refresh_loop._tick_once` for `aud`/`mix`, `EventDetector._fire` for `ev`) as SIBLING write-targets to MusicState — single synchronous writer per source, no async queues — closing Pitfall P12 (registry race) at the runtime boundary and producing the citable evidence corpus that Plan 18-03 will bake into Gemini's system prompt.

## What Shipped

### EventDetector (`src/vibemix/state/event_detector.py`)

**New constructor signature:**
```python
EventDetector(
    audio_buf: AudioBuffer | None = None,
    *,
    evidence_registry: EvidenceRegistry | None = None,
) -> None
```

**Refactored `_fire` signature** (private — no external callers):
```python
def _fire(
    self,
    ev_type: str,
    now: float,
    state: MusicState,
    *,
    cooldown_key: str | None = None,
) -> None
```

- `ev_type` = externally visible event name (the `Event.type` returned to the caller).
- `cooldown_key` defaults to `ev_type`. The ONLY override is the KAAN_SPOKE → "MIC" mapping that preserves v4's MIC cooldown bucket while exposing the event-type name (`KAAN_SPOKE`) to the registry / prompt grammar.
- All 7 `_fire` call sites updated: KAAN_SPOKE (cooldown_key="MIC"), MANUAL, TRACK_CHANGE, PHASE, LAYER_ARRIVAL, MIX_MOVE, HEARTBEAT.

**Anti-race contract:**
1. `last_event_at = now` and `last_per_type_at[bucket] = now` happen FIRST (cooldown bookkeeping is authoritative).
2. Registry write follows in `try/except: pass` — a registry failure CANNOT corrupt cooldown gates or kill event firing (Test D, T-18-02-04 mitigation).
3. `t_session = max(0.0, now - state.set_start_at)` — sub-second resolution preserved (no rounding at write time; rounding is the Phase 20 linter's concern per GROUND-07). The `max(0.0, ...)` floor handles the edge case where `set_start_at` is unset (== 0.0).

### state_refresh_loop (`src/vibemix/state/refresh.py`)

**Both functions extended with kwarg:**
```python
def _tick_once(..., evidence_registry: EvidenceRegistry | None = None) -> tuple[float, ...]
async def state_refresh_loop(..., *, evidence_registry: EvidenceRegistry | None = None) -> None
```

**The async wrapper passes the kwarg through to `_tick_once` on every tick.**

**Per-tick `aud` writes (audible-only):** Inside the existing `with state._lock:` block, AFTER all MusicState writes, when `state.audible` is True (post-debouncing), 7 keys are written together with the same `t_session`:
- `rms`, `bpm`, `onset_density`, `sub_share`, `low_share`, `mid_share`, `high_share`

The audible-only gate kills the silent-tick hallucination class (Test F): silent ticks do NOT register `aud` observations, so Gemini cannot cite `aud:rms@45.2` at a moment when the master output was actually silent. This is the cohost_v4 "trust the audio" rule encoded as a runtime invariant.

**Change-only `mix` writes:**
- `phase=<name>` written INSIDE the existing `if new_phase != state.phase:` branch (Test G).
- `audible_deck=<name>` written when `prev_deck != aud_deck` — required capturing `prev_deck = state.audible_deck` BEFORE the unconditional `state.audible_deck = aud_deck` assignment (Test H).

Per-tick noise is filtered: phase already debounces via `state.phase_history`; deck-change detection avoids spamming the registry when the controller snapshot doesn't change.

**Atomic-snapshot consistency contract (Test J — AST-checked):** Every `evidence_registry.write(...)` call lexically appears INSIDE the `with state._lock:` block in `_tick_once`. Lock ordering is documented in the docstring: `state._lock` OUTER, `EvidenceRegistry._lock` INNER, consistent across all writers (T-18-02-02 mitigation — no deadlock).

### AICoach (`src/vibemix/state/coach.py`)

**Both methods extended with kwarg:**
```python
@staticmethod
def evidence_line(
    state: MusicState,
    *,
    registry_snapshot: dict[str, dict[str, tuple[float, ...]]] | None = None,
) -> str

@staticmethod
def build_prompt(
    ev: Event,
    *,
    registry_snapshot: dict[str, dict[str, tuple[float, ...]]] | None = None,
) -> str
```

When `registry_snapshot` is non-None AND has at least one observation, the evidence_line gets a single appended footer:

```
evidence_corpus[ev=N,aud=M,mix=K]
```

where N/M/K are integer counts of observations per source. Empty / all-zero snapshots → footer omitted (no zero-only lines). Missing source keys treated as 0 (no KeyError).

**Phase 4 byte-identical-to-v4 invariant preserved:** `registry_snapshot=None` (default) produces the SAME string as v4. Confirmed by Test L (no-kwarg path = None-kwarg path = pinned silent-state baseline) AND by all 30 pre-existing test_coach.py tests staying GREEN unchanged.

## Source / Key Vocabulary Actually Written

| Source | Writer | When | Key shape | Example |
|--------|--------|------|-----------|---------|
| `ev`   | `EventDetector._fire` | Per event fire | Event-type string | `[ev:KAAN_SPOKE@45.2]`, `[ev:HEARTBEAT@130.5]` |
| `aud`  | `state_refresh_loop._tick_once` | Per tick, audible-only | Feature name | `[aud:rms@45.2]`, `[aud:bpm@45.2]`, `[aud:sub_share@45.2]` |
| `mix`  | `state_refresh_loop._tick_once` | On phase or deck change | `phase=<name>` or `audible_deck=<name>` | `[mix:phase=drop@45.2]`, `[mix:audible_deck=A@12.7]` |

**Deferred sources** (v1.0 explicitly excludes — producers live outside state package):
- `midi` — controller events live in MIDI thread, not state-refresh. Will land when controller producer is touched.
- `track` — the title-resolution path in `track_resolver` already lives outside state-refresh. Plan 18-03 may inject `[track:<title>]` into the prompt without registry write.
- `screen` — no screen-capture pipeline in current sidecar.
- `tend` — Phase 26 hook per CONTEXT.md.

This 3-source v1.0 scope is the minimum corpus needed to seed Gemini's prompt so it learns the citation grammar; Plan 18-04 telemetry will reveal whether to expand registry coverage in v2.1.

## Anti-Race Contract (Pitfall P12)

The Phase 18 design is **single synchronous writer per source**:

- `aud` + `mix` → `state_refresh_loop._tick_once` (single 10Hz writer thread / asyncio task; lock-protected against parallel readers).
- `ev` → `EventDetector._fire` (called from `coach_loop` coroutine — single-threaded asyncio).

There is NO async queue, NO separate writer coroutine. The `EvidenceRegistry`'s own `threading.Lock` (separate from `state._lock`) gates the actual write. Lock ordering: `state._lock` OUTER, `registry._lock` INNER — consistent across all writers, eliminating deadlock risk (T-18-02-02). The Plan 18-01 8-thread torn-write test (`test_evidence_03_concurrent_writes_no_torn`) is the gate proving the lock works under contention.

## Hand-off Note for Plan 18-03

Plan 18-03 will bake the citation grammar into the system prompt. The wiring it needs from this plan:

1. **Construct the registry once at session start** (in `__main__.py` — Plan 18-03 will own this wiring):
   ```python
   from vibemix.state import EvidenceRegistry
   evidence_registry = EvidenceRegistry()
   ```

2. **Pass it to both writers:**
   ```python
   event_detector = EventDetector(audio_buf=audio_buf, evidence_registry=evidence_registry)
   asyncio.create_task(state_refresh_loop(state, audio_buf, ctrl, track, stop, evidence_registry=evidence_registry))
   ```

3. **Snapshot once per `llm_node` invocation, pass into `build_prompt`:**
   ```python
   snapshot = evidence_registry.snapshot()  # cheap (~1ms for typical corpus)
   prompt = AICoach.build_prompt(ev, registry_snapshot=snapshot)
   ```

The registry's `snapshot()` returns a deep copy with tuple-frozen inner lists, so `build_prompt` (or the Plan 18-03 grammar-baking helper) can iterate lock-free.

## Test Count Delta

| Scope            | Before | After | Δ   |
| ---------------- | ------ | ----- | --- |
| `tests/state/test_event_detector.py` | 41 | 45 | +4 (Tests A-D) |
| `tests/state/test_refresh.py`        | 32 | 40 | +8 (Tests E-L; planned 7 + 1 bonus signature test) |
| `tests/state/test_coach.py`          | 30 | 35 | +5 (Tests L-N + 2 bonus snapshot edge cases) |
| `tests/state/` (full)                | 394 | 411 | **+17** |
| Full repo                            | 1568 | 1585 | **+17** |
| Pre-existing failures                | 9 | 9 | 0 (unchanged, all out of scope) |

Plan body specified "14 new green tests" — actual delta is +17 because three behavior items got bonus edge-case tests (state_refresh_loop signature thread-through pin, evidence_corpus footer empty-snapshot suppression, missing-source-keys handling).

## Threat Register Status

| Threat ID | Disposition | Status |
| --------- | ----------- | ------ |
| T-18-02-01 (concurrent-write tampering) | mitigate | **Closed** — EvidenceRegistry's threading.Lock from Plan 18-01 handles this; Plan 18-01 Test 3 is the gate. |
| T-18-02-02 (registry write inside state._lock could deadlock) | mitigate | **Closed** — lock ordering documented (`state._lock` OUTER, `registry._lock` INNER, consistent across all writers); registry has its own lock. |
| T-18-02-03 (per-tick writes amplifying disk + memory) | accept | Per-tick aud writes ≈ 7 floats × 10Hz × 1h ≈ 252k floats ≈ 2MB peak. Per CONTEXT.md acceptable for v1.0. `clear()` is exposed for the eventual `__main__.py` per-session wiring (deferred to that plan). |
| T-18-02-04 (registry exception killing the tick) | mitigate | **Closed** — every registry write wrapped in `try/except: pass`. The outer `_tick_once` already had top-level try/except in `state_refresh_loop`. Test D pins the cooldown-not-corrupted contract for `_fire`. |
| T-18-02-05 (phase change observation written without provenance) | accept | t_session is unrounded float, matches existing `events.jsonl` convention. P20 linter will own provenance verification per GROUND-07. |

## POC Files Untouched

`git status --short cohost.py cohost_v2.py cohost_lk.py cohost_v4.py cohost_v3.py cohost_v4_tr.py` shows only the pre-existing untracked POC files (`cohost_v3.py`, `cohost_v4.py`, `cohost_v4_tr.py`) — no edits, no staged changes. The pre-existing `tests/test_phase05_verification.py::test_g5_poc_files_untouched` failure is from session-pre-existing untracked POC reference files (not introduced by this plan).

## Deviations from Plan

**Rule 2 (auto-add critical functionality) — none applied.** The plan's `<action>` blocks were precise enough that the wiring went in as specified. Two minor additions to flesh out the test coverage (Test L state_refresh_loop signature pin, two snapshot edge-case tests in test_coach.py) — not deviations from the plan's intent, just bonus pins for the same behavior surface.

The plan's pre-flight note about waiting for P17-01 to ship was satisfied: the pre-existing `feat(17-01): populate Phase 17 fields in state_refresh_loop single-writer` commit `2ebc6b4` was already in `HEAD` at execute time. No merge-conflict surface emerged — this plan's `_tick_once` additions are all confined to (a) the registry-write block AT THE END of the lock body (after all MusicState writes Phase 17 added) and (b) the existing phase-change branch + the deck-assignment site (where the wraparound is purely additive — `prev_deck` capture before, write after, no change to MusicState write order).

## Commits

| Task | SHA       | Message                                                              |
| ---- | --------- | -------------------------------------------------------------------- |
| 1 RED   | `88e2fc4` | `test(18-02): add failing tests for EventDetector evidence_registry wiring` |
| 1 GREEN | `e77d2f3` | `feat(18-02): wire EvidenceRegistry into EventDetector._fire`        |
| 2 RED   | `7ef609e` | `test(18-02): add failing tests for state_refresh_loop registry wiring` |
| 2 GREEN | `3f2d055` | `feat(18-02): wire EvidenceRegistry into state_refresh_loop._tick_once` |
| 3 RED   | `5dc8a42` | `test(18-02): add failing tests for AICoach registry_snapshot kwarg` |
| 3 GREEN | `b082f57` | `feat(18-02): thread registry_snapshot kwarg through AICoach`        |

## Self-Check: PASSED

- `src/vibemix/state/event_detector.py` — modified, evidence_registry kwarg + refactored `_fire` shipped.
- `src/vibemix/state/refresh.py` — modified, evidence_registry kwarg threaded through `_tick_once` and `state_refresh_loop`; aud + mix writes inside `with state._lock:` block (AST-verified by Test J).
- `src/vibemix/state/coach.py` — modified, registry_snapshot kwarg added to `evidence_line` and `build_prompt`.
- `tests/state/test_event_detector.py` — 4 new tests (A-D) green.
- `tests/state/test_refresh.py` — 8 new tests (E-L) green.
- `tests/state/test_coach.py` — 5 new tests green (3 planned + 2 bonus).
- Commit `88e2fc4` — FOUND.
- Commit `e77d2f3` — FOUND.
- Commit `7ef609e` — FOUND.
- Commit `3f2d055` — FOUND.
- Commit `5dc8a42` — FOUND.
- Commit `b082f57` — FOUND.
- POC files: untracked status unchanged from session start — no edits introduced by this plan.
- `tests/state/` regression: 394 → 411 (+17, no losses).
- Full repo: 1568 → 1585 passed (+17), 9 failed unchanged (all pre-existing, all outside `tests/state/`).
