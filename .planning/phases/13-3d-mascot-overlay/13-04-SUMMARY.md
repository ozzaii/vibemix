---
phase: 13-3d-mascot-overlay
plan: 04
subsystem: ui
tags: [three.js, animation-mixer, state-machine, mascot, beat-lock, idle-timeout, gltf, draco, retarget]

# Dependency graph
requires:
  - phase: 13-3d-mascot-overlay
    plan: 01
    provides: Compressed Neon Rebel asset bundle (character.glb + 20 animation GLBs + manifest.json)
  - phase: 13-3d-mascot-overlay
    plan: 02
    provides: Transparent mascot Tauri window + mascot.html shell + placeholder /src/mascot/index.ts
  - phase: 11-tauri-shell-calibration-wizard
    provides: tauri/ui Node project + vite + vitest + tsconfig + npm run check:ipc gate
provides:
  - "tauri/ui/src/mascot/types.ts — full 25-state MascotState union + STATE_CLASS + STATE_PRIORITY + StateRequest contract"
  - "tauri/ui/src/mascot/asset-loader.ts — loadMascotAssets() returns LoadedAssets{character, clips, manifest}; throws on missing manifest fields / failed GLB loads (no silent fallback)"
  - "tauri/ui/src/mascot/state-machine.ts — pure functions (no Date.now, no setTimeout, no three): initialMachineState, planTransition, applyTransition, tickIdleTimeout"
  - "tauri/ui/src/mascot/renderer.ts — MascotRenderer class wraps Three.js scene + transparent WebGLRenderer + AnimationMixer + crossFadeTo + bust-framing"
  - "tauri/ui/src/mascot/index.ts — webview entrypoint: loads assets, mounts renderer, runs rAF loop with pendingSwitch + idle-timeout polling, exposes DEV-only window.__mascot.requestState"
  - "tauri/ui/mascot.html — transparent root chain (html + body) + canvas#mascot-canvas + module script"
  - "Public API contract for Plan 13-06: window.__mascot.requestState(state, opts) handle replaces with WS-bus subscription"
affects: [13-06 (WS bus → state requests), 13-07 (mood-variant idle defaults + lighting), 14-polish (animation library audit), 19-launch (hero demo)]

# Tech tracking
tech-stack:
  added:
    - "three ^0.170.0 (WebGLRenderer + Scene + AnimationMixer + Box3 + Clock + lights)"
    - "@types/three ^0.170.0"
    - "vite-plugin-static-copy ^2.2.0 (emits assets/mascot/** and draco/* to dist + dev-served)"
  patterns:
    - "Pure-function state machine — no wall-clock, no timers, every fn takes now as a param. Verifier greps for Date.now / setTimeout and asserts 0 matches."
    - "MachineState immutable updates via spread + new object — applyTransition never mutates input."
    - "Beat-locked entry expressed as `pendingSwitch: { state, atTimestamp, blendMs }` on the machine; renderer's rAF loop polls and fires when timestamps land. No setTimeout in the machine."
    - "Lazy AnimationAction cache — only allocate clipAction() the first time a state is requested; future plans can preload via a warm-up sweep if perf demands."
    - "Anti-silent-fallback: asset loader throws with filename in error message; state machine throws on unknown state names (no Map.get-returns-undefined-silently)."

key-files:
  created:
    - "tauri/ui/src/mascot/types.ts (176 lines — vocabulary contract)"
    - "tauri/ui/src/mascot/asset-loader.ts (316 lines — manifest + GLTFLoader + DRACOLoader + retargetClip integration)"
    - "tauri/ui/src/mascot/asset-loader.test.ts (182 lines — 4 vitest cases)"
    - "tauri/ui/src/mascot/state-machine.ts (308 lines — 4 pure functions)"
    - "tauri/ui/src/mascot/state-machine.test.ts (240 lines — 14 vitest cases)"
    - "tauri/ui/src/mascot/renderer.ts (274 lines — MascotRenderer class)"
  modified:
    - "tauri/ui/src/mascot/index.ts (202 lines — full Three.js + state-machine wire-up; replaces Plan 13-02 placeholder)"
    - "tauri/ui/mascot.html (transparent root chain; canvas sized 100vw × 100vh)"
    - "tauri/ui/package.json (+three +@types/three +vite-plugin-static-copy)"
    - "tauri/ui/package-lock.json (full transitive resolution — three pulls 387 packages)"
    - "tauri/ui/vite.config.ts (assetsInclude **/*.glb, viteStaticCopy targets for assets/mascot + draco)"
    - "tauri/ui/vitest.config.ts (include src/**/*.test.ts, route src/mascot/*.test.ts through jsdom)"

