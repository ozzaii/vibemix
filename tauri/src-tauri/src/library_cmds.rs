//! Library / vibe-engine BRIDGE — Tauri Rust ⇄ `vibemix library` Python CLI.
//!
//! This module is the desktop UI's only door into the library/vibe-search
//! backend. Each `#[tauri::command]` spawns the EXISTING `vibemix library`
//! CLI as a one-shot subprocess, parses its stdout JSON, and maps it into a
//! stable UI-facing shape. No backend logic is reimplemented here — the CLI
//! is the contract, this file is the transport.
//!
//! Binary resolution mirrors `sidecar.rs` exactly (the single source of truth
//! for "where does the Python live"):
//!
//!   * dev (`VIBEMIX_DEV_SIDECAR=1`, or no bundled binary): run repo source
//!     via the `resolve_sidecar_invocation` decision — `uv run python -m
//!     vibemix …` (or a `VIBEMIX_DEV_PYTHON` override) with cwd = repo root
//!     so the Python-side `_load_env_robust()` picks up the repo `.env`.
//!   * packaged: the bundled PyInstaller `vibemix-core` binary resolved via
//!     `resource_dir()`, cwd pinned to its parent so the bundled/.app-adjacent
//!     `.env` loads.
//!
//! In BOTH arms we relay `GEMINI_API_KEY` / `OPENROUTER_API_KEY` from the
//! parent env when present (identical to the sidecar watchdog) — the library
//! search/similar/embed paths boot a DIRECT genai client from GEMINI_API_KEY
//! (loaded from `.env` by the Python side, but the env relay wins when a key
//! is exported in the launching shell). SECURITY: env relay only — no key is
//! ever embedded (CLAUDE.md hard rule; the distribution answer is the Bravoh
//! proxy via VIBEMIX_PROXY_JWT, which needs no key).
//!
//! ## CLI contract this bridge maps (verified against src/vibemix/__main__.py
//!    + library/{search,similar,folder_ingest,budget}.py @ HEAD ac732e3):
//!
//!   * `library search <q> --k N --json`
//!       stdout → `{ "query", "cache_hit": bool, "results": [
//!                    { "track_id","title","artist","bpm","confidence","snippet" } ] }`
//!   * `library similar <id> --k N`
//!       stdout → `{ "track_id", "results": [
//!                    { "track_id","similarity","title","artist","bpm" } ] }`
//!   * `library embed-folder <path> --strategy mean_excerpt|cue_anchored`
//!       progress (stdout, NO --json) → `[<n>/<total>] ok|skip|err <file>  ~€<cost>`
//!       final (stdout)              → `embed-folder done: embedded=… skipped_cached=… failed=… total=…  ~€…`
//!       (with --json the per-track lines are suppressed + only an IngestReport
//!        JSON is printed; we run WITHOUT --json so we can stream progress.)
//!   * `library budget --json`  (OFFLINE — pure projection + in-proc telemetry,
//!       no Gemini network call) → `{ "projection": {…}, "telemetry": {…}, "dau" }`
//!
//! The UI never sees the raw CLI shape — `map_search_results` normalizes both
//! search + similar into `{ track_id, title, score, meta }` so the frontend
//! wires one shape. `centered` + `corpus_size` are read off the top-level CLI
//! JSON WHEN PRESENT (the concurrent mean-centering work adds them) and default
//! to `false` / corpus size when absent — forward-compatible by construction.

use serde_json::{json, Value};
use tauri::{AppHandle, Emitter, Manager, WebviewUrl, WebviewWindowBuilder};
use tauri_plugin_shell::process::CommandEvent;
use tauri_plugin_shell::ShellExt;

/// Window label for the vibe-engine / library window. Lowercase, no spaces
/// (tauri-runtime-wry restriction; mirrors `debrief_window::DEBRIEF_WINDOW_LABEL`).
pub const LIBRARY_WINDOW_LABEL: &str = "library";

