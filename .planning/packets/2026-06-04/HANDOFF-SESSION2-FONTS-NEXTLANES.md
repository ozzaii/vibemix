# Session-2 Handoff — Typeset CLOSED + next lanes armed (2026-06-04, post-compact read-me-first)

Branch: `ux-redesign-impeccable` (ONE shared tree, many parallel Claude/Codex sessions).
This supersedes `HANDOFF` for "what's next." Prior detail: `FRONTEND-PURGE-ORGANISM-HANDOFF.md`
(its SESSION 2 UPDATE block covers the purge/knob/build-fix; this doc adds the font swap + the
armed next-lane workflow).

## ⏩ CONTINUATION (do this first when you wake)
A deep blueprint workflow is RUNNING in the background: **runId `wcr96tr96`**
(`next-lane-blueprints`). When it completes it writes:
- `.planning/packets/2026-06-04/NEXT-LANE-BLUEPRINTS.md`  ← **read this first** (master, exec order + handshakes)
- `NEXT-LANE-BLUEPRINT-keyfield.md` · `NEXT-LANE-BLUEPRINT-cuetray.md` · `NEXT-LANE-BLUEPRINT-masklearn.md`

**Then execute, in the order the master recommends, the three next lanes** (Kaan's marching orders,
SHIP-FINISH-PLAN.md Lane A (2)+(3) + his add):
1. **in-GUI Gemini-key field + proxy-mode toggle** in Settings (DEMOCRATIZATION #1) — a non-dev pastes
   a key OR flips to the hosted proxy without editing `.env`. I own the IPC DEF + UI; Lane B (Python)
   owns the persist handler (handshake the message name). Secret never logged/committed.
2. **Cue Tray UI** — pure render of a CueSet: A–H slot ladder, ProvenanceBadge ◇AUTO(hollow)/●DJ(filled),
   ConfidenceMeter banded to policy floors, locked DJ rows, empty-as-empty, one-consent Land button +
   target picker + Landed receipt. Add `library_land_cues` IPC type (own the schema; codegen:ipc +
   ipc-wiring-checker). Spec: `CUE-LAND-ENGINE.md` "Sexy UX".
3. **mask integration into learn** — wire the particle-organism face-mask into the learn window so it
   focuses on the taught control during a lesson. **Kaan LOCKED: the mask stays VISUALLY AS-IS** (don't
   redo the visual, don't go standalone-organism, don't re-tune bloom). Wire-not-rebuild.

`test-passing-but-dark = 0`: prove each by-eye/by-bus on the running app, not just vitest.

## DONE this session (5 commits, all green + by-eye proven, surviving)
- `6538cf51` **fix(build)** — the `npm run build` tsc gate had been RED since `5a7bdb05`
  (`tests/mascot/browser-organism-probe.pw.ts` in the tsc include: `pngjs` untyped + `Buffer` index
  under noUncheckedIndexedAccess). vitest + Playwright both skip full tsc, so it rode in unseen.
  **LESSON: run `npx tsc --noEmit`, not just vitest, before claiming build-green.**
- `68a2f4d6` **fix(settings)** — purged the trust-rail telemetry board ("How Sven listens" + 4 cells +
  2 deferred-notes + dead CSS) from `src/settings/SettingsDrawer.ts`; pruned the 8 `settings.trust*`/
  `*.deferred-note` contract wires; deleted 3 obsolete specs. Drawer opens straight on PERSONA. 437 del.
- `dc7f69e4` **feat(learn)** — knob needle: classed each rotary index marker `.knob-indicator`
  (110 markers, 10 SVGs) → bolder round-cap pointer + eased group-rotate; stays `currentColor` so it
  lights rose ONLY on the taught knob (cue-color path), never a splatter. `_generic` (labeled-zone)
  untouched. Group rotation unchanged → `test_fader_does_not_rotate` green.
- `88b72e70` **feat(ui) — Phase-1b FONT SWAP**: Geist + Geist Mono retire Saira + JetBrains Mono.
  Vendored `Geist-Variable.woff2` + `GeistMono-Variable.woff2` (Vercel, OFL); `--type-display/-body`→
  Geist, `--type-mono`→Geist Mono; `--type-serif` (Instrument Serif hero) unchanged. Geist has a weight
  axis only (no width) → existing `font-variation-settings:"wdth" N` normalize to regular width, "wght"
  still applies. Every component reads `var(--type-*)`, so zero component edits. Flipped the
  design-slop-gate ALLOWED_FONTS + @font-face lock; updated `LICENSE-3RD-PARTY.md` (4 WOFF2, new
  SHA-256). By-eye `?dev=session-mock`: wordmark/labels/Geist-Mono numerics/Instrument-Serif hero all
  clean. tsc + gate(6/6) + 1494 vitest green.
- `c24a4587` docs — session-2 closeout note in `FRONTEND-PURGE-ORGANISM-HANDOFF.md`.

(Session-1 commits earlier: `aef8b999` `78cac647` `2ebb72e5` `826fddc9` `4e446ae4` `87d0f7bc`
`2bf1e2d5` `222b3f3e` `9dfef795` `5a7bdb05` `3f50c6dc`.)

## MASK / organism status (Kaan-confirmed this session)
- Mechanic WIRED + proven: `mascot.html?dev=organism-probe` cycles `phase=focus`/`reform`, zero
  shader/WebGL errors; teaching_focus → dissolve/stream/reform works; Playwright receipt green.
- Visual = a face-region particle mask on the existing 3D Meshy character (bright bloom). **Kaan:
  "güzel gözüküyor, bi daha uğraşmıyoruz" — the visual STAYS AS-IS.** Not the standalone full-body
  organism from `VIBEMIX-ORGANISM-DIRECTION.md`; that direction is parked.
- The only mask work queued = **integrate it into the learn window** (lane 3 above). Wire, don't redo.

## TYPESET follow-ups (non-functional, noted — NOT blockers)
- ~30 inline code COMMENTS across `tauri/ui/src/**` still say "Saira" / "Saira wdth 85" (e.g.
  wizard/*, session/components/*, learn/*). Cosmetic doc debt; the design-slop gate is green (no
  `font-family` decl references the old fonts). A follow-up sweep updates them.
- `DESIGN.md` + `PRODUCT.md` text still name Saira/JetBrains Mono as "shipping" — update to Geist.
- The `font-variation-settings: "wdth" N` sites (~198) are now inert-but-harmless (Geist ignores wdth,
  weight still applies). Optional cleanup to strip the dead `"wdth"` axis.

## SHARED LAW (obey or lose work)
- Commits survive; **uncommitted work gets WIPED** by a sibling git op. Commit each surface the instant
  it's green + proven. The tree IS hot — siblings committed alongside every commit this session.
- Race-proof: `git add <exact paths>` → review `git diff --cached --name-only` in a SEPARATE step →
  `git commit -s -F - -- <exact paths> <<'EOF'…EOF`. NEVER `git add -A`. Before staging a SHARED file
  (contract.ts, tokens.css) re-check `git diff` for foreign hunks.
- Git identity `Kaan Özkan <rahipdotaci@gmail.com>`; trailer `Co-Authored-By: Claude Opus 4.8 (1M
  context) <noreply@anthropic.com>`.
- IPC schema is the FRONTEND lane's; backend lanes request message types. Sidecar = one socket
  127.0.0.1:8765; `pkill -f "python -m vibemix"` before any probe.

## GATES
`cd tauri/ui && npx tsc --noEmit` (the real build-green check) · `npm test` (vitest, 1494) ·
`npm run codegen:ipc` after schema edits + the `ipc-wiring-checker` skill · `npm run build` is
`tsc --noEmit && vite build` · `vibemix-grounding-review` before shipping any co-host/learn/tutor
reaction wiring. By-eye on the running Vite dev server (:1420): `?dev=session-mock`, `?dev=shell`,
`library.html`, `learn.html`, `mascot.html?dev=organism-probe`.

## STILL OPEN (Kaan's, unchanged)
- `87d0f7bc` git-bundle (a sibling's auto_tags feature mislabeled in that commit) — leave vs split.
- Organism RIG verification (Kaan's rig: does the dissolve land on the actually-taught control).
- The ship DoD (SHIP-FINISH-PLAN.md §97): PKG rebuild, LIVE keystone capture, sign/notarize — Kaan's clock.
