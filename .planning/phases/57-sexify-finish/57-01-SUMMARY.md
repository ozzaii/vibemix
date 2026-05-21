---
phase: 57-sexify-finish
plan: 01
subsystem: testing
tags: [pytest, vitest, regression-gate, tauri, capabilities, tcc, macos-permissions, ast, jsdom]

# Dependency graph
requires:
  - phase: v0.1.0-rc1 carryover (fac4c4a)
    provides: the three shipped fixes (drag capability + JS drag fallback + chrome strip display:none + permissions.rs direct-open + TCC prime-registration path)
provides:
  - "Static pytest gate pinning core:window:allow-start-dragging + permissions.rs direct Command::new(\"open\") deep-link form"
  - "Vitest spec pinning the mascot/index.ts document-mousedown startDragging() fallback with button!==0 + [data-no-drag] guards"
  - "Extended chrome spec pinning chrome.css display:none over the three Phase 14 strip selectors"
  - "AST-scoped pytest gate pinning the TCC prime-registration call inside wizard.boot() + both capture-API requests"
affects: [58-signed-publish, future Tauri/wizard refactors, mascot overlay work]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "AST-scoped source assertion: ast.get_source_segment to bound an assertion to a specific function body so a moved call-site (not just a deleted one) fails the test"
    - "JSON-membership capability gate (parse permissions array, check membership) over substring matching — immune to whitespace/ordering churn"

key-files:
  created:
    - tests/security/test_drag_capability_present.py
    - tests/security/test_tcc_prime_path_wired.py
    - tauri/ui/src/mascot/__tests__/drag.spec.ts
  modified:
    - tauri/ui/tests/mascot.chrome.test.ts

key-decisions:
  - "AST boot-scoping over line slicing: bound the _prime_tcc_registration assertion to boot()'s source segment so moving the call out of boot fails the test (empirically verified)"
  - "JSON-membership (not substring) for the drag capability so reordering/whitespace in default.json cannot false-pass"
  - "Pin BOTH the presence of Command::new(\"open\") AND the absence of shell().open so the deprecated path can't quietly return"

patterns-established:
  - "VERIFY-AND-HARDEN: regression pins for already-shipped fixes; assertions read source as untrusted text, never run cargo/app code"

requirements-completed: [POLISH-02]

# Metrics
duration: ~10min
completed: 2026-05-21
---

# Phase 57 Plan 01: VERIFY-AND-HARDEN POLISH-02 Carryover Bugs Summary

**Five headless regression assertions (2 new pytest gates, 1 new vitest spec, 1 extended chrome spec) that pin the three v0.1.0-rc1 carryover-bug fixes shipped in `fac4c4a` so the drag capability, JS drag fallback, chrome strip hide, deep-link form, and TCC prime path can no longer silently regress.**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-05-21T07:40:00Z (approx)
- **Completed:** 2026-05-21T07:50:17Z
- **Tasks:** 2
- **Files modified:** 4 (3 created, 1 extended)

## Accomplishments
- `tests/security/test_drag_capability_present.py` — pins `core:window:allow-start-dragging` as a parsed-array member of `capabilities/default.json` (POLISH-02a) and pins `permissions.rs` using `Command::new("open")` with no `shell().open` (POLISH-02c deep-link form).
- `tauri/ui/src/mascot/__tests__/drag.spec.ts` — pins the `document` mousedown → `startDragging()` fallback in `mascot/index.ts` with its `button !== 0` and `[data-no-drag]` guards (POLISH-02a).
- Extended `tauri/ui/tests/mascot.chrome.test.ts` — new case asserts `chrome.css` hides `.mascot-window > .border-anim`, `.mascot-window__top-label`, `.mascot-window__state-caption` via `display: none` (POLISH-02b). Whitespace-normalized so a reorder can't false-fail and any selector/display deletion fails.
- `tests/security/test_tcc_prime_path_wired.py` — AST-scoped gate: `_prime_tcc_registration` must be called from WITHIN `boot()` (empirically verified that moving it out turns the test red), the prime body must fire both `request_microphone_permission` + `request_screen_recording_permission`, and `_on_permission_check` must keep both request_* calls (POLISH-02c TCC list-population).

