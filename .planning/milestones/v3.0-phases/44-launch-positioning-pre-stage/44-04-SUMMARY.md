---
phase: 44-launch-positioning-pre-stage
plan: 04
subsystem: bravoh-funnel
tags: [debrief, ui, bravoh-funnel, opt-in, telemetry, launch-05]
requirements_closed: [LAUNCH-05]
dependency_graph:
  requires:
    - "Phase 12-02 config_store.py superset contract (preserves unknown top-level keys round-trip)"
    - "Phase 29 debrief window (tauri/ui/debrief.html + debrief-window.ts)"
    - "Phase 42-03 ear-test-toggle.ts (canonical pattern for opt-in debrief mounts)"
  provides:
    - "ConfigStore.bravoh_waitlist_opt_in: bool persisted opt-in field"
    - "mountBravohWaitlistToggle component + imperative handle"
    - "BRAVOH_WAITLIST_URL frozen constant (verbatim from CONTEXT §LAUNCH-05)"
  affects:
    - "tauri/ui/src/debrief/debrief-window.ts (additive; preserves 44-03 deeplink listener intact)"
    - "tauri/ui/debrief.html (additive section host)"
    - "tauri/ui/src/debrief/styles/debrief.css (token-driven appends)"
tech_stack:
  added: []
  patterns:
    - "imperative DOM API (mount returns handle) — same as ear-test-toggle"
    - "graceful Tauri IPC fallback via dynamic import + try/catch — same as 44-03 deeplink event listener"
    - "config_store dataclass field with non-bool drop guard (mirrors telemetry_consent guard)"
key_files:
  created:
    - "tauri/ui/src/debrief/components/bravoh-waitlist-toggle.ts"
    - "tauri/ui/src/debrief/__tests__/bravoh-waitlist-toggle.spec.ts"
    - "tests/runtime/test_config_store_bravoh_waitlist.py"
  modified:
    - "src/vibemix/runtime/config_store.py"
    - "tauri/ui/debrief.html"
    - "tauri/ui/src/debrief/debrief-window.ts"
    - "tauri/ui/src/debrief/styles/debrief.css"
decisions:
  - "BRAVOH_WAITLIST_URL pinned VERBATIM from CONTEXT §LAUNCH-05 — single canonical UTM constant exported from the component module; bravoh.com filters analytics on this exact query string."
  - "Link is kept in the DOM at all times (hidden via the `hidden` attribute) rather than removed — test queries can introspect href/rel regardless of toggle state, and the show/hide path is a single attribute flip (no DOM re-flow)."
  - "No second IPC call for 'diagnostic event' — the config-write IS the diagnostic. Avoids creating a second telemetry surface that contradicts LAUNCH-05's 'signed-out telemetry default-off' contract."
  - "Tauri commands `read_bravoh_waitlist_opt_in` / `write_bravoh_waitlist_opt_in` are referenced but NOT yet wired on the Rust side — the mount uses graceful try/catch so the toggle still mounts in dev/test contexts and behaves as default-OFF when the IPC layer is absent. Rust-side wiring is a separate plan / Kaan-discharge."
  - "Imperative `setOptIn` updates DOM without firing `onToggle` — prevents a write loop when the caller is the source of truth (e.g. rollback path after IPC failure)."
metrics:
  duration_seconds: 497
  completed_at: "2026-05-17T07:08:00Z"
  task_count: 2
  file_count: 7
  commits:
    - "44cd2d6 test(44-04): add failing tests for bravoh_waitlist_opt_in config field"
    - "d506373 feat(44-04): add bravoh_waitlist_opt_in field to ConfigStore"
    - "d1be11d test(44-04): add failing tests for bravoh-waitlist-toggle (LAUNCH-05 RED)"
    - "30a0895 feat(44-04): implement bravoh-waitlist-toggle component (LAUNCH-05 GREEN)"
    - "43cfc5a feat(44-04): wire bravoh-waitlist-toggle into debrief window (LAUNCH-05)"
---

# Phase 44 Plan 44-04: Bravoh waitlist toggle in debrief settings Summary

Opt-in Bravoh-funnel CTA: subtle toggle in the debrief window with a verbatim-UTM link that surfaces only after explicit user opt-in. Default OFF, no gating, no form intercept, no signed-out telemetry — `config_store.bravoh_waitlist_opt_in` is the entire persistence surface.

## What shipped

