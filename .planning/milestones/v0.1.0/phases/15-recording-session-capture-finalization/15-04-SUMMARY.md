---
phase: 15
plan: 04
subsystem: tauri-ui
tags: [ui, settings-drawer, recording-browser, virtualization, audio-player, transcript-overlay, cdj-whisper-v5, tdd]
requires:
  - 15-01  # IPC schema additions for recordings.* (RecordingsEvents + RecordingsEventsResult shapes)
  - 15-02  # Tauri assetProtocol + session.json + CSP (asset:// URL availability)
provides:
  - "renderRecordingRow(opts) → RecordingRowHandle pure-function component"
  - "renderRecordingBrowser(opts) → RecordingBrowserHandle pure-function component"
  - "RecordingSummary TypeScript interface (mirrors IPC anonymous shape)"
  - "Transcript event-kind → bold/dim emphasis derivation (deriveEventLabel helper)"
  - "Sentinel-based loading/error wiring on disk usage line (bytes_total === -1 / -2)"
affects:
  - "Phase 12 confirmDialog danger variant — re-used; no extension required"
  - "Plan 15-05 wires renderRecordingBrowser into SettingsDrawer.ts:582 RECORDING group"
  - "Plan 15-06 will add soak + POC-compat tests alongside this component coverage"
tech-stack:
  added: []
  patterns:
    - "TDD RED → GREEN: failing spec committed first, then component implementation"
    - "Pure-function component shape per Phase 12 retention-slider.ts precedent"
    - "registerStyle singleton — one scope key per component file (vmx-rec-row, vmx-rec-browser)"
    - "Decoder release on row collapse: removeAttribute('src') + load() (RESEARCH Pitfall 3)"
    - "Transcript teardown alongside audio teardown — re-expand re-fetches fresh state"
    - "IntersectionObserver 12-row chunked render above 50 rows (RESEARCH virtualization example)"
    - "convertFileSrc(absolutePath) from @tauri-apps/api/core for asset:// URL (NOT custom recording:// scheme)"
    - "XSS-safe transcript rendering via textContent (never innerHTML)"
key-files:
  created:
    - tauri/ui/src/settings/components/recording-row.ts        # 558 lines
    - tauri/ui/src/settings/components/recording-row.spec.ts   # 503 lines, 18 it-cases (14 plan behaviors)
    - tauri/ui/src/settings/components/recording-browser.ts    # 268 lines
    - tauri/ui/src/settings/components/recording-browser.spec.ts # 341 lines, 11 it-cases (8 plan behaviors)
  modified:
    - tauri/ui/vitest.config.ts  # +6 lines: route src/settings/components/recording-*.spec.ts to jsdom
decisions:
  - "TDD discipline: each task split into RED + GREEN commits (test commit precedes impl commit)"
  - "Spec files live alongside components per plan §files_modified — required adding an environmentMatchGlobs entry so src/**/*.spec.ts can opt into jsdom for these files (the default routes them to node env)"
  - "Used var(--led-fault) directly for the destructive-hover stroke instead of var(--rec) — the UI-SPEC alias was never defined in tokens.css (Phase 14 shim deletion gap); var(--led-fault) is the actual defined token and matches the precedent in confirm-dialog.ts:175"
  - "Replay button click also toggles row expansion (UI-SPEC §Interaction Contracts — Enter on replay icon toggles row); both share the same onToggle callback wiring"
  - "Row body click handler attached to the header div (.vmx-rec-row__head) not the root — actions cluster events stopPropagation, so a click on ▶/🗑 NEVER stacks with toggle (Test 6 + 7)"
  - "fetchToken counter prevents stale resolvers from a prior open from mutating the DOM after a collapse + re-expand cycle (defensive: a slow ipc.recordings.events resolution can land after the user has already moved on)"
  - "Browser component owns confirm-dialog construction (parent-mounted to document.body) — row only fires onDelete() callback, so the dialog lives above the drawer body z-index layer (UI-SPEC §Component Contracts modal pattern)"
metrics:
  duration: ~52 minutes (start 17:24, plan-complete 18:16)
  tasks_completed: 2
  test_cases_added: 29 (18 row + 11 browser)
  commits: 4 (2 RED + 2 GREEN)
  files_created: 4
  files_modified: 1
  lines_added: ~1670
