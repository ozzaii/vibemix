# Phase 56: Performance + Live Mascot - Context

**Gathered:** 2026-05-21
**Status:** Ready for planning
**Mode:** Orchestrator-grounded — live-source findings injected directly (autonomous `fully`). Depends on Phase 54 + 55 (perf measured against real reaction traffic from both modes) + Phase 53 (mascot reacts to live MIDI).

<domain>
## Phase Boundary

On the real machine under live-session load: peak performance (TTFT within budget, no audio dropouts, mascot + UI hold 60fps) AND the **Neon Rebel mascot reacts correctly to live audio/MIDI across MANY modes**. Covers **PERF-01** (TTFT budget), **PERF-02** (no dropouts), **PERF-03** (60fps), **LIVE-05** (mascot reacts off the rich bus signals), **LIVE-05a** (mascot has many distinct modes — Kaan directive 2026-05-21).

**The mascot many-modes work is the headline of this phase** — it's the "feels alive / present" surface Kaan explicitly expanded. PERF is the floor it runs on.
</domain>

<decisions>
## Implementation Decisions (Claude's discretion, autonomous `fully`)

### ⚠ POST-RESEARCH CORRECTION (autonomous `fully`, 2026-05-21) — build target is the Three.js rig, NOT root `mascot.html`
56-RESEARCH verified **three independent ways** (`mascot_window.rs:104 WebviewUrl::App("mascot.html")` + `tauri.conf.json5:16 frontendDist:"../ui/dist"` + `vite.config.ts:93`) that the **shipped Tauri app loads `tauri/ui/dist/mascot.html` — the Three.js WebGL rig** — and that the root `mascot.html`'s sprite PNGs (`sprite-1/2/3.png`) **do not exist on disk** (it renders nothing). Targeting the root rig would make the headline deliverable invisible to users. **Therefore the LIVE-05/05a build target is the Three.js rig (`tauri/ui/mascot.html` + its TS modules), which already does ~80% of this phase** (consumes the rich bus fields, `stateForPhase` phase→mode map, drop-on-unknown anti-slop, priority/hysteresis, mood/emotion/reaction layers, `perf-observer.ts` fps pin, and a vitest fixture-replay harness). The work is **closing the 4 specific gaps RESEARCH found**, not a new sprite state machine:
1. Map the two currently-unmapped `state/phase.py` values — `"low"` and `"peak"` (phase returns 7: silent/low/groove/build/drop/breakdown/peak; rig covers 5).
2. Add the `drop && music >= PEAK_RMS` defence-in-depth guard (top anti-slop fix).
3. Reach the ≥6 distinct visible modes + speaking/emoting on the Three.js rig per the UI-SPEC's per-mode visual contract (apply the contract to the EXISTING rig — do NOT rebuild it as sprites).
4. Keep the `mascot-audit` CI gate green.
Root `mascot.html` stays a **dev/CI overlay only** — keep it audit-green, do NOT add new modes/art there (descope its palette cleanup unless it proves still-used). The 56-UI-SPEC was authored for the root sprite "path (b)"; treat its **mode taxonomy, anti-slop gating, hysteresis timing, and 60fps budget as the contract**, but the **implementation surface is the Three.js rig**.
**PERF-01 correction:** `TTFTMeter` is **telemetry-only now** (ack-bank retired — the "gates should_fire" note is stale). The real PERF-01 lever is `llm/thinking_gate.py::validate_live_config` (boot-time MINIMAL-thinking gate) — pin that. Assert TTFTMeter rolling-avg ≤ a named budget constant (reuse an existing budget if present in code; else a 1500 ms regression floor). The numeric live-path TTFT target + the felt "instant" confirmation ride the Kaan-action live-drive surface.

### Mascot — many modes, reactive to music (LIVE-05 / LIVE-05a) — Kaan's headline ask
- **Drive the mascot off the rich bus signals it currently ignores.** `mascot.html` today consumes ONLY `d.music` + `d.voice` (lines 223-224) → 3 crude loudness tiers (`tierForMusic`). The bus already broadcasts `phase`, `mood`, `bpm`, `reaction_intent`, and now (Phase 52) `detected_genre` + `genre_confidence`. The work: a **mode state machine** in `mascot.html` that maps these real signals → a distinct visual mode.
- **≥6 distinct modes, each gated to a REAL event** (anti-slop, [[project_anti_slop_grounded_gemini_thesis]]): idle/dead-air (`phase=silent`/low music), vibing/groove (steady music), building (`phase=build`), drop/peak (`phase=drop` + loud), breakdown/chill (low-energy section), speaking/emoting (while `voice>0` / AI talks). Mood (`mood` field) tints which variant (hype-grin vs coach-focused). **No random or purely decorative mode changes** — a mode flip must correspond to a real musical/session event. Add hysteresis so modes don't flicker bar-to-bar (mirror the state-side `HysteresisState` philosophy).
- **Keep the mascot OUT of the audio loop** ([[project_mascot_as_vtuber_personality_surface]]) — it's a pure personality surface reading the bus; it must not add latency to the reaction path.
- **Scope realistically for v4.0:** make the EXISTING mascot rig react across many modes off real signals. The full 3D Three.js/GLB rig is v2.x ([[project_mascot_as_vtuber_personality_surface]] pipeline) — do NOT build it here. If the current rig is 2D sprite tiers, extend the mode mapping on that rig; a richer art pass is Phase 57 (Sexify) / later. Confirm the current rig state before planning.