// Window geometry — CDJ-dark second window, sized per the task (~1180×760).
const LIBRARY_WIDTH: f64 = 1180.0;
const LIBRARY_HEIGHT: f64 = 760.0;
const LIBRARY_MIN_WIDTH: f64 = 920.0;
const LIBRARY_MIN_HEIGHT: f64 = 600.0;

use crate::sidecar::{
    resolve_sidecar_invocation_for_library, FORWARDED_ENV_KEYS,
};

/// Build a `tauri_plugin_shell::process::Command` that runs `vibemix <args…>`
/// using the SAME dev-vs-bundled resolution + env relay as the sidecar
/// watchdog. The caller appends the library subcommand args.
///
/// Returns the configured Command ready to `.spawn()`.
fn build_library_command(
    app: &AppHandle,
    library_args: &[&str],
) -> Result<tauri_plugin_shell::process::Command, String> {
    let invocation = resolve_sidecar_invocation_for_library(app)?;

    let mut cmd = match invocation {
        // Dev: `uv run python -m vibemix` (or override) + cwd = repo root.
        crate::sidecar::SidecarInvocation::DevSource { program, args, cwd } => {
            let mut c = app.shell().command(&program).current_dir(&cwd);
            // args = ["run","python","-m","vibemix"] (or ["-m","vibemix"]).
            // The library subcommand follows.
            for a in &args {
                c = c.args([a]);
            }
            c
        }
        // Packaged: the bundled vibemix-core binary; cwd = its parent so the
        // bundled .env loads (matches sidecar.rs Bundled arm).
        crate::sidecar::SidecarInvocation::Bundled(bin) => {
            let mut c = app.shell().command(&bin);
            if let Some(parent) = bin.parent() {
                c = c.current_dir(parent);
            }
            c
        }
    };

    // Append the library subcommand args.
    for a in library_args {
        cmd = cmd.args([*a]);
    }

    // Env relay — GEMINI_API_KEY / OPENROUTER_API_KEY from the parent env when
    // present and non-empty (no embedded key; CLAUDE.md hard rule).
    for key in FORWARDED_ENV_KEYS {
        if let Ok(val) = std::env::var(key) {
            if !val.is_empty() {
                cmd = cmd.env(key, val);
            }
        }
    }

    Ok(cmd)
}

/// Run a library subcommand to completion, returning (stdout, stderr, code).
///
/// Used by the one-shot JSON commands (search / similar / stats). The
/// streaming `embed-folder` command does NOT use this — it consumes the
/// CommandEvent stream live to emit progress events.
async fn run_library_to_completion(
    app: &AppHandle,
    library_args: &[&str],
) -> Result<(String, String, i32), String> {
    let cmd = build_library_command(app, library_args)?;
    let (mut rx, _child) = cmd
        .spawn()
        .map_err(|e| format!("library spawn failed: {e}"))?;

    let mut stdout = String::new();
    let mut stderr = String::new();
    let mut code: i32 = -1;

    while let Some(event) = rx.recv().await {
        match event {
            CommandEvent::Stdout(b) => {
                stdout.push_str(&String::from_utf8_lossy(&b));
            }
            CommandEvent::Stderr(b) => {
                stderr.push_str(&String::from_utf8_lossy(&b));
            }
            CommandEvent::Terminated(payload) => {
                code = payload.code.unwrap_or(-1);
            }
            _ => {}
        }
    }

    Ok((stdout, stderr, code))
}

