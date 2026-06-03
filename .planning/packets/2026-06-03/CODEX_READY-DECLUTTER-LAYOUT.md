# DECLUTTER + LAYOUT — vibemix (2026-06-03)

> CODEX_READY packet. Lead-designer synthesis of 7 per-surface declutter/layout audits + 2 adversarial verifications. Every fix is tozpembe-faithful ("Forged Obsidian Chrome", register=product), em-dash-free, and scoped to CLUTTER + LAYOUT only. Copy/jargon/token-contrast swaps shipped earlier this session are out of scope and not re-flagged.

---

## 1. PROOF-LEDGER

**Surfaces covered (7):**

| # | Surface | Primary file | densityScore (before) | Lens |
|---|---------|--------------|----------------------|------|
| S1 | Live deck (co-host hero) | `tauri/ui/src/session/SessionLayout.ts` | 62 | clutter + layout |
| S2 | Library / vibe engine window | `tauri/ui/library.html` + `src/library/library.css` + `index.ts` | 58 | clutter + layout |
| S3 | Learn practice booth | `tauri/ui/src/learn/learn-window.ts` + `styles/learn.css` | 46 | clutter + layout |
| S4 | Debrief review dock | `tauri/ui/src/shell/DebriefDock.ts` | 44 | clutter + layout |
| S5 | Settings drawer | `tauri/ui/src/settings/SettingsDrawer.ts` + `components/*` | 38 | clutter + layout |
| S6 | Floating co-host pill | `tauri/ui/src/pill/` (pill.css + next-suggestion.ts) | 61 | clutter + layout |
| S7 | Desktop shell (sidebar/stage/footer/palette) | `tauri/ui/src/shell/` (app.ts, DesktopShell.ts, CommandPalette.ts, shell.css) | 72 | clutter + layout |

**Lenses applied per surface:** One-Rose (at most one breathing/sweeping mark per panel), 20/80 (warm-void dominates, rose <=10%), no nested cards / no identical card grids / no hero-metric template, vary-spacing-for-rhythm (>=1.25 step ratio), gold quarantined to Camelot/key/heat numerics, no #000/#fff (tokens or file-idiom rgba), 5 cardinal invariants intact.

**Adversarial verifications resolved:**
- S1 `.vmx-voice::after` grille cut: **safeToCut=true** (pure decorative pseudo-element, no data-wire, no test pin, advances One-Rose). Source-confirmed at lines 468-482 (`content:""`, `pointer-events:none`, static gradient).
- S2 command-field orbit cut + rose-pool "freeze": **safeToCut=true** with one correction — the bottom rose pool (css:1054-1056) is ALREADY a static radial, no animation. The "freeze the rose pool" step is a near no-op; land the orbit removal, treat the pool freeze as cosmetic-only.

Two source-spot-checks I ran confirm the audit line refs are accurate: `SessionLayout.ts` rail (260-278) and foot (655-670) carry the identical 3-shadow bordered-card recipe the audit flags; `settings/components/group.ts:55-66` confirms the rose `::before` seam on EVERY group.

---

## 2. REDESIGN BOARD