---

# Phase 15 Plan 04: Recording Browser Components Summary

**One-liner:** Two new pure-function components — `recording-row.ts` + `recording-browser.ts` — implementing the in-drawer Recording Browser UI per UI-SPEC, with lazy-mounted `<audio>` (asset:// URL via `convertFileSrc`), on-demand `events.jsonl` transcript overlay (bold AI/trigger lines vs dim controller-moves), and IntersectionObserver chunked virtualization above 50 rows.

---

## What Shipped

### Task 1 — `recording-row.ts`

Single-session row + lazy-expanded inline panel. The row's three cells (timestamp · meta · actions) collapse to 44px min-height; expansion mounts a native HTML5 `<audio controls>` element with the recording's voice.wav loaded via `convertFileSrc()` (resolves to an `asset://localhost/<path>` URL the Tauri webview can fetch per Plan 15-02's `assetProtocol` scope) plus a transcript overlay rendered from a `ipc.recordings.events` IPC request (10s default timeout per Phase 11 W4 `sendIpcRequest`).

Transcript rendering follows the UI-SPEC §Row expanded state contract:
- **AI text** + **trigger / trigger_fired** events → `.vmx-rec-evt--bold` with `border-left: 1px solid var(--amber-22)` and `color: var(--silk)`.
- **controller_move** + **midi_event** + **session_start** + any other ambient event → `.vmx-rec-evt--dim` with `color: var(--silk-40)`.
- Each line prefixed with a `[+M:SS]` relative-timestamp span in `var(--type-mono)` (JetBrains Mono).
- Loading state: `<div class="vmx-rec-evt vmx-rec-evt--dim">Loading events…</div>` (verbatim copy).
- Error state: `<div class="vmx-rec-evt vmx-rec-evt--dim">Events unavailable.</div>` (verbatim copy).
- XSS-safe rendering via `textContent` — never `innerHTML`.

On `setExpanded(false)`:
- `<audio>.pause(); removeAttribute("src"); load();` — releases the decoder per MDN HTMLMediaElement docs (RESEARCH Pitfall 3).
- Transcript node `.remove()` — detached so a re-expand re-fetches fresh events.jsonl state (bounded memory).
- `fetchToken += 1` so any in-flight `ipc.recordings.events` resolver from the just-closed open becomes a no-op.

Other contracts:
- `data-crashed="true"` + 5×5 `--led-warn` LED dot prefix when `summary.crashed === true`.
- `prefers-reduced-motion: reduce` @media rule disables the 250ms height transition and falls back to `display: none` / `display: block` toggle.
- Delete button: `stopPropagation()` on click so it never stacks with the row's toggle handler.
- Keyboard: Enter / Space on the row toggles expansion; Enter on the focused delete button fires `onDelete` only (does NOT toggle).
- AT labels: row root has `role="button"` + `aria-expanded={true|false}` + a composed `aria-label`. Replay + delete buttons carry their own `aria-label`s with the formatted timestamp.

### Task 2 — `recording-browser.ts`

List + disk-usage header + empty state. Mounts as a sibling of the retention slider inside the existing Phase 12 RECORDING group (Plan 15-05 wires the actual insertion).

- **Disk usage line:** `RECORDINGS · {N} SESSIONS · {SIZE} USED` in Saira 9px wght 500 wdth 85, +0.22em tracking, UPPERCASE, `--silk-40` with engraved text-shadow. Sentinels: `bytes_total === -1` → `RECORDINGS · LOADING…`; `=== -2` → `RECORDINGS · UNAVAILABLE`. Format: integer MB for <1 GB; 1-decimal GB at ≥1 GB.
- **Empty state:** `<div role="status" aria-live="polite">No recordings yet. Sessions appear here after they end.</div>` (verbatim per CONTEXT Area 2).
- **Virtualization:** ≤50 rows full-mount; >50 rows IntersectionObserver chunked render (12-row chunks, 200px rootMargin). Sentinel `.vmx-rec-browser__sentinel` is removed when all rows are mounted.
- **Delete confirm:** owns the dialog construction — `renderConfirmDialog({ heading: "Delete session {timestamp}?", body: "This cannot be undone.", confirmLabel: "DELETE", cancelLabel: "CANCEL", variant: "danger", onConfirm, onCancel })`. Mounts on `document.body`. On confirm, fires `opts.onDelete(session_dir, timestamp)` — the component does NOT call the IPC directly (that's Plan 15-05's wiring concern).

The exported `RecordingBrowserHandle` shape is fixed at the three properties required by Plan 15-05's drawer wiring: `{ root, setSessions, setUsage }`. The browser reads the loading / unavailable sentinels off `setUsage()` directly — no separate `state` prop needed.

---

## Verification (all gates green)

| Gate | Result |
|------|--------|
| `npx vitest run src/settings/components/recording-row.spec.ts` | **18 / 18 pass** (covers 14 plan behaviors via nested describes) |
| `npx vitest run src/settings/components/recording-browser.spec.ts` | **11 / 11 pass** (covers 8 plan behaviors via nested describes) |
| `npx vitest run` (full suite) | **321 / 321 pass** across 24 files |
| `npx tsc --noEmit` | exit 0 |
| `npm run check:ipc` (IPC drift) | green — codegen output stable |
| Phase 14 shim-grep gate on both new files | **0 hits** (forbidden: `--phosphor*`, `--brushed-*`, `--bezel-*`, `--panel-*`, `--groove`, `--ink*`, `--charcoal`, `--col-mascot`) |
| Hex-literal gate | **0 hits** outside the documented inline rgba exceptions (`rgba(214,207,199,0.06)` row-hover and `rgba(212,65,58,0.18)` destructive-hover) |
| Transcript contract greps | `vmx-rec-evt--bold` ≥1, `vmx-rec-evt--dim` ≥3, `border-left: 1px solid var(--amber-22)` ≥1 — all present |
| Loading/error copy greps | `Loading events…` ≥1, `Events unavailable.` ≥1 — both present |
| Sentinel copy greps | `LOADING…` ≥1, `UNAVAILABLE` ≥1 in browser.ts — both present |
| Third-party UI deps | **0** (only `@tauri-apps/api/core`'s `convertFileSrc`) |
| `git diff main..HEAD -- tauri/ui/package.json` | **no diff** — zero new npm deps |

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] Spec files needed jsdom routing — vitest.config.ts default routes `src/**/*.spec.ts` to node env**

- **Found during:** Task 1 RED-phase first test run.
- **Issue:** The plan's `files_modified` array names the spec files under `tauri/ui/src/settings/components/`, and the `verify` block hard-codes `npx vitest run src/settings/components/recording-row.spec.ts` as the test command. But vitest.config.ts's existing `environmentMatchGlobs` only routes `src/**/*.dom.spec.ts` (not `*.spec.ts`) to jsdom — meaning `document`, `HTMLElement`, etc. would be undefined when running these specs.
- **Fix:** Added one entry to `environmentMatchGlobs`: `["src/settings/components/recording-*.spec.ts", "jsdom"]`. Scoped to recording-* files only so existing node-env specs in `src/` are unaffected.
- **Files modified:** `tauri/ui/vitest.config.ts` (+6 lines).
- **Commit:** `63e621c` (bundled with the Task 1 RED commit).

**2. [Rule 3 — Blocking] Worktree was missing tauri/ui/node_modules — vitest couldn't load**

- **Found during:** Task 1 RED-phase first test run (Error: `Cannot find package 'vitest'`).
- **Issue:** The worktree was created fresh and never had `npm install` run; the main repo's `node_modules` at `/Users/ozai/projects/dj-set-ai/tauri/ui/node_modules/` was the only place vitest existed locally.
- **Fix:** Symlinked the main repo's `node_modules` into the worktree (`ln -s /Users/ozai/projects/dj-set-ai/tauri/ui/node_modules /Users/ozai/projects/dj-set-ai/.claude/worktrees/agent-ab14a8d10d84ae968/tauri/ui/node_modules`). The `node_modules/` line in the repo's `.gitignore` covers the directory, but `git check-ignore` doesn't follow symlinks the same way — the symlink itself shows as untracked. **Not committed** (matches the gitignore intent of "deps aren't part of the repo").
- **Files modified:** none committed; runtime-only resolution.
- **Commit:** none.

**3. [Rule 2 — Missing critical] UI-SPEC referenced `var(--rec)` which is not defined in tokens.css**

- **Found during:** Token vocabulary cross-check before writing the row CSS.
- **Issue:** UI-SPEC §Color line 61 says `--rec` is an alias for `--led-fault`, but `tokens.css` post-Phase-14 shim-delete (commit `79a7208`) only defines `--led-fault` directly — the `--rec` alias was lost in the cleanup. `var(--rec)` is referenced by `drop-chip.ts` and `titlebar.ts` (those currently render with no fallback color — pre-existing Phase 14 gap, out of scope).
- **Fix:** Used `var(--led-fault)` directly for the destructive-hover stroke in `recording-row.ts`, matching the precedent in `confirm-dialog.ts:175` (which also uses `var(--led-fault)` directly for its danger-variant CTA). Documented in the CSS comment block. The visual contract is identical (`#d4413a`).
- **Files modified:** `tauri/ui/src/settings/components/recording-row.ts` (CSS only).
- **Commit:** `9f3be1d`.

No other deviations.

---

## Stub Tracking

None. All data paths are wired:
- `<audio src>` ← `convertFileSrc(resolveWavPath(session_dir))` — production wiring via Plan 15-05's `absoluteWavPathResolver` prop.
- Transcript ← `sendIpcRequest("ipc.recordings.events", { session_dir }, "ipc.recordings.events_result")` — Plan 15-01 added the schema; the sidecar handler ships in this same wave.
- Disk usage ← `setUsage()` called by Plan 15-05's drawer wiring on `ipc.recordings.usage` push.
- Empty state ← rendered when `setSessions([])`.

---

## Threat Flags

None. The recording-row/browser components touch no network endpoints, no auth paths, no schema boundaries. They consume the asset:// URL produced by `convertFileSrc` (whose scope is locked by Plan 15-02's `assetProtocol.scope: ["$APPDATA/vibemix/recordings/**", "$APPLOCALDATA/vibemix/recordings/**"]`) and the `ipc.recordings.events` request (whose payload is parsed through the shared `parseIpcMessage` ajv validator from Phase 11 Wave 0). XSS surface is closed via `textContent` on all event labels (verified by Test 14).

---

## Commits

| Hash | Kind | Description |
|------|------|-------------|
| `63e621c` | test | RED — `recording-row.spec.ts` + vitest.config.ts jsdom routing |
| `9f3be1d` | feat | GREEN — `recording-row.ts` (558 lines) — 18/18 tests pass |
| `0645817` | test | RED — `recording-browser.spec.ts` |
| `90dad14` | feat | GREEN — `recording-browser.ts` (268 lines) — 11/11 tests pass |

---

## TDD Gate Compliance

Per Plan 15-04 task `tdd="true"` markers:

- **Task 1:** RED commit `63e621c` (test only, fails import) → GREEN commit `9f3be1d` (implementation, all 18 cases pass). ✓
- **Task 2:** RED commit `0645817` (test only, fails import) → GREEN commit `90dad14` (implementation, all 11 cases pass). ✓

Both tasks followed the canonical RED → GREEN sequence. No REFACTOR commit needed — the first-pass implementations are already at the required token discipline + line-count targets.

---

## Self-Check: PASSED

- `[ -f tauri/ui/src/settings/components/recording-row.ts ]` → FOUND (558 lines)
- `[ -f tauri/ui/src/settings/components/recording-row.spec.ts ]` → FOUND (503 lines)
- `[ -f tauri/ui/src/settings/components/recording-browser.ts ]` → FOUND (268 lines)
- `[ -f tauri/ui/src/settings/components/recording-browser.spec.ts ]` → FOUND (341 lines)
- `git log --oneline --all | grep 63e621c` → FOUND
- `git log --oneline --all | grep 9f3be1d` → FOUND
- `git log --oneline --all | grep 0645817` → FOUND
- `git log --oneline --all | grep 90dad14` → FOUND
- `cd tauri/ui && npx vitest run src/settings/components/recording-*.spec.ts` → 29/29 pass
- `cd tauri/ui && npx tsc --noEmit` → exit 0
- `cd tauri/ui && npm run check:ipc` → exit 0