/// Parse the stdout of a one-shot library command as JSON, surfacing a
/// useful error (preferring the CLI's own stderr JSON `error` field) on
/// failure. The CLI prints a JSON `{ "error": …, "results": [] }` to stderr
/// on the "no client" / "no library cache" paths and exits 1.
fn parse_cli_json(
    stdout: &str,
    stderr: &str,
    code: i32,
) -> Result<Value, String> {
    if code != 0 {
        // The CLI's failure paths emit a JSON error object to stderr; surface
        // its `error` string when parseable, else the raw stderr tail.
        if let Ok(v) = serde_json::from_str::<Value>(stderr.trim()) {
            if let Some(msg) = v.get("error").and_then(|e| e.as_str()) {
                return Err(msg.to_string());
            }
        }
        let tail = stderr.trim().lines().last().unwrap_or("").to_string();
        return Err(format!("library CLI exited {code}: {tail}"));
    }
    serde_json::from_str::<Value>(stdout.trim())
        .map_err(|e| format!("library CLI returned non-JSON stdout: {e}"))
}

/// Map a raw search/similar CLI payload into the UI-facing response shape:
///
///   `{ "results": [ { "track_id","title","score","meta" } ],
///      "centered": bool, "corpus_size": n }`
///
/// `score` is read from `confidence` (search) OR `similarity` (similar) OR a
/// literal `score` (forward-compat) — whichever the result carries. Every
/// other per-result field collapses into `meta` so the frontend has the full
/// record (artist, bpm, snippet, …) without a second contract.
///
/// `centered` + `corpus_size` are read off the TOP-LEVEL CLI JSON when present
/// (the concurrent mean-centering work adds these) and default to `false` /
/// the result count when absent.
fn map_search_results(raw: &Value) -> Value {
    let empty: Vec<Value> = Vec::new();
    let raw_results = raw
        .get("results")
        .and_then(|r| r.as_array())
        .unwrap_or(&empty);

    let mapped: Vec<Value> = raw_results
        .iter()
        .map(|r| {
            let track_id = r
                .get("track_id")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string();
            let title = r
                .get("title")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string();
            // score: confidence (search) | similarity (similar) | score.
            let score = r
                .get("confidence")
                .or_else(|| r.get("similarity"))
                .or_else(|| r.get("score"))
                .and_then(|v| v.as_f64())
                .unwrap_or(0.0);
            // meta: a SHORT caption STRING for the row's mono sub-line. The
            // UI types `meta` as a string and renders it directly, so we must
            // not hand it the raw record object (that stringifies to
            // "[object Object]"). Prefer the CLI's `snippet`; fall back to the
            // track_id when a result carries no snippet.
            let meta = r
                .get("snippet")
                .and_then(|v| v.as_str())
                .filter(|s| !s.is_empty())
                .unwrap_or(&track_id)
                .to_string();
            json!({
                "track_id": track_id,
                "title": title,
                "score": score,
                "meta": meta,
            })
        })
        .collect();

    // `centered` + `corpus_size` — read top-level when the (concurrent)
    // mean-centering work surfaces them; sane defaults otherwise.
    let centered = raw
        .get("centered")
        .and_then(|v| v.as_bool())
        .unwrap_or(false);
    let corpus_size = raw
        .get("corpus_size")
        .and_then(|v| v.as_u64())
        .unwrap_or(mapped.len() as u64);

    json!({
        "results": mapped,
        "centered": centered,
        "corpus_size": corpus_size,
    })
}

/// `library_search` — natural-language vibe search against the indexed library.
///
/// Runs `library search <query> --k <k> --json`, returns the normalized
/// `{ results:[{track_id,title,score,meta}], centered, corpus_size }` shape.
#[tauri::command]
pub async fn library_search(
    app: AppHandle,
    query: String,
    k: u32,
) -> Result<Value, String> {
    let k_str = k.to_string();
    let (stdout, stderr, code) = run_library_to_completion(
        &app,
        &["library", "search", &query, "--k", &k_str, "--json"],
    )
    .await?;
    let raw = parse_cli_json(&stdout, &stderr, code)?;
    Ok(map_search_results(&raw))
}

