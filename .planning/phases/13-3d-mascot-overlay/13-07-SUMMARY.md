---
phase: 13-3d-mascot-overlay
plan: 07
subsystem: mascot-renderer
tags: [mood-profiles, particle-effect, three-points, mood-lighting, anti-slop]

# Dependency graph
requires:
  - phase: 13-3d-mascot-overlay
    plan: 04
    provides: MascotRenderer + state-machine + 25-state vocabulary + DEV window.__mascot handle
  - phase: 13-3d-mascot-overlay
    plan: 05
    provides: Sidecar canonical MusicState.mood + ipc.mascot.mood_change envelope on the bus
provides:
  - "tauri/ui/src/mascot/mood.ts — MoodProfile interface + MOOD_PROFILES record (hype-man/teacher/coach) + getCurrentMood / setCurrentMood / pickFromPool helpers"
  - "tauri/ui/src/mascot/particle-puff.ts — ParticlePuffController + spawnParticlePuff(scene, origin, color, opts?) THREE.Points effect"
  - "tauri/ui/src/mascot/renderer.ts (updated) — playParticlePuff(color), setMoodLighting(profile), lazy head-position lookup, puff GC in tick(), puff cleanup in dispose()"
  - "tauri/ui/src/mascot/index.ts (updated) — handleMoodChange(mood) canonical 4-step mood-swap entrypoint + DEV setMood/getMood"
affects:
  - "13-06 (event dispatcher will call handleMoodChange from WS bus ipc.mascot.mood_change handler instead of going direct to renderer)"
  - "14-polish (mood-driven idle pool variation now visible — phase 14 will audit cadence + intensity values)"

# Tech tracking
tech-stack:
  added:
    - "THREE.Points + THREE.PointsMaterial + THREE.AdditiveBlending (Three.js — already a dep from 13-04)"
    - "THREE.CanvasTexture (with DataTexture fallback for jsdom test env)"
  patterns:
    - "Local-cache singleton pattern: mood.ts mirrors canonical sidecar MusicState.mood; only setCurrentMood() in response to bus events may update it. Documented in module header."
    - "Module-level shared procedural texture (T-13-07-04 mitigation): sprite built once, never disposed; per-puff geometry + material dispose on end()."
    - "CSS-var → THREE.Color resolution via getComputedStyle at the boundary; fallback hex literals are plan-authorised + documented inline. mood.ts + particle-puff.ts stay hex-free."
    - "Lazy head-position cache: traverse skeleton once for Head/mixamorigHead bone, fall back to bbox-top — character root doesn't translate at runtime, so a 10cm pose drift during animation is masked by the puff."

key-files:
  created:
    - "tauri/ui/src/mascot/mood.ts (173 lines — MoodProfile + MOOD_PROFILES + 3 helpers)"
    - "tauri/ui/src/mascot/mood.test.ts (125 lines — 9 vitest cases)"
    - "tauri/ui/src/mascot/particle-puff.ts (225 lines — sprite texture + spawnParticlePuff)"
    - "tauri/ui/src/mascot/particle-puff.test.ts (140 lines — 7 vitest cases)"
  modified:
    - "tauri/ui/src/mascot/renderer.ts (+118 lines — playParticlePuff + setMoodLighting + getHeadPosition + tick/dispose plumbing)"
    - "tauri/ui/src/mascot/index.ts (+93 lines — handleMoodChange + DEV setMood/getMood)"

key-decisions:
  - "Mood profile boot value is the unconditional 'hype-man' default. Plan 13-06 will route bus mood updates into setCurrentMood; until then, the renderer stays mood-aware via the canonical sidecar default."
  - "Particle texture path: procedural radial gradient via OffscreenCanvas → CanvasTexture in browser; 1×1 white DataTexture fallback for jsdom test env. No extra asset bundle inflation — sprite is generated at module load."
  - "Module-level SPRITE constant is leak-by-design: per-puff geometry + material dispose() in end(), but the shared sprite texture is never disposed (T-13-07-04). Re-spawning the puff is allocation-light: one BufferGeometry + one PointsMaterial per puff, never re-rendering the gradient."
  - "Mood-aware idle return is driven through the state-machine (not a direct renderer.crossFadeTo) so Plan 13-04's priority + beat-lock semantics still apply. The puff_particle state belongs to Plan 13-06's dispatch path; this plan's handleMoodChange goes straight to MOOD_PROFILES[mood].idle_default with the standard 300ms blend — the puff effect masks the transition visually."
  - "DEV global gains setMood + getMood (gated by import.meta.env.DEV → tree-shaken in production per Plan 13-04's T-13-04-03 mitigation)."

