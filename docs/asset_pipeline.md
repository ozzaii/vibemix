# Asset Pipeline — Mascot GLBs (Phase 35)

Source-of-truth for how the 5 `prep_*.glb` mascot animation clips (and
any future Phase 35 additions) get produced, optimized, and shipped.

This doc is doctrine — it does not run by itself. The runnable pieces
live in:

- `scripts/glb_optimize.py` — DRACO L7 + KTX2 batch + per-clip/total
  budget enforcement.
- `tests/repo/test_mascot_glb_size_gate.py` — total-budget regression
  test (Phase 31 carry-forward).
- `tests/scripts/test_glb_optimize.py` — per-clip + total tests.
- `scripts/check_mascot_glb_size.sh` — shell-side total gate.

---

## 1. Generate base model — Meshy v6 vs Hunyuan3D 3.0

Pick ONE of:

### Option A — Meshy v6 (paid, ~$30 for 6-8 iterations)

1. Account: meshy.ai. ~$30 in credits for v6 generation rounds.
2. Prompt: see `mocks/vibemix-direction-final.html` mascot description —
   "single VTuber-style character, single mascot direction, mood
   variation on same rig". Reference: existing `character.glb` silhouette.
3. Output: GLB with PBR textures.

### Option B — Hunyuan3D 3.0 (paid via fal.ai, ~$20 for 4-5 iterations)

1. Account: fal.ai. ~$20 in credits.
2. Same prompt + reference as Meshy.
3. Output: GLB with PBR textures.

### A/B decision rule

Generate ONE shot from each. Compare on:
- Silhouette readability at 320×320 (typical overlay surface).
- Bone topology (Mixamo auto-rigging works best on humanoid biped
  topology with clean elbow/knee bends).
- Texture density (KTX2 transcoding is more lossy on noisy textures).

Pick the winner. Hash-cache its source GLB to
`tauri/ui/assets/mascot/raw/` (gitignored — keeps the per-iteration
exploration out of git history).

Tracked Kaan-action: `KAAN-ACTION-LEGAL.md` `ASSETS-MESHY-A/B`.

---

## 2. Auto-rig — Mixamo (free with Adobe account)

1. mixamo.com → Upload Character → upload the GLB picked in step 1.
2. Place rig markers (chin, wrists, elbows, knees, groin) — Mixamo
   guides this with click-to-place hints.
3. Auto-rig: ~30s server-side processing.
4. Download character + rigging as `character_rigged.glb`.

### Selecting motion clips (8-12 total)

Browse Mixamo motion library. The 5 prep_* placeholders Phase 22 defined
must map to real anticipations:

| State                    | Mixamo search             | Notes                                 |
|--------------------------|---------------------------|---------------------------------------|
| `prep_lean_in_neutral`   | "Looking Around" / "Listening" | mid-confidence anticipation     |
| `prep_lean_in_hyped`     | "Excited Cheer" (trimmed) | high-energy anticipation              |
| `prep_head_turn_left`    | "Quick Turn Head Left"    | direction prep                        |
| `prep_head_turn_right`   | "Quick Turn Head Right"   | direction prep                        |
| `prep_settle`            | "Idle Shift" / "Standing" | settle-back-into-base prep            |

For each clip:
- Trim to 0.8-1.5s (the additive layer blends in/out over 0.1-0.3s).
- "In Place" enabled (no translation — additive layer adds on top of
  base position).
- Download as Without Skin (re-uses the character_rigged.glb skin).

Tracked Kaan-action: `KAAN-ACTION-LEGAL.md` `ASSETS-MIXAMO-RIG`.

### Rokoko fallback (Pitfall P61)

Mixamo auto-rig occasionally produces broken IK — drifting bones, foot
sliding, hand penetration. If `SkeletonHelper` QA (see step 3) flags any
of these:

1. Sign up for Rokoko Studio (free for first month, ~$5/mo after).
2. Retarget Mixamo motion onto a Rokoko-rigged skeleton via Rokoko's
   retargeting tool.
3. Re-export as GLB.

---

## 3. SkeletonHelper QA — Three.js dev shell visual

For each clip:

1. Open `tauri/ui/` dev shell.
2. Load the clip into the existing mascot renderer.
3. Add `new THREE.SkeletonHelper(mesh)` to the scene.
4. Play the clip in loop.
5. Visually verify:
   - No bone drift (bones don't slide off the mesh).
   - No foot-floor penetration during idle.
   - No hand-body intersection on prep_lean_*.
   - Spine doesn't pop on loop boundary.

If any fail → return to Rokoko retargeting (step 2 fallback).

---

## 4. Optimize — gltfpack DRACO L7 + KTX2

```bash
python scripts/glb_optimize.py --optimize \
    tauri/ui/assets/mascot/raw/ \
    tauri/ui/assets/mascot/animations/
```

This shells out to:

```bash
gltfpack -i <src> -o <dst> -cc -tc -tq 8
```

- `-cc` = meshopt compression (Khronos KHR_mesh_quantization +
  EXT_meshopt_compression).
- `-tc` = KTX2 texture transcoding.
- `-tq 8` = texture quality (8 = good; 4 = small; 10 = max).

The script then re-runs `--check` on the output dir + asserts:
- per-clip ≤ 600 KB (Pitfall P52 sub-budget).
- total ≤ 25 MB (Pitfall P52 sub-budget; Phase 31 carry-forward).

`character.glb` (the rig mesh, ~20 MB DRACO-compressed) is excluded
from the per-clip cap but counts toward the total.

### gltfpack install

```bash
npm install -g gltfpack          # any platform
# or
brew install meshoptimizer       # macOS
```

---

## 5. Replace placeholders — drop into repo

```bash
cp <optimized clips> tauri/ui/assets/mascot/animations/
```

Filenames MUST match the existing 5 `prep_*.glb` paths — they're
referenced by `tauri/ui/assets/mascot/manifest.json`. The manifest is
the contract surface; the placeholder filenames ARE the future-real
filenames.

After drop:

```bash
./scripts/check_mascot_glb_size.sh                # total <= 25 MB
python scripts/glb_optimize.py --check \
    tauri/ui/assets/mascot/                       # per-clip + total
cd tauri/ui && npm test -- additive-layer        # Phase 22-02 contract
```

All three must pass before commit.

Tracked Kaan-action: `KAAN-ACTION-LEGAL.md` `ASSETS-PREP-REPLACE`.

---

## 6. Per-state Phase 22-02 idle-zero invariant

The 5 prep_* clips MUST preserve the idle-zero lower-body delta — at
`t=0` after `AnimationUtils.makeClipAdditive`, the lower-body bone
deltas (hip + knees + feet) must be ~0 so the additive layer doesn't
displace the base layer on first frame.

Test coverage:
- `additive-layer.test.ts` exercises makeClipAdditive at the TS layer.
- `tests/repo/test_phase_22_02_prep_glb_contract.py` enforces the
  structural contract (5 files exist, non-empty, all 5 state names
  referenced by additive-layer.test.ts).

If a real GLB breaks idle-zero (bone delta != 0 at t=0), the TS test
fails. Common cause: Mixamo motion that starts mid-stride. Fix: trim
the clip to start at a frame where lower-body matches the bind pose.

---

## 7. Anti-feature reminders

- NO AI-auto-cut video editing (Pitfall P57) — `scripts/demo_film/cut.sh`
  is manual.
- NO AI voiceover (Pitfall P58) — see `scripts/demo_film/vo_policy.md`.
- NO Linux platform — explicit out-of-scope (PROJECT.md).
- NO additional mascot characters — single character locked (memory
  `project_mascot_as_vtuber_personality_surface`).