### Performance (PERF-01/02/03)
- **TTFT (PERF-01):** `runtime/ttft.py::TTFTMeter` already measures event_fired→first_chunk rolling-avg ms and gates `should_fire`. Plan asserts the rolling TTFT stays within the live-path budget on real reaction traffic. **Critical known lever:** `llm/thinking_gate.py` — the Gemini thinking budget MUST stay MINIMAL; anything higher adds 7s+ TTFT regression. Pin that gate.
- **Dropouts (PERF-02):** reuse the Phase-51 soak underrun counter (`runtime/soak.py` observing `PlaybackQueue`) — assert zero playback underruns under real-session load (both modes generating traffic). Don't invent a new counter.
- **60fps (PERF-03):** the mascot's `requestAnimationFrame` loop + UI must hold 60fps on the integrated-GPU MacBook. The new mode state machine must not blow the frame budget (cheap CSS/canvas transitions, no per-frame layout thrash). Extend the existing perf/latency tests (`tests/integration/test_mascot_dispatch_latency.py`, `tests/e2e/test_phase_41_latency_stack_integration.py`, `tests/runtime/test_ttft.py`).
- **The real "TTFT/60fps/no-dropout under a real set" measurement on Kaan's Mac is Kaan-action** — engineering ships the budgets + automated/synthetic perf assertions + the measurement recipe; the felt-perf-under-real-load confirmation rides the live-drive surface.
</decisions>

<code_context>
## Existing Code Insights (verified live this session)

- **Mascot:** `mascot.html` (root, live overlay wired into `runtime.ws_bus` + CI `mascot-audit`; NOT a POC — keep it). Currently reads only `d.music`/`d.voice`; `tierForMusic` → 3 sprite tiers; `fpsForMusic`; `requestAnimationFrame` loop. The bus frame (`runtime/ws_bus.py`) carries `phase`, `mood`, `bpm`, `reaction_intent`, `detected_genre`, `genre_confidence`, levels — all currently unused by the mascot.
- **TTFT:** `runtime/ttft.py::TTFTMeter` (rolling-avg ms, LATENCY-04 gate); wired `__main__.py:642`. `llm/thinking_gate.py` enforces MINIMAL thinking budget (7s+ TTFT regression otherwise).
- **Dropouts:** `runtime/soak.py` (Phase 51) — RSS + PlaybackQueue underrun sampler; the PERF-02 substrate.
- **Mood:** `state/emotion_router.py` produces the `mood` the mascot should consume for variant tinting.
- **Perf tests:** `tests/integration/test_mascot_dispatch_latency.py`, `tests/e2e/test_phase_41_latency_stack_integration.py`, `tests/runtime/test_ttft.py` — extend these.
- **Mascot audit:** there's a CI `mascot-audit` gate — the many-modes change must keep it green.
</code_context>

<specifics>
## Specific Ideas

- **Mode state machine test:** feed synthetic ws frames (silent → build → drop → breakdown → voice>0) → assert the mascot enters the right mode for each, with hysteresis preventing single-frame flicker, and that an ambiguous/contradictory frame does NOT trigger a decorative mode change (anti-slop).
- **TTFT budget test:** replay real reaction traffic through TTFTMeter → assert rolling avg ≤ budget; assert thinking_gate stays MINIMAL.
- **Dropout test:** drive PlaybackQueue under load → assert zero underruns (reuse soak counter).
- **Live-drive recipe (Kaan-action):** run a real set both modes → mascot visibly changes mode on real drops/builds/breakdowns + while the AI talks, holds 60fps, no audio dropouts, TTFT feels instant.

<deferred>
## Deferred Ideas (Kaan-action — real hardware, autonomous carveout)

- The real **TTFT / 60fps / no-dropout-under-a-real-set + "does the mascot feel alive across its modes" drive on Kaan's Mac** is the PERF-* + LIVE-05/05a felt sign-off (his eyes + ears). Engineering ships the perf budgets + the mode state machine + automated/synthetic assertions + the measurement recipe.
- **Full 3D Three.js/GLB mascot rig** (Meshy/Hunyuan3D + Mixamo) is v2.x scope ([[project_mascot_as_vtuber_personality_surface]]) — NOT this phase. This phase makes the current rig react across many modes off real signals.
- Richer per-mode art/animation polish may land in Phase 57 (Sexify Finish, `impeccable` skill) once the mode mapping is proven here.
