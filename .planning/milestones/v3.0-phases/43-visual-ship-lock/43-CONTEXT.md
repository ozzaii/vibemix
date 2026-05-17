# Phase 43: Visual Ship Lock - Context

**Gathered:** 2026-05-16
**Status:** Ready for planning
**Mode:** Autonomous (gsd-autonomous fully — grey areas resolved by orchestrator from locked memories + roadmap success criteria)

<domain>
## Phase Boundary

Lock CDJ Whisper UI surfaces to FL-Studio-grade polish, replace 5 mascot stub animations with Mixamo retargets, and pre-produce the 30s hero demo for launch. Three internal waves:

- **Wave A — UI polish (VIS-01, VIS-02, VIS-03):** Tier-1 surface audit (session / mascot overlay / wizard / calibration) using paired `gsd-ui-checker` + `gsd-ui-auditor` until zero HIGH findings; hover-state coverage sweep with `--glow-faint`; `session/components/meter.ts` spectrum rebuild (hardware-LED-strip + amber peak hold).
- **Wave B — Mascot animation (VIS-04, VIS-05, VIS-06, VIS-07):** Replace 5 `prep_*.glb` placeholders with Mixamo retargets (per-clip 400KB-1.2MB, total bundle ≤25MB); mood→animation pool runtime validation across 3 personas with 30s smokes; integrated-GPU perf gate via `data-blur-perf` fallback ladder; memory + storyboard doc drift cleanup ("DJ bat" → "Neon Rebel", Workbench + DSEG7 → Saira + glass).
- **Wave C — Hero demo pre-production (VIS-08, VIS-09):** Re-mock UI chip overlay frames in `mocks/vibemix-cinematic-storyboard.html` to CDJ Whisper v5; finalize 8-cut shot list (≤8 cuts gate); pre-production handoff to Francesco (shot list + audio capture plan + vibemix demo-mode deterministic config + 1080p+60fps+48kHz spec).

