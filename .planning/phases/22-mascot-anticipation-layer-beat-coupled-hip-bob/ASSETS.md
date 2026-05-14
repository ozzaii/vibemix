# Phase 22 — `prep_*` GLB Authoring Brief

This file is the per-clip authoring contract consumed by the human asset
author (Kaan or contractor) producing the 5 anticipation-layer clips that
the Wave 1 code wires up. The Wave 1 code merge (Plan 22-02) ships
**placeholder GLBs sourced from existing Mixamo clips** in this repo so the
asset-loader pipeline doesn't trip on missing files; the placeholders MUST
be replaced before the P26 viral demo / v2.0 RC tag — see "Placeholder
policy" at the bottom.

## Rig reference

Target rig: `tauri/ui/assets/mascot/character.glb` — Mixamo biped, ~1.7 m
height, ~24-bone skeleton (matches the 21-clip Neon Rebel bundle from
Phase 13). Bone names are byte-identical to the source Mixamo rig
(`mixamorigHips`, `mixamorigSpine`, `mixamorigHead`, …). The animation GLBs
are stripped via `scripts/build-mascot-bundle.mjs` to keep mesh/material
out; only Skin + Animation tracks survive. Anim retargeting at runtime is
a no-op because the rig is identical — bone-name match binds the clip
straight onto the character's `AnimationMixer`.

## Why these clips are additive (delta-zero requirement)

Per Phase 22 CONTEXT D-LOCKED + PITFALLS.md Pitfall 19 — the anticipation
layer is the **second AnimationAction** on the SAME `AnimationMixer` (NOT
a second mixer). It's blended additively over whatever base layer is
currently active (idle / dance / talk / react). For additive blending to
look right the clips MUST be authored as **deltas from the rig's bind
pose**, NOT as absolute bone poses:

- Author the lean / head-turn / settle motion **on top of a zero-pose rig**
  (Hips at world origin, all rotations identity, all translations zero
  except for the bind-pose values).
- Hips bone Y/X/Z **rotation AND translation** must be zero at every
  keyframe (within ±0.001). This prevents the additive layer from fighting
  the procedural hip-bob (Phase 22 Wave 3) — the bob writes to Hips, the
  prep clips MUST NOT.
- Lower-body bones (`mixamorigLeftUpLeg`, `mixamorigRightUpLeg`,
  `mixamorigLeftLeg`, `mixamorigRightLeg`, `mixamorigLeftFoot`,
  `mixamorigRightFoot`) must hold zero-delta across all keyframes — the
  feet stay planted while the upper body anticipates.
- Upper body (`mixamorigSpine` / `mixamorigSpine1` / `mixamorigSpine2` /
  `mixamorigNeck` / `mixamorigHead` / arms) carries the entire motion.

Three.js will then run `AnimationUtils.makeClipAdditive(clip)` at asset
load (Wave 1 asset-loader pass) which subtracts the first-frame pose from
every subsequent frame — the clip becomes a pure delta the mixer can blend
additively over the running base layer at any weight ∈ [0, 1].

## Per-clip spec

All clips at **30 fps**. Sizes are post-DRACO compression budget — the
strip script keeps clips under ~300 KB each (Pitfall 23: bundle weight
budget).

### 1. `prep_lean_in_neutral.glb`

- **Duration:** 400 ms (12 frames @ 30 fps)
- **Vibe:** Restrained "you ready?" lean — the mascot leans forward
  subtly, eyes on the deck. Used when an event is anticipated but the
  predicted excitement is mid-range.
- **Primary motion:** ~6° torso lean forward (`mixamorigSpine` X rotation
  −6°), held flat on neck (face still readable to viewer), no arm motion.
- **Hands:** Held loosely at default rest position.
- **Head:** No turn, no nod — micro-motion only.
- **Curve:** Ease-out on lean-in (motion peaks at frame 8 of 12), held
  through frame 12; mascot stays leaned until the `prep_settle.glb`
  reverse plays.

### 2. `prep_lean_in_hyped.glb`

- **Duration:** 350 ms (10–11 frames @ 30 fps) — slightly faster than
  neutral to feel more committed.
- **Vibe:** "Something's coming" — the mascot leans further forward, head
  comes UP slightly (chin tilts +4°), arms tense at sides. Used when the
  predicted excitement is high (buildup_score > 0.7, hard_tek genre).
- **Primary motion:** ~12° torso lean forward, +4° head pitch up.
- **Hands:** Subtle clench — fingers curl ~10°.
- **Head:** No yaw — pure pitch-up.
- **Curve:** Sharper ease-out than neutral (peaks at frame 6 of 11).

### 3. `prep_head_turn_left.glb`

- **Duration:** 250 ms (7–8 frames @ 30 fps) — fast head turn, no body
  follow.
- **Vibe:** "Did you hear that?" — quick attention pivot toward the left
  deck (Deck A in the standard DDJ layout).
