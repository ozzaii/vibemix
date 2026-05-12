---
phase: 13-3d-mascot-overlay
plan: 01
subsystem: ui
tags: [mascot, gltf, draco, gltf-transform, gltf-pipeline, three.js, meshy, asset-pipeline, tauri]

requires:
  - phase: 11-tauri-shell
    provides: tauri/ui Node project, package.json + lockfile, scripts/ pattern
provides:
  - 21-asset Neon Rebel mascot bundle at tauri/ui/assets/mascot/ (22.4 MiB)
  - Idempotent build script (npm run build:mascot) for refreshing Meshy assets
  - Clip-name → state-vocab manifest.json contract consumed by Plan 13-04 renderer
  - Meshy AI attribution in LICENSE-3RD-PARTY.md
affects: [13-02, 13-03, 13-04, 13-05, 13-06, 14-polish, 19-launch]

tech-stack:
  added:
    - gltf-pipeline ^4.1.0 (Draco-compress character GLB)
    - "@gltf-transform/cli ^4.0.0 (CLI surface, npx fallback)"
    - "@gltf-transform/core ^4.0.0 (programmatic strip via NodeIO)"
  patterns:
    - "Asset bundle build script — committed output, manual regen only (no CI step)"
    - "Programmatic GLB strip via @gltf-transform/core NodeIO — drop Mesh/Material/Texture, keep Skin + Animation"
    - "Idempotency-first compression pipeline — same inputs + same tool versions = byte-identical outputs"

key-files:
  created:
    - tauri/ui/scripts/build-mascot-bundle.mjs
    - tauri/ui/assets/mascot/character.glb
    - tauri/ui/assets/mascot/animations/ (20 single-clip GLBs)
    - tauri/ui/assets/mascot/manifest.json
    - tauri/ui/assets/mascot/MANIFEST.md
  modified:
    - tauri/ui/package.json
    - tauri/ui/package-lock.json
    - tauri/ui/LICENSE-3RD-PARTY.md
    - .gitignore

key-decisions:
  - "Character: Draco compressionLevel=10, quantize{Position=14, Normal=10, Texcoord=12} — readable-quality sweet spot, 25.1% reduction (27.7 MB → 20.7 MB)"
  - "Animations: programmatic strip via @gltf-transform/core NodeIO instead of gltf-transform prune (prune only removes unreferenced nodes; meshes were scene-referenced and survived)"
  - "No Draco on animation GLBs after stripping — payload is already tiny (30-185 KB each), Draco gain marginal vs. Three.js load cost"
  - "Animation GLBs stripped of mesh/material/texture; only Skin + Animation tracks retained — Three.js retargets clips onto character.glb skeleton at load (Plan 13-04)"
  - "Build script is manual-only (no install-time hook) — honors one-click install hard requirement; Meshy source GLBs live in Kaan-local Downloads, not in repo"
  - "Bundle whitelist in .gitignore (!tauri/ui/assets/mascot/**) — defensive against future generic-glob ignore additions"

patterns-established:
  - "Single-source asset bundle: committed compressed output IS the source of truth for CI; raw Meshy assets are dev-only"
  - "ES-module Node build scripts under tauri/ui/scripts/ resolve CLIs from node_modules/.bin first, npx fallback (matches codegen-ipc.mjs)"
  - "Per-clip metadata in manifest.json carries both clip name (Three.js AnimationClip lookup) and abstract state labels (state-machine vocabulary)"

requirements-completed: [MASCOT-01]

duration: 33min
completed: 2026-05-12
---

# Phase 13 Plan 01: Mascot Asset Bundle Pipeline Summary

**Compressed 21 raw Meshy GLBs (583 MiB → 22.4 MiB, 96.2% reduction) into a shippable mascot bundle via Draco character compression + programmatic strip of mesh/material/texture from animation GLBs, with a deterministic `npm run build:mascot` script for regeneration.**

## Performance

- **Duration:** ~33 min
- **Completed:** 2026-05-12
- **Tasks:** 2 / 2
- **Files created:** 23 (1 script + 21 bundle assets + MANIFEST.md)
- **Files modified:** 4 (package.json, package-lock.json, LICENSE-3RD-PARTY.md, .gitignore)
- **Bundle size:** 22,463,172 bytes / 26,214,400 cap (85.7%)
- **Compression ratio:** 96.2% overall

## Accomplishments

- 21 mascot assets committed at `tauri/ui/assets/mascot/` (1 character + 20 single-clip animation GLBs + manifest.json + MANIFEST.md report)
- Deterministic, idempotent build script that takes the Meshy raw export at `MESHY_SRC_DIR` and produces byte-identical output on every run (verified via md5 round-trip)
- Locked Draco quantization knobs documented in the script header + MANIFEST.md so future re-runs against refreshed Meshy assets produce the same compression profile
- Clip-name → state-vocab map landed in `manifest.json` matching the canonical Area 1 schema from `13-CONTEXT.md` exactly — Plan 13-04 renderer + Plan 13-03 state machine consume this contract directly
- Meshy AI attribution block added to `LICENSE-3RD-PARTY.md` (Kaan-owned generated content per Meshy ToS, no SHA pinning required)
- `.gitignore` defensively whitelists the bundle path + ignores the `.mascot-build-tmp/` scratch dir

