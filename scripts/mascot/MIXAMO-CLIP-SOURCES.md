# Mixamo Clip Sources — VIS-04 (Phase 43, Plan 43-05)

Per CONTEXT §VIS-04: 5 Mixamo source clips → Neon Rebel rig → 5 `prep_*.glb`
slot replacements.

- **Source:** [Mixamo.com](https://www.mixamo.com/) — Kaan logs in with personal
  Adobe ID (§VIS-04 KAAN-discharge in `KAAN-ACTION-LEGAL.md`).
- **Target rig:** `tauri/ui/assets/mascot/character.glb` (Neon Rebel; locked
  per memory `project_mascot_as_vtuber_personality_surface`).
- **Pipeline:** `scripts/mascot/retarget_to_neon_rebel.py --source <mixamo.glb> --slot <slot> --really`
- **Per-clip target:** 400 KB – 1200 KB after draco compression.
- **Total bundle target:** ≤ 25 MB (enforced via `scripts/mascot/check_bundle_size.sh`).

This document is **selection guidance for Kaan**, not a binding asset list. Kaan
picks the actual best Mixamo variant per the "real DJ friend in your ear, no
AI slop" principle (CONTEXT specifics): the script picks slots, Kaan picks
energies.

## Source clip selections

| # | Mixamo asset (search term) | vibemix slot | Purpose | Notes |
|---|----------------------------|--------------|---------|-------|
| 1 | "Standing Idle" or "Breathing Idle" | `prep_settle.glb` | Idle — baseline pose | Universal across all moods; pick the calmest variant (subtle breath; no idle-fidget loop). |
| 2 | "Talking" or "Talking Casually" | `prep_head_turn_left.glb` | Talk_short — short talk loop | Target < 3 s clip; subtle head + hand motion only. |
| 3 | "Talking 2" or "Explaining" | `prep_head_turn_right.glb` | Talk_long — long talk loop | 4 – 6 s clip; slightly more expressive than Talk_short. |
| 4 | "Salute", "Cheering", or reserved "Jump" | `prep_lean_in_hyped.glb` | Celebrate — Hype-man moment | **Pioneer-CDJ headbob aesthetic** — pick a clip with reserved, grounded energy. Do NOT pick exaggerated VTuber dance / flailing arms / spin moves. |
| 5 | "Headbob" or "Macarena Dance" first 4 s | `prep_lean_in_neutral.glb` | Headbob — Pioneer-CDJ baseline | The single most load-bearing aesthetic signal. Reserved nod, weight-on-back-foot, occasional shoulder roll. Slop-checklist: no jazz hands, no body twirl, no full-arm dance. |

## Aesthetic guardrails (CONTEXT §VIS-04 specifics)

> "The Neon Rebel mascot mood for the celebrate clip should feel like a Pioneer
> CDJ headbob, NOT a generic VTuber dance — the visual direction is 'DJ friend',
> not 'vtuber slop'."

This applies to **all 5 clips**, not just celebrate. Concrete rules:

- **Hands:** stay close to the body. No "presenting" gestures, no over-articulated
  finger plays. A short hand wave on Talk_long is the max.
- **Hips:** no exaggerated weight-shift, no hip pop. Static-foot-grounded only.
- **Head:** primary expressive surface. Nods, tilts, micro-bobs OK.
- **Tempo:** clips that loop at ~120 BPM equivalent. The headbob in particular
  should feel like the DJ themselves head-nodding behind the decks, not a
  party-dancer in front of the booth.

## Download checklist (Kaan's flow)

- [ ] Each clip downloaded as **glTF Binary (.glb)** — Mixamo > Format dropdown.
- [ ] **Skin:** "Without Skin" if Mixamo offers the option (the rig comes from
      `tauri/ui/assets/mascot/character.glb`; the source clip only contributes
      animation data, not mesh).
- [ ] Each downloaded GLB ≤ 5 MB raw (draco compression brings it into the
      400 KB – 1200 KB target band).
- [ ] No watermark / promo banner on the asset preview (verify in Mixamo
      preview before download).
- [ ] Staged as `~/Downloads/mixamo_<slot>.glb` for each (the runbook in
      `KAAN-ACTION-LEGAL.md §VIS-04` assumes that filename convention).

## Retarget run (one-liner per clip)

```bash
uv run python scripts/mascot/retarget_to_neon_rebel.py \
    --source ~/Downloads/mixamo_idle.glb --slot prep_settle --really
```

Repeat for the remaining 4 slots (`prep_head_turn_left`, `prep_head_turn_right`,
`prep_lean_in_hyped`, `prep_lean_in_neutral`). The script auto-runs draco
compression + asserts the output lands in the 400 KB – 1200 KB band; failure
surfaces the gltf-pipeline flag to tune (`--draco.compressionLevel`).

## Verification

```bash
# Both tiers must be green:
bash scripts/mascot/check_bundle_size.sh

# Inventory check — 5 files, each 400 KB – 1200 KB:
ls -lh tauri/ui/assets/mascot/animations/prep_*.glb
```

## What unblocks

- **VIS-05** mood pool runtime validation (Plan 43-06) runs against real
  retargets instead of placeholders, giving the 30 s smoke its actual
  ship-quality signal.
- **v3.0 ship-cut gate** (Phase 45) — the visual ship lock cannot pass with
  placeholder GLBs in the bundle.

## Cross-references

- Retarget driver: `scripts/mascot/retarget_to_neon_rebel.py`
- Bundle size gate: `scripts/mascot/check_bundle_size.sh`
- Runbook: `KAAN-ACTION-LEGAL.md §VIS-04`
- CONTEXT: `.planning/phases/43-visual-ship-lock/43-CONTEXT.md` §`<decisions>` VIS-04
- Locked rig provenance: `tauri/ui/assets/mascot/MANIFEST.md`
- Placeholder GLB origin: `tauri/ui/assets/mascot/animations/PLACEHOLDER_NOTE.md`