- **Primary motion:** `mixamorigNeck` + `mixamorigHead` Y rotation +25°
  (camera-left from the mascot's POV).
- **Body:** Hold steady — NO spine rotation, NO hips translation.
- **Curve:** Hard ease-out (peaks at frame 4 of 8) then HOLD.

### 4. `prep_head_turn_right.glb`

- **Duration:** 250 ms (7–8 frames @ 30 fps) — mirror of left.
- **Vibe:** Same as left, opposite direction (Deck B side).
- **Primary motion:** Neck + Head Y rotation −25° (camera-right).
- **Body:** Hold steady.
- **Curve:** Same as left, mirrored.

### 5. `prep_settle.glb`

- **Duration:** 300 ms (9 frames @ 30 fps) — slightly slower than lean-in
  so the return doesn't feel jerky.
- **Vibe:** "Reset" — gentle return-to-zero from whichever prep clip is
  currently held. Plays when the anticipated event fires (so the base
  layer's react/talk takes over) OR when the prediction times out (no
  event landed inside the window).
- **Primary motion:** Reverse-curve return to identity on every prep_*
  bone — Spine / Neck / Head / Hands all back to zero delta.
- **Curve:** Ease-in-ease-out (smooth on both ends — no snap).

## Source pipeline (Mixamo → Blender → strip)

1. **Pick a source clip on Mixamo** that approximates the motion (or
   author from scratch in Blender on the existing biped rig).
2. **Re-target the clip** onto the Neon Rebel rig in Blender — use
   Auto-Rig Pro or Blender's stock retargeting. Verify the rig is identical
   to `character.glb` (bone-name + hierarchy match).
3. **Manual delta-zero pass** in Blender's NLA / Action editor:
   - Select `mixamorigHips`. For every keyframe, force the Hips Y/X/Z
     rotation to identity (use the Drivers panel or hard-overwrite the
     F-Curve values). Same for translation X/Y/Z.
   - Select all lower-body bones (`*LeftUpLeg`, `*LeftLeg`, `*LeftFoot`,
     `*LeftToeBase`, mirror for Right) and force ALL channels to their
     bind-pose values across every keyframe.
   - Render-preview the clip overlaid on a held T-pose — confirm only
     upper-body delta is visible.
4. **Export GLB**:
   - `File → Export → glTF 2.0`
   - Format: glb (binary)
   - Animation: Always sample, 30 fps, NLA strips off (single action only)
   - Skinning: All bones
   - Compression: OFF at export time (DRACO is applied by the strip
     pipeline below)
5. **Strip pass** — run the existing
   `scripts/build-mascot-bundle.mjs` equivalent to drop Mesh / Material /
   Texture / Image / Skin-bind data, keeping Skin + Animation tracks only.
   Same shape as the existing 20 stripped clips under
   `tauri/ui/assets/mascot/animations/`.
6. **Commit the stripped GLB** to
   `tauri/ui/assets/mascot/animations/<clip>.glb` and verify the size is
   ≤ 300 KB.

## Verification checklist (author runs before commit)

For each `prep_*.glb`:

- [ ] Loads cleanly in Three.js `GLTFLoader` (no warnings, no errors)
- [ ] `clip.tracks` contains tracks for upper-body bones only (no Hips,
      no UpLeg / Leg / Foot / ToeBase tracks)
- [ ] Hips bone delta < 0.001 on rotation + translation across every
      keyframe (open in Blender and scrub the timeline — the Hips
      transform widget MUST NOT move)
- [ ] File size ≤ 300 KB
- [ ] Retargeting visually correct on `character.glb` (Spine / Neck /
      Head / Arms move; nothing else)
- [ ] Duration matches the per-clip spec ±20 ms
- [ ] `AnimationUtils.makeClipAdditive(clip).blendMode ===
      THREE.AdditiveAnimationBlendMode` post-load (asset-loader verifies
      this — see `additive-layer.test.ts`)

## Placeholder policy (Wave 1 ships placeholders)

Wave 1 / Plan 22-02 commits placeholder GLBs **byte-copied from existing
Mixamo clips already in the repo** so the asset-loader pipeline + Wave 2
fire-path can land while the real authoring happens in parallel. The
placeholders are real loadable GLBs (not empty files) but they do **NOT**
honor the delta-zero requirement — playing them additively will look
wrong (the full Hips + lower-body motion gets layered onto the base
clip). This is intentional: it surfaces the "asset author owes us delta-
zero clips" gate visibly during dev playback rather than silently shipping
broken visuals.

Source mapping for the Wave 1 placeholders:

| prep clip                       | source clip (existing)             | reason                                                 |
| ------------------------------- | ---------------------------------- | ------------------------------------------------------ |
| prep_lean_in_neutral.glb        | alert_quick_turn.glb               | closest forward-attention motion in the bundle         |
| prep_lean_in_hyped.glb          | alert_quick_turn.glb               | same source, replaced separately when authored         |
| prep_head_turn_left.glb         | alert_quick_turn.glb               | the existing alert IS a quick head turn                |
| prep_head_turn_right.glb        | alert_quick_turn.glb               | same — distinct file so the contract is 1:1            |
| prep_settle.glb                 | shrug.glb                          | shrug ≈ "neutral reset" body language; ok as stub      |

**Replacement gate (HARD):** Before P26 viral demo OR v2.0 RC tag,
whichever lands first, the 5 placeholder GLBs MUST be replaced with the
real delta-zero clips authored per this brief. Tracked in
`KAAN-ACTION.md` under Phase 22 deliverables.
