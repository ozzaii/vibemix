---
phase: 91-controller-renderer-midi-mirror
plan: 04
subsystem: ui
tags: [tauri, rust, webview, learn-window, p91, render-07]

# Dependency graph
requires:
  - phase: 91-controller-renderer-midi-mirror
    provides: |
      Plan 91-01 — `capabilities/default.json` windows scope includes "learn"
      and `open_learn_window` allowlist entry; Plan 91-02 — `tests/learn/` and
      `tauri/ui/tests/learn/` test stubs (including the RED `test_learn_window_label.spec.ts`
      static-grep gate) scaffolded.
provides:
  - "tauri/src-tauri/src/learn_window.rs — new Rust module declaring `LEARN_WINDOW_LABEL: &str = \"learn\"` + `open_learn_window` Tauri command (focus-existing pattern; opens `learn.html` at 1280×720; no sidecar lifecycle)."
  - "main.rs — `mod learn_window;` declaration + `learn_window::open_learn_window` in `generate_handler![]` list."
  - "Round-trip with Plan 91-01 capabilities allowlist closes — the webview can now invoke `open_learn_window` and a separate `WebviewWindow` mounts."
affects: [91-05, 91-06, 91-07]

# Tech tracking
tech-stack:
  added: []  # zero new crates — uses existing `tauri` from Cargo.toml
  patterns:
    - "Trimmed-mirror discipline (research §Pattern 7) — `learn_window.rs` mirrors `debrief_window.rs` but DROPS the sidecar-spawn / path-validation / deep-link / close-handler / crash-watcher branches because Learn is a passive surface sharing the main vibemix process."

key-files:
  created:
    - "tauri/src-tauri/src/learn_window.rs (116 lines, 4,799 bytes)"
  modified:
    - "tauri/src-tauri/src/main.rs (+2 net lines: mod declaration + handler entry)"

key-decisions:
  - "Adopted research §Code Example 2 as the spec for `learn_window.rs` — verbatim minus 2 additions (added a `learn_window_default_dimensions` unit test pinning the 1280×720/960×540 named constants, and an extended SPDX/§Pattern-7 module docstring)."
  - "No `LearnSidecarHandle` State and no `--learn` CLI flag — the Learn webview connects to the existing ws:8765 once it mounts (Invariant #4 — one-socket — preserved). Documented in module docstring."
  - "Window title `Learn — vibemix` uses an em-dash separator (per UI-SPEC §Design System, mirrors the `Debrief — <session>` pattern)."

patterns-established:
  - "Trimmed-mirror precedent: future second-window features (e.g. settings/preferences) can mirror `learn_window.rs` (passive surface, no sidecar) rather than `debrief_window.rs` (full sidecar lifecycle) when no child process is required."

requirements-completed: [RENDER-07]

# Metrics
duration: 4min
completed: 2026-05-27
---

# Phase 91 Plan 04: Controller Renderer + MIDI Mirror — Tauri Rust Shell Summary

**Tauri 2.x `learn_window.rs` module + main.rs wire-in: `LEARN_WINDOW_LABEL = "learn"` const, `open_learn_window` command (focus-existing semantics, 1280×720 default), trimmed mirror of debrief precedent (no sidecar lifecycle).**

## Performance

- **Duration:** 4 min
- **Started:** 2026-05-27T21:33:22Z
- **Completed:** 2026-05-27T21:37:30Z
- **Tasks:** 2
- **Files modified:** 2 (1 new + 1 edited)

## Accomplishments

