# Phase 56: Performance + Live Mascot - Research

**Researched:** 2026-05-21
**Domain:** Real-machine live-session performance (TTFT / playback dropouts / 60fps) + reactive mascot mode state machine grounded on the rich bus signals (anti-slop)
**Confidence:** HIGH (this is a verify-and-extend phase against existing in-tree code; nearly every claim is grounded by reading the actual source this session)

---

## Summary

This is an **extend-and-pin** phase, not a greenfield build. Every performance substrate already exists in `src/vibemix/runtime/` (`TTFTMeter`, `soak.py` underrun counter, `thinking_gate.validate_live_config`) and the mascot reactive surface already exists in **two** divergent files. The phase's real work is (1) asserting the perf budgets hold under real reaction traffic, (2) building/finishing the ≥6-mode anti-slop state machine, and (3) **resolving which mascot file the user actually sees** — the single decision that determines whether this phase's headline deliverable reaches the screen.

**The one thing the planner MUST reconcile before writing tasks:** the 56-CONTEXT and 56-UI-SPEC both target the **root `mascot.html`** (a 253-line inline-JS sprite toy). But the **shipped Tauri app does NOT load that file** — it loads `tauri/ui/dist/mascot.html`, built by vite from `tauri/ui/mascot.html` (the Three.js WebGL rig). I verified this on disk three ways (below). The Three.js rig is a mature, fully-vitest-tested 4-layer state machine that **already** consumes `phase`/`mood`/`emotion`/`reaction_intent`/`bpm`/`bpm_confidence`/`downbeat_phase`, already maps `phase → mascot mode` (`stateForPhase`), already has anti-slop "unknown→null" discipline, already pins fps client-side (`perf-observer.ts`), and already has hysteresis-equivalent priority/block rules. If the plan targets root `mascot.html` literally, it ships LIVE-05/05a to a file users never see while leaving the actual user-visible mascot's gaps unaddressed. **This contradiction must be raised and a decision locked before planning** (see Open Questions Q1 — it is the highest-value item in this document).

**Primary recommendation:** Pin the three perf budgets by **extending** the existing Python tests (`test_ttft.py`, `test_soak_stability.py`, `test_thinking_gate.py`, `test_mascot_dispatch_latency.py`) — these are already green and own the substrate. For the mascot many-modes work, **target the shipped Three.js rig** (`tauri/ui/src/mascot/`) where the user-visible surface, the vitest fixture-replay harness, and 80% of the machinery already live — closing the *specific gaps* (≥6 distinct modes gated on `music`-confirmation, the `phase=="low"`/`"peak"` unmapped values, drop = `phase + PEAK_RMS` defence-in-depth) rather than re-implementing a parallel state machine in untestable inline HTML. Treat the root `mascot.html` palette/font cleanup (cyberpunk → CDJ Whisper) as a separate, smaller in-scope hygiene task if the dev `file://` overlay is still used as a live-drive surface.

---

## User Constraints (from CONTEXT.md)

> Source: `.planning/phases/56-performance-live-mascot/56-CONTEXT.md`. Mode: orchestrator-grounded, autonomous `fully` — these are Claude's-discretion calls already made, treat as locked unless this research surfaces a contradiction (it surfaces one — see Open Q1).

### Locked Decisions

**Mascot — many modes (LIVE-05 / LIVE-05a) — Kaan's headline ask:**
- Drive the mascot off the rich bus signals it currently ignores (`phase`, `mood`, `bpm`, `reaction_intent`, `detected_genre`, `genre_confidence`, levels) — not just `music`+`voice`.
- **≥6 distinct modes, each gated to a REAL event** (anti-slop): idle/dead-air, vibing/groove, building, drop/peak, breakdown/chill, speaking/emoting. Mood tints the variant. **No random/decorative mode changes** — a flip must correspond to a real musical/session event. Add hysteresis (mirror state-side `HysteresisState`) so modes don't flicker bar-to-bar.
- **Keep the mascot OUT of the audio loop** — pure personality surface reading the bus; must not add latency to the reaction path.
- **Scope realistically for v4.0:** make the EXISTING rig react across many modes off real signals. Full 3D Three.js/GLB rig (Meshy/Hunyuan3D + Mixamo) is v2.x — do NOT build it here. Richer per-mode art is Phase 57 (Sexify). **Confirm the current rig state before planning** (done — see Rig Reality below).

**Performance (PERF-01/02/03):**
- **TTFT (PERF-01):** `runtime/ttft.py::TTFTMeter` measures event_fired→first_chunk rolling-avg ms. Assert rolling TTFT stays within live-path budget on real reaction traffic. **Critical lever:** `llm/thinking_gate.py` — Gemini thinking budget MUST stay MINIMAL; higher adds 7s+ TTFT regression. Pin that gate.
- **Dropouts (PERF-02):** reuse the Phase-51 soak underrun counter (`runtime/soak.py` observing `PlaybackQueue`) — assert zero playback underruns under real-session load (both modes generating traffic). Don't invent a new counter.
- **60fps (PERF-03):** mascot `requestAnimationFrame` loop + UI must hold 60fps on the integrated-GPU MacBook. The new mode state machine must not blow the frame budget (cheap CSS/canvas transitions, no per-frame layout thrash). Extend existing perf/latency tests.
- The real "TTFT/60fps/no-dropout under a real set on Kaan's Mac" is **Kaan-action** — engineering ships budgets + automated/synthetic assertions + measurement recipe; the felt-perf confirmation rides the live-drive surface.

### Claude's Discretion
The entire decisions block above is Claude's discretion under autonomous `fully` — the orchestrator pre-grounded it. The choices that remain genuinely open for the planner: (a) which mascot file the mode machine lands in (Open Q1 — the contradiction); (b) path (a) author ≥6 sprite sheets vs path (b) treatment-vector over existing rig (UI-SPEC chose b for the sprite rig; the Three.js rig already has 21 GLB-backed states so this is moot if Q1 resolves to Three.js); (c) the exact numeric live-path TTFT budget (Open Q2).

