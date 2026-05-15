# Phase 31 — Research

**Gathered:** 2026-05-15 (gsd-autonomous fully)
**Status:** Ready for planning

## Key Findings From Codebase

### v2.0 Phase 22 anticipation rig (shipped — port verbatim)
- `tauri/ui/src/mascot/additive-layer.ts` — `AdditiveLayer` class. Single AnimationMixer (Pitfall 19), lazy AnimationAction build per prep_* state, `play(state, opts)` / `fadeOut(blendMs)` / `tick(now)` / `currentState()` API. Purity discipline (no wall-clock reads — `now` always passed in).
- `tauri/ui/src/mascot/additive-layer.test.ts` — 6 tests covering construction, weight ramp, makeClipAdditive, unknown-state throw, fadeOut clears state, no leak before play. Test names locked.
- `tauri/ui/src/mascot/state-machine.ts` — pure functions: `initialMachineState` / `planTransition` / `applyTransition` / `tickIdleTimeout`. Anticipation class priority 70 from `types.ts`.
- `tauri/ui/src/mascot/types.ts` — `MascotState` union, `MascotStateClass` (8 classes including `"anticipation"` priority 70), `STATE_PRIORITY` map (effect 100, talk 80, anticipation 70, react 60, dance 40, explanation 30, idle 20, misc 10). prep_* states already in union: `prep_lean_in_neutral`, `prep_lean_in_hyped`, `prep_head_turn_left`, `prep_head_turn_right`, `prep_settle`.

### MusicState API
- `src/vibemix/state/music_state.py`:
  - `active_genre: str` — `"house" | "techno" | "hard_tek" | "unknown"`. Set by `_classify_active_genre` in `state/refresh.py`.
  - No `energy_band` field; energy lives as `rms`, `bands` (sub/low/mid/high), `onset_density`, `energy_curve`, `buildup_score`. We derive an `energy_band` enum locally: `low` (rms < 0.08), `mid` (0.08–0.18), `high` (≥ 0.18). Thresholds align with cohost_v4 phase classification gates.
  - `phase: str` — `"silent"/"low"/"groove"/"build"/"drop"/"peak"/"breakdown"`.

### ws_bus payload (current)
- `src/vibemix/runtime/ws_bus.py` line 80–93: snapshot fields `audible`, `deck`, `phase`, `bpm`, `mood`, `bpm_confidence`, `downbeat_phase`, `beat_phase`, `active_genre`. Phase 31 adds two additive fields: `emotion`, `reaction_intent` (both nullable strings).
- IPC schema for typed messages: `tauri/ui/src/ipc/messages.schema.json`. `MascotMoodChange` already shipped at `ipc.mascot.mood_change`. Phase 31 adds two additive `ipc.mascot.*` schemas: `ipc.mascot.emotion_change` and `ipc.mascot.reaction_fire`.

### Frontend stack
- Vanilla TS (no React) — Vite + Vitest + Three.js 0.170. Tests live as `src/**/*.test.ts` (jsdom for mascot) plus `tests/**/*.test.ts`.
- vitest config already routes `src/mascot/*.test.ts` under jsdom. NEW per-channel layer files will live as `src/mascot/layers/{base,emotion,reaction}.ts` + adjacent `*.test.ts` — vitest config `src/**/*.test.ts` glob picks them up but jsdom routing only triggers under `src/mascot/*.test.ts`. We must add a second glob `src/mascot/layers/*.test.ts` for jsdom.

### Pitfalls in scope
- **P47** — additive-only; v2.0 test names port verbatim. Required test files (per PITFALLS line 194–196 evidence anchors):
  - `tauri/ui/src/mascot/__tests__/v2-anticipation-priority-70.spec.ts::test_anticipation_priority_70_preserved`
  - `tauri/ui/src/mascot/__tests__/v2-anticipation-timeout-crossfade.spec.ts::test_2_5s_timeout_crossfades_to_settle`
  - `tauri/ui/src/mascot/__tests__/v2-cancel-aware-crossfade.spec.ts::test_speech_interrupt_force_true_crossfades_to_settle`
  - Plus the linter-strip-aware test (v2.0 vocabulary): `v2-anticipation-linter-strip-aware.spec.ts::test_total_strip_crossfades_to_settle_then_ack_only`
  - These were "evidence anchors" referenced by P47 but never ACTUALLY landed in v2.0 (they live under `__tests__/` which has only `event-traces.json` fixtures). We CREATE them in Phase 31 as the v2.0-style port (matching contract names exactly).
- **P62** — 4-layer single-mixer race. 100ms stagger across simultaneous transitions. Vitest perf test asserts p99 < 22ms.
- **P72** — cancel-priority 999 + queue flush. Test `v2-1-cancel-flushes-queue.spec.ts` + `v2-1-cancel-priority-999.spec.ts`.
- **P52** — GLB ≤ 25 MB CI gate via shell script.