/// `library_similar` — USER-ASKED similar-track lookup against a seed.
///
/// `seed` is a track_id; if it is an external file path the CLI handles the
/// external-seed path itself. Runs `library similar <seed> --k <k> --json`
/// (the CLI's `--json` defaults on for similar, but we pass it explicitly so
/// the contract is unambiguous if the default ever changes), returns the same
/// normalized shape as `library_search`.
#[tauri::command]
pub async fn library_similar(
    app: AppHandle,
    seed: String,
    k: u32,
) -> Result<Value, String> {
    let k_str = k.to_string();
    let (stdout, stderr, code) = run_library_to_completion(
        &app,
        &["library", "similar", &seed, "--k", &k_str],
    )
    .await?;
    let raw = parse_cli_json(&stdout, &stderr, code)?;
    Ok(map_search_results(&raw))
}

/// `library_stats` — lightweight engine status for the UI header.
///
/// Returns `{ indexed:n, backend:"sqlite-vec", spent_eur:f, failed:n }`.
///
/// SOURCE (documented per the task): there is NO `library stats --json`
/// subcommand in the Python CLI at HEAD. The cheapest CLI-only signal that
/// makes NO Gemini network call is `library budget --json` — it is fully
/// offline (pure projection math + in-process `BudgetTelemetry`; no genai /
/// httpx import). We read `telemetry.current_cost_estimate_eur` for
/// `spent_eur`.
///
/// `indexed` + `failed` have no zero-network CLI source today (the store
/// row-count lives behind the Python `LibraryStore.row_count()` with no CLI
/// surface, and a probe `search` would cost a Gemini embed). They are reported
/// as `0` with `backend` hard-set to the canonical `"sqlite-vec"` value.
/// DEFERRED: a real `indexed`/`failed` count needs a tiny `library stats
/// --json` subcommand on the Python side (owned by the Python agent) — wiring
/// it here is then a one-line args change.
#[tauri::command]
pub async fn library_stats(app: AppHandle) -> Result<Value, String> {
    let (stdout, stderr, code) =
        run_library_to_completion(&app, &["library", "budget", "--json"]).await?;

    // budget is offline + always exits 0; tolerate parse hiccups gracefully so
    // the UI header never hard-fails on a stats glitch.
    let spent_eur = match parse_cli_json(&stdout, &stderr, code) {
        Ok(v) => v
            .get("telemetry")
            .and_then(|t| t.get("current_cost_estimate_eur"))
            .and_then(|c| c.as_f64())
            .unwrap_or(0.0),
        Err(_) => 0.0,
    };

    Ok(json!({
        "indexed": 0,
        "backend": "sqlite-vec",
        "spent_eur": spent_eur,
        "failed": 0,
    }))
}

/// `open_library_window` — open the second app window hosting the vibe engine.
///
/// Mirrors `debrief_window::open_debrief_window`'s window lifecycle (minus the
/// per-window sidecar — the library bridge spawns one-shot CLI subprocesses on
/// demand, so this window needs no dedicated long-lived child process):
///
///   1. Focus-existing — at most one `library` window; a second call focuses
///      the open one instead of spawning a duplicate.
///   2. Build a CDJ-dark `WebviewWindow` (label `library`) loading
///      `library.html`, sized ~1180×760, decorated + resizable.
///
/// The window's frontend (`/src/library/index.ts`, owned by the frontend
/// agent) calls the `library_*` commands above + listens for the
/// `library://embed-*` events.
#[tauri::command]
pub async fn open_library_window(app: AppHandle) -> Result<(), String> {
    // Focus-existing — single library window at a time.
    if let Some(existing) = app.get_webview_window(LIBRARY_WINDOW_LABEL) {
        let _ = existing.set_focus();
        return Ok(());
    }

    let window = WebviewWindowBuilder::new(
        &app,
        LIBRARY_WINDOW_LABEL,
        WebviewUrl::App("library.html".into()),
    )
    .title("vibemix · vibe engine")
    .inner_size(LIBRARY_WIDTH, LIBRARY_HEIGHT)
    .min_inner_size(LIBRARY_MIN_WIDTH, LIBRARY_MIN_HEIGHT)
    .resizable(true)
    .decorations(true)
    .build()
    .map_err(|e| format!("library window build: {e}"))?;

    let _ = window;
    Ok(())
}