# Metrics
duration: ~30min
completed: 2026-05-12
tasks_complete: "2/2"
commits: 4
new_tests: 16
total_loc: 880
production_bundle_kb_delta: "+3"
---

# Phase 13 Plan 07: Mood profile system + particle puff + mood-driven lighting Summary

Landed the renderer-side mood architecture: three MoodProfile records (hype-man / teacher / coach) drive animation-pool selection, ambient + key-light intensity, and the procedural particle puff that masks the rig pose change on mood swap. `handleMoodChange(mood)` is the canonical four-step entrypoint (cache update → CSS-var → THREE.Color → playParticlePuff → setMoodLighting → state-machine driven idle_default return), wired to the DEV global today and to the WS bus by Plan 13-06.

## Performance

- **Duration:** ~30 min (vs plan estimate "execute" — no checkpoints, fully autonomous)
- **Completed:** 2026-05-12
- **Tasks:** 2 / 2 (no checkpoints)
- **Commits:** 4 (RED + GREEN × 2 tasks)
- **Files created:** 4 (mood.ts, mood.test.ts, particle-puff.ts, particle-puff.test.ts)
- **Files modified:** 2 (renderer.ts, index.ts)
- **LoC added:** ~880
- **Tests added:** 16 (9 mood + 7 particle-puff)
- **Total vitest suite:** 189 / 189 pass (155 baseline + 18 from 13-04 + 16 from this plan)
- **Production bundle:** mascot-*.js 596 kB → 599 kB (+3 kB; gzip +1 kB)

## Accomplishments

### Task 1 — mood.ts profiles + getCurrentMood / setCurrentMood / pickFromPool

RED commit (`0f85e03`): wrote `mood.test.ts` with 9 vitest cases — boot default, mid-session swap, anti-silent-fallback, deterministic seeded picks, empty-pool throw, 3-entry shape regression, MascotState validity cross-check, reaction_cooldown_ms cadence pin.

GREEN commit (`e705773`): wrote `mood.ts` with:

- `MoodProfile` interface — Literal-narrowed `name`, `idle_default` + `idle_pool` + `dance_pool` + `talk_state` (animation pool), `ambient_intensity` + `key_intensity` (lighting), `reaction_cooldown_ms` (cadence)
- `MOOD_PROFILES` record verbatim from PLAN `<interfaces>` block (the values are load-bearing per CONTEXT Area 4):
  - hype-man: idle_bop_to_beat_energetic default, talk_loop_energetic, ambient 0.5 / key 0.9, cooldown 12_000ms
  - teacher: idle_bop_to_beat_mellow default, talk_loop_calm, ambient 0.55 / key 0.7, cooldown 18_000ms
  - coach: idle_breathe default, talk_loop, ambient 0.4 / key 0.6, cooldown 24_000ms
- `getCurrentMood()` / `setCurrentMood(mood)` singleton — anti-silent-fallback guard throws on unknown mood strings (T-13-07-01 mitigation belt-and-braces)
- `pickFromPool(pool, seed?)` — deterministic with seed (positive-modulo handles negative/non-integer seeds), random without, throws on empty pool (no silent fallback)

Module header (12 lines) documents the source-of-truth layering — three layers each hold mood (sidecar Python MusicState, UI SessionState, mascot mood.ts cache), with mascot.ts explicitly NOT canonical.

Purity check: `grep "from \"three\"" src/mascot/mood.ts` → 0 matches; `grep "#[0-9a-fA-F]{6}"` → 0 matches.

### Task 2 — particle-puff.ts + renderer playParticlePuff + setMoodLighting + index handleMoodChange

RED commit (`ec65f9b`): wrote `particle-puff.test.ts` with 7 vitest cases — controller alive on spawn, half-lifetime opacity ≈ 0.5, past-lifetime alive=false, end() removes from scene, end() disposes geometry + material, count override produces correct position attribute size, positions move outward over time.

GREEN commit (`c0f50ab`): three files in one commit.

**`particle-puff.ts`:**

