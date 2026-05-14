//! Phase 15 Plan 03 — `reveal_in_os` + `open_input_wav` Tauri commands.
//!
//! Closes ROADMAP success criteria #1 ("can click a row to reveal in
//! Finder/Explorer") and #2 ("open `input.wav` in their default audio app")
//! for the in-drawer recording browser.
//!
//! Design constraints (carried forward from 15-CONTEXT.md `<specifics>` +
//! 15-03-PLAN.md):
//!
//!   * Shell-out lives on the Tauri Rust parent — NOT the Python sidecar
//!     (sidecars don't shell out per CONTEXT decision).
//!   * macOS uses `open -R <path>` for Finder reveal; Windows uses
//!     `explorer /select,<path>`. Linux is OUT OF SCOPE for vibemix v1
//!     (CLAUDE.md §Constraints — Platforms: macOS + Windows).
//!   * `open_input_wav` uses `tauri-plugin-shell` `open()` which delegates
//!     to the OS-default handler for the file (audio app).
//!   * The path-traversal gate (`validate_under_root`) canonicalizes both
//!     root + candidate so symlinks pointing outside the recordings root
//!     are rejected (canonicalize follows the link before the prefix
//!     check). Threat T-15-03-01 / T-15-03-02 / T-15-03-04 in
//!     15-03-PLAN.md `<threat_model>`.
//!
//! Recordings root resolution (deviation from 15-03-PLAN Step 1 — Rule 3
//! blocking-fix): Python sidecar writes to
//!   * macOS:   `~/Library/Application Support/vibemix/recordings/`
//!   * Windows: `%APPDATA%/vibemix/recordings/`
//!   * Linux:   `$XDG_CONFIG_HOME/vibemix/recordings/` or `~/.config/vibemix/recordings/`
//!
//! Tauri's `app.path().app_data_dir()` would give `~/Library/Application
//! Support/world.bravoh.vibemix/` (bundle-id-suffixed) on macOS — which
//! does NOT match the Python sidecar's literal `vibemix` directory name.
//! We mirror `src/vibemix/runtime/config_store.py:_app_data_dir` exactly
//! so the canonicalize() prefix check resolves against the same disk
//! location the sidecar wrote.
//!
//! Tauri 2.x deprecation note: `app.shell().open(...)` is deprecated.
//! `open_input_wav` migrated to a direct `std::process::Command` shell-out
//! matching the `reveal_in_os` pattern above — same OS handler delegation
//! (`open` on macOS, `cmd /C start` on Windows), zero plugin dependency,
//! deprecation warning gone.

use std::path::{Path, PathBuf};
use std::process::Command;

use tauri::AppHandle;

/// Resolve the OS-aware recordings root that the Python sidecar writes to.
///
/// This MUST mirror `src/vibemix/runtime/config_store.py::_app_data_dir`
/// exactly — otherwise reveal/open commands canonicalize to a different
/// directory than the one the sidecar wrote sessions under, and every
/// reveal call returns Err("target canon: No such file or directory").
pub(crate) fn resolve_recordings_root() -> Result<PathBuf, String> {
    let app_data = app_data_dir_matching_sidecar()?;
    Ok(app_data.join("recordings"))
}

/// macOS: `$HOME/Library/Application Support/vibemix`.
/// Windows: `%APPDATA%/vibemix` (falls back to `$USERPROFILE/AppData/Roaming/vibemix`).
/// Other (CI/Linux): `$XDG_CONFIG_HOME/vibemix` or `$HOME/.config/vibemix`.
fn app_data_dir_matching_sidecar() -> Result<PathBuf, String> {
    #[cfg(target_os = "macos")]
    {
        let home = std::env::var("HOME").map_err(|_| "HOME not set".to_string())?;
        Ok(PathBuf::from(home)
            .join("Library")
            .join("Application Support")
            .join("vibemix"))
    }
    #[cfg(target_os = "windows")]
    {
        if let Ok(appdata) = std::env::var("APPDATA") {
            return Ok(PathBuf::from(appdata).join("vibemix"));
        }
        let userprofile = std::env::var("USERPROFILE")
            .map_err(|_| "USERPROFILE not set".to_string())?;
        Ok(PathBuf::from(userprofile)
            .join("AppData")
            .join("Roaming")
            .join("vibemix"))
    }
    #[cfg(not(any(target_os = "macos", target_os = "windows")))]
    {
        if let Ok(xdg) = std::env::var("XDG_CONFIG_HOME") {
            return Ok(PathBuf::from(xdg).join("vibemix"));
        }
        let home = std::env::var("HOME").map_err(|_| "HOME not set".to_string())?;
        Ok(PathBuf::from(home).join(".config").join("vibemix"))
    }
}

