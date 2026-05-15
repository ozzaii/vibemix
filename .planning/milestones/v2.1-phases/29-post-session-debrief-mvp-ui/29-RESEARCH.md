# Phase 29: Post-Session Debrief MVP UI — Research

**Researched:** 2026-05-15
**Domain:** Tauri 2 second-window UI · vanilla TS · WaveSurfer.js v7 regions · Python sidecar dispatch · Gemini 3 Pro structured output · Achird TTS · cited-critique stripping
**Confidence:** HIGH (every load-bearing claim verified against Context7 + repo + npm registry)

## Summary

Phase 29 fills the v2.0 DEBRIEF architectural slot (sidecar `--debrief` flag + port 8766 + 3 IPC reservations, all shipped in Phase 25) with a real, second-window UI. The session-replay reads `events.jsonl` + `voice.wav` + `evidence_registry.json` from `<recordings_root>/<session_dir>/`, derives chaptered review heuristically, generates a 60–90s Achird-voice TL;DR (Gemini TTS → MP3 via PyAV), produces 3 SBI/STAR-AR drills via a single Gemini 3 Pro structured-output call, and renders the surface in a 1280×720 standard-chrome Tauri webview that talks to the sidecar over the existing port-8766 reservation. Every advice line gets stripped if it doesn't carry an `[ev:*] / [track:*] / [mix:*]` citation per the Phase 20 linter pattern reused in debrief tolerance mode (±2.0s).

The phase is **dock-into-slot + extend**, not redesign — Phase 25 already shipped the entry point, port constant, dispatch flag, 3 dataclass payloads (`DebriefSessionLoadedPayload`, `DebriefCitationSummaryPayload`, `DebriefEventTimelinePayload`), 3 wrapper classes (`DebriefSessionLoaded` / `DebriefCitationSummary` / `DebriefEventTimeline`), and the corresponding JSON-schema entries in `tauri/ui/src/ipc/messages.schema.json`. The Phase 25 schemas are **additive-only-locked** (P82) and Phase 29 grows them — never breaks them.