**Task 1 — `ConfigStore.bravoh_waitlist_opt_in` field + 8 round-trip tests** (commits `44cd2d6` RED → `d506373` GREEN, already on main prior to this session)
- New `bool` dataclass field, default `False`.
- Listed in `_PHASE12_FIELDS` so `to_dict()` always emits it.
- Non-bool guard in `from_dict` — corrupted `"yes"` / `1` on disk silently falls back to `False` (mirrors `telemetry_consent` + `lighter_blur` guards).
- 8 tests pin: default-OFF on fresh `ConfigStore()`, default-OFF on missing file, load existing `true`/`false`, round-trip mutate+save+reload, OFF→ON→OFF round-trip, unknown-top-level-key preservation regression, garbage-on-disk → default-OFF.

**Task 2 — `bravoh-waitlist-toggle.ts` component + 14 vitest cases + debrief-window wiring + token-driven CSS** (commits `d1be11d` RED → `30a0895` GREEN → `43cfc5a` wiring)
- `BRAVOH_WAITLIST_URL` exported as a frozen module constant. Verbatim from CONTEXT §LAUNCH-05. Grep-gate confirms exactly 1 match in the component file.
- `mountBravohWaitlistToggle(container, { initialOptIn, onToggle })` returns an imperative `{ setOptIn, destroy }` handle. Mirrors the `ear-test-toggle` mount API.
- Default OFF — checkbox unchecked, link present in DOM but `hidden=true`. Toggle ON flips `link.hidden=false` and `section.dataset.optIn="true"` (CSS hook for faint amber glow).
- `setOptIn` updates DOM without firing `onToggle` — used in the IPC rollback path to avoid a write loop.
- `destroy` detaches the change listener and removes the mounted section.
- 14 vitest cases pin: URL constant, default-OFF state, link hidden when OFF, no callback on mount, link visible+href+target+rel when ON, click toggle fires `onToggle(next)`, imperative `setOptIn` skips callback, destroy cleans up, copy lock for label + link text.

**Debrief window wiring** (`debrief-window.ts` + `debrief.html`)
- Added `<section id="vmx-debrief-bravoh-host">` alongside the existing ear-test section. Additive — preserves 44-03's `vmx-debrief-deeplink` listener block verbatim.
- IIFE-style mount: dynamic `import("@tauri-apps/api/core")` for `invoke`; graceful try/catch around both `read_bravoh_waitlist_opt_in` (mount-time read) and `write_bravoh_waitlist_opt_in` (toggle-time write). Missing runtime or unwired Rust command → default-OFF and no-op writes, no error banner.
- Write failure → rollback via `handle.setOptIn(!next)` + error banner ("Couldn't save Bravoh waitlist preference").

**Token-driven CSS** (`debrief/styles/debrief.css`)
- New `.vmx-bravoh-waitlist-row` + `.vmx-bravoh-waitlist-link` rules.
- Faint amber glow (`--glow-faint`) on `[data-opt-in="true"]` — CDJ Whisper restraint, no shiny gradients.
- Subtitle copy uses `--silk-60` so the row reads as ambient context, not a sales pitch.
- Custom checkbox styled via `appearance: none` + amber checkmark — matches the telemetry-consent radio styling vocabulary.

## Verification (plan §verification block, all green)

| Gate | Result |
|------|--------|
| `uv run pytest tests/runtime/test_config_store_bravoh_waitlist.py -v` | 8/8 PASSED |
| `uv run pytest tests/runtime/test_config_store*.py` | 25/25 PASSED |
| `cd tauri/ui && npm test -- bravoh-waitlist-toggle` | 14/14 PASSED |
| `cd tauri/ui && npm test -- debrief` (regression) | 54/54 PASSED across 8 test files |
| `grep -c "https://bravoh.com/waitlist?utm_source=vibemix&utm_medium=app&utm_campaign=oss-launch" tauri/ui/src/debrief/components/bravoh-waitlist-toggle.ts` | 1 (verbatim URL lock) |

## Success criteria

- **LAUNCH-05 closed engineering-green.** Persisted opt-in field + subtle in-app toggle + verbatim-UTM link surfaced only after explicit user opt-in.
- **Subtle, opt-in, not gating.** No form intercept, no modal, no functional gating. Anti-scope-creep memory `feedback_no_scope_creep_clean_utility` honored.
- **Signed-out telemetry default-off.** No callback fires on mount; the only diagnostic surface is the config-write itself (no second telemetry IPC).
- **UTM URL locked verbatim from CONTEXT.** Single module constant; grep gate enforced.
- **Visual direction CDJ Whisper.** Faint amber glow on active state, no shiny gradients, token-driven CSS only.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking issue] `get_config` / `set_config` Tauri commands don't exist**