## Task Commits

Each task was committed atomically:

1. **Task 1: Author build-mascot-bundle.mjs + register npm script** — `42a9363` (feat)
2. **Task 2: Run bundle once + commit produced artifacts + record sizes** — `c4424c6` (feat)

## Files Created/Modified

- `tauri/ui/scripts/build-mascot-bundle.mjs` — ES-module Node script: Draco-compresses character.glb, programmatically strips mesh/material/texture from each animation GLB via `@gltf-transform/core` NodeIO, writes `manifest.json`, enforces 25 MiB bundle cap
- `tauri/ui/assets/mascot/character.glb` (20,747,776 B) — Draco-compressed base mesh + texture, biped skeleton
- `tauri/ui/assets/mascot/animations/{sleep_normally,indoor_swing,bass_beats,funny_dancing_01,funny_dancing_03,omg_groove,all_night_dance,hip_hop_dance_3,magic_genie,cheer_both_hands,shrug,not_your_mom,alert_quick_turn,handbag_walk,big_wave_hello,wave_for_help,fast_lightning,angry_stomp,walking,running}.glb` — 20 single-clip GLBs (29 KB to 184 KB each), skeleton + AnimationClip only
- `tauri/ui/assets/mascot/manifest.json` (3,064 B) — clip → state-vocab map, character pointer, bundle target metadata
- `tauri/ui/assets/mascot/MANIFEST.md` — per-file source-vs-compressed table, locked Draco flags, reproducibility instructions
- `tauri/ui/package.json` — added devDependencies `gltf-pipeline ^4.1.0`, `@gltf-transform/cli ^4.0.0`, `@gltf-transform/core ^4.0.0`; registered `npm run build:mascot` script
- `tauri/ui/package-lock.json` — locks the full transitive tree (359 new packages) for reproducible regeneration
- `tauri/ui/LICENSE-3RD-PARTY.md` — appended Meshy AI Neon Rebel attribution block
- `.gitignore` — added `tauri/ui/.mascot-build-tmp/` ignore + `!tauri/ui/assets/mascot/**` defensive whitelist

## Decisions Made

- **gltf-transform `prune` CLI is insufficient.** It only removes scene-unreferenced properties; the mesh in each animation GLB IS referenced by a Node attached to the scene root, so `prune` left every mesh + texture + material untouched (output was identical to input modulo dedup). Switched to programmatic `@gltf-transform/core` `NodeIO`: open the document, call `setMesh(null)` on every node, then `dispose()` every Mesh / Material / Texture, then orphan-cleanup accessors, then write. Result: 99.6-99.9% reduction per animation file.
- **No Draco on stripped animation GLBs.** After stripping mesh + texture, each animation file is 30-185 KB — predominantly the animation sampler input/output accessors (joint rotations as quaternions, joint translations as vec3). Draco-compressing these saved ~5-10 KB per file at the cost of a Draco decoder load at render time. Net win is marginal; left uncompressed for simplicity. Draco was retained for the character GLB where it shaves 7 MB off the mesh + texture payload.
- **Bundle whitelist over commit-time enforcement.** Considered a pre-commit hook that rejects commits exceeding 25 MiB. Rejected: pre-commit hooks slow every developer; the build script's own cap-enforcement at `enforceBundleCap()` is sufficient — if compression silently regresses, the script exits non-zero before anyone commits.
- **Manual-only regeneration.** Per CLAUDE.md scope rule + `project_one_click_install_hard_req`, the bundle build is NOT chained into `npm install` or `npm run build`. CI consumes the committed `tauri/ui/assets/mascot/` tree; only maintainers running against the Kaan-local Meshy export trigger `npm run build:mascot`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Replaced gltf-transform CLI prune+dedup with programmatic @gltf-transform/core strip**
- **Found during:** Task 2 (running the bundle)
- **Issue:** The plan specified `gltf-transform prune` + `gltf-transform dedup` to drop mesh/material/texture from animation GLBs. In practice, `prune` only removes properties unreferenced by a Scene, and the source meshes ARE referenced by Nodes in the scene root — so prune left the meshes (and textures, 8.96 MB each) intact. Bundle would have blown past the 25 MiB cap by an order of magnitude.
- **Fix:** Rewrote the animation pipeline to use `@gltf-transform/core` `NodeIO` programmatically: open the doc, `setMesh(null)` on every node to detach mesh refs, then `dispose()` every Mesh/Material/Texture, then orphan-cleanup unreferenced accessors. Added `@gltf-transform/core` to direct devDependencies (it was only available transitively before, which would have made the import brittle).
- **Files modified:** `tauri/ui/scripts/build-mascot-bundle.mjs`, `tauri/ui/package.json`
- **Verification:** Bundle dropped to 21.5 MiB total; each animation GLB is now 30-185 KB instead of ~28 MB. Three.js `GLTFLoader` will still find the `AnimationClip` since `Animation` properties were never touched.
- **Committed in:** c4424c6 (Task 2 commit)

