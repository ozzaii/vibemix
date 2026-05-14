# Phase 15: Recording Browser + Retention Enforcement - Context

**Gathered:** 2026-05-14
**Status:** Ready for planning
**Mode:** Smart discuss (fully autonomous — grey-area recommendations auto-accepted per `feedback_autonomous_no_grey_area_pause`)

<domain>
## Phase Boundary

DJs can find, replay, and prune past session recordings without filling their disk.

**In scope (REC-07, REC-08):**
- Settings → Recordings list — chronological roster of past sessions with date, duration, disk size.
- Per-row actions — replay `voice.wav` inline (AI side, small/short), open `input.wav` in OS default app (combined music+mic, large), reveal in Finder/Explorer, delete with confirm.
- Retention policy — default 7 days, configurable (1d / 7d / 30d / never), auto-pruned on sidecar startup + every 6h, logged to `events.jsonl`.

**Out of scope (deferred to v2.1 or beyond):**
- Inline waveform / spectrogram preview (just play buttons in v2.0).
- Bulk-select + bulk-delete (single-row delete only).
- Tag / favorite / pin sessions.
- Rename or annotate sessions in the UI.
- OS trash-bin integration (hard delete).
- Push notification on auto-prune.

</domain>

<decisions>
## Implementation Decisions

### List UI Shape
- Sort order: newest first. Standard pattern; matches Finder, Photos, all session-history UIs.
- Display columns: Date (relative + absolute on hover) | Duration | Size | Actions. Minimal & scannable; no genre/tag columns in v2.0.
- Empty state: "No recordings yet — start a session" with a CTA button linking to Live tab. Helpful, minimal, no illustration.
- Density: same row height as Settings → Audio device list (CDJ Whisper v5 primitives — reuse `Table` component if present, else hand-roll matching density).

### Replay Mechanism
- Inline player: ONLY for `voice.wav` (AI side — small, short, safe to load in-page).
- Combined `input.wav` (music + mic — multi-minute, multi-MB): open in OS default app via `tauri-plugin-shell` `open()`. No inline player.
- Player UX: native HTML5 `<audio controls>` styled with CDJ Whisper v5 amber accent on play head. No WaveSurfer / no waveform widget (scope creep).
- Single-row playback: starting playback on row N stops any active player on row M (≠N). Avoids two AI voices talking over each other.

### Delete Flow
- Confirm modal: required. Use existing CDJ Whisper v5 modal primitive.
- Modal copy: "Delete this recording? This can't be undone." Single primary action "Delete", single secondary "Cancel".
- Bulk-delete: NOT in v2.0 (scope creep — clean utility per `feedback_no_scope_creep_clean_utility`).
- Delete semantics: hard delete (`shutil.rmtree` of the session directory). No OS trash-bin (cross-platform inconsistency, deferred to v2.1).
- Disk-update reflection: row vanishes immediately on confirm; sidecar emits a `recording_deleted` event over the bus so any other window listening can refresh.

### Retention Enforcement
- Default retention: 7 days (matches REC-08 spec).
- Configurable values: 1 day / 7 days / 30 days / Never. Stored in vibemix sidecar config; default is 7d on first install.
- Schedule: prune runs on sidecar startup AND every 6h while sidecar is alive. Watchdog-free — just `asyncio.create_task` with a sleep loop, started in `main()`.
- Log shape: `events.jsonl` line `{"event": "retention_pruned", "count": N, "bytes": M, "t_session": ...}`. No user-facing banner / toast / notification (silent).
- Per-deletion safety: never prune the currently-recording session (skip the dir whose `session_id` matches the running sidecar's active session).

### IPC + Sidecar Surface
- New IPC messages: `recording.list` (sidecar→UI list), `recording.delete` (UI→sidecar), `recording.reveal_in_os` (UI→sidecar — opens file manager), `recording.set_retention` (UI→sidecar config write).
- Schema validated via existing jsonschema Draft-07 hand-written `@dataclass(frozen=True, slots=True)` (no pydantic per `STATE.md` decision).
- File system source-of-truth: `~/Library/Application Support/vibemix/sessions/` on Mac, `%APPDATA%\vibemix\sessions\` on Windows. Read directly on `recording.list` (no DB).

### Claude's Discretion
- Exact table HTML structure / CSS class names — must match CDJ Whisper v5 token palette (5 warm blacks, single amber accent) and Geist + Fraunces typography per `project_visual_direction_cdj_whisper`.
- Exact retention-config UI control (segmented control vs. dropdown — settle during plan).
- Whether to show a humanized "X recordings, Y MB total" footer (likely yes — gives users a feel for disk usage, but not REQ-mandated).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements + Roadmap
- `.planning/REQUIREMENTS.md` — REC-07, REC-08 — single source of truth for acceptance criteria.
- `.planning/ROADMAP.md` Phase 15 section — goal + success criteria + pitfall mapping.
- `.planning/PROJECT.md` "Anti-slop" + "Clean utility" + "Visual direction: CDJ Whisper" sections.

### Pre-existing Code
- `cohost_v4.py` `VoiceRecorder` class — current `~/.../sessions/<session_id>/{input.wav,voice.wav,events.jsonl}` layout. **Don't change disk layout** — read it.
- `tauri/src-tauri/src/sidecar.rs` — existing IPC bus pattern. Add 4 new message types.
- `tauri/ui/src/settings/` — Settings tab structure (CDJ Whisper v5 primitives).
- `.planning/codebase/ARCHITECTURE.md` Layer 1 (Audio I/O) + Layer 6 (Recording Path).

### Visual + UI Contract
- `mocks/vibemix-direction-final.html` — CDJ Whisper visual reference.
- `tauri/ui/src/components/Table.{tsx,css}` (if exists) — reuse table primitives.
- `tauri/ui/src/components/Modal.{tsx,css}` (if exists) — reuse delete-confirm modal.

### Pitfalls
- PITFALLS.md Pitfall 26 (retention edge cases) + Pitfall 19 (filesystem write race) — both Medium severity, applies here.

</canonical_refs>

<specifics>
## Specific Ideas

- Reveal-in-OS: macOS uses `open -R <path>` (Finder reveal), Windows uses `explorer /select,<path>`. Implement in sidecar Rust parent via `tauri-plugin-shell` (NOT the Python sidecar — sidecars shouldn't shell out).
- Empty state CTA links to existing Live route — re-use the `<Button>` primitive with amber accent.
- Per-row "..." overflow menu vs. inline icons — inline icons (3-4 max: play, reveal, delete) for scannability.
- Date format: relative ("2 hours ago", "Yesterday", "3 days ago") in the column; absolute ("2026-05-14 14:32") in tooltip on hover.

</specifics>

<deferred>
## Deferred Ideas

- Inline waveform preview (v2.1 — needs WaveSurfer or canvas waveform — scope creep in v2.0).
- Bulk-select + bulk-delete (v2.1).
- Tag / favorite sessions (v2.1+).
- Rename / annotate sessions in UI (v2.1+).
- OS trash-bin integration (v2.1 — cross-platform parity work).
- Auto-prune notification banner (out of scope — silent prune per "no scope creep" rule).
- Session metadata export (CSV / JSON) — v2.1+ DEBRIEF surface territory.

</deferred>

---

*Phase: 15-recording-browser-retention-enforcement*
*Context gathered: 2026-05-14 (smart discuss, fully autonomous)*