- New `tauri/src-tauri/src/learn_window.rs` (116 lines) declares `pub const LEARN_WINDOW_LABEL: &str = "learn"` and exposes the `#[tauri::command] pub async fn open_learn_window(app: AppHandle) -> Result<(), String>` entry point.
- Focus-existing pattern: if a window with label `"learn"` already exists, `set_focus()` it and return `Ok(())`; otherwise build a new `WebviewWindow` pointing at `WebviewUrl::App("learn.html".into())` with title `"Learn — vibemix"`, default 1280×720, min 960×540, resizable + decorated.
- `main.rs` updated with exactly 2 net added lines — `mod learn_window;` in alphabetical position (between `mod hotkey;` and `mod library_cmds;`) and `learn_window::open_learn_window,` appended to the `generate_handler![]` list.
- 2 Rust unit tests added: `learn_window_label_const_is_lowercase_no_spaces` (pins the const value + lowercase + no-whitespace invariant, mirroring the debrief precedent) and `learn_window_default_dimensions` (pins the 4 named float constants against drift to the SVG `viewBox="0 0 1280 720"` design grid).
- Round-trip with Plan 91-01's `capabilities/default.json` closes: the webview is allowlisted to invoke `open_learn_window` AND the Rust handler now exists.
- Plan 02's RED `tauri/ui/tests/learn/test_learn_window_label.spec.ts` static-grep gate flips RED → GREEN (the file exists with the correct const).

## Task Commits

1. **Task 1: Author `learn_window.rs` trimmed mirror** — `4136f72f` (feat)
   - SPDX header, module docstring (RENDER-07 + §Pattern 7 diff), `LEARN_WINDOW_LABEL` const, 4 named-float dimension constants, `open_learn_window` command, 2 unit tests.
2. **Task 2: Wire `mod learn_window;` + `invoke_handler` entry in `main.rs`** — `508ef572` (feat)
   - Inserted module declaration alphabetically; appended handler entry; ALSO rewrote `learn_window.rs` docstrings (Rule 3 auto-fix) to clear the mechanical forbidden-strings grep (see Deviations below).

**Plan metadata commit:** (pending — added with this SUMMARY + STATE/ROADMAP updates.)

## Files Created/Modified

- **Created:** `tauri/src-tauri/src/learn_window.rs` (116 lines, 4,799 bytes) — Apache-2.0; new Rust module exposing the Learn second-window Tauri command.
- **Modified:** `tauri/src-tauri/src/main.rs` — `mod learn_window;` declaration (line 25) + `learn_window::open_learn_window,` handler entry (line 111). Net diff = 2 added lines, zero deletions, zero other changes.

## Main.rs Exact Diff

```diff
diff --git a/tauri/src-tauri/src/main.rs b/tauri/src-tauri/src/main.rs
@@ -22,6 +22,7 @@ mod debrief_window;
 mod debug_log;
 mod djay_ax;
 mod hotkey;
+mod learn_window;
 mod library_cmds;
 mod mascot_window;
 mod overlay;
@@ -107,6 +108,7 @@ fn main() {
             library_cmds::library_models,
             library_cmds::library_embed_folder,
             library_cmds::open_library_window,
+            learn_window::open_learn_window,
         ])
```

## Test Results

```
$ cd tauri/src-tauri && cargo test learn_window
running 2 tests
test learn_window::tests::learn_window_default_dimensions ... ok
test learn_window::tests::learn_window_label_const_is_lowercase_no_spaces ... ok
test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 90 filtered out

$ cd tauri/src-tauri && cargo test
test result: ok. 92 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out
(baseline was 90 → 92 with the 2 new learn_window tests; zero regression)

$ cd tauri/src-tauri && cargo check
Finished `dev` profile [unoptimized + debuginfo] target(s) in 0.29s
(exit 0)

$ cd tauri/ui && npx vitest run tests/learn/test_learn_window_label.spec.ts
Test Files  1 passed (1)  Tests  1 passed (1)
(Plan 02 RED gate flipped GREEN)

$ PYTHONPATH=src python -m pytest -q tests/learn/test_no_new_ws_port.py
1 passed in 0.02s
(one-socket invariant gate stays GREEN — Plan 04 introduced no new ws port)
```

## Acceptance-Criteria Sweep