| Surface | Issue | Type | file:line | Fix | Risk |
|---------|-------|------|-----------|-----|------|
| S1 | `.vmx-voice::after` dot-matrix grille = 2nd decorative texture on the hero, dilutes One-Rose | CLUTTER | SessionLayout.ts:468-482 | Delete the rule. Keep `::before` faceplate (452-463) so the slab still reads machined | safe |
| S1 | Rail is a full bordered glass card wrapping chrome controls | LAYOUT | SessionLayout.ts:260-278 | Demote to borderless control strip: drop border + gradient + 3 box-shadows + min-height, keep flex | safe |
| S1 | Foot is a 2nd full bordered glass card wrapping bpm/key/meter | LAYOUT | SessionLayout.ts:655-670 | Replace card with `border-top:1px solid var(--glass-edge)` only; readout engraved into void | safe |
| S1 | bpm 22px / key 18px / labels 9px read at near-equal weight | HIERARCHY | SessionLayout.ts:676-683 | Unify bpm+key to one mono scale (both 20px), demote bpm/key micro-labels to silk-12; key stays amber-quarantined | safe |
| S1 | 3 panels share one padding/margin recipe = monotone rhythm | LAYOUT | SessionLayout.ts:255,267,659 | Vary >1.25: rail tight (6px), voice generous clamp(28px,4.5vw,52px), foot close under hero | safe |
| S1 | Persona key micro-label "persona" beside the lit mood value | CLUTTER | SessionLayout.ts:307-319,1016 | Cut the key span; keep lit mood value (button title/aria already name it) | safe |
| S1 | Idle reports readiness twice: 4-cell proof grid AND 2 ghost prose lines | CLUTTER | SessionLayout.ts:501-516,1346-1350 | Keep the scannable grid + IDLE_HERO_LINE + 1 next-step; drop the ghost readiness lines | moderate |
| S1 | Status right-meta crams output+voice+genre in one footer string | CLUTTER | SessionLayout.ts:1444-1445 | Collapse to the one fact that changes (output profile + short device); drop voice+genre | moderate |
| S1 | Always-on 5-input mono list + 4 separators competes at glance | LAYOUT | SessionLayout.ts:718-757 | Render lit only NOT-ok inputs; all-ok collapses to one quiet "inputs ok"; keep claim-policy pill (758) | moderate |
| S2 | Decorative command-field orbit (3 dots + readout) behind chat | CLUTTER | library.html:218-228 / css:934-1022 | Cut the orbit. (verified safe; aria-hidden, opacity 0.28, hardcoded text) | safe |
| S2 | Right rack shows 2 empty placeholders + parent idle = 3 idle labels | CLUTTER | library.css:1100-1118 | Keep ONE idle line until a tool fires | safe |
| S2 | qecho "conversation" sub-label beside a title already saying Viber | CLUTTER | library.html:212-213 | Hide in chat mode; show only when echoing a real query/seed/theme | safe |
| S2 | Curate/build placeholder AND a 3-chip example row = same idea twice | CLUTTER | library.html:128-132 | Keep one-tap chips, tighten to short distinct vibes | safe |
| S2 | Operator 3-cell grid shown idle atop intro + starters (nested card) | CLUTTER | library.html:255-277 | Hide-until-relevant: reveal only once a run is in flight | moderate |
| S2 | Corpus 4-stat 2x2 bordered tile grid (hero-metric) | CLUTTER | library.html:177-194 | Collapse to one inline Crate+spend line, demote Search/Failed diagnostics | moderate |
| S2 | Two stacked near-identical readiness panels (model + agent setup) | CLUTTER | library.html:195-205 | Merge to one Ready block, two lines, one Install button | moderate |
| S2 | Near-monotone left-console rhythm (all opens at 18px) | LAYOUT | library.css:360,464,591 | Group via spacing: mode-switch tight (12px), open sp-5 before Run, rule + sp-5 before diagnostics | safe |
| S2 | qecho 13px vs Viber label 11px = under 1.25 step | HIERARCHY | library.css:35-43,702-704 | Drop qecho to mono 10-11px tertiary (--silk-40); title vs caption | safe |
| S2 | Operator brief is a bordered panel of bordered cells (nested) | LAYOUT | library.css:1239-1356 | Flatten one level: render operator borderless, split by slab hairlines (keep grid gap:1px) | safe |
| S2 | Titlebar dot breathes while rose pool + margin rule + orbit glow | LAYOUT | library.css:103-112,1052-1063,1149-1158 | One breath per panel: freeze orbit (cut), keep Viber margin rule lit, pool static-by-state | safe |
| S2 | Gold on ordinal slot/step indices (outside heat quarantine) | HIERARCHY | library.css:1581-1583,1752-1759 | Slot rank 01/02/03 to mono tertiary ink; reserve --gold for BPM/key/energy | safe |
| S2 | Center 420px starved vs left 326 / right 342; idle pad floats intro | LAYOUT | library.css:139,1047 | Widen center to minmax(480px,1fr), trim right rack to ~300px, reduce idle chat-thread padding | moderate |
| S2 | Ingest 52ch seg-note + control + folder field + label = dense setup | LAYOUT | library.html:80-95 | Drop seg-note to one line / title on segments; ingest = calmest mode | safe |
| S3 | learn-booth-brief 3-col dl restates title + readiness (nested tiles) | CLUTTER | learn-window.ts:359-372 / learn.css:409-469 | Cut. Command line already says do-this + how-i-check in one grounded sentence | moderate |
| S3 | learn-booth-proof span = 3rd print of same screen readiness | CLUTTER | learn-window.ts:350 / learn.css:358-361 | Fold readiness into the pulse line only; drops a competing rose accent | safe |
| S3 | learn-booth-kicker "ready to practice" above a START button | CLUTTER | learn-window.ts:346 / learn.css:316-325 | Cut the kicker; tightens the stack by one row | safe |
| S3 | Latency pip prints NNms during normal practice (dev telemetry) | CLUTTER | learn-window.ts:1329 / learn.css:1069-1093 | Keep the pip; show numeric text only on warn/fault | moderate |
| S3 | Flat 10-13px micro-label band, only the 22px serif breaks it | HIERARCHY | learn.css:316-461 | After cuts: 22 serif title / 13 command / 11 readiness ladder only | safe |
| S3 | Whole booth stacks every region at one flat var(--sp-2) gap | LAYOUT | learn.css:290 | Vary: kicker->title sp-1, title->command sp-4, command->pulse sp-3 | safe |
| S3 | Panel nests bordered brief tiles + bordered earned cells (2 levels) | LAYOUT | learn.css:418-426,516-534 | After cuts, zero nested borders; title/command/pulse sit on the one slab | safe |
| S3 | Two breathing marks at idle: booth pulse re-fires + titlebar breathe | LAYOUT | learn.css:640-642,92-101 | One-Rose: idle = only titlebar under-stroke breathes; pulse fires on real state change | safe |
| S3 | Uniform sp-4 padding on a 7-region panel of mixed weight | LAYOUT | learn.css:293 | Asymmetric: padding sp-5 sp-5 sp-4 so title floats, buttons sit near lower lip | safe |
| S3 | learn-footer = permanent 40px verbatim trademark rail | GATED | learn-window.ts:404,813-814 / learn.css:1822-1832 | Demote to "trademarks" line in chooser drawer; KEEP exported constant for test | gated |
| S3 | learn-booth-earned 6-cell skill wall on the idle booth (densest) | GATED | learn-window.ts:373-381,562-607 / learn.css:471-634 | Collapse to 1-line summary on booth; move 6-cell wall into "choose lesson" drawer | gated |
| S4 | 4-cell payback strip restates the gate the title+sub+metrics state | CLUTTER | DebriefDock.ts:454-459,213-246 | Cut; collapse to one sub-line | safe |
| S4 | 3-cell readiness-metrics grid duplicates per-row meta (identical-card) | CLUTTER | DebriefDock.ts:460-464,247-274 | Merge to one mono readout line "24m · 31 events · ready" | safe |
| S4 | Per-row meter bar (rose glow) restates pill + reason + payoff in % | CLUTTER | DebriefDock.ts:355-371,613-615 | Show only on "capture more" rows; zero glow on ready rows | safe |
| S4 | Per-row payoff line = same idea as reason line, stacked | CLUTTER | DebriefDock.ts:609-611,348-354 | Cut payoff; keep reason, the Open button is the CTA | safe |
| S4 | Decorative ::before scanline + vertical rose seam at 34% misaligns grid | CLUTTER | DebriefDock.ts:43-54 | Cut; warm-void + token grain carry the material | safe |
| S4 | row-state pill + reason line = label-then-sentence redundancy | CLUTTER | DebriefDock.ts:585-587,325-337 | Keep pill as scannable badge; reason only on "capture more" rows | safe |
| S4 | Mast proof dl (Timeline/why/Next) = static feature-bullet marketing | CLUTTER | DebriefDock.ts:437-441,116-140 | Demote to one quiet sub-line; mast = kicker + serif title + sub | moderate |
| S4 | Rose in 3 places at once (seam + meter glow + ready washes) | LAYOUT | DebriefDock.ts:50-53,189-194,305-310,363-371 | One rose carrier: brand-08 wash on the best-candidate ready panel only | safe |
| S4 | Monotone sp-3 everywhere = no group boundaries | LAYOUT | DebriefDock.ts:33,65,145,278,295 | Ladder: sp-2 intra-row / sp-4 between-rows / sp-5 between-sections | safe |
| S4 | Readiness panel nests bordered grids inside a bordered card | LAYOUT | DebriefDock.ts:176-274 | After cuts: title + sub + one hairline-separated mono line, no inner borders | safe |
| S4 | 3 of 4 text roles sit at 13px (sub/metric/payback) | HIERARCHY | DebriefDock.ts:198-243,266-274 | 18/14/11 ladder: title 18/650, sub 14/400, numerics mono 11 tracked | safe |
| S4 | Each row stacks 6 elements; list reads as a wall | LAYOUT | DebriefDock.ts:292-371,567-634 | Ready row = 2 lines (date+Open / meta); reason/meter only on "capture more"; ready row gets sp-4 | safe |
| S4 | Mast and sessions columns ~50/50 weight, no clear primary | LAYOUT | DebriefDock.ts:30-31,431-466 | Lighten mast to header; right column (the action) is primary; 0.72/1fr ratio fine | moderate |
| S5 | Trust rail = contract block + 4 cells restating PERSONA/OUTPUT | CLUTTER | SettingsDrawer.ts:1118-1149,531-545 | Collapse to ONE honest status line (grounded/listening + recording-vault bytes) | moderate |
| S5 | Every one of 12 groups paints a rose seam + brand dot (12x One-Rose) | CLUTTER | settings/components/group.ts:55-66 | Reserve rose seam + brand dot for the ONE top status module; rest = neutral tick | safe |
| S5 | HELP DOCS + SOURCE both open the same GITHUB_REPO_URL | CLUTTER | components/help-group.ts:289-298 | Merge to one "GITHUB" row | safe |
| S5 | Two near-identical deferred-apply captions (voice + output restarts) | CLUTTER | SettingsDrawer.ts:1296-1301 | Merge to one "changes apply on Sven's next line / audio restart" note per group | safe |
| S5 | 12 groups uniform margin + padding = PERSONA reads same as 1-toggle | LAYOUT | components/group.ts:38,139 | Cluster into 3 bands (Live tuning / Your data / Setup), sp-5 between, 10px within; vary pad by control count | safe |
| S5 | Drawer is one glass surface nesting 12 recessed lit modules | LAYOUT | components/group.ts:35-51 | Most groups = header + hairline section; reserve recessed-module treatment for one status block | safe |
| S5 | Trust rail is a repeat(2,1fr) card grid (identical-card, heaviest block) | LAYOUT | SettingsDrawer.ts:531-545 | Replace with single full-width status line; one rose dot, no per-field cards | safe |
| S5 | Title 13 / headers 11 / rows 10 all in a 3px band, nothing dominant | HIERARCHY | SettingsDrawer.ts:240-254 | Lift the 3 band labels to ~14px Saira so they organize the 12 flat groups | safe |
| S5 | mascot/help/learn/performance read legacy --silk/--amber aliases | LAYOUT | components/mascot-group.ts:84,113,126-132 | Repoint active-state aliases to canonical brand/text/border (match-the-file); no new tokens | moderate |
| S5 | Genre RELOADING overlay = full amber glowing 2nd sign-of-life | LAYOUT | SettingsDrawer.ts:350-374 | Replace with quiet inline state on the GENRE picker (rose tick / "reloading" sub) | moderate |
| S5 | DIAGNOSTICS (slop %/stripped %/LIVE badge) is dev instrumentation | GATED | SettingsDrawer.ts:1618-1630 | Demote behind HELP/advanced; render only when bypassActive | gated |
| S5 | MODE rocker is overridden by LENS (LENS_TO_MODE_MOOD), a dead control | GATED | SettingsDrawer.ts:1304-1316 | Cut the MODE rocker from PERSONA (structural, separate from done copy swap) | gated |
| S5 | MASCOT ships ENABLE + CLICK-THROUGH + MOOD though off-by-default | GATED | components/mascot-group.ts:235-297 | Show ENABLE only by default; reveal CLICK-THROUGH + MOOD when enabled | moderate |
| S5 | HELP TROUBLESHOOT AUDIT = label row + 3 always-"unknown" check rows | GATED | components/help-group.ts:300-339 | Collapse 3 checks behind a disclosure; drop status dots until they carry real state | moderate |
| S6 | 3 rose progress rails fire at once on the collapsed face (One-Rose) | CLUTTER | pill.css:1160,1304,1704 | Keep the full-width pill__streak heat rail; drop the grade-chip + level-bead ::after underlines | safe |
| S6 | Grade chip + level bead = 2 bordered glass tiles on the pill glass | LAYOUT | pill.css:1098,1257 | Fold LVn into grade chip (LABEL +Nxp · LVn), one border; drop glass-on-glass | moderate |
| S6 | Peek why-row mixes silk + brand chip tones, competes with action pill | LAYOUT | pill.css:2957,2963 | Collapse to one quiet silk meta line; reserve brand chip for expand panel | moderate |
| S6 | Peek card = 7-row receipt for a hover glance | CLUTTER | next-suggestion.ts:1292,1316 / pill.css:2947 | Suppress why-chips + cue-confidence in peek; keep label / title / transition+cue-rail / 1-line grade | moderate |
| S6 | Peek care reason shown in grade row AND again as warn pill | CLUTTER | pill.css:3024 / next-suggestion.ts:1332 | Drop the standalone warn reason-pill in peek; grade-row reason carries it | safe |
| S6 | Collapsed waveform stays painted at 0.42 during peek (no signal) | CLUTTER | pill.css:1462 | Fade pill__wave to 0 (max-width:0) on data-peek so face is quiet while drawer owns attention | safe |
| S6 | Expand panel = 4 identical sp-2 gaps, hero gets no extra air | LAYOUT | pill.css:1973 | sp-3 below reaction line (hero), sp-1 between citation strip and deck chips (cluster receipts) | safe |
| S6 | Peek type scale 14/10/9/8 = sub-1.25 steps, rows blur | HIERARCHY | pill.css:2926,2939,3004 | Title 14 anchor; demote transition/why/grade to ONE 9px secondary at silk-65 | safe |
| S6 | Collapsed face badges nest border+glass-2 on the pill glass | LAYOUT | pill.css:1108,1266 | Drop borders + glass-2 fills; grade = borderless mono ink riding the pill body | safe |
| S6 | Row 7px top pad pushes content below a blank forehead | LAYOUT | pill.css:725,618 | Reduce 7px top pad to sp-1, let drag strip overlay; center dot/label/grade in the 42px | safe |
| S6 | Reaction-echo replays a 1.8s glowing all-caps label on collapse | GATED | pill.css:990 / index.ts:70 | Shorten echo window, drop to normal-weight silk label (keep dot tone) | gated |
| S7 | Footer = 3 colored dots + 2 dividers (spec wants dot + label) | CLUTTER | app.ts:153-163 / shell.css:899-929 | Library/voice badges dot-only when ok, dot+label only on warn/fault/setup; conn dot stays | moderate |
| S7 | Cmd+K summary = 4-cell identical-card grid duplicating footer state | CLUTTER | DesktopShell.ts:149-166 / CommandPalette.ts:158-170 / shell.css:1058-1090 | Cut the grid; open straight onto the action list; one inline sentence if a state line is wanted | moderate |
| S7 | Palette legend (Enter/Esc/arrows kbd chips) always shown | CLUTTER | CommandPalette.ts:142-147 / shell.css:1205-1231 | Quiet to one muted line, or show only when query is empty | safe |
| S7 | Deck idle scene chips render 3 dash placeholders ("— BPM", "—", "—") | CLUTTER | DesktopShell.ts:64-68 / shell.css:476-494 | display:none until activation is listening/live (gate visibility like the opacity ramp) | safe |
| S7 | Palette placeholder enumerates 4 nouns (reads as a feature list) | CLUTTER | CommandPalette.ts:130 | One verb-led line ("Jump to a surface or run a control"); only the list-of-four shape | safe |
| S7 | Grounding panel sections all sit at one uniform interval | LAYOUT | shell.css:875-877 | Keep sp-5 between groups; widen inter-group to sp-6 OR drop per-section hairline (gap groups) | safe |
| S7 | Sidebar active row differs only by color/fill (near-invisible at glance) | HIERARCHY | shell.css:236-247 | Add font-weight contrast to active .sb-label so "where you are" wins on weight; keep gap:4px rail | safe |
| S7 | Palette summary cells = 3 nested bordered boxes | LAYOUT | shell.css:1064-1070 | If summary survives: drop per-cell border+fill, borderless label/value pairs | moderate |
| S7 | Empty state stacks 3 different center widths (420 / 34ch / 440) | LAYOUT | shell.css:424,506-515 | Align to one --empty-measure so the empty state reads as one column | safe |
| S7 | Learn earned-wall folded as a repeat(3,1fr) bordered grid under stage | GATED | shell.css:746-788 | Compact to a borderless horizontal skill strip, or show only the next-earnable skill | gated |
| S7 | Folded booth-panel uses a dense sp-1 row gap inside the shell | GATED | shell.css:642-663 | Learn-owner grid; lift booth row gap to sp-2 if Kaan wants shell calm carried in | gated |

