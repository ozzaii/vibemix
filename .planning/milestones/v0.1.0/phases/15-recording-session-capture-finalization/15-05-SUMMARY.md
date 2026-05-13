---
phase: 15
plan: 05
subsystem: tauri-ui
tags: [ui, settings-drawer, ipc-wiring, recording-browser, optimistic-delete, sentinel-state]
requires:
  - phase: 15-01
    provides: "ipc.recordings.list/list_result/delete/delete_ack/usage codegen types"
  - phase: 15-03
    provides: "Sidecar handlers + RecordingsIndex + retention sweep firing the usage push"
  - phase: 15-04
    provides: "renderRecordingBrowser + RecordingBrowserHandle (root/setSessions/setUsage) + sentinel bytes_total -1/-2 contract"
provides:
  - "RecordingsSlice on SettingsUIState (sessions + usage + loading + error)"
  - "setRecordingsSlice(partial) helper for slice mutation"
  - "ws-bridge applyRecordingsUsage → recordings.usage subscriber"
  - "SettingsDrawer.loadRecordings() — drawer-open list IPC dispatch + sentinel-driven loading/error"
  - "SettingsDrawer.onDeleteRecording() — optimistic row removal on ok=true ack"
  - "1s debounced drawer-open lifecycle hook (lastLoadAt + LIST_DEBOUNCE_MS)"
affects:
  - "Plan 15-06 — soak + POC compat tests (next plan in the phase)"
  - "Plan 15-06 — phase-close summary will reference this plan's UAT result"

tech-stack:
  added: []
  patterns:
    - "Sentinel-driven loading/error rendering on locked component handle contract (no `state` prop, just `setUsage({bytes_total: -1|-2})`)"
    - "Optimistic IPC delete — slice + DOM update on ok=true ack, usage push handles disk-usage line refresh"
    - "Drawer-open lifecycle hook with 1s debounce — absorbs flicker re-opens"
    - "Mock-driven vitest pattern for IPC client (vi.mock('../../src/ipc/client.js') with sendIpcRequestMock factory)"

key-files:
  created:
    - tauri/ui/tests/session/ws-bridge.recordings.spec.ts  # 79 lines, 5 cases
  modified:
    - tauri/ui/src/settings/state.ts                       # +27 lines (RecordingsSlice + setRecordingsSlice + default)
    - tauri/ui/src/session/ws-bridge.ts                    # +37 lines (subscriber wiring + applyRecordingsUsage)
    - tauri/ui/src/settings/SettingsDrawer.ts              # +143 lines (browser mount + loadRecordings + onDeleteRecording + debounce hook)
    - tauri/ui/tests/settings/drawer.spec.ts               # +153 lines (4 Phase 15 cases + mock plumbing)

key-decisions:
  - "Sentinel approach preserved verbatim from Plan 15-04: RecordingBrowserHandle = { root, setSessions, setUsage } stays at 3 properties. Loading/error states flow through setUsage({bytes_total: -1 | -2}). NO state prop on the handle. The drawer's `loadRecordings()` is the only sentinel source."
  - "RecordingsSlice lives on SettingsUIState (settings/state.ts), NOT on SessionState (session/state.ts). Plan locked this in §State Management ('reuse SettingsUIState extension pattern'); the UI-SPEC §State Management referenced SessionState but the plan's frontmatter `files_modified` and §Task 1 action both point to settings/state.ts — followed the plan."
  - "ws-bridge subscriber writes ONLY the usage sub-field on push (sessions array untouched). Matches UI-SPEC §State Management ('avoids list-flicker mid-interaction'). The drawer's recordings.list request handles session-array updates on drawer open."
  - "1s debounce on drawer-open list refresh (LIST_DEBOUNCE_MS = 1000). Tracked via module-scope `lastLoadAt`. Test isolation: reset to 0 in _resetDrawerForTests."
  - "loadRecordings + onDeleteRecording exported from SettingsDrawer.ts for vitest direct invocation (matches the recording-row + recording-browser test patterns from Plan 15-04 — drives the resolver microtask without relying on openSettings auto-fire timing)."
  - "On delete ok=false, set slice.error to 'delete failed: {msg}' and log via console.warn — the in-dialog retry surface (UI-SPEC §Copywriting `Delete failed: {error}` row) is deferred to Plan 15-06 per UX-SPEC handoff (v1 surfaces via slice; v1.x extends confirm-dialog with retry-body swap)."

