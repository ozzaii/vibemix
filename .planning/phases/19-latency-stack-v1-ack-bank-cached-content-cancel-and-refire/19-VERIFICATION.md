---
phase: 19-latency-stack-v1-ack-bank-cached-content-cancel-and-refire
verified: 2026-05-14T00:00:00Z
status: gaps_found
score: 4/5 success criteria verified at primitive level; 0/5 verified at runtime-flow level
overrides_applied: 0
gaps:
  - truth: "Ack bank fires within 100ms of EventDetector.detect() return when rolling_ttft_avg_ms > 800"
    status: failed
    reason: "AckBank class + 40 OPUS placeholders + four-gate should_fire are loaded but NEVER invoked from runtime/coach.py. coach_loop:136 still calls session.generate_reply(allow_interruptions=False) directly with no should_fire / pick_for_event / PlaybackQueue.push call sites. Bank can never fire in production."
    artifacts:
      - path: "src/vibemix/runtime/coach.py"
        issue: "Zero references to AckBank, should_fire, pick_for_event. grep -rn 'AckBank' src/vibemix/runtime/ returns empty."
      - path: "src/vibemix/__main__.py:434"
        issue: "DJCoHostAgent constructed without an ack_bank instance — no plumbing exists upstream."
    missing:
      - "Construct AckBank() at __main__.py startup (after audio paths are wired)"
      - "Pass ack_bank + cancel_gate to coach_loop() (extend signature)"
      - "Inside coach_loop event branch: call ack_bank.should_fire(rolling_ttft_avg_ms, last_ack_at, last_response_at, cancel_cooldown_active=cancel_gate.last_cancel_at within 8s); if (True, 'fire') → ack_bank.pick_for_event(ev) → PlaybackQueue.push(pcm.tobytes())"
      - "Track rolling TTFT average from session.generate_reply turnaround (currently no telemetry exists at this seam)"
      - "Emit recorder.log_event('ack_fire', bucket=..., sample_index=..., reason=...) for Phase 16 attribution"
  - truth: "SpeechHandle.interrupt(force=True) wrapper preempts in-flight generation on priority-bumped events"
    status: failed
    reason: "CancelGate class is the sole owner of interrupt(force=True) (verified: exactly 1 grep hit), but no caller in src/vibemix/ ever invokes CancelGate.try_cancel. coach_loop holds the SpeechHandle in a local variable (line 136-138) but never compares incoming events' priority against the in-flight event, never instantiates a CancelGate, never injects one. Cancel-and-refire is dead in production."
    artifacts:
      - path: "src/vibemix/runtime/coach.py:136"
        issue: "session.generate_reply(allow_interruptions=False) — note allow_interruptions=False explicitly DISABLES the interrupt path that CancelGate would drive. handle is local, never shared with a gate."
    missing:
      - "Construct CancelGate(time_fn=time.monotonic, telemetry_cb=...) at __main__ or coach_loop entry"
      - "Hold the in-flight handle + in-flight Event in shared state (trigger_state dict already exists)"
      - "On every detected event, BEFORE calling generate_reply, call gate.try_cancel(handle, ev, in_flight_event) — fire-and-refire pattern"
      - "Wire telemetry_cb to ipc bus so soft-cap auto-disable surfaces in UI"
  - truth: "Gemini context caching active (cached_content via extra_kwargs); telemetry shows prompt_cached_tokens > 0 sustained"
    status: failed
    reason: "GeminiContextCache class fully implements 1024-token floor + 4min refresh + atomic-swap. DJCoHostAgent.invalidate_cache + 3-branch dispatch (warm/cold/disabled) wired correctly inside llm_node. BUT the agent is instantiated at __main__.py:434 with NO cache=... kwarg, so self._cache is None permanently → cache_state always 'disabled' → cached_content NEVER set on any Gemini call → prompt_cached_tokens will always be 0 in production."
    artifacts:
      - path: "src/vibemix/__main__.py:434-442"
        issue: "DJCoHostAgent(genai_client=..., clean_audio_buf=..., screen_buf=..., state=..., recorder=..., llm_inst=..., tts_inst=...) — cache kwarg missing"
      - path: "src/vibemix/runtime/coach.py"
        issue: "No GeminiContextCache import. No cache.create() call at startup. No refresh_loop task spawned."
    missing:
      - "Construct cache = GeminiContextCache(genai_client, body=AICoach.SYSTEM_INSTRUCTION_PADDED_FOR_CACHE, model=LLM_MODEL) at __main__"
      - "await cache.create() before session.start(agent)"
      - "asyncio.create_task(cache.refresh_loop(stop_event)) for the 4-min lifecycle"
      - "DJCoHostAgent(..., cache=cache) — pass through to constructor"
      - "Wire CancelGate telemetry callback OR ack-bank cancel-fire to call await agent.invalidate_cache() (chokepoint exists, no caller exists)"