/// Path-traversal gate for the two recording shell-out commands.
///
/// Canonicalizes BOTH `root` and `candidate` (canonicalize follows symlinks
/// + resolves `..`), then asserts the canonicalized candidate starts with
/// the canonicalized root AND is not equal to the root itself (rejecting
/// the bare-root case the user could pass via `session_dir = ""` or
/// `session_dir = "."`).
///
/// Returns the canonical candidate on success; an opaque
/// `"path_traversal_rejected"` string on rejection so the UI does not
/// receive a leaky error message that hints at the disk layout.
pub(crate) fn validate_under_root(candidate: &Path, root: &Path) -> Result<PathBuf, String> {
    let canon_root = root
        .canonicalize()
        .map_err(|e| format!("root canon: {e}"))?;
    let canon_target = candidate
        .canonicalize()
        .map_err(|e| format!("target canon: {e}"))?;
    if !canon_target.starts_with(&canon_root) {
        return Err("path_traversal_rejected".into());
    }
    if canon_target == canon_root {
        return Err("path_traversal_rejected".into());
    }
    Ok(canon_target)
}

/// Reveal a session directory in macOS Finder / Windows Explorer.
///
/// `session_dir` is the BASENAME of the session directory (e.g.
/// `"20260513-210410"`), as emitted by `RecordingsIndex._read_session_summary`
/// in the Python sidecar. The Rust command joins it under the recordings
/// root and rejects any `..`-traversal or symlink-escape via
/// `validate_under_root`.
#[tauri::command]
pub async fn reveal_in_os(_app: AppHandle, session_dir: String) -> Result<(), String> {
    let root = resolve_recordings_root()?;
    let candidate = root.join(&session_dir);
    let safe = validate_under_root(&candidate, &root)?;
    let safe_str = safe.to_str().ok_or_else(|| "path utf8".to_string())?;

    #[cfg(target_os = "macos")]
    {
        Command::new("open")
            .args(["-R", safe_str])
            .status()
            .map_err(|e| format!("open: {e}"))?;
    }
    #[cfg(target_os = "windows")]
    {
        // `explorer /select,<path>` requires the comma to be glued to the
        // flag — passing them as separate args breaks the selection. Tested
        // pattern shipped on Phase 11 Wave 2 explorer-style invocations.
        Command::new("explorer")
            .arg(format!("/select,{}", safe_str))
            .status()
            .map_err(|e| format!("explorer: {e}"))?;
    }
    #[cfg(not(any(target_os = "macos", target_os = "windows")))]
    {
        // Linux is OUT OF SCOPE per CLAUDE.md §Constraints. Fail loud so the
        // capability is never silently accepted on an unsupported platform.
        let _ = safe_str;
        return Err("unsupported platform".into());
    }
    Ok(())
}