### Deferred Ideas (OUT OF SCOPE)
- The real TTFT/60fps/no-dropout-under-a-real-set + "does the mascot feel alive across modes" drive on Kaan's Mac — Kaan-action felt sign-off.
- Full 3D Three.js/GLB mascot rig build (Meshy/Hunyuan3D + Mixamo) — v2.x.
- Richer per-mode art/animation polish — Phase 57 (Sexify Finish).

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| **PERF-01** | TTFT (trigger → first audio out) measured on real hardware, meets live-path budget | `TTFTMeter` (verified, src/vibemix/runtime/ttft.py) is **read-only telemetry now** (ack-bank retired — see Pitfall 1). `thinking_gate.validate_live_config` (verified) is the boot-time gate enforcing MINIMAL thinking. Existing tests: `tests/runtime/test_ttft.py`, `tests/llm/test_thinking_gate.py`, `tests/e2e/test_phase_41_latency_stack_integration.py`. Budget number is **undefined in code** — Open Q2. |
| **PERF-02** | No audio glitches/dropouts under real-session load | `runtime/soak.py` (verified): `is_underrun()` + `SoakCounters.observe_pull()` + `assert_healthy()`. Existing tests: `tests/runtime/test_soak_stability.py`, `tests/recording/test_60min_soak.py`. Assert zero underruns under both-mode traffic. |
| **PERF-03** | Mascot + UI hold 60fps on integrated-GPU MacBook | Three.js rig has `perf-observer.ts` (verified) — rAF p99 frame-time window, drops blur ladder when p99 > 20ms (~<50fps). `tests/integration/test_mascot_dispatch_latency.py` pins sidecar→client p95 < 50ms (half the 100ms MASCOT-08 budget). Webview-side is vitest pure-fn (<1ms). |
| **LIVE-05** | Mascot responds correctly to live audio/MIDI off rich bus signals, not just loudness | Bus frame shape verified (`ws_bus.py:262-288`): emits all rich fields. Three.js rig **already** consumes them (`stateForPhase`, mood/emotion/reaction layers). Root `mascot.html` consumes **only** `music`+`voice` (lines 223-224). Gap = which file + finishing the mapping. |
| **LIVE-05a** | Mascot has many distinct modes (≥6), each grounded in a real bus signal (anti-slop) | Three.js rig has a `MascotState` union with many idle/dance/talk states + `STATE_CLASS` + `STATE_PRIORITY` + `dispatchEvent` anti-slop drop-on-unknown. Root sprite rig has 3 loudness tiers only. UI-SPEC §6-modes table is the contract — but it omits two real `phase` values (`"low"`, `"peak"` — see Pitfall 4). |

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| TTFT measurement (PERF-01) | API/Backend (Python asyncio, `runtime/ttft.py`) | — | TTFT is event_fired→first_chunk on the Gemini stream; lives where the LLM node runs. Single-threaded asyncio invariant. |
| Thinking-budget enforcement (PERF-01 lever) | API/Backend (`llm/thinking_gate.py`) | — | Boot-time config validation of `GenerateContentConfig`; raises before the agent runs. |
| Playback underrun counting (PERF-02) | API/Backend (`runtime/soak.py`) | Audio I/O thread (`PlaybackQueue.pull`) | Underrun is observed at the `PlaybackQueue.pull()` boundary; soak observes, never modifies the hot path. |
| Bus frame broadcast (LIVE-05 source) | API/Backend (`runtime/ws_bus.py` @30Hz) | — | The "dumb wire" — carries all rich fields as-is; anti-hallucination is the *source's* job, the wire never fabricates. |
| Mascot mode state machine (LIVE-05/05a) | **Browser/Webview** (Tauri webview JS/TS) | — | Pure personality surface, reads the bus, must add ZERO audio-path latency. The shipped rig is `tauri/ui/src/mascot/` (Three.js). |
| 60fps render budget (PERF-03) | **Browser/Webview** (rAF loop + GPU compositor) | — | Frame budget is owned by the webview; mode-select logic is float-compares (<0.5ms/frame), the render/blit dominates. |
| Felt perf + "feels alive" sign-off | **Human (Kaan-action)** | — | Deferred — real MacBook, real set, his eyes/ears. Engineering ships budgets + synthetic assertions + recipe. |

---

## Rig Reality (the decisive on-disk findings)

> **This section is the heart of the research.** Read before anything else. All verified this session by reading source.

### Two mascot files exist; the Tauri app loads ONLY the Three.js one

| File | Lines | Rig | Bus fields consumed today | Served by shipped app? |
|------|-------|-----|---------------------------|------------------------|
| `mascot.html` (repo root) | 253 | 2D sprite-sheet `<canvas>` + 2 CSS auras, one rAF loop | **`music` + `voice` only** (lines 223-224) → 3 loudness tiers (`tierForMusic`) | **NO** — see proof below |
| `tauri/ui/mascot.html` → built to `tauri/ui/dist/mascot.html` | 87 (HTML) + ~120KB of `src/mascot/*.ts` | **Three.js WebGL** rig: 4-layer dispatcher, pure-fn state machine, 21 GLB clips, perf-observer | `music`/`voice`/`phase`/`mood`/`bpm`/`bpm_confidence`/`downbeat_phase`/`beat_phase`/`emotion`/`reaction_intent` (full rich set) | **YES** |

**Proof the shipped app loads the Three.js rig, not root `mascot.html` [VERIFIED: source read this session]:**
1. `tauri/src-tauri/src/mascot_window.rs:104` → `WebviewUrl::App("mascot.html".into())`.
2. `tauri/src-tauri/tauri.conf.json5:16` → `"frontendDist": "../ui/dist"`. `WebviewUrl::App(path)` resolves `path` *relative to frontendDist*, i.e. `tauri/ui/dist/mascot.html`.
3. `tauri/ui/vite.config.ts:93` → `rollupOptions.input.mascot = resolve(projectRoot, "mascot.html")` where `projectRoot` is `tauri/ui/` — so vite builds **`tauri/ui/mascot.html`** (the Three.js page) into `dist/mascot.html`. Confirmed the artifact exists: `tauri/ui/dist/mascot.html` (4.4KB, built 2026-05-21 02:31).

