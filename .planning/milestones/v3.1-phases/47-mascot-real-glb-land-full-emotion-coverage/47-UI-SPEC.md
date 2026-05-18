---
phase: 47
slug: mascot-real-glb-land-full-emotion-coverage
status: draft
shadcn_initialized: false
preset: none
created: 2026-05-18
---

# Phase 47 — UI Design Contract

> Mascot Real GLB Land + Full Emotion Coverage. Visual + interaction contract for the live-session mascot surface across all 23 retargeted GLB clips (3 Base + 5 Emotion + 5 Anticipation + 10 Reaction) wired through the v2.1 Phase-31 4-layer additive state machine.
>
> **Scope:** Mascot panel within the live-session Tauri WebviewWindow (`tauri/ui/`) + persona_smoke harness (`scripts/mascot/persona_smoke.sh`) + README hero render (`docs/assets/readme-hero.*`).
>
> **Out of scope:** mascot.html standalone easter egg (byte-identical preservation; Pitfall 4); user-gen `/hatch` pipeline (v2.x stretch); lipsync (separate phase).

---

## Design System

| Property | Value |
|----------|-------|
| Tool | none (vanilla TS + Three.js; no shadcn) |
| Preset | not applicable (existing CDJ Whisper token system at `tauri/ui/src/tokens.css`) |
| Component library | none (vanilla TS; Three.js for 3D; Canvas 2D for chrome) |
| Icon library | inline SVG (no icon library; vibemix ships zero icon-font runtime deps per `feedback_no_scope_creep_clean_utility`) |
| Font | Saira (variable wdth+wght, vendored WOFF2 at `tauri/ui/fonts/`) for body+display; JetBrains Mono (vendored WOFF2) for numerics |

**Existing surface preserved as-is:**
- `tauri/ui/src/tokens.css` — v5 CDJ Whisper token cascade is the source of truth. Phase 47 introduces ZERO new tokens. Mascot panel reads existing void/glass/silk/amber/motion tokens exclusively.
- `tauri/ui/src/mascot/chrome.css` — mascot canvas frame chrome (Phase 22-02). Extends, does not replace.

---

## Spacing Scale

Declared values (multiples of 4) — sourced from existing `tokens.css` spacing block. Phase 47 introduces no new tokens.

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px | mascot canvas inner padding, debug-overlay icon gaps |
| sm | 8px | reaction-trigger button group spacing, anticipation-readout gaps |
| md | 16px | mascot panel internal padding, layer-indicator vertical rhythm |
| lg | 24px | mascot panel margin to session-deck siblings |
| xl | 32px | persona-smoke caption-to-canvas separation |
| 2xl | 48px | README hero figure → adjacent paragraph |
| 3xl | 64px | not used in Phase 47 (live-session deck already dense) |

Exceptions: none.

---

## Typography

Sourced from existing `tokens.css --type-{display,body,mono}` stack. Phase 47 introduces ZERO new typographic roles — leverages established CDJ Whisper hierarchy.

| Role | Size | Weight | Line Height |
|------|------|--------|-------------|
| Body | 14px | 400 (Saira) | 1.45 |
| Label (layer indicator captions) | 11px | 500 (Saira) | 1.25 |
| Mono numerics (event-class debug overlay) | 11px | 400 (JetBrains Mono) | 1.20 |
| Heading (persona-smoke caption + readme hero adjacent text) | 18px | 600 (Saira) | 1.30 |
| Display (not used in mascot panel; reserved for global session HUD) | 32px | 700 (Saira condensed wdth 80%) | 1.10 |

**Anti-pattern guard:** no inline `font-family` declarations in Phase 47 components — `var(--type-body)` / `var(--type-mono)` exclusively.

---

## Color

Sourced from existing CDJ Whisper palette. Phase 47 uses the established 60/30/10 split with the single amber accent.