/// Parsed shape of a single `embed-folder` progress line.
#[derive(Debug, PartialEq)]
struct EmbedProgress {
    n: u64,
    total: u64,
    status: String, // "ok" | "skip" | "err"
    filename: String,
    cost_eur: f64,
}

/// Parse a per-track progress line of the form
///   `[<n>/<total>] <ok|skip|err> <filename>  ~€<cost>`
/// (emitted by `folder_ingest._emit_progress`). Returns None for any line
/// that does not match (banners, blank lines, the final summary).
fn parse_embed_progress_line(line: &str) -> Option<EmbedProgress> {
    let line = line.trim();
    if !line.starts_with('[') {
        return None;
    }
    let close = line.find(']')?;
    let counts = &line[1..close]; // "n/total"
    let slash = counts.find('/')?;
    let n: u64 = counts[..slash].trim().parse().ok()?;
    let total: u64 = counts[slash + 1..].trim().parse().ok()?;

    let rest = line[close + 1..].trim();
    // rest = "<status> <filename...>  ~€<cost>"
    let sp = rest.find(' ')?;
    let status = rest[..sp].trim().to_string();
    if status != "ok" && status != "skip" && status != "err" {
        return None;
    }
    let after_status = rest[sp + 1..].trim();

    // Split off the trailing cost token "~€<cost>". The filename can contain
    // spaces, so find the LAST "~€" occurrence and treat everything before it
    // as the filename.
    let (filename, cost_eur) = match after_status.rfind("~€") {
        Some(idx) => {
            let fname = after_status[..idx].trim().to_string();
            let cost_str = after_status[idx + "~€".len()..].trim();
            let cost = cost_str.parse::<f64>().unwrap_or(0.0);
            (fname, cost)
        }
        None => (after_status.to_string(), 0.0),
    };

    Some(EmbedProgress {
        n,
        total,
        status,
        filename,
        cost_eur,
    })
}

/// Parsed shape of the final `embed-folder done:` summary line.
#[derive(Debug, PartialEq)]
struct EmbedDone {
    embedded: u64,
    skipped: u64,
    failed: u64,
    total: u64,
    cost_eur: f64,
}

/// Parse the final summary line:
///   `embed-folder done: embedded=N skipped_cached=N failed=N total=N  ~€C`
fn parse_embed_done_line(line: &str) -> Option<EmbedDone> {
    let line = line.trim();
    if !line.starts_with("embed-folder done:") {
        return None;
    }
    let field = |key: &str| -> u64 {
        // find "key=" then read the integer run.
        if let Some(i) = line.find(&format!("{key}=")) {
            let start = i + key.len() + 1;
            let num: String = line[start..]
                .chars()
                .take_while(|c| c.is_ascii_digit())
                .collect();
            num.parse().unwrap_or(0)
        } else {
            0
        }
    };
    let cost_eur = match line.rfind("~€") {
        Some(idx) => line[idx + "~€".len()..]
            .trim()
            .split_whitespace()
            .next()
            .and_then(|s| s.parse::<f64>().ok())
            .unwrap_or(0.0),
        None => 0.0,
    };
    Some(EmbedDone {
        embedded: field("embedded"),
        skipped: field("skipped_cached"),
        failed: field("failed"),
        total: field("total"),
        cost_eur,
    })
}