## Task Commits

Each task was committed atomically:

1. **Task 1: Pin drag capability + JS drag handler + chrome strip** - `1e99ac8` (test)
2. **Task 2: Pin the TCC prime-registration path** - `a393f7c` (test)

## Files Created/Modified
- `tests/security/test_drag_capability_present.py` (created) - JSON-membership drag-cap gate + permissions.rs direct-open / no-shell-open gate
- `tests/security/test_tcc_prime_path_wired.py` (created) - AST-scoped boot()→_prime_tcc_registration + both capture-API request gates
- `tauri/ui/src/mascot/__tests__/drag.spec.ts` (created) - mascot/index.ts JS drag fallback + guards
- `tauri/ui/tests/mascot.chrome.test.ts` (modified) - appended chrome strip `display: none` regression case; pre-existing cases untouched

## Decisions Made
- Used `ast.get_source_segment(src, boot_node)` to bound the prime-path assertion to `boot()`'s body, so the call leaving `boot()` (not just being deleted) fails the test. Empirically confirmed via a removal mutation.
- Used JSON `permissions`-array membership for the drag capability rather than substring matching so reordering/whitespace can't false-pass; object-form entries handled by `identifier`.
- Pinned both the presence of `Command::new("open")` and the absence of `shell().open` so the deprecated silent-failure path can't quietly reappear.
- Routed `drag.spec.ts` into `src/mascot/__tests__/` (matches the existing `src/mascot/__tests__/*.spec.ts` jsdom glob) and extended the existing chrome `tests/**/*.test.ts` (jsdom) rather than rewriting.

## Deviations from Plan

None - plan executed exactly as written. Zero production files edited; no Kaan WIP file touched; no new package installed.

## Issues Encountered
- `tauri/ui/node_modules` was absent in the worktree. Per the plan's parallel-execution note, symlinked it from the main checkout (`ln -s /Users/ozai/projects/dj-set-ai/tauri/ui/node_modules tauri/ui/node_modules`). The symlink is intentionally NOT staged (verified absent from every commit's staged set). It is untracked-only.

## Verification
- `pytest -q tests/security/test_drag_capability_present.py tests/security/test_tcc_prime_path_wired.py` → 7 passed.
- `vitest run src/mascot/__tests__/drag.spec.ts tests/mascot.chrome.test.ts` → 24 passed (4 drag + 20 chrome, incl. the new strip case).
- `git diff --name-only` after both commits → empty; `git status` clean except the untracked node_modules symlink. Confirms zero production edits and zero Kaan WIP touches.
- AST boot-scoping sanity: removing the prime call from boot's body slice makes the membership check `False` (test would go red) — confirmed empirically.

## KAAN-ACTION (deferred — real hardware / felt confirmation, not engineering)
The three real-app interaction confirmations stay surfaced as KAAN-ACTION (per plan must_haves.kaan_action). Engineering only pins the code is present + regression-gated:
- Real-app: the mascot window actually drags on Kaan's Mac.
- Real-app: no mascot chrome strip renders.
- Real-app: the macOS Privacy list populates with vibemix after a fresh wizard boot.

## Next Phase Readiness
- POLISH-02's three carryover-bug fixes are now each pinned by at least one headless regression assertion. A stray edit dropping the drag cap, un-hiding the chrome strip, removing the JS drag fallback, breaking the deep-link form, or moving the TCC prime call out of `boot()` now turns a test red.
- No blockers introduced. STATE.md / ROADMAP.md intentionally NOT modified (parallel-executor constraint).

## Self-Check: PASSED

All 4 test files + SUMMARY.md exist on disk; both task commits (`1e99ac8`, `a393f7c`) present in git log.

---
*Phase: 57-sexify-finish*
*Completed: 2026-05-21*
