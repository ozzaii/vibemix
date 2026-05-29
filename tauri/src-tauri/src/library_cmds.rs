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
//! In BOTH arms we relay the same runtime mode/auth env as the sidecar watchdog
//! (`VIBEMIX_LLM_MODE`, direct/proxy keys/tokens, and `CODEX_HOME`) when
//! present. Library search/similar/embed is local CLAP ONNX and keyless; the
//! Library/Viber reasoning backend is pinned to local Codex for the desktop
//! product path. SECURITY: env relay only — no key is ever embedded
//! (CLAUDE.md hard rule; distribution should use the Bravoh proxy).
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
const LIBRARY_AGENT_BACKEND: &str = "codex";
const MODEL_PROGRESS_PREFIX: &str = "VIBEMIX_MODEL_PROGRESS ";

use crate::sidecar::{resolve_sidecar_invocation_for_library, FORWARDED_ENV_KEYS};

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

    // Env relay — runtime auth + Codex setup from the parent env when present
    // and non-empty (no embedded key/token; CLAUDE.md hard rule).
    for key in FORWARDED_ENV_KEYS {
        if let Ok(val) = std::env::var(key) {
            if !val.is_empty() {
                cmd = cmd.env(key, val);
            }
        }
    }
    // Product path: keep Library/Viber on local Codex even if an old shell still
    // has VIBEMIX_LIBRARY_AGENT_BACKEND=gemini in its environment.
    cmd = cmd.env("VIBEMIX_LIBRARY_AGENT_BACKEND", LIBRARY_AGENT_BACKEND);

    // Codex backend shell allow. Any `--backend codex` app path runs `codex exec`
    // against an MCP server; an upstream Codex regression broke MCP tool-approval
    // mode, so the wrapper fails closed (`codex_mcp_blocked`) unless
    // VIBEMIX_CODEX_ALLOW_SHELL=1 is set. The desktop app is a trusted local
    // context, so we set it WHEN (and only when) the codex backend is requested.
    // Unused/harmless for every other library subcommand.
    if library_args_request_codex_backend(library_args) {
        cmd = cmd.env("VIBEMIX_CODEX_ALLOW_SHELL", "1");
    }

    Ok(cmd)
}

fn library_args_request_codex_backend(library_args: &[&str]) -> bool {
    library_args
        .windows(2)
        .any(|pair| pair[0] == "--backend" && pair[1] == "codex")
}

/// Viber backend for the desktop app.
///
/// The presentation/product path is local Codex. This intentionally ignores the
/// old `VIBEMIX_LIBRARY_AGENT_BACKEND` override so stale shell env cannot select
/// a legacy backend for Library chat/build/curate.
fn library_agent_backend() -> &'static str {
    LIBRARY_AGENT_BACKEND
}

fn chat_library_args(
    message: &str,
    history_json: Option<&str>,
    live_context_json: Option<&str>,
) -> Vec<String> {
    let backend = library_agent_backend();
    let mut args = vec![
        "library".to_string(),
        "chat".to_string(),
        message.to_string(),
        "--backend".to_string(),
        backend.to_string(),
        "--json".to_string(),
    ];
    if let Some(h) = history_json {
        args.push("--history".to_string());
        args.push(h.to_string());
    }
    if let Some(ctx) = live_context_json {
        let trimmed = ctx.trim();
        if !trimmed.is_empty() && trimmed != "null" {
            args.push("--live-context".to_string());
            args.push(trimmed.to_string());
        }
    }
    args
}

fn model_library_args(install: Option<&str>, force: bool) -> Vec<String> {
    let mut args = vec![
        "library".to_string(),
        "models".to_string(),
        "--json".to_string(),
    ];
    if let Some(target) = install {
        args.push("--install".to_string());
        args.push(target.to_string());
    }
    if force {
        args.push("--force".to_string());
    }
    args
}

fn normalize_model_install_target(raw: Option<String>) -> Result<Option<String>, String> {
    let Some(raw) = raw else {
        return Ok(None);
    };
    let value = raw.trim().to_ascii_lowercase();
    match value.as_str() {
        "" => Ok(None),
        "required" | "clap" | "cue" | "all" => Ok(Some(value)),
        _ => Err(format!(
            "invalid model install target {value:?} (expected required | clap | cue | all)"
        )),
    }
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
    let mut stderr_line_buf = String::new();
    let mut code: i32 = -1;

    while let Some(event) = rx.recv().await {
        match event {
            CommandEvent::Stdout(b) => {
                stdout.push_str(&String::from_utf8_lossy(&b));
            }
            CommandEvent::Stderr(b) => {
                stderr_line_buf.push_str(&String::from_utf8_lossy(&b));
                while let Some(nl) = stderr_line_buf.find('\n') {
                    let line: String = stderr_line_buf.drain(..=nl).collect();
                    if !dispatch_model_progress_line(app, line.trim_end()) {
                        stderr.push_str(&line);
                    }
                }
            }
            CommandEvent::Terminated(payload) => {
                code = payload.code.unwrap_or(-1);
            }
            _ => {}
        }
    }
    if !stderr_line_buf.is_empty() && !dispatch_model_progress_line(app, stderr_line_buf.trim_end())
    {
        stderr.push_str(&stderr_line_buf);
    }

    Ok((stdout, stderr, code))
}

fn parse_model_progress_line(line: &str) -> Option<Value> {
    let raw = line.trim().strip_prefix(MODEL_PROGRESS_PREFIX)?;
    serde_json::from_str::<Value>(raw).ok()
}

