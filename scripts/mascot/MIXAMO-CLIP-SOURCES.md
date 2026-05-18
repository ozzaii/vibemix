# Mixamo Clip Sources — VIS-04 (Phase 43 → Phase 47 extension)

Per CONTEXT §VIS-04 + Phase 47 / MASCOT-02: 5 legacy slots + 23 new Phase 47
slots (3 Base + 5 Emotion + 5 Anticipation + 10 Reaction) — 28 total Mixamo
retargets at full discharge.

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

---

# Phase 47 / MASCOT-02 — 18 new selection-guidance rows

23 new Phase 47 slots split across 4 families. Same retarget pipeline as Phase 43-05;
extended slot taxonomy. Per memory `project_visual_direction_cdj_whisper`:
Pioneer-CDJ headbob aesthetic across all families — hands close to body,
static-foot-grounded, head as primary expressive surface, ~120 BPM equivalent loop.

## Base family (3 looping baseline clips)

| # | Mixamo asset (search term) | vibemix slot | Purpose | Notes |
|---|----------------------------|--------------|---------|-------|
| 1 | "Standing Idle Relaxed" | `base_idle.glb` | Default boot state | Lowest priority loop; mascot returns here when no event fired |
| 2 | "Breathing Idle" | `base_breathe.glb` | HEARTBEAT rotation | Subtle chest rise; no exaggerated shoulder pop |
| 3 | "Subtle Sway" | `base_sway.glb` | Mid-set HEARTBEAT rotation | Full-body shift (weight transfer), NOT waist twist |

**Aesthetic guardrails (Base family):** Loops MUST be < 4s. Breath visible at the
chest; no exaggerated chest rise. Sway = full-body shift, not waist twist. Per
memory `project_visual_direction_cdj_whisper` — restraint over flair.

## Emotion family (5 priority-60 emotion clips)

| # | Mixamo asset (search term) | vibemix slot | Purpose | Notes |
|---|----------------------------|--------------|---------|-------|
| 1 | "Happy Idle — restrained" | `emotion_joy.glb` | KAAN_SPOKE positive + LAYER_ARRIVAL stack | NO clapping, NO above-shoulder gestures |
| 2 | "Nodding Confidently" | `emotion_trust.glb` | Extended HEARTBEAT silence (>= 90s) | Slow, deliberate nods only |
| 3 | "Surprised Mild" | `emotion_surprise.glb` | LAYER_ARRIVAL (Hard Tek) + SUB_LAYER_ARRIVAL | Eyebrow + head tilt; no jump |
| 4 | "Listening Forward Lean" | `emotion_anticipation.glb` | PHASE entry (intro/buildup) | Subtle forward weight shift, NOT bow |
| 5 | "Concentrated Idle" | `emotion_focus.glb` | TRACK_CHANGE + KICK_DENSITY_SHIFT | Eyes-forward stillness; default-emotion state |

**Aesthetic guardrails (Emotion family):** Face + upper body only. Hands hover near
belt; no above-shoulder gestures. Emotion clips are 2-4s loops. Per memory
`project_visual_direction_cdj_whisper`.

## Anticipation family (5 NEW event-class prep clips — distinct from legacy_prep)

| # | Mixamo asset (search term) | vibemix slot | Purpose | Notes |
|---|----------------------------|--------------|---------|-------|
| 1 | "Ready Stance Slight Headbob" | `prep_kick.glb` | BREAKDOWN_KICK_KILL detected | Weight forward; ready posture |
| 2 | "Settling Calm" | `prep_breakdown.glb` | PHASE entry (breakdown) | Weight back; head subtly down |
| 3 | "Coiled Tension Forward" | `prep_drop.glb` | PHASE entry (drop) | Lean-in; eyes-forward; pre-impact stillness |
| 4 | "Listening Head Tilt" | `prep_layer.glb` | LAYER_ARRIVAL window | Head tilt + slight shoulder turn |
| 5 | "Subtle Sway Anticipation" | `prep_mix.glb` | TRACK_CHANGE imminent | Steady sway with eyes-forward focus |