## Implementation Approach

### `priority-stack.ts` (MASCOT-20)
Pure class. State: `Map<LayerName, ActiveClip | null>` plus per-layer FIFO `Queue<PendingClip>`. API:
- `play(layer, clip, opts)` — enqueue or activate.
- `cancel(layer)` — cancel current + flush queue for that layer (priority 999 sentinel).
- `cancel_all()` — flush every layer EXCEPT base.
- `resolve()` → snapshot of active clip per layer.
- Constructor takes layer priorities (base 50, emotion 60, anticipation 70, reaction 80). Cancel sentinel 999 documented but is a flag on call rather than a stored priority.

### `crossfade-policy.ts` (MASCOT-21)
Pure function `transition(from, to)` returns `{stagger_ms, fade_in_ms, fade_out_ms}`. Defaults: 200ms in, 150ms out. Stagger derived from layer-priority ordering (highest fires at t=0, next at t=100, etc.). Cancel-priority bypasses (stagger 0, fade 0).

### Base layer (MASCOT-22)
`src/mascot/layers/base.ts` — exports `BaseLayer` class. Wraps existing `idle_breathe` AnimationAction. Priority 50. `cancel()` is a no-op (never canceled). `cancel_all()` skips base.

### Emotion layer (MASCOT-23)
`src/mascot/layers/emotion.ts` — `EmotionLayer` consumes `{active_genre, energy_band, phase}` via ws_bus snapshot or direct API. 4 states: `neutral`, `focused` (techno/house + mid energy), `hyped` (any genre + high energy), `concerned` (low energy + long phase).
Python side: `src/vibemix/state/emotion_router.py` — pure function `derive_emotion(active_genre, energy_band, phase, time_in_phase) -> str`. Emits via ws_bus. Tests `tests/state/test_emotion_router.py`.

### Reaction layer (MASCOT-24)
`src/mascot/layers/reaction.ts` — `ReactionLayer` priority 80, cancel-aware, 2.5s timeout.
Python side: `src/vibemix/agent/emote_parser.py` — `parse_emote_tags(text) -> list[ReactionIntent]` extracts `[emote:NAME]` patterns. Whitelist of NAMEs (wave, point_left, point_right, fist_pump, nod, headbang, surprised). Unknown tags rejected (anti-slop). Tests `tests/agent/test_emote_parser.py`.
Frontend: `src/mascot/reaction_dispatcher.ts` wires ws_bus `reaction_intent` to PriorityStack.

### v2.0 test name port (MASCOT-25)
Create `tauri/ui/src/mascot/__tests__/` dir with the four named spec files per P47 evidence anchors. Each spec exercises the FULL stack (PriorityStack + crossfade policy + AdditiveLayer). Grep gate: `scripts/grep_v2_test_names.sh` asserts all 4 test names appear.

### `additive-layer.ts` 3 → 4 (MASCOT-26)
Add a comment marker `// PHASE-31: 4-channel hook` describing the additive extension via the new layer stack. `additive-layer.ts` itself stays a single-channel anticipation overlay; the "4-channel" view emerges from the `PriorityStack` composing AdditiveLayer + base + emotion + reaction. We add `// PHASE-22: 3-channel today, 4-channel hook in Phase 31` marker (was missing from v2.0 file) and update the doc-block. SkeletonHelper snapshot via vitest `__tests__/v2-1-skeleton-helper-snapshot.test.ts`.

### GLB budget (MASCOT-27)
`scripts/check_mascot_glb_size.sh` — sums all `.glb` under `tauri/ui/public/mascot/` + `tauri/ui/assets/mascot/`. Asserts ≤ 25 MB. Exits 1 on overage. CI wires via `.github/workflows/` (existing file or new yml).

### ws_bus payload (additive)
Add to `runtime/ws_bus.py` snapshot: `"emotion": state.emotion or None` and `"reaction_intent": state.last_reaction_intent or None`. MusicState gets two new fields: `emotion: str | None = None` and `last_reaction_intent: str | None = None`. Both nullable, default None — non-breaking.

## Files To Create / Modify