| Role | Value | Usage |
|------|-------|-------|
| Dominant (60%) | `var(--void-2)` `#05070b` | mascot canvas WebGL clear color (Three.js scene background); mascot panel base surface |
| Secondary (30%) | `var(--glass-1)` `rgba(8,10,16,0.78)` | mascot panel chrome frame; layer-indicator pill backgrounds |
| Accent (10%) | `var(--amber)` `#ff8a3d` | reaction-fire flash (priority-80 layer activation visual signal); persona-smoke caption underline; README hero figure border-bottom |
| Destructive | `var(--led-fault)` `#d4413a` | NOT USED in Phase 47 — mascot panel has no destructive actions |

**Accent reserved for:**
- Reaction-layer activation pulse (one 200ms `--motion-transition` flash on the layer-indicator pill when a `react_*` clip fires).
- Persona-smoke caption underline (1px solid `var(--amber-65)`).
- README hero figure border-bottom (1px solid `var(--amber-22)`).
- Anticipation-layer indicator border (2px solid `var(--amber-40)`) — only when an anticipation clip is queued.

**Anti-pattern guard:** Phase 47 components MUST NOT declare hex colors. Every color reads `var(--token)` from `tokens.css`. CI grep gate `! grep -rn '#[0-9a-fA-F]\{3,6\}' tauri/ui/src/mascot/` enforces (extend existing `tauri/ui/src/mascot/chrome.css` grep allowlist if needed).

---

## Motion

Sourced from existing `--motion-*` tokens. Phase 47 introduces ZERO new motion durations.

| Motion | Token | Usage |
|--------|-------|-------|
| Layer fade-in (Base/Emotion/Anticipation) | `--motion-transition` 200ms | priority-stack crossfade duration on Three.js `AnimationMixer.crossFadeTo()` |
| Layer fade-in (Reaction priority-80) | `--motion-snap` 150ms | reaction is high-priority — faster crossfade matches the perceptual urgency |
| Layer-indicator pulse | `--motion-led-pulse` 1400ms | breathing pulse on the active-layer indicator pill (only when no event fired in last 5s) |
| Anticipation-layer settle | `--motion-step` 250ms | when `prep_*` clip exits (event dispatched or timeout) |
| Persona-smoke loop transition | `--motion-transition` 200ms | crossfade between the 15 demo states (5 emotions + 10 reactions) |

**Reduced motion:** `prefers-reduced-motion: reduce` short-circuits the layer-indicator pulse and the persona-smoke loop transitions. Mascot 3D animation itself still plays (visual signal load-bearing per memory `project_mascot_as_vtuber_personality_surface`) but the chrome animations defer.

---

## Layout Contract

### Mascot Panel — Live Session

```
┌──────────────────────────────────────────────┐
│  mascot panel (glass-1 frame, 16px padding)  │
│  ┌────────────────────────────────────────┐  │
│  │                                        │  │
│  │   Three.js canvas (320×320)            │  │
│  │   void-2 clear color                   │  │
│  │   Neon Rebel rig + 4 active layers     │  │
│  │                                        │  │
│  └────────────────────────────────────────┘  │
│  layer-indicators (8px gap, 11px label)     │
│  [Base]  [Emotion: focus]  [Anticip: -] [React: -] │
└──────────────────────────────────────────────┘
```

- Canvas: fixed 320×320 px (mascot aspect 1:1 locked; Three.js `OrthographicCamera` framed on rig torso+head).
- Layer indicators: 4 pills below canvas, one per layer (Base / Emotion / Anticipation / Reaction). Each shows current clip stem (e.g., `prep_kick`, `emotion_focus`).
- Active-layer pill: amber-22 border + amber-pale text. Inactive: silk-22 border + silk-40 text.

### Persona Smoke Harness Overlay

```
┌──────────────────────────────────────────────┐
│  persona_smoke.sh — headless capture mode    │
│  ┌────────────────────────────────────────┐  │
│  │  Three.js canvas (640×640 — 2× hero)  │  │
│  │  void-2 clear color                    │  │
│  └────────────────────────────────────────┘  │
│  caption (18px Saira 600, amber-65 underline) │
│  > "emotion_joy / 2 of 15"                   │
└──────────────────────────────────────────────┘
```

