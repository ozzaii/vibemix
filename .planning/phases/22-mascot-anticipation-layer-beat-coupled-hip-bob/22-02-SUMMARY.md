---
phase: 22
plan: 02
subsystem: mascot
tags: [mascot, three-js, additive-blend, anticipation, ws-bus, phase-17-integration]
requires:
  - 22-01 (spike + WAVE-0-SPIKE.md template)
  - 13-04 (mascot state vocabulary, STATE_PRIORITY, MascotState)
  - 13-05 (ws_bus 30Hz mascot broadcast)
  - 17-01 (MusicState beat_phase + active_genre fields)
provides:
  - MascotState union with 5 prep_* members (anticipation pool)
  - MascotStateClass "anticipation" at priority 70
  - AdditiveLayer class (Three.js — single-mixer, weight-managed)
  - 30Hz ws_bus payload extended with beat_phase + active_genre
  - 5 prep_* GLB placeholders + ASSETS.md authoring brief
affects:
  - Wave 2 (22-03) — wires AdditiveLayer into renderer + fire-path
tech-stack:
  added:
    - three.AnimationUtils.makeClipAdditive (loader-side conversion)
  patterns:
    - Pitfall 19 single-mixer mandate (additive on SAME mixer, NOT a second)
    - Anti-slop discipline carried from asset-loader.ts (throw on unknown state)
    - Purity discipline carried from state-machine.ts (explicit tick(now), no wall-clock reads)
key-files:
  created:
    - .planning/phases/22-mascot-anticipation-layer-beat-coupled-hip-bob/ASSETS.md
    - tauri/ui/assets/mascot/animations/prep_lean_in_neutral.glb
    - tauri/ui/assets/mascot/animations/prep_lean_in_hyped.glb
    - tauri/ui/assets/mascot/animations/prep_head_turn_left.glb
    - tauri/ui/assets/mascot/animations/prep_head_turn_right.glb
    - tauri/ui/assets/mascot/animations/prep_settle.glb
    - tauri/ui/src/mascot/additive-layer.ts
    - tauri/ui/src/mascot/additive-layer.test.ts
    - tests/runtime/test_ws_bus_phase22_fields.py
  modified:
    - tauri/ui/assets/mascot/manifest.json
    - tauri/ui/src/mascot/types.ts
    - tauri/ui/src/mascot/asset-loader.ts
    - src/vibemix/runtime/ws_bus.py
decisions:
  - "Single AnimationMixer per mascot — anticipation layer is the SECOND AnimationAction on the existing mixer, not a second mixer (Pitfall 19)."
  - "makeClipAdditive runs ONCE at load (in asset-loader) — NOT per-play. Non-prep clips intentionally skip additive; only the anticipation overlay is additive in v2.0 (D-LOCKED)."
  - "action.weight as static multiplier preserves the fadeIn weight interpolant from corruption. Pre-setting effectiveWeight before fadeIn cancels the interpolant (verified empirically via three.js source)."
  - "Both beat_phase + downbeat_phase ride the wire — Plan 13-06 dispatcher binds to downbeat_phase, Phase 22 layers bind to beat_phase. Bus is a dumb wire; anti-hallucination is the renderer's job."
  - "5 placeholder GLBs byte-copied from existing Mixamo clips so the asset-loader pipeline + Wave 2 fire-path land in parallel with real authoring. Replacement is a HARD GATE before P26 viral demo / v2.0 RC."
metrics:
  duration_minutes: 14
  completed_date: 2026-05-14
  commits: 6
  files_changed: 13
  pytest_delta: "+4 new (1843→1847 passed, same 10 pre-existing failures)"
  vitest_delta: "+8 new (421→429 passed, 0 regressions)"
---

# Phase 22 Plan 02: Anticipation Layer Foundation Summary

**One-liner:** Ships the AdditiveLayer wrapper, 5 prep_* state vocabulary,
manifest + asset-loader makeClipAdditive pass, and the ws_bus 30Hz
beat_phase + active_genre extension — the foundation Wave 2 (Plan 22-03)
wires into the fire-path. Real GLB authoring deferred to Kaan / Blender
artist (placeholders ship to keep the pipeline loadable).

## What Shipped

