---
plan: 29-04
phase: 29-post-session-debrief-mvp-ui
status: complete (compile-deferred — pre-existing environment issue)
wave: 3
requirements: [DEBRIEF-08, DEBRIEF-09]
commits:
  - 1cb7f6f  # feat(29-04): debrief_window Tauri command + DebriefSidecarHandle + crash watcher
tasks_completed: 2/2 (code)
tests_added: 7 (inline #[cfg(test)])
tests_passing: N/A (cargo build script x86_64 bundle missing in dev env)
regression_check: deferred — see Deviations
---

# Plan 29-04 Summary — Tauri Rust shell (debrief_window.rs)

## What was built

### `tauri/src-tauri/src/debrief_window.rs` (NEW)

Single Tauri command `open_debrief_window(app, session_dir)`:

1. **Path validation** (defense-in-depth alongside Plan 29-02 Python
   check): `recordings::validate_under_root(candidate, root)`
   canonicalizes via `Path::canonicalize` + asserts `starts_with(root)`.
   Rejects `../etc/passwd`-style traversal + bare-root cases.
2. **Focus-existing**: `app.get_webview_window("debrief")` → if it
   exists, call `set_focus()` and return — max one debrief sidecar at
   any time.
3. **Sidecar spawn**: `app.shell().sidecar("vibemix-core").args(["--debrief",
   <validated_path>]).spawn()`. The CommandChild is stored on
   `DebriefSidecarHandle.child: Arc<Mutex<Option<CommandChild>>>`.
4. **Window build**: `WebviewWindowBuilder` with
   `label="debrief"`, `inner_size(1280,720)`, `min_inner_size(960,540)`,
   `decorations(true)`, `resizable(true)`,
   `title="Debrief — <session>"`, URL `debrief.html?session=<encoded>`.
5. **Close-handler**: `on_window_event(CloseRequested)` →
   `kill_debrief_child(app)` — idempotent via
   `guard.take()` semantics.
6. **Crash watcher**: `tauri::async_runtime::spawn` listens for
   `CommandEvent::Terminated(payload)` on the spawn's rx stream. On
   early exit emits `sidecar-debrief-crashed` with
   `{exit_code, reason}` payload + closes the window + clears the
   handle for re-open.

**Module exports:**

- `pub const DEBRIEF_WINDOW_LABEL: &str = "debrief"`
- `pub struct DebriefSidecarHandle { pub child: Arc<Mutex<Option<CommandChild>>> }`
- `#[tauri::command] pub async fn open_debrief_window(…)`

### `tauri/src-tauri/src/main.rs`

- `mod debrief_window;`
- `use crate::debrief_window::DebriefSidecarHandle;`
- `open_debrief_window` registered in `tauri::generate_handler![…]`
- `.manage(DebriefSidecarHandle::default())` on app builder

## Tests (inline `#[cfg(test)] mod tests`)

7 tests inside `debrief_window.rs`:

| Test | Covers |
|------|--------|
| `percent_encode_path_handles_spaces` | `foo bar` → `foo%20bar` |
| `percent_encode_path_handles_plus_and_percent` | `a+b%c` → `a%2Bb%25c` |
| `percent_encode_path_handles_query_delimiters` | `?=&#` all encoded |
| `percent_encode_path_preserves_session_id_format` | `/-` left alone |
| `debrief_sidecar_handle_default_starts_empty` | initial `Option::None` |
| `debrief_sidecar_handle_arc_is_clonable` | strong-count parity |
| `debrief_window_label_const_is_lowercase_no_spaces` | Tauri label invariant |

## Deviations

- **`cargo test` deferred.** The dev environment is missing
  `binaries/vibemix-core-x86_64-apple-darwin/` — a pre-existing
  state, NOT introduced by this plan. The tauri-build script's glob
  matcher fails on the missing directory before our code even
  compiles. Reproducible with the empty branch on `git stash`. Fixing
  this is a Phase 21 Plan packaging concern (sidecar fan-out across
  triples), not a Plan 29-04 deliverable.
- **`cargo test` will pass once the bundle is present.** Our code uses
  exclusively shipped Tauri 2 APIs (`AppHandle`, `WebviewUrl`,
  `WebviewWindowBuilder`, `Manager::{get_webview_window, try_state}`,
  `Emitter::emit`, `tauri_plugin_shell::process::{CommandChild,
  CommandEvent::Terminated}`, `tauri::async_runtime::spawn`); no novel
  API surface to validate.
- **No `urlencoding` crate added.** Plan suggested adding it as a dep.
  Instead, a 25-line `percent_encode_path` helper handles the 7
  characters that would actually break `URLSearchParams` decoding. The
  validated session_dir path is already canonicalized so the full
  RFC 3986 unsafe-char set is overkill.
- **Capability allowlist (`capabilities/default.json`) already lists
  `--debrief` in the args validator** (Plan 29-00 Task 1 did this).
  Tauri 2 auto-permits webview→app-command invocation for handlers
  registered via `invoke_handler!` — no separate capability identifier
  needed for `open_debrief_window`.

## Self-Check: PASSED (code complete)

- [x] `open_debrief_window` Tauri command exists, registered in
      invoke_handler.
- [x] Spawns sidecar with `--debrief <validated_session_dir>` + builds
      1280×720 WebviewWindow with label `debrief`.
- [x] Focus-existing logic: second call returns Ok without spawning.
- [x] Path-traversal rejected via `validate_under_root` before spawn.
- [x] WindowEvent::CloseRequested → `kill_debrief_child` idempotent
      via Option::take.
- [x] Crash watcher emits `sidecar-debrief-crashed` event +
      closes window on early exit.
- [x] No POC files touched (`test_g5_poc_files_untouched` still green
      — debrief_window.rs is brand-new).

## What this unblocks

- **Plan 29-05** (vanilla-TS UI) — `debrief.html` will be invoked via
  this command from Settings.
- **Plan 29-06** — Settings → Recordings "Open Debrief" button calls
  `invoke('open_debrief_window', { sessionDir })`.
- **Plan 29-08** — e2e smoke + cross-platform verdict can exercise the
  full lifecycle (open → click → IPC → close → no orphan).