The root `mascot.html` is reachable only via `open file://$(pwd)/mascot.html` (the legacy dev overlay) and the `ws_bus` "send {action: trigger}" hint. It is **not** in any Tauri build path.

### The 56-UI-SPEC §0 reached the OPPOSITE conclusion to the on-disk reality

The UI-SPEC §0 acknowledges both files but **decides to target the root sprite rig**, citing "it is the file 56-CONTEXT names, the one ws_bus feeds, scoped as 'make the EXISTING rig react'." That rationale has a hole: the Three.js rig **also** subscribes to the same `ws:8765` bus (`ws-client.ts` header comment: "mood + bpm_confidence + downbeat_phase + bpm fields"), and it is the EXISTING rig users actually see. **The planner must resolve this contradiction explicitly (Open Q1) — it is not a detail, it determines whether the headline deliverable is visible.**

### What the Three.js rig ALREADY does (so the plan doesn't rebuild it) [VERIFIED]

- **`phase → mode` mapping:** `event-dispatcher.ts::stateForPhase()` maps `drop`/`groove`/`build`/`silent`/`breakdown` → mascot states. (Header table lines 9-15.)
- **≥6 distinct states already:** `types.ts` `MascotState` union has many idle/dance/talk/sleep states (`idle_breathe`, `idle_breathe_slow`, `idle_bop_to_beat_mellow`, `idle_bop_to_beat_energetic`, `dance_hard`, talk states, `sleep`, …) with `STATE_CLASS` + `STATE_PRIORITY`.
- **Anti-slop drop-on-unknown:** `dispatchEvent` returns `null` on unknown/malformed subtype (header line 29: "Unknown subtype or malformed message → return null (silent — anti-slop)").
- **Hysteresis-equivalent:** `STATE_PRIORITY` + the talk-blocks-dance rule + `tickIdleTimeout` + downbeat-scheduled switches (`planTransition` → `schedule_for_downbeat`) function as the anti-flicker layer.
- **Mood / emotion / reaction:** `mood.ts`, `layers/emotion.ts`, `layers/reaction.ts`, `MASCOT_REACTIONS` whitelist (`wave`/`point_left`/`point_right`/`fist_pump`/`nod`).
- **Client-side fps pinning:** `perf-observer.ts` — 60-frame rolling p99 window, drops a "blur ladder" when p99 > 20ms.
- **Full vitest coverage:** 20+ `.test.ts` files including the `state-machine-fixtures.test.ts` synthetic-trace replay harness (the exact "feed synthetic frames → assert mode" pattern 56-CONTEXT §specifics asks for) and `__tests__/event-coverage-matrix.test.ts` (4-layer × 15-event matrix, in `mascot-audit` CI).

### Gaps the Three.js rig still has vs the LIVE-05a contract (the real plan surface)

1. **`drop` is NOT defence-in-depth.** `stateForPhase("drop")` fires on `phase=="drop"` alone. The UI-SPEC contract requires `phase=="drop"` **AND** `music ≥ PEAK_RMS (0.110)` — a `phase=drop` with quiet music is a misclassification that must NOT trigger the peak animation. **This guard is missing** and is the single most important anti-slop addition.
2. **Two real `phase` values are unmapped: `"low"` and `"peak"`** (see Pitfall 4). `stateForPhase` handles only `silent/groove/build/drop/breakdown`. An unmapped value currently → no transition (acceptable anti-slop default), but the contract should map `"low"` → idle/breakdown-ish and `"peak"` → vibing/drop deliberately, not by accident.
3. **`speaking` priority + exit hold.** The talk-blocks layer exists; verify it implements the UI-SPEC's "immediate enter, 600ms exit hold" and that `voice>0.05` enter / `voice<0.03` exit thresholds match.
4. **`detected_genre`/`genre_confidence`** (Phase 52, NEW) are on the wire but the rig's `SnapshotSlice` doesn't include them yet — optional aura/tint micro-shift per UI-SPEC (gated `genre_confidence ≥ 0.6`).

### The root `mascot.html` cleanup (separate, smaller, in-scope-if-still-used)

If the dev `file://` overlay is kept as a live-drive surface, it needs: cyberpunk palette → CDJ Whisper amber retire (`--cyan/--magenta/--purple` lines 8-11, the aura gradients lines 50-67, the drop-shadows lines 76-78), `-apple-system/monospace` → Saira + JetBrains Mono. But note: **the sprite PNGs it references (`sprite-1/2/3.png`) do not exist anywhere on disk** [VERIFIED: `find` returned nothing], so the root rig renders nothing today regardless. This is a strong additional signal that the root rig is dead/dev-only.

---

## Standard Stack

> No new packages are needed. This phase extends in-tree code with the stack already locked by the project (Python 3.12, Gemini-only, uv; vite/vitest/Three.js for the webview). **No `## Package Legitimacy Audit` section is required — zero external packages are installed by this phase.**

### Core (already in the tree — verify versions, do not add)
| Library | Where | Purpose | Why Standard |
|---------|-------|---------|--------------|
| `pytest` 9.x | `tests/` | All Python perf assertions | The authoritative dev workflow per CONTRIBUTING.md |
| `psutil` | `runtime/soak.py` | RSS sampling for soak | Already a dep — soak.py header: "already a dep, no new dependency" |
| `vitest` ^2.1 | `tauri/ui/` | Webview pure-fn state-machine tests | `tauri/ui/package.json:10` `"test": "vitest run --reporter=dot"` — the existing mascot test runner |
| `three` | `tauri/ui/src/mascot/` | The shipped mascot rig | The rig the Tauri app actually loads (DRACO-compressed GLBs) |
| `google-genai` 2.x | `llm/` | `ThinkingLevel`, `ServiceTier`, `GenerateContentConfig` | The thinking_gate validates these SDK types directly |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Extend root `mascot.html` inline JS | Factor mode logic into a vitest-testable module | Inline JS in HTML is **untestable** — the `mascot-tauri-only-grep` CI gate forbids referencing `mascot.html` from `tests/`. Any mode-machine logic in root HTML cannot be unit-tested without violating that gate (see Pitfall 2). The Three.js rig already solved this by putting logic in `src/mascot/*.ts` with vitest. |
| New TTFT gate | Keep TTFTMeter as telemetry + pin thinking_gate | Ack-bank (the thing that gated on TTFT) was retired; re-introducing a TTFT *gate* re-litigates a settled decision. Pin the budget as an *assertion over telemetry*, not a runtime gate. |

