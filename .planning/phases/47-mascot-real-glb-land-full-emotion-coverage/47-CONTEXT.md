# Phase 47 Context — Mascot Real GLB Land + Full Emotion Coverage

**Date:** 2026-05-18
**Mode:** `gsd-autonomous fully` / `gsd-discuss-phase --auto` — all grey areas auto-resolved with recommended defaults; no AskUserQuestion calls; defer blockers to Kaan-action surface.
**Discuss pass:** 1 of 1 (single-pass cap per `modes/auto.md`).

---

## Domain

This phase delivers the full Mascot visual surface: swap the 5 v2.0 placeholder `prep_*.glb` clips for 23 real Mixamo-retargeted GLBs (3 Base + 5 Emotion + 5 Anticipation + 10 Reaction) wired into the v2.1 Phase-31 4-layer additive state machine, with every shipped event class driving at least one layer. Closes v3.0 §VIS-04 pre-stage. Single VTuber-style 3D character (Neon Rebel) per memory `project_mascot_as_vtuber_personality_surface` — no `/hatch` user-gen surface in this phase.

**Engineering deliverables are 100% unblocked.** Real-asset selection by Kaan (Mixamo Adobe-account walk) surfaces to KAAN-ACTION-LEGAL §VIS-04 — placeholders + retarget CLI + manifest schema + test harness + state-machine wiring + bundle-gate logic ship now; real GLBs swap in at discharge time via the existing drop-in slot pattern (Phase 22-02 same-name overwrite contract).

---

## Locked Requirements (from REQUIREMENTS.md § MASCOT)

- **MASCOT-01** — 23 real GLB clips ship at `tauri/ui/assets/mascot/animations/` slot paths: 3 Base (idle / breathe / sway) + 5 Emotion (joy / trust / surprise / anticipation / focus) + 5 Anticipation (prep_kick / prep_breakdown / prep_drop / prep_layer / prep_mix) + 10 Reaction (kick_swap / sub_layer / breakdown / reentry / phrase_boundary / distortion_climb / acid_line / mix_in / mix_out / hype_peak).
- **MASCOT-02** — Each GLB Mixamo-retargeted via `scripts/mascot/` Phase 43-05 CLI; source `.fbx` provenance documented under `assets/mascot/source/` (gitignored) with in-repo manifest.
- **MASCOT-03** — `scripts/mascot/check_bundle_size.sh` exits 0 with real GLBs in place — draco retune under existing 25 MB Tier-1 cap (preferred) OR documented 30 MB cap bump with audit-trail rationale.
- **MASCOT-04** — `tauri/ui/src/mascot/pools.ts` `clipName` mapping addresses real GLB track names; no placeholder regressions.
- **MASCOT-05** — 4-layer additive state machine drives every shipped event class (TRACK_CHANGE / PHASE / LAYER_ARRIVAL / MIX_MOVE / HEARTBEAT / KAAN_SPOKE / MANUAL + Hard Tek detectors) through Base + Emotion + Anticipation + Reaction with priority-stacked crossfades; vitest coverage matrix proves each event hits at least one layer.
- **MASCOT-06** — 30s persona smoke (`scripts/mascot/persona_smoke.sh`) plays each emotion + reaction at least once; screencast committed to `docs/mascot/persona_smoke.webm` (LFS or sized < 5 MB).
- **MASCOT-07** — README hero renders embedded GLB still (or short loop) alongside locked-verbatim hero text; passes anti-slop blocklist + does not trip readme-hero-sync CI.
- **MASCOT-08** — Mascot tests exercise v3.0 Tauri+Three.js production surface (not `mascot.html` easter egg); CI grep gate `! grep -rn "mascot.html" tests/ e2e/ scripts/ci/` enforced.

---

## Canonical Refs (downstream MUST read these before planning)