| Gate | Required | Actual | Pass |
|------|----------|--------|------|
| `learn_window.rs` exists | yes | yes (4,799 bytes) | ✓ |
| Byte count > 1000 | yes | 4,799 | ✓ |
| `pub const LEARN_WINDOW_LABEL: &str = "learn"` grep | 1 match | 1 match (line 41) | ✓ |
| `#[tauri::command]` grep (decorator only) | 1 match | 1 match (line 63) | ✓ |
| `"Learn — vibemix"` grep | 1 match | 1 match (line 77) | ✓ |
| `sidecar\|session_dir\|DebriefDeepLink\|kill_` grep in `learn_window.rs` | 0 matches | 0 matches | ✓ |
| SPDX header | `// SPDX-License-Identifier: Apache-2.0` | matches | ✓ |
| `learn_window_label_const_is_lowercase_no_spaces` test | pass | pass | ✓ |
| `learn_window_default_dimensions` test | pass | pass | ✓ |
| `cargo check` exit code | 0 | 0 | ✓ |
| `^mod learn_window;` in `main.rs` | 1 match | 1 match (line 25) | ✓ |
| `learn_window::open_learn_window` in `main.rs` | 1 match | 1 match (line 111) | ✓ |
| `LearnSidecarHandle\|--learn\|learn_sidecar` global grep | 0 matches | 0 matches | ✓ |
| `main.rs` net added lines | exactly 2 | exactly 2 | ✓ |

## Decisions Made

- **Followed research §Code Example 2 verbatim** for the `learn_window.rs` source, with two intentional additions to satisfy the PLAN spec: (1) the second unit test `learn_window_default_dimensions` (PLAN explicitly required it; not in §Code Example 2 source); (2) an extended module docstring documenting the §Pattern 7 diff (DROPPED vs KEPT lists) so future readers don't re-implement the dropped branches by accident.
- **Did NOT add `.manage(LearnSidecarHandle::default())`** — research §Pattern 7 explicitly forbids it. The Learn webview is a passive surface that connects to the EXISTING main vibemix sidecar's ws:8765 (Invariant #4 — one-socket — preserved).
- **Window title uses em-dash** (`"Learn — vibemix"`) per UI-SPEC §Design System, mirroring the `Debrief — <session>` precedent in `debrief_window.rs:156`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Forbidden-string grep tripped on docstring prose**
- **Found during:** Task 2 (acceptance-criteria sweep)
- **Issue:** My initial `learn_window.rs` module docstring documented the §Pattern 7 deviations using the literal substrings the PLAN's mechanical forbidden-strings grep flags (`sidecar`, `session_dir`, `kill_`, `LearnSidecarHandle`, `--learn`). The intent was negated-prose ("there is no `LearnSidecarHandle` State"), but a `git grep` cannot distinguish prose from real references. The Task 1 acceptance gate `git grep -n 'sidecar\|session_dir\|DebriefDeepLink\|kill_' tauri/src-tauri/src/learn_window.rs` returned 4 matches when it must return 0.
- **Fix:** Rewrote the docstrings to convey the same meaning using neutral substitutes: "main vibemix process" instead of "main sidecar", "no Python child is launched" instead of "no sidecar spawn", "no close-event handler terminating a child" instead of "no kill_*". The §Pattern 7 deviation surface is still documented; no information lost.
- **Files modified:** `tauri/src-tauri/src/learn_window.rs` (docstring rewrite — no behavior change)
- **Verification:** All 5 forbidden-string greps now return 0 matches; both unit tests still pass; full suite still 92/92.
- **Committed in:** `508ef572` (folded into Task 2 commit per the auto-fix-during-verification protocol).

**2. [Rule 3 - Blocking] Extra `#[tauri::command]` grep match from docstring mention**
- **Found during:** Task 1 acceptance sweep (initial run)
- **Issue:** The PLAN says `git grep -n '#\[tauri::command\]' tauri/src-tauri/src/learn_window.rs` returns exactly 1 match. My initial docstring mentioned `#[tauri::command]` in prose, producing 2 matches.
- **Fix:** Rewrote the docstring sentence to use the non-decorated form `tauri::command` (no `#[...]` brackets).
- **Files modified:** `tauri/src-tauri/src/learn_window.rs` (docstring rewrite)
- **Verification:** Grep now returns exactly 1 match — the decorator on line 63.
- **Committed in:** `508ef572` (folded into Task 2 commit).

