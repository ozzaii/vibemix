# Phase 56: Performance + Live Mascot - Pattern Map

**Mapped:** 2026-05-21
**Files analyzed:** 11 (8 modify/extend + 2 new test fixtures-or-traces + 1 new vitest assertion file-or-block)
**Analogs found:** 11 / 11 (this is a verify-and-EXTEND phase — every target file already exists; the "analog" for a modified file is its own current structure + the closest sibling already doing the thing being added)

> **Build-surface ground truth (from 56-CONTEXT POST-RESEARCH CORRECTION + 56-RESEARCH Rig Reality):**
> The LIVE-05/05a build target is the **Three.js rig under `tauri/ui/src/mascot/`** (the file the shipped Tauri app actually loads — `tauri/ui/dist/mascot.html` ← vite ← `tauri/ui/mascot.html`), **NOT** root `mascot.html`. Root `mascot.html` is a dev/CI overlay only (its sprite PNGs don't exist on disk); keep it audit-green, add NO new modes there. The 56-UI-SPEC's mode taxonomy, anti-slop gating, hysteresis timing, and 60fps budget are the **contract**; the **implementation surface is the Three.js TS modules**.
>
> **Two RESEARCH "gaps" are partly stale — verify before planning:**
> 1. `stateForPhase` in `event-dispatcher.ts:110-129` **ALREADY maps `"low"` → `idle_bop_to_beat_mellow` and `"peak"` → `dance_hard`** (lines 120-121, 113-114). The gap is NOT "unmapped" — it is "mapped without music-confirmation". Treat gap #1 as "add the defence-in-depth `music`/level guard to drop/peak/breakdown", not "add a missing case".
> 2. `speaking` is currently driven by the **`AI_GENERATING_REPLY` event → `talk_loop`** (event-dispatcher.ts:225-230), not by a `voice > 0.05` level read. The UI-SPEC asks for level-driven speaking enter/exit hysteresis. Confirm whether to keep the event-driven path (already wired, already CI-covered) or add a level-driven path — the planner should prefer EXTENDING the event path unless the live-drive needs the level read.

---

## File Classification

| Target File | Role | Data Flow | Closest Analog (own structure + sibling) | Match Quality |
|-------------|------|-----------|-------------------------------------------|---------------|
| `tauri/ui/src/mascot/event-dispatcher.ts` | controller (pure dispatcher) | event-driven / transform | self (stateForPhase + SnapshotSlice) + `state-machine.ts` beat-lock guard pattern | exact (self) |
| `tauri/ui/src/mascot/types.ts` | model (vocabulary contract) | transform | self (`SnapshotSlice` analog is `StateRequest`; emotion/mood/reaction unions already present) | exact (self) |
| `tauri/ui/src/mascot/state-machine.ts` | service (pure FSM) | event-driven | self (`planTransition` block-rule + beat-lock = the hysteresis analog) | exact (self) |
| `tauri/ui/src/mascot/index.ts` | provider (bus→dispatch wiring) | event-driven / request-response | self (`handleMessage` snapshot-reader at :181-208) | exact (self) |
| `src/vibemix/runtime/ttft.py` | utility (telemetry meter) | streaming / transform | self (rolling deque) — telemetry-only; budget is asserted in TEST, not added here | exact (self) |
| `src/vibemix/runtime/soak.py` | utility (underrun/RSS sampler) | batch / streaming | self (`SoakCounters.observe_pull` + `is_underrun`) | exact (self) |
| `src/vibemix/llm/thinking_gate.py` | middleware (boot-time config guard) | request-response | self (`validate_live_config` aggregating validator) | exact (self) |
| `tests/runtime/test_ttft.py` | test (unit) | request-response | self (deterministic `time_fn` injection) | exact (self) |
| `tests/llm/test_thinking_gate.py` | test (unit) | request-response | self (pass/fail-case pairs at :34-147) | exact (self) |
| `tests/runtime/test_soak_stability.py` | test (integration/slow) | batch | self (real `PlaybackQueue` drive + `assert_healthy`) | exact (self) |
| `tests/integration/test_mascot_dispatch_latency.py` | test (integration) | streaming | self (websockets serve/connect p95) | exact (self) |
| `tests/e2e/test_phase_41_latency_stack_integration.py` | test (e2e) | request-response | self (`test_agent_validates_live_config` LAT-08 scenario) | role-match |
| `tauri/ui/src/mascot/state-machine-fixtures.test.ts` | test (vitest replay harness) | event-driven | self (`replayTrace` + `matchExpected`) | exact (self) |
| `tauri/ui/src/mascot/__fixtures__/event-traces.json` | test fixture (data) | data | self (9 existing traces; PHASE-subtype shape) | exact (self) |

---

## Pattern Assignments

### `tauri/ui/src/mascot/event-dispatcher.ts` (controller, event-driven) — THE primary anti-slop gap surface

**Analog:** self — `stateForPhase()` (lines 110-129) is the function to harden; the `state-machine.ts` beat-lock guard (lines 179-206) is the sibling pattern for "trust the signal but block when a confirming value disagrees".

**Current `stateForPhase` — already maps low/peak, lacks music-confirmation** (lines 110-129):
```typescript
function stateForPhase(phase: string): MascotState | null {
  switch (phase) {
    case "drop":      return "dance_hard";   // ← GAP: fires on phase alone; needs && music >= PEAK_RMS
    case "peak":      return "dance_hard";   // ← already mapped (RESEARCH "unmapped" claim is stale)
    case "groove":    return "idle_bop_to_beat_energetic";
    case "build":     return "idle_bop_to_beat_energetic";
    case "low":       return "idle_bop_to_beat_mellow";  // ← already mapped
    case "silent":    return "idle_breathe";
    case "breakdown": return "idle_breathe"; // ← GAP: contract wants && music < LOW_RMS
    default:          return null;           // ← anti-slop default: unknown phase = no transition (KEEP)
  }
}
```

**Anti-slop guard to ADD — mirror the `state-machine.ts` beat-lock typed-guard shape** (the established "all conditions must hold or fall through" pattern, state-machine.ts:179-206). Mirror the Python source-of-truth constants verbatim (do NOT invent new thresholds):
```typescript
// Constants mirror src/vibemix/audio/constants.py — SILENT_RMS=0.012, LOW_RMS=0.040, PEAK_RMS=0.110
// drop  entry requires: phase === "drop"      && music >= PEAK_RMS (0.110)
// breakdown entry req.: phase === "breakdown" && music <  LOW_RMS  (0.040)
// a contradicting frame → return null (treat as "no signal" — current mode persists). This is
// the SAME discipline as the existing `default: return null` and the dispatchEvent
// "unknown subtype → return null (silent — anti-slop)" rule at lines 259-261.
```

**Required type change:** `SnapshotSlice` (lines 58-63) carries `bpm/bpm_confidence/downbeat_phase/mood` but **NOT `music`/`voice`** — the level the guard needs is not yet on the snapshot. The guard requires adding `music` (and `voice` if speaking goes level-driven) to `SnapshotSlice` AND to the `PHASE` case's `stateForPhase(to)` call site (line 202-203). Pass the level through and gate the return.

**PHASE case wiring** (lines 200-223) — where the guarded `stateForPhase` plugs in:
```typescript
case "PHASE": {
  const to = strField(m.payload, "to");
  if (to === null) return null;
  const target = stateForPhase(to /* + snapshot.music for the new guard */);
  if (target === null) return null;            // ← contradictory frame falls out here = anti-slop
  // ... existing beat-lock wiring unchanged ...
}
```

**Anti-slop discipline already present (preserve verbatim):** `dispatchEvent` returns `null` on unknown type/subtype/malformed (lines 163-166, 184-185, 259-261). The new guard is the SAME shape — never throw, never invent a default mode.

---

### `tauri/ui/src/mascot/types.ts` (model, transform)

**Analog:** self — `SnapshotSlice` (in event-dispatcher.ts) is shaped like `StateRequest` here (lines 188-201); the mood/emotion/reaction unions you may tint with already exist.

**Existing vocabulary the mode machine reuses (do NOT add new modes/states):**
- `MascotState` union (lines 26-67) — already has ≥21 states: `idle_breathe`, `idle_breathe_slow`, `idle_bop_to_beat_mellow`, `idle_bop_to_beat_energetic`, `dance_hard`, `talk_loop*`, `react_*`, `sleep`, etc. The 6 UI-SPEC modes map onto EXISTING states — no new union members needed for the headline.
- `STATE_CLASS` (lines 93-127) + `STATE_PRIORITY` (lines 140-151) — `effect 100 > talk 80 > anticipation 70 > react 60 > dance 40 > explanation 30 > idle 20 > misc 10`. This priority ladder IS the `speaking`-overrides-music rule (talk=80 > dance=40). Adding a state REQUIRES a `STATE_CLASS` entry (the `Record<MascotState,…>` type enforces it).
- `MascotEmotion` (line 222) = `neutral|focused|hyped|concerned` — the `emotion` bus field (finer eye/brow nudge).
- `MASCOT_REACTIONS` whitelist (lines 243-261) — `wave|point_left|point_right|fist_pump|nod|headbang|surprised` — the `reaction_intent` one-shot gesture overlay whitelist.
- `mood` is NOT in this file as a state — it lives in `mood.ts` `MOOD_PROFILES` (`hype-man|teacher|coach`), a variant TINT, not a 7th mode.

**If `music`/`voice` get added to `SnapshotSlice`:** keep the const-asserted-union, no-pydantic, zero-runtime-cost discipline noted at lines 14-17.

---

### `tauri/ui/src/mascot/state-machine.ts` (service, event-driven) — the hysteresis analog

**Analog:** self — `planTransition` (lines 137-215) already implements priority + block-rule + beat-lock, which together ARE the anti-flicker layer. The UI-SPEC's "min dwell" hysteresis maps onto the existing `pendingSwitch` / `schedule_for_downbeat` mechanism + `STATE_PRIORITY`.

**Block-rule pattern (the `speaking`-overrides-music guard already exists)** (lines 165-174):
```typescript
if (
  (currentClass === "talk" || currentClass === "effect") &&
  requestedPriority < currentPriority
) {
  return { action: "deny", blendMs: 0, reason: `blocked_by_${currentClass}` };
}
```
This is why `talk_loop` (class talk, priority 80) blocks incoming `dance`/`idle` — the UI-SPEC's "speaking overrides every music mode" is ALREADY enforced here. Do not rebuild it.

**Beat-lock typed-guard (the shape to mirror for the new music-confirm guard)** (lines 179-206): "all of bpmConfidence ≥ 0.6 AND bpm > 0 AND downbeatPhase present → schedule, else fall through to switch_now." Copy this conjunction shape for `drop = phase + music>=PEAK_RMS`.

**Purity invariant (load-bearing — the verifier greps this file):** no wall-clock reads (every fn takes `now: number`), no timers, no `three` imports (lines 1-12). Any hysteresis addition MUST stay pure — express delays as data on `MachineState`, never `setTimeout`. The forbidden tokens are grep-gated.

**`tickIdleTimeout`** (lines 301-308) — the existing class-based idle/sleep timeout; the `idle`/dead-air mode reuses this, do not invent a parallel timer.

---

### `tauri/ui/src/mascot/index.ts` (provider, event-driven) — the bus→snapshot→dispatch wiring

**Analog:** self — `handleMessage` (lines 181-240) is the integration seam. Snapshots are state-READERS (update `currentSnapshot`), events are state-WRITERS (call `dispatchEvent`).

**Snapshot-reader pattern — where `music`/`voice` must be threaded in** (lines 187-208):
```typescript
if (/* message.type === "snapshot" */) {
  const m = message as Record<string, unknown>;
  currentSnapshot.bpm = typeof m.bpm === "number" ? m.bpm : currentSnapshot.bpm;
  currentSnapshot.bpm_confidence = ...;
  currentSnapshot.downbeat_phase = ...;
  currentSnapshot.mood = ...;
  // ← ADD: currentSnapshot.music / .voice from the same flat frame (ws_bus broadcasts them)
  return;  // snapshots never trigger transitions
}
```
The `currentSnapshot` default (lines 168-173) must gain `music: 0, voice: 0` defaults if `SnapshotSlice` grows.

**Dispatch + apply + crossfade pattern (unchanged)** (lines 210-239):
```typescript
const result = dispatchEvent(machine, message, now, currentSnapshot);
if (!result) return;
machine = result.machine;
if (result.plan.action === "switch_now" && result.plan.target) {
  renderer.crossFadeTo(result.plan.target, result.plan.blendMs);
}
```

**60fps invariant (PERF-03):** the dev-only `DISPATCH_SLOW_MS` warn (lines 211-218) already pins dispatch cost. Mode-select is a handful of float compares (<0.5ms). Single rAF loop — mode eval happens inside the existing `tick`, never a second loop / `setInterval`.

---

### `src/vibemix/runtime/ttft.py` (utility, streaming) — DO NOT add a gate; assert in test

**Analog:** self — already complete. **No code change expected** unless a named budget constant is added.

**Critical correction (Pitfall 1):** TTFTMeter is **telemetry-only**. The docstring (lines 6-9) states the ack-bank `should_fire` gate was retired. There is **no `should_fire` method**. Do NOT re-introduce a runtime TTFT gate. PERF-01's lever is `thinking_gate.py` (below); TTFT is asserted as a telemetry budget over replayed traffic in `test_ttft.py`.

**The meter's public surface** (lines 63-95): `record_event_fired`, `record_first_chunk`, `rolling_avg_ms()` (default sentinel 1500.0ms when empty), `samples_count()`. Window=8, single-threaded asyncio (no lock). The PERF-01 assertion replays samples through this and asserts `rolling_avg_ms() <= BUDGET`.

**Budget number is undefined in code (Open Q2 / Assumption A1):** no `LIVE_TTFT_BUDGET_MS` constant exists. Plan should assert `<= 1500.0` (the sentinel floor) as a conservative regression floor and flag for Kaan to tighten on real hardware, OR gate behind `checkpoint:human-verify`.

---

### `src/vibemix/runtime/soak.py` (utility, batch) — reuse the underrun counter, invent nothing

**Analog:** self — already complete. PERF-02 EXTENDS the **test**, not this file.

**The underrun classifier (the "don't hand-roll" surface)** (lines 41-91):
```python
def is_underrun(chunk, requested, *, had_pending, held=None) -> bool:
    # PlaybackQueue.pull(n) ALWAYS returns n bytes (zero-pads) → length is useless.
    # Underrun = had_pending AND held < requested (or all-zero full-length pull).
```
`SoakCounters.observe_pull(...)` increments `underruns`; `assert_healthy(result, max_growth_bytes=..., max_underruns=0)` asserts bounded RSS **growth** (not absolute — macOS noise) + zero underruns. `SoakResult.growth_bytes` is the delta property (lines 120-122).

**PERF-02 task surface:** drive `run_soak(queue=<real PlaybackQueue>)` under simulated both-mode reaction traffic → assert `result.underruns == 0`. The CONTEXT explicitly forbids a new counter.

---

### `src/vibemix/llm/thinking_gate.py` (middleware, request-response) — PERF-01's real lever

**Analog:** self — already complete. **No code change expected.** PERF-01 PINS this via positive+negative test assertions.

**The validator (the gate that actually protects TTFT)** (lines 73-107):
```python
def validate_live_config(cfg: GenerateContentConfig) -> None:
    # raises LiveCoachConfigError when:
    #   thinking_level != MINIMAL  ("anything higher adds 7s+ TTFT regression")
    #   service_tier == FLEX       ("Flex SLA = live UX collapse")
    # Aggregates ALL violations into one message. Pure callable, zero per-turn cost.
```
`_ALLOWED_THINKING = {"MINIMAL"}` (line 40), `_DISALLOWED_TIER = {"FLEX"}` (line 43). Runs ONCE at agent/llm_factory init.

**PERF-01 task:** assert the LIVE coach's actual `GenerateContentConfig` passes `validate_live_config` (positive pin) AND that a MEDIUM/HIGH config is rejected (negative pin) — proves the 7s+ regression protection is live.

---

### `tests/runtime/test_ttft.py` (test, unit) — EXTEND

**Analog:** self — deterministic `time_fn` injection (lines 28-37, 98-109). Add the PERF-01 budget assertion: replay a sequence of realistic event_fired→first_chunk samples through `TTFTMeter`, assert `rolling_avg_ms() <= BUDGET` (1500.0 floor pending Open Q2). Mirror the existing `state[0]` clock-driving pattern. Do NOT call any `should_fire` (it doesn't exist).

---

### `tests/llm/test_thinking_gate.py` (test, unit) — EXTEND

**Analog:** self — the pass/fail case pairs (lines 34-147) are the template. The LIVE-config positive+negative pin already exists in spirit (`test_dj_cohost_init_passes_with_default_config` :240-259, `test_dj_cohost_init_raises_on_flex_tier` :262-290). PERF-01 may only need an explicit "the production LIVE `_gen_cfg` passes the gate" assertion if not already covered by `test_validate_not_called_per_turn`. Reuse `_build_state()` (:226-237) + the `mocker.patch.object(Agent, "__init__", …)` seam.

---

### `tests/runtime/test_soak_stability.py` (test, integration/slow) — EXTEND

**Analog:** self — drives a REAL `PlaybackQueue` through `run_soak` / `SoakCounters` (imports at :30-37). PERF-02 task: add a scenario that drives the queue under simulated both-mode reaction traffic (party + feedback generating playback chunks) → `assert result.underruns == 0` via `assert_healthy(..., max_underruns=0)`. Keep the unit/slow/deselect-guard 3-layer structure (docstring :3-12). The real ≥30-min soak stays Kaan-action (`python -m vibemix.runtime.soak --seconds 1800 --attach`).

---

### `tests/integration/test_mascot_dispatch_latency.py` (test, integration) — EXTEND

**Analog:** self — real `websockets.serve`/`connect`, 100 frames @ 30Hz, asserts `p95(t_recv - t_emit) < 50ms` (sidecar-side half of the 100ms MASCOT-08 budget; webview adds ≤10ms, 40ms slack). PERF-03 task: add a synthetic mode-transition frame to the emitted set and confirm the budget still holds (mode-select is <1ms, so it does). `@pytest.mark.integration`. Do NOT grep/import `mascot.html` (CI gate forbids it — Pitfall 2).

---

### `tests/e2e/test_phase_41_latency_stack_integration.py` (test, e2e) — EXTEND

**Analog:** self — `test_agent_validates_live_config` is the LAT-08 / PERF-01 cross-plan scenario (header :15-44). PERF-01 e2e leg: assert TTFT integration across the latency stack stays within budget on replayed traffic + thinking=MINIMAL holds end-to-end. `@pytest.mark.e2e`. SDK-boundary mock posture (header §VCR — no cassettes, mock the genai client directly).

---

### `tauri/ui/src/mascot/state-machine-fixtures.test.ts` + `__fixtures__/event-traces.json` (test, event-driven) — EXTEND (the exact harness CONTEXT §specifics asks for)

**Analog:** self — `replayTrace` (lines 90-229) + `matchExpected` (lines 237-254) replay `event-traces.json` traces through `dispatchEvent + planTransition + applyTransition`, ±100ms tolerance, pure (no Three.js/DOM, <50ms). 9 traces exist today (`track_change_then_idle`, `drop_then_groove`, `ai_speaks_then_done`, `silent_phase`, `talk_blocks_dance`, `beat_locked_entry_at_high_confidence`, …).

**Add to `__fixtures__/event-traces.json` (NEW traces):**
1. **Multi-mode sequence:** `silent → build → drop(music>=0.110) → breakdown(music<0.040) → voice>0.05` — assert each enters the right mode; hysteresis blocks single-frame flicker.
2. **Anti-slop contradiction (Wave 0 — the LIVE-05a acceptance):** frame `{ phase:"drop", music: 0.05 }` → mode does NOT change (held). This is the highest-value new assertion.

**Cross-language pin:** the same fixture is replayed Python-side by `tests/integration/test_mascot_event_taxonomy_e2e.py` (validates JSON shape vs the taxonomy). If you add new event subtypes/states to the fixture, that test must stay green too. Snapshot frames in the fixture currently carry `bpm/bpm_confidence/downbeat_phase/mood` (DEFAULT_SNAPSHOT :39-44) — add `music`/`voice` to the snapshot shape there to drive the new guard.

---

## Shared Patterns

### Anti-slop "unknown/contradiction → no-op" (THE phase-defining discipline)
**Source:** `tauri/ui/src/mascot/event-dispatcher.ts:163-166, 184-185, 259-261` (`return null` on unknown type/subtype/malformed) + `ws-client.ts:117-127` (try/catch `JSON.parse`, drop non-JSON silently).
**Apply to:** the new music-confirmation guard in `stateForPhase`/`PHASE` case — a frame whose `phase` and `music` disagree returns `null` = current mode persists. Never throw, never default to a decorative mode. This doubles as the V5 input-validation security control (malformed ws frame → no-op, never crash).
```typescript
// established shape — copy it verbatim for the level guard:
default:
  // Anti-slop discipline: unknown subtype is dropped silently.
  return null;
```

### Pure-function FSM (no wall-clock, no timers, no three.js)
**Source:** `state-machine.ts:1-12` purity docstring; `event-dispatcher.ts:24-30` purity discipline (greps for forbidden `Date.now`/`setTimeout` tokens).
**Apply to:** ALL new mode/hysteresis logic — every function takes `now: number`, scheduling is data on `MachineState`, the renderer's single rAF loop fires it. This is what keeps it vitest-testable in <50ms and CI-gated. The verifier greps for the forbidden patterns — putting timers here breaks the build.

### Source-of-truth thresholds (mirror Python, never invent)
**Source:** `src/vibemix/audio/constants.py:53-55` — `SILENT_RMS=0.012`, `LOW_RMS=0.040`, `PEAK_RMS=0.110`; `src/vibemix/state/emotion_router.py:38-39` — `RMS_HIGH=0.18`, `RMS_LOW=0.08`.
**Apply to:** the mascot's music-confirmation boundaries so they agree with `state.phase`. Define them as named consts in the TS guard (a comment citing `audio/constants.py`), never as magic numbers.

### Telemetry-budget assertion, NOT a runtime gate (PERF-01)
**Source:** `runtime/ttft.py:6-9` docstring (ack-bank retired) + `llm/thinking_gate.py:73-107` (the real gate).
**Apply to:** PERF-01 tests — pin TTFT as `rolling_avg_ms() <= budget` over replayed traffic AND pin `validate_live_config` rejects non-MINIMAL/FLEX. Do not write a test that calls a `should_fire` method (none exists).

### Observe-don't-instrument hot paths (PERF-02/03)
**Source:** `runtime/soak.py:20-22` ("audio hot path NOT modified — underruns are observed") + `perf-observer.ts:29-33` (DOM-only sensor, runs whether mascot mounted or not) + the dispatch-latency test observing from a real client.
**Apply to:** every perf assertion — drive the real component and observe its boundary; never add probes to prod hot paths or audio/reaction latency. The mascot is a leaf bus consumer (RESEARCH architecture diagram) — structurally cannot add reaction-path latency.

### Mood-as-variant-tint, not a new mode
**Source:** `tauri/ui/src/mascot/mood.ts:38-98` (`MoodProfile` + `MOOD_PROFILES` for `hype-man|teacher|coach`); `src/vibemix/state/music_state.py:63` (`mood` field). NOT to be confused with `emotion` (`emotion_router.py` → `neutral|focused|hyped|concerned`) — Pitfall 5.
**Apply to:** mood re-tints the SAME mode (expression family/scale-pump intensity), it does not add a 7th mode. `emotion` is a finer eye/brow nudge layered on top; `emotion == null` → no-op.

---

## No Analog Found

None. Every target file already exists in-tree with a directly applicable structure. This is an extend-and-pin phase — the failure mode is *re-implementation* (building a second mode machine in the wrong/invisible/untestable file), not missing analogs.

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| — | — | — | All target files have exact self-analogs. |

---

## CI / Build Constraints (must stay green — RESEARCH Runtime State Inventory)

- **`mascot-audit` workflow** (`.github/workflows/mascot-audit.yml`) triggers on `tauri/ui/src/mascot/**` (line 21). Three gates:
  - **`mascot-tauri-only-grep`** — do NOT reference `mascot.html` from `tests/`, `e2e/`, `scripts/ci/` (Pitfall 2). New mode tests target the TS logic / fixtures, never grep the HTML.
  - **`mascot-anti-slop`** (Phase 47 grep gate) — keep mode captions / clip names off the blocklist.
  - **`mascot-event-coverage`** — `npm test -- event-coverage-matrix pools anticipation` (15-event × 4-layer matrix). If you touch `EVENT_LAYER_PRIORITY_MAP` (event-dispatcher.ts:377-402) it must stay covered.
- **Build artifact:** webview changes require `npm run build` in `tauri/ui/` to reach `tauri/ui/dist/mascot.html` (the shipped surface). This is exactly why root `mascot.html` edits never reach users — no build step includes it.
- **Root `mascot.html`** — keep audit-green, add no new modes/art. Its sprite PNGs don't exist on disk (renders nothing); descope its palette cleanup unless Kaan confirms the dev `file://` overlay is still used (Open Q3 / Assumption A2).

## Metadata

**Analog search scope:** `tauri/ui/src/mascot/**` (Three.js rig + tests + fixtures), `src/vibemix/runtime/` (ttft, soak, ws_bus), `src/vibemix/llm/` (thinking_gate), `src/vibemix/state/` (phase, music_state, emotion_router), `src/vibemix/audio/constants.py`, `tests/{runtime,llm,integration,e2e}/`, `.github/workflows/mascot-audit.yml`.
**Files read this session:** event-dispatcher.ts, state-machine.ts, types.ts, state-machine-fixtures.test.ts, ws-client.ts, perf-observer.ts, index.ts (snapshot section), mood.ts (surface), ttft.py, soak.py, thinking_gate.py, phase.py, ws_bus.py (frame), constants/emotion/music_state (grep), test_ttft.py, test_thinking_gate.py, test_soak_stability.py (head), test_mascot_dispatch_latency.py (head), test_phase_41_latency_stack_integration.py (head), event-traces.json (names), mascot-audit.yml (scope).
**Pattern extraction date:** 2026-05-21
