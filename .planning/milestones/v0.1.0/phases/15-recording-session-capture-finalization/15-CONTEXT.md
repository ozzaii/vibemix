# Phase 15: Recording & Session Capture Finalization - Context

**Gathered:** 2026-05-13
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous fully — recommended answers auto-accepted; no user pause)

<domain>
## Phase Boundary

Lock per-session recording at production quality: every running session writes
`recordings/<YYYYMMDD-HHMMSS>/{input.wav, voice.wav, events.jsonl, session.json}`
with consistent wall-clock + session-relative timestamps. Ship the recording
browser UI inside the existing Settings drawer "Recording" group so the user
can list past sessions, replay voice + event-overlay in-app, and delete with
confirm. Enforce the retention policy on startup, on settings change, and on a
slow background cadence; surface current disk usage live in Settings. Anchor
shape compatibility with the POC diagnostic tools (matching the `cohost_v4.py`
recording layout).

Out of scope: streaming uploads to cloud, per-track stem capture, encrypted
recordings, multi-session merge tooling. POC files (`cohost*.py`, `mascot.html`,
`mocks/*`) are untouchable per the project rule.

</domain>

<decisions>
## Implementation Decisions

### Area 1 — Session Metadata + Format Compatibility (REC-01..04)
- `session.json` schema written at session start, finalized at close:
  - `vibemix_version`, `started_at_iso`, `started_at_unix`, `ended_at_iso`,
    `ended_at_unix`, `duration_s`, `voice` (TTS voice id), `mode` (hype/coach),
    `genre`, `user_level` (beginner/intermediate/pro), `event_count`,
    `voice_wav_bytes`, `input_wav_bytes`, `events_jsonl_bytes`, `crashed` (bool).
- `events.jsonl` first line stays the existing `session_start` record from
  `VoiceRecorder.__init__` — no schema break with POC (`cohost_v4.py:771-850`).
  `session.json` is **additive**, not a replacement.
- WAV formats locked verbatim per ROADMAP success criterion #1:
  `input.wav` = 16kHz mono int16, `voice.wav` = 24kHz mono int16. No re-tune.
- POC compatibility gate: `tests/recording/test_poc_compat.py` opens a fresh
  recording from the shipped binary in `cohost_v4.py`'s `VoiceRecorder` reader
  shape — same dir layout + same WAV headers + same JSONL shape.