---

## Architecture Patterns

### System Architecture Diagram (the mascot reaction path — verify the mascot adds ZERO audio latency)

```
  BlackHole / WASAPI master audio
            │
            ▼
  ┌──────────────────────┐      MIDI (DDJ-FLX4)
  │ AudioBuffer / Levels │◀───────────────────────┐
  │  RMS, FFT, BPM       │                         │
  └──────────┬───────────┘                  ControllerState
             ▼                                     │
  ┌──────────────────────┐                         │
  │ MusicState (10Hz)    │◀────────────────────────┘
  │  phase, bpm, mood,   │
  │  emotion, genre, …   │
  └──────┬───────────────┴──────────────┐
         │                              │
         ▼ (reaction path)             ▼ (telemetry path — NO audio latency)
  ┌─────────────────┐          ┌───────────────────────────────┐
  │ EventDetector   │          │ ws_bus.ws_broadcast @30Hz     │
  │ → Gemini LLM    │          │  flat mascot frame (rich)     │
  │ (thinking=MIN!) │          └──────────────┬────────────────┘
  │ TTFTMeter ◀─────┤ event_fired→first_chunk │ ws://127.0.0.1:8765
  └────────┬────────┘                         ▼
           ▼ TTS                    ┌─────────────────────────────┐
  ┌─────────────────┐              │ Tauri webview (Three.js rig) │
  │ PlaybackQueue   │              │  ws-client → dispatchEvent   │
  │  soak.observe_  │              │  → planTransition →          │
  │  pull (underrun)│              │  renderer.crossFadeTo        │
  └────────┬────────┘              │  perf-observer (fps p99)     │
           ▼                       └─────────────────────────────┘
      headphones                   (reads bus only — never writes audio)
```

The mascot is a **leaf consumer of the bus**. It is structurally incapable of adding reaction-path latency — it reads frames, it never feeds back into the audio/LLM path. This is the `project_mascot_as_vtuber_personality_surface` invariant and it is already satisfied by the wire architecture.

### Pattern 1: Pure-function state machine (mirror the Three.js rig, do NOT invent a new shape)
**What:** `planTransition(machine, request, now) → TransitionPlan`; `applyTransition(machine, plan, now) → MachineState`. No wall-clock reads inside (every fn takes `now`), immutable returns. This is what makes it vitest-testable in <50ms with deterministic synthetic traces.
**When to use:** All mascot mode logic. It is the established, CI-gated pattern.
```typescript
// Source: tauri/ui/src/mascot/state-machine.ts (verified this session)
//   caller → planTransition() → TransitionPlan
//          → applyTransition() → new MachineState
//          → if plan.action === "switch_now": renderer.crossFadeTo(target, blendMs)
//          → if plan.action === "schedule_for_downbeat": rAF loop watches pendingSwitch
```

### Pattern 2: Synthetic-frame fixture replay (the exact test 56-CONTEXT §specifics asks for, already exists)
**What:** `__fixtures__/event-traces.json` replayed through `dispatchEvent + planTransition + applyTransition`, asserting transitions match documented expectations within ±100ms tolerance. Pure — no Three.js, no DOM.
```typescript
// Source: tauri/ui/src/mascot/state-machine-fixtures.test.ts (verified)
// Same fixture is replayed Python-side by
// tests/integration/test_mascot_event_taxonomy_e2e.py — pins the contract
// across the JS/Py boundary. ADD the silent→build→drop→breakdown→voice>0
// trace + the anti-slop contradiction case (phase=drop + music<PEAK_RMS → NO flip) here.
```

### Pattern 3: Defence-in-depth `phase`-led, `music`-confirmed mode entry (the gap to close)
**What:** trust `phase` but block the flip when the level disagrees. Mirrors the Python source-of-truth constants so mascot boundaries agree with `state.phase`.
```typescript
// thresholds VERIFIED in src/vibemix/audio/constants.py:
//   SILENT_RMS = 0.012, LOW_RMS = 0.040, PEAK_RMS = 0.110
// drop entry must require BOTH: phase === "drop" && music >= 0.110
// breakdown entry must require: phase === "breakdown" && music < 0.040
// a contradicting frame → treat as "no signal", hold current mode (anti-slop)
```