**Aesthetic guardrails (Anticipation family):** Same aesthetic as the 5 legacy
`prep_*` family. This Phase 47 family adds event-class-specific posture
(e.g., prep_kick = ready stance, weight forward; prep_breakdown = settling,
weight back). Each clip is a 1-2.5s loop. Per memory
`project_visual_direction_cdj_whisper`.

## Reaction family (10 priority-80 one-shot reactions)

| # | Mixamo asset (search term) | vibemix slot | Purpose | Notes |
|---|----------------------------|--------------|---------|-------|
| 1 | "Short Head Nod" | `react_kick_swap.glb` | KICK_SWAP detector | Single deliberate nod |
| 2 | "Eyebrow Raise Subtle" | `react_sub_layer.glb` | SUB_LAYER_ARRIVAL | Face-only; brief |
| 3 | "Slow Bow Head" | `react_breakdown.glb` | BREAKDOWN_KICK_KILL | Head dips, weight settles |
| 4 | "Head Lift Slight Smile" | `react_reentry.glb` | REENTRY_KICK_LAND | Recovery + acknowledgment |
| 5 | "Quick Headbob 8-count" | `react_phrase_boundary.glb` | PHRASE_BOUNDARY | 4-beat headbob, lands on downbeat |
| 6 | "Building Tension Shoulder Roll" | `react_distortion_climb.glb` | DISTORTION_CLIMB | Restrained shoulder roll, NO full convulsion |
| 7 | "Wry Smile Tilt" | `react_acid_line.glb` | ACID_LINE_ENTRY | Knowing-look face + head tilt |
| 8 | "Approving Nod Forward" | `react_mix_in.glb` | TRACK_CHANGE + MIX_MOVE | Forward nod (acknowledgment of incoming) |
| 9 | "Glance Aside Subtle" | `react_mix_out.glb` | TRACK_CHANGE end | Eyes-aside glance + slight head turn |
| 10 | "Reserved Hype Headbang" | `react_hype_peak.glb` | PHASE entry (peak/hype) | **README HERO RENDER ASSET — get this one right.** Reserved headbob, not full-body convulsion. |

**Aesthetic guardrails (Reaction family):** One-shot, NOT loops. Each clip is
1-2.5s. NO peak-energy dance moves — even `react_hype_peak` is reserved headbob,
not full-body convulsion. `react_hype_peak` is the README hero render asset — get
this one right. Per memory `project_visual_direction_cdj_whisper`.

## Download checklist (Phase 47 new families — Kaan's flow)

In addition to the Phase 43-05 5 legacy slots above:

- [ ] Each Phase 47 slot's source file at `~/Downloads/mixamo_<slot>.glb` (e.g., `~/Downloads/mixamo_react_hype_peak.glb`)
- [ ] Format: glTF Binary (.glb) — Mixamo > Format dropdown
- [ ] Skin: "Without Skin" (the rig is `tauri/ui/assets/mascot/character.glb`)
- [ ] Each downloaded GLB <= 5 MB raw
- [ ] No watermark / promo banner
- [ ] Aesthetic vetted against the per-family guardrails above

## Retarget run — Phase 47 batch mode

```bash
# Single slot:
uv run python scripts/mascot/retarget_to_neon_rebel.py \
    --slot react_hype_peak --source ~/Downloads/mixamo_react_hype_peak.glb --really

# Full family batch (assumes ~/Downloads/mixamo_<slot>.glb for each slot in the family):
uv run python scripts/mascot/retarget_to_neon_rebel.py \
    --slot-family reaction --really
```

## Verification (full 28-slot discharge)

```bash
# Both tiers must be green:
bash scripts/mascot/check_bundle_size.sh

# Manifest ↔ on-disk parity:
python3 scripts/mascot/check_manifest_complete.py

# Inventory check — 28 files across 4 family prefixes + the legacy 5:
ls -lh tauri/ui/assets/mascot/animations/base_*.glb \
       tauri/ui/assets/mascot/animations/emotion_*.glb \
       tauri/ui/assets/mascot/animations/prep_*.glb \
       tauri/ui/assets/mascot/animations/react_*.glb
```