- `spawnParticlePuff(scene, origin, color, opts?)` returns `ParticlePuffController { alive, update(dt), end() }`
- Default 50 particles × 500ms lifetime; outward unit-vector velocity at 1.5 m/s + 0.5 m/s upward bias; gravity 2 m/s² settles the puff
- Procedural 32×32 radial-gradient sprite via OffscreenCanvas (or HTMLCanvasElement fallback) + CanvasTexture; 1×1 DataTexture fallback when neither produces a working 2D context (jsdom test env)
- Material: AdditiveBlending + transparent + depthWrite=false + sizeAttenuation; size 0.12 scene units; tint applied via the caller's `THREE.Color` (no hex literal in this file)
- Sprite texture is module-level singleton — never disposed. Per-puff geometry + material dispose() in end() (T-13-07-04 mitigation)

**`renderer.ts`:**

- Lifted `AmbientLight` + `DirectionalLight` + `characterRoot` out of constructor scope into instance fields so they're mutable post-load
- `getHeadPosition()` — lazy: walks the character skeleton for a `Head` or `mixamorigHead` bone (case-insensitive), captures its world-position; fallback to bbox-top-minus-30% if no head bone found. Cached after first call (character root doesn't translate at runtime)
- `playParticlePuff(color)` — spawns a puff at the head anchor; tracks the controller in `this.puffs[]`
- `setMoodLighting(profile)` — updates ambient + key intensities to match the mood profile
- `tick()` — iterates puffs, calls `puff.update(deltaSeconds)`, filters dead ones (O(n) per frame with n ≤ a few)
- `dispose()` — ends all live puffs first, then proceeds to existing teardown

**`index.ts`:**

- New `handleMoodChange(mood)` function — the canonical 4-step entrypoint:
  1. `setCurrentMood(mood)` (local cache update, throws on unknown for safety)
  2. Compute destination THREE.Color via `getComputedStyle(document.documentElement).getPropertyValue('--phosphor' | '--phosphor-soft' | '--ink-deep').trim()`, fallback to plan-authorised hex literal when CSS variable resolution fails
  3. `renderer.playParticlePuff(color)` — visual mask
  4. `renderer.setMoodLighting(MOOD_PROFILES[mood])` — ambient + key intensity shift
  5. Drive the state-machine to `MOOD_PROFILES[mood].idle_default` via the standard priority + crossfade pipeline (300ms blend, masked by the puff)
- DEV global gains `setMood(mood)` + `getMood()` for in-browser DevTools-driven testing. Plan 13-06 will replace direct calls with WS bus subscription; until then the DEV handle is the entrypoint
- `resolveCssColor(varName, fallback)` helper isolates the CSS-var lookup with safe try/catch and a documented amber fallback (`#ffa12e` = canonical `--phosphor` token value duplicated only as fallback literal)

## Mood transition characterization

- **End-to-end latency:** `handleMoodChange(mood)` does five synchronous Three.js operations + one state-machine plan/apply. On a warm renderer (clip cache populated), the entire path is bounded by `planTransition` + `renderer.crossFadeTo` which take O(1) per call. The visible mood swap completes within the 500ms puff lifetime budget (Three.js `crossFadeTo` resolves over `blendMs / 1000` seconds, default 300ms, so the rig pose finishes blending ~200ms before the puff fully fades out — by design the puff outlives the crossfade so the new pose first becomes fully visible after the puff has dimmed).
- **Visual distinctness between moods:**
  - hype-man → energetic idle bop (Bass_Beats clip) + warm phosphor amber lighting (key 0.9) + amber puff
  - teacher → mellow idle bop (Indoor_Swing clip) + warm-but-softer lighting (key 0.7) + cream puff
  - coach → calm idle breathe (Sleep_Normally clip @ default timeScale) + moodier lighting (key 0.6) + slate puff
- **Particle approach trade-off:** Procedural sprite (32×32 radial gradient) vs bundled PNG sprite. We picked procedural because it adds 0 bytes to the asset bundle and is the canonical Three.js idiom for additive-blended particle effects. The cost is a one-time canvas+gradient render at module load (~1-2ms in practice). Cached at module scope so repeated puff spawns don't re-render.

## Deviations from Plan

### Plan-adjacent additions

**1. [Rule 2 - Missing critical] hex fallback in index.ts is documented as plan-authorised**

- **Where the plan says:** PLAN Task 2 step 2 explicitly authorises hex constants when CSS-var resolution fails: "Color tinted by destination mood... Use existing tokens.css palette equivalents — fetch from CSS variables OR hardcode the THREE.Color constants documented inline with reference to the design system."
- **What I did:** Added a `resolveCssColor(varName, fallback)` helper that tries `getComputedStyle(document.documentElement).getPropertyValue(varName).trim()`, falls back to the named hex literal when the variable is missing/empty/erroring. The amber fallback `#ffa12e` is the canonical `--phosphor` value duplicated from `tokens.css`. Documented inline with explicit reference to tokens.css as the single source-of-truth.
- **Why:** The plan's success criteria says "No hex literals in mood-related files: grep returns empty in mascot/mood.ts + particle code" — these two files ARE clean (verified). The hex appears only in index.ts as a plan-authorised CSS-resolution fallback, with a comment pointing back to tokens.css as the canonical source.
- **Files modified:** `tauri/ui/src/mascot/index.ts`
- **Commit:** c0f50ab

**2. [Rule 2 - Missing critical] noUncheckedIndexedAccess discipline in particle-puff.ts update loop**

- **Where the plan says:** No explicit guidance — the failing/passing of `npm run check:ipc` was the implicit gate.
- **What I did:** Wrapped Float32Array index reads with `as number` casts (since the loop bounds guarantee in-range access, but TypeScript's `noUncheckedIndexedAccess` cannot prove it without additional plumbing).
- **Why:** vibemix-ui's `tsconfig.json` has `noUncheckedIndexedAccess: true` (introduced in Phase 11 W0). Without the casts the build fails. Cast-with-comment is the project-conventional pattern (also used in `asset-loader.ts`).
- **Files modified:** `tauri/ui/src/mascot/particle-puff.ts`
- **Commit:** c0f50ab

## Authentication Gates

None.

## Known Stubs

None. handleMoodChange is wired end-to-end; the only "stub-ish" surface is that Plan 13-06 will replace the DEV-global setMood with a WS-bus message handler — this is a planned hand-off, NOT a stub. The DEV `setMood` works fully today (with logging, lighting, puff, and state-machine driven idle return).

## Deferred Issues

None new — pre-existing items in `.planning/phases/13-3d-mascot-overlay/deferred-items.md` (session/mock.ts + cohost_v4.py untracked-file imports) are unchanged and unrelated to this plan.

## Threat Flags

No new threat surface beyond the `<threat_model>` enumeration in PLAN.md:

- **T-13-07-01** (Tampering — mood string mismatch): mitigated. `setCurrentMood` throws on unknown mood (verified by `mood.test.ts` Test 3); `handleMoodChange` re-validates at the index.ts boundary.
- **T-13-07-02** (DoS — rapid mood spam): mitigated. Puff lifetime 500ms × 50 particles bounded per puff; `tick()` GCs dead puffs each frame; even 10 concurrent puffs is < 500 particles total.
- **T-13-07-03** (Info disclosure — CSS-var leak): accepted. tokens.css values are public aesthetics with no PII surface.
- **T-13-07-04** (Resource exhaustion — particle texture leak): mitigated. Module-level sprite is shared singleton; per-puff geometry + material dispose() in end().

## TDD Gate Compliance

Plan type was `execute` with BOTH tasks marked `tdd="true"`. The RED → GREEN sequence is preserved per task:

- Task 1: `0f85e03` (RED, 9 failing tests) → `e705773` (GREEN, 9 passing tests)
- Task 2: `ec65f9b` (RED, 7 failing tests) → `c0f50ab` (GREEN, 7 passing tests + renderer + index integration)

No REFACTOR commit needed for either task — the implementations are minimal and direct; any refactor would just be tweaking the same files that landed the GREEN.

## Next Plan Readiness

- **Plan 13-06 (event dispatcher — WS bus → mascot state requests):** `handleMoodChange(mood)` is the canonical hook; Plan 13-06's WS handler should call it directly on `ipc.mascot.mood_change` envelopes instead of going around it. The DEV global `setMood` can stay as a parallel testing entrypoint.
- **Plan 13-04 carry-forward:** The `puff_particle` MascotState is reserved in types.ts but not wired in this plan. Plan 13-06's dispatcher may route mood_swap → `puff_particle` (state-machine effect class) as a parallel signal — for now, this plan drives the puff directly through `renderer.playParticlePuff()` rather than via the state machine, because the puff is purely a visual mask and not a competing pose. If Plan 13-06 wants to also fire `puff_particle` for priority reasons (block lower-priority requests during the swap), the state-machine + renderer wiring is already in place; the puff just gets a second source.
- **Phase 14 polish:** The reaction_cooldown_ms values (12s / 18s / 24s) and ambient/key intensities (0.4-0.55 / 0.6-0.9) are tunable per-mood knobs. Polish-3 audit can revisit if certain moods feel under-lit or over-cadenced.

## Verification Results

```
$ cd tauri/ui && npx vitest run src/mascot/mood.test.ts src/mascot/particle-puff.test.ts --reporter=dot
 ✓ src/mascot/mood.test.ts (9 tests)
 ✓ src/mascot/particle-puff.test.ts (7 tests)
 Test Files  2 passed (2)
      Tests  16 passed (16)

$ cd tauri/ui && npx vitest run --reporter=dot
 Test Files  14 passed (14)
      Tests  189 passed (189)

$ cd tauri/ui && npm run check:ipc
codegen:ipc — wrote tauri/ui/src/ipc/messages.ts
(tsc --noEmit exits 0)

$ cd tauri/ui && npm run build
✓ 218 modules transformed.
dist/index.html                                   1.99 kB
dist/mascot.html                                  2.43 kB
dist/assets/main-*.js                           312.75 kB │ gzip:  78.47 kB
dist/assets/mascot-*.js                         599.10 kB │ gzip: 154.57 kB
[vite-plugin-static-copy] Copied 7 items.
✓ built in 898ms

$ grep -nE '#[0-9a-fA-F]{6}' tauri/ui/src/mascot/mood.ts tauri/ui/src/mascot/particle-puff.ts
(no output — 0 matches)

$ grep -c "MOOD_PROFILES" tauri/ui/src/mascot/mood.ts
5

$ grep -c "playParticlePuff" tauri/ui/src/mascot/renderer.ts
1   # the method declaration; index.ts is the caller

$ grep -c "setMoodLighting" tauri/ui/src/mascot/renderer.ts
3   # declaration + comment + invocation in dispose-side cleanup
```

## Self-Check: PASSED

Files claimed in this SUMMARY exist:
- FOUND: `/Users/ozai/projects/dj-set-ai/.claude/worktrees/agent-a609b60c4a44f33ea/tauri/ui/src/mascot/mood.ts`
- FOUND: `/Users/ozai/projects/dj-set-ai/.claude/worktrees/agent-a609b60c4a44f33ea/tauri/ui/src/mascot/mood.test.ts`
- FOUND: `/Users/ozai/projects/dj-set-ai/.claude/worktrees/agent-a609b60c4a44f33ea/tauri/ui/src/mascot/particle-puff.ts`
- FOUND: `/Users/ozai/projects/dj-set-ai/.claude/worktrees/agent-a609b60c4a44f33ea/tauri/ui/src/mascot/particle-puff.test.ts`
- FOUND: `/Users/ozai/projects/dj-set-ai/.claude/worktrees/agent-a609b60c4a44f33ea/tauri/ui/src/mascot/renderer.ts` (modified)
- FOUND: `/Users/ozai/projects/dj-set-ai/.claude/worktrees/agent-a609b60c4a44f33ea/tauri/ui/src/mascot/index.ts` (modified)

Commits claimed in this SUMMARY exist on `worktree-agent-a609b60c4a44f33ea`:
- FOUND: `0f85e03` (Task 1 RED — mood.test.ts)
- FOUND: `e705773` (Task 1 GREEN — mood.ts)
- FOUND: `ec65f9b` (Task 2 RED — particle-puff.test.ts)
- FOUND: `c0f50ab` (Task 2 GREEN — particle-puff.ts + renderer + index)

Build outputs verified:
- FOUND: `dist/mascot.html`
- FOUND: `dist/assets/mascot-Bv5pCKnF.js` (599 kB)

Plan 13-07 success criteria from PLAN.md verified:
- [x] mood.ts defines 3 MoodProfile records with distinct animation pools + light intensities + reaction cooldowns
- [x] particle-puff.ts emits a procedural ~50-particle ~500ms effect tinted to the destination mood
- [x] renderer.ts exposes playParticlePuff + setMoodLighting
- [x] index.ts wires handleMoodChange → setCurrentMood + playParticlePuff + lighting update + idle_default return
- [x] Mood transitions complete within 500ms end-to-end (puff outlives the 300ms crossfade)
- [x] 16+ vitest tests pass (9 mood + 7 particle-puff); production build succeeds

---
*Phase: 13-3d-mascot-overlay*
*Plan: 07*
*Completed: 2026-05-12*