deferred: []
human_verification: []
---

# Phase 19: Latency Stack v1 Verification Report

**Phase Goal:** Sub-300ms perceived first reaction + sub-2s actual voice-to-voice via prompt diet + Gemini context caching + 40-OPUS ack bank + cancel-and-refire — all without budget blowout.

**Verified:** 2026-05-14
**Status:** gaps_found
**Re-verification:** No — initial verification

## Verdict (one-liner)

The four CODE PRIMITIVES (CancelGate, prompt-diet build_prompt, GeminiContextCache, AckBank) all ship with green tests and clean APIs. The RUNTIME WIRING that connects those primitives to the live coach loop / agent constructor is **entirely absent** — none of the four levers is reachable in production today. CONTEXT D-08 explicitly mandates "All four mitigations ship together in v2.0 — none deferred to v2.x follow-up". This phase shipped the foundations but the v2.0 outcome is not deliverable until coach.py + __main__.py wire them.

## Goal Achievement

### Observable Truths (from ROADMAP success criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Ack bank (40 OPUS, 5 buckets) fires within 100ms when rolling_ttft_avg_ms > 800; rotation deque prevents collisions | ✗ FAILED | AckBank class + 40 OPUS files + 5 buckets all present and tested. `should_fire` 4-gate ladder works. BUT zero call sites in `src/vibemix/runtime/` — `grep -rn "AckBank" src/vibemix/runtime/` returns empty. Bank is loaded but unreachable. |
| 2 | Gemini context caching active (cached_content via extra_kwargs); prompt_cached_tokens > 0 sustained; cache lifecycle refreshes every 4 min; system instruction padded above 1024 tokens | ✗ FAILED | GeminiContextCache fully implemented (TTL=300, refresh=240, floor=1024 padding). DJCoHostAgent has 3-branch dispatch + invalidate_cache method. BUT `__main__.py:434` constructs `DJCoHostAgent(...)` WITHOUT `cache=...` kwarg → `self._cache=None` → `cache_state="disabled"` for every llm_node call → cached_content NEVER set on Gemini. prompt_cached_tokens will be 0 in production. |
| 3 | Prompt diet trims audio Part 18s→6s on non-PHASE events; screen Part skipped on MIX_MOVE/HEARTBEAT — TTFT win ≥500ms | ✓ VERIFIED | `AICoach.build_prompt(diet=True)` 800-token cap, compact evidence_line, ValueError on non-ack types. `DJCoHostAgent.llm_node` lines 213-214 compute `audio_seconds = DIET_AUDIO_SECONDS if diet else INVOKE_AUDIO_SECONDS` and `skip_screen = ev_type_for_diet in SCREEN_SKIP_EVENTS`. `snapshot_wav(buf, audio_seconds)` and `if screen_jpeg and not skip_screen` enforce both diet axes in the live llm_node path. v4 byte-identity preserved for diet=False (35 golden tests pass). **TTFT ≥500ms win cannot be measured without the cache + ack bank wired** — kept as VERIFIED at the primitive layer; runtime measurement deferred to Phase 16. |
| 4 | SpeechHandle.interrupt(force=True) wrapper preempts in-flight generation on priority-bumped events; HARD cap CANCEL_COOLDOWN_S=8.0 + SOFT cap 30/session telemetry auto-disable | ✗ FAILED | CancelGate class + 8s cooldown + 30/session soft cap + telemetry callback all implemented and tested (10 tests pass). Sole `interrupt(force=True)` callsite confirmed. BUT zero callers in `src/vibemix/`. `coach_loop:136` calls `session.generate_reply(allow_interruptions=False)` — `allow_interruptions=False` actively DISABLES the interrupt seam CancelGate would drive. Cancel-and-refire is dead in production. |
| 5 | Synthetic burst-event harness (20 events in 30s) emits ≤3 interrupted=True outcomes; min-ack-to-response gap = 400ms enforced | ✗ FAILED (harness not built) | Plan 19-04 surfaced the burst harness as a deliberate non-goal (planner SUMMARY deviation #5). `tests/runtime/test_burst.py` does not exist. The 400ms min-gap constant `ACK_MIN_GAP_S=0.4` IS asserted in `should_fire` and unit-tested; the end-to-end burst behavior is unmeasured. |

**Score:** 1/5 truths verified end-to-end; 4/5 verified at primitive layer only (code shipped, runtime unreachable).

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/vibemix/runtime/cancel.py` | CancelGate class + constants + sole interrupt(force=True) site | ✓ VERIFIED | 127 lines; 1 chokepoint confirmed via `grep -rE "interrupt\(force=True\)" src/vibemix/`. Constants `CANCEL_COOLDOWN_S=8.0`, `CANCEL_SOFT_CAP=30` exported. |
| `src/vibemix/state/event.py` | Event.priority field + EVENT_PRIORITY ladder | ✓ VERIFIED | priority field positioned last (preserves positional callers), EVENT_PRIORITY 8 known types + DROP=10 reserved. |
| `src/vibemix/state/coach.py` | build_prompt(diet=True) 800-token cap, compact evidence_line | ✓ VERIFIED | PROMPT_TOKEN_CAP_ACK=800, PROMPT_TOKEN_CAP_FULL=1500, ACK_ELIGIBLE_EVENTS frozenset, ValueError on non-ack diet=True. |
| `src/vibemix/agent/cache.py` | GeminiContextCache class + 1024-floor + 4min refresh + invalidate | ✓ VERIFIED (primitive) / ⚠️ ORPHANED (runtime) | All constants present (`GEMINI_CACHE_TOKEN_FLOOR=1024`, `GEMINI_CACHE_TTL_S=300.0`, `GEMINI_CACHE_REFRESH_S=240.0`). `caches.create` chokepoint = 3 grep hits (1 actual call + 2 doc/comments) all in this file. NO caller in src/vibemix/. |
| `src/vibemix/agent/dj_cohost.py` | cache kwarg + 3-branch dispatch + invalidate_cache method + diet wiring | ✓ VERIFIED (primitive) / ⚠️ ORPHANED (cache) | self._cache + 3 dispatch branches + invalidate_cache method all present. Diet wiring (audio_seconds + skip_screen) is fully active. BUT cache kwarg never set by __main__.py:434. |
| `src/vibemix/agent/ack_bank.py` | AckBank class + four-gate should_fire + per-bucket rotation deque | ✓ VERIFIED (primitive) / ⚠️ ORPHANED (runtime) | All constants (`ACK_TTFT_GATE_MS=800.0`, `ACK_MIN_GAP_S=0.4`, `ACK_ROTATION_MAXLEN=10`, `ACKS_PER_BUCKET=8`) present. Frozen BUCKET_FOR_EVENT via MappingProxyType. Loader, pick_for_event, should_fire all implemented. Zero callers in src/vibemix/. |
| `src/vibemix/audio/ack_bank/<bucket>/*.opus` | 40 OPUS files in 5 buckets × 8 | ✓ VERIFIED | `find ... -name "*.opus" -type f \| wc -l` → 40. `find ... -mindepth 1 -maxdepth 1 -type d \| wc -l` → 5. Silent placeholders (Achird-voice replacement = Kaan-action). |
| `scripts/generate_placeholder_acks.py` | Idempotent silent-OPUS generator | ✓ VERIFIED | Created; OGG-CRC32 deterministic patching ensures shasum-stable re-runs. |

### Key Link Verification (Wiring)

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `coach_loop` (runtime/coach.py) | `CancelGate.try_cancel` | direct call before generate_reply | ✗ NOT_WIRED | coach.py has zero CancelGate reference. `allow_interruptions=False` on line 136 actively disables the seam. |
| `coach_loop` (runtime/coach.py) | `AckBank.should_fire` + `pick_for_event` | direct call on event detection | ✗ NOT_WIRED | coach.py has zero AckBank reference. Bank never invoked. |
| `coach_loop` / `__main__.py` | `GeminiContextCache.create` + `refresh_loop` | startup wiring | ✗ NOT_WIRED | No cache instance created. No refresh_loop task spawned. |
| `__main__.py:434` (DJCoHostAgent constructor) | `cache=GeminiContextCache(...)` | kwarg | ✗ NOT_WIRED | Agent instantiated without cache kwarg → self._cache=None permanently. |
| `CancelGate.telemetry_cb` (on cancel-and-refire) | `agent.invalidate_cache()` | callback | ✗ NOT_WIRED | invalidate_cache method exists; no caller. |
| `AckBank` cancel-cooldown cross-cut | `CancelGate.last_cancel_at + CANCEL_COOLDOWN_S` | `should_fire(cancel_cooldown_active=...)` arg | ✗ NOT_WIRED | Both constants exist; no orchestrator computes the bool and passes it. |
| `AICoach.build_prompt(diet=True)` | `DJCoHostAgent.llm_node` | computed `diet = ev_type in ACK_ELIGIBLE_EVENTS` | ✓ WIRED | dj_cohost.py:213 — diet computed, threaded into both build_prompt callsites + audio_seconds + skip_screen. |
| Diet flag | events.jsonl telemetry | `recorder.log_event("llm_invoke", diet=..., audio_seconds=...)` | ✓ WIRED | Both fields appear in payload (Plan 19-02 telemetry contract). |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Phase-19 unit tests pass | `pytest tests/state/test_event_priority.py tests/runtime/test_cancel.py tests/state/test_coach_prompt_diet.py tests/agent/test_dj_cohost_prompt_diet.py tests/agent/test_cache.py tests/agent/test_dj_cohost_cached_content.py tests/agent/test_ack_bank.py -q` | 92 passed | ✓ PASS |
| v4 byte-identity preserved (diet=False) | `pytest tests/state/test_coach.py -q` | 35 passed | ✓ PASS |
| Targeted suite regression | `pytest tests/state/ tests/agent/ tests/runtime/ -q` | **722 passed, 1 failed (pre-existing test_persona_02 — out of scope), 1 skipped** | ✓ PASS (no new regressions) |
| Single chokepoint for `interrupt(force=True)` | `grep -rE "interrupt\(force=True\)" src/vibemix/ \| wc -l` | 1 | ✓ PASS |
| Single chokepoint for `caches.create` | `grep -rE "caches\.create" src/vibemix/ \| wc -l` | 3 (1 actual call + 2 doc/comments, all in cache.py) | ✓ PASS |
| 40 OPUS files in 5 buckets | `find src/vibemix/audio/ack_bank -name "*.opus" \| wc -l` && `find src/vibemix/audio/ack_bank -mindepth 1 -maxdepth 1 -type d \| wc -l` | 40 / 5 | ✓ PASS |

### Anti-Patterns Found

None of the standard anti-patterns (TBD/FIXME/XXX, empty handlers, hardcoded stub data) are present. The code primitives are clean. The "stub" here is structural: working modules with zero call sites in the live runtime path.

### Requirements Coverage

| REQ-ID | Description (per Plan SUMMARYs) | Status | Evidence |
|--------|--------------------------------|--------|----------|
| LATENCY-01 | 40-OPUS ack bank loaded | ✓ SATISFIED | 40 files in 5 buckets via AckBank constructor eager-load |
| LATENCY-02 | Per-bucket rotation deque (no collision) | ✓ SATISFIED | deque(maxlen=10) + LRU fallback, 7-pick window invariant tested |
| LATENCY-03 | Bucket dispatch frozen | ✓ SATISFIED | MappingProxyType BUCKET_FOR_EVENT, KeyError on unknown |
| LATENCY-04 | TTFT gate ≤800ms | ✓ SATISFIED (primitive) / ✗ BLOCKED (runtime) | Gate logic in `should_fire`; rolling_ttft_avg_ms never measured at runtime |
| LATENCY-05 | Min-ack-to-response gap = 400ms | ✓ SATISFIED (primitive) / ✗ BLOCKED (runtime) | ACK_MIN_GAP_S=0.4 enforced in `should_fire`; never reached in production |
| LATENCY-06 | cached_content via extra_kwargs | ✓ SATISFIED (primitive) / ✗ BLOCKED (runtime) | Dispatch in dj_cohost.py:296 builds GenerateContentConfig(cached_content=name); never reached because self._cache=None |
| LATENCY-07 | 4-min cache refresh / 5-min TTL | ✓ SATISFIED | `refresh_loop` with `asyncio.wait_for(stop_event.wait(), timeout=240.0)`; never spawned at runtime |
| LATENCY-08 | 1024-token cache floor padding | ✓ SATISFIED | `padded_body()` + `_CACHE_PAD_BLOCK` ~5KB deterministic; floor check `len(body)//4 >= 1024` |
| LATENCY-09 | Prompt diet (18s→6s + screen-skip) | ✓ SATISFIED | LIVE in dj_cohost.py llm_node — actually runs in production today (the only working lever of Phase 19 in production) |
| LATENCY-10 | Event.priority ladder (DROP=10 down to HEARTBEAT=1) | ✓ SATISFIED | EVENT_PRIORITY map + Event.priority field |
| LATENCY-11 | CancelGate 8s hard cooldown | ✓ SATISFIED (primitive) / ✗ BLOCKED (runtime) | CANCEL_COOLDOWN_S=8.0 enforced; gate never invoked |
| LATENCY-12 | 30/session soft cap + auto-disable telemetry | ✓ SATISFIED (primitive) / ✗ BLOCKED (runtime) | CANCEL_SOFT_CAP=30 + sticky disable + one-shot telemetry; gate never invoked |
| LATENCY-13 | Single chokepoint for `interrupt(force=True)` | ✓ SATISFIED | grep proves 1 call site |

**Net:** 13/13 satisfied at primitive layer; 6/13 BLOCKED at runtime (LATENCY-04/05/06/11/12 + the cache-state cross-cut).

## Gaps Summary

Phase 19 shipped four high-quality primitives (CancelGate, prompt-diet, GeminiContextCache, AckBank) with 92 passing tests and clean APIs. The CONTEXT mandate is unambiguous: **"All four mitigations ship together in v2.0 — none deferred to v2.x follow-up"**. Three of the four mitigations are not reachable in production today:

1. **AckBank** is loaded but never invoked — coach.py has zero references to it.
2. **CancelGate** has its sole `interrupt(force=True)` chokepoint but no caller — coach.py uses `allow_interruptions=False` which explicitly disables that seam.
3. **GeminiContextCache** is never instantiated at startup; `__main__.py:434` constructs `DJCoHostAgent(...)` without the `cache=...` kwarg, so `cache_state="disabled"` for every llm_node call. `prompt_cached_tokens` will be 0 in production.

Only **prompt-diet (LATENCY-09)** is genuinely live — `audio_seconds` + `skip_screen` actually flow into `snapshot_wav` and the screen-Part guard inside `llm_node`. That is one out of four levers.

The deferral is honestly tracked in STATE.md (`P19-04 followup: AckBank wiring in coach loop`) and 19-04 SUMMARY surfaced-followups table flags both AckBank wiring and the Achird-voice OPUS replacement. The cache wiring deferral is implicit — referenced in 19-03 SUMMARY's "Cancel-aware invalidate hook" section as a Plan 19-04 / coach loop refactor responsibility — but no separate STATE.md entry exists for the cache-side wiring (`__main__.py:434` cache kwarg, `cache.create()` call, `refresh_loop` task spawn). The CancelGate runtime wiring is similarly only mentioned in 19-01 SUMMARY's "Coach loop refactor (followup)" section.

### What Would Close Each Gap

**Gap 1 — AckBank wiring** (estimated: 1-2 hour plan):
- Construct `AckBank()` in `__main__.py` startup
- Extend `coach_loop()` signature: `ack_bank: AckBank, cancel_gate: CancelGate, ttft_meter: TTFTMeter`
- Add TTFT measurement around `session.generate_reply` call
- In event branch, BEFORE generate_reply: `should_fire = ack_bank.should_fire(...)`; if `(True, "fire")` → `pick_for_event(ev)` → `PlaybackQueue.push(pcm.tobytes())` → `last_ack_at = time.monotonic()`
- Emit `recorder.log_event("ack_fire", bucket=..., sample_index=..., reason=...)`

**Gap 2 — CancelGate wiring** (combined with Gap 1):
- Construct `CancelGate(time_fn=time.monotonic, telemetry_cb=lambda p: ws_bus.emit({"event": "session.cancel", **p}))` in `__main__.py`
- Hold in-flight handle + in-flight Event in `trigger_state` dict
- On every detected event BEFORE generate_reply: if in-flight, call `cancel_gate.try_cancel(in_flight_handle, incoming_ev, in_flight_ev)` → if returns True, refire with new event
- Switch `allow_interruptions=False` → `allow_interruptions=True` on generate_reply (CancelGate now owns the cancel decision)

**Gap 3 — Cache wiring** (combined with Gap 1):
- In `__main__.py`, before `session.start(agent)`:
  ```python
  cache = GeminiContextCache(
      client=genai_client,
      body=AICoach.SYSTEM_INSTRUCTION,  # already > 1024 token-proxy in v4 baseline
      model=LLM_MODEL,
  )
  await cache.create()
  asyncio.create_task(cache.refresh_loop(stop_event))
  agent = DJCoHostAgent(..., cache=cache)
  ```
- In coach_loop: when `cancel_gate.try_cancel` returns True, ALSO call `await agent.invalidate_cache()` (cancel-and-refire invalidates the cached prefix that was about to be used by the now-cancelled generation)

These three gaps share an architectural seam: a single coach-loop refactor that introduces TTFT measurement + a CancelGate-mediated `generate_reply` wrapper + an ack-bank pre-LLM gate + a cache-aware agent constructor. They are tightly coupled and should ship as one plan.

---

*Verified: 2026-05-14*
*Verifier: Claude (gsd-verifier)*