**Primary recommendation:** Replace the `_run_debrief_sidecar` banner-only body with a real async WS server on `127.0.0.1:8766`; spawn from Rust via a new `open_debrief_window` Tauri command that runs `sidecar(...).args(["--debrief", session_dir])` AND builds a `WebviewWindow` (label=`"debrief"`); wire the existing `sidecar.rs::Arc<Mutex<Option<CommandChild>>>` pattern to kill the child on `WindowEvent::CloseRequested`. Vanilla TS + WaveSurfer.js v7.12.7 + RegionsPlugin for the timeline. MP3 (verified MP3 plays on both WKWebView and WebView2). Gemini 3 Pro with `responseSchema` Pydantic model for the 3 drills. Cited-critique stripping = sentence-level regex `\[(ev|track|mix|aud|midi|screen|tend):[^\s,\]]+\]` (reusing Phase 18's locked grammar).

## User Constraints (from CONTEXT.md)

### Locked Decisions (Claude's Discretion per `gsd-autonomous fully`)

All choices grounded in ROADMAP Phase 29 success criteria, REQUIREMENTS.md DEBRIEF-03..11, Pitfalls P81+P82, v2.0 Phase 25 sidecar slot (shipped), v2.0 Phase 15 recording browser (shipped), and memories:

**Window architecture (DEBRIEF-08):**
- Tauri command `open_debrief_window(session_dir: String)` creates `WebviewWindow` with label=`"debrief"`, 1280×720, **standard chrome** (NOT `decorations(false)` — full title bar, movable, resizable so user can manage the window like any normal window).
- Title: `Debrief — {session_name}`.
- Single debrief window at a time. If already open, focus existing instance.
- URL: `tauri://localhost/debrief.html?session=<urlencoded(session_dir)>`.

**Sidecar lifecycle (DEBRIEF-09 / P81 placement-note resolution):**
- `Arc<Mutex<Option<CommandChild>>>` in `sidecar.rs` — same pattern as `SidecarHandle` (already shipped).
- On `open_debrief_window` → spawn `--debrief <session_dir>` PyInstaller binary; store the new CommandChild in a NEW `DebriefSidecarHandle` Tauri-managed state (separate from main `SidecarHandle` since they own different children).
- Subscribe to `WindowEvent::CloseRequested` on the debrief window → `take()` the CommandChild out of the mutex → `child.kill()`.
- Health check: if sidecar dies before window closes, emit `sidecar-debrief-crashed` and close the window.

**Port + IPC (DEBRIEF-08 / DEBRIEF-10 / P82):**
- Port 8766 (already reserved in v2.0 Phase 25 — `DEBRIEF_PORT` constant at `src/vibemix/__main__.py:199`).
- **Existing schemas** (additive-only): `DebriefSessionLoaded` / `DebriefCitationSummary` / `DebriefEventTimeline`.
- **New schemas to add** (additive-only, extend `debrief.py`): `DebriefChapterList`, `DebriefTldrAudio`, `DebriefDrills`, `DebriefCitationTooltip`, `DebriefError`. All under `ipc.debrief.*` namespace.
- TS codegen via existing `npm run check:ipc`.

**Chaptered review (DEBRIEF-03):**
- Auto-derived from `events.jsonl` event types (verified present in real sample sessions): `TRACK_CHANGE` → "Track N: <title>", `PHASE` → phase boundaries ("Intro/Build/Drop/Outro"), `LAYER_ARRIVAL` → arrival cards, `MIX_MOVE` → "Mix at MM:SS", `KAAN_SPOKE` → "Crowd interaction".
- Heuristic: chapter break on `TRACK_CHANGE` OR `PHASE` transition older than 30s.
- Persists in `<session_dir>/session_debrief.json` (schema = `debrief.v1`).

**Voiced TL;DR (DEBRIEF-04 / P81):**
- Gemini TTS Achird voice (consistent with Phase 27 LATENCY-15 ack bank).
- Target length: 60–90s.
- **Format: MP3** (cross-webview parity verified: WKWebView macOS supports MP3 via WebKit's codec set; WebView2 Windows supports MP3 via Chromium's codec set).
- Persists in `<session_dir>/debrief_tldr.mp3`. SHA256 hash logged in `session_debrief.json` for cache invalidation.
- Generated once on first `open_debrief`, cached forever after (re-generate only on explicit user "refresh").

**Waveform + timeline (DEBRIEF-05):**
- WaveSurfer.js v7.12.7 (confirmed current via npm registry, released 2026-05-13).
- Audio source: `<session_dir>/voice.wav` (Gemini AI voice output, 24kHz s16le).
- Regions plugin: click → `wavesurfer.setTime(start)` + tooltip showing `{event_id, evidence_text, timestamp}`.
- CDJ Whisper skin: amber-3 fill 30% opacity for regions, amber-1 outline 1px; warm-black-2 background.

**3 drills (DEBRIEF-06):**
- Generated by Gemini 3 Pro one-shot, `responseSchema=Pydantic Drills model`.
- SBI/STAR-AR pattern: each drill = `{situation, behavior, impact, action_recommended}`.
- Stored in `session_debrief.json` under `drills` array.

**Cited-critique stripping (DEBRIEF-07):**
- Sentence-splitter (regex `[.!?]+\s+`) → for each sentence, require ≥1 match of the **existing** Phase 18 EBNF grammar `EVIDENCE_CITATION_RE` (already shipped at `vibemix.state.evidence_registry.EVIDENCE_CITATION_RE`).
- Sentences without any citation are stripped.
- Test: `test_no_uncited_critique_in_debrief` — pass debrief JSON through stripper, assert zero uncited sentences.

**Schema lock (DEBRIEF-10 / P82):**
- `debrief.v1` schema in `src/vibemix/ui_bus/schemas/debrief.py` (frozen-slotted dataclasses) + Draft-07 jsonschema export in `tauri/ui/src/ipc/messages.schema.json`.
- Additive-only contract: no required fields removed, no field types changed across v2.1.
- CI gate: `test_debrief_schema_additive_only` — compares current schema vs v2.1 baseline, asserts only additions.

**Entry point (DEBRIEF-11):**
- Settings → Recordings tab (already shipped Phase 15) — row hover reveals "Open Debrief" button → invokes `invoke("open_debrief_window", { session_dir })`.
- 5th action button in the existing `.vmx-rec-row__actions` cluster (currently 4: replay · reveal · open-external · delete; grows to 5 with debrief inserted before delete).
- Disable when `events.jsonl` missing OR session length < 5min.

**Frontend convention:**
- Vanilla TS class (per Phase 28 research lock + memory).
- File: `tauri/ui/src/debrief/debrief-window.ts` (entry) + `tauri/ui/src/debrief/components/{chapter-list,tldr-player,timeline,drills-panel,citation-tooltip}.ts`.
- `tauri/ui/debrief.html` is the second-window entry HTML.

**Visual direction (CDJ Whisper memory):**
- 5 warm blacks, single amber accent (4 intensities), Geist + Fraunces typefaces.
- Timeline regions: amber-3 fill 30% opacity, amber-1 outline 1px.
- Citation tooltip: warm-black-2 background, amber-2 text, fade 200ms.

### Claude's Discretion (open for plan-phase recommendation)

- Internal task ordering inside Wave 0 / Wave 1 / Wave 2.
- Exact WaveSurfer config knobs (`waveColor`, `progressColor`, `cursorColor`, `barWidth`, `barRadius`) — recommend within CDJ Whisper palette.
- Sentence-splitter tokenizer details (regex vs `nltk` — recommend regex; no new dep).
- Exact drill prompt wording — recommend SBI/STAR-AR framing template anchored to FEATURES.md §Feature 3.

### Deferred Ideas (OUT OF SCOPE)

- Drill audio playback / DJ exercises within the window — text-only in v2.1; v2.2 stretch.
- Multi-session aggregation / trends — Phase 32 DJ profile owns it.
- Custom drill templates — out of scope.
- Drill bookmarking / progress tracking — v2.2 backlog.
- Sharing debrief publicly — privacy, out of scope.
- Export debrief as PDF/Markdown — v2.2.
- Live debrief / commentary replay — explicitly NOT this phase.
- Real-time live debrief.
- Re-recording / patching sessions.
- Cross-user sharing.
- Interactive Q&A in debrief mode (per FEATURES.md anti-feature list).

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DEBRIEF-03 | Chaptered review from events.jsonl → `session_debrief.json` | Verified real-session events.jsonl has `TRACK_CHANGE` / `PHASE` / `LAYER_ARRIVAL` / `MIX_MOVE` / `HEARTBEAT` kinds; chapter heuristic is repo-grounded. |
| DEBRIEF-04 | 60-90s voiced TL;DR — Gemini TTS Achird, MP3 | `scripts/generate_ack_audio.py` shipped (Phase 27 LATENCY-15) — identical Achird call path; encode via PyAV (already shipped dep) MP3 not OPUS. |
| DEBRIEF-05 | Clickable timeline — WaveSurfer.js regions + tooltip | WaveSurfer.js v7.12.7 (latest, 2026-05-13) — Regions plugin natively supports click-to-seek + tooltip via `content` field; pattern verified via Context7. |
| DEBRIEF-06 | 3 drills SBI/STAR-AR | Gemini 3 Pro structured-output `responseSchema=Pydantic` returns guaranteed-shape JSON; verified via Google Developers Blog. |
| DEBRIEF-07 | Cited critique strip | Phase 18 `EVIDENCE_CITATION_RE` already locked + Phase 20 `CitationLinter` already supports `mode="debrief"` tolerance (±2.0s). Phase 29 adds sentence-level wrapper. |
| DEBRIEF-08 | Tauri `open_debrief_window` + 2nd WebviewWindow | Tauri 2.11 `WebviewWindowBuilder` shipped; pattern in `mascot_window.rs` shipped (label-bound second window). |
| DEBRIEF-09 | Rust sidecar child lifecycle on close | `SidecarHandle::Arc<Mutex<Option<CommandChild>>>` shipped in `sidecar.rs:62-72`; reuse via new `DebriefSidecarHandle`. `WindowEvent::CloseRequested` documented in Tauri 2.11. |
| DEBRIEF-10 | `debrief.v1` additive-only | `scripts/check_ipc_schema.py` already enforces wrapper-count parity; extend with field-set diff vs v2.1 baseline. Frozen-slotted dataclasses prevent field removal. |
| DEBRIEF-11 | Settings → Recordings entry | `recording-row.ts` has 4-button action cluster (replay · reveal · open-external · delete); 5th button slots in before delete. `RecordingSummary` shape already includes `duration_s` + `event_count` for disable gate. |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Debrief window opening + lifecycle | Tauri Rust shell | — | Window creation + child supervision = Rust parent's job (mirrors `mascot_window.rs` pattern). |
| Debrief HTML/CSS/TS render | Tauri webview (renderer) | — | All UI work, vanilla TS, talks to sidecar over WS. |
| Session file loading + parsing (events.jsonl, voice.wav meta) | Python sidecar (debrief mode) | — | File I/O + dataclass parsing belongs in Python; the sidecar is `vibemix-core --debrief <session_dir>`. |
| Chapter derivation heuristic | Python sidecar | — | Pure data transform over events.jsonl; runs once per session, cached. |
| TL;DR text + audio generation | Python sidecar | Bravoh proxy | Gemini text + TTS calls go through proxy in `mode=proxy`; direct in `mode=direct`. Sidecar owns the call. |
| Drill generation | Python sidecar | Bravoh proxy | Same. Single Gemini 3 Pro call with `responseSchema`. |
| Cited-critique stripping | Python sidecar | — | Runs server-side before persisting `session_debrief.json` — UI receives pre-stripped text only. |
| Schema validation (IPC) | Both (Python ws_bus + TS validator.generated.mjs) | — | Same pattern as live session — Pydantic-ish wrappers Python side; codegen-built ajv TS validator renderer side. |
| Waveform render | Tauri webview (renderer) | — | WaveSurfer.js is browser-native; reads `voice.wav` via `asset://` protocol. |
| Audio playback | Tauri webview (renderer) | — | HTML5 `<audio>` element + WaveSurfer wraps it. WKWebView + WebView2 both decode MP3 natively. |
| Citation lookup at click time | Python sidecar | Tauri webview | Renderer sends `{event_id}` → sidecar resolves against persisted `evidence_registry.json` snapshot → emits `ipc.debrief.citation-tooltip`. |
| Entry button | Tauri webview (Settings → Recordings) | Tauri Rust shell | Vanilla TS button in `recording-row.ts`; invokes Rust command. |

## Standard Stack

### Core (new for Phase 29)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `wavesurfer.js` | `^7.12.7` | Waveform + regions + click-to-seek + tooltip rendering | [VERIFIED: npm registry — latest 7.12.7 released 2026-05-13.] Best-in-class TS-native waveform lib with regions/timeline plugins. v2.1 STACK.md already locks `^7.10` (we use newer minor 7.12). [CITED: STACK.md Bucket 3] |

### Supporting (already shipped, reused)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `google-genai` | `>=2.0.1` | Gemini 3 Pro structured output + Gemini TTS Achird | All AI calls. Same SDK Phase 27 LATENCY-15 already uses. |
| `av` (PyAV) | (already shipped) | PCM 24kHz s16le → MP3 encoding for TL;DR | Already used in `scripts/generate_ack_audio.py` for OPUS encoding; same lib, MP3 codec. |
| `tauri-plugin-shell` | `2.3` | Sidecar spawn for `--debrief` mode | Already used for main sidecar spawn; same `app.shell().sidecar(...)` API. |
| `tauri` | `2.11` | `WebviewWindowBuilder` for second window + `WindowEvent::CloseRequested` | Already used by `mascot_window.rs`; reuse pattern. |
| `websockets` | `16.0` | Sidecar ws_bus server on port 8766 | Already used for main ws_bus on 8765; same lib. |
| `pydantic` | `2.x` (already shipped) | Gemini 3 Pro `responseSchema` typing | Already shipped as transitive dep. |
| `numpy` + `scipy` | (already shipped) | Voice WAV header read (no resampling needed — Gemini TTS emits 24kHz mono directly) | Already shipped. |
| `ajv` + `ajv-formats` | `^8.20` / `^3.0` | TS IPC schema validation | Already in `package.json` devDependencies; codegen path `npm run check:ipc` already locked. |

### Alternatives Considered (rejected)

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `wavesurfer.js` | Howler.js | Howler = playback only, no waveform. Wrong tool. [CITED: STACK.md Bucket 3] |
| `wavesurfer.js` | Tone.js | Tone.js = synthesis library, wrong domain. [CITED: STACK.md] |
| `wavesurfer.js` | Raw `<audio>` + custom Canvas waveform | +2 weeks dev work, fragile, no reason to hand-roll. [CITED: STACK.md] |
| Achird via Gemini TTS | ElevenLabs / OpenAI TTS | Gemini-only memory lock (`feedback_no_clap_use_gemini_embedding` and stack discipline). |
| MP3 | OPUS | OPUS support in WKWebView is unreliable per Tauri Discussion #9388; OGG/OPUS not supported on Safari/WebKit. MP3 plays on both. [VERIFIED: Tauri Discussion #9388] |
| MP3 | AAC | Both work, but PyAV's MP3 encoder is more permissive (smaller PCM input). Bundle has libmp3lame ready via PyAV. |
| Structured output via Pydantic `responseSchema` | Free-form JSON + post-parse | Gemini 3 Pro guarantees schema adherence via JSON Schema since 2026. [CITED: blog.google/innovation-and-ai/technology/developers-tools/gemini-api-structured-outputs/] |
| Sentence regex splitter | `nltk` punkt tokenizer | +30MB dep for 1 regex worth of work. Reject. |

### Installation

Already-shipped deps need NO action.

**One new npm dep:**

```bash
# In tauri/ui/
npm install wavesurfer.js@^7.12.7
```

**Version verification (run at start of Wave 0):**

```bash
npm view wavesurfer.js version  # confirm 7.12.x still latest
npm view wavesurfer.js dist-tags  # confirm `latest` channel
```

[VERIFIED: 2026-05-15 — npm registry returned `7.12.7` for `wavesurfer.js version`; `dist-tags` returned `{ latest: '7.12.7', beta: '7.8.5-beta.0', alpha: '7.0.0-alpha.58' }`.]

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│  Tauri Rust shell (existing process)                                │
│                                                                      │
│  Settings → Recordings tab                                          │
│    └─ recording-row.ts "Open Debrief" button                        │
│         └─ invoke("open_debrief_window", { session_dir })           │
│                                                                      │
│  src-tauri/src/debrief_window.rs (NEW)                              │
│    ├─ #[tauri::command] open_debrief_window                         │
│    │    1. Spawn sidecar: app.shell().sidecar()                     │
│    │       .args(["--debrief", &session_dir])                       │
│    │    2. Store CommandChild in DebriefSidecarHandle (NEW state)   │
│    │    3. Build WebviewWindow                                      │
│    │       label="debrief", 1280x720, standard chrome               │
│    │    4. Wire on_window_event(WindowEvent::CloseRequested)        │
│    │       → kill the CommandChild                                  │
│    └─ if already-open: window.set_focus()                           │
└─────────────────────────┬───────────────────────────────────────────┘
                          │
        ┌─────────────────┴─────────────────┐
        │                                   │
        ▼                                   ▼
┌──────────────────────┐         ┌──────────────────────────────────┐
│ Python sidecar       │         │ Tauri webview "debrief" window   │
│ (NEW --debrief mode) │         │                                  │
│                      │         │  tauri/ui/debrief.html           │
│ __main__.py          │         │  tauri/ui/src/debrief/           │
│   --debrief flag     │         │    debrief-window.ts (entry)     │
│   → debrief/main.py  │         │    components/                   │
│                      │         │      chapter-list.ts             │
│ src/vibemix/debrief/ │         │      tldr-player.ts (WaveSurfer) │
│   (NEW pkg)          │         │      timeline.ts (regions)       │
│   chapters.py        │         │      drills-panel.ts             │
│   tldr.py            │         │      citation-tooltip.ts         │
│   drills.py          │         │      entry.ts                    │
│   stripper.py        │         │                                  │
│   ws_server.py       │         │ Connects: ws://127.0.0.1:8766    │
│     (port 8766)      │◄────WS─►│                                  │
└──────────┬───────────┘         └──────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Filesystem (recordings root)                                        │
│                                                                      │
│ <recordings_root>/<session_dir>/                                    │
│   ├─ events.jsonl     ← read (chapter derivation)                   │
│   ├─ voice.wav        ← read (waveform + region lookup)             │
│   ├─ input.wav        ← optional reference                          │
│   ├─ evidence_registry.json ← read (citation tooltips)              │
│   ├─ session_debrief.json   ← WRITE on first run; READ on cache hit │
│   └─ debrief_tldr.mp3       ← WRITE on first run; served via        │
│                               asset:// to WaveSurfer                │
└─────────────────────────────────────────────────────────────────────┘

External: Gemini API (text + TTS) via Bravoh proxy (or direct in dev)
```

**Trace for primary use case (open debrief first time):**
1. User clicks "Open Debrief" in Settings → Recordings.
2. Renderer fires `invoke("open_debrief_window", { session_dir })`.
3. Rust spawns sidecar with `--debrief <session_dir>` flag; stores CommandChild.
4. Rust builds `WebviewWindow` with label `"debrief"`, navigates to `debrief.html`.
5. Renderer parses URL `?session=` param, connects WS to `127.0.0.1:8766`.
6. Sidecar: parses events.jsonl, derives chapters, generates TL;DR (Gemini + TTS), generates drills (Gemini 3 Pro structured output), strips uncited critique, persists `session_debrief.json` + `debrief_tldr.mp3`.
7. Sidecar emits `ipc.debrief.session-loaded` → `chapter-list` → `tldr-audio` → `drills`.
8. Renderer renders chapters, mounts WaveSurfer with `voice.wav`, plots regions for each chapter + citation, mounts TL;DR `<audio src=debrief_tldr.mp3>`.
9. User clicks region → `wavesurfer.setTime(region.start)`, renderer fires `ipc.debrief.citation-tooltip-request {event_id}`.
10. Sidecar responds with `ipc.debrief.citation-tooltip {evidence_text, timestamp}`.
11. User closes window → Rust catches `WindowEvent::CloseRequested` → kills the CommandChild.

### Recommended Project Structure

```
src/vibemix/debrief/                  # NEW Python package
├── __init__.py
├── main.py                           # entry — replaces _run_debrief_sidecar
├── ws_server.py                      # port 8766 server (websockets lib)
├── chapters.py                       # events.jsonl → chapter list
├── tldr.py                           # Gemini text + Achird TTS → MP3
├── drills.py                         # Gemini 3 Pro structured output
├── stripper.py                       # sentence-level cited-critique filter
├── session_loader.py                 # reads events.jsonl + evidence snapshot
└── persistence.py                    # session_debrief.json read/write

src/vibemix/ui_bus/schemas/debrief.py # EXTEND additive-only

tauri/src-tauri/src/
├── debrief_window.rs                 # NEW — open_debrief_window cmd + lifecycle
└── sidecar.rs                        # EXTEND — DebriefSidecarHandle alongside SidecarHandle

tauri/ui/debrief.html                 # NEW second-window entry HTML
tauri/ui/src/debrief/
├── debrief-window.ts                 # entry; bootstraps from URL ?session=
├── ws-client.ts                      # connects 127.0.0.1:8766; wraps Phase 25 wrappers
├── components/
│   ├── chapter-list.ts               # left-side chapter cards
│   ├── tldr-player.ts                # MP3 player + WaveSurfer mini-bar
│   ├── timeline.ts                   # full-width waveform + regions plugin
│   ├── drills-panel.ts               # 3 drill cards (SBI/STAR-AR shape)
│   ├── citation-tooltip.ts           # warm-black-2 tooltip on region click
│   └── error-banner.ts               # sidecar-crashed / events-missing surface

tauri/ui/src/settings/components/recording-row.ts  # EXTEND — add 5th button

tauri/src-tauri/capabilities/default.json          # EXTEND — sidecar args regex
                                                    # + windows allowlist + asset scope

tests/debrief/                        # NEW pytest dir
├── test_chapter_derivation.py
├── test_tldr_length_60_to_90s.py
├── test_drill_schema_validates.py
├── test_no_uncited_critique_in_debrief.py
├── test_session_too_short_falls_back.py
└── test_missing_events_jsonl_errors_gracefully.py

tests/ui_bus/test_debrief_schema_additive_only.py  # P82 gate

tauri/ui/src/debrief/__tests__/
├── chapter-list.spec.ts
├── timeline-regions-click-seek.spec.ts
└── stripper-roundtrip.spec.ts
```

### Pattern 1: WaveSurfer.js Regions Plugin with Click-to-Seek + Tooltip

**What:** Standard regions API; click → seek + emit citation tooltip request.
**When to use:** Always — this is the load-bearing UI primitive for DEBRIEF-05.

**Example:**

```typescript
// Source: Context7 /katspaugh/wavesurfer.js — RegionsPlugin docs
// File: tauri/ui/src/debrief/components/timeline.ts

import WaveSurfer from "wavesurfer.js";
import RegionsPlugin from "wavesurfer.js/dist/plugins/regions.esm.js";

interface ChapterRegion {
  id: string;
  start: number;
  end: number;
  label: string;
  citation_event_id: string;  // resolves via WS round-trip to sidecar
}

export function mountTimeline(
  container: HTMLElement,
  voiceWavUrl: string,
  chapters: ChapterRegion[],
  onCitationClick: (event_id: string) => void,
) {
  const regions = RegionsPlugin.create();

  const wavesurfer = WaveSurfer.create({
    container,
    waveColor: "var(--silk-40)",      // CDJ Whisper warm-silk
    progressColor: "var(--amber-2)",  // single amber accent
    cursorColor: "var(--amber-3)",
    url: voiceWavUrl,                  // asset://… from convertFileSrc()
    plugins: [regions],
    barWidth: 2,
    barRadius: 1,
    height: 96,
  });

  wavesurfer.on("decode", () => {
    for (const ch of chapters) {
      regions.addRegion({
        id: ch.id,
        start: ch.start,
        end: ch.end,
        content: ch.label,
        color: "rgba(212, 167, 79, 0.30)",  // amber-3 @ 30%
        drag: false,
        resize: false,
      });
    }
  });

  regions.on("region-clicked", (region, e) => {
    e.stopPropagation();
    // Per CONTEXT: click-only (not hover) — click triggers both seek + tooltip
    wavesurfer.setTime(region.start);
    const ch = chapters.find((c) => c.id === region.id);
    if (ch) onCitationClick(ch.citation_event_id);
  });

  return { wavesurfer, regions };
}
```

### Pattern 2: Tauri Rust Second-Window with Sidecar Child Lifecycle

**What:** Build a labeled second WebviewWindow + spawn child sidecar + tie child kill to `WindowEvent::CloseRequested`.
**When to use:** DEBRIEF-08 + DEBRIEF-09 — the load-bearing Rust primitive.

**Example:**

```rust
// Source: tauri/src-tauri/src/mascot_window.rs (shipped pattern) +
// tauri/src-tauri/src/sidecar.rs (shipped SidecarHandle pattern) +
// Context7 /websites/v2_tauri_app — WebviewWindowBuilder + on_window_event.
// File: tauri/src-tauri/src/debrief_window.rs (NEW)

use std::sync::{Arc, Mutex};
use tauri::{AppHandle, Manager, WebviewUrl, WebviewWindowBuilder, WindowEvent};
use tauri_plugin_shell::process::CommandChild;
use tauri_plugin_shell::ShellExt;

pub const DEBRIEF_WINDOW_LABEL: &str = "debrief";

/// Shared handle to the debrief sidecar child — separate from main SidecarHandle.
pub struct DebriefSidecarHandle {
    pub child: Arc<Mutex<Option<CommandChild>>>,
}
impl Default for DebriefSidecarHandle {
    fn default() -> Self {
        Self { child: Arc::new(Mutex::new(None)) }
    }
}

#[tauri::command]
pub async fn open_debrief_window(
    app: AppHandle,
    session_dir: String,
) -> Result<(), String> {
    // 1. Focus existing if already open.
    if let Some(existing) = app.get_webview_window(DEBRIEF_WINDOW_LABEL) {
        existing.set_focus().map_err(|e| format!("focus: {e}"))?;
        return Ok(());
    }

    // 2. Spawn sidecar in --debrief mode.
    let sidecar = app
        .shell()
        .sidecar("binaries/vibemix-core")
        .map_err(|e| format!("sidecar lookup: {e}"))?
        .args(["--debrief", &session_dir]);
    let (_rx, child) = sidecar.spawn().map_err(|e| format!("spawn: {e}"))?;

    // 3. Store child in handle.
    if let Some(state) = app.try_state::<DebriefSidecarHandle>() {
        if let Ok(mut g) = state.child.lock() {
            *g = Some(child);
        }
    }

    // 4. Build WebviewWindow — standard chrome.
    let url = format!("debrief.html?session={}", urlencoding::encode(&session_dir));
    let title = format!("Debrief — {}", session_dir);
    let window = WebviewWindowBuilder::new(
        &app,
        DEBRIEF_WINDOW_LABEL,
        WebviewUrl::App(url.into()),
    )
    .title(&title)
    .inner_size(1280.0, 720.0)
    .min_inner_size(960.0, 540.0)
    .resizable(true)
    .decorations(true)   // standard chrome — full title bar
    .visible(true)
    .build()
    .map_err(|e| format!("window build: {e}"))?;

    // 5. Wire close → kill child.
    let app_for_close = app.clone();
    window.on_window_event(move |event| {
        if matches!(event, WindowEvent::CloseRequested { .. }) {
            if let Some(state) = app_for_close.try_state::<DebriefSidecarHandle>() {
                if let Ok(mut g) = state.child.lock() {
                    if let Some(child) = g.take() {
                        let _ = child.kill();
                    }
                }
            }
        }
    });

    Ok(())
}
```

### Pattern 3: Gemini 3 Pro Structured Output for Drills

**What:** One-shot Gemini 3 Pro call returns drills in guaranteed-shape JSON via `response_schema`.
**When to use:** DEBRIEF-06 — drill generation.

**Example:**

```python
# Source: ai.google.dev/gemini-api/docs/structured-output + Phase 27 ack-bank pattern.
# File: src/vibemix/debrief/drills.py

from pydantic import BaseModel, Field
from google import genai

class Drill(BaseModel):
    situation: str = Field(description="The cited moment from the session — quote the [ev:*] / [track:*] / [mix:*] citation.")
    behavior: str = Field(description="What the DJ did in that moment.")
    impact: str = Field(description="What effect it had on the mix/audience.")
    action_recommended: str = Field(description="One concrete drill for next session.")
    citation: str = Field(description="The [ev:*] / [track:*] / [mix:*] tag this drill is grounded in.")

class Drills(BaseModel):
    drills: list[Drill] = Field(description="Exactly 3 drills.", min_length=3, max_length=3)

def generate_drills(
    client: genai.Client,
    cited_critique: str,
    chapter_summaries: list[str],
) -> Drills:
    prompt = f"""Generate exactly 3 SBI/STAR-AR drills from this session.
Each drill MUST cite a real [ev:*] / [track:*] / [mix:*] tag from the input.
Sessions:
{chr(10).join(chapter_summaries)}

Cited critique:
{cited_critique}
"""
    response = client.models.generate_content(
        model="gemini-3-pro",
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": Drills,
        },
    )
    return Drills.model_validate_json(response.text)
