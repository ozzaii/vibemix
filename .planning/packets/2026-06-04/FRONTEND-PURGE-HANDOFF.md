# Frontend Purge + UX Redesign — Session Handoff (2026-06-04)

Branch: `ux-redesign-impeccable` (ONE shared tree, multiple parallel sessions).
Goal: Crate → full-bleed Viber agentic chat (real `library://viber-tool` stream) +
strip ALL telemetry/defensive-copy off user surfaces. Spec: `GOAL-frontend.md` +
`UX-CRITIQUE-IMPECCABLE.md` (both in `.planning/packets/2026-06-04/`).

## UPDATE — mandate expanded (Stop hook) + more landed
The lane now also owns: (B) three Crate fixes on the sibling's `918839a0` rebuild
— B1 kill desktop dead-space (center the conversation; the left-rail-vs-centered
tension reads "unfinished"); B2 remove the redundant VIBER mode tab beside SEND
(one SEND; VIBER is the title); **B3 already DONE** (starter chips pre-fill + run +
hide rail, test-enforced `chat.test.ts:589` — no change). (C) organism phase-2:
add `ipc.learn.teaching_focus {control_id,deck,band,phase}` + `control_rect` schema
section (run `npm run codegen:ipc` + ipc-wiring-checker), wire dissolve→stream-to-
control→glow→reform + EQ-knob needle rotation; organism animates ONLY on real
signals (voice RMS, beat, teaching focus, MIDI) — random dots = fail; verify on the
real rig by eye. B1/B2 + C need the RUNNING app (`VIBEMIX_DEV_SIDECAR=1`), not guessing.

Landed since first handoff (all `-s`, surviving): `2b654c44` session made-by-bravoh ·
`12b4e919` session AI-COHOST strip · `b756abe5` debrief telemetry · `980558ec` ear-test
gate · `fa52a00a` drills title · `37956f5d` debrief session-id · `0106a6f0` pill idle-dot ·
`cba060c2` session Sven→co-host · `0357195a` session a11y (aria-live + cite chip).

REMAINING after this: debrief bravoh-waitlist toggle; session hero coupled removals
(`vmx-modebar` — DOM+handle+`setModePickerActive`+`session.mode-picker` contract wire;
`vmx-idle-proof` grid — interface+DOM+CSS+`session.idle-proof*` wires+the 'sven' cell;
`vmx-claim-policy` GUARD/RED); `vmx-voice::before` (DEFERRED — judgment call, may flatten
the slab, needs by-eye); pill gamification (XP/LV/combo/feedback/cue-confidence/backup —
deep data+contract+test coupling); learn-window; type scale; then B1/B2 + C on the rig.

## SHARED LAW (proven the hard way — obey or lose work)
- Commits survive; **UNCOMMITTED work gets WIPED** when a sibling session's git op
  resets the tree (my ~20min settings purge was wiped this way). So: finish a
  surface → `git add <exact paths>` (NEVER `-A`) → `git commit -s` IMMEDIATELY.
  Verify `git diff --cached --name-only` shows ONLY your files before committing.
- Git identity: `Kaan Özkan <rahipdotaci@gmail.com>` (already the repo default).
- Co-Author trailer: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

## ISLAND (this lane = sole owner)
ALL `tauri/ui/src/**` (session, settings, debrief, pill, shell, library/Crate,
mascot/organism, learn-window TS) + `tauri/ui/library.html`/`debrief.html` +
the IPC schema (`tauri/ui/src/ipc/messages.schema.json` — SOLE owner; run
`npm run codegen:ipc` after edits) + `src/vibemix/ui_bus/*.py` +
`scripts/check_ipc_schema.py`. NOT any other `src/vibemix/**` Python.

## DONE (committed, surviving)
- `e148d054` shell: Grounding→Receipts (`--text-muted`), palette `Command deck`
  title/subtitle + `Bus`/`Proof` cells gone, library/voice badges hide on
  `unknown` (separator too), sidebar co-host caps label → static ear dot.
- `2b654c44` session: `made by bravoh` removed from live status bar.
- `12b4e919` session: `AI COHOST · audio + screen` top-strip (`buildTopStrip`) removed.
- `b756abe5` debrief: titlebar `Local analyzer`/`Evidence lock` badges, TL;DR HUD
  `Format`/`Hash` cells, `Fault line inspection armed.` note removed.