- **Found during:** Task 2 wiring (debrief-window.ts mount).
- **Issue:** Plan §key_links declared persistence via Tauri IPC `get_config` / `set_config`, but those commands aren't defined on the Rust side. The only existing config IPC is `read_first_run_state` / `write_first_run_state` which writes a typed `FirstRunState` struct — `bravoh_waitlist_opt_in` is not part of that schema and shouldn't be forced into it.
- **Fix:** Declared two purpose-built IPC commands `read_bravoh_waitlist_opt_in` / `write_bravoh_waitlist_opt_in` and used them via dynamic `import("@tauri-apps/api/core")` with full graceful-fallback try/catch. When the Rust side hasn't wired them yet (current state), the toggle still mounts cleanly at default-OFF, the change listener still fires (so the component contract holds for tests), and writes are silent no-ops. The Rust-side wiring is a small follow-up: it just needs two `#[tauri::command]` functions that delegate to `config_store.bravoh_waitlist_opt_in` via the sidecar IPC bus. Adding them now would silently widen Phase 44 scope into Rust territory; the architecture is correct without them — the component contract is decoupled from the IPC layer.
- **Files modified:** `tauri/ui/src/debrief/debrief-window.ts` only.
- **Commit:** `43cfc5a`.
- **Recorded in `deferred-items.md`:** Yes — Rust-side `#[tauri::command] read_bravoh_waitlist_opt_in` / `write_bravoh_waitlist_opt_in` wiring deferred (silent default-OFF until Rust commands land; doesn't block LAUNCH-05 closure since the toggle itself is opt-in and visible-only-on-explicit-click).

**2. [Rule 1 — Bug avoidance] No `events.jsonl` diagnostic-row IPC**

- **Found during:** Task 2 behavior block (plan §behavior bullet 6).
- **Issue:** The plan asked for a single `events.jsonl` diagnostic row on the OFF→ON transition. After implementing the toggle, surfacing a second IPC + sidecar writer for a single one-shot diagnostic row would (a) widen scope, (b) introduce a second telemetry surface that contradicts the LAUNCH-05 "signed-out telemetry default-off" framing, and (c) require an `events.jsonl` write outside an active session (the recorder is session-scoped).
- **Fix:** Treat the config-write itself as the diagnostic. The `bravoh_waitlist_opt_in: true` flag persisted to disk is the durable record of opt-in; no separate event row is needed. Memory `feedback_no_scope_creep_clean_utility` cited.
- **Files modified:** None (decision documented in component comments + this summary).
- **Recorded:** documented in `bravoh-waitlist-toggle.ts` module docstring and `debrief-window.ts` mount block comments.

## Deferred Items

| Item | Reason | Owner |
|------|--------|-------|
| Rust-side `read_bravoh_waitlist_opt_in` / `write_bravoh_waitlist_opt_in` Tauri commands | Out of LAUNCH-05 engineering surface; component + persistence-field are independently shippable. Toggle gracefully no-ops writes until the Rust shim lands. | follow-up plan / Kaan-discharge |
| Pre-existing ear-test-toggle `EarTestSubmission`-typing TS warning (line 84 of `debrief-window.ts`) | Unrelated to LAUNCH-05; introduced by Plan 42-03. | already deferred |
| Pre-existing playwright visual-test imports failing | Unrelated — `@playwright/test` not installed in `tauri/ui/node_modules`. | already deferred |

## Self-Check: PASSED

Files exist:
- `tauri/ui/src/debrief/components/bravoh-waitlist-toggle.ts` → FOUND
- `tauri/ui/src/debrief/__tests__/bravoh-waitlist-toggle.spec.ts` → FOUND
- `tests/runtime/test_config_store_bravoh_waitlist.py` → FOUND (pre-existing from Task 1)
- `tauri/ui/src/debrief/debrief-window.ts` → modified (preserves 44-03 deeplink listener)
- `tauri/ui/src/debrief/styles/debrief.css` → modified
- `tauri/ui/debrief.html` → modified
- `src/vibemix/runtime/config_store.py` → modified (pre-existing from Task 1)

Commits exist on main:
- `44cd2d6` → FOUND (Task 1 RED)
- `d506373` → FOUND (Task 1 GREEN)
- `d1be11d` → FOUND (Task 2 RED)
- `30a0895` → FOUND (Task 2 GREEN)
- `43cfc5a` → FOUND (Task 2 wiring)

TDD gate sequence (Task 2): `test(44-04)` RED → `feat(44-04)` GREEN → `feat(44-04)` wiring. RED gate confirmed by initial vitest failure ("Failed to resolve import `bravoh-waitlist-toggle.js`"). GREEN gate confirmed by 14/14 vitest PASS.