- `.planning/ROADMAP.md` § Phase 47 — goal, success criteria, invariants, KAAN-ACTION-LEGAL §VIS-04 deferral block.
- `.planning/REQUIREMENTS.md` § MASCOT-01..MASCOT-08 — locked acceptance criteria.
- `.planning/research/STACK.md` § Mascot tools — Mixamo + Adobe auto-rigger; `@gltf-transform/cli^4.0.0` + `gltf-pipeline^4.1.0`; Phase 43-05 retargeting scaffold.
- `.planning/research/FEATURES.md` § MASCOT — 23-clip enumeration anchored to Plutchik 8-primary + VTuber convention.
- `.planning/research/ARCHITECTURE.md` § Mascot — drop-in slot paths at `tauri/ui/assets/mascot/animations/prep_*.glb`; zero state-machine code change required (additive — extends, doesn't replace).
- `.planning/research/PITFALLS.md` — Pitfall 4 (mascot.html easter egg trap), Pitfall 11 (25 MB GLB bundle ceiling); v3-shipped P22+P23 cross-references.
- `tauri/ui/src/mascot/state-machine.ts` — Phase 13 Plan 04 pure state machine (no wall-clock, no timers, no three.js).
- `tauri/ui/src/mascot/pools.ts` — Phase 43 Plan 43-06 mood-pool taxonomy (`MOOD_POOLS`, `KIND_TO_SLOT`) — `clipName` mapping to update.
- `tauri/ui/src/mascot/layers/base.ts` + `emotion.ts` + `reaction.ts` — Phase 31 4-layer additive surface (Base / Emotion=p60 / Anticipation / Reaction=p80).
- `tauri/ui/src/mascot/types.ts` — `MascotState` / `MascotEmotion` / `MascotReaction` vocabulary; `STATE_PRIORITY` table.
- `tauri/ui/assets/mascot/manifest.json` — animation slot manifest (`states[]` → clip mapping); MUST extend, not break.
- `tauri/ui/assets/mascot/animations/PLACEHOLDER_NOTE.md` — Phase 22-02 idle-zero lower-body invariant + same-name drop-in workflow.
- `scripts/mascot/retarget_to_neon_rebel.py` — existing CLI (Phase 43-05); extend slot list from 5 → 23.
- `scripts/mascot/MIXAMO-CLIP-SOURCES.md` — selection-guidance doc for Kaan; extend with 18 new slot rows (Base + Emotion + 10 Reaction additions on top of 5 Anticipation).
- `scripts/mascot/check_bundle_size.sh` — two-tier bundle gate (Tier 1: ≤25 MB total; Tier 2: 400-1200 KB per `prep_*` clip); extend Tier 2 band to also cover new Base / Emotion / Reaction slots OR carve out per-family bands.
- `scripts/check_mascot_glb_size.sh` — Phase 31 Pitfall-P52 total-bundle gate that Tier 1 delegates to.
- `tauri/ui/assets/mascot/animations/character.glb` — Neon Rebel rig (locked baseline).
- `docs/asset_pipeline.md` § 5 — canonical placeholder→real swap workflow.
- Memory anchors: `project_mascot_as_vtuber_personality_surface` (single VTuber Neon Rebel; `/hatch` is v2.x stretch), `project_one_click_install_hard_req` (bundle size = install impact), `feedback_no_scope_creep_clean_utility` (minimum useful surface; no extra clip families), `project_v0_1_0_rc1_open_bugs` (mascot chrome strip regression class — test prod Tauri+Three.js surface, NOT mascot.html), `project_visual_direction_cdj_whisper` (mascot aesthetic = Pioneer CDJ headbob, NOT generic VTuber dance), `feedback_worktree_must_sync_main_first` (every subagent prompt MUST include Step-0 `git merge origin/main`).

---

## Decisions (auto-resolved per `--auto` recommended defaults)

### Clip Taxonomy + Slot Naming

- **[auto] Q: Slot file-name convention for the 18 new clips?** → **Same pattern as Phase 22-02 `prep_*.glb` family — short kebab-case, `<family>_<name>.glb`:**
  - Base (3): `base_idle.glb`, `base_breathe.glb`, `base_sway.glb`
  - Emotion (5): `emotion_joy.glb`, `emotion_trust.glb`, `emotion_surprise.glb`, `emotion_anticipation.glb`, `emotion_focus.glb`
  - Anticipation (5): `prep_kick.glb`, `prep_breakdown.glb`, `prep_drop.glb`, `prep_layer.glb`, `prep_mix.glb` (keeps the `prep_*` family from Phase 22-02, NEW slots — DOES NOT alias the existing 5 `prep_lean_in_*` / `prep_head_turn_*` / `prep_settle.glb` paths which stay for the v3.0 anticipation surface)
  - Reaction (10): `react_kick_swap.glb`, `react_sub_layer.glb`, `react_breakdown.glb`, `react_reentry.glb`, `react_phrase_boundary.glb`, `react_distortion_climb.glb`, `react_acid_line.glb`, `react_mix_in.glb`, `react_mix_out.glb`, `react_hype_peak.glb`
- **[auto] Q: Old `prep_*.glb` placeholders retained or deleted?** → **RETAINED.** Phase 22-02 `PLACEHOLDER_NOTE.md` documents the same-name drop-in contract; Kaan can still discharge the 5 original Anticipation slots independently via the existing §VIS-04 workflow. The 5 NEW `prep_kick/breakdown/drop/layer/mix.glb` are additional event-class-specific anticipations (not aliases). Both families live side-by-side in `manifest.json`.
- **[auto] Q: New clipKind enum entries in `pools.ts` `ClipKind`?** → **YES — extend the closed-set union with 23 new entries** corresponding to slot stems; existing `idle/talk_short/talk_long/celebrate/headbob` kinds STAY (they reference the legacy `prep_*` placeholders for Phase 43 mood pools — backward compat). The new families register under a fresh `BASE_CLIPS / EMOTION_CLIPS / ANTICIPATION_CLIPS / REACTION_CLIPS` map sibling to `KIND_TO_SLOT`.

### Retarget CLI Extension (MASCOT-02)

- **[auto] Q: Reuse existing `retarget_to_neon_rebel.py` or new script?** → **EXTEND** the existing CLI — add `--slot-family {base,emotion,anticipation,reaction}` flag + per-family slot whitelist. One script, one source of truth for draco retune + size-band assertion + manifest update.
- **[auto] Q: `assets/mascot/source/` `.fbx` provenance manifest format?** → **YAML at `assets/mascot/source/MANIFEST.yaml`** (gitignored sources, in-repo manifest) — each row: `{slot, mixamo_search_term, downloaded_at, sha256_of_source, draco_compression_level, output_bytes}`. Same shape as Phase 46 `dep_ratings.yaml` for consistency.
- **[auto] Q: CI gate on manifest completeness?** → **YES** — `scripts/mascot/check_manifest_complete.py` asserts every shipped GLB in `animations/` has a corresponding `MANIFEST.yaml` row; runs as part of `dep-audit.yml` or new `mascot-audit.yml`.

### Bundle-Gate Strategy (MASCOT-03)

- **[auto] Q: Draco retune under 25 MB cap (preferred) or 30 MB cap bump (fallback)?** → **PREFERRED: Draco retune under 25 MB.** 23 clips × 400-1200 KB band = 9.2-27.6 MB worst case; aim for mid-band (~700 KB avg) = ~16 MB total + character.glb baseline. Tune `--draco.compressionLevel 10` (max) on Reaction family (10 clips × ~600 KB target). If gate fails after retune attempt, document 30 MB bump in `docs/mascot/BUNDLE-DECISION.md` with audit trail (compression-level pushed to 10, per-clip target hit but cumulative still exceeded → cap bumped).
- **[auto] Q: Per-clip size band — same 400-1200 KB for all families or per-family?** → **Per-family bands** to match motion complexity:
  - Base (loop, simple): 200-600 KB (lighter — loops are short, low pose-key density)
  - Emotion (expressive face/torso): 300-900 KB
  - Anticipation (kept compat with Phase 22-02 band): 400-1200 KB
  - Reaction (peak-energy moves): 400-1200 KB
- **[auto] Q: How does the gate report under placeholders?** → **Tier 2 expected-fail-when-placeholder behavior is preserved** — existing comment in `check_bundle_size.sh` documents this is the gate's mechanism for reminding the operator §VIS-04 isn't discharged. Extend the same expected-fail UX to the 18 new slots: gate fails until Kaan drops real GLBs (intentional Kaan-action signal).

### State-Machine Wiring (MASCOT-05)

- **[auto] Q: Where does the 4-layer × 7-event coverage matrix live?** → **`tauri/ui/src/mascot/__tests__/event-coverage-matrix.test.ts`** — vitest test that imports the event dispatcher + the 4 layers and asserts, for each event type in {TRACK_CHANGE, PHASE, LAYER_ARRIVAL, MIX_MOVE, HEARTBEAT, KAAN_SPOKE, MANUAL} + Hard Tek detectors {DISTORTION_CLIMB, ACID_LINE_ENTRY, KICK_SWAP, SUB_LAYER_ARRIVAL, BREAKDOWN_KICK_KILL, REENTRY_KICK_LAND, KICK_DENSITY_SHIFT, PHRASE_BOUNDARY}, that at least one of {Base, Emotion, Anticipation, Reaction} layers receives a non-deny request after dispatch.
- **[auto] Q: Event → layer mapping in code?** → **Build a `EVENT_LAYER_PRIORITY_MAP` const** in `tauri/ui/src/mascot/event-dispatcher.ts` declaring which layer(s) each event class fans out to:
  - TRACK_CHANGE → Emotion (focus) + Anticipation (prep_mix) + Reaction (mix_in)
  - PHASE → Emotion (focus/anticipation depending on phase) + Anticipation (prep_breakdown / prep_drop)
  - LAYER_ARRIVAL → Reaction (sub_layer) + Emotion (surprise)
  - MIX_MOVE → Reaction (mix_in / mix_out)
  - HEARTBEAT → Base (idle/breathe/sway rotation, low priority)
  - KAAN_SPOKE → no-op (mascot stays on Base; talk-block rule applies)
  - MANUAL → caller-specified; full layer surface
  - DISTORTION_CLIMB → Reaction (distortion_climb)
  - ACID_LINE_ENTRY → Reaction (acid_line)
  - KICK_SWAP → Reaction (kick_swap)
  - SUB_LAYER_ARRIVAL → Reaction (sub_layer)
  - BREAKDOWN_KICK_KILL → Anticipation (prep_breakdown) + Reaction (breakdown)
  - REENTRY_KICK_LAND → Reaction (reentry)
  - KICK_DENSITY_SHIFT → Emotion (focus shift)
  - PHRASE_BOUNDARY → Reaction (phrase_boundary)
- **[auto] Q: Priority-stacked crossfade contract?** → **Reuse existing `priority-stack.ts`** with the established priorities (Base = lowest / Emotion = 60 / Anticipation = 70 (Phase 22-02 contract) / Reaction = 80). No new priority slots — composition over expansion.

### Pools.ts Update Strategy (MASCOT-04)

- **[auto] Q: Replace existing `KIND_TO_SLOT` mapping or extend?** → **EXTEND.** Old map stays (5 Phase 43 entries reference legacy `prep_*` placeholders for 3 mood pools — `pools.test.ts` greps `§VIS-05 verbatim`, must not regress). Add 4 sibling const maps:
  - `BASE_CLIP_TO_SLOT: Record<BaseClip, string>` (3 entries)
  - `EMOTION_CLIP_TO_SLOT: Record<EmotionClip, string>` (5 entries)
  - `ANTICIPATION_CLIP_TO_SLOT: Record<AnticipationClip, string>` (5 entries — NEW prep_kick family, NOT the legacy 5)
  - `REACTION_CLIP_TO_SLOT: Record<ReactionClip, string>` (10 entries)
- **[auto] Q: Animation `clipName` (GLB internal track name) vs slot file name?** → **CLI emits both** — `retarget_to_neon_rebel.py --slot react_kick_swap --really` writes the GLB to `react_kick_swap.glb` AND ensures the internal Three.js `AnimationClip.name` is `react_kick_swap` (slot stem). Asset-loader binds by clip-name; pools.ts maps clipKind → slot stem → clip-name 1:1.

### Persona Smoke Script (MASCOT-06)

- **[auto] Q: Headless or interactive?** → **Headless** via `xvfb-run` (Linux CI) or via Tauri's `--test` mode on Mac local. The smoke kicks an in-tauri test page that cycles through all 5 emotions + all 10 reactions on a 2s timer (5×0.5s + 10×2.5s = 30s exact), records via `ffmpeg -f avfoundation` (Mac) or `wf-recorder` (Linux); output `docs/mascot/persona_smoke.webm`.
- **[auto] Q: LFS or sized < 5 MB?** → **Sized < 5 MB** — 30s @ 480p WebM-VP9 at 800 kbps = ~3 MB. Avoids the LFS dependency for vibemix repo; matches `feedback_no_scope_creep_clean_utility` (no extra infra).
- **[auto] Q: CI run on every PR or weekly?** → **Weekly cron + manual `workflow_dispatch`.** Persona smoke needs a windowed display (xvfb works but is slow); not blocking PRs. The vitest coverage matrix IS the per-PR gate.

### README Hero GLB Render (MASCOT-07)

- **[auto] Q: Embedded GLB viewer (model-viewer web component) or pre-rendered still?** → **Pre-rendered still + short looping WebM** (model-viewer needs JS in README which GitHub strips). Path: `docs/assets/readme-hero.webm` (3s loop, 100 KB target) + `docs/assets/readme-hero.png` (still fallback for non-JS contexts).
- **[auto] Q: Which animation goes in the hero render?** → **`react_hype_peak` mid-loop** — the most visually load-bearing reaction; Pioneer-CDJ headbob aesthetic per memory `project_visual_direction_cdj_whisper`. NOT `emotion_joy` (too generic VTuber-coded).
- **[auto] Q: How does the anti-slop blocklist apply?** → **Hero RENDER (visual) bypasses the 15-token grep gate** (it's binary). Hero CAPTION text adjacent to the render (any new line added to README around the embed) passes the existing `check_no_ai_slop.py` gate. `readme-hero-sync.yml` extended to assert the new `docs/assets/readme-hero.{webm,png}` paths exist alongside the verbatim hero text.

### POC Immutability + mascot.html (MASCOT-08)

- **[auto] Q: How is the grep gate wired?** → **Add a step to `.github/workflows/poc-immutability-check.yml`** (existing v3.0 gate workflow): `! grep -rn "mascot.html" tests/ e2e/ scripts/ci/`. Returns non-zero exit if ANY match. Phrase the failure message: "mascot.html is the standalone easter-egg surface — Phase 47 tests MUST target the Tauri+Three.js production surface via Playwright at tauri/ui/dist/. See Pitfall 4."
- **[auto] Q: Tests directory structure?** → **`tauri/ui/src/mascot/__tests__/` (vitest, unit) + `e2e/mascot/` (Playwright, integration)** — the integration suite spawns the Tauri WebviewWindow via `cargo tauri dev` headless, snapshots the canvas WebGL output, asserts visual non-regression via pixelmatch against `tests/e2e/macbook/__snapshots__/mascot_*.png` baselines. The unit tests cover layer composition logic on Node; integration tests cover the actual GLB load + render path.
- **[auto] Q: Does `mascot.html` byte-identity get re-asserted here?** → **Already covered by v3.0 Phase 37-06 POC immutability gate** (`scripts/ci/check_poc_immutability.sh` greps git diff vs v2.0 tag for `mascot.html`). Phase 47 does NOT edit `mascot.html`; the new grep gate is a *complementary* assertion (tests don't reference it), not a duplicate of the byte-identity gate.

### Anti-slop blocklist extension

- **[auto] Q: Which Phase-47 artifacts join the anti-slop grep target?** → **`docs/mascot/persona_smoke.webm` caption (if any), `docs/mascot/BUNDLE-DECISION.md`, `scripts/mascot/MIXAMO-CLIP-SOURCES.md`, `assets/mascot/source/MANIFEST.yaml` rationale fields, `tauri/ui/src/mascot/event-dispatcher.ts` `EVENT_LAYER_PRIORITY_MAP` jsdoc comments.** Extend `scripts/launch/check_no_ai_slop.py` (or equivalent) target list. CI grep gate fails the build on any match.

### ModelRouter seam invariant

- **[auto] Q: Does Phase 47 touch ModelRouter?** → **NO.** Mascot is pure-frontend visual surface. No `gemini-*` literals introduced anywhere — invariant holds trivially. CI grep gate already excludes this concern from new Phase 47 files.

### Worktree-subagent Step-0 invariant

- **[auto] Q: Apply Step-0 invariant?** → **YES (mandated by v3.1 milestone-wide decision per memory `feedback_worktree_must_sync_main_first`).** Every Phase 47 subagent prompt skeleton MUST include:
  ```
  Step 0: cd <worktree> && git fetch origin main && git merge origin/main --no-edit
  Verify: git rev-parse origin/main == merge-base with HEAD
  ```
  Plan-checker rejects any plan lacking this. Without it, stale-base regressions on merge (the Phase 40 ~161k-line learning).

### Kaan-Action Surface (defer per autonomous mode)

- **KAAN-ACTION-LEGAL §VIS-04 (Mascot Real GLB Land — Mixamo Adobe-account walk).** Engineering ships:
  - `retarget_to_neon_rebel.py` extended to 23 slots
  - `MIXAMO-CLIP-SOURCES.md` extended with 18 new slot selection-guidance rows
  - `assets/mascot/source/MANIFEST.yaml` schema + manifest-completeness CI gate
  - All 23 placeholder GLBs (~50 KB each, alias to existing placeholder content) so the asset-loader doesn't 404 in dev
  - Bundle gate Tier 2 per-family bands + draco retune target levels
  - `event-dispatcher.ts` EVENT_LAYER_PRIORITY_MAP + 4-layer × 7-event vitest matrix
  - `persona_smoke.sh` headless harness (will operate over placeholders showing no-op-style anim, gates green when real GLBs drop in)
  - README hero asset stubs + `readme-hero-sync.yml` extension
  - CI grep gate `! grep -rn "mascot.html" tests/ e2e/ scripts/ci/`

  Kaan discharges at convenience: opens Mixamo, downloads 23 retargets via search-term guidance in `MIXAMO-CLIP-SOURCES.md`, runs `uv run python scripts/mascot/retarget_to_neon_rebel.py --slot <slot> --source ~/Downloads/<file>.glb --really` for each, commits the resulting GLBs + `MANIFEST.yaml` rows in one PR. Bundle gate flips green automatically.

Per memory `feedback_autonomous_no_grey_area_pause` — this is surfaced to STATE.md "Phase 47 Kaan-Action Surface" block; engineering does NOT block on it.

---

## Code Context (reusable assets + integration points)

- **`tauri/ui/src/mascot/state-machine.ts`** — Phase 13 Plan 04 pure state machine. NO three.js, NO wall-clock, NO timers. Pure functions: `initialMachineState`, `planTransition`, `applyTransition`, `tickIdleTimeout`. Phase 47 does NOT modify this file — additive layers compose on top.
- **`tauri/ui/src/mascot/priority-stack.ts`** — priority-stacked crossfade infrastructure (Phase 31). Reused as-is by 4-layer system. NO modifications.
- **`tauri/ui/src/mascot/layers/{base,emotion,reaction}.ts`** — Phase 31 4-layer surface. Phase 47 extends `emotion.ts` `EMOTION_CLIP_NAME` map to cover the new 5-emotion taxonomy (joy/trust/surprise/anticipation/focus) and `reaction.ts` `REACTION_CLIP_NAME` for the new 10-reaction taxonomy. NEW file `layers/anticipation.ts` lands for the 5-anticipation family (prep_kick/breakdown/drop/layer/mix).
- **`tauri/ui/src/mascot/pools.ts`** — Phase 43 Plan 43-06 mood-pool taxonomy. EXTEND with 4 new const maps (base/emotion/anticipation/reaction) sibling to existing `KIND_TO_SLOT`. Existing `MOOD_POOLS` + `KIND_TO_SLOT` stay verbatim — `pools.test.ts` greps it.
- **`tauri/ui/src/mascot/event-dispatcher.ts`** — NEW `EVENT_LAYER_PRIORITY_MAP` const + event → layer fanout. Existing dispatcher logic preserved.
- **`tauri/ui/src/mascot/asset-loader.ts`** — extends to bind 23 new clipNames; uses existing manifest.json shape.
- **`tauri/ui/assets/mascot/manifest.json`** — extends `animations[]` with 23 new entries (file + clip + states[]).
- **`scripts/mascot/retarget_to_neon_rebel.py`** — Phase 43-05 CLI. EXTEND slot whitelist from 5 → 28 (existing 5 `prep_*_lean/head_turn/settle` placeholders + 23 new family slots).
- **`scripts/mascot/check_bundle_size.sh`** — Phase 43-05 two-tier gate. EXTEND Tier 2 to per-family bands + cumulative cap check.
- **`scripts/mascot/MIXAMO-CLIP-SOURCES.md`** — Phase 43-05 selection-guidance doc. EXTEND with 18 new slot rows + aesthetic guardrails for each family.
- **`docs/asset_pipeline.md` § 5** — canonical placeholder→real swap workflow. NO modifications needed (same-name drop-in contract reused).

---

## Deferred Ideas (NOT Phase 47)

- `/hatch` user-generated mascot pipeline — v2.x stretch per memory `project_mascot_as_vtuber_personality_surface`. Recorded in backlog only.
- Multiple character rigs beyond Neon Rebel — v2.x stretch (single VTuber lock).
- Lipsync from TTS audio waveform — separate phase, not v3.1 scope.
- Mascot reactions driven by MIDI controller moves (e.g., crossfader detection) — research already covered in Phase 31; not a Phase 47 expansion.
- Procedural animation blending beyond the existing priority-stack crossfade — Three.js mixer is the engine; no replacement engine in scope.

---

## Open Questions Resolved by Auto-Mode

All resolved silently per `--auto` recommended defaults. See "Decisions" block above. No questions remain open at end of discuss.

---

## Next Steps

1. **UI design contract** — `gsd-ui-phase 47` generates UI-SPEC.md for the mascot visual surface (live session mascot panel + persona-smoke harness).
2. **Plan** — `gsd-plan-phase 47` decomposes into wave-able plans (estimated 6-8 plans: 47-01 retarget CLI extension + manifest schema, 47-02 pools.ts + layer wiring, 47-03 event-dispatcher EVENT_LAYER_PRIORITY_MAP + vitest matrix, 47-04 bundle gate per-family bands, 47-05 placeholder GLB stubs + manifest rows, 47-06 persona_smoke.sh + headless harness, 47-07 README hero render + readme-hero-sync.yml extension, 47-08 CI grep gate + anti-slop extension).
3. **Execute** — `gsd-execute-phase 47 --no-transition`.
4. **Code review + UI review** — `gsd-code-review 47` then `gsd-ui-review 47`.