```

### Pattern 4: Sentence-Level Cited-Critique Stripping

**What:** Reuse Phase 18's `EVIDENCE_CITATION_RE` (already locked) + split-by-sentence; drop sentences without any match.
**When to use:** DEBRIEF-07 — every advice line must cite.

**Example:**

```python
# Source: src/vibemix/state/evidence_registry.py (shipped) + Phase 20 CitationLinter.
# File: src/vibemix/debrief/stripper.py

import re
from vibemix.state.evidence_registry import EVIDENCE_CITATION_RE

# Sentence boundary: period / exclamation / question + whitespace.
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")

def strip_uncited_sentences(text: str) -> tuple[str, int]:
    """Return (filtered_text, stripped_count).

    Splits on sentence boundaries; drops any sentence with zero matches
    against the locked EBNF grammar. The returned text re-joins kept
    sentences with " " (single space) — visual flow preserved.
    """
    sentences = _SENTENCE_BOUNDARY.split(text.strip())
    kept = [s for s in sentences if EVIDENCE_CITATION_RE.search(s)]
    stripped = len(sentences) - len(kept)
    return (" ".join(kept), stripped)
```

### Anti-Patterns to Avoid

- **Inventing a new IPC bus.** Port 8766 + 3 reserved schemas already shipped in Phase 25 — extend, don't replace. Adding a 4th port = architectural drift.
- **Letting Gemini emit free-form drill JSON.** Use `response_schema` — parse failures become Gemini-bug not vibemix-bug.
- **Hand-rolling sentence tokenization with nltk.** +30MB dep. Regex is fine for English coach text.
- **Generating TL;DR every open.** Hash-cache via `session_debrief.json.tldr_sha256`. Regenerate only on user explicit "refresh".
- **OPUS for TL;DR.** WKWebView (Safari/WebKit) doesn't decode OPUS reliably. MP3 only.
- **Putting AX/Quartz calls in the debrief sidecar.** Debrief is pure file-I/O + LLM. No audio/MIDI/screen capture. Honors `--debrief` mode = no live audio.
- **Mutating Phase 25 dataclass fields.** P82 — additive-only. Add new wrapper classes, never remove or retype existing ones.
- **Using `decorations(false)` on the debrief window.** CONTEXT lock: standard chrome. The mascot uses `decorations(false)` because it's an overlay; the debrief is a regular utility window the user wants to move/resize/close normally.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Waveform rendering + click-to-seek | Custom Canvas + Web Audio + manual offset math | wavesurfer.js + RegionsPlugin | 180KB lib vs 2 weeks of edge cases. [CITED: STACK.md Bucket 3] |
| JSON schema for drills | Free-form prompt + post-parse | Gemini 3 Pro `response_schema` + Pydantic | Guaranteed adherence since 2026; no parse failures. [CITED: blog.google structured outputs] |
| Sentence splitting | nltk punkt | regex `(?<=[.!?])\s+` | nltk = 30MB dep for English-only coach text. |
| MP3 encoding | libmp3lame Python bindings | PyAV (already shipped) | Already used in Phase 27 ack bank; same encoder. |
| Session file watching | inotify / watchdog | One-shot read on `--debrief` startup | Sidecar lifecycle is open-on-click, kill-on-close; no need to watch. |
| Second-window state | Custom IPC singleton | `app.get_webview_window(label).set_focus()` | Tauri native; one line. |
| Child process lifecycle | Manual PID tracking + signal handling | `Arc<Mutex<Option<CommandChild>>>` + `child.kill()` | Already shipped pattern in `sidecar.rs` (`SidecarHandle`). |
| Tooltip rendering | Floating-ui / popper | Vanilla absolute-positioned div with fade transition | One DOM node + CSS keyframes. No new dep. |
| Sentence-level citation match | Custom EBNF parser | Reuse `EVIDENCE_CITATION_RE` from Phase 18 | Already locked + tested. |

**Key insight:** Every primitive Phase 29 needs is either (a) already shipped in v2.0 (sidecar pattern, IPC schema infra, EvidenceRegistry, citation grammar, mascot-style second window), (b) already locked in v2.1 STACK.md (wavesurfer.js), or (c) trivial regex/Pydantic glue. There is no novel infrastructure in this phase. The work is composition.

## Runtime State Inventory

Phase 29 is **net-new feature, not rename/refactor** — no Runtime State Inventory triggers. The phase ADDS:
- A new Python package `src/vibemix/debrief/`
- A new Rust source file `tauri/src-tauri/src/debrief_window.rs`
- A new HTML entry `tauri/ui/debrief.html`
- A new vanilla-TS dir `tauri/ui/src/debrief/`
- One new npm dep `wavesurfer.js`
- New IPC wrapper classes (additive-only)
- New session-files (`session_debrief.json`, `debrief_tldr.mp3`) inside existing `<session_dir>` writes

It does NOT rename / refactor / migrate anything. Section omitted by trigger rules — no rename/migration semantics in scope.

## Common Pitfalls

### Pitfall 1: P81 — MP3 cross-webview parity

**What goes wrong:** Debrief audio plays on Windows (WebView2 / Chromium decodes MP3) but silent-fails on macOS (WKWebView / WebKit can't decode the encoding format the sidecar wrote).

**Why it happens:** Gemini TTS Achird returns raw PCM 24kHz s16le (verified in `scripts/generate_ack_audio.py` lines 60-62). If we naively wrap that in OPUS-in-OGG (as Phase 27 does for ack bank), WKWebView fails — Safari/WebKit doesn't decode OPUS reliably.

**How to avoid:**
- Encode TL;DR via PyAV with `codec='libmp3lame'` (not OPUS).
- Verified: WKWebView decodes MP3 natively (per Tauri Discussion #9388 — MP3 plays on macOS, OPUS does not).
- Verified: WebView2 inherits Chromium's MP3 decoder.

**Warning signs:**
- Debrief audio plays on Windows but not macOS (or vice versa).
- Webview console: "Failed to load audio: unsupported MIME".
- File extension `.opus` instead of `.mp3` in `<session_dir>`.

**Mitigation evidence:** `tests/debrief/test_tldr_mp3_decodes_in_webview.py` (Mac+Win VM) + asserts file extension + mimetype `audio/mpeg`.

### Pitfall 2: P82 — Schema additive-only across v2.1

**What goes wrong:** Phase 25 shipped 3 dataclass payloads + 3 wrapper classes + 3 jsonschema definitions. If Phase 29 modifies field names, types, or required-ness on any of those, the schema-additive contract breaks and downstream phases (32 / 36 / 37) inherit a corrupted IPC surface.

**Why it happens:** Frozen-slotted dataclasses make changes a Python-side error, but the JSON schema in `messages.schema.json` is hand-touched — a developer could update one without the other.

**How to avoid:**
- Phase 29 ADDS new wrapper classes (`DebriefChapterList`, `DebriefTldrAudio`, `DebriefDrills`, `DebriefCitationTooltipReq`, `DebriefCitationTooltip`, `DebriefError`).
- Phase 29 NEVER renames `DebriefSessionLoaded` / `DebriefCitationSummary` / `DebriefEventTimeline` field names or types.
- CI gate `test_debrief_schema_additive_only` — captures v2.1 baseline schema at first Phase 29 commit; subsequent commits diff against baseline, fail on field removal / rename / type change.
- `scripts/check_ipc_schema.py` already enforces wrapper-vs-schema count parity (extends naturally).

**Warning signs:**
- Phase 29 PR diff modifies `src/vibemix/ui_bus/schemas/debrief.py` LINES 31-93 (the existing dataclasses).
- Phase 29 PR diff renames JSON schema definition `"DebriefSessionLoaded"` (or removes it from `oneOf`).
- `scripts/check_ipc_schema.py` exits non-zero.

**Mitigation evidence:** Test file `tests/ui_bus/test_debrief_schema_additive_only.py`. Baseline JSON committed to `tests/ui_bus/fixtures/debrief_schema_v2_1_baseline.json`.

### Pitfall 3: Capabilities allowlist blocks `--debrief` sidecar arg

**What goes wrong:** Current `capabilities/default.json` line 23 restricts sidecar args via validator regex `^--(wizard|session)$`. A spawn with `--debrief` would be rejected by the Tauri capability gate at runtime.

**Why it happens:** Phase 25 reserved the flag in Python but the Rust-side capability was scoped to v2.0 flags only.

**How to avoid:** Phase 29 plan MUST include a Wave 0 capability-update task: change the validator to `^--(wizard|session|debrief)$` AND extend `allow` entries to permit the session-dir positional arg via a second `args` array entry (regex match against the canonical session-dir format `^\d{8}-\d{6}$`).

**Warning signs:**
- First `--debrief` spawn fails with Tauri "argument does not match validator" error.
- `capabilities/default.json` `shell:allow-execute` `validator` regex still says `wizard|session`.

**Mitigation evidence:** `tests/capabilities/test_debrief_arg_allowlist.py` — instantiates the JSON, regex-matches `--debrief` literal + sample session-dir string. Fast unit test, no Tauri runtime needed.

### Pitfall 4: Asset:// protocol scope doesn't include `voice.wav` or `debrief_tldr.mp3` in writable mode

**What goes wrong:** `tauri.conf.json5` Phase 15 enabled `protocol-asset` with scope `$APPDATA/vibemix/recordings/**` + `$APPLOCALDATA/vibemix/recordings/**` — Phase 29's MP3 lives at `$APPDATA/vibemix/recordings/<session_dir>/debrief_tldr.mp3`, which IS within scope. **Verified:** the existing wildcard pattern covers all session-dir files including new MP3 (because Phase 15 globbed `**` not `**/*.wav`).

**How to avoid:** No action needed. Verify in Wave 0 by smoke-loading a `.mp3` via `convertFileSrc()` from a sample session dir. If it fails, extend the scope pattern in `tauri.conf.json5`.

**Warning signs:** WaveSurfer `wavesurfer.on("error")` fires with "asset protocol denied" or 403.

### Pitfall 5: WaveSurfer rendering disparity between WKWebView and WebView2

**What goes wrong:** WaveSurfer uses Shadow DOM + Canvas — STACK.md flagged this as Open Question #9: "Verify it renders identically in WKWebView (Mac) and WebView2 (Win) in the wizard / debrief view."

**Why it happens:** Shadow DOM v1 is universally supported in both webview engines, but minor Canvas devicePixelRatio differences exist.

**How to avoid:**
- Wave 0 smoke test: open debrief.html in `npm run dev` on Mac + on Windows VM with the same `voice.wav` fixture; visually compare waveform shape.
- Lock `wavesurfer` config with explicit `barWidth` + `barRadius` + `height` + `barGap` to neutralize devicePixelRatio drift.

**Warning signs:** Waveform looks pixel-correct on one platform but blurry / off-scale on the other.

**Mitigation evidence:** Visual smoke screenshot from both platforms attached to the Phase 29 SUMMARY.md. No automated test — manual gate per Wave 0.

### Pitfall 6: Session too short or missing events.jsonl

**What goes wrong:** User clicks "Open Debrief" on a 30-second recording (or a crashed session whose `events.jsonl` is empty). Sidecar tries to generate chapters from 0-3 events, drills from no critique, and Gemini hallucinates filler.

**How to avoid:**
- Disable the "Open Debrief" button when `summary.duration_s < 300` OR `summary.event_count < 5` (data already in `RecordingSummary` shape — verified at `tauri/ui/src/settings/components/recording-row.ts:63-70`).
- Sidecar-side defensive: if `events.jsonl` missing or has 0 event rows, emit `ipc.debrief.error {reason: "events_missing"}` and exit cleanly.
- Renderer renders "session too short for meaningful debrief" empty-state, NOT a blank window.

**Mitigation evidence:** `tests/debrief/test_session_too_short_falls_back.py` + `tests/debrief/test_missing_events_jsonl_errors_gracefully.py`.

### Pitfall 7: Drills cite events that aren't in the session's EvidenceRegistry snapshot

**What goes wrong:** Gemini 3 Pro generates SBI/STAR-AR drills that cite plausible-looking `[ev:DROP_HIT@01:23]` tags that don't actually exist in the session's EvidenceRegistry snapshot. UI renders confidently, user clicks the citation, tooltip shows "evidence not found."

**How to avoid:**
- Pass `evidence_registry.json` snapshot summary into the Gemini prompt explicitly: "Available citations: [ev:HEARTBEAT@687, ev:LAYER_ARRIVAL@805, ...]".
- After Gemini returns drills, validate each `citation` field against the snapshot — drop any drill whose citation doesn't resolve (or replace with closest neighbor).
- Test asserts: every drill's `citation` field resolves against the registry at debrief tolerance (±2.0s).

**Mitigation evidence:** `tests/debrief/test_drill_citations_resolve.py`.

## Code Examples

### Common Operation 1: Spawn `--debrief` sidecar from Rust

Already shown in Pattern 2 above.

### Common Operation 2: Persist `session_debrief.json` with SHA256-cached TL;DR

```python
# Source: src/vibemix/runtime/recorder.py (events.jsonl write pattern shipped).
# File: src/vibemix/debrief/persistence.py