/// Open `<recordings_root>/<session_dir>/input.wav` in the OS default audio app.
///
/// Direct shell-out to the OS handler — `open <path>` on macOS delegates to
/// LaunchServices (same surface `tauri-plugin-shell::open()` wrapped, but
/// without the deprecated plugin layer); `cmd /C start "" <path>` on Windows
/// delegates to ShellExecute. The path is validated against the recordings
/// root before the shell-out so a crafted `session_dir` cannot escape to
/// e.g. `/etc/passwd` (T-15-03-01 / T-15-03-04 in 15-03-PLAN).
///
/// AppHandle is retained in the signature for forward-compat with future
/// telemetry; the function does not currently consult it.
#[tauri::command]
pub async fn open_input_wav(_app: AppHandle, session_dir: String) -> Result<(), String> {
    let root = resolve_recordings_root()?;
    let candidate = root.join(&session_dir).join("input.wav");
    let safe = validate_under_root(&candidate, &root)?;
    let safe_str = safe.to_string_lossy().to_string();
    #[cfg(target_os = "macos")]
    {
        Command::new("open")
            .arg(&safe_str)
            .status()
            .map_err(|e| format!("open: {e}"))?;
    }
    #[cfg(target_os = "windows")]
    {
        // `start` is a cmd builtin — invoke via `cmd /C`. The empty quoted
        // string is the window title slot; without it the first quoted arg
        // is consumed as the title and the file path is ignored.
        Command::new("cmd")
            .args(["/C", "start", "", &safe_str])
            .status()
            .map_err(|e| format!("cmd start: {e}"))?;
    }
    #[cfg(not(any(target_os = "macos", target_os = "windows")))]
    {
        let _ = safe_str;
        return Err("unsupported platform".into());
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// Unit tests — pure-function path-validation gate.
//
// End-to-end Tauri command tests (which require an `AppHandle`) are out
// of scope per 15-03-PLAN Step 4 ("integration territory for Phase 16 /
// manual ear-test"). The four cases below exercise every branch in
// `validate_under_root` — the load-bearing security boundary.
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::TempDir;

    /// Test 1: canonical-path success. Given a real subdir under the root,
    /// returns Ok(canonical_path) starting with the canonicalized root.
    #[test]
    fn validates_path_under_root_returns_canonical_path() {
        let tmp = TempDir::new().expect("tmpdir");
        let root = tmp.path();
        let sub = root.join("session-1");
        fs::create_dir(&sub).expect("mkdir");

        let result = validate_under_root(&sub, root).expect("should accept");
        // Canonical root may differ from `root` on macOS (e.g. /var → /private/var),
        // so compare canonicalize-vs-canonicalize, not raw vs canonical.
        let canon_root = root.canonicalize().expect("root canon");
        assert!(
            result.starts_with(&canon_root),
            "expected {result:?} to start with {canon_root:?}",
        );
        assert_ne!(result, canon_root, "subdir must not equal root");
    }

    /// Test 2: traversal rejection via `..`. A session_dir of `../etc`
    /// canonicalizes to a path OUTSIDE the root and must be rejected.
    #[test]
    fn rejects_traversal_via_dotdot() {
        let tmp = TempDir::new().expect("tmpdir");
        let root = tmp.path().join("recordings");
        fs::create_dir(&root).expect("mkdir root");
        // Sibling dir OUTSIDE the root that the candidate resolves to.
        let sibling = tmp.path().join("etc");
        fs::create_dir(&sibling).expect("mkdir sibling");

        // candidate = recordings/../etc → canonicalizes to <tmp>/etc, NOT
        // under <tmp>/recordings.
        let candidate = root.join("..").join("etc");
        let result = validate_under_root(&candidate, &root);
        assert_eq!(
            result.unwrap_err(),
            "path_traversal_rejected",
            "../etc must be rejected",
        );
    }

    /// Test 3: bare-root rejection. session_dir of "" or "." would resolve
    /// to the recordings root itself — opening Finder on the parent dir
    /// rather than a session folder is incorrect UX, AND collapses the
    /// "you can only operate on a session row" invariant.
    #[test]
    fn rejects_root_itself() {
        let tmp = TempDir::new().expect("tmpdir");
        let root = tmp.path().join("recordings");
        fs::create_dir(&root).expect("mkdir root");

        // candidate == root itself.
        let result = validate_under_root(&root, &root);
        assert_eq!(
            result.unwrap_err(),
            "path_traversal_rejected",
            "root itself must be rejected",
        );
    }

    /// Test 4: symlink escape. A symlink INSIDE the root pointing OUTSIDE
    /// the root must be rejected. canonicalize() follows symlinks, so the
    /// resolved path lands outside the canonical root prefix.
    #[cfg(unix)]
    #[test]
    fn rejects_symlink_escape() {
        use std::os::unix::fs::symlink;

        let tmp = TempDir::new().expect("tmpdir");
        let root = tmp.path().join("recordings");
        fs::create_dir(&root).expect("mkdir root");
        let outside = tmp.path().join("outside");
        fs::create_dir(&outside).expect("mkdir outside");

        // recordings/escape -> ../outside  (symlink inside root pointing out)
        let link = root.join("escape");
        symlink(&outside, &link).expect("symlink create");

        let result = validate_under_root(&link, &root);
        assert_eq!(
            result.unwrap_err(),
            "path_traversal_rejected",
            "symlink-escape must be rejected after canonicalize follows the link",
        );
    }

    /// Test 5 (sanity): missing candidate surfaces a `target canon: ...`
    /// error rather than silently passing the validation. Defends
    /// T-15-03-05 (DoS via malformed session_dir → no panic, just Err).
    #[test]
    fn missing_candidate_returns_target_canon_error() {
        let tmp = TempDir::new().expect("tmpdir");
        let root = tmp.path().join("recordings");
        fs::create_dir(&root).expect("mkdir root");

        let candidate = root.join("nonexistent-session");
        let result = validate_under_root(&candidate, &root);
        let err = result.expect_err("missing candidate should error");
        assert!(
            err.starts_with("target canon:"),
            "expected target canon error, got: {err}",
        );
    }
}