**2. [Rule 2 - Missing Critical] Added @gltf-transform/core as direct devDependency**
- **Found during:** Task 2 (programmatic strip rewrite)
- **Issue:** The script imports `@gltf-transform/core` directly via `import { NodeIO } from "@gltf-transform/core"`. The package was only present as a transitive dep of `@gltf-transform/cli`. A future cli upgrade could drop it without warning, silently breaking the build script.
- **Fix:** Added `"@gltf-transform/core": "^4.0.0"` to `tauri/ui/package.json` devDependencies.
- **Files modified:** `tauri/ui/package.json`, `tauri/ui/package-lock.json`
- **Verification:** `npm install` resolves it as a top-level dep; `import` works; script runs end-to-end.
- **Committed in:** c4424c6 (Task 2 commit, alongside the script rewrite)

**3. [Rule 2 - Missing Critical] Added .mascot-build-tmp/ ignore**
- **Found during:** Task 1 (.gitignore edit)
- **Issue:** Initial script design used a scratch tmp dir for intermediate stripped GLBs. Without a `.gitignore` entry, leftover scratch files would be visible in `git status` if a build was interrupted.
- **Fix:** Added `tauri/ui/.mascot-build-tmp/` to `.gitignore` alongside the `!tauri/ui/assets/mascot/**` whitelist line. (After the programmatic-strip rewrite, the tmp dir is no longer used — but the ignore line stays as a safety net for any future tmp-using build phase.)
- **Files modified:** `.gitignore`
- **Verification:** `git status` shows no untracked tmp files after build.
- **Committed in:** 42a9363 (Task 1 commit)

---

**Total deviations:** 3 auto-fixed (1 bug, 2 missing critical)
**Impact on plan:** All auto-fixes essential for correctness. The CLI `prune` failure would have made the plan unfulfillable as written; the rewrite is a strict superset of what the plan required (same inputs, same output paths, same manifest, just a different stripping mechanism). No scope creep.

## Issues Encountered

- Every animation GLB read produced two warnings: `Missing optional extension, "KHR_materials_specular"` and `KHR_materials_ior`. These are PBR material extensions that the source Meshy GLBs declare in `extensionsUsed` but our installed `@gltf-transform/core` Extensions module doesn't ship handlers for. Safe to ignore — materials are removed by the strip step regardless. Documented in MANIFEST.md.

## User Setup Required

None — no external service configuration required. The committed `tauri/ui/assets/mascot/` tree is everything Phase 13's downstream plans (renderer + state machine) need. Only Kaan-as-maintainer ever re-runs `npm run build:mascot`, and only when refreshing Meshy outputs.

## Next Phase Readiness

- **Plan 13-02 (Tauri overlay window + tray plugin):** Ready. No asset dependency.
- **Plan 13-03 (state machine):** Ready. Will read `manifest.json` `.animations[].states` to build the WS-event → clip-name routing table.
- **Plan 13-04 (Three.js renderer):** Ready. Loads `character.glb` via `GLTFLoader`, iterates `manifest.json` `.animations[]`, loads each animation GLB, extracts its single `AnimationClip`, retargets onto the character skeleton via `SkeletonUtils.retargetClip`, and registers in the `AnimationMixer`.
- **Plan 13-05/06 (overlay UI + tray):** Ready. No asset dependency until Plan 13-04 wires up the renderer.
- **Phase 14 (polish):** MANIFEST.md table makes per-clip compression visible — if any clip needs higher fidelity (e.g., dance_hard looks janky), the Draco flags + strip aggression are knobs at the top of the script.

## Self-Check: PASSED

Files created exist:
- `tauri/ui/scripts/build-mascot-bundle.mjs` — FOUND
- `tauri/ui/assets/mascot/character.glb` — FOUND (20,747,776 bytes)
- `tauri/ui/assets/mascot/animations/*.glb` — FOUND (20 files)
- `tauri/ui/assets/mascot/manifest.json` — FOUND (3,064 bytes, parses as valid JSON, 20-entry animations array)
- `tauri/ui/assets/mascot/MANIFEST.md` — FOUND

Commits exist:
- `42a9363` — FOUND (Task 1: build script + deps + .gitignore)
- `c4424c6` — FOUND (Task 2: built bundle + script rewrite + lockfile + LICENSE)

Bundle cap held: 21,992 KB ≤ 25,600 KB ✓
Idempotency verified: md5 round-trip 2026-05-12 — second run produced byte-identical output ✓
LICENSE-3RD-PARTY.md contains Meshy AI block ✓

---
*Phase: 13-3d-mascot-overlay*
*Completed: 2026-05-12*