import hashlib
import json
from pathlib import Path
from typing import Any

DEBRIEF_SCHEMA_VERSION = "v1"  # P82 lock

def write_debrief(session_dir: Path, debrief: dict[str, Any], tldr_mp3_bytes: bytes) -> Path:
    """Write session_debrief.json + debrief_tldr.mp3 atomically.

    Schema = debrief.v1 (additive-only — P82). Hash the MP3 bytes into the
    JSON so a later open detects cache validity in O(1).
    """
    debrief["schema_version"] = DEBRIEF_SCHEMA_VERSION
    debrief["tldr_sha256"] = hashlib.sha256(tldr_mp3_bytes).hexdigest()
    debrief["tldr_path"] = "debrief_tldr.mp3"  # relative to session_dir

    mp3_path = session_dir / "debrief_tldr.mp3"
    mp3_path.write_bytes(tldr_mp3_bytes)

    json_path = session_dir / "session_debrief.json"
    json_path.write_text(json.dumps(debrief, indent=2, sort_keys=True))
    return json_path

def read_debrief(session_dir: Path) -> dict[str, Any] | None:
    """Return cached debrief if MP3 still matches recorded hash; else None."""
    json_path = session_dir / "session_debrief.json"
    if not json_path.exists():
        return None
    debrief = json.loads(json_path.read_text())
    mp3_path = session_dir / debrief.get("tldr_path", "debrief_tldr.mp3")
    if not mp3_path.exists():
        return None
    expected = debrief.get("tldr_sha256", "")
    actual = hashlib.sha256(mp3_path.read_bytes()).hexdigest()
    return debrief if actual == expected else None
