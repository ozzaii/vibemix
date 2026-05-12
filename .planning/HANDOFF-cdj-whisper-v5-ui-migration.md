# HANDOFF — CDJ Whisper v5 UI Migration

**Created:** 2026-05-12 (end of strategic + visual direction session)
**Resume topic:** Apply picked UI direction (CDJ Whisper v5) to the actual Tauri UI, then formalize the migration via Phase 14 GSD workflow.
**For:** Next Claude session, after Kaan runs `/clear`.

---

## TL;DR — what you (next Claude) do first

1. Read this file (you're already doing it).
2. Read `mocks/vibemix-direction-final.html` — the v5 mock IS the visual contract. Internalize every `:root` variable, glass alpha, glow distance, animated border config.
3. Read `tauri/ui/src/tokens.css` (369 lines) — internalize the OLD FL-Studio tactile vocabulary that's about to be replaced.
4. **Execute Phase 1 of the migration: rewrite `tokens.css`** with v5 design system + backward-compat shim. Don't break existing components — remap, don't delete.
5. Tell Kaan to run `cd tauri/ui && npm run tauri dev` (verify exact command in `tauri/ui/package.json`). He screenshots; you iterate.
6. After visual smoke test green → update ROADMAP.md Phase 14 + REQUIREMENTS.md POLISH-* → `/gsd-discuss-phase 14`.

Do NOT skip the prototype step and go straight to Phase 14 GSD. Visual feedback on real data is required input for PLAN.md.

---

## What got decided this session

### Visual direction = **CDJ Whisper v5**

> *"Pioneer-grade dark hardware in library mode. Seen through icy frosted glass with night-rave ambient color bleed and a slow amber light traveling around panel borders."*

Replaces the prior **FL-Studio retro-tactile** direction that was already partially built into Phase 11 + Phase 12 code. The FL-Studio direction was rejected as "too generic" / "no character."

Iteration history (kept for reference):
- `mocks/vibemix-direction-explorations.html` — 4-direction explorations (Acid Flyer / Soft Toy / Editorial / Cyber Cassette). Historical only.
- `mocks/vibemix-direction-final.html` — CDJ Whisper v1 → v5 iterations live here. **Current state = v5. This is the design contract baseline.**

### v5 design system (lift this into `tokens.css`)

```css
:root {
  /* Void stack — cool, layered blacks */
  --void:   #000000;
  --void-1: #020205;
  --void-2: #05070b;
  --void-3: #0a0c12;
  --void-4: #11141c;

  /* Glass surfaces — DARKER than v4, deck dominates */
  --glass-1: rgba(8, 10, 16, 0.78);    /* primary panel */
  --glass-2: rgba(12, 14, 22, 0.62);   /* secondary panel */
  --glass-3: rgba(2, 3, 6, 0.88);      /* recessed (display window, mood track) */
  --glass-edge: rgba(255, 255, 255, 0.065);
  --glass-top:  rgba(255, 255, 255, 0.055);

  /* Silk text (replaces --ink stack) */
  --silk:    #d6cfc7;
  --silk-65: rgba(214, 207, 199, 0.65);
  --silk-40: rgba(214, 207, 199, 0.40);
  --silk-22: rgba(214, 207, 199, 0.22);

  /* Amber accent (replaces --phosphor — different shade) */
  --amber:      #ff8a3d;  /* was #ffa12e in Phase 11/12 — DELIBERATE swap */
  --amber-deep: #ff5a1a;
  --amber-pale: #ffb88a;
  --amber-22:   rgba(255, 138, 61, 0.22);
  --amber-40:   rgba(255, 138, 61, 0.40);
  --amber-65:   rgba(255, 138, 61, 0.65);

  /* Night-rave ambient body washes — atmospheric only, never on chrome */
  --rave-magenta: rgba(192, 56, 224, 0.055);
  --rave-pink:    rgba(255, 92, 188, 0.038);
  --rave-cyan:    rgba(72, 152, 255, 0.042);
  --rave-purple:  rgba(118, 56, 224, 0.030);
  --rave-teal:    rgba(64, 220, 200, 0.022);

  /* Glass blurs */
  --blur-glass:         blur(32px) saturate(140%);
  --blur-glass-light:   blur(16px) saturate(120%);
  --blur-glass-display: blur(6px)  saturate(105%);

  /* Glow — RESTRAINED (v5 reduced ~40% from v4) */
  --glow-faint:  0 0 5px var(--amber-22);
  --glow-soft:   0 0 6px var(--amber-40), 0 0 14px var(--amber-22);
  --glow-strong: 0 0 8px var(--amber-65), 0 0 18px var(--amber-22);
}
```

Plus the **animated border** (slow amber light traveling around panel perimeters):

```css
@keyframes borderSweep { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.border-anim {
  position: absolute; inset: 0; border-radius: inherit;
  background: conic-gradient(
    from 0deg at 50% 50%,
    transparent 0%, transparent 30%,
    rgba(255,138,61,0.28) 45%,
    rgba(255,220,180,0.42) 50%,
    rgba(255,138,61,0.28) 55%,
    transparent 70%, transparent 100%);
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
          mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
  -webkit-mask-composite: xor;
          mask-composite: exclude;
  padding: 1px; pointer-events: none; z-index: 4;
  animation: borderSweep 22s linear infinite;
}
.border-anim.slow { animation-duration: 32s; }
.border-anim.rev  { animation-direction: reverse; }
```

Place a `<div class="border-anim"></div>` as first child inside each major panel (session, mascot overlay).

### Backward-compat shim (so existing components don't break on day-1)

Map OLD Phase 11/12 token names → NEW v5 values:

```css
/* Backward-compat shim — drop these after Phase 14 component-level audit completes */
--bg:           var(--void-1);
--panel:        var(--glass-1);
--panel-lift:   var(--glass-2);
--panel-deep:   var(--void-2);
--groove:       var(--glass-3);
--bezel-1:      transparent;            /* no more 3D bevels in v5 */
--bezel-2:      transparent;
--bezel-3:      transparent;
--brushed-hi:   var(--glass-top);
--brushed-lo:   rgba(0, 0, 0, 0.5);
--ink:          var(--silk);
--ink-dim:      rgba(214, 207, 199, 0.55);
--ink-deep:     rgba(214, 207, 199, 0.30);
--ink-engraved: rgba(214, 207, 199, 0.15);
--phosphor:      var(--amber);
--phosphor-warm: var(--amber-deep);
--phosphor-soft: var(--amber-22);
--phosphor-glow: var(--glow-soft);
--phosphor-halo: 0 0 22px var(--amber-22);
--col-mascot:    0;  /* mascot is now overlay window, not embedded corner — Phase 12 reserved space is freed */
```

After Phase 14 component-level audit completes, these aliases get removed and components reference v5 tokens directly.

### Body background (night-rave ambient — apply in app shell, not tokens.css)

```css
body {
  background-image:
    radial-gradient(ellipse 92% 78% at 50% 45%, transparent 0%, rgba(0,0,0,0.5) 75%, rgba(0,0,0,0.9) 100%),
    radial-gradient(ellipse 55% 38% at 18% 22%, var(--rave-magenta), transparent 60%),
    radial-gradient(ellipse 48% 36% at 84% 78%, var(--rave-cyan),    transparent 55%),
    radial-gradient(ellipse 60% 42% at 55% 105%, var(--rave-pink),   transparent 60%),
    radial-gradient(ellipse 35% 28% at 92% 12%, var(--rave-purple),  transparent 55%),
    radial-gradient(ellipse 28% 22% at 5% 88%,  var(--rave-teal),    transparent 55%),
    linear-gradient(180deg, #02030a 0%, #000000 55%, #030208 100%);
  background-attachment: fixed;
  background-color: #000;
}
```

Plus a film-grain `body::before` (full SVG noise blob in the mock).

---

## Migration approach (Path C — confirmed by Kaan)

Path A (formal Phase 14 GSD only) was rejected as too slow — can't plan without seeing the swap on real data first. Path B (custom code, no GSD) was rejected as too risky for 10k LOC base. **Path C is the middle:**

1. **Phase 1 — Quick token swap (~1-2 hours):**
   Rewrite `tauri/ui/src/tokens.css` with v5 tokens + backward-compat shim. Most components inherit new aesthetic via cascade. **Don't break anything; just remap.**
2. **Phase 2 — Visual smoke test:**
   Kaan runs the dev build. Screenshots → side-by-side with mock. Identify components that didn't auto-flip (hard-coded values, custom box-shadows, bezel-style gradients, brushed-aluminum textures).
3. **Phase 3 — ROADMAP + REQUIREMENTS update:**
   - `ROADMAP.md` Phase 14 → rename "FL-Studio Polish Phase (Critique → Execute Loop)" to "**CDJ Whisper v5 Migration + Polish**." Same critique→execute loop, new visual target.
   - `REQUIREMENTS.md` POLISH-01..06 → reference CDJ Whisper baseline (mock file) instead of FL-Studio retro-hardware. POLISH-04 still "no AI slop" but reference now means "no FL-Studio tactile residue."
4. **Phase 4 — `/gsd-discuss-phase 14` → `/gsd-plan-phase 14`:**
   With prototype delta documented, write atomic-commit migration plan. Likely waves: tokens (done) → session window → settings drawer → wizard surfaces → calibration glass → mascot prep (Phase 13 prep work) → final critique→execute polish loop.
5. **Phase 5 — `/gsd-execute-phase 14`:**
   Atomic commits, verification gates. `frontend-enforcement` skill auto-loads — when conflict with CDJ Whisper direction, **CDJ Whisper wins** (project-local override; documented in `[[project_visual_direction_cdj_whisper]]` memory).

---

## Memory anchors (auto-load in fresh session)

These persist across sessions via the project memory system; fresh session will see them in CLAUDE.md context. **Read these before doing any work** — they encode binding decisions you must respect.

- `project_visual_direction_cdj_whisper.md` — full v5 design system spec (the source of truth this handoff summarizes)
- `project_mascot_as_vtuber_personality_surface.md` — single 3D mascot, character "Neon Rebel" (Meshy AI-generated, asset bundle in hand at `/Users/ozai/Downloads/Meshy_AI_Neon_Rebel_biped/`)
- `project_anti_slop_grounded_gemini_thesis.md` — central anti-slop principle; every feature evaluated by "what hallucination class does it close?"
- `project_one_click_install_hard_req.md` — every dep choice rated green/yellow/red on install impact
- `project_v2_planning_active.md` — v2 scope under Kaan's control; don't autonomously kick off `/gsd-explore` or `/gsd-new-milestone`
- `project_v2_open_candidates.md` — full v2 backlog (Mixxx OSC + pyrekordbox + Gemini Embedding 2 confirmed; ProDJ Link + stems + CLAP deferred)
- `feedback_no_scope_creep_clean_utility.md` — no stems, no CLAP, no multi-provider, no enterprise
- `feedback_no_clap_use_gemini_embedding.md` — Gemini Embedding 2 over CLAP, never propose CLAP even when research recommends it
- `project_gemini_embedding_2.md` — affirmative spec of Gemini Embedding 2 capabilities + use cases
- `project_github_star_goal.md` — 500-1000+ stars target frames every UX/scope decision

---

## Watchouts (things to NOT trip on)

- **`--phosphor: #ffa12e`** (Phase 11/12 amber) → **`--amber: #ff8a3d`** (v5 amber) is a deliberate visual swap, not a silent rename. The new tone is slightly more orange / less yellow. Verify in browser before celebrating.
- **`--col-mascot: 256px`** in Phase 12 reserved an embedded mascot corner in the session UI. v5 frees this — mascot is overlay window, not embedded. Set to `0` (or remove); recover the layout space. Phase 13 CONTEXT.md Open Q 2 documents the reallocation decision (recommend leave empty for v2.0, defer art to Phase 14).
- **`--bezel-1/2/3`** + **`--brushed-hi/lo`** vocab is FL-Studio tactile residue. Map to transparent or to glass primitives in the shim, then audit out at the component level during Phase 14. Anywhere these are used with hard-coded shadows (skeuomorphic 3D bevels), the shadow values need v5 glass treatment instead.
- **`frontend-enforcement` skill** auto-loads on every UI-touching agent. It may say things contradicting CDJ Whisper v5 (e.g., it was authored when FL-Studio direction was canonical). **`[[project_visual_direction_cdj_whisper]]` memory explicitly overrides it project-locally.**
- **Don't go straight to Phase 14 GSD without the token-swap prototype first.** Visual feedback on real data is required input for the PLAN.md. The mock is necessary but not sufficient.
- **Phase 13 mascot work** is paused for character + animations Kaan is generating in Meshy AI (character codename "Neon Rebel", full asset bundle in hand 2026-05-12 at `/Users/ozai/Downloads/Meshy_AI_Neon_Rebel_biped/` — base GLB + 20 separate skinned animation GLBs, single track each, rig baked in). Resume order: **Phase 14 UI direction migration first**, then **Phase 13 mascot integration** on top of clean UI.
- **Backdrop-filter perf** — `blur(32px) saturate(140%)` on multiple panels can hammer integrated GPUs. Test on a non-dev machine (Phase 20 fresh-machine rehearsal will catch but earlier review good). Fallback: lighter blur (`blur(16px)`) on lower-end devices.

---

## Files modified in this session

Already on disk:
- `.planning/ROADMAP.md` — Phase 13 rewritten from "Reactive Mascot (Avery)" SVG-pose-vocabulary to "**3D Mascot Screen Overlay**" (Meshy GLB + Three.js + sticky overlay + menu-bar icon + mood swap)
- `.planning/REQUIREMENTS.md` — MASCOT-01..09 rewritten (added MASCOT-08 WS subscription + MASCOT-09 menu-bar/tray icon); POLISH-03 reworded for animation library
- `.planning/phases/13-3d-mascot-overlay/13-CONTEXT.md` — full Phase 13 context (6 implementation areas, 6 open questions, cross-phase dependencies)
- `mocks/vibemix-direction-explorations.html` — 4-direction explorations (historical reference)
- `mocks/vibemix-direction-final.html` — **CDJ Whisper v5 (current = source of truth for the visual contract)**
- Memory (10 files): visual direction, mascot, anti-slop thesis, install constraint, v2 planning, v2 open candidates, scope-creep feedback, no-CLAP, Gemini Embedding 2, GitHub star goal

Not yet on disk (the migration work):
- `tauri/ui/src/tokens.css` — still on FL-Studio tactile vocab. **This is the first file to touch in the new session.**
- ROADMAP.md Phase 14 description (currently "FL-Studio Polish") — update after prototype validates
- REQUIREMENTS.md POLISH-01..06 — update after prototype validates
- All `tauri/ui/src/**/*.css` and any inline CSS — audit + refactor during Phase 14 execution

---

## v2 inventory (the strategic conversation outcome)

See `[[project_v2_open_candidates]]` memory for the full living list. TL;DR:

- **Confirmed v2:** Mixxx OSC adapter, Mixxx controller map transpiler, pyrekordbox priors, Gemini Embedding 2 library coach, post-session debrief loop, learning mode tiers
- **Deferred:** ProDJ Link path (niche audience + install friction), stem separation (scope creep), CLAP/local embeddings (Gemini Embedding 2 used instead)
- **Backlog:** OBS browser-source mascot path, Sonic Pi/TidalCycles algorave demo bait, ai-remixmate energy-arc lift, `/hatch` user-gen mascot pipeline, `$0 djay Free tier` landing CTA, Serato static via triseratops + What's Now Playing, Beat This! for post-session debrief, Open Beat Control / Carabiner sidecars, CAPTION.Ninja pattern, openDAW watch-list

v2 milestone planning fires via `/gsd-new-milestone` — **only after v1 ships** (~early June 2026 target). The strategic v2 conversation is captured for then.

---

## Resume command in fresh session

After Kaan runs `/clear`, he'll likely just say something like "let's do this" or "start the UI migration" or invoke `/gsd-progress`. Your first response:

> "Reading the v5 mock + current tokens.css + this handoff. Then I'll rewrite tokens.css with v5 design system + backward-compat shim — should take ~30min. After that you run `cd tauri/ui && npm run tauri dev`, screenshot the live session UI, and we iterate from real data."

Then execute Phase 1 of the migration. Wait for visual smoke test feedback before continuing.

Don't ask broad clarifying questions — every binding decision is in memory or this file. If genuinely ambiguous, default to what the v5 mock says.