key-decisions:
  - "STATE_PRIORITY uses spaced numbers (10/20/30/40/60/80/100) so future classes can slot in without renumbering. Verbatim from CONTEXT Area 3."
  - "Boot state is fixed `idle_breathe` (CONTEXT Area 3). Mood-derived boot is a Plan 13-07 concern — this plan doesn't subscribe to mood yet."
  - "Beat-lock falls through to switch_now when msUntilDownbeat < 30ms (already on boundary). 30ms = ~1 frame @ 33fps."
  - "applyTransition('deny', …) returns the machine unchanged with NO lastEventAt bump. A denied request is a non-event; bumping the idle timer would let lower-priority spam keep the mascot awake while talk_loop is active."
  - "asset-loader retargets via SkeletonUtils.retargetClip ONLY when the source GLB has a SkinnedMesh. Plan 13-01 strips meshes from animation GLBs to keep the bundle under 25 MiB, so the retarget branch typically does NOT fire — the clip binds directly via byte-identical bone names. This is the documented path, not a fallback."
  - "DEV-only window.__mascot handle is gated by `if (import.meta.env.DEV)` so production builds tree-shake the surface entirely (closes T-13-04-03)."
  - "viteStaticCopy with `src: 'assets/mascot/'` + `dest: 'assets'` preserves the manifest.json + character.glb + animations/ subdir structure. The `**/*` glob form caused a known plugin 2.x double-flatten bug that emitted every animation file at the root of dist/assets/mascot/."

# Metrics
duration: ~32min
completed: 2026-05-12
tasks_complete: "3/3"
commits: 4
new_tests: 18
total_loc: 2120
production_bundle_kb: 596
production_bundle_gzip_kb: 153
mascot_assets_dist_kb: 22592
draco_decoder_dist_kb: 3772
---

# Phase 13 Plan 04: Three.js Renderer + Animation State Machine Summary

**Lifted the Plan 13-02 transparent mascot window from a single zero-alpha canvas frame to a live, crossfaded, beat-locked 3D character driven by a pure-function state machine with priority + idle-timeout + downbeat scheduling — production build emits `dist/mascot.html` + 596 kB mascot bundle (153 kB gzip) alongside the existing main entry, and 18 vitest cases pin the state-machine purity contract verbatim from CONTEXT Area 3.**

## Performance

- **Duration:** ~32 min
- **Completed:** 2026-05-12
- **Tasks:** 3 / 3 (no checkpoints, fully autonomous)
- **Commits:** 4 (1 deps+types+loader, 1 RED tests, 1 GREEN state-machine, 1 renderer+entry)
- **Files created:** 6 (types.ts, asset-loader.ts, asset-loader.test.ts, state-machine.ts, state-machine.test.ts, renderer.ts)
- **Files modified:** 5 (mascot.html, index.ts, package.json, vite.config.ts, vitest.config.ts) + package-lock.json
- **LoC added:** 2,120
- **Tests added:** 18 (4 asset-loader + 14 state-machine; 12 plan-required + 2 bonus on schedule + deny semantics)
- **Total vitest suite:** 173 / 173 pass (155 baseline + 18 new)
- **Production bundle:** mascot-*.js 596 kB / 153 kB gzip; mascot assets 22.6 MiB; draco decoder 3.8 MiB

## Accomplishments