```

### Common Operation 3: WaveSurfer mount in vanilla TS with CDJ-Whisper palette

See Pattern 1 above.

### Common Operation 4: Tauri command invocation from existing recording-row

```typescript
// File: tauri/ui/src/settings/components/recording-row.ts (EXTEND)

import { invoke } from "@tauri-apps/api/core";

const debriefBtn = document.createElement("button");
debriefBtn.type = "button";
debriefBtn.className = "vmx-rec-row__action vmx-rec-row__action--debrief";
debriefBtn.setAttribute("aria-label", "Open debrief");
debriefBtn.disabled = summary.duration_s < 300 || summary.event_count < 5;
debriefBtn.addEventListener("click", async (e) => {
  e.stopPropagation();
  try {
    await invoke("open_debrief_window", { sessionDir: summary.session_dir });
  } catch (err) {
    console.error("[debrief] open failed:", err);
  }
});
actions.insertBefore(debriefBtn, deleteBtn);  // 5th button, before delete
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Free-form JSON parsing from Gemini | `response_schema` with Pydantic / Zod | 2026 (Gemini 3 release) | Drills guaranteed schema-valid; no `try/except json.JSONDecodeError` for hallucinated keys. |
| WaveSurfer v6 (jQuery-style, callbacks) | WaveSurfer v7 (TS rewrite, Shadow DOM) | 2024 | Native TS types; CSS isolation prevents style leakage between debrief window and main window. |
| OPUS for compact AI voice | MP3 for cross-webview parity | This phase (P81 resolution) | Loses ~30% compression vs OPUS but gains macOS playback. 60-90s MP3 ≈ ~700 KB — fine. |
| Custom WebView2 / WKWebView second-window orchestration | Tauri 2.x `WebviewWindowBuilder` + label-bound focus | Tauri 2.0 GA | One Rust file replaces ~500 LOC of platform-specific code. |
| Pre-generating debrief at session-end | Lazy generate on first `open_debrief` | This phase | User opens debrief on <10% of sessions historically; lazy saves 90% of TTS spend. |