/// `library_embed_folder` — ingest a raw audio folder, streaming progress.
///
/// Spawns `library embed-folder <path> --strategy <strategy>` WITHOUT `--json`
/// (so the per-track human progress lines are emitted on stdout — `--json`
/// would suppress them and only print a final report). For each parsed
/// progress line we emit:
///
///   `library://embed-progress` → `{ n, total, status, filename, cost_eur }`
///
/// and on the final summary line:
///
///   `library://embed-done` → `{ embedded, skipped, failed, total, cost_eur }`
///
/// `strategy` is validated against the CLI's allowed choices
/// (`mean_excerpt` | `cue_anchored`) before spawn — an out-of-band value is
/// rejected here rather than surfacing the CLI's argparse error.
///
/// Returns once the child terminates. A non-zero exit is surfaced as Err AND
/// the final `library://embed-done` (if seen) is still emitted.
#[tauri::command]
pub async fn library_embed_folder(
    app: AppHandle,
    path: String,
    strategy: String,
) -> Result<(), String> {
    // Validate the strategy against the CLI's choices before spawn.
    if strategy != "mean_excerpt" && strategy != "cue_anchored" {
        return Err(format!(
            "invalid strategy {strategy:?} (expected mean_excerpt | cue_anchored)"
        ));
    }

    let cmd = build_library_command(
        &app,
        &["library", "embed-folder", &path, "--strategy", &strategy],
    )?;
    let (mut rx, _child) = cmd
        .spawn()
        .map_err(|e| format!("embed-folder spawn failed: {e}"))?;

    let mut code: i32 = -1;
    // The CLI emits stdout line-buffered (via _enable_line_buffering); tauri's
    // CommandEvent::Stdout may still chunk mid-line, so we buffer + split on
    // newlines to keep progress parsing robust.
    let mut line_buf = String::new();

    while let Some(event) = rx.recv().await {
        match event {
            CommandEvent::Stdout(b) => {
                line_buf.push_str(&String::from_utf8_lossy(&b));
                while let Some(nl) = line_buf.find('\n') {
                    let line: String = line_buf.drain(..=nl).collect();
                    dispatch_embed_line(&app, line.trim_end());
                }
            }
            CommandEvent::Stderr(b) => {
                // embed-folder prints diagnostics (client=direct, strategy, …)
                // + [FATAL] errors to stderr — forward to the parent log.
                let s = String::from_utf8_lossy(&b);
                tracing::info!("[library embed-folder] {}", s.trim_end());
            }
            CommandEvent::Terminated(payload) => {
                code = payload.code.unwrap_or(-1);
            }
            _ => {}
        }
    }
    // Flush any trailing partial line (defensive — the summary line ends with
    // a newline, but a final chunk without a trailing \n is still handled).
    if !line_buf.trim().is_empty() {
        dispatch_embed_line(&app, line_buf.trim_end());
    }

    if code != 0 {
        return Err(format!("embed-folder exited {code}"));
    }
    Ok(())
}