- Crash recovery: `session.json` is rewritten at close. If the process dies
  before close, the absent `ended_at_iso` + `crashed: true` (set lazily by the
  next launch's retention sweep) marks the session as recovered. No corruption
  recovery beyond that — WAV files are already best-effort writes.

### Area 2 — Recording Browser UI (REC-05)
- Lives **inside the existing Settings drawer "Recording" group** added in
  Phase 12 — no separate route, no separate window. Renders below the retention
  slider as a virtualized list (lazy-rendered rows; only mounts when the drawer
  opens).
- Row layout (CDJ Whisper v5 token vocabulary — no hex literals):
  - Left: timestamp (`2026-05-13 21:04`) in `--type-mono`
  - Center: duration (`1h 24m`) + event count (`38 events`) in `--type-body`
  - Right: ▶ replay button + 🗑 delete button (icon-only, amber accent on hover)
- Click row → expand inline (no modal). Expansion shows: voice.wav `<audio>`
  element with native controls + transcript-style overlay listing `events.jsonl`
  entries with relative-time stamps. AI text + trigger reason events render
  bold; controller moves render dim. No animation beyond a height transition.
- Replay implementation: HTML5 `<audio>` with `src` set to a Tauri custom
  protocol (`recording://session_dir/voice.wav`) — registered via
  `tauri.conf.json` `app.security.assetProtocol` allowlist scoped to the
  recordings directory. Events.jsonl rendered statically (not synced to audio
  position) — synced playback is a v2 stretch noted in deferred.
- Delete: reuse the Phase 12 `confirmDialog` modal. Confirm text:
  "Delete session 2026-05-13 21:04? This cannot be undone."
- Empty state: muted text "No recordings yet. Sessions appear here after they
  end." — matches v5 voice (state words over sentences).

### Area 3 — Retention Policy (REC-06)
- Default retention: **7 days** (from REQUIREMENTS REC-06, already wired in
  ConfigStore).
- Enforcement triggers, in priority order:
  1. **On sidecar startup** — single sweep before any session opens.
  2. **On retention-days setting change** — immediate sweep with the new value.
  3. **On session close** — same sweep runs after the WAVs/JSONL are flushed.
- Sweep logic: walk `recordings/`, parse dir name as `%Y%m%d-%H%M%S`, compute
  age vs `now()`. Anything older than `retention_days` is deleted whole-dir via
  `shutil.rmtree` (best-effort, ignore_errors=True). Sentinel `36500` (∞ from
  Phase 12) skips the sweep entirely.
- Disk usage display: live read on drawer open + after each sweep. Format:
  `"Recordings: 12 sessions, 3.4 GB used"`. Computed by `os.scandir` +
  `Path.stat().st_size` summed per session; cached in a `RecordingsIndex`
  dataclass for the drawer.
- IPC families added (3 new, brings total 26 → 29):
  - `recordings.list` (request) → `recordings.list_result` (response, includes
    sessions array + total bytes).
  - `recordings.delete` (request, by session_dir name) → `recordings.delete_ack`.
  - `recordings.usage` (push, on sweep) → drawer re-renders disk usage.
- Schema codegen + drift gate (`npm run check:ipc`) must stay green.

### Area 4 — Verification (Success Criterion #1 + #4)
- 60-minute soak test: `tests/recording/test_60min_soak.py` runs an integration
  loop that pushes 60 minutes of synthetic 16kHz frames + 60 minutes of
  synthetic 24kHz TTS PCM + 200 events. Asserts:
  - `input.wav` duration == 60min ± 1s, valid WAV header
  - `voice.wav` duration == 60min ± 1s, valid WAV header
  - Every `events.jsonl` line parses as JSON
  - All `t` values are monotonically non-decreasing
  - `session.json` `started_at_unix` matches the first `session_start` event
- Marked `@pytest.mark.slow`; skipped in default `pytest`, included in
  `pytest -m slow` and `pytest -m "not slow or slow"` CI matrix.
- POC compat test (Area 1 last bullet) runs in default pytest.

### Claude's Discretion
- File names inside the executor's implementation (e.g. `src/vibemix/audio/session_metadata.py` vs `src/vibemix/runtime/recordings_index.py`) — pick what reads cleanly with existing layout.
- Exact RetentionSweep cadence (whether to add a slow asyncio task at e.g. 12h interval) — leave to plan if it materially helps long-running sessions; default skip per "no scope creep".
- IPC schema field names beyond what's named above — match Phase 12 conventions (snake_case, frozen dataclass, slots=True).

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/vibemix/audio/recorder.py` — `VoiceRecorder` already lifted from
  `cohost_v4.py:771-850`, supports configurable root via constructor.
  Adds session_start event with wall_clock_iso/unix and session_dir.
- `src/vibemix/runtime/session_loop.py:448` — passes `retention_days` from
  `ConfigStore` already. Hook point for retention sweep is right here.
- `src/vibemix/runtime/settings.py` — `ConfigStore` with retention_days field,
  atomic writes, OS-aware config dirs.
- `tauri/ui/src/settings/SettingsDrawer.ts:570` — `renderRetentionSlider`
  already mounted in the drawer; we extend the RECORDING group below it.
- `tauri/ui/src/settings/components/retention-slider.js` — 6-stop knurled
  slider, returns RetentionSliderHandle.
- Phase 12 `confirmDialog` modal — reused for delete confirmation.
- Phase 12 IPC codegen pipeline — Python `@dataclass(frozen=True, slots=True)`
  + TS union codegen + drift gate.

### Established Patterns
- `registerStyle()` singleton + zero hardcoded hex (CONVENTIONS guardrail).
- IPC schema mirrors hand-written in `src/vibemix/ui_bus/messages.py`,
  TS generated by `npm run check:ipc`.
- Pure-function presentation components in `tauri/ui/src/settings/components/`.
- Audio-thread / asyncio thread boundary uses `threading.Lock` in
  `VoiceRecorder`; no async-safe queues between OS audio thread and the
  asyncio loop.
- CDJ Whisper v5 token vocabulary lands directly (no shim — Phase 14 deleted it).

### Integration Points
- `SessionLoop.start()` in `src/vibemix/runtime/session_loop.py` already
  constructs `VoiceRecorder` with the recordings root from ConfigStore;
  Phase 15 wires `session.json` write at start + close + the retention sweep.
- `tauri/ui/src/settings/SettingsDrawer.ts` RECORDING group — add the
  recording browser UI below the retention slider.
- `tauri/ui/src/ipc/` — 3 new families codegen'd; drift gate stays green.
- `tauri.conf.json` — register `recording://` asset protocol scoped to the
  recordings dir per OS (`~/Library/Application Support/vibemix/recordings`
  on macOS, `%APPDATA%\vibemix\recordings` on Windows).

</code_context>

<specifics>
## Specific Ideas

- Browser UI density matches the Phase 12 wave-4 settings rows — same row
  height, same hover treatment (`--silk-22` background, amber accent on hover).
- Disk usage string format: `"Recordings: 12 sessions, 3.4 GB used"` —
  state-words-over-sentences voice from Phase 14 copy purge.
- Empty state copy: `"No recordings yet. Sessions appear here after they end."`
- "Delete session ..." confirm copy: `"Delete session {timestamp}? This cannot be undone."`
- `session.json` is the metadata file. It is named `session.json`, not
  `metadata.json` or `manifest.json`, per ROADMAP wording.

</specifics>

<deferred>
## Deferred Ideas

- **Synced playback of voice.wav with events.jsonl scrubbing** — events list
  highlights the current event as audio plays. Adds non-trivial JS state
  management. Push to v2 (`/hatch`-flavored "session debrief" feature).
- **Per-track stem capture** — out of project scope (PROJECT.md OUT-of-scope
  bullet list). Not in v1.
- **Cloud upload of recordings** — explicit OUT in REQUIREMENTS. Privacy +
  one-click-install impact. Push to v2.
- **Encrypted recordings at rest** — out of v1 scope. macOS FileVault + Windows
  BitLocker cover the disk-level case; per-file encryption is a v2 feature for
  shared-machine scenarios.
- **Recording export bundle (.zip)** — out of v1; the recordings dir is
  already a portable folder. Settings could surface "Reveal in Finder/Explorer"
  in v2.
- **Multi-session merge / diff tooling** — explicit "POC = reference, devour
  it" scope sits in the diagnostic POC files; not in product chrome.

</deferred>