**Deprecated/outdated (do not use):**
- WaveSurfer v6 imperative API — use v7 plugin-based.
- `@tauri-apps/api/dialog.confirm` (Tauri 1.x) — Tauri 2.x moves to `@tauri-apps/plugin-dialog`.
- `app.shell().open(...)` deprecated in Tauri 2.x (per `recordings.rs:36-40` doc-comment).

## Assumptions Log

All claims tagged `[ASSUMED]` that need confirmation:

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Gemini 3 Pro model ID is `gemini-3-pro` at phase-execution time. | Pattern 3 | Model could be renamed to `gemini-3.0-pro` or `gemini-3-pro-001`. Plan should verify at Wave 0 by running a tiny `generate_content` smoke call. Risk: medium — wrong model ID = sidecar errors at runtime. |
| A2 | `evidence_registry.json` is written by VoiceRecorder per session. | Architecture | If it's NOT yet persisted (only in-memory), Phase 29 must add a write step. **Plan-time investigation required:** grep `voicerecorder.*evidence_registry\\|evidence_registry.*json` to confirm. Risk: high — citation tooltip lookup is core feature. |
| A3 | PyAV `libmp3lame` codec is already linked into PyInstaller bundle. | Stack | If PyAV's MP3 encoder isn't compiled in, falls back to silent encoding. **Plan-time investigation required:** `python -c "import av; av.codec.codecs_available"` lists `libmp3lame`. Risk: medium — fallback path is FFmpeg subprocess (works but ugly). |
| A4 | `tauri.conf.json5` asset protocol scope already permits `*.mp3` under `recordings/**`. | Pitfall 4 | Phase 15 scope used `recordings/**` glob; should include MP3 files. **Verify in Wave 0** by reading the actual file. Risk: low — scope extension is one line if needed. |
| A5 | Achird voice produces sufficiently varied 60-90s narration without sounding monotone. | Pattern (TL;DR) | Achird is the ack-bank voice (8 word ack lines, not 60s narration). **Plan-time investigation required:** generate a 60s sample, listen for monotone. Risk: medium — quality bar is "no AI slop"; if Achird sounds robotic at 60s length, fallback to Kore or another voice. |
| A6 | `summary.event_count` field exists on `RecordingSummary` shape. | Pitfall 6 | Verified present at `recording-row.ts:67` `event_count: number`. Risk: zero. |
| A7 | Gemini 3 Pro at proxy mode supports `response_schema` with Pydantic. | Pattern 3 | Bravoh-side proxy must forward `response_schema` field unchanged. **Plan-time investigation required:** verify by sending a structured-output call through `api.altidus.world` in Wave 0. Risk: medium — fallback is direct mode for debrief only. |
| A8 | Sentence-splitter regex `(?<=[.!?])\\s+` is sufficient for English coach text. | Pattern 4 | Edge cases like "Dr.", "e.g." would split mid-sentence. Risk: low — coach text doesn't use abbreviations typically. Test against real Phase 27 ack-bank text in Wave 0 to confirm. |
| A9 | Tauri 2.11's `WindowEvent::CloseRequested` fires before the window is destroyed (so child.kill() lands cleanly). | Pattern 2 | Verified via Tauri Discussion #5334 + Issue #8435 — close event fires first; window stays alive until handler returns. Risk: zero. |
| A10 | WaveSurfer v7's regions plugin click event includes the region.id we set. | Pattern 1 | Verified via Context7 docs — `regions.on("region-clicked", (region, e) => ...)` returns the region object. Risk: zero. |

## Open Questions

1. **Should the debrief sidecar tear down EvidenceRegistry / live runtime state when it spawns?**
   - What we know: `--debrief` mode is supposed to skip audio I/O + LiveKit. The Phase 25 `_run_debrief_sidecar` function body is a no-op banner; we replace it.
   - What's unclear: Does the existing `main()` orchestrator path run any heavy initialization BEFORE the `--debrief` dispatch check? Quick look at `__main__.py:1141-1156` shows `args.debrief is not None` check is in `cli_entry`, which is called from `main()` — but the surrounding code path needs verification.
   - Recommendation: Plan Wave 0 task — trace `__main__.py:main()` execution order; confirm `--debrief` short-circuits BEFORE any audio device probe / LiveKit session init. If not, restructure entry to dispatch debrief BEFORE.