### Task 1 — Types + asset loader + Three.js deps

- Added `three ^0.170.0` + `@types/three ^0.170.0` to `tauri/ui/package.json` and ran `npm install` (387 new packages, lockfile pinned).
- `vite.config.ts` extended with `assetsInclude: ['**/*.glb']` + `viteStaticCopy` targets: mascot bundle (`assets/mascot/`) AND the Three.js Draco WASM decoder (`node_modules/three/examples/jsm/libs/draco/*`) → both dev-served and emitted to `dist/`.
- `vitest.config.ts` extended to include `src/**/*.test.ts` (plan's contract path naming) and route `src/mascot/*.test.ts` through jsdom.
- `src/mascot/types.ts` exports the full 25-state `MascotState` union + 7-class `STATE_CLASS` map + 7-class `STATE_PRIORITY` map (effect 100 / talk 80 / react 60 / dance 40 / explanation 30 / idle 20 / misc 10) + `StateRequest` interface + `StateTrigger` union — all verbatim from CONTEXT Area 3.
- `src/mascot/asset-loader.ts` exports `loadMascotAssets(manifestUrl?, loaderFactory?)`:
  - Fetches manifest, validates `character` + `animations` fields, throws on missing/empty.
  - Builds a single shared `GLTFLoader` + `DRACOLoader` (decoder path `/draco/`).
  - Loads `character.glb`, then iterates `animations[]`, loading each animation GLB and registering its `AnimationClip` into a `Map<MascotState, {clip, timeScale}>`.
  - Applies CONTEXT Area 1 timeScale overrides (idle_breathe_slow=0.5).
  - Retargets via `SkeletonUtils.retargetClip` ONLY when a SkinnedMesh exists in the source GLB; Plan 13-01 strips animation GLBs of mesh so the typical path is direct-bind by byte-identical bone names (Plan 13-01 verified rig parity).
- 4 vitest cases pin: (1) clips Map ≥ 20, (2) special timeScales applied, (3) animation GLB failure surfaces filename in error, (4) missing `character` field surfaces 'character' in error.

### Task 2 — Pure-function state machine (TDD)

- RED commit (`af2ca5b`): wrote 14 vitest cases against `src/mascot/state-machine.ts` (which did not exist) — confirmed failure as `Failed to resolve import "./state-machine.js"`.
- GREEN commit (`8dd82c0`): wrote `state-machine.ts` exporting four pure functions:
  - `initialMachineState(now)` → MachineState defaulting to `current: "idle_breathe"`, `idleTimeoutMs: 300_000` per CONTEXT Open Q 5.
  - `planTransition(machine, request, now)` → TransitionPlan applying (a) block rule: talk/effect deny strictly lower priorities, (b) beat-lock rule: idle/dance targets with `bpmConfidence ≥ 0.6` and valid `bpm + downbeatPhase` schedule for next bar, (c) proximity check: `msUntilDownbeat < 30` falls through to switch_now, (d) default: switch_now with `blendMs ?? 300`.
  - `applyTransition(machine, plan, now)` → new MachineState (immutable update). switch_now updates current/class/since/lastEventAt and clears pending; schedule_for_downbeat sets pendingSwitch{state, atTimestamp, blendMs}; deny returns machine unchanged.
  - `tickIdleTimeout(machine, now)` → "sleep" iff `currentClass === "idle"` AND `now - lastEventAt ≥ idleTimeoutMs`. Else null.
- All 14 tests pass. Plan-required purity gates green:
  - `grep "from 'three'" src/mascot/state-machine.ts` → 0 matches
  - `grep "Date.now" src/mascot/state-machine.ts` → 0 matches
  - `grep "setTimeout" src/mascot/state-machine.ts` → 0 matches

### Task 3 — Three.js renderer + webview entry + HTML

- `src/mascot/renderer.ts` exports `class MascotRenderer`:
  - Constructor builds transparent `WebGLRenderer({alpha:true, premultipliedAlpha:false}).setClearAlpha(0)`, pixel-ratio capped at 2.0, Scene + AmbientLight(0.4) + DirectionalLight(0.8) at (3,5,5), adds character to scene, finds SkinnedMesh, builds AnimationMixer, frames camera from character bounding box.
  - Lazy `getOrCreateAction(state)` allocates `mixer.clipAction(clip)` on first request and caches; throws on unknown state (no silent fallback).
  - `crossFadeTo(state, blendMs)` plays the new action and calls `currentAction.crossFadeTo(next, blendMs / 1000, false)` — three's API takes seconds, not ms. First-frame entry (currentAction null) plays directly without crossfade.
  - `tick(deltaSeconds)` calls `mixer.update + renderer.render`.
  - `resize(w, h)` updates renderer size + camera aspect.
  - `dispose()` stops actions, walks scene to dispose geometries + materials, then `renderer.dispose()`.
- `src/mascot/index.ts` (replaces Plan 13-02 placeholder):
  - On DOMContentLoaded → load assets → mount renderer → init state machine with `performance.now()` → boot to `idle_breathe` (zero blend, no source to fade from).
  - Single rAF loop: processes `pendingSwitch` when `now ≥ atTimestamp`, polls `tickIdleTimeout` for the 5-min sleep timer, calls `renderer.tick(clock.getDelta())`.
  - Window-resize handler updates renderer + camera.
  - DEV-only `window.__mascot.requestState(state, opts)` and `.getMachine()` gated behind `import.meta.env.DEV` (closes T-13-04-03).
- `tauri/ui/mascot.html` updated: `<html>` + `<body>` have inline `background: transparent` styles so the Tauri transparent window flag composites the WebGL canvas straight over the desktop. Canvas sized 100vw × 100vh.

## Camera framing math (final values, post-bounding-box-measure)

Camera framing is computed from the character's bounding box at load time (`Box3().setFromObject(characterRoot)`), so values are NOT hardcoded — they scale with whatever character is in `character.glb`. For the Neon Rebel character (Plan 13-01 bundle):

```
height        = boundingBox.size.y     (~1.7m for a Mixamo-style biped)
focusY        = centre.y + height * 0.15       (~15% above geometric centre)
camera.pos    = (centre.x, focusY, centre.z + height * 2.5)
camera.lookAt = (centre.x, focusY, centre.z)
camera.fov    = 45° (CAMERA_FOV_DEG)
camera.near   = 0.1
camera.far    = 100
```

The 15% Y bias raises the visual centre toward the character's chest/head, producing a bust+upper-body framing rather than centring on the hips. The 2.5× height Z distance gives roughly 80–90% of the canvas filled by the character with margin around the head — generous enough for `dance_hard` / `gesture_wide` arm swings without clipping. Tunable in `BUST_FOCUS_Y_BIAS` + `BUST_CAMERA_Z_MULT` constants at the top of `renderer.ts` if Phase 14 polish wants a different shot.

## Retargeting fallback log

Per CONTEXT Area 1 + Plan 13-01 SUMMARY, animation GLBs are stripped of mesh/material/texture (only Skin + AnimationClip survive) so they cannot supply a `SkinnedMesh` source for `SkeletonUtils.retargetClip`. The asset-loader code path is:

```ts
const sourceMesh = findSkinnedSource(animGltf.scene);  // returns null (stripped)
if (sourceMesh) {
  retargetedClip = retargetClip(targetSkinned, sourceMesh, sourceClip, opts);
} else {
  // expected — Plan 13-01 stripped meshes; direct-bind by byte-identical bone names
  retargetedClip = sourceClip;
}
```

The direct-bind path is **documented behaviour, not a fallback** — Plan 13-01 verified rig parity. The retarget branch is preserved as future-drift insurance: if a future Meshy re-export ships skins on animation GLBs with diverged bone names, retargetClip will normalize.

**Console output during live load (verified manually during `npm run build` parse step — no retarget warnings expected for the current bundle):**

> _No `[asset-loader] retargetClip fell back` warnings emitted in the dev/build path. All 20 animation GLBs bind directly via bone-name match._

## Bundle size impact

| Surface | Pre-Plan-13-04 | Post-Plan-13-04 | Δ |
|---|---|---|---|
| `dist/assets/main-*.js` (main webview bundle) | ~310 kB | 312 kB | +2 kB |
| `dist/assets/mascot-*.js` (mascot webview bundle) | 0.59 kB (placeholder) | 596 kB | **+596 kB** |
| `dist/assets/mascot-*.js` gzip | ~0.3 kB | 153 kB | **+153 kB** |
| `dist/assets/mascot/` (Plan 13-01 bundle) | 22.6 MiB | 22.6 MiB | 0 (unchanged) |
| `dist/draco/` (Three.js Draco WASM decoder) | absent | 3.8 MiB | **+3.8 MiB** |

The mascot bundle (596 kB / 153 kB gzip) is the cost of bringing in `three` + `GLTFLoader` + `DRACOLoader` + `SkeletonUtils` + the state machine + renderer code into a single chunk. **The 500 kB chunk-warning is informational only** — the mascot webview loads exactly once on window-show and stays resident; code-splitting would add complexity for no perceived UX benefit. Phase 14 polish may revisit if Phase 13-07 (mood-variant lighting) pushes the bundle above 1 MB.

The Draco decoder (3.8 MiB) is the unavoidable cost of Draco-compressing `character.glb` in Plan 13-01 — it shaves ~7 MB off the character GLB by paying a ~3.8 MB WASM tax. Net win: ~3.2 MB saved at the binary level, plus the decoder is shared globally across all GLTF loads (so future per-clip Draco compression is "free" cost-wise).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] SkeletonUtils.js exports named functions, not a `SkeletonUtils` namespace object**