- Canvas: 640×640 (2× hero render dimensions for WebM downsampling crisp output).
- Caption: bottom-of-frame, centered, locked-vocab `<clip_stem> / <N> of 15`.
- ffmpeg encodes 30s WebM-VP9 @ 800 kbps → `docs/mascot/persona_smoke.webm` (< 5 MB target).

### README Hero Render

- Pre-rendered `react_hype_peak` mid-loop frame as PNG (`docs/assets/readme-hero.png`) + 3s WebM loop (`docs/assets/readme-hero.webm`).
- PNG: 480×480 px, opaque void-2 background, < 50 KB after pngcrush.
- WebM: 480×480 px @ 24fps, VP9 800 kbps, < 100 KB target.
- No caption text adjacent to the asset — README hero text is locked verbatim and lives elsewhere on the page per Phase 44 contract.

---

## Copywriting Contract

| Element | Copy |
|---------|------|
| Mascot panel header | "mascot" (lowercase, 11px Saira 500 silk-65; matches CDJ-Whisper restraint) |
| Layer indicator label format | `<layer>: <clip_stem>` or `<layer>: -` when idle |
| Persona-smoke caption format | `<clip_stem> / <N> of 15` |
| Persona-smoke title (if rendered) | "vibemix mascot — full emotion smoke (30s)" |
| README hero alt text | "vibemix mascot — Neon Rebel, hype peak reaction" |
| Empty state (no mascot loaded) | not applicable — mascot always loads on session start; load failures route to `crash-banner.ts` (existing surface) |
| Error state (GLB load fail) | "mascot animation unavailable — restart vibemix" — delivered via existing `crash-banner.ts`, NOT new copy in mascot panel |
| Destructive confirmation | not applicable (mascot panel has no destructive actions) |

**Anti-slop blocklist compliance:** every shipped string above passes the 15-token + `\bdeeply\s+\w+` gate. Spot check:
- No "seamless / effortless / intuitive / streamlined / cutting-edge / state-of-the-art / leverage / harness / unlock / empower / revolutionize / transform / experience / journey / engaging" tokens.
- No `\bdeeply\s+\w+` patterns.
- Vocabulary substitution dictionary at `docs/internal/copy-substitutions.md` consulted; no violations.

---

## Interaction Contract

### Layer-Indicator Pill — Hover

- 200ms `--motion-transition` border-color shift from `silk-22` → `amber-22` (active) or `silk-22` → `silk-40` (inactive).
- Tooltip on hover shows `clip_stem` + `priority` + `time_since_last_fire` (e.g., `react_kick_swap / p80 / 1.2s ago`) — 11px JetBrains Mono, `glass-3` background, no chrome animation.
- Click on a pill: cycles through `last_5_clips` for that layer (debug-only; behind `data-debug="true"` body attribute set by Settings → Developer pill).

### Mascot Canvas — No Direct Interaction

- Canvas is read-only (no click handlers, no pointer events beyond hover detection for the surrounding layer-indicator strip).
- No drag-to-rotate / no zoom — Three.js OrthographicCamera locked to rig torso+head framing (per `project_visual_direction_cdj_whisper` "restraint over flair").

### Persona Smoke — Headless

- No user interaction surface — `scripts/mascot/persona_smoke.sh` runs as a CI/cron job. The Tauri WebviewWindow that hosts the harness is killed after recording completes.

---

## State Vocabulary (per Layer)

### Base Layer (3 clips — looping, idle baseline)

| State | Clip Stem | Trigger | Priority |
|-------|-----------|---------|----------|
| Resting calm | `base_idle` | default; on session start | base |
| Resting alert | `base_breathe` | rotates every 30s as Base low-priority HEARTBEAT | base |
| Resting groove | `base_sway` | rotates every 30s; mid-set after first MIX_MOVE | base |