---

## 3. PRIORITY ORDER (cheapest + safest first)

### Tier 1 — safe, pure-style (spacing / hierarchy / decoration removal; no feature loss, no logic)
1. S1 — Cut `.vmx-voice::after` grille — SessionLayout.ts:468-482
2. S1 — De-card rail to borderless control strip — SessionLayout.ts:260-278
3. S1 — De-card foot to a single top-hairline readout — SessionLayout.ts:655-670
4. S1 — Unify bpm+key to 20px mono, demote labels to silk-12 — SessionLayout.ts:676-683
5. S1 — Vary the 3-panel vertical rhythm (>1.25 step) — SessionLayout.ts:255,267,659
6. S1 — Cut the "persona" key micro-label — SessionLayout.ts:307-319,1016
7. S2 — Cut the command-field orbit (verified safe) — library.html:218-228 / css:934-1022
8. S2 — Collapse right-rack to one idle line until a tool fires — library.css:1100-1118
9. S2 — Hide qecho "conversation" in chat mode — library.html:212-213
10. S2 — Tighten curate/build chips, drop the placeholder duplication — library.html:128-132
11. S2 — Group left-console spacing (sp-5 before Run + diagnostics) — library.css:360,464,591
12. S2 — Demote qecho to mono 10-11px tertiary — library.css:35-43,702-704
13. S2 — Flatten operator brief to borderless (slab hairlines) — library.css:1239-1356
14. S2 — One breath per panel (keep Viber margin rule lit) — library.css:103-112,1052-1063,1149-1158
15. S2 — Move ordinal slot ranks off gold to tertiary ink — library.css:1581-1583,1752-1759
16. S2 — Ingest seg-note to one line — library.html:80-95
17. S3 — Cut learn-booth-proof span (fold readiness into pulse) — learn-window.ts:350 / learn.css:358-361
18. S3 — Cut learn-booth-kicker — learn-window.ts:346 / learn.css:316-325
19. S3 — Vary booth row gaps (sp-1/sp-4/sp-3) — learn.css:290
20. S3 — Collapse booth type to 22/13/11 ladder — learn.css:316-461
21. S3 — Remove nested booth borders after cuts — learn.css:418-426,516-534
22. S3 — One breathing mark at idle (titlebar only) — learn.css:640-642,92-101
23. S3 — Asymmetric booth padding (sp-5 sp-5 sp-4) — learn.css:293
24. S4 — Cut the 4-cell payback strip — DebriefDock.ts:454-459,213-246
25. S4 — Merge 3-cell metrics grid to one mono line — DebriefDock.ts:460-464,247-274
26. S4 — Cut per-row payoff line — DebriefDock.ts:609-611,348-354
27. S4 — Cut decorative ::before scanline + 34% rose seam — DebriefDock.ts:43-54
28. S4 — Hide per-row meter (+ glow) except on "capture more" — DebriefDock.ts:355-371,613-615
29. S4 — Reason only on "capture more"; pill stays the badge — DebriefDock.ts:585-587,325-337
30. S4 — One rose carrier (ready panel wash only) — DebriefDock.ts:50-53,189-194,305-310,363-371
31. S4 — Ladder sp-2/sp-4/sp-5 spacing — DebriefDock.ts:33,65,145,278,295
32. S4 — De-nest readiness panel after cuts — DebriefDock.ts:176-274
33. S4 — 18/14/11 readiness hierarchy — DebriefDock.ts:198-243,266-274
34. S4 — Reduce ready rows to 2 lines (date+Open / meta) — DebriefDock.ts:292-371,567-634
35. S5 — Reserve rose seam + brand dot for the one top status module — group.ts:55-66
36. S5 — Merge HELP DOCS + SOURCE to one GITHUB row — help-group.ts:289-298
37. S5 — Merge the two deferred-apply captions — SettingsDrawer.ts:1296-1301
38. S5 — Cluster 12 groups into 3 spaced bands — group.ts:38,139
39. S5 — De-containerize groups to hairline sections — group.ts:35-51
40. S5 — Replace trust-rail card grid with one status line — SettingsDrawer.ts:531-545
41. S5 — Lift the 3 band labels to ~14px Saira — SettingsDrawer.ts:240-254
42. S6 — Drop 2 of 3 collapsed-face rose rails (keep streak) — pill.css:1160,1304,1704
43. S6 — Drop care reason warn-pill duplicate in peek — pill.css:3024 / next-suggestion.ts:1332
44. S6 — Fade pill__wave to 0 on data-peek — pill.css:1462
45. S6 — Vary expand-panel rhythm (sp-3 hero, sp-1 receipts) — pill.css:1973
46. S6 — Widen peek type contrast to 2 tiers (14 / 9 silk-65) — pill.css:2926,2939,3004
47. S6 — De-card collapsed-face badges (borderless mono) — pill.css:1108,1266
48. S6 — Reduce row top pad to sp-1, let drag overlay — pill.css:725,618
49. S7 — Quiet/conditional palette legend — CommandPalette.ts:142-147 / shell.css:1205-1231
50. S7 — display:none the idle dash scene chips until live — DesktopShell.ts:64-68 / shell.css:476-494
51. S7 — One verb-led palette placeholder — CommandPalette.ts:130
52. S7 — Vary grounding-panel inter-group spacing — shell.css:875-877
53. S7 — Add font-weight contrast to active nav label — shell.css:236-247
54. S7 — Align empty state to one --empty-measure — shell.css:424,506-515