/// Classify one embed-folder stdout line and emit the matching Tauri event.
fn dispatch_embed_line(app: &AppHandle, line: &str) {
    if let Some(p) = parse_embed_progress_line(line) {
        let _ = app.emit(
            "library://embed-progress",
            json!({
                "n": p.n,
                "total": p.total,
                "status": p.status,
                "filename": p.filename,
                "cost_eur": p.cost_eur,
            }),
        );
    } else if let Some(d) = parse_embed_done_line(line) {
        let _ = app.emit(
            "library://embed-done",
            json!({
                "embedded": d.embedded,
                "skipped": d.skipped,
                "failed": d.failed,
                "total": d.total,
                "cost_eur": d.cost_eur,
            }),
        );
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_ok_progress_line() {
        let p = parse_embed_progress_line("[3/120] ok track.wav  ~€0.0123")
            .expect("should parse");
        assert_eq!(p.n, 3);
        assert_eq!(p.total, 120);
        assert_eq!(p.status, "ok");
        assert_eq!(p.filename, "track.wav");
        assert!((p.cost_eur - 0.0123).abs() < 1e-9);
    }

    #[test]
    fn parses_progress_line_with_spaces_in_filename() {
        let p = parse_embed_progress_line(
            "[12/40] skip My Cool Track (Extended Mix).flac  ~€0.0000",
        )
        .expect("should parse");
        assert_eq!(p.n, 12);
        assert_eq!(p.status, "skip");
        assert_eq!(p.filename, "My Cool Track (Extended Mix).flac");
        assert_eq!(p.cost_eur, 0.0);
    }

    #[test]
    fn parses_err_progress_line() {
        let p = parse_embed_progress_line("[40/40] err broken.mp3  ~€0.0500")
            .expect("should parse");
        assert_eq!(p.status, "err");
        assert_eq!(p.filename, "broken.mp3");
    }

    #[test]
    fn rejects_non_progress_lines() {
        assert!(parse_embed_progress_line("-> embed-folder: strategy=cue_anchored").is_none());
        assert!(parse_embed_progress_line("").is_none());
        assert!(parse_embed_progress_line("random banner text").is_none());
        // Unknown status token is rejected.
        assert!(parse_embed_progress_line("[1/2] wat file.wav  ~€0.0").is_none());
    }

    #[test]
    fn parses_done_summary_line() {
        let d = parse_embed_done_line(
            "embed-folder done: embedded=98 skipped_cached=20 failed=2 total=120  ~€1.2345",
        )
        .expect("should parse");
        assert_eq!(d.embedded, 98);
        assert_eq!(d.skipped, 20);
        assert_eq!(d.failed, 2);
        assert_eq!(d.total, 120);
        assert!((d.cost_eur - 1.2345).abs() < 1e-9);
    }

    #[test]
    fn done_line_not_confused_with_progress_line() {
        assert!(parse_embed_progress_line(
            "embed-folder done: embedded=1 skipped_cached=0 failed=0 total=1  ~€0.01"
        )
        .is_none());
    }

    #[test]
    fn maps_search_results_to_ui_shape() {
        let raw = json!({
            "query": "warm sunset",
            "cache_hit": false,
            "results": [
                { "track_id": "t1", "title": "A", "artist": "X", "bpm": 124.0,
                  "confidence": 0.91, "snippet": "A — X @ 124 BPM" }
            ]
        });
        let mapped = map_search_results(&raw);
        let r = &mapped["results"][0];
        assert_eq!(r["track_id"], "t1");
        assert_eq!(r["title"], "A");
        assert!((r["score"].as_f64().unwrap() - 0.91).abs() < 1e-9);
        // meta is the short caption STRING (the CLI's snippet) — NOT the raw
        // object (which would render "[object Object]" in the UI).
        assert_eq!(r["meta"], "A — X @ 124 BPM");
        // defaults when CLI omits centering metadata.
        assert_eq!(mapped["centered"], false);
        assert_eq!(mapped["corpus_size"], 1);
    }

    #[test]
    fn maps_similar_results_score_from_similarity() {
        let raw = json!({
            "track_id": "seed1",
            "results": [
                { "track_id": "t2", "similarity": 0.77, "title": "B",
                  "artist": "Y", "bpm": 128.0 }
            ]
        });
        let mapped = map_search_results(&raw);
        assert!((mapped["results"][0]["score"].as_f64().unwrap() - 0.77).abs() < 1e-9);
        // No snippet on the similar payload → meta falls back to track_id
        // (still a STRING, never the raw object).
        assert_eq!(mapped["results"][0]["meta"], "t2");
    }

    #[test]
    fn reads_centering_metadata_when_present() {
        // Forward-compat: the concurrent mean-centering work surfaces these.
        let raw = json!({
            "results": [],
            "centered": true,
            "corpus_size": 4096
        });
        let mapped = map_search_results(&raw);
        assert_eq!(mapped["centered"], true);
        assert_eq!(mapped["corpus_size"], 4096);
    }

    #[test]
    fn parse_cli_json_surfaces_stderr_error_on_failure() {
        let stderr = r#"{"error": "No library cache.", "results": []}"#;
        let err = parse_cli_json("", stderr, 1).expect_err("should be Err");
        assert_eq!(err, "No library cache.");
    }
}