### Anti-Patterns to Avoid
- **Mode logic in root `mascot.html` inline `<script>`:** untestable + collides with the `mascot-tauri-only-grep` CI gate (you cannot grep/import it from `tests/`). If root rig must change, keep changes to CSS/palette only.
- **A second rAF loop or `setInterval` for mode evaluation:** the existing rig has exactly one rAF chain; mode eval must happen inside it (`tick`).
- **Re-introducing a TTFT runtime gate:** ack-bank was retired deliberately; pin TTFT as a telemetry assertion, not a `should_fire` gate.
- **Animating `width`/`height`/`top`/`left` per frame:** breaks the 60fps budget; drive everything through `transform`/`opacity`/`filter` (already the rule).
- **Inventing a new underrun/RSS counter:** reuse `soak.SoakCounters` / `is_underrun` — the CONTEXT explicitly forbids a new one.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| TTFT measurement | A new timer wrapper | `runtime.ttft.TTFTMeter` (window=8, default 1500ms sentinel) | Already wired at `__main__.py:642,778,921`; pending-overwrite + no-pending-noop semantics already correct |
| Thinking-budget enforcement | A custom config check | `llm.thinking_gate.validate_live_config` | Already raises `LiveCoachConfigError` on non-MINIMAL thinking / FLEX tier at boot; aggregates all violations |
| Playback dropout detection | A new queue probe | `runtime.soak.is_underrun` + `SoakCounters.observe_pull` + `assert_healthy` | PlaybackQueue zero-pads, so naive byte-length checks miss underruns; soak's all-zero-full-length classifier is the correct one (verified) |
| RSS growth assertion | Absolute-RSS check | `soak.SoakResult.growth_bytes` (delta, not absolute) | macOS shared pages + PyInstaller make absolute RSS noisy — assert on growth |
| Mascot state machine | A parallel inline-JS FSM | `tauri/ui/src/mascot/state-machine.ts` (planTransition/applyTransition) | Pure, immutable, vitest-tested, CI-gated, already does phase→mode + priority + downbeat scheduling |
| Synthetic-frame mode test | A bespoke harness | `state-machine-fixtures.test.ts` + `__fixtures__/event-traces.json` | The exact replay pattern already exists; add traces, don't rebuild |
| Client-side fps pinning | A new frame counter | `tauri/ui/src/mascot/perf-observer.ts` | 60-frame p99 window + ladder already implemented and tested |

**Key insight:** This phase's failure mode is *re-implementation* — building a second mode machine in the wrong (invisible, untestable) file when a mature, tested, user-visible one already exists. The value is in **closing 3-4 specific gaps in the real rig + pinning 3 perf budgets with existing test infra**, not in net-new code.

---

## Runtime State Inventory

> This is a code/config phase (perf assertions + webview state machine). No data migration, no stored-state renames. Included for completeness because it touches the wire frame and CI gates.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — verified: phase touches no DB/datastore. The wire frame is ephemeral 30Hz, not persisted. | None |
| Live service config | The `mascot-audit` CI workflow (`.github/workflows/mascot-audit.yml`) gates on `tauri/ui/src/mascot/**`. New `.ts` mode logic there triggers the vitest event-coverage-matrix + tauri-only-grep gates — must keep green. | Keep CI green; add fixtures, don't break the matrix |
| OS-registered state | None — verified: no Task Scheduler / launchd / pm2 registration in this phase. | None |
| Secrets/env vars | None new. `GEMINI_API_KEY` unchanged. | None |
| Build artifacts | `tauri/ui/dist/mascot.html` is a vite build artifact — if mode logic lands in `tauri/ui/src/mascot/`, a rebuild (`npm run build` in `tauri/ui/`) is required for it to reach the shipped app. **This is exactly why root `mascot.html` edits never reach users — there is no build step that includes it.** | Rebuild dist after webview changes |

---

## Common Pitfalls

### Pitfall 1: Treating TTFTMeter as a live `should_fire` gate (it is now telemetry only)
**What goes wrong:** PERF-01 plan asserts "TTFTMeter gates reactions" and writes a test that the gate blocks slow reactions.
**Why it happens:** 56-CONTEXT and 56-UI-SPEC both say "gates should_fire" — that is **stale**. The ttft.py docstring (verified) states: "Originally fed the ack-bank `should_fire(...)` LATENCY-04 gate; ack-bank has since been retired ... so the meter is now read-only telemetry."
**How to avoid:** Assert TTFT as a **telemetry budget** (rolling_avg_ms ≤ budget over replayed real traffic) and pin the actual *gate* — `thinking_gate.validate_live_config` — which is what really protects TTFT (rejects non-MINIMAL thinking that adds 7s+).
**Warning signs:** A test that calls a `should_fire` method on TTFTMeter (it has none).

### Pitfall 2: Putting mode logic in root `mascot.html` inline `<script>` (untestable + CI-forbidden)
**What goes wrong:** The state machine ships in 253-line inline HTML JS; no unit test can cover it.
**Why it happens:** Following the UI-SPEC's "target root mascot.html" literally.
**How to avoid:** The `mascot-tauri-only-grep` CI gate **forbids** referencing `mascot.html` from `tests/`, `e2e/`, `scripts/ci/` (allowlist excepts only POC-immutability gates). You physically cannot write a vitest/pytest test that imports root mascot.html logic without tripping CI. The Three.js rig avoids this by living in `src/mascot/*.ts`. (See Open Q1 — this is a strong argument for resolving Q1 toward the Three.js rig.)
**Warning signs:** A planned task that adds a test grepping or importing `mascot.html`.

### Pitfall 3: Shipping mode logic to a file the app doesn't load
**What goes wrong:** All LIVE-05/05a work lands in root `mascot.html`; the live app (loading `tauri/ui/dist/mascot.html`) shows the unchanged Three.js rig — Kaan's headline ask is invisible on the real surface.
**Why it happens:** The UI-SPEC §0 conclusion contradicts the on-disk Tauri load path (both verified above).
**How to avoid:** Resolve Open Q1 before planning. If the answer is "root rig is the dev-overlay only", the plan must state how the mode machine reaches the user-visible Three.js surface (or scope it as a follow-up *with rationale*, which the prompt explicitly permits).
**Warning signs:** No task touches `tauri/ui/src/mascot/` yet LIVE-05a is claimed done.

### Pitfall 4: Unmapped `phase` values (`"low"`, `"peak"`) causing accidental anti-slop violations or dead modes
**What goes wrong:** The UI-SPEC §Mode table and `stateForPhase` both enumerate only `silent/groove/build/drop/breakdown`. But `state/phase.py` (verified) also returns **`"low"`** (line 46) and **`"peak"`** (line 62).
**Why it happens:** The v4 classifier has 7 phase outputs, not 5; the contracts were written against 5.
**How to avoid:** Map `"low"` → idle/breakdown-family and `"peak"` → vibing/drop-family deliberately. An unmapped value must fall through to "hold current mode" (anti-slop), never to a default decorative flip.
**Warning signs:** A live set where the mascot freezes during a `"low"` or `"peak"` section, or flips to a default state on them.

