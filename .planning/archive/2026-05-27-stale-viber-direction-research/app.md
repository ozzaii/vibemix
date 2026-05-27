# Vibe Engine — App Integration Audit (READ-ONLY)

Repo: /Users/ozai/projects/dj-set-ai · branch live-tuning-or-brain · vibemix Tauri app

## VERDICT: NO — three concrete bugs will break the live `cargo tauri dev` test

The spawn stack (invoke → Rust → `uv run python -m vibemix library …` → vectors)
is correctly wired and will actually run. But the GUI test fails on real bugs:

1. **No way to open the window** — `open_library_window` is registered but NOTHING
   in the UI or tray ever calls it. Test can only proceed via a manual JS `invoke()`.
2. **embed-folder is 100% broken** — the TS sends `strategy: "cue-anchored"` (default)
   / `"mean"`; the Rust command hard-rejects anything but `cue_anchored` / `mean_excerpt`.
   Every Ingest run returns `Err("invalid strategy …")` before spawning Python.
3. **Search/Similar results render `[object Object]`** as the caption — the Rust bridge
   sends `meta` as a JSON OBJECT, the TS renders it with `esc(r.meta)` expecting a string.
   Scores + titles render fine; the caption line is broken in the REAL app only.

Search + Similar will otherwise spawn Python, embed, and return ranked rows correctly.

## STACK TRACE (each hop)

### Hop 1 — invoke registration & spawn  ✅
- `main.rs:100-104` — all 5 commands in `invoke_handler`; `mod library_cmds;` at line 25. OK.
- `build_library_command` (library_cmds.rs:75) → `resolve_sidecar_invocation_for_library`
  (sidecar.rs:436). Under dev (`VIBEMIX_DEV_SIDECAR=1`) returns `DevSource{ program:"uv",
  args:["run","python","-m","vibemix"], cwd = repo_root_from_manifest() }`. cwd = repo
  root (tauri/src-tauri → tauri → root), so Python `_load_env_robust()` finds repo `.env`. OK.
- **GEMINI_API_KEY relay** ✅ — library_cmds.rs:110-116 relays `FORWARDED_ENV_KEYS`
  (GEMINI_API_KEY, OPENROUTER_API_KEY) from parent env when non-empty. Python also loads
  `.env` itself, so a key in either place works.
- **NOTE**: dev spawn REQUIRES `VIBEMIX_DEV_SIDECAR=1` in the env that launches
  `cargo tauri dev`. With the flag UNSET the resolver hits the Bundled arm →
  `resolve_sidecar_path()` → `resource_dir()`, which under dev points at a non-existent
  bundle → `library_*` commands return `Err("sidecar lookup failed…")`. This is the same
  contract as the main sidecar watchdog; just confirm the flag is exported.

### Hop 2 — capabilities  ✅
- capabilities/default.json:5 — `"library"` window IS in `windows` scope.
- shell:allow-execute (lines 36-37) grants `{cmd:"uv", args:true}` and
  `{cmd:"python3", args:true}` — the dev-source CLI invocation is permitted.
- Bundled path spawns the resolved binary via `app.shell().command(&bin)` (sidecar-style),
  no extra allow entry needed. OK.

### Hop 3 — window creation & vite input  ✅
- `open_library_window` (library_cmds.rs:349) — focus-existing, then builds a
  WebviewWindow label `"library"` loading `WebviewUrl::App("library.html")`, 1180×760. OK.
- vite.config.ts:108 — `library: resolve(projectRoot,"library.html")` is a registered
  rollup input → resolves in BOTH dev (dev-server) and prod (dist/). library.html mounts
  `/src/library/index.ts`. OK.

### Hop 4 — CLI JSON shape vs Rust parser  ✅ (parser) / see Hop 6 (meta)
- Python `library search … --json` (`__main__.py:1457`) emits PURE JSON to **stdout**
  via `_json.dump(…, indent=2)` — pretty-printed/multi-line:
  `{"query","cache_hit",results:[{track_id,title,artist,bpm,confidence,snippet}]}`.
- The `-> library store: backend=…` line goes to **stderr** (store.py:146-168, all
  `file=sys.stderr`). So stdout is clean JSON. ✅
- Rust `parse_cli_json` (library_cmds.rs:177) does `serde_json::from_str(stdout.trim())`
  — serde tolerates multi-line/indented JSON. ✅
- `map_search_results` reads `confidence` → `score` (search) and `similarity` → `score`
  (similar). ✅ Matches `VibeSearchResult.confidence` / `SimilarResult.similarity`.
- `centered`/`corpus_size` default to false/len() — the CLI does NOT emit them today
  (search dumps only query/cache_hit/results). Forward-compat default kicks in. ✅
- `library_stats` runs `library budget --json` (offline, no Gemini call) and reads
  `telemetry.current_cost_estimate_eur`; reports indexed/failed as 0 (no CLI source).
  Header will show indexed=0 — cosmetic, documented as deferred. ⚠️ minor.

### Hop 5 — embed-folder progress streaming  ✅ parser / ❌ strategy (see bug 2)
- Progress lines `[n/total] ok|skip|err <file>  ~€<cost>` on stdout (only when NOT --json);
  Rust spawns WITHOUT --json and line-buffers, parses, emits `library://embed-progress`.
  Final `embed-folder done: …` → `library://embed-done`. Parsers match the Python format
  (folder_ingest + __main__.py:1600). Two trailing stdout lines (`-> library cache:`,
  `-> query it:`) are ignored by both parsers — harmless. ✅
- BUT the whole path is unreachable because of the strategy mismatch (bug 2).

### Hop 6 — frontend api.ts real-vs-fallback  ✅ real path taken (see THE RISK)

## THE REAL-VS-FALLBACK RISK — DEFINITIVE ANSWER