/// Parse a live tool-tape line from the Codex MCP path.
///
/// Format (emitted by `codex_curate::_drain_tool_tape` on stderr):
/// `[viber-tool] <name> <ok|err> <summary…>`. Surfaced to the conversation so
/// the user watches each tool fire — search, sequence, create — as it happens.
fn parse_viber_tool_line(line: &str) -> Option<Value> {
    let rest = line.trim().strip_prefix("[viber-tool] ")?;
    let mut parts = rest.splitn(3, ' ');
    let name = parts.next()?.to_string();
    let ok = parts.next().unwrap_or("ok") == "ok";
    let summary = parts.next().unwrap_or("").to_string();
    Some(serde_json::json!({ "tool": name, "ok": ok, "summary": summary }))
}

fn dispatch_model_progress_line(app: &AppHandle, line: &str) -> bool {
    if let Some(payload) = parse_model_progress_line(line) {
        let _ = app.emit("library://model-progress", payload);
        return true;
    }
    if let Some(payload) = parse_viber_tool_line(line) {
        let _ = app.emit("library://viber-tool", payload);
        return true;
    }
    false
}

/// Parse the stdout of a one-shot library command as JSON, surfacing a
/// useful error (preferring the CLI's own stderr JSON `error` field) on
/// failure. The CLI prints a JSON `{ "error": …, "results": [] }` to stderr
/// on the "no client" / "no library cache" paths and exits 1.
fn parse_cli_json(stdout: &str, stderr: &str, code: i32) -> Result<Value, String> {
    if code != 0 {
        // Agent backends can fail in a UI-recoverable way: no Codex CLI,
        // Codex auth required, max_iters/no_playlist, timeout, etc. Those
        // runs still emit a structured payload with `stop_reason` so the
        // Library window can render "No set built (reason)" plus the backend's
        // setup hint instead of collapsing into a generic engine error. Some
        // CLI paths print a human hint after the JSON on stderr, so parse only
        // the first JSON value when looking for this structured terminal.
        for stream in [stdout, stderr] {
            if let Some(v) = parse_first_json_value(stream) {
                if is_agent_terminal_payload(&v) {
                    return Ok(v);
                }
            }
        }
        for stream in [stderr, stdout] {
            if let Some(v) = parse_clarification_terminal(stream) {
                return Ok(v);
            }
        }
        // The CLI's failure paths emit a JSON error object to stderr; surface
        // its `error` string when parseable, else the raw stderr tail.
        if let Some(v) = parse_first_json_value(stderr) {
            if let Some(msg) = v.get("error").and_then(|e| e.as_str()) {
                return Err(msg.to_string());
            }
        }
        let tail = stderr.trim().lines().last().unwrap_or("").to_string();
        return Err(format!("library CLI exited {code}: {tail}"));
    }
    parse_first_json_value(stdout).ok_or_else(|| {
        let detail = serde_json::from_str::<Value>(stdout.trim())
            .err()
            .map(|e| e.to_string())
            .unwrap_or_else(|| "empty stdout".to_string());
        format!("library CLI returned non-JSON stdout: {detail}")
    })
}

fn parse_first_json_value(raw: &str) -> Option<Value> {
    let trimmed = raw.trim_start();
    if trimmed.is_empty() {
        return None;
    }
    serde_json::Deserializer::from_str(trimmed)
        .into_iter::<Value>()
        .next()
        .and_then(Result::ok)
}

fn is_agent_terminal_payload(v: &Value) -> bool {
    v.get("stop_reason")
        .and_then(|reason| reason.as_str())
        .is_some_and(|reason| !reason.is_empty())
}

fn parse_numbered_choice(line: &str) -> Option<String> {
    let (number, choice) = line.split_once('.')?;
    if number.is_empty() || !number.bytes().all(|b| b.is_ascii_digit()) {
        return None;
    }
    let choice = choice.trim();
    if choice.is_empty() {
        None
    } else {
        Some(choice.to_string())
    }
}

fn parse_clarification_terminal(raw: &str) -> Option<Value> {
    const MARKER: &str = "[viber/codex] clarification_needed:";

    let mut lines = raw.lines();
    while let Some(line) = lines.next() {
        let trimmed = line.trim();
        let Some(suffix) = trimmed.strip_prefix(MARKER) else {
            continue;
        };

        let mut question = suffix.trim().to_string();
        let mut choices: Vec<String> = Vec::new();

        for line in lines {
            let trimmed = line.trim();
            if trimmed.is_empty() {
                continue;
            }
            if trimmed.starts_with("Re-run with:") {
                break;
            }
            if let Some(choice) = parse_numbered_choice(trimmed) {
                choices.push(choice);
                continue;
            }
            if question.is_empty() {
                question = trimmed.to_string();
            }
        }

        let rationale = if question.is_empty() {
            "Viber needs one more detail before building the set.".to_string()
        } else {
            question.clone()
        };

        return Some(json!({
            "theme": "",
            "playlist": null,
            "playlist_name": null,
            "track_ids": [],
            "rationale": rationale,
            "iterations": 0,
            "stop_reason": "clarification_needed",
            "seen_track_ids": [],
            "error": rationale,
            "question": question,
            "choices": choices,
        }));
    }

    None
}

