# UI Quality Pass — Ledger (2026-06-10)

9-surface audit vs `mocks/vibemix-bravoh-grade-pink.html` (the contract) + frontend-enforcement skill. Full findings with file:line + fix sketches: `UI-QUALITY-AUDIT-FULL.json` (key `audits`; ~90 findings, 14 P0). Before-screenshots `/tmp/uxshots/audit-before/`. Baseline at start: **174 files / 1614 tests green** on the dirty working tree.

Grades: wizard **5.5** · viber **6** · tokens **6** · motion **6** · learn/debrief **6** · a11y **6.5** · deck **7** · shell **7** · settings **7**.

## Fix units (atomic commits, test pins move in the same commit)

- [x] **U1 wizard re-materialization** (fa2842b1 + 7702acf9 — also: live clock, spoken done-handoff, sticky CTA) (worst grade, self-contained): kill v5 cool-blue + `#d6cfc7` literals in `primary-panel.ts:37-52`; port rose keycap into `button.ts` armed; collapse green/red/yellow LED triad → rose+ink (fault-red only on true failure); pin "Open vibemix" CTA above the fold; style the bare done-div + dead `00:00` clock.
- [x] **U2 settings organs** (f2ffdb48 — banner, voice readout, genre labels, mascot DEV-gate, dead help LEDs, warm toast, sentinels; mono retexture + blur rocker still OPEN): style+hide staleness banner (`staleness-banner.ts:36-49`, ships as raw text "Library is … old."); replace dead 14-voice MOSS picker (`SettingsDrawer.ts:493-515,932-943`) with honest `SVEN · LOCAL VOICE` readout — KEEP the config field/schema (only the control dies); mono-label retexture (`group.ts:72-91`, `rocker.ts:62-66` — shared with deck, two suites move).
- [x] **U3 shell** (3487c2c0 — footer seam-sync, frosted palette, Learn tease voice, panel ×+idle furniture, cmdk keycap, TONIGHT gate, badge words, settings empty fix; debrief labels still OPEN): footer/panel occlusion — offset `.shell-footer` by `--panel-cur`, matched 250ms (`shell.css:1596-1612`; var must exist =0 on every surface); Learn tease copy `app.ts:97-120` sprint-memo → Sven first person (also `drills-panel.ts:144/152`); palette frosted glass (MUST honor lighter-blur flag / blur-perf-ladder spec); grounding drawer: panel-label slab idle copy + 24px ×-close.
- [x] **U4 deck instruments** (1c37ed44 — phrase tape + nowPct playhead + RMS→opacity, ~N bars grammar, MUTE/STOP powered, ghost mark, dead 780 rules; receipt restructure + persona strip still OPEN): render `phase.chunks`/`nowPct` as segmented phrase-line + playhead (props flow and die unrendered, `SessionLayout.ts:1051-1093,1932-1943`); drop-chip fake `:00` timecode → "~N bars" phrase (`drop-chip.ts:149-154`; pin `tests/session/components.spec.ts:165` moves); fmeter fill/peak clamp mismatch; MUTE/STOP rest material (`SessionLayout.ts:358-374` kill 0.58 dimmer); text floor → no glyph below `--ink-20`.
- [x] **U5a tokens** (f3c25123 — 8 undefined tokens → semantic ladder, --ok/--warn/--danger added, foreign #ff6b6b dead): undefined tokens `--silk-90/-72/-58/-38/-35/-50`, `--mint-pale`, `--radius-sm` → real ladder; add `--danger/--ok/--warn` aliases (error must stop rendering as brand rose / `#ff6b6b`). Sites: `library.css:1098-1625,2509-2529`, `learn.css:1594`, `pill.css:1337,2436`, `library-panel.ts:169`.
- [ ] **U5b radius collapse**: `--rad-sm` 2px→4px + re-point `--rad-md/--rad-lg` (re-skins pill/mascot/debrief — visual re-check all three).
- [x] **U6 a11y** (a82dd075 — 8 focus-ring suppressions deleted, global rose ring applies; text-floor sweep still OPEN): delete six `:focus-visible { outline: none }` overrides (mode-picker, rocker, titlebar, status-bar, picker, citation-strip) or upgrade to 2px brand-50; reduced-motion leak sweep.
- [x] **U7 motion** (648f7645 — gate = ONE ambient runtime-verified, perimeter stilled, hidden-foot loops paused, BPM playhead glide, 3 reduced-motion leaks; easing collapse 108 literals still OPEN): one-breath law on gate screen (sidebar ear yields — reuse `shell.css:303` pattern; still the 22s perimeter sweep); BPM-locked fmeter peak glide + receipt bar duration (reuse `--bpm-period-ms` feed; `--bpm-beat/--bpm-bar` sit dead in tokens.css); easing collapse: 108× hardcoded `cubic-bezier(0.16,1,0.3,1)` → `var(--ease-brand)`; wizard router inline X-slide also ignores reduced-motion.
- [ ] **U8 debrief dock flatten**: stage-as-page, hairline `.nr` rows + left brand-bars, ONE lead card; cold-boot 7-cell stat wall → one serif line + receipt row (`DebriefDock.ts:30-85,469-485,677-707`); rose-budget re-check (`shell.css:1029-1090`).

## SESSION 2026-06-10 CLOSED — 8 commits fa2842b1..648f7645, suite 1614 green at every step, prod build green. After-shots /tmp/uxshots/{u-final,wiz-final,settings-final}. Also done: frontend-enforcement SKILL.md is STALE (still says amber/charcoal v5) — refresh when touching docs.

## DEFERRED (not tonight, with reasons)

- **Viber `index.ts` fixes** (data-role "you"→"user" P0 at `:1773`, raw-hash receipts `:2285-2287,2574`, tool-rack into active turn `:2180-2210`): file is ANOTHER SESSION'S uncommitted WIP — hands off. Also the role fix is 3 coupled sites + persisted history compat (map role→data-role at render only, never rename stored values) + `chat.test.ts:2084` pin (also dirty). CSS-only viber fixes (progress bar → recessed hairline, `library.css:1574-1601`) are fair game.
- **NEXT UP queue on deck**: gated on a dark producer (`suggestion_service=None` in `__main__.py`) — shipping the slab without proving SuggestionService fires on the live bus yields a permanently-empty lead card, worse than the void. Needs drive-vibemix proof first.
- **v5→v6 full rename sweep** (914 refs silk/amber/glass → ink/brand/border): MUST land with the legacy-gate rewrite in the SAME commit — `tests/tokens.legacy-detect.test.ts` regex currently bans the canonical `--ink-*` ladder (gate inversion) and is byte-synced with `scripts/check_v5_migration.sh`. Big, do as its own session-closing unit or next session.
- **Unaudited surfaces** (critic): floating PILL (the default in-set surface!), mascot overlay (in-flight WIP anyway), click-through overlay, crash/muted/error banners, wizard failure paths, deck failure states (`ai service unreachable` hero), go-live warming/ARMED in-between, tray/quit-guard/window behavior, font-load FOUC, Sven-voice copy consistency pass. → next audit wave.

## Standing risks (from the adversarial critic — read before each unit)

1. Test pins: `components.spec.ts:165` (DROP IN), `start-gate.spec.ts` captions, `drills-panel-shape.spec.ts:89` copy, settings/shell suites, visual snapshots — move atomically with fixes.
2. Concurrent WIP: tree dirty on `library/index.ts`, mascot, `vitest.config.ts`, `tsconfig.json`, `package.json` etc. Pathspec commits only; verify `git diff --cached --name-only` before every commit.
3. Invariant #5: anything near status/grounding copy keeps the failure timer gated on ACTIVE (`grounding-failure.spec.ts`).
4. Invariant #4: new wiring rides the Rust IPC bridge, never a second ws client; new ipc fields need `npm run codegen:ipc`.
5. Optimistic repaint: every rebuilt settings control flips `data-active` locally.
6. Shared components (rocker/picker) re-skin deck AND settings; tokens.css edits re-skin pill/mascot/debrief — re-capture after.
7. New glass honors the lighter-blur flag (`blur-perf-ladder.spec.ts`).

## Verdict cross-ref

Framework question settled: **stay-tauri (0.86)** — `.planning/research/2026-06-10-native-ui-verdict.md`. Judge conditions feeding engineering: nspanel pill now, Windows/WebView2 QA lane, webview footprint budget, IPC seam stays UI-agnostic.