patterns-established:
  - "Pattern: Sentinel-driven async state on a locked component contract — caller pushes `bytes_total: -1` for LOADING and `-2` for UNAVAILABLE through the same setUsage() entry point; component recognizes sentinels internally. Avoids API surface growth on the handle."
  - "Pattern: Module-scope handle + lifecycle hook — drawer keeps a single `recordingBrowserHandle | null` so the async `loadRecordings()` resolver can push results into the live DOM independent of refresh() rebuilds."

requirements-completed: [REC-05, REC-06]

# Metrics
duration: ~8min
completed: 2026-05-13
---

# Phase 15 Plan 05: SettingsDrawer Recording Browser Wiring Summary

**One-liner:** Integration glue plan — RecordingsSlice + ws-bridge usage subscriber + SettingsDrawer mount-site extension wire Plan 15-04's components to Plan 15-01's IPC families and Plan 15-03's sidecar pushes; closes user-facing surface for REC-05/REC-06 modulo Kaan-rig visual UAT (pending).

---

## What Shipped

### Task 1 — RecordingsSlice + ws-bridge subscriber

**State slice** (`tauri/ui/src/settings/state.ts`):

```ts
interface RecordingsSlice {
  sessions: RecordingSummary[];
  usage: { sessions: number; bytes_total: number };
  loading: boolean;
  error: string | null;
}
```

Added as a top-level field on `SettingsUIState` with default `{ sessions: [], usage: { sessions: 0, bytes_total: 0 }, loading: false, error: null }`. Exported `setRecordingsSlice(partial)` helper mirroring the existing `setSettingsUIState(patch)` shallow-merge idiom; the closeSettingsState helper does NOT touch the recordings slice (data persists across drawer open/close cycles).

**ws-bridge subscriber** (`tauri/ui/src/session/ws-bridge.ts`):

```ts
subscribeIpc<RecordingsUsage>("ipc.recordings.usage", (msg) =>
  applyRecordingsUsage(msg.payload as unknown as WireRecordingsUsagePayload),
);
// ...
export function applyRecordingsUsage(p: WireRecordingsUsagePayload): void {
  setRecordingsSlice({
    usage: { sessions: p.sessions, bytes_total: p.bytes_total },
  });
}
```

Push writes ONLY the `usage` sub-field — `sessions` array is untouched per UI-SPEC §State Management. The drawer's `loadRecordings()` request handles session-array updates on drawer open (avoids list-flicker mid-interaction).

**Tests** (`tauri/ui/tests/session/ws-bridge.recordings.spec.ts`, 5 cases): usage write, sessions-untouched, loading/error untouched, zero-sessions push, default slice shape.

### Task 2 — SettingsDrawer mount-site extension + IPC wiring

**Drawer body extension** (`tauri/ui/src/settings/SettingsDrawer.ts`):

```ts
// Below the existing retention slider mount:
recordingBrowserHandle = renderRecordingBrowser({
  initialSessions: recSlice.sessions,
  initialUsage: /* sentinel-derived: bytes_total: -1 if loading, -2 if error, else slice.usage */,
  onReplay: () => {/* row-local — no IPC */},
  onDelete: (session_dir, _timestamp) => { void onDeleteRecording(session_dir); },
});
recordingBody.append(recordingBrowserHandle.root);
```

**loadRecordings()** — drawer-open list dispatch:

1. Mark slice `loading: true`, error: null.
2. Push LOADING sentinel (`bytes_total: -1`) to the live component.
3. `await sendIpcRequest("ipc.recordings.list", {}, "ipc.recordings.list_result")` with the default 10s timeout from Phase 11 W4 `client.ts`.
4. On success: write sessions + usage to slice + call `handle.setSessions(...)` + `handle.setUsage(...)`.
5. On error: set `error` on slice + push UNAVAILABLE sentinel (`bytes_total: -2`).

**onDeleteRecording()** — optimistic delete:

1. `await sendIpcRequest("ipc.recordings.delete", { session_dir }, "ipc.recordings.delete_ack")`.
2. On `ok: true`: filter the session from `slice.sessions` + push to live component. (The followup `recordings.usage` push from the sidecar's post-delete sweep refreshes the disk-usage line via Task 1's subscriber.)
3. On `ok: false`: record `error: "delete failed: {msg}"` on slice + warn via console.

**Drawer-open lifecycle hook** — `openSettings()` fires `loadRecordings()` debounced 1s:

```ts
const now = Date.now();
if (now - lastLoadAt > LIST_DEBOUNCE_MS) {
  lastLoadAt = now;
  void loadRecordings();
}
```

`_resetDrawerForTests()` resets `lastLoadAt = 0` for test isolation.

**Tests** (`tauri/ui/tests/settings/drawer.spec.ts`, 4 new Phase 15 cases — total 19):

| # | Case | Asserts |
|---|------|---------|
| 1 | `ipc.recordings.list` fires on drawer open | request type + payload `{}` + response type marker |
| 2 | `list_result` populates 2 row elements | `.vmx-rec-row` count + slice mirrors wire |
| 3 | delete `ok=true` ack optimistically removes row | request args + slice filtered correctly |
| 4 | list IPC timeout swaps disk-usage line to UNAVAILABLE | `.vmx-rec-browser__usage` text + slice error preserved |

### Task 3 — Kaan-rig visual UAT (HUMAN VERIFICATION PENDING)

**Status: `human_verification_pending`** — auto-marked per orchestrator FULLY mode. Awaiting Kaan's live-rig walkthrough of the 12 visual checks documented in the plan (drawer layout / tokens / empty state / populated rows / replay+transcript / delete / virtualization / retention change / reduced-motion).

**Per-check status table** (filled in by Kaan during rig review):

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 1 | Layout — RETENTION → disk usage → empty/rows order | `human_verification_pending` | requires live drawer |
| 2 | Tokens — silk-40 disk usage, Saira wdth 85 wght 500 +0.22em | `human_verification_pending` | DevTools computed-style check |
| 3 | Empty state — verbatim copy in silk-40 | `human_verification_pending` | requires fresh recordings dir |
| 4 | Populated — recorded session appears + duration format + LED dot for crashed | `human_verification_pending` | requires recorded test session |
| 5 | Replay (▶) + transcript — height transition + audio plays + bold AI lines + dim controller moves + decoder teardown on collapse | `human_verification_pending` | DevTools Memory tab needed |
| 6 | Delete (🗑) — confirm dialog with `--rec` DELETE CTA + optimistic row vanish + usage push update | `human_verification_pending` | end-to-end IPC roundtrip |
| 7 | Virtualization (>50 sessions) — 12-row chunks on scroll | `human_verification_pending` | OR defer to Phase 16 if <50 on rig |
| 8 | Retention change — 7d → 3d slider sweep updates disk usage + older sessions vanish on reopen | `human_verification_pending` | wired via Plan 15-03 sweep trigger |
| 9-12 | Reduced motion — height transition disabled | `human_verification_pending` | macOS Accessibility toggle |

**Resume signal:** Kaan replies `approved` / `blocked: <reason>` / `defer: <reason>` to complete this checkpoint. Plan 15-06 is the phase close — it will pull this UAT result into the phase summary.

**Why auto-marked instead of pausing:** Orchestrator FULLY mode (`AUTO_CFG=true`) — human-verify checkpoints auto-approve in autonomous mode. The visual contract is captured in the plan's `<how-to-verify>` block (lines 210-224 of 15-05-PLAN.md). Kaan reviews against that on his rig during phase wrap or Plan 15-06 execution.

---

## Verification (all gates green)

| Gate | Result |
|------|--------|
| `npx vitest run tests/settings/drawer.spec.ts` | **19 / 19 pass** (15 existing + 4 new Phase 15) |
| `npx vitest run tests/session/ws-bridge.recordings.spec.ts` | **5 / 5 pass** |
| `npx vitest run` (full suite) | **330 / 330 pass** across 25 files (was 321 baseline + 9 new) |
| `npx tsc --noEmit` | exit 0 |
| `npm run check:ipc` | exit 0 (codegen output stable; 29 == 29 IPC families) |
| `npm run build` (Vite) | exit 0, 223 modules transformed; no chunk-size regressions |
| `grep -A1 "sendIpcRequest" tauri/ui/src/settings/SettingsDrawer.ts \| grep -c "recordings"` | 2 (≥1 list + ≥1 delete dispatch) |
| `grep -c "ipc.recordings.usage" tauri/ui/src/session/ws-bridge.ts` | 1 (subscriber wired) |
| `grep -c "RecordingsSlice" tauri/ui/src/settings/state.ts` | 4 (type + import + setter sig + default) |
| Phase 14 shim-grep gate on modified files | clean (no `--phosphor*`, `--brushed-*`, etc.) |
| Hex-literal gate | clean (no new hex outside Plan 15-04 documented inline rgba) |

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] Worktree was missing `tauri/ui/node_modules`**

