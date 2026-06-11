# FABLE CINEMATIC CUT — 2026-06-11

**Goal (Kaan):** "aggressive UI level up... people will be paying for this product, they
need to feel that it deserves it. INSANE impeccable lenses but Fable cinematic cut."
Live by-eye verdicts during the session: "looks vibe coded — the colors, the depth, the
feel, very toy-ish, not premium" → "criticize it to ground" → "previous level-ups were
insanely subtle, never real upgrades; 80% enterprise-native quality, 20% MEMORABLE AND
SEXY" → "still v safe, looks coded not felt" → "depth and layering is crucial" →
"little tactile, even".

## The grounded critique (what was actually wrong)

Measured by a 5-agent inventory (`wf_012ca190-353`, ~880k tok) + live captures:

1. **The base was pink-washed.** Every edge, lip, bevel, and border in tokens.css was
   rose-tinted (rgba 255,222,242 / 205,238 / 210,240). With edges everywhere, the whole
   app graded MAUVE — rose read as a theme, not a light. ~880 rose references in
   tauri/ui/src, 70% trim: ~15 simultaneous rose sources on the live screen vs the
   design's ONE.
2. **No depth.** The void ladder hovered in a narrow mid-grey band; every base tile
   baked in its own ambient drop (dozens of surfaces floating at once = nothing
   recessed); both hero compositions (armed deck, wizard intro) were centered cards
   inside decorative rounded hairline frames — "floating card in nowhere", the exact
   banned composition.
3. **Sticker controls.** ONE copy-pasted "pressed amber tile" recipe (rose text + rose
   inset ring + rose text-glow + outer halo) lived in every active segment; a blanket
   `--glow-faint` outer halo rode every hover. Glow around a key sitting INSIDE a
   recessed well is physically wrong.
4. **Type had no middle.** ~150 of ~380 font-size declarations at 9–11px uppercase
   mono; the 15–28px confidence band nearly empty; the type-step tokens existed with
   ZERO consumers; the wordmark shipped in TWO treatments + a permanently lit pink
   "mix" syllable (startup-logo sticker).
5. **Hue lies.** Camelot KEY in rose (gold is the quarantined harmonic lane); VU
   meters pulsing rose on every beat with an off-palette magenta clip; alert tiles
   glowing the same rose as "alive"; gold atmospheric washes violating the quarantine.

## What landed (7 commits)