- `980558ec` debrief: ear-test sign-off mount gated behind `import.meta.env.DEV`.
- (sibling `46ead19e` did a LIGHTER settings purge: gated DIAGNOSTICS, removed
  group-dot/EXPERIMENTAL/pendingGenreReload — but KEPT the trust rail; see gap.)
- (sibling `918839a0` did the Crate→conversational rebuild; `93540ee9` organism spine.)

## REMAINING KILL-LIST (mine now)
- **Settings trust-rail GAP (Major #11, high value):** `SettingsDrawer.ts`
  `renderSettingsTrustRail` "How Sven listens" status board still renders (line
  ~1078 def / ~1257 call). Remove it + the now-dead helpers + `.vmx-settings-trust*`
  CSS, AND remove `settings.trust*` + `settings.*.deferred-note` wires from
  `src/mock-transfer/contract.ts` (`SETTINGS_RUNTIME_WIRES` + descriptions) so the
  contract-mount test stays green. Also the two freestanding truth-notes ("voice
  changes when Sven restarts", "routing changes when audio restarts").
- **Session hero (`SessionLayout.ts` — BIG, most-contended file, deeply coupled:
  interface fields + CSS + DOM build + update logic + contract + tests):**
  `vmx-modebar` (COHOST/LEARN/BUILD/DEBRIEF nav), `vmx-idle-proof` 4-cell grid,
  `Sven` in `idleReadinessLines()` → "co-host", `vmx-claim-policy` GUARD/RED dot,
  `vmx-voice::before` decoration. a11y: `aria-live` on `.vmx-voice`, citation chip
  `opacity:1` in reduced-motion block, mute/status `aria-label`/`aria-pressed`.
- **Pill (`pill/next-suggestion.ts` + `pill.css`/`pill.html` + contract
  `pill.grade/level/streak/overdrive/burst`):** XP/LV/combo gamification, feedback
  buttons keep/later/timing, cue-confidence chip, `backup` alternatives, state
  caps labels, idle dot → `--silk-40`.
- **Debrief remainder:** `Drill N` headings (`drills-panel.ts:30`), Bravoh waitlist
  toggle (`bravoh-waitlist-toggle.ts` + contract `debrief.bravoh` + its test), raw
  session-ID in titlebar (`debrief-window.ts:45` writer + `debrief.html` element).
- **Learn (`learn-window.ts`):** trademark footer (→ HTML comment), `learn-booth-brief`
  dl, `learn-booth-earned` mini-grid, `P95: NN ms` (`status-bar.ts`), exemplar
  `${gain} dB`, `L1.01 OF 16` curriculum keys.
- **Type scale (`tokens.css`):** declare 5-step `--text-*` ladder (11/13/15/18/clamp),
  delete live text <11px, move UI body toward OFL grotesk (Inter/Geist).

## PATTERNS THAT WORK (reuse)
- Dev-only telemetry → gate with `if (import.meta.env.DEV)`. vitest runs DEV=true so
  tests stay green; shipped build (DEV=false) strips it. Used for DIAGNOSTICS + ear-test.
- Removing DOM `data-wire`s → also prune `src/mock-transfer/contract.ts`
  (`*_RUNTIME_WIRES` list + the purpose map) or the contract-mount test fails.
- Hide-on-indeterminate: set `element.hidden = state === "unknown"` (+ sibling
  separator) instead of painting "unknown" copy (idle ≠ fault, invariant #5).
- Tokens: ink ladder `--text-primary/secondary/tertiary/muted/disabled`, status
  `--led-ok/warn/fault` (NOT brand rose), no em dashes. Design contract = `DESIGN.md`.

## GATES
- `cd tauri/ui && npm run build && npm test` (159 files / 1558 tests). Per-surface:
  `npx vitest run <dir>`. `npm run codegen:ipc` after schema edits;
  `ipc-wiring-checker` skill on any new `ipc.*` type.
- Validator = BY-EYE in `VIBEMIX_DEV_SIDECAR=1` app (Crate reads as chat, agent log
  streams real tools, telemetry gone). test-passing-but-dark = 0.
- Ignore: semgrep INFO on a pre-existing `console.log` in `SettingsDrawer.ts:~1731`.

## NEXT
Phase 2 after the purge = the particle Organism (`GOAL-organism.md`) — spine already
landed in `93540ee9` (`mascot/particle-organism.ts` + `morph-controller.ts`).