fn parse_library_models_json(stdout: &str, stderr: &str, code: i32) -> Result<Value, String> {
    if code != 0 {
        if let Some(v) = parse_first_json_value(stdout) {
            return Ok(v);
        }
    }
    parse_cli_json(stdout, stderr, code)
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
pub async fn library_search(app: AppHandle, query: String, k: u32) -> Result<Value, String> {
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
pub async fn library_similar(app: AppHandle, seed: String, k: u32) -> Result<Value, String> {
    let k_str = k.to_string();
    let (stdout, stderr, code) =
        run_library_to_completion(&app, &["library", "similar", &seed, "--k", &k_str]).await?;
    let raw = parse_cli_json(&stdout, &stderr, code)?;
    Ok(map_search_results(&raw))
}

/// Map a raw `library curate --json` payload into the UI-facing curate shape:
///
///   `{ "name": str, "rationale": str, "stop_reason": str,
///      "tracks": [ { "track_id","title","meta" } ], "count": n }`
///
/// CLI contract (verified against src/vibemix/__main__.py `_cmd_library_curate`
/// + library/codex_curate.py `CodexCurateResult.to_dict`
/// + library/create_playlist.py `PlaylistResult.to_dict`):
///
///   `{ "theme", "playlist": { "name", "track_ids":[str], "m3u_path",
///       "json_path", "dropped_ids":[str] } | null,
///      "rationale", "iterations", "stop_reason", "seen_track_ids":[str] }`
///
/// HONESTY (anti-slop): the in-memory `PlaylistResult` carries only `track_ids`
/// (strings) — NO per-track titles (the rich title/artist/bpm record lives only
/// in the persisted JSON file, which this one-shot bridge does not re-read). So
/// each row's `title` IS the track_id and `meta` is "track <id>". We never
/// fabricate a human title the CLI did not give us. If a future CLI surfaces a
/// title field per track, it is read here when present and the id is the
/// fallback — forward-compatible by construction.
///
/// `name` defaults to the theme when the agent did not name the playlist;
/// `count` is the validated track count.
fn map_curate_result(raw: &Value) -> Value {
    let theme = raw.get("theme").and_then(|v| v.as_str()).unwrap_or("");
    let rationale = raw
        .get("rationale")
        .and_then(|v| v.as_str())
        .filter(|s| !s.is_empty())
        .or_else(|| raw.get("error").and_then(|v| v.as_str()))
        .unwrap_or("")
        .to_string();
    let stop_reason = raw
        .get("stop_reason")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();

    let playlist = raw.get("playlist");
    // `name` — the agent-chosen playlist name. Legacy nested payloads keep it
    // under `playlist.name`; the Codex backend surfaces it top-level as
    // `playlist_name`.
    // Fall back to the theme when neither names the set.
    let name = playlist
        .and_then(|p| p.get("name"))
        .or_else(|| raw.get("playlist_name"))
        .and_then(|v| v.as_str())
        .filter(|s| !s.is_empty())
        .unwrap_or(theme)
        .to_string();

    let empty: Vec<Value> = Vec::new();
    // The playlist may carry future-proof rich track objects OR (today) a flat
    // `track_ids` string list. Handle both: if `tracks` array of objects is
    // present use it; else map `track_ids`.
    let tracks: Vec<Value> = if let Some(arr) = playlist
        .and_then(|p| p.get("tracks"))
        .and_then(|t| t.as_array())
    {
        arr.iter()
            .map(|t| {
                let track_id = t
                    .get("track_id")
                    .and_then(|v| v.as_str())
                    .unwrap_or("")
                    .to_string();
                // title: a real title field WHEN PRESENT, else the id (honest).
                let title = t
                    .get("title")
                    .and_then(|v| v.as_str())
                    .filter(|s| !s.is_empty())
                    .unwrap_or(&track_id)
                    .to_string();
                let meta = t
                    .get("artist")
                    .and_then(|v| v.as_str())
                    .filter(|s| !s.is_empty())
                    .map(|a| a.to_string())
                    .unwrap_or_else(|| format!("track {track_id}"));
                json!({ "track_id": track_id, "title": title, "meta": meta })
            })
            .collect()
    } else {
        // Flat id list. Legacy nested payloads keep it under
        // `playlist.track_ids`; the Codex backend surfaces it top-level as
        // `track_ids`. Try nested, then top-level.
        let ids = playlist
            .and_then(|p| p.get("track_ids"))
            .or_else(|| raw.get("track_ids"))
            .and_then(|t| t.as_array())
            .unwrap_or(&empty);
        ids.iter()
            .map(|v| {
                let track_id = v.as_str().unwrap_or("").to_string();
                // No title in the flat id list → id IS the title (no fabrication).
                json!({
                    "track_id": track_id,
                    "title": track_id,
                    "meta": format!("track {track_id}"),
                })
            })
            .collect()
    };

    let count = tracks.len() as u64;
    // `export_path` — present (a string) when a set-prep run exported the chosen
    // set to Rekordbox XML; `null` for plain curation. Surfaced verbatim so the
    // build-set UI can show the "Exported → <path>" line + import hint. Curate
    // never exports, so this is simply absent/null on the curate path.
    let export_path = raw.get("export_path").cloned().unwrap_or(Value::Null);
    let question = raw.get("question").cloned().unwrap_or(Value::Null);
    let choices = raw
        .get("choices")
        .and_then(|v| v.as_array())
        .map(|items| {
            items
                .iter()
                .filter_map(|item| item.as_str().map(|s| Value::String(s.to_string())))
                .collect::<Vec<Value>>()
        })
        .map(Value::Array)
        .unwrap_or(Value::Null);
    json!({
        "name": name,
        "rationale": rationale,
        "stop_reason": stop_reason,
        "tracks": tracks,
        "count": count,
        "export_path": export_path,
        "question": question,
        "choices": choices,
    })
}

/// `library_curate` — theme → AI-curated playlist (one-shot, NOT interactive).
///
/// Runs `library curate <theme> --backend <selected> --json`. The packaged app
/// defaults to local Codex for the test/demo phase. `map_curate_result` maps
/// either backend shape into the stable UI DTO.
#[tauri::command]
pub async fn library_curate(app: AppHandle, theme: String) -> Result<Value, String> {
    let backend = library_agent_backend();
    let (stdout, stderr, code) = run_library_to_completion(
        &app,
        &["library", "curate", &theme, "--backend", backend, "--json"],
    )
    .await?;
    let raw = parse_cli_json(&stdout, &stderr, code)?;
    Ok(map_curate_result(&raw))
}

/// `library_build_set` — the v8.2 set-prep co-host: a natural-language brief →
/// a discovered + sequenced set, auto-exported to Rekordbox XML.
///
/// Mirrors `library_curate` exactly (one-shot CLI subprocess → JSON → mapped UI
/// shape), running `library build-set <brief> --curve <curve> --export
/// rekordbox --json`. `--export rekordbox` makes the agent write the chosen set
/// to a Rekordbox XML; the resulting `export_path` is surfaced in the mapped
/// shape so the UI can show the "Exported → <path>" line + import hint.
///
/// The Codex wrapper returns the same curate DTO shape for curate/build-set
/// (plus `export_path`), so `map_curate_result` is reused verbatim — it already
/// tolerates `playlist: null`. A set-prep run can terminate via export
/// (`stop_reason == "exported"`) rather than a created playlist, so the build
/// flow leans on `export_path` + the rationale as the headline value; the rows
/// (when present) are the same numbered set the curate path renders.
///
/// `curve` is one of the agent's energy-curve presets
/// (`opener` | `peak_time` | `after_hours` | `festival`) — validated here
/// before spawn so an out-of-band value never reaches the CLI as a confusing
/// argparse error.
///
/// HONESTY (anti-slop): backend errors surface via `parse_cli_json` as an Err —
/// the frontend renders the real error, never fake data.
#[tauri::command]
pub async fn library_build_set(
    app: AppHandle,
    brief: String,
    curve: String,
) -> Result<Value, String> {
    // Validate the curve preset before spawn (matches the CLI's choices).
    const CURVES: [&str; 4] = ["opener", "peak_time", "after_hours", "festival"];
    if !CURVES.contains(&curve.as_str()) {
        return Err(format!(
            "invalid curve {curve:?} (expected opener | peak_time | after_hours | festival)"
        ));
    }
    let backend = library_agent_backend();
    let (stdout, stderr, code) = run_library_to_completion(
        &app,
        &[
            "library",
            "build-set",
            &brief,
            "--curve",
            &curve,
            "--export",
            "rekordbox",
            "--backend",
            backend,
            "--json",
        ],
    )
    .await?;
    let raw = parse_cli_json(&stdout, &stderr, code)?;
    Ok(map_curate_result(&raw))
}

/// `library_chat` — one conversational, tool-using Viber turn.
///
/// Thin bridge over `vibemix library chat <message> --history <json> --json`.
/// The Python CLI owns the agent/tool logic and returns `ChatResult.to_dict()`:
/// `{ reply, tool_trace, playlist, export_path, seen_track_ids, iterations,
/// stop_reason, live_verification? }`. The bridge intentionally does not reshape
/// it so the frontend can consume the same DTO that backend tests pin.
#[tauri::command]
pub async fn library_chat(
    app: AppHandle,
    message: String,
    history: Option<Value>,
    live_context: Option<Value>,
) -> Result<Value, String> {
    let history_json = history
        .as_ref()
        .map(serde_json::to_string)
        .transpose()
        .map_err(|e| format!("invalid chat history: {e}"))?;
    let live_context_json = match live_context.as_ref() {
        Some(value) if !value.is_null() => {
            Some(serde_json::to_string(value).map_err(|e| format!("invalid live context: {e}"))?)
        }
        _ => None,
    };

    // Current test/demo default is local Codex; passing it through here also
    // trips build_library_command's shell-allow gate for the Codex MCP path.
    let args = chat_library_args(
        &message,
        history_json.as_deref(),
        live_context_json.as_deref(),
    );
    let arg_refs: Vec<&str> = args.iter().map(String::as_str).collect();

    let (stdout, stderr, code) = run_library_to_completion(&app, &arg_refs).await?;
    parse_cli_json(&stdout, &stderr, code)
}

/// `library_stats` — lightweight engine status for the UI header.
///
/// Returns `{ indexed:n, backend:"sqlite-vec"|"numpy", embedding_backend,
/// embedding_dim, clap_model_installed, clap_model_path, agent_backend,
/// agent_ready, agent_status, agent_hint, spent_eur:f, failed:n }`.
///
/// Two OFFLINE CLI calls (neither makes a Gemini/network call):
///   * `library stats --json`  → `{ indexed, backend, embedding_backend,
///     embedding_dim, clap_model_*, agent_*, failed }` — the store row-count
///     plus active embedding/model/agent setup status. `failed` has no persisted
///     source yet → `0`.
///   * `library budget --json`  → `telemetry.current_cost_estimate_eur` for
///     `spent_eur` (the running-cost readout; stats does not carry cost).
///
/// Resilience is PARTIAL and the boundary matters: a parse/exit-code hiccup is
/// tolerated — `stats` falls back to `indexed:0 / backend:"sqlite-vec"`, `budget`
/// to `spent_eur:0.0` — so a malformed-JSON glitch never crashes the header. But
/// a sidecar SPAWN failure (binary missing/unlaunchable) on either call still
/// `?`-propagates as `Err`, which surfaces to the UI as a thrown invoke. A spawn
/// failure on the `stats` call short-circuits before `budget` runs, so it is the
/// whole-command failure mode — not a graceful fallback.
#[tauri::command]
pub async fn library_stats(app: AppHandle) -> Result<Value, String> {
    let agent_backend = library_agent_backend();

    // 1) indexed + backend + embedding seam + failed from the offline
    // `stats` subcommand.
    let (s_out, s_err, s_code) =
        run_library_to_completion(&app, &["library", "stats", "--json"]).await?;
    let (
        indexed,
        backend,
        embedding_backend,
        embedding_dim,
        clap_model_installed,
        clap_model_path,
        clap_model_missing,
        agent_ready,
        agent_status,
        agent_hint,
        failed,
    ) = match parse_cli_json(&s_out, &s_err, s_code) {
        Ok(v) => (
            v.get("indexed").and_then(|n| n.as_u64()).unwrap_or(0),
            v.get("backend")
                .and_then(|b| b.as_str())
                .unwrap_or("sqlite-vec")
                .to_string(),
            v.get("embedding_backend")
                .and_then(|b| b.as_str())
                .unwrap_or("clap")
                .to_string(),
            v.get("embedding_dim")
                .and_then(|n| n.as_u64())
                .unwrap_or(512),
            v.get("clap_model_installed")
                .and_then(|b| b.as_bool())
                .unwrap_or(false),
            v.get("clap_model_path")
                .and_then(|p| p.as_str())
                .unwrap_or("")
                .to_string(),
            v.get("clap_model_missing")
                .and_then(|m| m.as_array())
                .map(|arr| {
                    arr.iter()
                        .filter_map(|v| v.as_str().map(str::to_string))
                        .collect::<Vec<String>>()
                })
                .unwrap_or_default(),
            v.get("agent_ready")
                .and_then(|b| b.as_bool())
                .unwrap_or(false),
            v.get("agent_status")
                .and_then(|s| s.as_str())
                .unwrap_or("unknown")
                .to_string(),
            v.get("agent_hint")
                .and_then(|s| s.as_str())
                .unwrap_or("")
                .to_string(),
            v.get("failed").and_then(|n| n.as_u64()).unwrap_or(0),
        ),
        Err(_) => (
            0,
            "sqlite-vec".to_string(),
            "clap".to_string(),
            512,
            false,
            "".to_string(),
            Vec::new(),
            false,
            "unknown".to_string(),
            "".to_string(),
            0,
        ),
    };

    // 2) spent_eur — from the offline `budget` telemetry (stats has no cost).
    let (b_out, b_err, b_code) =
        run_library_to_completion(&app, &["library", "budget", "--json"]).await?;
    let spent_eur = match parse_cli_json(&b_out, &b_err, b_code) {
        Ok(v) => v
            .get("telemetry")
            .and_then(|t| t.get("current_cost_estimate_eur"))
            .and_then(|c| c.as_f64())
            .unwrap_or(0.0),
        Err(_) => 0.0,
    };

    Ok(json!({
        "indexed": indexed,
        "backend": backend,
        "embedding_backend": embedding_backend,
        "embedding_dim": embedding_dim,
        "clap_model_installed": clap_model_installed,
        "clap_model_path": clap_model_path,
        "clap_model_missing": clap_model_missing,
        "agent_backend": agent_backend,
        "agent_ready": agent_ready,
        "agent_status": agent_status,
        "agent_hint": agent_hint,
        "spent_eur": spent_eur,
        "failed": failed,
    }))
}

/// `library_models` — local AI model status/install seam for setup UX.
///
/// Status is offline (`library models --json`). Installing required assets may
/// network via Hugging Face (`library models --install required --json`). CUE is
/// optional and installable only when an operator-hosted ONNX URL plus verified
/// pins are configured. Returns the CLI's JSON payload even if the install
/// failed, so the UI can show per-file errors instead of a generic invoke
/// failure.
#[tauri::command]
pub async fn library_models(
    app: AppHandle,
    install: Option<String>,
    force: Option<bool>,
) -> Result<Value, String> {
    let install = normalize_model_install_target(install)?;
    let mut args = model_library_args(install.as_deref(), force.unwrap_or(false));
    if install.is_some() {
        args.push("--progress".to_string());
    }
    let arg_refs: Vec<&str> = args.iter().map(String::as_str).collect();

    let (stdout, stderr, code) = run_library_to_completion(&app, &arg_refs).await?;
    parse_library_models_json(&stdout, &stderr, code)
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
                // embed-folder prints diagnostics (embedder, strategy, ...)
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
        let p = parse_embed_progress_line("[3/120] ok track.wav  ~€0.0123").expect("should parse");
        assert_eq!(p.n, 3);
        assert_eq!(p.total, 120);
        assert_eq!(p.status, "ok");
        assert_eq!(p.filename, "track.wav");
        assert!((p.cost_eur - 0.0123).abs() < 1e-9);
    }

    #[test]
    fn parses_progress_line_with_spaces_in_filename() {
        let p =
            parse_embed_progress_line("[12/40] skip My Cool Track (Extended Mix).flac  ~€0.0000")
                .expect("should parse");
        assert_eq!(p.n, 12);
        assert_eq!(p.status, "skip");
        assert_eq!(p.filename, "My Cool Track (Extended Mix).flac");
        assert_eq!(p.cost_eur, 0.0);
    }

    #[test]
    fn parses_err_progress_line() {
        let p =
            parse_embed_progress_line("[40/40] err broken.mp3  ~€0.0500").expect("should parse");
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
    fn maps_curate_result_from_flat_track_ids() {
        // The real CLI shape today: playlist carries `track_ids` (strings only),
        // no per-track titles. We map id → {track_id, title=id, meta="track <id>"}.
        let raw = json!({
            "theme": "warm sunset rooftop",
            "playlist": {
                "name": "Golden Hour",
                "track_ids": ["t1", "t2", "t3"],
                "m3u_path": "/x/golden.m3u8",
                "json_path": "/x/golden.json",
                "dropped_ids": []
            },
            "rationale": "Built a slow-burn arc from dusk to dark.",
            "iterations": 3,
            "stop_reason": "created",
            "seen_track_ids": ["t1", "t2", "t3", "t9"]
        });
        let m = map_curate_result(&raw);
        assert_eq!(m["name"], "Golden Hour");
        assert_eq!(m["stop_reason"], "created");
        assert_eq!(m["rationale"], "Built a slow-burn arc from dusk to dark.");
        assert_eq!(m["count"], 3);
        assert_eq!(m["tracks"][0]["track_id"], "t1");
        // honest: title IS the id (CLI gave no human title), meta names the id.
        assert_eq!(m["tracks"][0]["title"], "t1");
        assert_eq!(m["tracks"][0]["meta"], "track t1");
    }

    #[test]
    fn maps_curate_result_from_codex_backend_shape() {
        // The Codex backend (`library curate --backend codex --json`) emits a
        // FLAT shape: `playlist_name` + `track_ids` at the top level (no nested
        // `playlist` object) — see CodexCurateResult.to_dict. The mapper must read
        // both legacy nested and Codex-flat shapes through one contract.
        let raw = json!({
            "theme": "dark hypnotic peak-time",
            "stop_reason": "created",
            "playlist_name": "Codex Vibe Set",
            "track_ids": ["folder:aa", "folder:bb"],
            "m3u_path": "/x/codex-vibe-set.m3u8",
            "json_path": "/x/codex-vibe-set.json",
            "rationale": "A peak-time pressure curve.",
            "error": null
        });
        let m = map_curate_result(&raw);
        assert_eq!(m["name"], "Codex Vibe Set");
        assert_eq!(m["stop_reason"], "created");
        assert_eq!(m["rationale"], "A peak-time pressure curve.");
        assert_eq!(m["count"], 2);
        assert_eq!(m["tracks"][0]["track_id"], "folder:aa");
        assert_eq!(m["tracks"][1]["track_id"], "folder:bb");
        // honest: no per-track title from the flat id list → id IS the title.
        assert_eq!(m["tracks"][0]["title"], "folder:aa");
    }

    #[test]
    fn curate_name_falls_back_to_theme_and_uses_rich_tracks_when_present() {
        // Forward-compat: if a future CLI surfaces rich `tracks` objects with
        // titles/artists, prefer them; `name` falls back to the theme when the
        // playlist is unnamed.
        let raw = json!({
            "theme": "rolling hypnotic",
            "playlist": {
                "name": "",
                "tracks": [
                    { "track_id": "a1", "title": "Quälgeist", "artist": "Brutalismus" }
                ],
                "track_ids": ["a1"],
                "dropped_ids": []
            },
            "rationale": "",
            "stop_reason": "created"
        });
        let m = map_curate_result(&raw);
        assert_eq!(m["name"], "rolling hypnotic"); // empty name → theme
        assert_eq!(m["count"], 1);
        assert_eq!(m["tracks"][0]["title"], "Quälgeist");
        assert_eq!(m["tracks"][0]["meta"], "Brutalismus");
    }

    #[test]
    fn curate_empty_playlist_maps_to_zero_tracks() {
        // The "no playlist created" path still exits 0 in some flows; a null
        // playlist maps to an honest empty track list (UI shows the stop_reason).
        let raw = json!({
            "theme": "impossible vibe",
            "playlist": null,
            "rationale": "Nothing in the library matched.",
            "stop_reason": "no_create"
        });
        let m = map_curate_result(&raw);
        assert_eq!(m["name"], "impossible vibe");
        assert_eq!(m["count"], 0);
        assert_eq!(m["stop_reason"], "no_create");
        assert!(m["tracks"].as_array().unwrap().is_empty());
    }

    #[test]
    fn maps_build_set_export_path_when_present() {
        // A set-prep run terminates via export: stop_reason "exported", no
        // playlist, but a Rekordbox XML export_path the UI surfaces.
        let raw = json!({
            "theme": "warehouse opener, 90 min",
            "playlist": {
                "name": "Warehouse Opener",
                "track_ids": ["t1", "t2"],
                "dropped_ids": []
            },
            "rationale": "Eased in at 122, climbed to 126 by slot 8.",
            "iterations": 5,
            "stop_reason": "exported",
            "seen_track_ids": ["t1", "t2"],
            "export_path": "/Users/x/Music/vibemix-set.xml"
        });
        let m = map_curate_result(&raw);
        assert_eq!(m["stop_reason"], "exported");
        assert_eq!(m["export_path"], "/Users/x/Music/vibemix-set.xml");
        assert_eq!(m["count"], 2);
    }

    #[test]
    fn curate_result_export_path_is_null_when_absent() {
        // Plain curation never exports → export_path is null (not fabricated).
        let raw = json!({
            "theme": "dusk to dark",
            "playlist": { "track_ids": ["t1"], "dropped_ids": [] },
            "rationale": "",
            "stop_reason": "created"
        });
        let m = map_curate_result(&raw);
        assert!(m["export_path"].is_null());
    }

    #[test]
    fn curate_result_uses_agent_error_as_visible_rationale() {
        let raw = json!({
            "theme": "warehouse",
            "stop_reason": "codex_not_installed",
            "playlist_name": null,
            "track_ids": [],
            "rationale": "",
            "error": "Codex CLI not found. Install it and run codex login.",
        });
        let m = map_curate_result(&raw);
        assert_eq!(m["stop_reason"], "codex_not_installed");
        assert_eq!(
            m["rationale"],
            "Codex CLI not found. Install it and run codex login."
        );
        assert_eq!(m["count"], 0);
    }

    #[test]
    fn curate_result_preserves_clarification_prompt() {
        let raw = json!({
            "theme": "warehouse",
            "stop_reason": "clarification_needed",
            "playlist_name": null,
            "track_ids": [],
            "rationale": "Which direction should I take this?",
            "question": "Which direction should I take this?",
            "choices": ["Hypnotic", "Peak-time"]
        });
        let m = map_curate_result(&raw);
        assert_eq!(m["stop_reason"], "clarification_needed");
        assert_eq!(m["question"], "Which direction should I take this?");
        assert_eq!(m["choices"][0], "Hypnotic");
        assert_eq!(m["choices"][1], "Peak-time");
        assert_eq!(m["count"], 0);
    }

    #[test]
    fn app_agent_backend_is_pinned_to_codex() {
        unsafe {
            std::env::set_var("VIBEMIX_LIBRARY_AGENT_BACKEND", "gemini");
        }
        assert_eq!(library_agent_backend(), "codex");
        unsafe {
            std::env::remove_var("VIBEMIX_LIBRARY_AGENT_BACKEND");
        }
    }

    #[test]
    fn codex_shell_gate_only_fires_for_backend_arg() {
        assert!(library_args_request_codex_backend(&[
            "library",
            "chat",
            "hello",
            "--backend",
            "codex",
            "--json",
        ]));
        assert!(library_args_request_codex_backend(&[
            "library",
            "build-set",
            "brief",
            "--backend",
            "codex",
            "--json",
        ]));
        assert!(!library_args_request_codex_backend(&[
            "library",
            "chat",
            "codex",
            "--backend",
            "gemini",
            "--json",
        ]));
        assert!(!library_args_request_codex_backend(&[
            "library", "search", "codex",
        ]));
    }

    #[test]
    fn chat_library_args_pin_codex_json_and_history() {
        let args = chat_library_args(
            "Find 1 dark peak techno track.",
            Some(r#"[{"role":"you","text":"first"}]"#),
            Some(r#"{"deck":"A","deck_state":{"A":{"title":"Strobe","confidence":0.8}}}"#),
        );
        assert_eq!(
            args,
            vec![
                "library",
                "chat",
                "Find 1 dark peak techno track.",
                "--backend",
                "codex",
                "--json",
                "--history",
                r#"[{"role":"you","text":"first"}]"#,
                "--live-context",
                r#"{"deck":"A","deck_state":{"A":{"title":"Strobe","confidence":0.8}}}"#,
            ]
        );
        let refs: Vec<&str> = args.iter().map(String::as_str).collect();
        assert!(library_args_request_codex_backend(&refs));
    }

    #[test]
    fn chat_library_args_preserve_time_aligned_audio_context() {
        let live_context = json!({
            "live_context_schema_version": 2,
            "live_context_capabilities": [
                "deck_state",
                "deck_source_status",
                "audio_part_context",
                "deck_audio_separation_context",
                "audio_window_map",
                "audio_delta",
                "live_evidence"
            ],
            "deck": "A",
            "recent_moves": ["A_low: cut->killed"],
            "deck_source_context": concat!(
                "deck_source_context[identity_state=MusicState.deck_state ",
                "primary=nowplaying_controller_attribution_to_library_cache ",
                "resolved=A unresolved=B sources=folder_cache live_db=not_read ",
                "event_xml=diagnostic_only second_deck=independent_source_required ",
                "rule=unresolved_deck_is_not_transition_evidence]"
            ),
            "audio_part_context": concat!(
                "audio_part_context[surface=live_context P1=live_global_mix ",
                "P1_model_heard=false P1_runtime_observed=true P1_audience_heard=true ",
                "P1_span=-6.0..0.0 P1_deck_audio=global_mix_not_stems ",
                "deck1=A deck2=B together_audio=P1 per_deck_audio=not_attached ",
                "duplicate_audio=same_master_not_deck_split ",
                "rule=part_labels_not_outcome_verdict]"
            ),
            "deck_audio_separation_context": concat!(
                "deck_audio_separation_context[requested_device=BlackHole_2ch ",
                "capture_device=BlackHole_2ch input_channels=2 opened_channels=2 ",
                "sample_rate=48000 device_capacity=stereo_or_less mode=global_mix_only ",
                "current_capture=P1_global_mix gemini_audio=mono_downmix_of_capture ",
                "deckA_audio=not_captured deckB_audio=not_captured ",
                "per_deck_audio=not_attached isolated_decks=false ",
                "upgrade_path=multi_channel_deck_pair_capture ",
                "rule=separation_capability_not_outcome]"
            ),
            "audio_window_context": concat!(
                "audio_window_context[P1=master_global_mix pre=-6.0..-1.0 ",
                "action=-1.0..0.0 move_anchor=A_low_cut_to_killed@-0.3s:inside_P1 ",
                "P2=source_file_lookahead heard=false future=0.0..+3.0 ",
                "future_rule=forecast_only_not_audience_evidence ",
                "deckA_audio=not_attached deckB_audio=not_attached ",
                "per_deck_audio=structured_text_only duplicate_audio=same_master_not_deck_split ",
                "deck_separation=deck_lanes_context lane_aliases=deck1:A,deck2:B]"
            ),
        });
        let live_context_json =
            serde_json::to_string(&live_context).expect("live context serializes");

        let args = chat_library_args("What did that EQ move do?", None, Some(&live_context_json));

        assert_eq!(
            args,
            vec![
                "library",
                "chat",
                "What did that EQ move do?",
                "--backend",
                "codex",
                "--json",
                "--live-context",
                live_context_json.as_str(),
            ]
        );
        let live_context_arg = args
            .iter()
            .position(|arg| arg == "--live-context")
            .and_then(|index| args.get(index + 1))
            .expect("live context arg should be present");
        let parsed: Value =
            serde_json::from_str(live_context_arg).expect("live context arg should parse");
        assert_eq!(
            parsed
                .get("live_context_schema_version")
                .and_then(Value::as_i64),
            Some(2)
        );
        assert!(parsed
            .get("live_context_capabilities")
            .and_then(Value::as_array)
            .expect("capabilities array")
            .iter()
            .any(|value| value.as_str() == Some("audio_window_map")));
        assert!(parsed
            .get("live_context_capabilities")
            .and_then(Value::as_array)
            .expect("capabilities array")
            .iter()
            .any(|value| value.as_str() == Some("audio_part_context")));
        assert!(parsed
            .get("live_context_capabilities")
            .and_then(Value::as_array)
            .expect("capabilities array")
            .iter()
            .any(|value| value.as_str() == Some("deck_audio_separation_context")));
        assert!(parsed
            .get("audio_part_context")
            .and_then(Value::as_str)
            .unwrap_or("")
            .contains("P1_model_heard=false"));
        assert!(parsed
            .get("audio_part_context")
            .and_then(Value::as_str)
            .unwrap_or("")
            .contains("P1_deck_audio=global_mix_not_stems"));
        assert!(parsed
            .get("deck_audio_separation_context")
            .and_then(Value::as_str)
            .unwrap_or("")
            .contains("deckA_audio=not_captured"));
        assert!(parsed
            .get("deck_audio_separation_context")
            .and_then(Value::as_str)
            .unwrap_or("")
            .contains("per_deck_audio=not_attached"));
        assert!(parsed
            .get("deck_source_context")
            .and_then(Value::as_str)
            .unwrap_or("")
            .contains("second_deck=independent_source_required"));
        assert!(parsed
            .get("deck_source_context")
            .and_then(Value::as_str)
            .unwrap_or("")
            .contains("rule=unresolved_deck_is_not_transition_evidence"));
    }

    #[test]
    fn chat_library_args_omit_empty_history_flag() {
        let args = chat_library_args("hello", None, None);
        assert_eq!(
            args,
            vec!["library", "chat", "hello", "--backend", "codex", "--json"]
        );
        assert!(!args.iter().any(|arg| arg == "--history"));
        assert!(!args.iter().any(|arg| arg == "--live-context"));
    }

    #[test]
    fn model_library_args_shape_status_install_and_force() {
        assert_eq!(
            model_library_args(None, false),
            vec!["library", "models", "--json"]
        );
        assert_eq!(
            model_library_args(Some("required"), false),
            vec!["library", "models", "--json", "--install", "required"]
        );
        assert_eq!(
            model_library_args(Some("cue"), true),
            vec!["library", "models", "--json", "--install", "cue", "--force"]
        );
    }

    #[test]
    fn parse_model_progress_line_accepts_prefixed_json_only() {
        let payload = parse_model_progress_line(
            r#"VIBEMIX_MODEL_PROGRESS {"target":"required","id":"clap","n":2,"total":6,"status":"downloading","rel_path":"onnx/text_model.onnx","downloaded":1048576,"size":501513769}"#,
        )
        .expect("progress payload");

        assert_eq!(payload["target"], "required");
        assert_eq!(payload["id"], "clap");
        assert_eq!(payload["n"], 2);
        assert_eq!(payload["status"], "downloading");
        assert!(parse_model_progress_line("plain stderr").is_none());
    }

    #[test]
    fn model_install_target_normalizes_and_rejects_unknown() {
        assert_eq!(normalize_model_install_target(None).unwrap(), None);
        assert_eq!(
            normalize_model_install_target(Some(" CLAP ".to_string())).unwrap(),
            Some("clap".to_string())
        );
        assert_eq!(
            normalize_model_install_target(Some(" required ".to_string())).unwrap(),
            Some("required".to_string())
        );
        assert_eq!(
            normalize_model_install_target(Some("all".to_string())).unwrap(),
            Some("all".to_string())
        );
        assert_eq!(
            normalize_model_install_target(Some("cue".to_string())).unwrap(),
            Some("cue".to_string())
        );
        let err = normalize_model_install_target(Some("gpt".to_string()))
            .expect_err("unknown target should fail");
        assert!(err.contains("required | clap | cue | all"));
    }

    #[test]
    fn parse_cli_json_surfaces_stderr_error_on_failure() {
        let stderr = r#"{"error": "No library cache.", "results": []}"#;
        let err = parse_cli_json("", stderr, 1).expect_err("should be Err");
        assert_eq!(err, "No library cache.");
    }

    #[test]
    fn parse_cli_json_returns_structured_agent_terminal_on_failure() {
        let stderr = r#"{
  "theme": "warehouse",
  "stop_reason": "codex_not_installed",
  "playlist_name": null,
  "track_ids": [],
  "rationale": "",
  "error": "Codex CLI not found. Install it and run codex login."
}
[viber/codex] codex_not_installed: install Codex
"#;
        let payload = parse_cli_json("", stderr, 1).expect("agent terminal payload");
        assert_eq!(payload["stop_reason"], "codex_not_installed");
        assert_eq!(
            payload["error"],
            "Codex CLI not found. Install it and run codex login."
        );
    }

    #[test]
    fn parse_cli_json_returns_structured_clarification_on_exit_11() {
        let stderr = r#"[viber/codex] clarification_needed:
  Which direction should I take this?

  1. More hypnotic, lower vocal density
  2. Brighter peak-time pressure

  Re-run with: library curate "warehouse + <chosen option>"
"#;
        let payload = parse_cli_json("", stderr, 11).expect("clarification payload");
        assert_eq!(payload["stop_reason"], "clarification_needed");
        assert_eq!(payload["question"], "Which direction should I take this?");
        assert_eq!(payload["choices"][0], "More hypnotic, lower vocal density");
        assert_eq!(payload["choices"][1], "Brighter peak-time pressure");
        assert_eq!(payload["track_ids"].as_array().unwrap().len(), 0);
    }

    #[test]
    fn parse_cli_json_accepts_success_json_with_trailing_hint() {
        let stdout = r#"{"ok":true,"count":2}
[library] cache warm
"#;

        let payload = parse_cli_json(stdout, "", 0).expect("first JSON value");

        assert_eq!(payload["ok"], true);
        assert_eq!(payload["count"], 2);
    }

    #[test]
    fn parse_library_models_json_keeps_failed_install_summary_with_trailing_hint() {
        let stdout = r#"{"models":[],"required_ready":false,"all_ready":false,"install":{"target":"required","results":[],"ok":false}}
[models] required setup failed
"#;

        let payload = parse_library_models_json(stdout, "", 1).expect("structured model result");

        assert_eq!(payload["required_ready"], false);
        assert_eq!(payload["install"]["target"], "required");
        assert_eq!(payload["install"]["ok"], false);
    }
}