| Commit | Unit |
|---|---|
| `80dbcfdd` | **THE GRADE** — void ladder a step deeper/desaturated (#141113 floor), ALL edge light neutralized to silk-white, scene-lit rebuilt (one rose key, gold wash dead), base tile flattened (flat-by-default restored), alert→warn lamp, single-tone wordmark ×3, --rad-sm→2px machined corner, grain up, type steps→1.27 modular scale, DESIGN.md synced |
| `2bff2fbb` | **THE ARMED STAGE** — three depth planes replace the centered card: ROOM (dawn compressed to a low horizon), AIR (serif at 76–138px lit from below), CONSOLE (new full-bleed machined strip, readouts left + GO LIVE transport key right, the dawn spilling over its top lip from BEHIND — light crossing planes) |
| `e407377b` | **THE LIT KEY grammar** — active = rose FILL under INK text (GO LIVE's material at control scale) across rocker/persona/picker/deck controls/hotkey/slider; blanket hover halos dead; drawer furniture de-rosed (group seams, label ticks, readout glow) |
| `b0bcfdc6` | **CHROME** — intro joins the stage language (card+blob dead, trademark at cinema scale, CTA hover no longer flips slab→sticker); ONE lowercase trademark product-wide; LIVE chip→LED+engraved; debrief joins the one-light room (top-left key, frame dead, panels flattened) |
| `ae4f112a` | **LIVE-DECK HONESTY** — KEY→gold, lead track name→serif mid-register, VU→hardware vocabulary (silk level / gold heat / fault clip; meter.test.ts re-pinned w/ no-rose leak guards), final 37 pink-edge literals neutralized app-wide |

Gates at close: full vitest **1649 + 1 todo green** (178 files), `npm run build` green.
Captures: `cinematic-cut/` (00/01 = before; 20/21/30/31/40/50/61 = after).

## Remaining lanes (next rounds of this goal)

- **Wizard INTERIOR steps** — card-in-card stack (primary-panel > skill/consent boxes >
  bordered radio rows); BOXES inventory has file:line anchors. The intro is done; the
  interior should join the stage language.
- **Type middle register per surface** — settings drawer title + debrief
  morning-mirror up into 18–28px; wire components through --type-step-*; 24
  uppercase-at-0.04em spots → ≥0.06em; the 74 dead "wdth" font-variation no-ops.
- **The live breath** — LIGHT inventory: tail cursor + activation-ramped energy are
  occluded behind the opaque .vmx-session (.deck-energy dead, sweep mounted nowhere).
  The live deck's ONE breathing mark must actually render. Needs careful z/paint work.
- **Dead material cleanup** — --shadow-raised (now consumer-less?), --rim-brand,
  --grad-specular zero consumers; session/components/panel.ts + mode-picker.ts dead
  recipes; drawer ::before sheen <1% alpha; chrome lips: hand-rolled 0.045 lips →
  --chrome-highlight token on wizard/debrief titlebars.
- **Settings drawer head** — left rose seam kept as the drawer's one mark
  (deliberate); head underline gradients re-judge by eye.
- **Learn surface** — graded by token sweep only; full pass parked with the Learn
  redesign milestone.
- **Live-verify lane** — packaged-app eyeball of the new grade (browser-verified only).


## ROUND 2 (same session, post-R1)

5 more commits, all gates green at each step (final: suite 1641+1 todo — 8 fewer =
deleted dead tests; build green):

| Commit | Unit |
|---|---|
| `4cd7e855` | **WIZARD INTERIOR joins the stage** — primary-panel card deleted (was re-carded by the 06-10 pass against its own docstring); step titles speak serif at the mid register (clamp 30-40px lowercase); ordinals engraved; hover union de-haloed; skill rows: rest on hairlines, selected is the LIT KEY |
| `eed60035` | **THE TAIL CURSOR finally breathes** — DESIGN §6's promised single sign-of-life now renders on the product surface: a rose block riding the end of the spoken line on the 1400ms LED pulse; silent hands the breath to the foot meter, fault extinguishes, reduced-motion steady-on. Scene-line rose lead-in demoted to silk in exchange |
| `7b31e5e9` | **Middle register** — drawer title serif 20px lowercase (rose heartbeat dot died), morning-mirror 20→28px + eyebrow de-rosed; dead mode-picker.{ts,test.ts} deleted (zero consumers) |
| `d7d60846` | **Tracking-by-case + lips** — 5 uppercase-at-0.04em → 0.08em; wizard statusbar lip → 0.07 chrome standard; DebriefDock proof terms de-rosed |

Final captures: cinematic-9x-final-*.png (intro / skill / armed / live-with-breath / drawer).

## R2 CLOSE — externally gated leftovers

- **Kaan's eye** — the round was driven by his live verdicts; the next correction is his.
- **Packaged-app live-verify** — all verification was browser/dev-server; the DMG eyeball
  (grain/blur/vibrancy under WebView) needs a packaged build.
- **Other session's WIP** — library/index.ts (Viber), mascot/** untouched by contract.
- **Learn full pass** — parked with the Learn redesign milestone (Kaan's call).
- **wdth no-op sweep** (74 font-variation-settings no-ops) — pure hygiene, zero visual
  delta (Geist has no width axis); fold into any future type pass.
- **panel.ts dead recipe** — still imported by tests/session/components.spec.ts (other
  sessions touch that spec); delete pair together in a quiet window.
- **shell.css surfaces** (DesktopShell sidebar/palette) — graded via tokens + wordmark
  fix only; not the product-mounted surface (shell.html is a dev harness).