### Pitfall 5: `mood` vs `emotion` confusion
**What goes wrong:** Plan wires `mood` from `emotion_router` and gets `neutral/focused/hyped/concerned` (those are `emotion`).
**Why it happens:** Both are mascot-tinting fields and the names are close.
**How to avoid:** Verified: `mood` ∈ `{"hype-man","teacher","coach"}` (`state/music_state.py:63`) — drives variant family. `emotion` ∈ `{"neutral","focused","hyped","concerned",null}` (`emotion_router.py:33`) — finer eye/brow nudge. They are different fields on the same frame.
**Warning signs:** A `mood` switch case with `"hyped"` in it.

### Pitfall 6: `phase=="drop"` firing the peak animation on quiet misclassification
**What goes wrong:** A spurious `phase=drop` during a quiet section pumps the mascot — pure AI-slop.
**Why it happens:** `stateForPhase("drop")` (verified) fires on phase alone; the `&& music >= PEAK_RMS` guard is missing.
**How to avoid:** Add the defence-in-depth guard (Pattern 3). This is THE highest-value anti-slop addition in the phase.

---

## Code Examples

### Pinning the thinking-budget gate (PERF-01 lever) — already tested, EXTEND
```python
# Source: src/vibemix/llm/thinking_gate.py (verified this session)
# validate_live_config(cfg) raises LiveCoachConfigError when:
#   thinking_level != MINIMAL   ("anything higher adds 7s+ TTFT regression")
#   service_tier == FLEX        ("Flex SLA 1-15 min P99 60 min = live UX collapse")
# Existing test: tests/llm/test_thinking_gate.py
# PERF-01 task: assert the LIVE coach's actual GenerateContentConfig passes
#   validate_live_config (positive pin) AND that a MEDIUM/HIGH config is rejected
#   (negative pin) — proves the regression-protection is live.
```

### Soak underrun assertion (PERF-02) — already implemented, EXTEND under both-mode load
```python
# Source: src/vibemix/runtime/soak.py (verified)
# is_underrun(chunk, requested, had_pending, held): all-zero full-length pull
#   == queue was empty == underrun (PlaybackQueue zero-pads, so length is useless).
# SoakCounters.observe_pull(...) increments underruns; assert_healthy() asserts
#   bounded RSS GROWTH (not absolute) + zero underruns.
# Existing tests: tests/runtime/test_soak_stability.py, tests/recording/test_60min_soak.py
# PERF-02 task: drive PlaybackQueue under simulated both-mode reaction traffic,
#   assert SoakResult.underruns == 0.
```

### Mascot synthetic-frame mode test (LIVE-05a) — extend the existing vitest harness
```typescript
// Source pattern: tauri/ui/src/mascot/state-machine-fixtures.test.ts (verified)
// Add a trace to __fixtures__/event-traces.json:
//   silent → build → drop(music>=0.110) → breakdown(music<0.040) → voice>0.05
//   assert: each enters the right mode; hysteresis blocks single-frame flicker.
// Add the ANTI-SLOP assertion:
//   frame { phase:"drop", music: 0.05 }  →  mode does NOT change (held)
//   (this is the LIVE-05a anti-slop acceptance — contradictory frame = no flip)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Ack-bank pre-recorded fillers gated on TTFT | Ack-bank retired; TTFTMeter is read-only telemetry | Pre-Phase-56 (ttft.py docstring) | PERF-01 pins telemetry + thinking_gate, NOT a should_fire gate |
| Root `mascot.html` 2D sprite, music/voice → 3 tiers | Three.js WebGL rig (`tauri/ui/src/mascot/`), 4-layer, 21 GLBs, rich-bus-driven | Phase 13/22/31/47 | The user-visible mascot is already rich; root rig is dev-only with missing PNGs |
| `phase` ∈ 5 values | `phase` ∈ 7 values (`silent/low/groove/build/drop/breakdown/peak`) | v4 classifier | Contracts written for 5 must handle `low`/`peak` |

**Deprecated/outdated:**
- The claim "TTFTMeter gates should_fire" (in 56-CONTEXT and 56-UI-SPEC) — ack-bank retired; it's telemetry.
- Root `mascot.html` as the shipped surface — it is not in the Tauri build path and its sprite PNGs don't exist on disk.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The live-path TTFT *budget number* is not defined in code; PERF-01 needs Kaan/orchestrator to set it (Open Q2). I did not find a numeric budget constant. | PERF-01 / Open Q2 | Plan asserts against an invented threshold; could be too strict (false fail) or too loose (no protection) |
| A2 | The dev `file://` root-mascot overlay may still be used as a live-drive surface (so its palette cleanup is in-scope). If Kaan never uses it, that cleanup is wasted scope. | Rig Reality / root cleanup | Minor — a small CSS task done unnecessarily |
| A3 | UI-SPEC's `mood` tint table (`hype-man`/`teacher`/`coach`) maps cleanly onto the Three.js rig's existing `mood.ts` — I verified `mood` values match but did not deep-read `mood.ts`'s variant mapping. | Mode/mood | Low — values confirmed; mapping detail is implementation, not contract |
| A4 | The Three.js rig's existing talk-block layer already implements `speaking` priority correctly; I read its existence (`layers/reaction.ts`, talk-blocks-dance rule) but not the exact voice thresholds. | Gaps #3 | Low-medium — may need a small threshold alignment task |

**If A1 is unresolved at plan time:** the planner should add a `checkpoint:human-verify` for the TTFT budget number before writing the assertion, OR assert "rolling_avg_ms ≤ default sentinel (1500ms)" as a conservative floor and flag it for Kaan to tighten on real hardware.

---

## Open Questions