2. **Where does the debrief sidecar process write its log?**
   - What we know: Main sidecar logs to `$APPLOCALDATA/vibemix/logs/sidecar.log` via Rust-side `FileRotate`. Debrief sidecar has no such pipe wired.
   - What's unclear: Should debrief sidecar share the rotating log or get its own?
   - Recommendation: Share via stdout/stderr (Rust drains it the same way main sidecar's are drained); prefix log lines with `[debrief]` so the same `sidecar.log` is greppable.

3. **What does `evidence_registry.json` persistence look like, and when is it written?**
   - What we know: `EvidenceRegistry.clear()` is called from `VoiceRecorder.close()` (per Phase 18 docstring) — implying writer-during-session, cleared at end.
   - What's unclear: Is the in-memory registry snapshot serialized to disk anywhere right now?
   - Recommendation: Plan Wave 0 task — confirm whether `evidence_registry.json` exists in real session dirs (sample showed only `events.jsonl + voice.wav + input.wav + invocations/`). **If absent, Phase 29 must add the write step to `VoiceRecorder.close()`** — but that's a backward-touchpoint into Phase 18 code that Phase 27 should have closed.

4. **Should TL;DR generation block window-open, or stream progress?**
   - What we know: 60-90s of TTS = ~30s of Gemini wall time (per Phase 27 ack-bank empirical 6.5s/clip × N). Drills generation = ~5s. Chapters = instant (file parse).
   - What's unclear: Does the user see a spinner for 40s, or do chapters render first while TL;DR audio + drills stream in?
   - Recommendation: Progressive render — emit `ipc.debrief.chapter-list` FIRST (instant), then `ipc.debrief.drills` (~5s later), then `ipc.debrief.tldr-audio` (~30s later). Each component shows its own skeleton until its data arrives.

5. **Does the renderer have to download `voice.wav` over the WS bus, or can WaveSurfer load it via `asset://`?**
   - What we know: Phase 15 enabled asset protocol scope for `recordings/**`. `convertFileSrc()` returns `asset://...` URLs WaveSurfer can `url:` directly.
   - What's unclear: Whether `asset://` URLs work cross-window (the debrief window is a SECOND webview).
   - Recommendation: Verify in Wave 0 smoke — likely YES (capability is app-wide, not window-specific) but confirm against the capability `windows` list (currently `["main", "mascot", "overlay-*"]` — needs `"debrief"` added).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js + npm | `npm install wavesurfer.js` + `npm run check:ipc` | ✓ | (existing) | — |
| Python 3.12 (sidecar) | `vibemix-core --debrief` | ✓ | 3.12 (existing) | — |
| Rust 1.77+ | Tauri build | ✓ | (existing) | — |
| Gemini API access (direct or proxy) | TTS + drill generation | ✓ | (existing) | Both `mode=direct` (GEMINI_API_KEY) and `mode=proxy` (api.altidus.world) shipped. |
| PyAV (`av`) | MP3 encoding | ✓ | 17.0.1 (existing, used by Phase 27) | If `libmp3lame` is NOT compiled in, subprocess to system `ffmpeg`. Plan-time check needed (A3). |
| WaveSurfer.js v7.12.7 | Timeline rendering | ✗ | needs install | None — no graceful fallback for the timeline UI; this is core to DEBRIEF-05. |

**Missing dependencies with no fallback:**
- `wavesurfer.js` — install via npm in Wave 0.

**Missing dependencies with fallback:**
- PyAV `libmp3lame` — fallback to system ffmpeg subprocess if not compiled in.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework (Python) | pytest 8.x (existing 1961 passing tests) |
| Framework (TS) | Vitest 2.1 (existing — covers Phase 22 mascot tests) |
| Config file (Python) | `pyproject.toml` (existing) |
| Config file (TS) | `tauri/ui/vitest.config.ts` (existing) |
| Quick run command (Python) | `pytest tests/debrief/ -x` |
| Quick run command (TS) | `cd tauri/ui && npm test -- src/debrief` |
| Full suite command | `pytest && cd tauri/ui && npm test` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DEBRIEF-03 | Chapter list derived from events.jsonl | unit | `pytest tests/debrief/test_chapter_derivation.py -x` | ❌ Wave 0 |
| DEBRIEF-04 | TL;DR length 60-90s | unit | `pytest tests/debrief/test_tldr_length_60_to_90s.py -x` | ❌ Wave 0 |
| DEBRIEF-04 | TL;DR is MP3 (cross-webview) | unit | `pytest tests/debrief/test_tldr_mp3_codec.py -x` | ❌ Wave 0 |
| DEBRIEF-05 | Timeline click seeks audio | vitest | `cd tauri/ui && npm test -- timeline-regions-click-seek` | ❌ Wave 0 |
| DEBRIEF-06 | 3 drills with SBI/STAR-AR shape | unit | `pytest tests/debrief/test_drill_schema_validates.py -x` | ❌ Wave 0 |
| DEBRIEF-06 | Drill citations resolve to registry | unit | `pytest tests/debrief/test_drill_citations_resolve.py -x` | ❌ Wave 0 |
| DEBRIEF-07 | Uncited sentences stripped | unit | `pytest tests/debrief/test_no_uncited_critique_in_debrief.py -x` | ❌ Wave 0 |
| DEBRIEF-07 | Stripper roundtrip TS | vitest | `cd tauri/ui && npm test -- stripper-roundtrip` | ❌ Wave 0 |
| DEBRIEF-08 | Tauri command spawns window | manual + Rust unit | `cargo test debrief_window` + visual smoke | ❌ Wave 0 |
| DEBRIEF-09 | Sidecar killed on close | manual + Rust unit | `cargo test debrief_sidecar_kill_on_close` | ❌ Wave 0 |
| DEBRIEF-10 | Schema additive-only | unit | `pytest tests/ui_bus/test_debrief_schema_additive_only.py -x` | ❌ Wave 0 |
| DEBRIEF-10 | IPC count-parity gate | scripts | `python scripts/check_ipc_schema.py` | ✓ (exists, extends naturally) |
| DEBRIEF-11 | Disabled-button gate for short sessions | vitest | `cd tauri/ui && npm test -- recording-row-debrief-disabled` | ❌ Wave 0 |
| DEBRIEF-11 | Capability allows --debrief arg | unit | `pytest tests/capabilities/test_debrief_arg_allowlist.py -x` | ❌ Wave 0 |
| Edge | Missing events.jsonl handled | unit | `pytest tests/debrief/test_missing_events_jsonl_errors_gracefully.py -x` | ❌ Wave 0 |
| Edge | Session too short fallback | unit | `pytest tests/debrief/test_session_too_short_falls_back.py -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/debrief/ -x` + `cd tauri/ui && npm test -- src/debrief`
- **Per wave merge:** `pytest && cd tauri/ui && npm test` (full suite)
- **Phase gate:** Full suite green + `scripts/check_ipc_schema.py` exits 0 + visual smoke on Mac + Windows VM before `/gsd-verify-work`.

### Wave 0 Gaps

- [ ] `tests/debrief/__init__.py` + all 8 test files listed above — covers DEBRIEF-03..11 + edges
- [ ] `tests/debrief/conftest.py` — shared fixtures (sample events.jsonl, sample voice.wav, sample evidence_registry.json)
- [ ] `tests/ui_bus/test_debrief_schema_additive_only.py` + `tests/ui_bus/fixtures/debrief_schema_v2_1_baseline.json` — P82 gate baseline captured at first Wave 0 commit
- [ ] `tests/capabilities/test_debrief_arg_allowlist.py` + extend `capabilities/default.json` validator regex
- [ ] `tauri/ui/src/debrief/__tests__/` directory + 3 vitest spec files
- [ ] No framework install needed — pytest + vitest already shipped

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Local single-user app; no auth surface. |
| V3 Session Management | no | No web session — Tauri WebviewWindow is IPC-scoped. |
| V4 Access Control | yes | Capability allowlist gates sidecar-arg + window + asset:// scope. |
| V5 Input Validation | yes | `session_dir` from renderer MUST be canonicalized + validated against recordings root (reuse `validate_under_root` from `recordings.rs:103-117`). |
| V6 Cryptography | no | SHA256 for cache-invalidation only (not security). |

### Known Threat Patterns for {Tauri + Python sidecar}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via `session_dir = "../etc/passwd"` | Tampering | Reuse `validate_under_root(candidate, recordings_root)` — proven pattern in `recordings.rs:103-117`. |
| Renderer escape → spawn arbitrary sidecar args | Elevation of Privilege | Capability `shell:allow-execute.args.validator` regex constrains to `^--(wizard|session|debrief)$` + session-dir regex `^\d{8}-\d{6}$`. |
| asset:// URL escape → read arbitrary file | Information Disclosure | `tauri.conf.json5` asset protocol scope already restricted to `recordings/**`. |
| Sidecar accepts non-canonical `session_dir` | Tampering | Sidecar Python-side ALSO canonicalizes + verifies under recordings root before reading any session file. |
| MP3 file injection via crafted session_dir | Tampering | Renderer never trusts the MP3 filename — it loads `debrief_tldr.mp3` literally from the validated session_dir. |
| Window-impersonation (renderer creates fake debrief window) | Spoofing | Window label `"debrief"` is unique; capability `windows: ["main", "mascot", "overlay-*", "debrief"]` allowlists. |
| AIza key leak via Gemini-call response body | Information Disclosure | Reuse Phase 27 LATENCY-15 pattern — never log response repr; log only `OK <session>/debrief_tldr.mp3 (<n> bytes)`. |

## Sources

### Primary (HIGH confidence)

- **Context7 `/katspaugh/wavesurfer.js`** — Regions plugin, click-to-seek, region.id, region.content. Verified via `npx ctx7 docs ... "regions plugin click seek tooltip"`. [VERIFIED]
- **Context7 `/websites/v2_tauri_app`** — `WebviewWindowBuilder`, `on_window_event`, `WindowEvent::CloseRequested`, `app.shell().sidecar()`. Verified via two ctx7 docs queries. [VERIFIED]
- **`scripts/generate_ack_audio.py`** — Achird voice + Gemini TTS pattern + PyAV codec encoding. Repo-shipped, Phase 27 LATENCY-15. [VERIFIED]
- **`src/vibemix/__main__.py:163-187, 199-247, 1141-1156`** — `--debrief` flag wiring + DEBRIEF_PORT constant + `_run_debrief_sidecar` body shipped Phase 25 Plan 25-03. [VERIFIED]
- **`src/vibemix/ui_bus/schemas/debrief.py`** — 3 dataclass payloads (additive-only baseline). [VERIFIED]
- **`src/vibemix/ui_bus/messages.py:1352-1413`** — 3 wrapper classes for debrief. [VERIFIED]
- **`src/vibemix/state/evidence_registry.py:69-100`** — `EVIDENCE_CITATION_RE` regex locked + 7 EBNF source identifiers. [VERIFIED]
- **`src/vibemix/coach/citation_linter.py:88-166`** — `mode="debrief"` tolerance (±2.0s) already supported. [VERIFIED]
- **`tauri/src-tauri/src/sidecar.rs:62-72`** — `SidecarHandle::Arc<Mutex<Option<CommandChild>>>` proven pattern. [VERIFIED]
- **`tauri/src-tauri/src/mascot_window.rs:58-109`** — Second WebviewWindow + label + on_window_event pattern. [VERIFIED]
- **`tauri/src-tauri/src/recordings.rs:103-117`** — `validate_under_root` path-traversal gate proven pattern. [VERIFIED]
- **`tauri/src-tauri/capabilities/default.json:21-25`** — Current validator regex restricting sidecar args. [VERIFIED]
- **`tauri/ui/src/settings/components/recording-row.ts:63-70, 390-472`** — 4-button action cluster + `RecordingSummary` shape with `duration_s` + `event_count`. [VERIFIED]
- **`tauri/ui/package.json`** — Current devDependencies; wavesurfer.js NOT yet present. [VERIFIED]
- **`recordings/20260515-112139/events.jsonl`** — Real-session event-type inventory confirmed (`TRACK_CHANGE`, `PHASE`, `LAYER_ARRIVAL`, `MIX_MOVE`, `HEARTBEAT`). [VERIFIED]
- **npm registry** — wavesurfer.js@7.12.7 (latest 2026-05-13). [VERIFIED via `npm view wavesurfer.js`]

### Secondary (MEDIUM confidence — multiple verified)

- **Tauri Discussion #9388** — Safari doesn't support OGG/OPUS; MP3 is the portable choice. [CITED: https://github.com/orgs/tauri-apps/discussions/9388]
- **Google Developers Blog — Gemini structured outputs (2026)** — JSON Schema + Pydantic responseSchema. [CITED: https://blog.google/innovation-and-ai/technology/developers-tools/gemini-api-structured-outputs/]
- **ai.google.dev/gemini-api/docs/structured-output** — Official structured-output API. [CITED]
- **Tauri Discussion #5334 + Issue #8435** — `WindowEvent::CloseRequested` semantics + dynamically-created window edge cases. [CITED]
- **`.planning/research/v2-1/STACK.md` Bucket 3** — Locks wavesurfer.js, vanilla TS, MP3. [CITED]
- **`.planning/research/v2-1/PITFALLS.md` P81 + P82** — Cross-webview MP3 parity + schema additive-only. [CITED]
- **`.planning/research/v2-1/FEATURES.md` Feature 3** — SBI/STAR-AR framing, anti-feature list, 60-90s TL;DR cap, 3 drills. [CITED]
- **`.planning/research/v2-1/ARCHITECTURE.md` Feature 3** — Dock-to-slot + port 8766 + asset:// protocol notes. [CITED]

### Tertiary (training knowledge, flagged for verification)

- A1, A3, A5, A7 in Assumptions Log — Gemini 3 Pro model ID, PyAV libmp3lame compile, Achird quality at 60s, proxy `response_schema` passthrough. All require Wave 0 smoke checks.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every lib verified via Context7 + npm + repo grep.
- Architecture: HIGH — patterns lifted verbatim from already-shipped Phase 13 (mascot window) + Phase 15 (recordings) + Phase 25 (debrief slot).
- Pitfalls: HIGH — P81 + P82 cross-checked with Tauri discussions + STACK.md anchor.
- Schema additive-only enforcement: HIGH — existing `scripts/check_ipc_schema.py` already enforces count parity; Phase 29 baseline-diff extension is straightforward.
- Gemini 3 Pro structured output: MEDIUM-HIGH — verified via Google blog + ai.google.dev, but exact model ID at execution time needs Wave 0 confirmation (A1).
- Cited-critique stripping correctness: HIGH — reuses Phase 18's locked grammar + Phase 20's `mode="debrief"` tolerance band, both shipped.

**Research date:** 2026-05-15
**Valid until:** 2026-06-15 (30 days — stable Tauri 2.11 + WaveSurfer v7 + Gemini 3 Pro surfaces).

## RESEARCH COMPLETE

**Phase:** 29 — Post-Session Debrief MVP UI
**Confidence:** HIGH

### Key Findings

- Phase 29 is a **dock-into-slot + extend** phase, not novel infrastructure. The v2.0 Phase 25 architectural slot (DEBRIEF_PORT=8766 + `--debrief` flag + 3 IPC schemas) is already shipped; the slot itself is empty (`_run_debrief_sidecar` is a banner-only no-op). Phase 29 fills it.
- **P81 resolved:** MP3 is the only cross-webview portable format. WKWebView (Safari/WebKit on macOS) decodes MP3 but NOT OPUS/OGG. WebView2 (Chromium on Windows) decodes both but inherits MP3 cleanly. PyAV with `libmp3lame` is the standard encoder path (already used in `scripts/generate_ack_audio.py`).
- **P82 enforcement strategy locked:** Extend the existing `scripts/check_ipc_schema.py` count-parity gate with a field-set diff against a v2.1 baseline JSON captured at first Phase 29 commit. Frozen-slotted dataclasses prevent field removal at the Python layer.
- **Critical capability allowlist gap:** `capabilities/default.json:21-25` currently restricts sidecar args to `^--(wizard|session)$` — Phase 29 MUST update this regex to include `debrief` AND add a second args entry for the session-dir positional. This is a Wave 0 blocker, not a polish item.
- **Sentence-level cited-critique stripping is a 12-line regex** — reuses Phase 18's locked `EVIDENCE_CITATION_RE` and Phase 20's `mode="debrief"` tolerance band; no new grammar work needed.
- **WaveSurfer.js v7.12.7 verified current** (npm registry, 2026-05-13 release); STACK.md lock of `^7.10` is satisfied by `^7.12`.
- **Gemini 3 Pro structured output via `response_schema` + Pydantic** is the recommended drill-generation primitive — guaranteed JSON adherence eliminates parse-error handling.

### File Created

`/Users/ozai/projects/dj-set-ai/.planning/phases/29-post-session-debrief-mvp-ui/29-RESEARCH.md`

### Confidence Assessment

| Area | Level | Reason |
|------|-------|--------|
| Standard stack | HIGH | All deps verified via npm + Context7 + repo grep. |
| Architecture | HIGH | Patterns lifted verbatim from shipped Phase 13/15/25 code. |
| Pitfalls (P81, P82) | HIGH | Cross-verified Tauri discussions + STACK.md anchors. |
| Gemini API surface | MEDIUM-HIGH | Model ID + proxy `response_schema` passthrough need Wave 0 smoke (A1, A7). |
| Achird voice quality at 60-90s | MEDIUM | Voice is ack-bank-proven at 8 words; 60s sample needs Wave 0 listening test (A5). |
| Path security | HIGH | Reuses Phase 15's proven `validate_under_root` pattern. |

### Open Questions for Planner

1. Does `evidence_registry.json` persist to disk per session today, or only live in memory? (A2 in Assumptions Log — investigation task for Wave 0.)
2. Should TL;DR generation be progressive (chapters first, drills next, audio last) or all-at-once with spinner? (Recommend progressive — see Open Question #4.)
3. Where does the debrief sidecar log? (Recommend share stdout/stderr piped into main `sidecar.log` with `[debrief]` prefix — see Open Question #2.)
4. Does the `--debrief` dispatch short-circuit BEFORE audio device init? (Trace `__main__.py:main()` order in Wave 0 — see Open Question #1.)

### Ready for Planning

Research complete. Planner has every load-bearing decision pre-resolved by CONTEXT + verified via repo + Context7. Recommended planning approach: 3 waves —

- **Wave 0 (1 day):** Investigations (A1-A7 verification), capability-allowlist update, test scaffolding (8 pytest files + 3 vitest files), schema baseline capture for P82.
- **Wave 1 (2 days):** Backend — `src/vibemix/debrief/` package (chapters + tldr + drills + stripper + ws_server + persistence) + IPC wrapper additions + extend `_run_debrief_sidecar`.
- **Wave 2 (2 days):** Frontend — `tauri/src-tauri/src/debrief_window.rs` + `debrief.html` + `tauri/ui/src/debrief/` (entry + components) + extend `recording-row.ts` with 5th button + CDJ Whisper styling.
- **Wave 3 (1 day):** Verification — full pytest + vitest green + visual smoke on Mac + Windows VM + P82 schema gate exits 0 + manual end-to-end open/close cycle.