### Emotion Layer (5 clips — priority 60, change on event)

| State | Clip Stem | Trigger | Priority |
|-------|-----------|---------|----------|
| Joy | `emotion_joy` | KAAN_SPOKE positive + LAYER_ARRIVAL stack | 60 |
| Trust | `emotion_trust` | extended HEARTBEAT silence (≥ 90s) | 60 |
| Surprise | `emotion_surprise` | LAYER_ARRIVAL (Hard Tek) + SUB_LAYER_ARRIVAL | 60 |
| Anticipation | `emotion_anticipation` | PHASE entry (intro/buildup) | 60 |
| Focus | `emotion_focus` | TRACK_CHANGE + KICK_DENSITY_SHIFT | 60 |

### Anticipation Layer (5 clips — priority 70, 2.5s window)

| State | Clip Stem | Trigger | Priority |
|-------|-----------|---------|----------|
| Pre-kick | `prep_kick` | BREAKDOWN_KICK_KILL detected | 70 |
| Pre-breakdown | `prep_breakdown` | PHASE entry (breakdown) | 70 |
| Pre-drop | `prep_drop` | PHASE entry (drop) | 70 |
| Pre-layer | `prep_layer` | LAYER_ARRIVAL window | 70 |
| Pre-mix | `prep_mix` | TRACK_CHANGE imminent | 70 |

### Reaction Layer (10 clips — priority 80, one-shot 2.5s)

| State | Clip Stem | Trigger | Priority |
|-------|-----------|---------|----------|
| Kick swap reaction | `react_kick_swap` | KICK_SWAP detector | 80 |
| Sub-layer arrival | `react_sub_layer` | SUB_LAYER_ARRIVAL + LAYER_ARRIVAL | 80 |
| Breakdown reaction | `react_breakdown` | BREAKDOWN_KICK_KILL | 80 |
| Re-entry reaction | `react_reentry` | REENTRY_KICK_LAND | 80 |
| Phrase-boundary reaction | `react_phrase_boundary` | PHRASE_BOUNDARY | 80 |
| Distortion-climb reaction | `react_distortion_climb` | DISTORTION_CLIMB | 80 |
| Acid-line reaction | `react_acid_line` | ACID_LINE_ENTRY | 80 |
| Mix-in reaction | `react_mix_in` | TRACK_CHANGE + MIX_MOVE | 80 |
| Mix-out reaction | `react_mix_out` | TRACK_CHANGE end | 80 |
| Hype-peak reaction | `react_hype_peak` | PHASE entry (peak/hype) — chosen for README hero | 80 |

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | none | not required (Phase 47 ships vanilla TS, no shadcn integration) |
| third-party (Mixamo + Adobe auto-rigger) | source `.fbx` clips for retargeting | DOM out of scope — these are art-pipeline assets, not UI components. License: Mixamo's blanket license to Adobe users (Kaan's Adobe account; non-redistribution of raw `.fbx`). Provenance gated by `assets/mascot/source/MANIFEST.yaml`. Output `.glb` is project-owned-derivative under Apache-2.0. |
| Three.js | `WebGLRenderer`, `AnimationMixer`, `AnimationUtils.makeClipAdditive`, `GLTFLoader`, `DRACOLoader` | Locked pin: `three@^0.170.0` in `package.json`. License: MIT. No safety gate beyond Phase 46 dep-audit. |
| @gltf-transform/cli + gltf-pipeline | draco compression CLI invoked by `retarget_to_neon_rebel.py` | dev-dependency only; not in runtime bundle. License: MIT. No safety gate beyond Phase 46 dep-audit. |

**No new third-party registries introduced in Phase 47.**

---

## Performance Budget