1. **[HIGHEST VALUE] Which mascot file does the LIVE-05/05a mode machine land in?**
   - What we know: The shipped Tauri app loads `tauri/ui/dist/mascot.html` (Three.js rig), built from `tauri/ui/src/mascot/*.ts` [VERIFIED 3 ways]. The Three.js rig already does ~80% of LIVE-05/05a and is vitest-tested + CI-gated. The root `mascot.html` (which 56-CONTEXT + 56-UI-SPEC name) is dev-only, has missing sprite PNGs, and its inline JS is untestable + CI-grep-forbidden.
   - What's unclear: 56-UI-SPEC §0 deliberately chose the root sprite rig. That decision contradicts the on-disk load path. Was the UI-SPEC author aware the Tauri app doesn't serve root `mascot.html`?
   - Recommendation: **Resolve toward the Three.js rig** (`tauri/ui/src/mascot/`) — close the 4 specific gaps (drop defence-in-depth, `low`/`peak` mapping, speaking exit-hold, optional genre tint) + add the anti-slop synthetic-frame fixtures. This is where the user-visible surface, the test harness, and the CI gates already are. If the orchestrator insists on the root rig per UI-SPEC, the plan MUST add an explicit task/rationale for how the root-rig mode machine reaches the shipped Tauri surface (it currently cannot without a build-path change). **Flag this to discuss-phase before planning.**

2. **What is the numeric live-path TTFT budget for PERF-01?**
   - What we know: thinking_gate enforces MINIMAL (the lever); TTFTMeter default sentinel is 1500ms; ack-bank's old gate was ~800ms.
   - What's unclear: no `LIVE_TTFT_BUDGET_MS` constant exists in code (searched).
   - Recommendation: Set the budget explicitly (Kaan-action or orchestrator). Conservative interim: assert ≤ 1500ms (sentinel) and pin thinking=MINIMAL; tighten on real-hardware drive (which is already Kaan-action).

3. **Is the root `mascot.html` dev overlay still in active use?**
   - What we know: sprite PNGs absent → it renders nothing; not in Tauri build path.
   - Recommendation: If unused, skip its palette cleanup entirely (descope A2). If used, the cleanup is a small isolated CSS task. Confirm with Kaan.

---

## Environment Availability

> The perf budgets and "feels alive" sign-off require Kaan's real MacBook + a real DJ set — that confirmation is explicitly **Kaan-action / deferred**. Engineering ships synthetic/automated assertions that run in CI without the hardware.

| Dependency | Required By | Available (CI/dev) | Version | Fallback |
|------------|------------|--------------------|---------|----------|
| Python 3.12 + pytest | PERF-01/02 assertions | ✓ | 3.12.x, pytest 9.x | — |
| `psutil` | soak RSS sampling | ✓ (already a dep) | in uv.lock | — |
| Node + vitest | LIVE-05a webview tests | ✓ | vitest ^2.1 | — |
| Three.js + DRACO | shipped mascot rig | ✓ (in tauri/ui) | in package.json | — |
| Real MacBook (integrated GPU) | felt 60fps + dropout + TTFT under a real set | ✗ (Kaan-action) | — | Synthetic assertions (perf-observer p99, soak underrun, TTFTMeter replay) stand in for CI; felt sign-off rides the live-drive surface |
| BlackHole 2ch + DJ app + DDJ-FLX4 | live-drive recipe | ✗ in CI (✓ on Kaan's Mac) | — | Synthetic ws-frame replay covers the automated path |

**Missing dependencies with fallback:** the entire "real hardware under a real set" requirement is Kaan-action by design; synthetic/automated assertions are the engineering deliverable and run without it.
**Missing dependencies with no fallback:** none that block engineering work.

---

## Validation Architecture

> `workflow.nyquist_validation: true` (config verified). This section is required.

### Test Framework
| Property | Value |
|----------|-------|
| Framework (Python) | pytest 9.x |
| Framework (webview) | vitest ^2.1 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]`; `tauri/ui/vite.config.ts` + `package.json` for vitest |
| Quick run command (Python) | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q` (or `uv run pytest -q`) |
| Quick run command (webview) | `cd tauri/ui && npm test` (`vitest run --reporter=dot`) |
| Full suite | Python `-q` (default skips `macos_audio`/`integration`/`slow`/`e2e`/`network` markers) + `npm test` in `tauri/ui` + `mascot-audit` CI workflow |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PERF-01 | TTFT rolling avg ≤ budget on replayed traffic | unit | `pytest tests/runtime/test_ttft.py -x` | ✅ extend (add budget-assertion + real-traffic replay) |
| PERF-01 | thinking=MINIMAL enforced; non-MINIMAL rejected | unit | `pytest tests/llm/test_thinking_gate.py -x` | ✅ extend (positive+negative pin on the LIVE config) |
| PERF-01 | TTFT integration across the latency stack | e2e | `pytest tests/e2e/test_phase_41_latency_stack_integration.py -m e2e -x` | ✅ extend |
| PERF-02 | zero playback underruns under both-mode load | integration | `pytest tests/runtime/test_soak_stability.py -x` | ✅ extend (drive under simulated reaction traffic) |
| PERF-02 | bounded RSS growth over soak window | slow | `pytest tests/recording/test_60min_soak.py -m slow -x` | ✅ exists |
| PERF-03 | sidecar→client dispatch p95 < 50ms | integration | `pytest tests/integration/test_mascot_dispatch_latency.py -m integration -x` | ✅ extend (add mode-transition synthetic frame) |
| PERF-03 | webview rAF p99 frame-time pin | unit (vitest) | `cd tauri/ui && npm test -- perf-observer` | ✅ exists (`perf-observer.test.ts`) |
| LIVE-05 | mascot maps phase/mood/emotion/bpm → modes | unit (vitest) | `cd tauri/ui && npm test -- state-machine` | ✅ extend (add drop-confirm + low/peak mapping) |
| LIVE-05a | ≥6 modes, each gated to a real bus event | unit (vitest) | `cd tauri/ui && npm test -- state-machine-fixtures` | ✅ extend (add silent→build→drop→breakdown→voice trace) |
| LIVE-05a | **anti-slop**: contradictory frame (phase=drop + music<PEAK_RMS) → NO flip | unit (vitest) | same | ❌ Wave 0 (the new acceptance assertion — does not exist yet) |
| LIVE-05a | cross-boundary contract pinned Py-side | integration | `pytest tests/integration/test_mascot_event_taxonomy_e2e.py -m integration -x` | ✅ extend if fixtures change |

