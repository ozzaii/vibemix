# Phase 29: Post-Session Debrief MVP UI - Context

**Gathered:** 2026-05-15
**Status:** Ready for planning
**Mode:** Auto-generated (gsd-autonomous fully — Claude's discretion locked against ROADMAP + REQUIREMENTS + STATE + memory)

<domain>
## Phase Boundary

After a session, the user opens a Debrief window that walks them through what happened — chapters, voiced TL;DR, drills, and a clickable waveform timeline. Every advice line cited from session evidence — un-cited critique stripped.

**Mapped REQ-IDs (9):** DEBRIEF-03 (chaptered review), DEBRIEF-04 (60–90s voiced TL;DR), DEBRIEF-05 (clickable timeline), DEBRIEF-06 (3 drills), DEBRIEF-07 (cited-critique stripping), DEBRIEF-08 (Tauri open_debrief_window command + second WebviewWindow), DEBRIEF-09 (Rust sidecar child lifecycle on close), DEBRIEF-10 (`debrief.v1` schema additive-only lock), DEBRIEF-11 (Settings → Recordings → Open Debrief entry).

**In scope:**
- Tauri command `open_debrief_window` — second WebviewWindow (label=`debrief`, 1280×720, standard chrome) spawned from Settings → Recordings.
- Spawns `--debrief <session_dir>` PyInstaller binary on existing port 8766.
- Renders chaptered review from `events.jsonl` + 60–90s Gemini-TTS voiced TL;DR (MP3) in WaveSurfer.js.
- Clickable waveform regions → seek + citation tooltip.
- 3 drills per session, SBI/STAR-AR pattern from FEATURES.md, grounded in cited critique.
- Cited-critique stripper — every advice line carries `[ev:*]`, `[track:*]`, or `[mix:*]` reference from EvidenceRegistry snapshot.
- Rust `WindowEvent::CloseRequested` handler — sidecar child teardown via `Arc<Mutex<Option<CommandChild>>>` in `sidecar.rs`.
- `debrief.v1` jsonschema lock (additive-only).

**Out of scope:**
- Real-time live debrief (this is post-session only).
- Multi-session aggregation / trends (deferred to Phase 32 DJ profile).
- Drill audio playback / DJ exercises within the window (text-only drills).
- Re-recording / patching sessions.
- Cross-user sharing.
- Custom rubrics / drill templates.
</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion (locked per gsd-autonomous fully)

All choices at Claude's discretion, grounded in:
- ROADMAP Phase 29 success criteria (verbatim)
- REQUIREMENTS.md DEBRIEF-03..11
- Pitfalls P81 (cross-webview MP3 parity), P82 (additive-only schema lock)
- v2.0 Phase 25 DEBRIEF sidecar slot (`--debrief` flag + port 8766 + 3 IPC reservations) — already shipped
- v2.0 Phase 15 recording browser — already shipped
- Memory `project_visual_direction_cdj_whisper` — CDJ Whisper visual direction
- Memory `feedback_mic_audio_as_multimodal_part` — audio Parts pattern
- Memory `project_anti_slop_grounded_gemini_thesis` — every line must be grounded

### Window architecture (DEBRIEF-08)
- Tauri command `open_debrief_window(session_dir: String)` creates `WebviewWindow` with label=`debrief`, 1280×720, standard chrome (NOT decorated=false — full title bar so user can move/resize), title=`Debrief — {session_name}`.
- Single debrief window at a time. If already open, focus existing.
- URL: `tauri://localhost/debrief.html?session=<urlencoded>`.

### Sidecar lifecycle (DEBRIEF-09 / P81)
- `Arc<Mutex<Option<CommandChild>>>` in `sidecar.rs` — same pattern as v2.0 mascot sidecar.
- On `open_debrief_window` → spawn `--debrief <session_dir>` PyInstaller binary; store CommandChild in mutex.
- Subscribe to `WindowEvent::CloseRequested` on the debrief window → take CommandChild out of mutex → `.kill().await`.
- Health check: if sidecar dies before window closes, emit `ipc.debrief.error` and close window.

### Port + IPC (DEBRIEF-08)
- Port 8766 (already reserved in v2.0 Phase 25).
- 3 new IPC schemas under existing `debrief.v1` namespace: `debrief.chapter_list`, `debrief.tldr_audio`, `debrief.drills`, `debrief.citation_tooltip`. All additive-only (P82).
- TS codegen via existing `npm run check:ipc`.

### Chaptered review (DEBRIEF-03)
- Auto-derived from `events.jsonl` event types: TRACK_CHANGE → "Track 1: <title>", PHASE → "Intro/Build/Drop/Outro markers", KAAN_SPOKE → "Crowd interaction".
- Heuristic: chapter break on TRACK_CHANGE OR PHASE transition > 30s apart.
- Persists in `<session_dir>/session_debrief.json` (schema = `debrief.v1`).

### Voiced TL;DR (DEBRIEF-04 / P81)
- Gemini TTS Achird voice (consistent with Phase 27 LATENCY-15 ack bank).
- Target length: 60–90s. Builds from chapter list + cited critique highlights.
- Format: **MP3** (cross-webview parity verified: WKWebView macOS + WebView2 Windows both support MP3 natively — no codec negotiation required).
- Persists in `<session_dir>/debrief_tldr.mp3`. SHA256 hash logged in `session_debrief.json` for cache invalidation.
- Generated once on first `open_debrief`, cached forever after.

### Waveform + timeline (DEBRIEF-05)
- WaveSurfer.js v7.10 (locked in STATE.md v2.1 deps).
- Audio source: `<session_dir>/voice.wav` (Gemini AI voice output) overlaid with chapter markers + cited-region markers.
- Regions plugin: click → seek to that timestamp + show citation tooltip with `{event_id, evidence_text, timestamp}`.
- Skin: CDJ Whisper — single amber accent for waveform fill, warm black background.

### 3 drills (DEBRIEF-06)
- Generated by Gemini 3 Pro (high-quality reasoning) — one-shot prompt that receives full session_debrief.json + cited critique highlights and returns 3 drills in `debrief.drills` schema.
- SBI/STAR-AR pattern: each drill = `{situation, behavior, impact, action_recommended}`.
- Stored in `session_debrief.json` under `drills` array.

### Cited-critique stripping (DEBRIEF-07)
- Gemini response post-processor: regex `\[(ev|track|mix):[\w\-]+\]` MUST appear in every advice sentence.
- Sentences without citation are stripped before display.
- Test: `test_no_uncited_critique_in_debrief` — pass debrief JSON through stripper, assert zero sentences without citation.

### Schema lock (DEBRIEF-10 / P82)
- `debrief.v1` schema in `ipc/schemas/debrief.py` (pydantic) + Draft-07 jsonschema export in `messages.schema.json`.
- Additive-only contract: no required fields removed, no field types changed across v2.1.
- CI gate: `test_debrief_schema_additive_only` — compares current schema vs v2.1 baseline, asserts only additions.

### Entry point integration (DEBRIEF-11)
- Settings → Recordings tab (already exists from v2.0 Phase 15) → row hover reveals "Open Debrief" button → invokes Tauri command.
- Visual: amber-2 link button, no glow, restraint per CDJ Whisper direction.
- Disable button if `events.jsonl` missing or session length < 5min (no useful debrief from tiny recordings).

### Frontend convention
- Vanilla TS class (per memory + Phase 28 research). NO React.
- File: `tauri/ui/src/debrief/debrief-window.ts` (entry) + `tauri/ui/src/debrief/components/{chapter-list,tldr-player,timeline,drills-panel}.ts`.
- `debrief.html` is the second-window entry HTML.

### Visual direction
- CDJ Whisper (memory `project_visual_direction_cdj_whisper`): Pioneer-grade, 5 warm blacks, single amber accent (4 intensities).
- Geist + Fraunces typefaces.
- Timeline regions: amber-3 fill 30% opacity, amber-1 outline 1px.
- Citation tooltip: warm-black-2 background, amber-2 text, fade 200ms.
</decisions>

<code_context>
## Existing Code Insights

- **v2.0 Phase 25 (shipped) sidecar slot:** `tauri/src-tauri/src/sidecar.rs` — `Arc<Mutex<Option<CommandChild>>>` pattern, port 8766 reserved.
- **v2.0 Phase 15 (shipped) recording browser:** Settings → Recordings tab — base UI exists, Phase 29 adds "Open Debrief" button.
- **v2.0 Phase 25 IPC reservation:** 3 IPC schema slots reserved under `debrief.v1` namespace.
- **Gemini TTS** — Achird voice consistent with Phase 27 ack bank (`scripts/generate_ack_audio.py` template).
- **EvidenceRegistry** — read-only snapshot for past sessions; lookup by event_id → `{evidence_text, timestamp}`.
- **WaveSurfer.js v7.10** — already in v2.1 deps lockfile.
- **Frontend convention** — vanilla TS class pattern; IPC codegen via `npm run check:ipc` from `messages.schema.json` Draft-07.

Codebase maps under `.planning/codebase/` feed plan-phase research.
</code_context>

<specifics>
## Specific Ideas

- **MP3 codec parity (P81)** — verified at planning time: WKWebView + WebView2 both decode MP3 natively. No need for AAC/OGG fallback.
- **Single debrief window at a time** — focus existing if already open. Avoids sidecar process explosion.
- **Drill template = SBI/STAR-AR** — situation/behavior/impact + action-recommended. Format locked in FEATURES.md.
- **Citation tooltip on click, not hover** — click-only avoids accidental tooltip-spam during timeline scrubbing.
- **Cache TL;DR forever** — never regenerate unless user explicitly asks for fresh.
- **No live debrief** — strictly post-session. Don't drift into "AI commentary replay" — that's the main app's job.
- **Session minimum length** — 5min minimum for debrief to surface, else "session too short for meaningful debrief".
</specifics>

<deferred>
## Deferred Ideas

- **Drill audio playback / DJ exercises** — text-only in v2.1. v2.2 stretch.
- **Multi-session aggregation / trends** — Phase 32 DJ profile owns it.
- **Custom drill templates** — out of scope.
- **Drill bookmarking / progress tracking** — v2.2 backlog.
- **Sharing debrief publicly** — privacy concern, out of scope.
- **Export debrief as PDF/Markdown** — v2.2.
- **Live debrief / commentary replay** — explicitly NOT in this phase; main app handles live.
</deferred>