**3. [Rule 3 - Blocking] Initial commit comment block exceeded "exactly 2 net added lines"**
- **Found during:** Task 2 verification (immediately after the first Edit pass)
- **Issue:** I initially added a 3-line block comment in `main.rs` next to the `learn_window::open_learn_window` handler entry explaining why no `.manage(...)` line was added. This violated the PLAN's "exactly 2 net added lines" acceptance criterion.
- **Fix:** Removed the comment block; the same documentation lives in `learn_window.rs`'s module docstring and in this SUMMARY.
- **Files modified:** `tauri/src-tauri/src/main.rs` (removed 3-line comment in same editing pass before commit)
- **Verification:** `git diff tauri/src-tauri/src/main.rs` now shows exactly 2 net added lines as required.
- **Committed in:** `508ef572` (only the corrected version was committed; the 3-line block never reached the index).

---

**Total deviations:** 3 auto-fixed (all Rule 3 — blocking verification gates). All were prose/comment tweaks to make the mechanical PLAN gates pass; zero behavior change, zero scope creep.
**Impact on plan:** Cosmetic. The shipped Rust code matches research §Code Example 2 + the PLAN's additional dimensions test verbatim.

## Issues Encountered

None. Both tasks executed cleanly; the §Pattern 7 trimmed-mirror discipline was followed exactly; cargo check + cargo test stayed green through every iteration.

## Threat Flags

None. The threat surface from this plan is identical to what the `<threat_model>` block in `91-04-PLAN.md` anticipated — `open_learn_window` lives behind the Plan 01 capability allowlist (mitigates T-91-04-01); the URL is the hardcoded literal `learn.html` (mitigates T-91-04-02); focus-existing semantics bound the window count at 1 (mitigates T-91-04-03). No new security-relevant surface introduced.

## Self-Check

Verifying file + commit claims:

- File `tauri/src-tauri/src/learn_window.rs` exists: `FOUND` (4,799 bytes, 116 lines)
- Commit `4136f72f` (Task 1): `FOUND` in `git log --oneline -3`
- Commit `508ef572` (Task 2): `FOUND` in `git log --oneline -3`
- `pub const LEARN_WINDOW_LABEL: &str = "learn"` in source: `FOUND` (line 41)
- `mod learn_window;` in main.rs: `FOUND` (line 25)
- `learn_window::open_learn_window` in main.rs: `FOUND` (line 111)
- `cargo test learn_window`: `2 PASSED` (verified above)
- `cargo check`: `exit 0` (verified above)
- vitest `test_learn_window_label.spec.ts`: `1 PASSED` (verified above)
- pytest `test_no_new_ws_port.py`: `1 PASSED` (one-socket invariant intact)

## Self-Check: PASSED

## Next Phase Readiness

Plan 91-05 (`Learn Frontend — controller-stage + ws_client + lesson list`) is now unblocked:

- The Rust shell can open a separate `WebviewWindow` for Learn (`open_learn_window` is registered + allowlisted).
- The frontend mount point (`tauri/ui/learn.html`) already exists from prior plan scaffolding (per directory listing); Plan 91-05 wires the TypeScript surface into it.
- The Learn webview will connect to the existing ws:8765 — no further Rust-side wire-in needed for Invariant #4 (one-socket) to hold.
- Plan 91-06 (lesson runtime + AI highlight contract) and Plan 91-07 (the live audit + ear-pass) inherit a working Learn-window shell.

No blockers. No KAAN-ACTION carveouts introduced by this plan (the window opens; the visual / live-hardware ear-pass lives in Plan 91-07's gate).

---
*Phase: 91-controller-renderer-midi-mirror*
*Completed: 2026-05-27*