### Sampling Rate
- **Per task commit:** the single touched test file (`pytest <file> -x` or `npm test -- <pattern>`).
- **Per wave merge:** `pytest -q` (Python fast set) + `cd tauri/ui && npm test`.
- **Phase gate:** full Python suite (incl. `-m integration` for the perf tests) + `npm test` + `mascot-audit` CI green, before `/gsd:verify-work`.

### Wave 0 Gaps
- [ ] New vitest assertion: contradictory-frame anti-slop case (phase=drop + music<PEAK_RMS → no mode flip) — the LIVE-05a acceptance test. Add to `state-machine-fixtures.test.ts` + `__fixtures__/event-traces.json`.
- [ ] New vitest mapping for `phase=="low"` and `phase=="peak"` in `stateForPhase` (+ tests) — currently unmapped.
- [ ] `drop` defence-in-depth guard (`&& music >= PEAK_RMS`) + its test.
- [ ] PERF-01 budget assertion: requires the budget number (Open Q2) — gate behind a `checkpoint:human-verify` if unresolved, or use the 1500ms sentinel floor.
- [ ] No framework install needed — pytest + vitest both present.

---

## Security Domain

> `security_enforcement` is not set to `false` in config (absent = enabled). This phase is local-only (no network exposure, no auth, no user input parsing beyond the localhost ws bus), so the surface is minimal.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth surface — local single-machine app |
| V3 Session Management | no | No sessions |
| V4 Access Control | no | No multi-user surface |
| V5 Input Validation | yes (minor) | The mascot parses ws frames from `127.0.0.1:8765`. The Three.js rig already does anti-slop "unknown subtype → null" (`dispatchEvent`) — a `JSON.parse` in a `try/catch` (root rig line 221-225) + drop-on-unknown is the correct posture. New mode-select must keep the "malformed/unknown field → no-op" discipline (this doubles as the anti-slop guarantee). |
| V6 Cryptography | no | No secrets handled in this phase; `GEMINI_API_KEY` is read elsewhere |

### Known Threat Patterns for this stack
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malformed/hostile ws frame crashing the webview | Denial of Service | `try/catch` around `JSON.parse` + drop-on-unknown (already present); never throw on a bad field |
| ws bus bound beyond localhost | Information Disclosure | Bus is `127.0.0.1` only (verified `ws://127.0.0.1:8765`) — keep it loopback, never `0.0.0.0` |
| API key in bus frames | Information Disclosure | The mascot frame carries no secrets (verified shape) — keep it that way; do not add config/secrets to the wire |

---

## Sources

### Primary (HIGH confidence — read directly this session)
- `src/vibemix/runtime/ttft.py` — TTFTMeter (telemetry-only, ack-bank retired), window=8, sentinel=1500ms
- `src/vibemix/runtime/soak.py` — is_underrun, SoakCounters, SoakResult.growth_bytes, assert_healthy
- `src/vibemix/llm/thinking_gate.py` — validate_live_config (MINIMAL thinking + non-FLEX tier gate)
- `src/vibemix/runtime/ws_bus.py:262-300` — the flat mascot frame shape (all rich fields verified)
- `src/vibemix/state/phase.py` — `classify_phase` returns silent/low/groove/build/drop/breakdown/peak (7 values)
- `src/vibemix/state/music_state.py:63` — `mood ∈ {hype-man, teacher, coach}`; `last_reaction_intent`
- `src/vibemix/state/emotion_router.py` — `emotion ∈ {neutral, focused, hyped, concerned}`; RMS_HIGH=0.18, RMS_LOW=0.08
- `src/vibemix/audio/constants.py` — SILENT_RMS=0.012, LOW_RMS=0.040, PEAK_RMS=0.110
- `tauri/src-tauri/src/mascot_window.rs:104` + `tauri.conf.json5:16` + `tauri/ui/vite.config.ts:93` — proof the app loads the Three.js `mascot.html`, not root
- `tauri/ui/src/mascot/{state-machine,event-dispatcher,types,perf-observer}.ts` + their `.test.ts` — the shipped rig's API + test pattern
- `tauri/ui/src/mascot/state-machine-fixtures.test.ts` + `__fixtures__/event-traces.json` — the synthetic-frame replay harness
- `.github/workflows/mascot-audit.yml` — the CI gates (tauri-only-grep, anti-slop, event-coverage-matrix)
- `mascot.html` (root, full read) — 3-tier sprite toy, music/voice only, references missing sprite-1/2/3.png
- `.planning/REQUIREMENTS.md` — PERF-01/02/03, LIVE-05/05a verbatim

### Secondary (MEDIUM)
- 56-CONTEXT.md, 56-UI-SPEC.md — the upstream contracts (note: both contain the stale "TTFTMeter gates should_fire" claim and the root-mascot targeting contradiction surfaced here)

### Tertiary (LOW)
- None — every claim in this document is grounded in a file read this session.

---

## Metadata

**Confidence breakdown:**
- Perf substrate (PERF-01/02/03): HIGH — all three substrates read directly; budget *number* is the only gap (Open Q2)
- Mascot rig reality / which file ships: HIGH — verified 3 independent ways (rust loader + tauri config + vite input)
- Mode state machine gaps: HIGH — read the actual `stateForPhase` + `MascotState` + dispatcher
- Anti-slop test pattern: HIGH — the exact harness exists and was read
- The Q1 contradiction resolution: MEDIUM — the *facts* are HIGH; the *decision* needs human/orchestrator confirmation

**Research date:** 2026-05-21
**Valid until:** 2026-06-20 (stable in-tree code; re-verify only if `tauri/ui/src/mascot/` or the ws_bus frame shape changes before planning)