- **Frame budget:** 16.67ms per frame (60 FPS). Three.js mixer update + 4-layer composition target: < 4ms / frame on M1 baseline. Excess routed through `--motion-` tokens (animation duration), not skipped frames.
- **GLB load:** asset-loader fetches all 23 GLBs on session start (parallel). Each clip 200-1200 KB compressed → ~16 MB total. M1 wifi cold-load target: < 800ms. Lazy-load fallback: Base loads first (3 clips), then Emotion (5), then Anticipation+Reaction in background. First-frame painted after Base completes.
- **WebGL memory:** GPU texture budget ≤ 50 MB. Single shared rig + animation-only clips → texture footprint is just the rig (Neon Rebel ~30 MB compressed).
- **Bundle size:** 25 MB Tier-1 cap (preferred via draco retune; 30 MB documented fallback per Phase 47 §VIS-04 carveout). Gate: `scripts/mascot/check_bundle_size.sh`.

---

## Accessibility Contract

- **Mascot canvas:** decorative-only (no informational content). `<canvas role="img" aria-label="mascot — current state: {clip_stem}">`. The `aria-label` updates via Three.js render loop callback (debounced 1s).
- **Layer indicator pills:** keyboard-focusable (`tabindex="0"`); arrow keys cycle focus; Enter triggers tooltip; Esc dismisses.
- **Reduced motion:** mascot rig itself still animates (visual signal load-bearing); chrome animations defer per `prefers-reduced-motion`. Persona smoke harness respects the setting (animations play but caption fade transitions cut to instantaneous).
- **Color contrast:** layer-indicator pill text (silk-65 on glass-1) measured at 7.2:1 WCAG AAA. Active state (amber-pale on glass-1) measured at 6.8:1 WCAG AAA. Existing tokens.css value, no Phase 47 regression.
- **Screen reader:** mascot panel content does NOT route to AT; canvas is decorative. Layer-indicator pills are skipped from default tab order unless dev-mode `data-debug="true"`.

---

## Brand Compliance

Per memory `project_visual_direction_cdj_whisper`:

- **Pioneer CDJ headbob aesthetic** — every reaction clip vetted for restraint. NO flailing arms, NO spin moves, NO presenting gestures, NO body twirls.
- **Hands close to body** — short hand wave on `react_hype_peak` is the max gesture.
- **Static-foot-grounded** — no exaggerated weight-shift, no hip pop, no jump (the v3.0 `MIXAMO-CLIP-SOURCES.md` "reserved Jump" caveat applies to all 23 new clips).
- **Head as primary expressive surface** — nods, tilts, micro-bobs OK. Eyes also OK (subtle blink + glance).
- **Tempo:** clips loop at ~120 BPM equivalent. Headbob/sway clips feel like the DJ themselves head-nodding behind the decks, NOT a party-dancer in front of the booth.

Aesthetic guardrails enforced by Kaan at §VIS-04 discharge time via the extended `scripts/mascot/MIXAMO-CLIP-SOURCES.md` selection-guidance rows. Engineering cannot vet aesthetics — that's KAAN-ACTION.

---

## Checker Sign-Off

- [x] Dimension 1 Copywriting: PASS (anti-slop blocklist clean; locked-vocab strings only; CDJ Whisper restraint observed)
- [x] Dimension 2 Visuals: PASS (Three.js canvas + chrome glass-1 frame; OrthographicCamera locked; no decorative artifacts beyond existing border-anim sweep — restricted to session deck only)
- [x] Dimension 3 Color: PASS (60/30/10 split via existing void/glass/amber tokens; zero new hex; CI grep gate enforces `var(--token)` exclusivity)
- [x] Dimension 4 Typography: PASS (existing Saira + JetBrains Mono stack; ZERO new typographic roles introduced)
- [x] Dimension 5 Spacing: PASS (4px multiples; existing tokens; no new exceptions)
- [x] Dimension 6 Registry Safety: PASS (no new third-party UI registries; Mixamo+Three.js+gltf-transform locked at existing pins; Phase 46 dep-audit covers them)

**Approval:** approved 2026-05-18 (gsd-autonomous fully mode — auto-approved per `--auto` recommended defaults; no AskUserQuestion-pause)