### Tier 2 — moderate (touches conditional render / per-component token alias / responsive)
55. S1 — Drop idle ghost readiness lines (keep grid + hero + next-step) — SessionLayout.ts:1346-1350
56. S1 — Collapse status right-meta to output-only — SessionLayout.ts:1444-1445
57. S1 — Lit only NOT-ok inputs; collapse all-ok to "inputs ok" — SessionLayout.ts:718-757
58. S2 — Hide operator grid until a run is in flight — library.html:255-277
59. S2 — Collapse corpus 4-stat grid to one inline line — library.html:177-194
60. S2 — Merge the two readiness panels into one — library.html:195-205
61. S2 — Widen center to minmax(480px,1fr), trim right rack — library.css:139,1047
62. S3 — Cut learn-booth-brief 3-col dl (nested-card violation) — learn-window.ts:359-372 / learn.css:409-469
63. S3 — Latency NNms text only on warn/fault — learn-window.ts:1329 / learn.css:1069-1093
64. S4 — Demote mast proof dl to one sub-line — DebriefDock.ts:437-441,116-140
65. S4 — Make right column primary, lighten mast — DebriefDock.ts:30-31,431-466
66. S5 — Collapse trust rail to one honest status line — SettingsDrawer.ts:1118-1149,531-545
67. S5 — Repoint legacy --silk/--amber aliases to canonical — mascot-group.ts:84,113,126-132
68. S5 — Replace genre reload overlay with inline state — SettingsDrawer.ts:350-374
69. S5 — MASCOT: show ENABLE only, reveal rest when on — mascot-group.ts:235-297
70. S5 — Collapse HELP troubleshoot checks behind disclosure — help-group.ts:300-339
71. S6 — Fold LVn into grade chip (one border) — pill.css:1098,1257
72. S6 — Collapse peek why-row to one silk meta line — pill.css:2957,2963
73. S6 — Slim peek to 4-row glance — next-suggestion.ts:1292,1316 / pill.css:2947
74. S7 — Footer badges dot-only when ok — app.ts:153-163 / shell.css:899-929
75. S7 — Cut Cmd+K 4-cell summary grid — DesktopShell.ts:149-166 / shell.css:1058-1090
76. S7 — De-nest palette summary cells (if it survives) — shell.css:1064-1070