### 1. AdditiveLayer API (`tauri/ui/src/mascot/additive-layer.ts`)

The anticipation overlay class. Lives alongside the renderer's existing
mixer (NEVER a second AnimationMixer — Pitfall 19 hard rule). Public API:

```typescript
export interface PlayOpts {
  blendMs: number;  // crossfade-in duration
  weight: number;   // target effective weight (0..1)
}

class AdditiveLayer {
  constructor(mixer: AnimationMixer, clips: Map<MascotState, LoadedClip>);

  /** Play a prep_* state; ramps weight via fadeIn over blendMs.
   *  Throws on unknown state (anti-slop). */
  play(state: MascotState, opts: PlayOpts): void;

  /** Fade weight back to 0 over blendMs. No-op if nothing playing. */
  fadeOut(blendMs: number): void;

  /** Renderer rAF hook. Drives fadeOut-completion detection without
   *  wall-clock reads (purity mirror of state-machine.ts). */
  tick(now: number): void;

  /** null when layer is silent; the playing MascotState otherwise. */
  currentState(): MascotState | null;
}
```

### 2. Five-clip anticipation vocabulary (`tauri/ui/src/mascot/types.ts`)

| State                     | Class         | Priority | Vibe                                                           |
| ------------------------- | ------------- | -------- | -------------------------------------------------------------- |
| `prep_lean_in_neutral`    | anticipation  | 70       | Subtle 6° forward torso lean, 400ms                            |
| `prep_lean_in_hyped`      | anticipation  | 70       | 12° lean + chin-up + tense hands, 350ms (hard_tek / high build) |
| `prep_head_turn_left`     | anticipation  | 70       | 25° head yaw left (Deck A), 250ms                              |
| `prep_head_turn_right`    | anticipation  | 70       | 25° head yaw right (Deck B), 250ms                             |
| `prep_settle`             | anticipation  | 70       | Reverse-curve return-to-zero, 300ms                            |

Two new `StateTrigger` labels: `"anticipate"` (fire prep) +
`"anticipation_settle"` (fire reverse).

**Priority slot at 70** sits between `react=60` and `talk=80`. Anticipation
pre-empts react/dance/idle/explanation/misc but yields to talk — when audio
arrives, the talk_loop takes over and the anticipation fades out naturally
because it's on its OWN AnimationAction (the base layer is uninterrupted
per the 4-layer additive model — D-LOCKED simplified subset for v2.0).

### 3. Single-mixer contract (Pitfall 19 prevention)

The asset-loader applies `AnimationUtils.makeClipAdditive(clip)` ONCE at
load (per-entry, gated by `entry.states.every(s => s.startsWith("prep_"))`).
This sets `clip.blendMode = AdditiveAnimationBlendMode` so the mixer
combines the additive action's contribution with the base-layer action's
output via subtraction (the additive clip is converted to a delta from
its first-frame pose at load time).

Non-prep clips intentionally skip additive — they stay on the default
Normal blend mode. The full 4-layer additive model (mood +
anticipation + speak + react) is deferred to v2.1 per CONTEXT D-LOCKED;
v2.0 ships the 3-layer subset (mood / anticipation overlay /
speak+react).

### 4. Weight-management approach

Three.js `action.fadeIn(blendSec)` schedules a weight interpolant from
0 → 1 over `blendSec` seconds. The action's static `weight` field
(distinct from `_effectiveWeight`) acts as a multiplier:
`_effectiveWeight = weight * interpolantValue`. Setting
`action.weight = opts.weight` (e.g. 0.6 for restrained prep) yields a
final effective weight of `0.6 * 1.0 = 0.6` after fadeIn completes —
without corrupting the interpolant.

**Empirical discovery:** Pre-setting `setEffectiveWeight(0)` before
`fadeIn` cancels the weight interpolant (Three internally calls
`_updateWeight` which short-circuits when an interpolant exists; setting
the weight directly stops the fade). The AdditiveLayer code never
pre-sets effectiveWeight on lazy-built actions — the default `weight=1`
multiplier + lazy build (action only constructed on first play) prevents
leak onto the base layer before any prep_* fires.

### 5. fadeOut completion via explicit tick(now)

