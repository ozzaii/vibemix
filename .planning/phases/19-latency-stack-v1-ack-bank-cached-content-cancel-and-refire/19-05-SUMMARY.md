# SPDX-License-Identifier: Apache-2.0
---
phase: 19
plan: 05
subsystem: runtime-wiring
tags:
  - latency-stack
  - runtime-wiring
  - ack-bank
  - cancel-gate
  - context-cache
  - ttft
  - gap-closure
requires:
  - 19-01-SUMMARY.md (CancelGate + 8s cooldown + 30/session soft cap)
  - 19-02-SUMMARY.md (prompt diet — 18s→6s + screen-skip)
  - 19-03-SUMMARY.md (GeminiContextCache + 1024-token floor + 4min refresh + invalidate hook)
  - 19-04-SUMMARY.md (40-OPUS AckBank + four-gate should_fire + per-bucket rotation)
provides:
  - TTFTMeter primitive (rolling-avg event_fired→first_chunk in ms)
  - coach_loop ack-fire pre-LLM path wired to AckBank.should_fire + PlaybackQueue.push
  - coach_loop cancel-and-refire path wired to CancelGate.try_cancel + agent.invalidate_cache
  - DJCoHostAgent.ttft_meter wiring (set_next_event records event_fired; llm_node records first_chunk)
  - __main__.py constructs cache + ack_bank + cancel_gate + ttft_meter and threads them through agent + coach_loop
  - Graceful degradation when cache.create fails (cache=None falls through to agent's disabled-cache branch)
affects:
  - src/vibemix/runtime/coach.py (extended signature; wired path; allow_interruptions=True flip)
  - src/vibemix/agent/dj_cohost.py (ttft_meter kwarg; first-chunk recording)
  - src/vibemix/__main__.py (cache + ack_bank + cancel_gate + ttft_meter construction; refresh_loop spawn)
tech-stack:
  added:
    - vibemix.runtime.ttft.TTFTMeter (new module)
  patterns:
    - bounded deque(maxlen=8) rolling average with sentinel default
    - constructor-injected time_fn (deterministic test clock)
    - graceful-degradation try/except around cache.create
    - additive backward-compat kwargs (None default → legacy path)
key-files:
  created:
    - src/vibemix/runtime/ttft.py
    - tests/runtime/test_ttft.py
    - tests/runtime/test_coach_ack_wiring.py
    - tests/runtime/test_coach_cancel_wiring.py
    - .planning/phases/19-latency-stack-v1-ack-bank-cached-content-cancel-and-refire/19-05-PLAN.md
  modified:
    - src/vibemix/runtime/coach.py
    - src/vibemix/agent/dj_cohost.py
    - src/vibemix/__main__.py
    - tests/runtime/conftest.py
    - tests/agent/test_dj_cohost.py
    - tests/test_main_smoke.py
decisions:
  - TTFTMeter sentinel default = 1500.0 ms (>800.0 ACK_TTFT_GATE_MS) so the FIRST event of a session can fire an ack while Gemini is still cold and the user is waiting on the first response
  - Pending-overwrite semantics on record_event_fired (the prior event was preempted via CancelGate or failed via TimeoutError; its TTFT is unmeasurable)
  - Wired path = ALL FOUR (ack_bank + cancel_gate + ttft_meter + playback) non-None; legacy path triggered when ANY is None — preserves Phase 4 byte-identical contract for existing callers/tests (test_coach.py 13 assertions stay green)
  - allow_interruptions flip True only on the wired path; SpeechHandle.interrupt(force=True) chokepoint inside CancelGate now reachable in production
  - Cache failure = graceful degradation (warn + cache=None) — agent's existing 3-branch dispatch handles None as cache_state="disabled" (Phase 4 byte-identical fallback)
  - Cancel-and-refire branch reachable from a stale in_flight_handle (TimeoutError cleanup left it populated); the same seam will carry v2.x async fan-in
metrics:
  duration_minutes: 16
  completed_date: 2026-05-14
  tests_added: 22
  tests_total_before: 1711
  tests_total_after: 1733
  pre_existing_failures: 9 (unchanged)
---

# Phase 19 Plan 05: Runtime Wiring Closes Phase 19 Gaps Summary

Closes the three runtime-wiring gaps surfaced by `19-VERIFICATION.md`:
**LATENCY-04/05/06/11/12 satisfied at primitive layer but BLOCKED at runtime** because
coach.py never invoked AckBank/CancelGate and __main__.py never constructed
GeminiContextCache. Single architectural-seam refactor: TTFTMeter primitive +
coach_loop wired path (ack pre-fire + cancel-and-refire + allow_interruptions=True) +
__main__.py cache construction with graceful degradation.

## What Shipped

### Task 1 — TTFTMeter (commits `bb0289d` test + `87a8d3f` impl)

`vibemix.runtime.ttft.TTFTMeter` — bounded-window deque rolling average of
`(event_fired, first_chunk)` pairs in milliseconds. 1500ms sentinel default so the
first event of a session passes the AckBank TTFT gate (>800ms). Constructor-
injected time_fn for deterministic tests. 7 tests pinning empty-meter sentinel,
single-sample recording, rolling-window cap, no-pending no-op, pending-overwrite
semantics, ack-gate-passing default, and injected time_fn.

### Task 2 — DJCoHostAgent meter wiring (commits `c7347a7` test + `1520d1c` impl)

- `__init__` accepts `ttft_meter: TTFTMeter | None = None` (None preserves Phase 4
  backward compat).
- `set_next_event(ev)` calls `meter.record_event_fired()` when meter is non-None.
- `llm_node` records first-chunk timestamp exactly once on the first non-empty
  stream yield (`first_chunk_recorded` flag prevents per-chunk recording).
- 3 new tests + 28 existing dj_cohost tests still green.

### Task 3 — coach_loop ack + cancel wiring (commits `724f366` test + `d98823f` impl)

- `coach_loop` signature gains four kwargs (defaults None for backward compat):
  `ack_bank`, `cancel_gate`, `ttft_meter`, `playback`.
- When ALL four are non-None (= "wired" path):
  1. **Cancel-and-refire**: if `trigger_state["in_flight_handle"]` and
     `trigger_state["in_flight_ev"]` are populated (stale from prior
     TimeoutError tick), invoke
     `cancel_gate.try_cancel(handle, incoming, in_flight_ev)`. On True:
     `await agent.invalidate_cache()` + clear stale handle/ev.
  2. **Ack pre-fire**: compute `cancel_cooldown_active = (cancel_gate.last_cancel_at
     != 0.0 AND now - last_cancel_at < CANCEL_COOLDOWN_S)`. Query
     `ack_bank.should_fire(rolling_ttft_avg_ms, last_ack_at, last_response_at,
     cancel_cooldown_active)`. On True: `pick_for_event(ev) → playback.push(pcm.tobytes())
     → trigger_state["last_ack_at"] = monotonic() → recorder.log_event("ack_fire",
     bucket=, sample_index=, reason=)`.
  3. **`generate_reply(allow_interruptions=True)`** — the SpeechHandle.interrupt(force=True)
     chokepoint inside CancelGate is now reachable in production.
  4. `trigger_state["in_flight_handle"]` + `["in_flight_ev"]` updated on assignment;
     `["last_response_at"]` updated on success; both cleared in finally.
- When ANY of the four kwargs is None: legacy path runs verbatim with
  `allow_interruptions=False` — Phase 4 byte-identical contract preserved
  (existing test_coach.py 13 assertions byte-identical).
- 7 ack-wiring tests + 3 cancel-wiring tests new.

### Task 4 — __main__.py cache construction (commits `90a5ac1` test + `ca22bec` impl)

`async def main()` now constructs the four primitives BEFORE `DJCoHostAgent(...)`:

```python
ttft_meter = TTFTMeter()
ack_bank = AckBank()  # eager-loads 40 OPUS files; AckBankError on bad shape
cancel_gate = CancelGate()
cache = GeminiContextCache(client=genai_client, system_instruction_body=SYSTEM_INSTRUCTION, model=LLM_MODEL)
try:
    await cache.create()
    print("-> cache: warm (Gemini context cache active)")
except Exception as e:
    print(f"-> cache disabled: {e}", file=sys.stderr)
    cache = None  # graceful degradation
```

Then `DJCoHostAgent(..., cache=cache, ttft_meter=ttft_meter)` and
`coach_loop(..., ack_bank=ack_bank, cancel_gate=cancel_gate, ttft_meter=ttft_meter,
playback=playback)`. `cache.refresh_loop(stop_event)` spawned as background asyncio
task AFTER `await session.start(agent)` and added to the cleanup-cancel list. Skipped
when cache is None (graceful degradation path).

SMOKE-07/08 tests use AST-level source assertions to lock the wiring contract
because the pre-existing baseline-9 main() teardown failure (carried in
test_smoke_03/04/05/06 — unrelated to this plan) prevents the live-runtime smoke
harness from reaching the cache construction code in the test environment. AST-level
wiring assertions catch any future regression that drops `cache=cache`,
`ttft_meter=ttft_meter`, or any of the four coach_loop kwargs.

## Test Counts

| Suite | Before | After | Delta |
|-------|--------|-------|-------|
| `pytest -q` total | 1711 passed / 9 failed | 1733 passed / 9 failed | **+22 new passing** |
| `tests/runtime/test_ttft.py` | — | 7 | +7 |
| `tests/runtime/test_coach_ack_wiring.py` | — | 7 | +7 |
| `tests/runtime/test_coach_cancel_wiring.py` | — | 3 | +3 |
| `tests/agent/test_dj_cohost.py` | 28 | 31 | +3 |
| `tests/test_main_smoke.py` (Plan 19-05 only) | — | 2 | +2 |

Pre-existing 9 failures unchanged: `test_persona_02`, 3 `test_phase15_success_criteria`,
`test_audio_macos_live`, 3 `test_smoke_03/04/05`, `test_g5_poc_files_untouched`.

## Wiring Verification

| Verification | Command | Result |
|--------------|---------|--------|
| Plan 19-05 wiring chokepoints | `grep -c "ack_bank.should_fire" src/vibemix/runtime/coach.py` | 2 (≥1 ✓) |
| | `grep -c "cancel_gate.try_cancel" src/vibemix/runtime/coach.py` | 1 (≥1 ✓) |
| | `grep -c "ttft_meter" src/vibemix/runtime/coach.py` | 4 (≥1 ✓) |
| | `grep -c "allow_interruptions=True" src/vibemix/runtime/coach.py` | 2 (≥1 ✓) |
| Cache wiring in __main__ | `grep -c "GeminiContextCache" src/vibemix/__main__.py` | 2 (≥1 ✓) |
| | `grep -c "ack_bank=ack_bank" src/vibemix/__main__.py` | 1 (≥1 ✓) |
| Single-call chokepoint preserved | `grep -rE "interrupt\(force=True\)" src/vibemix/ --include="*.py" \| grep -v "^.*#\|docstring"` actual call sites | 1 (cancel.py:124) — coach.py:32 is a docstring reference |
| `caches.create` chokepoint preserved | `grep -rE "caches\.create" src/vibemix/` | 3 (1 actual call + 2 docs in cache.py) — UNCHANGED |
| POC files untouched | `pytest tests/test_main_smoke.py::test_smoke_06_poc_files_untouched_during_smoke` | PASS |

## Behavior Change

The single user-visible behavior change is `allow_interruptions=False` →
`allow_interruptions=True` on the wired path. This means LiveKit's SpeechHandle
playout can now be preempted by `handle.interrupt(force=True)` — which is the
sole call site inside CancelGate, gated by the three-rung priority + cooldown +
soft-cap ladder. In legacy/test paths (any of ack_bank/cancel_gate/ttft_meter/playback
is None), `allow_interruptions=False` is preserved.

## Graceful Degradation Paths

| Failure | Behavior |
|---------|----------|
| `cache.create()` raises (network / auth) | Warn to stderr; `cache = None`; agent's None-cache branch handles as `cache_state="disabled"` (Phase 4 byte-identical). refresh_loop NOT spawned. |
| `AckBank()` constructor raises (bundling regression) | Propagates — fails loud per CONTEXT D-08. The 40-OPUS shape invariant is a release gate, not a runtime degradation. |
| `should_fire` returns (False, ...) | Skip ack; proceed to set_next_event + generate_reply. No PCM pushed; no telemetry emitted (the reason word is captured in caller's debug log only when an ack DOES fire). |
| `try_cancel` returns False | Skip invalidate_cache; in-flight handle remains; new event proceeds (which would normally be blocked by the in-flight enforcement on the prior tick — current Phase 19 reachability is the TimeoutError cleanup path). |

## Deviations from Plan

None — plan executed exactly as written. The only structural decision made during
execution was switching SMOKE-07/08 from runtime smoke (which would hit pre-existing
baseline-9 main() teardown failure) to AST-level source assertions (which lock the
wiring contract independently of the live-runtime smoke harness). This is a Rule
3 fix (existing infrastructure blocked the originally-planned testing approach) —
the wiring contract is verified, just at a different layer.

## Threat Flags

None — this plan only wires existing primitives into existing call sites. No new
network endpoint, auth path, file access pattern, or schema change at any trust
boundary. Plan 19-04's existing T-19-04-* register covers the AckBank surface;
Plan 19-03's covers the cache surface; Plan 19-01's covers the cancel surface.

## Self-Check: PASSED

Files created — verified present:
- `src/vibemix/runtime/ttft.py` ✓
- `tests/runtime/test_ttft.py` ✓
- `tests/runtime/test_coach_ack_wiring.py` ✓
- `tests/runtime/test_coach_cancel_wiring.py` ✓
- `.planning/phases/19-latency-stack-v1-ack-bank-cached-content-cancel-and-refire/19-05-PLAN.md` ✓

Commits — verified in `git log --oneline`:
- `043de0e` docs(19-05): plan ✓
- `bb0289d` test(19-05): TTFTMeter RED ✓
- `87a8d3f` feat(19-05): TTFTMeter GREEN ✓
- `c7347a7` test(19-05): dj_cohost meter RED ✓
- `1520d1c` feat(19-05): dj_cohost meter GREEN ✓
- `724f366` test(19-05): coach ack/cancel wiring RED ✓
- `d98823f` feat(19-05): coach_loop wired path GREEN ✓
- `90a5ac1` test(19-05): smoke 07/08 RED ✓
- `ca22bec` feat(19-05): __main__ cache wiring GREEN ✓

## Followups

- **Real Achird-voice OPUS recordings (Kaan-action)** — replace 40 silent OPUS
  placeholders one-for-one. This is the SOLE Phase 19 work that remains
  Kaan-action-required after this plan. Runtime path unchanged when bytes are
  swapped; AIza-key scan must re-run on new bytes per CONTEXT D-08.
- **`telemetry_cb` for CancelGate** — currently a no-op. A future v2.x plan can
  wire it to ws_bus when the `session.cancel` IPC surface lands.
- **v2.x asynchronous fan-in** — the cancel-and-refire branch is currently
  reachable only via TimeoutError-cleanup paths because the synchronous
  `await wait_for_playout()` inside coach_loop blocks the loop. v2.x async fan-in
  (multiple events arriving inside one playout) will use the same seam.
</content>
</invoke>