**In a real `cargo tauri dev` run the app uses the REAL commands, NOT the fallback.**
- api.ts `getInvoke()` (line 84) does `await import("@tauri-apps/api/core")` and reads
  `mod.invoke`. In a real Tauri webview this import resolves and `invoke` is a function →
  `_invoke` is set, fallback is skipped. The import only fails under plain `vite`/jsdom.
- The fallbacks fire ONLY on (a) import failure (non-Tauri) or (b) the invoke call THROWS.
  In the real app neither happens for search/similar/stats — they return real data.
- **Subtle trap**: because every call wraps the real invoke in `try/catch → return DEV_*`,
  a real backend ERROR (e.g. "No library cache", missing key, bad strategy) is SWALLOWED
  and the UI silently shows the canned 142-track sample data. So if the library cache is
  empty during the test, you will see plausible-looking fake results and think it worked.
  **Mitigation for the test: embed a folder first (or watch the terminal/stderr), and
  verify the rendered track titles are YOUR tracks, not the baked-in sample list**
  (Raffertie — The Substance, ARTLUS…, Quälgeist, etc. = the dev fallback fingerprint).

## BUG DETAILS

### Bug 2 — strategy enum mismatch (embed-folder always rejected)
- api.ts:30 `EmbedStrategy = "mean" | "cue-anchored"`; state-machine.ts:38 default
  `strategy: "cue-anchored"`; index.ts:277 sets `"mean" | "cue-anchored"`.
- library_cmds.rs:504 rejects unless `"mean_excerpt"` or `"cue_anchored"`.
- Result: `invoke("library_embed_folder",{path,strategy:"cue-anchored"})` →
  `Err("invalid strategy \"cue-anchored\" …")`, caught by api.ts:206 → returns `false`
  (dev replay), so the UI animates the FAKE 8-file log and never embeds anything.
- Fix (TS side): send `mean_excerpt` / `cue_anchored` (map the chip values), OR widen the
  Rust validator to accept the hyphen/`mean` forms. One-liner either way.

### Bug 3 — meta object vs string
- Rust `map_search_results` (library_cmds.rs:227) sets `"meta": r.clone()` — the full raw
  result OBJECT.
- TS `TrackResult.meta: string` (api.ts:39) and index.ts:92 `esc(r.meta)`.
- `esc()` (index.ts:72) calls `.replace` on its arg; on an object `String(obj)` →
  `"[object Object]"`, so the caption renders literally "[object Object]". (Titles/scores
  are fine.) Dev fallback hides this because there `meta` IS a string.
- Fix: Rust should send a short caption string (e.g. the `snippet`/`folder:hash · 1536d`),
  OR the TS should read `r.meta.snippet` and type `meta` as the object.

## HOW TO OPEN THE WINDOW — MISSING TRIGGER (gap)

There is **no UI affordance** to open the Vibe Engine window:
- No `invoke("open_library_window")` anywhere in tauri/ui (index.html, main.ts, src/*.ts).
- tray.rs build_menu has mood / mute / "Open Session UI" / recalibrate / settings / quit —
  no "Open Vibe Engine" / "Library" item.
- The command is registered (main.rs:104) and the window/capability/vite-input are all
  ready — it just has no caller. For the test you must open it programmatically.

## STEP-BY-STEP ON-APP TEST RECIPE (cargo tauri dev)

1. Ensure `.env` at repo root has `GEMINI_API_KEY=…`. Export `VIBEMIX_DEV_SIDECAR=1`
   in the SAME shell that launches the app (else library commands hit the bundled arm
   and error). Optionally `VIBEMIX_DEV_PYTHON=$(pwd)/.venv/bin/python3` to skip `uv`.
2. Confirm a library cache exists: run `uv run python -m vibemix library search "dark"
   --k 3 --json` in the terminal first. If it errors "No library cache", embed a folder
   via CLI (`uv run python -m vibemix library embed-folder /Users/ozai/Music/hardtechno
   --strategy mean_excerpt`) so search/similar have data. (Confirms the Python side
   independently of the GUI.)
3. Launch `cargo tauri dev` from tauri/src-tauri (or `cargo tauri dev` at repo if wired).
4. OPEN THE WINDOW (no UI button): in the MAIN window devtools console run
   `window.__TAURI__.core.invoke("open_library_window")`. The 1180×760 vibe-engine
   window should appear loading library.html.
5. SEARCH: type a vibe (e.g. "dark hypnotic rolling"), Run. EXPECT real rows. **Verify
   the titles are YOUR tracks, not the sample set** (Raffertie/ARTLUS/Quälgeist = fake).
   The caption line under each title will read "[object Object]" until Bug 3 is fixed —
   that itself confirms the REAL bridge is in play (fallback would show a real caption).
6. SIMILAR: switch to Similar, give a seed track_id (from step 2's `--json` output), Run.
   Same verification.
7. INGEST: switch to Ingest, set a folder, Run. EXPECT it to be BROKEN today (Bug 2) —
   either an error or the canned 8-file fake replay (jecta/Just Like You/…). Watch the
   `cargo tauri dev` terminal: if you see NO Python embed-folder stderr and the same 8
   files every time, it fell to the fallback → confirms the strategy bug.
8. STATS header: indexed shows 0 (documented), spent updates from budget telemetry.

## SUMMARY OF FIXES NEEDED BEFORE A CLEAN TEST
- Add an "Open Vibe Engine" trigger (tray item or main-UI button) → invoke open_library_window.
- Fix strategy enum: TS `mean_excerpt`/`cue_anchored` (or widen Rust validator).
- Fix meta: Rust emit a caption string, or TS read `meta.snippet` + retype.
- (Optional) Surface real backend errors instead of silently falling back to sample data,
  so a failed search isn't mistaken for success during the test.