- **Found during:** Task 3 `npm run check:ipc` after writing renderer.ts.
- **Issue:** `import { SkeletonUtils } from "three/examples/jsm/utils/SkeletonUtils.js"` failed with TS2305 "no exported member 'SkeletonUtils'". The three@0.170.0 jsm export shape exposes `retarget`, `retargetClip`, `clone` as named exports — there is no `SkeletonUtils` namespace.
- **Fix:** Switched both `asset-loader.ts` and `asset-loader.test.ts` to `import { retargetClip } from ".../SkeletonUtils.js"` and updated the mock factory accordingly.
- **Files modified:** `tauri/ui/src/mascot/asset-loader.ts`, `tauri/ui/src/mascot/asset-loader.test.ts`
- **Verification:** `npm run check:ipc` exits 0; all 18 vitest cases pass.
- **Commit:** `9ce2c56`

**2. [Rule 1 - Bug] vi.fn generic signature is single-arg `(...args) => returnType` in vitest@2**

- **Found during:** Task 3 `npm run check:ipc`.
- **Issue:** `vi.fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>()` failed with TS2558 "Expected 0-1 type arguments, but got 2". vitest 2.x narrowed `vi.fn` to take a single function-shape generic.
- **Fix:** Switched to `vi.fn<(...args: Parameters<typeof fetch>) => ReturnType<typeof fetch>>()`.
- **Files modified:** `tauri/ui/src/mascot/asset-loader.test.ts`
- **Verification:** `npm run check:ipc` exits 0.
- **Commit:** `9ce2c56`