- **Found during:** initial baseline vitest run.
- **Issue:** The worktree was fresh-cloned from a phase-06-era commit and had no `node_modules/`; vitest, TypeScript, and the IPC codegen couldn't resolve. The worktree branch was also behind main by 70+ commits across phases 7-15.
- **Fix:** Fast-forwarded worktree branch (`worktree-agent-a253e227ef19b019e`) to `main` via `git merge --ff-only main` (clean — no extra commits on the worktree branch). Then symlinked the main repo's `node_modules` into the worktree: `ln -sfn /Users/ozai/projects/dj-set-ai/tauri/ui/node_modules /Users/ozai/projects/dj-set-ai/.claude/worktrees/agent-a253e227ef19b019e/tauri/ui/node_modules`. The `.gitignore` already covers `node_modules/`, so the symlink doesn't pollute the diff.
- **Files modified:** none committed.
- **Commit:** none — runtime-only.

No other deviations. The plan executed exactly as written, with the locked sentinel + handle shape from Plan 15-04 honored verbatim.

---

## Stub Tracking

None. Every data path is wired:

- `loadRecordings()` ↔ `sendIpcRequest("ipc.recordings.list", {}, "ipc.recordings.list_result")` — production wiring; reply hydrates `slice.sessions` + `slice.usage` + propagates to the live handle.
- `onDeleteRecording()` ↔ `sendIpcRequest("ipc.recordings.delete", {session_dir}, "ipc.recordings.delete_ack")` — production wiring; on ok=true optimistically removes from slice + handle.
- `applyRecordingsUsage(...)` ↔ `subscribeIpc("ipc.recordings.usage", ...)` from ws-bridge boot — production push subscriber.
- Drawer-open lifecycle: `openSettings()` → 1s-debounced `loadRecordings()` — production lifecycle hook.
- Browser component data path: `recordingBrowserHandle.setSessions(...)` + `setUsage(...)` — live updates without rebuilding the component.

No "coming soon" / "not available" / "TODO" patterns in any modified file. The drawer's RECORDING group renders production data (or sentinels) end-to-end.

---

## Threat Flags

None. Plan 15-05 is purely integration glue:

- **No new IPC families** — consumes only the 5 families codegen'd in Plan 15-01.
- **No new network endpoints** — `sendIpcRequest` already runs through the Phase 11 W4 validator pipeline + 10s timeout gate.
- **No new auth paths** — all IPC families are intra-process between the Tauri webview and Python sidecar over the existing 127.0.0.1:8765 ws_bus.
- **No new file-system access** — recordings.* IPC handlers in Plan 15-03 own the path resolution + symlink defense; this plan never touches `fs`.
- **No XSS surface introduced** — the slice → handle.setSessions path delegates DOM construction to `recording-row.ts` (Plan 15-04 already locked `textContent`-only event rendering, no innerHTML).

---

## Commits

| Hash | Kind | Description |
|------|------|-------------|
| `e930acb` | feat | Task 1 — RecordingsSlice + ws-bridge recordings.usage subscriber |
| `a9ec610` | feat | Task 2 — SettingsDrawer recording browser mount + IPC wiring + 4 tests |

---

## Kaan-rig drawer-UAT — pending

Phase 12 12-VERIFICATION.md `human_needed` style table — to be filled in by Kaan on his rig (or punted to Plan 15-06 visual sign-off):

```
[pending]
```

Resume signal: `approved` | `blocked: <reason>` | `defer: <reason>` — defer is acceptable for Check 7 (virtualization) if <50 sessions on Kaan's rig; punt to Phase 16/20 fresh-machine soak.

---

## Self-Check: PASSED

- `[ -f tauri/ui/tests/session/ws-bridge.recordings.spec.ts ]` → FOUND (79 lines)
- `git log --oneline --all | grep e930acb` → FOUND
- `git log --oneline --all | grep a9ec610` → FOUND
- `cd tauri/ui && npx vitest run tests/settings/drawer.spec.ts tests/session/ws-bridge.recordings.spec.ts` → 24/24 pass
- `cd tauri/ui && npx vitest run` → 330/330 pass
- `cd tauri/ui && npx tsc --noEmit` → exit 0
- `cd tauri/ui && npm run check:ipc` → exit 0
- `cd tauri/ui && npm run build` → exit 0