The class mirrors `state-machine.ts` purity discipline — no
`setTimeout`, no `Date.now()` reads inside class methods. `fadeOut(blendMs)`
stores the relative blendMs; the next `tick(now)` call converts it to an
absolute deadline (`now + blendMs`); subsequent ticks check `now >=
deadline` and clear `current` + reset the action's weight to 0.

Uses two separate fields (`fadeOutPendingMs` + `fadeOutDeadlineAt`)
instead of a magnitude-based sentinel — `performance.now()` and
`Date.now()` differ by ~13 orders of magnitude and a single-field
sentinel can't safely distinguish "relative duration just stored" from
"absolute deadline in the small-magnitude clock" (e.g. `t0=1_000_000` ms
test fixture).

### 6. ws_bus 30Hz payload extension (`src/vibemix/runtime/ws_bus.py`)

Added two fields after `downbeat_phase`:

```python
"beat_phase": state.beat_phase,        # Phase 17 alias of downbeat_phase, ∈ [0, 1)
"active_genre": state.active_genre,    # "house" | "techno" | "hard_tek" | "unknown"
```

Both `beat_phase` and `downbeat_phase` ship on the wire simultaneously
(Plan 13-06 dispatcher binds to `downbeat_phase`; Phase 22 layers bind to
`beat_phase`). The bus is a **dumb wire** — under low `bpm_confidence`
the bus still emits `beat_phase` as-is; the renderer (Plan 13-04 Open Q 4)
ignores beat-locked behavior under low confidence. Anti-hallucination is
the renderer's responsibility, not the bus's.

### 7. GLB stub policy & ASSETS.md authoring brief

The 5 `prep_*.glb` files committed to `tauri/ui/assets/mascot/animations/`
are **byte-copied placeholders** sourced from existing clips:

| prep clip                    | placeholder source         |
| ---------------------------- | -------------------------- |
| `prep_lean_in_neutral.glb`   | `alert_quick_turn.glb`     |
| `prep_lean_in_hyped.glb`     | `alert_quick_turn.glb`     |
| `prep_head_turn_left.glb`    | `alert_quick_turn.glb`     |
| `prep_head_turn_right.glb`   | `alert_quick_turn.glb`     |
| `prep_settle.glb`            | `shrug.glb`                |