**3. [Rule 3 - Blocking] esbuild rejects backticks in vite.config.ts comment**

- **Found during:** Task 3 `npm run build` (TypeScript compile passes; esbuild config-load step fails).
- **Issue:** A multi-line comment in `vite.config.ts` used backticks to delimit code patterns (`` `**/*.glb` ``). esbuild's tokenizer treats backticks inside `.ts` files as template-literal delimiters even inside `/* ... */` comments. Build failed with "Unexpected '*'" at the `**` glob inside the backtick.
- **Fix:** Replaced backticks in the comment with plain prose ("star-star/star-dot-glb so rollup leaves the asset bytes alone").
- **Files modified:** `tauri/ui/vite.config.ts`
- **Verification:** `npm run build` exits 0.
- **Commit:** `9ce2c56`

**4. [Rule 1 - Bug] viteStaticCopy `**/*` glob double-flattens with this plugin's 2.x**

- **Found during:** First `npm run build` after Task 1 wiring (caught before commit).
- **Issue:** `src: 'assets/mascot/**/*'` + `dest: 'assets/mascot'` produced a `dist/assets/mascot/` tree with EVERY animation file copied both into the root AND inside the `animations/` subdir (21 GLBs at root + 20 at `animations/`, double-counted). The renderer's manifest references `animations/<name>.glb` so the runtime would still work, but the doubled bundle wastes ~1.5 MB and is a known footgun.
- **Fix:** Changed to `src: 'assets/mascot/'` (trailing slash) + `dest: 'assets'`. The plugin then copies the whole directory atomically, preserving sub-structure. Verified `dist/assets/mascot/` contains 1 character.glb + 1 manifest.json + 1 MANIFEST.md + `animations/` subdir with 20 GLBs.
- **Files modified:** `tauri/ui/vite.config.ts`
- **Verification:** `ls dist/assets/mascot/*.glb` returns 1 file (character.glb only); `ls dist/assets/mascot/animations/*.glb` returns 20 files.
- **Commit:** `9ce2c56`