Engineering-side ships everything except live performance capture (Francesco's discharge) and Mixamo asset uploads (Kaan-discharge if real-name account required).

Anti-feature carveouts:
- Do NOT redesign visual direction — CDJ Whisper is locked per memory `project_visual_direction_cdj_whisper` (Pioneer-grade hardware in library mode; 5 warm blacks; single amber accent; Geist + Fraunces; restraint over flourish). Baseline: `mocks/vibemix-direction-final.html`.
- Do NOT introduce a second mascot — memory `project_mascot_as_vtuber_personality_surface` locks SINGLE VTuber rig with mood variation. /hatch user-gen mascots are v2.x deferred.
- Do NOT extend animations beyond the 5 `prep_*.glb` slots — pool taxonomy is fixed (Hype-man / Teacher / Coach × idle/talk/celebrate clip set).
- Do NOT auto-build the live performance shoot — Francesco owns capture day; Kaan owns scratch-capture verification with vibemix demo-mode after Phase 43 lands.

</domain>

<decisions>
## Implementation Decisions

### UI Polish Wave (VIS-01..03)

- **VIS-01 audit loop methodology:** Run `gsd-ui-checker` (BLOCK/FLAG/PASS verdicts) + `gsd-ui-auditor` (scored 6-pillar audit) on each Tier-1 surface — session window, mascot overlay, wizard (6 onboarding steps), calibration / first-run. Loop critique→execute until zero HIGH findings per surface. Findings written to `.planning/phases/43-visual-ship-lock/UI-REVIEW-<surface>.md`. Plan 43-01 ships the audit driver script + first audit run; Plan 43-02..04 close findings per Tier-1 surface bucket (session, overlay, wizard+calibration combined). Tier-1 set sourced from `tauri/ui/src/{session,mascot,overlay,wizard,settings}/`.
- **VIS-02 hover-state sweep:** Every `[data-interactive]` / `<button>` / `<a>` / `[role="button"]` element in Tier-1 surfaces gets the `--glow-faint` token (already in `tauri/ui/src/tokens.css` per memory). Visual-regression test pins shape via Playwright snapshot at hover state. Test lives in `tauri/ui/tests/visual/hover-glow.spec.ts`; regression baseline checked into `tauri/ui/tests/visual/__snapshots__/`.
- **VIS-03 meter spectrum rebuild:** `tauri/src/session/components/meter.ts` is the existing meter source (canonical from `mocks/vibemix-app-ui.html`). Replace the web-app gradient render with: (a) hardware-LED-strip segmentation (discrete 12-segment bars, not smooth gradient), (b) amber peak-hold lozenge (decay over 1.2s per CDJ convention), (c) silk-12 minor grid lines (1px subtle separators every Nth segment). Reuses CSS tokens; no new dependencies. Smoke test pins frame rate ≥60fps with `requestAnimationFrame` loop and screenshot harness.

### Mascot Animation Wave (VIS-04..07)

- **VIS-04 Mixamo retarget pipeline:** 5 placeholder GLB files in `tauri/ui/public/mascot/prep_*.glb` get replaced via Mixamo auto-rig + Three.js skeleton retarget. Pipeline: Kaan picks 5 Mixamo source clips (Idle / Talk_short / Talk_long / Celebrate / Headbob) → ffmpeg-free GLB export → scripts/mascot/retarget_to_neon_rebel.py applies skeleton remap to the locked "Neon Rebel" rig (placeholder mascot mesh from `tauri/ui/public/mascot/neon-rebel.glb`). Per-clip target: 400KB-1.2MB after gltf-pipeline draco compression. Total bundle (rig + 5 clips + textures) ≤25MB enforced by `scripts/mascot/check_bundle_size.sh` invoked in CI. **Kaan-discharge:** actual Mixamo account login + 5 clip downloads documented in `KAAN-ACTION-LEGAL.md §VIS-04`. Engineering ships retarget script + size gate + placeholder→real swap-in CI step.
- **VIS-05 mood pool runtime validation:** Existing pool taxonomy in `tauri/ui/src/mascot/pools.ts` (or to be created if absent). Hype-man pool = [idle, talk_short, celebrate]; Teacher = [idle, talk_long, headbob]; Coach = [idle, talk_short, headbob]. Validation: 30s smoke per persona triggered via `tauri/ui/tests/mascot/smoke-30s.spec.ts` — crossfade duration ≥200ms, idle-zero contract (no clip plays after persona reset within 50ms), bone-level frame test asserts neutral pose snap.
- **VIS-06 integrated-GPU perf:** `data-blur-perf` attribute on `<body>` toggles backdrop-filter ladder (high/med/low). Already wired in `tokens.css` per memory. New: runtime perf observer (`requestAnimationFrame` 60-frame rolling average) auto-flips to `low` if p99 frame > 20ms. Validation: Playwright on `--prefers-reduced-motion: reduce` simulated env + on `--disable-gpu` simulated Intel UHD env, asserts p99 ≤16.7ms.
- **VIS-07 doc drift sweep:** Two file edits:
  1. `/Users/ozai/.claude/projects/-Users-ozai-projects-dj-set-ai/memory/project_mascot_as_vtuber_personality_surface.md` — change "DJ bat" → "Neon Rebel" (preserve everything else).
  2. `mocks/vibemix-cinematic-storyboard.html` — replace any "Workbench" / "DSEG7" references with "Saira" / "Glass" / "Geist" per CDJ Whisper v5 vocab. Also align color tokens: any teal / electric-blue chip overlay → amber (`--amber-pri`). Visual-regression check: snapshot the storyboard hero panels and confirm color extraction matches the 5-black + 1-amber palette via `scripts/launch/check_storyboard_palette.py`.

### Hero Demo Wave (VIS-08, VIS-09)

- **VIS-08 storyboard v5 alignment:** Re-mock UI chip overlay frames inline in `mocks/vibemix-cinematic-storyboard.html`. 8-cut shot list:
  1. Cold open — DJ hands on FLX4 + dim room
  2. vibemix wizard "Welcome" frame (1 sec hold)
  3. Calibration screen with live audio meter rising
  4. Live session — mascot overlay subtle reaction
  5. AI line caption pop ("nice kick swap @ 2:33")
  6. EvidenceRegistry chip strip render (anti-slop receipts)
  7. Mascot Hype-man celebrate animation (mid-track moment)
  8. End card — vibemix logo + altidus.world/vibemix + "open-source"
  ≤8 cuts hard gate enforced via `scripts/launch/check_cut_count.py` parsing the `mocks/vibemix-cinematic-storyboard.html` `<section data-cut>` elements.
- **VIS-09 Francesco handoff package:** Three deliverables written to `docs/launch-prep/`:
  1. `SHOT-LIST.md` — 8-cut sequenced shot list with timing budget per cut + B-roll suggestions.
  2. `AUDIO-CAPTURE.md` — Gemini-voice + ambient + headphone-return as 3 separate tracks; sync via clapboard; sample rate 48kHz 24-bit WAV; record vibemix's session.wav alongside as canonical mix.
  3. `DEMO-MODE-CONFIG.md` — `vibemix.demo_mode` config flag (already partially in `src/vibemix/runtime/`) seeded with a deterministic 30-event sequence (track A → 2:33 kick swap → mascot celebrate → 4:50 layer drop → mascot teacher line → 6:00 end). Reset between takes via `vibemix --demo-mode reset`. Spec: 1080p min, 60fps min, 48kHz audio.

  Francesco-discharge documented in `KAAN-ACTION-LEGAL.md §VIS-09` — Phase 43 ships engineering; Francesco handles capture day post-Phase 43.

### Claude's Discretion
- Whether Plan 43-01 audit driver is its own plan or folded into 43-02..04 closure plans (planner decides; default = separate driver).
- Exact retarget skeleton mapping in `scripts/mascot/retarget_to_neon_rebel.py` (planner reads existing rig structure).
- Whether mood pool taxonomy lives in `mascot/pools.ts` (new) or extends existing `mascot/manifest.ts` (planner reads existing source).
- Plan count: 6-9 plans (3 waves; planner decides per-wave split).

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `mocks/vibemix-direction-final.html` — locked CDJ Whisper visual baseline (per memory).
- `mocks/vibemix-app-ui.html` — live session UI shape.
- `mocks/vibemix-cinematic-storyboard.html` — hero demo storyboard (needs v5 re-mock).
- `tauri/ui/src/tokens.css` — design tokens including `--glow-faint`, `--amber-pri`, `--blur-*` per memory.
- `tauri/ui/src/session/components/meter.ts` — existing meter (gradient renderer; Phase 43 rebuilds).
- `tauri/ui/src/mascot/` — existing mascot Three.js mount with prep_*.glb placeholders.
- `tauri/ui/src/wizard/` — 6-step onboarding flow.
- `tauri/ui/src/overlay/` — mascot overlay floating window.
- `tauri/ui/src/settings/` — settings drawer.
- `src/vibemix/runtime/` — backend hooks for demo-mode seed.

### Established Patterns
- Tier-1 surface convention = `tauri/ui/src/{session,mascot,overlay,wizard,settings}/`.
- Token-driven CSS only — no hex literals in component styles (enforced by `frontend-enforcement` skill).
- Visual regression baseline = Playwright snapshots committed under `tauri/ui/tests/visual/__snapshots__/`.
- Scripts for launch-prep checks live in `scripts/launch/`.
- Mascot assets in `tauri/ui/public/mascot/`.
- KAAN-ACTION discharges live in `KAAN-ACTION-LEGAL.md §<TAG>` sections (precedent from Phase 40 §AUDIO-05/06/07 and Phase 42 §GATE-01/02/03/05).

### Integration Points
- `frontend-enforcement` skill — auto-loaded for any frontend file edit per project CLAUDE.md.
- `gsd-ui-checker` + `gsd-ui-auditor` agents — paired audit pattern for Tier-1 surfaces.
- Phase 41 streaming pipe-through doesn't affect UI; Phase 42 ear-test toggle in debrief is a UI surface that should be in scope of VIS-01 audit.
- `scripts/release/check_no_hardcoded_model.sh` precedent for grep-gate scripts in launch.

</code_context>

<specifics>
## Specific Ideas

- 8-cut storyboard end card should read "open-source · MIT · github.com/bravoh/vibemix" (anchor for star-goal funnel per memory `project_github_star_goal`).
- The "amber peak hold" lozenge on the meter is the single most visceral CDJ Whisper signal — get it right first; everything else follows aesthetically.
- Storyboard ending should match the README hero one-liner from Phase 44 ("the only AI co-host that actually listens to your set") if Phase 44 has locked that copy; otherwise leave the end card with logo only and Francesco overlays text in post.
- "Neon Rebel" mascot mood for the celebrate clip should feel like a Pioneer CDJ headbob, NOT a generic VTuber dance — the visual direction is "DJ friend", not "vtuber slop".

</specifics>

<deferred>
## Deferred Ideas

- **/hatch user-generated mascots:** v2.x — locked per memory.
- **Live performance capture on shoot day:** Francesco's job post-Phase 43; not engineering scope.
- **Animation expansion beyond 5 clips:** v2.x.
- **Mascot rig replacement (Hunyuan3D / Meshy regeneration):** v2.x — locked rig "Neon Rebel" stays.
- **In-app theme switcher (light mode / alt accents):** v2.x — single CDJ Whisper accent is the locked aesthetic.

</deferred>

<canonical_refs>
## Canonical References
- `mocks/vibemix-direction-final.html` — visual direction baseline
- `mocks/vibemix-app-ui.html` — live session UI shape
- `mocks/vibemix-cinematic-storyboard.html` — hero demo storyboard (needs v5 re-mock)
- `mocks/vibemix-settings-drawer.html` — settings drawer reference
- `tauri/ui/src/tokens.css` — design token system
- Memory: `project_visual_direction_cdj_whisper` — visual direction locked
- Memory: `project_mascot_as_vtuber_personality_surface` — single mascot, mood variation
- Memory: `project_github_star_goal` — 500-1000+ star funnel anchors
- `.planning/REQUIREMENTS.md` — VIS-01..09
- `.planning/ROADMAP.md` — Phase 43 success criteria
- `.claude/skills/frontend-enforcement/SKILL.md` — frontend discipline (auto-loaded)
</canonical_refs>