Each is a real loadable GLB (the asset-loader doesn't error) but **does
NOT honor the delta-zero requirement** (Hips + lower-body bones must hold
zero across keyframes for additive blending to look right — placeholders
have full Hips motion which will fight the procedural hip-bob in Wave 3).
This is intentional: it surfaces the "asset author owes us delta-zero
clips" gate visibly during dev playback rather than silently shipping
broken visuals.

`ASSETS.md` documents the full authoring contract:
- Per-clip vibe + duration + degrees + curve direction
- Mixamo → Blender → strip pipeline (re-target, manual delta-zero on
  Hips + lower-body bones, export GLB, run strip pass)
- ≤300KB DRACO size budget (Pitfall 23)
- Verification checklist (Hips delta <0.001, file size, retarget
  correctness, `makeClipAdditive` post-load blend mode assertion)

**Replacement gate:** Real delta-zero authored GLBs MUST land before
P26 viral demo / v2.0 RC tag — tracked in `KAAN-ACTION.md`.

## Decisions Made

1. **Pitfall 19 — single AnimationMixer.** The AdditiveLayer constructor
   takes the renderer's mixer; it does NOT instantiate one of its own.
   Verified by the "shares the caller's mixer" test
   (`mixer.existingAction(clip)` returns the same handle whether queried
   via the layer or directly via the mixer).

2. **makeClipAdditive at load, NOT at play.** Conversion is one-shot
   and runs in the asset-loader path. Lazy / play-time conversion would
   re-pay the cost on every play, and it would silently fail if the
   loader skipped the conversion (debug nightmare — clip plays but looks
   wrong). Loader-side gate makes the contract explicit: the clip arrives
   to the renderer already additive.

3. **`action.weight` as multiplier, not `setEffectiveWeight`.** Discovered
   that `setEffectiveWeight` cancels Three's weight interpolant — using
   the static `.weight` field as a final scale factor preserves the
   interpolant. Verified empirically (probe script in conversation log).

4. **Both `beat_phase` + `downbeat_phase` on the wire.** Phase 13-06
   dispatcher already binds to `downbeat_phase`; ripping it out would
   require touching that code. Carrying both lets the renderer migrate
   incrementally — Wave 2 will subscribe new code to `beat_phase` while
   old code keeps consuming `downbeat_phase`.

5. **Placeholder GLBs over no-op stubs.** A 12-byte GLB header would
   fail the GLTFLoader. Real Mixamo clips load cleanly and let Wave 2
   land in parallel. The placeholder mismatch is documented and
   gate-tracked.

## Deviations from Plan

**None substantive.** Followed the plan task-by-task:
- Task 1: ASSETS.md + 5 placeholder GLBs committed ✓
- Task 2: types vocabulary + manifest + asset-loader + AdditiveLayer
  (RED→GREEN, 8 new vitest specs) ✓
- Task 3: ws_bus extension (RED→GREEN, 4 new pytest specs) ✓

**Minor implementation discovery during Task 2:**
`setEffectiveWeight(0)` pre-init cancels the fadeIn interpolant. Refactored
to use `action.weight` as a static multiplier instead. Verified
empirically via a probe script (not committed). Documented in the
"Weight-management approach" section above. This is a Rule 1 (bug fix)
type adjustment, but the bug was in my first-draft implementation —
nothing in the plan or the codebase had to change.

## Self-Check: PASSED

**Files exist:**
- `.planning/phases/22-mascot-anticipation-layer-beat-coupled-hip-bob/ASSETS.md` — FOUND
- `tauri/ui/assets/mascot/animations/prep_lean_in_neutral.glb` — FOUND
- `tauri/ui/assets/mascot/animations/prep_lean_in_hyped.glb` — FOUND
- `tauri/ui/assets/mascot/animations/prep_head_turn_left.glb` — FOUND
- `tauri/ui/assets/mascot/animations/prep_head_turn_right.glb` — FOUND
- `tauri/ui/assets/mascot/animations/prep_settle.glb` — FOUND
- `tauri/ui/src/mascot/additive-layer.ts` — FOUND
- `tauri/ui/src/mascot/additive-layer.test.ts` — FOUND
- `tests/runtime/test_ws_bus_phase22_fields.py` — FOUND

**Commits exist:**
- `18a0744`: scaffold 5 prep_* GLB placeholders + ASSETS.md — FOUND
- `ce04c92`: RED — AdditiveLayer wrapper — FOUND
- `bd5a441`: GREEN — AdditiveLayer + prep_* state vocab — FOUND
- `7ff9708`: RED — ws_broadcast Phase 22 fields — FOUND
- `3fc727c`: GREEN — ws_broadcast emits beat_phase + active_genre — FOUND

**Test counts:**
- pytest: 1847 passed (1843 baseline + 4 new), 7 skipped, 10 pre-existing
  failures unchanged
- vitest: 429 passed (421 baseline + 8 new), 0 regressions

## TDD Gate Compliance

Each TDD task followed RED → GREEN strictly:
- Task 2: `ce04c92` (test, RED) → `bd5a441` (feat, GREEN)
- Task 3: `7ff9708` (test, RED) → `3fc727c` (feat, GREEN)

Both RED commits were verified failing before the GREEN commit landed
(see conversation log). No `--no-verify`, no hook skips.

## Known Stubs

The 5 `prep_*.glb` files are byte-copied Mixamo placeholders, NOT
authored delta-zero clips. They satisfy the asset-loader contract
(loadable, `makeClipAdditive` applies cleanly) but the visual output
will be wrong (full Hips + lower-body motion fights the procedural
hip-bob from Wave 3). Documented in `ASSETS.md` "Placeholder policy"
section + tracked in `KAAN-ACTION.md` as a HARD GATE before P26 viral
demo / v2.0 RC.

This is **intentional and documented** — the placeholders surface the
"asset author owes real clips" gate visibly during dev playback. The
code-side contract (which is what v2.0 ship-gate cares about) is
complete and tested.

## Threat Flags

None — this plan does not introduce new network endpoints, auth paths,
file access patterns, or schema changes at trust boundaries. The ws_bus
extension adds two read-only fields to an existing 127.0.0.1-bound bus
that was already in the threat register from Phase 13.