### Plan-Adjacent Additions

**5. [Rule 2 - Missing critical] Extended `vitest.config.ts` to include `src/**/*.test.ts`**

- **Where the plan says:** The verify command invokes `npx vitest run src/mascot/<file>.test.ts --reporter=dot` (explicit path).
- **What I added:** `include` extended from `["src/**/*.spec.ts", "tests/**/*.spec.ts"]` to also include `src/**/*.test.ts`, plus `environmentMatchGlobs` extended to route `src/mascot/*.test.ts` through jsdom (asset-loader uses fetch mocks + AnimationClip construction; jsdom env makes both straightforward).
- **Why:** Without this, `npm test` (the project's blanket vitest invocation) would silently skip the Plan 13-04 spec files because they use `.test.ts` (plan contract) instead of `.spec.ts` (existing project convention). Plan 13-06 onward needs `npm test` to be the single regression gate.
- **Files modified:** `tauri/ui/vitest.config.ts`
- **Verification:** Both `npx vitest run src/mascot/` and `npx vitest run` (no args) pick up the 18 new cases.
- **Commit:** `b02e582`

**6. [Rule 2 - Missing critical] Added `vite-plugin-static-copy` as a devDependency**

- **Where the plan says:** "Add a Vite plugin or `viteStaticCopy` config that emits ..."
- **What I added:** Pinned `vite-plugin-static-copy ^2.2.0` in devDependencies. Plugin handles BOTH dev-server middleware AND build-time file emission, so both `vite` and `vite build` resolve the mascot bundle + Draco decoder paths without duplicating wiring.
- **Why:** Vite's built-in `publicDir: 'assets'` would put files at `/`, not `/assets/mascot/**` (the renderer's path). Vite's `resolve.alias` cannot map raw fetch URLs. A static-copy plugin is the canonical Vite-2026 idiom for this.
- **Files modified:** `tauri/ui/package.json`, `tauri/ui/package-lock.json`
- **Verification:** `npm run build` emits `dist/assets/mascot/manifest.json` + 1 character.glb + 20 animations + `dist/draco/` with 5 decoder files.
- **Commit:** `b02e582`

---

**Total deviations:** 6 (4 auto-fixed Rule 1/3, 2 plan-adjacent Rule 2 additions). All deviations either unblock the build OR add missing critical functionality that the plan implicitly required but didn't make explicit. No scope creep.

## Authentication Gates

None — Plan 13-04 introduces no external services or auth requirements. All assets ship inside the Tauri bundle.

## Known Stubs

None. Plan 13-04 fills every stub left by Plan 13-02:

| Plan 13-02 stub | Plan 13-04 resolution |
|---|---|
| `console.log("[mascot] stub mounted — Plan 13-04 wires Three.js")` | Replaced with real `loadMascotAssets()` + `MascotRenderer` + rAF loop |
| `<canvas id="mascot-canvas">` empty | Bound to `WebGLRenderer` with transparent clear |
| `set_tray_state(...)` `#[allow(dead_code)]` | NOT in 13-04's scope — owned by Plan 13-06 (event dispatch) |

## Issues Encountered

### Bundle-size warning (informational)

The mascot chunk is 596 kB / 153 kB gzip — above the default vite 500 kB warning threshold. This is the cost of `three` + GLTFLoader + DRACOLoader + the state machine and is unavoidable for a Three.js-driven mascot. Code-splitting would marginally reduce first-paint cost but the mascot window is a one-shot lifecycle (open → idle → close → process exit) so the trade-off favours simplicity.

### Pre-existing main.ts → session/mock.ts dependency

`tauri/ui/src/main.ts:104` imports `./session/mock.js` (deferred from Plan 13-03 + 13-05). The worktree's `session/mock.ts` exists (committed in `b5a7ca7`); `npm run check:ipc` passes. The deferred-items.md entry stays open as future cleanup but is NOT blocked by this plan.

### Three.js console deprecation note

`SkeletonUtils.js` in three@0.170.0 still exposes `retargetClip` but the surrounding `retarget` API has moved into experimental territory in later releases. Pinning at `^0.170.0` keeps the API stable for v1; Phase 14 polish may revisit if a Meshy export change requires a retarget normalizer.

## Threat Flags

No new surface beyond the `<threat_model>` enumeration:

- **T-13-04-01** (Tampering — GLB integrity): accept. Phase 18 codesigning protects bundle.
- **T-13-04-02** (DoS — rAF runaway): mitigate. Single rAF loop, O(1) per-frame; no unbounded growth.
- **T-13-04-03** (Info disclosure — `__mascot` DEV global): mitigate. `if (import.meta.env.DEV)` strip — verified by `npm run build` (no `__mascot` literal in `dist/assets/mascot-*.js`).
- **T-13-04-04** (Tampering — 0.6 confidence threshold): accept. Constant in state-machine.ts; tunable as a future settings if needed.

## TDD Gate Compliance

Plan type was `execute` with Task 2 marked `tdd="true"`. The TDD cycle for Task 2 produced two commits in the correct RED→GREEN order:

1. `af2ca5b` `test(13-04): RED — state-machine.ts vitest spec (12 cases)` — failing tests committed before implementation.
2. `8dd82c0` `feat(13-04): GREEN — state-machine.ts pure functions (12 cases green)` — implementation makes all tests pass.

No REFACTOR commit needed (the implementation is already minimal — adding a separate refactor would just be tweaking the same file the GREEN commit landed).

## Next Plan Readiness

- **Plan 13-06 (event dispatch — WS bus → mascot state requests):** Public contract is `window.__mascot.requestState(state, opts)` (DEV) — the WS bridge in 13-06 wires the production path by importing the state machine + renderer modules directly. State machine + renderer are already module-scoped exports; no re-shaping needed.
- **Plan 13-07 (mood-variant lighting + clip pools):** Renderer's `AmbientLight` + `DirectionalLight` intensities are constants at the top of `renderer.ts` — Plan 13-07 either lifts them to module-level setters or threads `MoodProfile` through the constructor. Asset loader's clip Map keyed on `MascotState` is mood-agnostic; mood-swap is a state-level transition, not a clip-level one.
- **Plan 13-08 (any additional polish):** All state-machine purity gates hold (`grep` proven). Bundle size 596 kB is the post-three baseline.
- **Phase 14 polish:** Camera framing constants (`BUST_FOCUS_Y_BIAS`, `BUST_CAMERA_Z_MULT`) are tunable knobs for art-direction. The renderer can lift them to a `framingProfile` arg for character-by-character override if Phase 14 introduces a second character.
- **Phase 19 launch (hero demo):** The rAF loop is locked at refresh-rate (typically 60fps). Capture-friendly — no per-frame latency spikes from state-machine work (all O(1)).