| Path | New / Modify | REQ |
|---|---|---|
| `tauri/ui/src/mascot/priority-stack.ts` | new | MASCOT-20 |
| `tauri/ui/src/mascot/priority-stack.test.ts` | new | MASCOT-20 |
| `tauri/ui/src/mascot/crossfade-policy.ts` | new | MASCOT-21 |
| `tauri/ui/src/mascot/crossfade-policy.test.ts` | new | MASCOT-21 |
| `tauri/ui/src/mascot/layers/base.ts` | new | MASCOT-22 |
| `tauri/ui/src/mascot/layers/base.test.ts` | new | MASCOT-22 |
| `tauri/ui/src/mascot/layers/emotion.ts` | new | MASCOT-23 |
| `tauri/ui/src/mascot/layers/emotion.test.ts` | new | MASCOT-23 |
| `tauri/ui/src/mascot/layers/reaction.ts` | new | MASCOT-24 |
| `tauri/ui/src/mascot/layers/reaction.test.ts` | new | MASCOT-24 |
| `tauri/ui/src/mascot/__tests__/v2-anticipation-priority-70.spec.ts` | new | MASCOT-25 |
| `tauri/ui/src/mascot/__tests__/v2-anticipation-timeout-crossfade.spec.ts` | new | MASCOT-25 |
| `tauri/ui/src/mascot/__tests__/v2-cancel-aware-crossfade.spec.ts` | new | MASCOT-25 |
| `tauri/ui/src/mascot/__tests__/v2-anticipation-linter-strip-aware.spec.ts` | new | MASCOT-25 |
| `tauri/ui/src/mascot/__tests__/v2-1-cancel-flushes-queue.spec.ts` | new | P72 |
| `tauri/ui/src/mascot/__tests__/v2-1-cancel-priority-999.spec.ts` | new | P72 |
| `tauri/ui/src/mascot/__tests__/v2-1-four-layer-burst-perf.spec.ts` | new | P62 |
| `tauri/ui/src/mascot/__tests__/v2-1-no-animation-cycle-warning.spec.ts` | new | P62 |
| `tauri/ui/src/mascot/__tests__/v2-1-skeleton-helper-snapshot.test.ts` | new | MASCOT-26 |
| `tauri/ui/src/mascot/additive-layer.ts` | modify | MASCOT-26 (doc marker only) |
| `tauri/ui/src/mascot/types.ts` | modify | MASCOT-23/24 (add `MascotEmotion`, `MascotReaction`) |
| `tauri/ui/vitest.config.ts` | modify | jsdom routing for `__tests__/*.spec.ts` + `layers/*.test.ts` |
| `src/vibemix/state/music_state.py` | modify | MASCOT-23/24 (`emotion`, `last_reaction_intent`) |
| `src/vibemix/state/emotion_router.py` | new | MASCOT-23 |
| `src/vibemix/agent/__init__.py` | new | MASCOT-24 |
| `src/vibemix/agent/emote_parser.py` | new | MASCOT-24 |
| `tests/state/test_emotion_router.py` | new | MASCOT-23 |
| `tests/agent/test_emote_parser.py` | new | MASCOT-24 |
| `src/vibemix/runtime/ws_bus.py` | modify | additive emotion + reaction_intent fields |
| `scripts/check_mascot_glb_size.sh` | new | MASCOT-27 |
| `tests/install/test_mascot_glb_size_gate.py` | new | MASCOT-27 |

## Constraints / Anti-Patterns

- **No clean-slate rewrite.** AdditiveLayer + state-machine + types.ts stay AS IS; we extend by adding new files. Modifications to existing files are limited to additive doc markers + new optional fields.
- **No new GLB content.** Pure logic / state-layer work. Budget compliance trivial.
- **No `setTimeout` inside pure modules.** All timing via explicit `tick(now)` calls (purity discipline mirroring state-machine.ts).
- **Cancel-priority 999.** Documented sentinel. Implemented as a boolean flag on the cancel call, not an actual priority value (to avoid type pollution).
- **POC files untouched.** No edits to `cohost*.py` or `fillers/`.
- **No animation cycle warning.** vitest perf test grep on three.js console output asserts absence.

## Open Questions

None — all decisions locked per gsd-autonomous fully + 31-CONTEXT.md.

## Plan Decomposition (target ~7 plans)

1. **31-01** — PriorityStack + CrossfadePolicy (MASCOT-20/21) — core arbitration + p99 perf test.
2. **31-02** — Base layer + types.ts emotion/reaction additions (MASCOT-22).
3. **31-03** — Emotion layer (TS) + emotion_router (Python) + ws_bus payload extension (MASCOT-23).
4. **31-04** — Reaction layer (TS) + emote_parser (Python) (MASCOT-24).
5. **31-05** — v2.0 test name port + linter-strip-aware (MASCOT-25 + P47 evidence).
6. **31-06** — additive-layer.ts 3→4 marker + SkeletonHelper snapshot (MASCOT-26).
7. **31-07** — GLB ≤25MB CI gate (MASCOT-27 + P52).
8. **31-08** — Cancel-flush + 4-layer burst perf tests (P62 + P72) — covers the cross-cutting test gates.
