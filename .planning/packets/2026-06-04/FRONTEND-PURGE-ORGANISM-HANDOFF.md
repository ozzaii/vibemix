# Frontend Purge + Organism Phase-2 — Session Handoff (2026-06-04, post-compact)

Branch: `ux-redesign-impeccable` (ONE shared tree, many parallel Claude/Codex sessions).
Read this first, then the per-surface notes. Supersedes `FRONTEND-PURGE-HANDOFF.md`.

## SHARED LAW (obey or lose work)
- Commits survive; **UNCOMMITTED work gets WIPED** when a sibling session's git op
  resets the tree. Finish a surface → commit IMMEDIATELY.
- **Commit race-proof:** `git add <exact paths>` → REVIEW `git diff --cached --name-only`
  in a SEPARATE step → `git commit -s -F - -- <exact paths> <<'EOF' ... EOF`. The
  `-- <paths>` pathspec scopes the commit to ONLY your files even if a sibling staged
  something in the gap. NEVER `git add -A`. NEVER chain add+diff+commit in one call
  (that's how `87d0f7bc` swept in a sibling's auto_tags feature — see Open Items).
- Git identity: `Kaan Özkan <rahipdotaci@gmail.com>`. Trailer:
  `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

## ISLAND (this lane = sole owner)
ALL `tauri/ui/src/**` (session, settings, debrief, pill, shell, library/Crate,
mascot/organism, learn-window TS) + `tauri/ui/{library,debrief,pill,mascot}.html` +
the IPC schema (`tauri/ui/src/ipc/messages.schema.json` — SOLE owner; run
`npm run codegen:ipc` after edits, the ajv validator is pre-compiled) +
`src/vibemix/ui_bus/*.py` + `scripts/check_ipc_schema.py`. For the organism, Kaan
greenlit crossing into `src/vibemix/learn/runtime.py` (the teaching_focus emit) —
otherwise NOT other `src/vibemix/**` Python.

## DONE this session (12 commits, all by-eye/by-bus verified, surviving)
Kill-list (mandate A): `aef8b999` debrief Bravoh funnel · `78cac647` debrief hash cell ·
`2ebb72e5` learn booth (trademark/P95/brief/earned/L1.01, 747 del) · `826fddc9` pill
gamification (XP/LV/combo/feedback/cue-conf/backup, 4254 del) · `4e446ae4` session
modebar/idle-proof/claim-policy/Sven (435 del) · `87d0f7bc` shell footer Sven→co-host.
Crate (B): `2bf1e2d5` B1 dead-space (centered 720px column + composer) · `222b3f3e`
B2 mode-tabs floated to a fixed top header, composer = [textarea][Send]. B3 already
covered by chat.test.ts:589.
Organism (C / NEXT-MOVES #1+#2): `9dfef795` teaching-focus dissolve→stream→reform
wiring · `5a7bdb05` Playwright pixel-variance receipt.

## ORGANISM phase-2 — what shipped + how it's proven
The spine (`93540ee9`: particle-organism.ts + morph-controller.ts, organism+bloom in
renderer.ts) already had the focus mechanic (`focusAt`/`reform` + the
idle→dissolving→holding→reforming state machine + the shader `mix(pos, uFocusTarget…)`).
Phase-2 WIRED it:
- Schema: `ipc.learn.teaching_focus {control_id,deck,band,phase}` + `ipc.learn.control_rect
  {control_id,deck,cx,cy}` (NOT an overload of `ipc.learn.highlight`'s 16ms paint).
- Python producer: `learn/runtime.py::_emit_highlight` emits phase=focus, `_emit_advance`
  emits phase=reform; envelopes in `ui_bus/learn_messages.py`.
- Mascot consumer: `mascot/focus-layer.ts` (control-rect registry → screen→world unproject
  → `organism.focusAt`; reform pulls home; mask-centroid fallback when no rect). Routed in
  `mascot/index.ts` (222-235). `renderer.ts` exposes `screenToWorld`/`focusOrganismAt`/
  `reformOrganism`.
- `learn-window.ts` relays the highlighted control's `getBoundingClientRect` as control_rect.
- EQ-knob: real-CC-delta tangential particle swirl (`uTangentialBias`, idle-silent). The
  SVG `.knob-indicator` needle rotation is a FLAGGED DESIGN-ASSET dependency (not built).

**Proof:** (1) by-eye: `mascot.html?dev=mascot-mock` renders the organism (face cloud +
eye apertures, bloomed, zero shader errors). (2) by-bus: `mascot.html?dev=organism-probe`
(NEW harness in index.ts) drives real focus/reform cycles → particles stream into the
glow cluster; console logs `[organism-probe] phase=focus/reform`. (3) durable CI:
`npm run test:e2e:mascot` (Playwright, real Chromium) asserts LIT + ALIVE + real-path —
PASSES. (4) `vibemix-grounding-review`: all 5 invariants green (152 py + 12 ts).

## OPEN ITEMS (Kaan decisions / not-yet-done)
1. **GIT BUNDLE (Kaan's call):** `87d0f7bc` accidentally committed a sibling's COMPLETE
   `library auto_tags` feature (`src/vibemix/library/auto_tags.py`, `scripts/eval/
   library_auto_tags.py`, 2 tests, an eval report) that was staged in the shared index.
   No work lost (committed/preserved), just mislabeled history. Leave it, or split later
   at a calm moment (reset risks racing on this hot tree).
2. **ORGANISM rig verification (Kaan):** the DoD is by-eye per step on the REAL rig — fire
   a live lesson, confirm the dissolve streams to the ACTUAL taught control (screen→world
   landing), the glow lands on it, and the EQ swirl fires on a real CC. The probe proves
   the mechanic; the rig confirms the coordinate landing + the window-offset question
   (full-screen mascot overlay vs `windowOffset` correction — see VIBEMIX-ORGANISM-DIRECTION.md).
3. **SVG knob-needle (design):** add a `.knob-indicator` SVG element to the learn deck so
   `angleDeg = (value/127)*270 - 135` rotates a visible needle (swirl already wired).
4. **Settings trust-rail purge (#11, OPTIONAL):** NOT in the Stop-hook mandate or NEXT-MOVES.
   `SettingsDrawer.ts::renderSettingsTrustRail` "How Sven listens" board + always-on group
   rose dots (`group.ts:101`) + the two freestanding truth-notes + `settings.trust*`/
   `*.deferred-note` contract wires. Same pure-deletion pattern; by-eye-able; no rig.
5. Lower priority kill-list leftovers: type scale (tokens.css 5-step + OFL grotesk),
   color OKLCH pass, focus-ring overrides, `library` redundancy echoes. See
   `UX-CRITIQUE-IMPECCABLE.md` backlog.

## CONFLICT NOTE
Kill-list #7 says "delete root `/mascot.html`" — **DO NOT.** CLAUDE.md says mascot.html
IS the live overlay (ws_bus + CI mascot-audit). Keep it. The organism uses it.

## PATTERNS THAT WORKED (reuse)
- Big coupled surgeries (pill/session/learn/organism) → delegate to a focused `opus`
  Agent with a precise boundary spec (files in/out, keep-tests-green-by-deleting-obsolete,
  no git, verify build+test, report data). Then YOU review the diff + by-eye + commit.
- **contract.ts is shared across surfaces** — serialize anything that prunes its wires
  (only one agent/edit touching it at a time). The contract-mount test enforces BOTH
  directions (every wire ↔ DOM), so a DOM-wire removal MUST prune the contract entry.
- By-eye via the running Vite dev server (`:1420`, still up): `?dev=shell`,
  `?dev=session-mock`, `library.html`, `debrief.html?mock=1`, `learn.html`,
  `mascot.html?dev=mascot-mock` / `?dev=organism-probe`. Drive Chrome MCP; read console
  for shader/WS errors.
- Dev-gate telemetry that must exist for devs but not ship: `if (import.meta.env.DEV)`.

## GATES
`cd tauri/ui && npm run build && npm test` · `npm run codegen:ipc` after schema edits ·
`npm run test:e2e:mascot` for the organism receipt · `uv run pytest -q <paths>` for Python ·
`vibemix-grounding-review` skill before shipping co-host/learn/tutor wiring.

## SESSION 2 UPDATE (2026-06-04 cont.) — closed 2 open items + 1 build-fix
- **`6538cf51` fix(build):** the tsc gate (`npm run build`) had been RED since
  `5a7bdb05` — `tests/mascot/browser-organism-probe.pw.ts` is in the tsc include
  surface and imported `pngjs` (no types) + indexed a `Buffer` under
  noUncheckedIndexedAccess. vitest + the Playwright runner both skip full-project
  tsc, so it rode in unseen. Fixed with an ambient `pngjs` decl + `?? 0` floor.
  **Lesson: run `npx tsc --noEmit` (not just vitest) before claiming build-green.**
- **`68a2f4d6` OPEN ITEM #4 DONE — settings trust-rail purge.** Stripped the
  "How Sven listens" board + 4 trust cells + 2 deferred-notes + dead CSS from
  `src/settings/SettingsDrawer.ts` (handoff path was STALE: it's `src/settings/`
  not `src/session/`), pruned the 8 `settings.trust*`/`*.deferred-note`
  contract wires + purposes, deleted 3 obsolete specs. The "group rose dots"
  half of #4 was already gone (`46ead19e`). Drawer opens straight on PERSONA;
  by-eye verified on `?dev=session-mock`. 437 deletions, atomic.
- **`dc7f69e4` OPEN ITEM #3 DONE — knob needle.** Not a missing-element build:
  the index marker already existed + rotated, it was just indistinct (same thin
  currentColor as the dial). Classed each rotary marker `.knob-indicator`
  (110 markers, 10 SVGs) → bolder round-cap pointer + eased group-rotate.
  Stays currentColor → lights rose ONLY on the taught knob (cue-color path),
  never a splatter. ACCENT CORRECTION: rose `--brand`, NOT the stale
  frontend-enforcement amber (DESIGN.md "Forged Obsidian Chrome" supersedes v5).
  `_generic` is labeled-zone (no knobs) → untouched. By-eye proven on learn.html.
- **OPEN ITEM #5 typeset = KAAN DECISION, not shipped.** Verified `--type-step-N`
  is library-local (9 uses in library.css only), so the sub-1.25 ratio is not a
  global violation; DESIGN.md's hierarchy is deliberately axis-driven (tight
  sizes), so forcing ≥1.25 would fight the just-rebuilt Crate. The real work
  (Saira→Geist, the documented Phase-1b target) is hard-gated: WOFF2 vendor +
  `design-slop-gate` ALLOWED_FONTS amend + a PRODUCT.md override + wordmark
  licensing (NHG is trial). No clean blind win — left for Kaan's font call.
- **Still open (unchanged):** #1 git-bundle (`87d0f7bc`), #2 organism rig
  verification (Kaan's rig), the SVG `_generic` and the static-dial-tick polish
  (a future enhancement; the pointer ships without printed dial ticks — up=center
  reads by convention).