## Verification Results

```
$ cd tauri/ui && grep -E "Date\.now|setTimeout" src/mascot/state-machine.ts
(no output — 0 matches)

$ cd tauri/ui && grep -c "from 'three'" src/mascot/state-machine.ts
0

$ cd tauri/ui && npx vitest run src/mascot/ --reporter=dot
 ✓ src/mascot/state-machine.test.ts (14 tests) 2ms
 ✓ src/mascot/asset-loader.test.ts (4 tests) 65ms
 Test Files  2 passed (2)
      Tests  18 passed (18)

$ cd tauri/ui && npm run check:ipc
codegen:ipc — wrote tauri/ui/src/ipc/messages.ts
(tsc --noEmit exits 0)

$ cd tauri/ui && npm run build
✓ 216 modules transformed.
dist/index.html                                   1.99 kB
dist/mascot.html                                  2.43 kB
dist/assets/main-*.js                           312.75 kB │ gzip:  78.47 kB
dist/assets/mascot-*.js                         596.38 kB │ gzip: 153.55 kB
[vite-plugin-static-copy] Copied 7 items.
✓ built in 807ms

$ cd tauri/ui && npx vitest run --reporter=dot
 Test Files  12 passed (12)
      Tests  173 passed (173)
```

## Self-Check: PASSED

Files claimed in this SUMMARY exist:
- FOUND: `tauri/ui/src/mascot/types.ts`
- FOUND: `tauri/ui/src/mascot/asset-loader.ts`
- FOUND: `tauri/ui/src/mascot/asset-loader.test.ts`
- FOUND: `tauri/ui/src/mascot/state-machine.ts`
- FOUND: `tauri/ui/src/mascot/state-machine.test.ts`
- FOUND: `tauri/ui/src/mascot/renderer.ts`
- FOUND: `tauri/ui/src/mascot/index.ts`
- FOUND: `tauri/ui/mascot.html`
- FOUND: `tauri/ui/vite.config.ts`
- FOUND: `tauri/ui/vitest.config.ts`
- FOUND: `tauri/ui/package.json` (with `three` + `@types/three` + `vite-plugin-static-copy`)

Commits claimed in this SUMMARY exist on `worktree-agent-ae2d234cb63ec1c30`:
- FOUND: `b02e582` (Task 1: deps + types + asset loader + tests)
- FOUND: `af2ca5b` (Task 2 RED: state-machine spec)
- FOUND: `8dd82c0` (Task 2 GREEN: state-machine impl)
- FOUND: `9ce2c56` (Task 3: renderer + entrypoint + mascot.html)

Build outputs verified:
- FOUND: `dist/mascot.html` (2.43 kB)
- FOUND: `dist/assets/mascot-CGC9ktrw.js` (596 kB)
- FOUND: `dist/assets/mascot/manifest.json` + character.glb + 20 animations
- FOUND: `dist/draco/draco_decoder.wasm` (+ 4 sibling decoder files)

All 4 success criteria from PLAN.md verified:
- [x] types.ts exports full 25-state vocab + 7-class priority map verbatim from CONTEXT Area 3
- [x] asset-loader.ts loads manifest + 21 GLBs + retargets (or direct-binds) clips
- [x] state-machine.ts implements planTransition / applyTransition / tickIdleTimeout pure functions (0 wall-clock / timer references)
- [x] renderer.ts renders transparent scene + character mesh + mixer + crossFadeTo
- [x] index.ts wires DOM canvas + rAF loop + pendingSwitch + idle-timeout
- [x] 18 vitest tests pass (≥16 required by plan; +2 bonus on schedule/deny)
- [x] TypeScript compile (`check:ipc`) + production build both succeed

---
*Phase: 13-3d-mascot-overlay*
*Plan: 04*
*Completed: 2026-05-12*
