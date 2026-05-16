# Placeholder GLBs — Anticipation Layer (Phase 22-02 / Phase 35)

The following 5 GLBs in this directory are **v2.0 placeholders**:

- `prep_lean_in_neutral.glb`
- `prep_lean_in_hyped.glb`
- `prep_head_turn_left.glb`
- `prep_head_turn_right.glb`
- `prep_settle.glb`

They were provisioned in Phase 22 (Plan 22-02) for the AdditiveLayer
anticipation surface. Phase 35 (ASSETS-03 / `ASSETS-PREP-REPLACE`)
replaces them with Mixamo-rigged real clips via Kaan-action.

## Contract real GLBs MUST preserve

**Idle-zero lower-body delta (Phase 22-02 invariant).**

At `t=0` after `AnimationUtils.makeClipAdditive(clip, refPose)`, the
lower-body bone deltas (hip + knees + feet) must be ≈ 0. The additive
layer must not displace the base layer on the first frame — otherwise
the mascot's pose pops when an anticipation fires.

### Why

The additive layer blends in over 100-300ms. If t=0 of the prep clip
already has non-zero hip/knee/foot deltas, the first frame is a
discontinuous jump from the base layer pose. Visually: the mascot
snaps before easing into the prep.

### How to verify before commit

1. Run the TS-side gate (in `tauri/ui/`):

   ```bash
   npm test -- additive-layer
   ```

   The test exercises makeClipAdditive on each prep_* clip. Bone-level
   validation lives here.

2. Run the Python structural gate (from repo root):

   ```bash
   pytest tests/repo/test_phase_22_02_prep_glb_contract.py -v
   ```

   This checks file existence + non-empty + state-name coverage in the
   TS test file. It does NOT parse GLB bone data — that's the TS test's
   job.

3. Run the Phase 35 budget gates:

   ```bash
   ./scripts/check_mascot_glb_size.sh
   python scripts/glb_optimize.py --check tauri/ui/assets/mascot/
   ```

## Source replacement workflow

See `docs/asset_pipeline.md` § 5 (Replace placeholders — drop into
repo) for the canonical workflow.

## Provenance

- Placeholder source: Meshy AI — Neon Rebel biped (v2.0 character).
- Placeholder clip names (per `manifest.json`): all 5 currently alias
  the `Alert_Quick_Turn_Right` Mixamo clip (4 of 5) or `Shrug` (settle).
  This is the placeholder behavior — distinct clip data lands in
  Phase 35.

## Do NOT remove

These files are LIVE-LOADED via `tauri/ui/assets/mascot/manifest.json`.
Removal breaks the mascot anticipation surface. The replacement workflow
is drop-in by same-name overwrite, not delete-then-add.