### Tier 3 — GATED feature-removals (flag for Kaan, do NOT land blind)
77. S5 — Cut the LENS-overridden MODE rocker from PERSONA — SettingsDrawer.ts:1304-1316 (dead control per Bug D, but a removed surface; Kaan call)
78. S5 — Gate DIAGNOSTICS behind advanced/bypassActive — SettingsDrawer.ts:1618-1630 (dev instrumentation; confirm no live-monitoring use)
79. S3 — Collapse learn-booth-earned 6-cell wall to summary + move to chooser — learn-window.ts:373-381,562-607 / learn.css:471-634 (skill-wall is a feature surface)
80. S3 — Demote learn-footer trademark to chooser drawer — learn-window.ts:404,813-814 / learn.css:1822-1832 (LEGAL: keep the exported constant; `test_disclaimer_present.py` source-scans it, verify before moving)
81. S6 — Shorten reaction-echo window + de-glow label — pill.css:990 / index.ts:70 (changes a deliberate performance beat)
82. S7 — Compact learn earned-wall fold to a strip / next-skill — shell.css:746-788 (learn surface owner's grid)
83. S7 — Lift folded booth row gap to sp-2 — shell.css:642-663 (learn-owner grid, cross-surface call)

---

## 4. PER-SURFACE APPENDIX

### S1 — Live deck (co-host hero) — `tauri/ui/src/session/SessionLayout.ts` — densityScore 62

**clutterCuts**
- **CUT** `.vmx-voice::after` dot-matrix grille (468-482) — second non-load-bearing texture on the single most important panel; One-Rose wants exactly one lit mark. Removing it lets the spoken line own the slab. **VERIFIED safeToCut=true** (no data-wire, no JS handle, no test pin; `::before` faceplate 452-463 keeps the machined read). Risk: safe.
- **DEMOTE** rail bordered glass card (260-278) to a borderless control strip — drop border + 3-layer gradient + 3 inset shadows + min-height:64px, keep flex + persona/controls as self-contained buttons. Risk: safe.
- **DEMOTE** foot bordered glass card (655-670) to `border-top:1px solid var(--glass-edge)` only — the docstring calls it "a single master strip behind one hairline", not its own slab. Risk: safe.
- **COLLAPSE** status right-meta "HP default out · Adam · techno" (1444-1445) to output profile + short device; drop set-once voice + genre. Risk: moderate.
- **MERGE/DROP** idle redundancy (501-516, 1346-1350) — the 4-cell proof grid and the two ghost readiness lines report the same input states twice. Keep the scannable grid + IDLE_HERO_LINE + one next-step; drop the ghost prose lines. Risk: moderate.
- **CUT** "persona" key micro-label (307-319, 1016) — the lit mood word + rail context already say what it is; button title/aria name it. Risk: safe.

**layoutFixes**
- Make the voice slab the ONLY bordered+shadowed surface (250-256, 260-278, 655-670): one lit slab on void, a thin readout hairline below, a quiet control strip above (the 20/80 the docstring describes).
- Vary vertical rhythm >1.25 (255, 267, 659): rail thin (padding 6px, drop min-height), voice generous clamp(28px,4.5vw,52px), foot close under hero (margin-top sp-3, padding 10px 0).
- Foot hierarchy (676-683): unify bpm+key to one mono scale (both 20px), demote bpm/key labels to silk-12 so numerics carry the read; key stays amber-quarantined (correct today); the meter is the third distinct form.
- Idle composition (501-506, 802-803): treat the slab as one centered column with explicit gap rhythm (grid then IDLE_HERO_LINE then one next-step; sp-5 group-to-hero, sp-3 within); drop `margin:0 auto` on the grid in favor of column align.
- Inputs row (718-757, 1133): render lit only NOT-ok inputs, collapse all-ok to one quiet "inputs ok"; keep the claim-policy pill (758) since it is the citation receipt (Invariant #2). Preserves honest fault surfacing (Invariant #5).

### S2 — Library / vibe engine window — densityScore 58

**clutterCuts**
- **HIDE-UNTIL-RELEVANT** Operator 3-cell grid (html:255-277) — nested card in the chat slab duplicating starters; reveal only once a run is in flight. Risk: moderate.
- **MERGE** right-rack idle placeholders (css:1100-1118) — keep one idle line until a tool fires. Risk: safe.
- **COLLAPSE** corpus 4-stat 2x2 grid (html:177-194) to one inline Crate+spend line; demote Search/Failed diagnostics. Risk: moderate.
- **MERGE** the two readiness panels (html:195-205) to one Ready block, two lines, one Install button. Risk: moderate.
- **CUT** command-field orbit (html:218-228) — decorative orbital ornament under the transcript. **VERIFIED safeToCut=true** (aria-hidden, pointer-events:none, opacity 0.28, hardcoded placeholder text, no JS binding, no test pin). Risk: safe.
- **DEMOTE** qecho "conversation" sub-label (html:212-213) — hide in chat mode; earn it only on a real query/seed/theme. Risk: safe.
- **DEMOTE** curate/build placeholder + 3-chip duplication (html:128-132) — keep one-tap chips, tighten to short distinct vibes. Risk: safe.

**layoutFixes**
- Group left-console spacing (css:360,464,591): mode-switch->field tight (12px), open sp-5 before the hero Run, rule + sp-5 before diagnostics.
- Hierarchy (css:35-43,702-704): drop qecho to mono 10-11px tertiary (--silk-40); keep center label 11px/0.22em.
- Flatten operator brief (css:1239-1356): render borderless, columns split by slab hairlines (keep operator__grid gap:1px, drop the outer panel border+shadow).
- One breath (css:103-112,1052-1063,1149-1158): freeze the orbit (cut), keep only the Viber margin rule lit; bottom rose pool is **already a static radial** (correction from verification) so its "freeze" is a near no-op; drive opacity by state, not motion.
- Gold quarantine (css:1581-1583,1752-1759): slot ranks 01/02/03 are ordinals, move to mono tertiary ink; reserve --gold for BPM/key/energy.
- Width (css:139,1047): widen center to minmax(480px,1fr), trim right rack to ~300px, reduce idle chat-thread padding so intro+starters sit higher.
- Ingest (html:80-95): drop the 52ch seg-note to one line or a title on the segments.

> Note (file idiom): library.css uses literal rgba per its own convention. Match that file; do not introduce token vars here. No #000/#fff added.

### S3 — Learn practice booth — densityScore 46

**clutterCuts**
- **CUT** learn-booth-brief 3-col dl (ts:359-372 / css:409-469) — "do this" = recommended.title already in boothTitle + command; "how i check" restates readinessProofLine; three nested tiles = nested-card violation, data triplicated. The command line already says do-this + how-i-check in one grounded sentence. Risk: moderate.
- **MERGE** learn-booth-proof span (ts:350 / css:358-361) — third print of the same readiness; fold into the pulse line only (also removes a competing rose accent). Risk: safe.
- **COLLAPSE** learn-booth-earned 6-cell skill wall (ts:373-381,562-607 / css:471-634) to the one-line summary on the booth; move the 6-cell wall to the opt-in "choose lesson" drawer. Risk: **gated** (skill-wall is a feature surface).
- **CUT** learn-booth-kicker "ready to practice" (ts:346 / css:316-325) — label-on-label above title + START. Risk: safe.
- **DEMOTE** learn-footer trademark rail (ts:404,813-814 / css:1822-1832) to a "trademarks" line in the chooser drawer. Risk: **gated** — LEGAL: `test_disclaimer_present.py` source-scans the constant; keep it exported, verify the test before moving the paint.
- **HIDE-UNTIL-RELEVANT** latency pip NNms text (ts:1329 / css:1069-1093) — dev-visible telemetry; keep the pip, show numeric only on warn/fault. Risk: moderate.

**layoutFixes**
- Vary row gap per the ladder (css:290): kicker->title sp-1, title->command sp-4, command->pulse sp-3 (override the one global sp-2).
- Type (css:316-461): after cuts, 22px serif title / 13px command / 11px readiness = clean 22/13/11 ladder.
- De-nest (css:418-426,516-534): after the brief cut + earned collapse, zero nested bordered containers; if the earned summary stays, render borderless inline.
- One breath (css:640-642,92-101): at idle only the titlebar under-stroke breathes; booth pulse fires on real state change (lesson picked/completed), not passive readiness recomputes.
- Asymmetric padding (css:293): sp-5 sp-5 sp-4 so the title floats and buttons sit near the lower lip.
- Overlay activation matrix (css:828-831,926-934,1772-1779): verify exemplar chip / live-meter / progress-list / booth are mutually exclusive; if exemplar + live-meter can co-occur in a beatmatch lesson, clamp the schematic max-width so it never collapses below readable.

### S4 — Debrief review dock — densityScore 44

**clutterCuts**
- **CUT** 4-cell payback strip (ts:454-459,213-246,704-723) — restates the gate the title+sub+metrics already state; collapse to one sub-line. Risk: safe.
- **MERGE** 3-cell readiness-metrics grid (ts:460-464,247-274,695-697) to one mono readout line ("24m · 31 events · ready"). Risk: safe.
- **HIDE-UNTIL-RELEVANT** per-row meter bar (ts:355-371,613-615) — show only on "capture more" rows; zero the rose glow on ready rows. Risk: safe.
- **CUT** per-row payoff line (ts:609-611,348-354,755-763) — same idea as the reason line stacked; keep reason, the Open button is the CTA. Risk: safe.
- **DEMOTE** mast proof dl (ts:437-441,116-140) — static feature-bullet marketing in a tool surface; keep kicker + serif title + one sub-line. Risk: moderate.
- **CUT** decorative ::before scanline + 34% rose seam (ts:43-54) — the seam misaligns the real 0.72fr divider; warm-void + token grain carry the material. Risk: safe.
- **MERGE** row-state pill + reason (ts:585-587,325-337) — pill stays the scannable badge; reason serves only "capture more" (ready rows need none, the green button is the signal). Risk: safe.

**layoutFixes**
- Ladder spacing (ts:33,65,145,278,295): sp-2 intra-row / sp-4 between-rows / sp-5 between-sections; column gap readiness->list jumps to sp-5.
- De-nest readiness panel (ts:176-274): after cuts, title + sub + one hairline-separated mono line, no inner borders.
- 18/14/11 hierarchy (ts:198-243,266-274): title 18/650, one 14/400 sub, numerics mono 11 tracked 0.08em; drop the duplicate 13px payback values.
- Two-line ready rows (ts:292-371,567-634): date + green Open on line one, meta (duration · events · size) mono on line two; reason/payoff/meter only on "capture more"; give the ready row sp-4.
- One rose carrier (ts:50-53,189-194,305-310,363-371): only the best-candidate ready readiness panel gets the brand-08 wash; remove seam, zero meter glow, ready rows signal via Open button + brand-22 border (no fill wash).
- Right column is primary (ts:30-31,431-466): lighten the mast to a quiet header so the eye lands on the readiness panel + the one ready row; 0.72/1fr track ratio stays.

### S5 — Settings drawer — densityScore 38

**clutterCuts**
- **COLLAPSE** trust rail (ts:1118-1149) — `__contract` (voice/mode/skill/lens/output/proof) + 4 `__cell` cards restate PERSONA (voice) and OUTPUT; keep ONE honest status line (grounded/proof + recording-vault bytes). Risk: moderate.
- **HIDE-UNTIL-RELEVANT** DIAGNOSTICS group (ts:1618-1630) — slop% / stripped% / LIVE badge is dev instrumentation; demote behind advanced/HELP, render only when bypassActive. Honors Invariant #2 (linter still strips). Risk: **gated**.
- **CUT** LENS-overridden MODE rocker (ts:1304-1316) — production always sets lens, so MODE writes a field the brain ignores (Bug D); structural subtraction. Risk: **gated** (removed surface; Kaan call).
- **MERGE** HELP DOCS + SOURCE (help-group.ts:289-298) — same GITHUB_REPO_URL; one "GITHUB" row. Risk: safe.
- **DEMOTE** the 12 per-group rose seams + brand dots (group.ts:55-66) — reserve the seam + dot for the one top status module; remaining groups get a neutral tick. Risk: safe.
- **HIDE-UNTIL-RELEVANT** MASCOT click-through + mood (mascot-group.ts:235-297) — inert until ENABLE is on; show ENABLE only, reveal the rest when enabled. Risk: moderate.
- **COLLAPSE** HELP troubleshoot-audit static row + 3 always-"unknown" checks (help-group.ts:300-339) — fake checklist; collapse behind a disclosure, drop status dots until they carry real state (Invariant #3: do not show a status the app cannot prove). Risk: moderate.
- **MERGE** the two deferred-apply captions (ts:1296-1301) — one "changes apply on Sven's next line / audio restart" note per group. Risk: safe.

**layoutFixes**
- Three spaced bands (group.ts:38,139): Live tuning (PERSONA+OUTPUT+HOTKEY) / Your data (RECORDING+LIBRARY+PROFILE+LEARN) / Setup (CALIBRATION+MASCOT+PERFORMANCE+HELP); sp-5 between bands, 10px within; vary body padding by control count.
- De-containerize (group.ts:35-51): drop per-group border box + inset floor shadow; reserve the full recessed-module treatment for one status block; rest = labeled sections on `var(--border-subtle)` hairlines.
- Trust rail to a single full-width status line (ts:531-545): brand/text-primary `GROUNDED` (or claimPolicy.label) + mono recording-vault sub; idle grounded=false shows "listening", not a warn card (Invariant #5).
- Band-label hierarchy (ts:240-254): lift LIVE TUNING / YOUR DATA / SETUP to ~14px Saira (the missing mid tier); keep group headers 11px, rows 10px.
- Token alias drift (mascot-group.ts:84,113,126-132 and the help/learn/performance/citation-diagnostics components): repoint active-state `--silk`/`--amber`/`--glass-edge` aliases to the canonical brand/text/border tokens the drawer header uses (match-the-file). No new tokens.
- Genre reload (ts:350-374): replace the full glowing overlay with a quiet inline state on the GENRE row (one rose tick / "reloading" sub) so the change does not paint a second sign-of-life.

### S6 — Floating co-host pill — densityScore 61

**clutterCuts**
- **MERGE** the three collapsed-face rose rails (pill.css:1160 grade::after, :1304 level::after, :1704 streak) — keep the full-width pill__streak heat rail, drop the per-chip ::after underlines so the eye tracks one rose progress. Risk: safe.
- **COLLAPSE** grade chip + level bead (pill.css:1098,1257) — fold LVn into the grade chip (LABEL +Nxp · LVn) inside one border; frees ~42px and removes a nested card. Risk: moderate.
- **HIDE-UNTIL-RELEVANT** peek why block (next-suggestion.ts:1292,1316 / pill.css:2947) — why-chips + cue-confidence chip are receipt detail; suppress in peek density, keep label / title / transition / cue-rail / one-line grade. Full citation receipt stays in the expand panel (Invariant #2 holds). Risk: moderate.
- **DEMOTE** peek care reason-pill (pill.css:3024 / next-suggestion.ts:1332) — same text shows in the grade row and again as a glowing warn pill; drop the standalone warn pill, the grade-row reason carries it. Risk: safe.
- **HIDE-UNTIL-RELEVANT** collapsed-face waveform during peek (pill.css:1462) — fade pill__wave to 0 (max-width:0 like expand-quiet) on data-peek; idle/peek has no RMS to show. Risk: safe.
- **DEMOTE** reaction-echo afterglow (pill.css:990 / index.ts:70) — shorten the 1800ms echo window and drop to a normal-weight silk label (keep the dot tone) so collapse reads as settling, not a victory replay. Risk: **gated**.

**layoutFixes**
- Vary expand rhythm (pill.css:1973): sp-3 below the reaction line (hero air), sp-1 between citation strip and deck chips (cluster the receipts) instead of four flat sp-2 gaps.
- Peek type to two tiers (pill.css:2926,2939,3004): title 14 anchor, demote transition/why/grade to one shared 9px secondary at silk-65; cut the third tier rather than scaling it.
- De-card the face badges (pill.css:1108,1266): drop border + glass-2 fill; render grade as borderless mono ink riding the pill body (the pill IS the glass).
- Peek why-row tone (pill.css:2957,2963): if it survives, one quiet silk meta line, no chip borders; reserve brand chips for the expand panel; keep the rose KEEP/CARE action pill the only peek accent.
- Row vertical band (pill.css:725,618): reduce 7px top pad to sp-1, let the drag strip overlay (already z-indexed), so dot/label/grade center in the full 42px.

### S7 — Desktop shell — densityScore 72

**clutterCuts**
- **HIDE-UNTIL-RELEVANT** footer badges (app.ts:153-163 / shell.css:899-929) — library + voice badges show dot-only when ok (label hidden), dot+label only on warn/fault/setup; conn dot+label always. One honest sign-of-life mid-set. Risk: moderate.
- **CUT** Cmd+K 4-cell summary grid (DesktopShell.ts:149-166 / CommandPalette.ts:158-170 / shell.css:1058-1090) — banned identical-card grid restating footer State + Bus; open straight onto the action list; one inline sentence if a state line is wanted. Risk: moderate.
- **DEMOTE** palette legend (CommandPalette.ts:142-147 / shell.css:1205-1231) — quiet to one muted line (no boxed kbd caps) or show only when the query is empty. Risk: safe.
- **HIDE-UNTIL-RELEVANT** deck idle dash chips (DesktopShell.ts:64-68 / shell.css:476-494) — three "—" placeholders; display:none until activation is listening/live (gate visibility like the existing opacity ramp; never fabricate a value, Invariant #3). Risk: safe.
- **COLLAPSE** learn earned-wall fold (shell.css:746-788) — repeat(3,1fr) bordered grid nested under the stage; compact to a borderless skill strip or show only the next-earnable skill. Risk: **gated** (learn surface owner's grid).
- **MERGE** palette placeholder four-noun list (CommandPalette.ts:130) to one verb-led line ("Jump to a surface or run a control"). Only the list-of-four shape (the word/jargon swap is DONE). Risk: safe.

**layoutFixes**
- Grounding-panel rhythm (shell.css:875-877): keep sp-5 between groups, widen inter-group to sp-6 OR drop the per-section hairline so the panel reads as grouped blocks, not a flat ruled list.
- Active nav weight (shell.css:199-227,236-247): keep the dense uniform rail (gap:4px is defended), but add font-weight contrast to the active `.sb-label` so "where you are" wins on weight, not a near-invisible -10 vs -04 fill.
- De-nest palette summary cells (shell.css:1064-1070): if the summary survives, drop per-cell border+fill, render borderless label/value pairs framed by the head's own border.
- Footer responsive (shell.css:1278-1287): the <=620px rule already hides badge labels + separators; pair with the badge cut so the default is conn-dot + label + at most one action badge, never three.
- Empty-state measure (shell.css:424,506-515): align the 420px title block + 34ch sub + min(440px) proof to one `--empty-measure` so the empty state reads as one column.
- Folded booth row gap (shell.css:642-663): learn-owner grid; lift booth row gap to sp-2 only if Kaan wants the shell's calmer rhythm carried in. Risk: **gated** (cross-surface).

---

## 5. WHAT NOT TO TOUCH

**Load-bearing controls / status (keep them, they earn their place):**
- The spoken now-line `data-wire="session.now-line"` and the receipt/cite ignite (`.vmx-receipt`/`.vmx-cite`, SessionLayout.ts:615-648) — the grounding gesture, Invariant #2.
- The `.vmx-idle-proof` status grid (SessionLayout.ts:501-516) — a real audio/screen/grounded health panel; only the redundant ghost prose lines go, not the grid.
- The claim-policy pill (SessionLayout.ts:758) — the citation-grounding receipt.
- The full citation receipt in the pill EXPAND panel — the why-chips/cue-confidence detail moves here, it is not deleted.
- The session inputs health row (SessionLayout.ts:718-757) and footer connection dot+label (shell.css:899) — honest fault surfacing; only the always-on all-ok noise is trimmed.
- The `.vmx-voice::before` faceplate (SessionLayout.ts:452-463) — keeps the machined-hardware character after the `::after` grille is cut.
- The exported trademark disclaimer constant (learn-window.ts) — `test_disclaimer_present.py` source-scans it; demote the PAINT, never delete the constant.
- The MIDI-latency pip dot and DIAGNOSTICS linter behavior — the pip stays, the linter keeps stripping; only the always-on numeric/percentage glance-noise is hidden.

**The 5 cardinal invariants (no fix may break any):**
1. **Single-writer MusicState** — none of these are state-layer edits; all CSS/DOM/render-gating.
2. **Citation grounding** — the cite/receipt path and claim-policy pill stay; the pill expand panel keeps the full receipt.
3. **Trust-the-audio / invent-no-data** — idle dash chips are gated to display:none (never a fabricated value); idle status grid keeps showing only what the app can prove.
4. **One socket 8765** — all changes are presentation; no new listener, no second bus.
5. **Idle != fault** — the trust-rail status line shows idle grounded=false as "listening", never a warn-bordered card or a blanked deck; the grounding-failure timer logic (SessionLayout.ts:1298-1320) is untouched.

**Build gate after any tauri/ui change:** `cd tauri/ui && npm run build && npm test`. For the two CSS-only verified cuts (S1 `::after`, S2 orbit) there is no DOM test coverage, so additionally glance them live in `cargo tauri dev` (session deck + library window in chat mode) per the verification method, not a test run alone.

---

## 6. IMPLEMENTATION LOG + VERIFICATION CORRECTIONS (Claude, 2026-06-03)

Implemented surface-by-surface against the gate (`build && test`, 1548 green throughout), surgical per-surface commits on `ux-redesign-impeccable`. **`/impeccable audit` first scored the frontend 13/20 ("Acceptable"): not AI-slop (the system is distinctive) but over-containerized + raw-branded-rgba; 0 P0/P1.**

**LANDED (each gate-green, committed):**
- **S1 deck — layout** (`eb18efb0`): cut the `::after` grille (One-Rose), de-carded rail + foot to chrome strips / a single hairline, unified bpm+key to one 20px mono scale (key amber = second value by hue), stepped the rhythm >1.25, cut the redundant PERSONA key label (aria-label already names it).
- **S1 deck — delight** (`f5062715`): the persona dial perks up on reach — rose key-light pools from the lower-left, mood word brightens; fixed the backwards hover-dim. One-Rose-safe, eased, reduced-motion-frozen, CSS-only.
- **S7 shell — layout** (`ca90cdb4`): de-carded the Cmd+K 4-up summary grid to one inline run, plain kbd legend (no chips), verb-led + de-jargon palette placeholder, active-nav weight contrast, idle deck-scene chips hidden until a real signal (Inv #3), grounding-panel rhythm.
- **S2 library — layout** (`c36d0680`): moved slot/step ORDINAL ranks off gold to tertiary ink (Gold-Is-Quarantined; ordinals are not heat).

**VERIFIED UNSAFE — do NOT land these as written (the workflow's "Tier-1 safe" rating missed documented owner intent / wires):**
- **S2 "cut the command-field orbit"** (html:218-228) — NOT decorative. `mock-transfer/contract.ts:102` declares `library.command-field` as a real wire ("command echo and active-mode label"); it is *under-wired*, not dead. Keep it; wire it, don't cut it.
- **S5 "merge HELP DOCS + SOURCE"** (help-group.ts:289-298) — reverses a documented Kaan decision (`help-group.ts:283` "/impeccable critique round 4, Kaan: H10 final — two intents: read the guide vs browse the code") and breaks `help-group.spec.ts` ("DOCS + SOURCE rows both route to the public repo URL"). The two rows are deliberate.
- **S5 "de-containerize the 12 groups"** (group.ts:35-66) — reverses Kaan's "saçmalık → LIT RECESSED MODULE" decision (`group.ts:25-33`). The per-group rose seam is *static* (opacity 0.55, 1px), not a One-Rose *breathing* violation. Owner call, not a blind layout fix.

**REMAINING = needs Kaan's eyes or a focused spec-update pass, NOT a blind CSS sweep:**
- **S6 pill** — the rose-rail consolidation / de-card / peek-tier items are sound but the pill is a live-rendered transparent reaction window; the gate can't confirm the choreography reads right. Pair with the deferred pill-choreography eyes-on.
- **S3 learn booth** — the monotone grid-`gap` → varied rhythm is real, but per-row gap on a single grid needs eyes to land; not gate-verifiable.
- **S4 debrief** — spacing already varied (sp-5/4/3/2) post the earlier honesty pass; remaining items are DOM cuts needing lockstep `debrief-dock.spec.ts` updates.
- **S5 settings** — the safe items (genre inline-reload, mascot progressive-disclosure) are conditional-render changes needing spec updates; the structural ones conflict with owner decisions above.
