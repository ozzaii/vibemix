# Phase 25: Pyrekordbox XML One-Shot Import + DEBRIEF Architectural Slot - Context

**Gathered:** 2026-05-14
**Status:** Ready for planning
**Mode:** Auto-generated (gsd-autonomous fully — auto-accepted recommended decisions)

<domain>
## Phase Boundary

vibemix reads the user's Rekordbox `collection.xml` ONCE and grounds track citations in real BPM/key/cue data via 4-tier fuzzy lookup confidence ladder. SQLite cache at `$APPDATA/vibemix/library/rekordbox.db` (3 tables: tracks, cues, beat_grid). DEBRIEF sidecar `--debrief` flag + IPC reservations ship as the v2.1 docking point — NO UI surface in v2.0 (architectural slot only).

**Critical scope boundary:** Wave 0 day-1 spike: `pyrekordbox==0.4.4` SQLCipher dep tree check — does it pull `sqlcipher3-wheels` on plain install? Use `--no-deps` install path if so. SQLCipher path stays explicitly UNUSED. Per STATE: DEBRIEF in v2.0 = architectural slot ONLY (sidecar `--debrief` flag + port 8766 + 3 IPC schema reservations). Full UI feature deferred to v2.1. Library intelligence v1 (sqlite-vec / embed pipeline) explicitly DEFERRED to v2.1 per project memory.

</domain>

<decisions>
## Implementation Decisions

### Pyrekordbox Install Path (LOCKED — per STATE Wave 0 spike + Pitfall)
- Pin: `pyrekordbox==0.4.4` (per STATE STACK.md decision).
- Wave 0 Day-1 dep tree check: if `pip install pyrekordbox==0.4.4` hard-requires `sqlcipher3-wheels`, use `pip install --no-deps pyrekordbox==0.4.4` install path.
- SQLCipher code path explicitly NEVER touched — XML import only.
- Spike artifact: `.planning/phases/25-.../WAVE-0-DEPS-SPIKE.md` with verdict.

### XML Parser (LOCKED — per ROADMAP success criteria)
- `RekordboxLibrary` class lives in `src/vibemix/library/rekordbox.py`.
- Parses TEMPO + POSITION_MARK nested elements (Rekordbox 5/6/7 schemas — schema-version detection at parse start).
- Performance gate: ~5k tracks completes in <30s (PyInstaller-bundled CPython 3.12 on M1).
- User UX: drag-drop or file-pick `collection.xml` in Settings → Library tab.

### SQLite Cache (LOCKED — per success criteria)
- Path: `$APPDATA/vibemix/library/rekordbox.db` (Mac: `~/Library/Application Support/vibemix/library/`, Win: `%APPDATA%\vibemix\library\`).
- 3 tables: `tracks`, `cues`, `beat_grid`.
- Plain SQLite (NOT SQLCipher). Stdlib `sqlite3` module — no extra deps.
- Schema migrations via single version pragma; v2.0 ships at v1.

### Fuzzy Lookup Ladder (LOCKED — per Pitfall 16 + success criteria)
- 4-tier confidence ladder:
  1. Exact match (title + artist + BPM): confidence = 1.0
  2. BPM-disambiguated (title match + BPM ±2): confidence = 0.85
  3. Partial+artist (title prefix + artist): confidence = 0.7
  4. Partial-only (title contains): confidence = 0.4
- **Pitfall 16 mitigation**: artist OR BPM REQUIRED for ≥0.7 confidence. No "partial-only at 0.7+".
- Confidence-aware grounding rendering:
  - <0.5: "I think this is X" (hedged speech)
  - ≥0.7: full `[track:<id>]` citation (Phase 18 citation grammar)

### Staleness Nudge (LOCKED — per Pitfall 15 + success criteria)
- 30-day staleness nudge: UI surfaces "Looks like you've added new tracks — re-import to keep me grounded" at 30d since last import.
- OR triggers on 10 lookup misses (whichever first).
- Nudge dismissible per session; persists across sessions if not re-imported.
- Nudge copy frozen in `tauri/ui/src/strings/library_nudge.ts` per `project_visual_direction_cdj_whisper`.

### DEBRIEF Architectural Slot (LOCKED — per STATE + cross-doc reconciliation)
- Sidecar `--debrief <session_dir>` flag spawns SEPARATE child process.
- WS bus port 8766 (avoids 8765 collision with live mascot bus).
- 3 IPC schema reservations (hidden in v2.0, surfaced in v2.1):
  - `ipc.debrief.start`
  - `ipc.debrief.status`
  - `ipc.debrief.result`
- v2.0 = NO UI surface. v2.1 ships full UI (post-session debrief view).
- Citation linter tolerance ±2.0s in debrief mode (Phase 20 reservation).

### Embed/Vector Pipeline (Claude's Discretion within constraint)
- DEFERRED to v2.1 per project memory `project_v2_open_candidates`.
- v2.0 ships text-match lookup ONLY. Gemini Embedding 2 audio embeddings = v2.1 work.
- sqlite-vec dep is committed to STATE STACK.md but NOT exercised in v2.0 — bundled for forward-compat (Mac/Linux only, Win numpy fallback).

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `cohost_v4.py` `TrackInfo` (nowplaying-cli poll) — port-from reference; new `RekordboxLibrary` is the durable source.
- `src/vibemix/state/track_info.py` — Phase 6 nowplaying poll; cross-references with Rekordbox lookup.
- Phase 18 `EvidenceRegistry` — `[track:<id>]` citation source includes Rekordbox track ID.
- Phase 5 FastAPI proxy — quota for embed calls (NOT used in v2.0; reserved for v2.1).

### Established Patterns
- Hand-written `@dataclass(frozen=True, slots=True)` + jsonschema Draft-07 (no pydantic).
- Stdlib `sqlite3` for cache (no SQLAlchemy in sidecar — keeps PyInstaller bundle lean).
- IPC over WebSocket `127.0.0.1:8765` (live), `127.0.0.1:8766` (debrief reserved).
- Settings tab structure already established in Phase 11/12 — Library tab joins.

### Integration Points
- `RekordboxLibrary.lookup(title, artist=None, bpm=None) -> (Track | None, confidence: float)` — single primitive consumed by `EvidenceRegistry`.
- AICoach `prompt_builder` adds Rekordbox track context to prompt when confidence ≥0.7.
- Settings → Library drag-drop UI fires `ipc.library.import` IPC.
- DEBRIEF sidecar `--debrief` flag spawns from Tauri Rust parent on user trigger (UI hidden in v2.0).

</code_context>

<specifics>
## Specific Ideas

- Wave 0 (Day-1): pyrekordbox SQLCipher dep tree check → WAVE-0-DEPS-SPIKE.md verdict + install path locked.
- Wave 1: `RekordboxLibrary` XML parser (Rekordbox 5/6/7 schemas) + SQLite cache + 3-table schema.
- Wave 2: 4-tier fuzzy lookup ladder + Pitfall 16 artist-OR-BPM gate.
- Wave 3: Settings → Library drag-drop UI + 30-day staleness nudge + 10-miss counter.
- Wave 4: confidence-aware grounding integration with Phase 18 EvidenceRegistry + AICoach prompt.
- Wave 5: DEBRIEF architectural slot — sidecar `--debrief` flag + port 8766 + 3 IPC schema reservations (NO UI).

</specifics>

<deferred>
## Deferred Ideas

- DEBRIEF UI surface (v2.1 — architectural slot only in v2.0 per STATE).
- Library intelligence v1 (sqlite-vec audio embedding search) — v2.1 per project memory.
- "Vibe search" via Gemini Embedding 2 audio space — v2.1.
- Apple Music / Spotify library import — v2.x (Rekordbox-only in v2.0).
- iTunes XML parser — v2.x.
- Real-time library watch (re-import on collection.xml change) — v2.x; v2.0 = one-shot + 30-day nudge.
- SQLCipher path activation (encrypted Rekordbox DB) — never (XML import only).
- Multi-library merge (multiple collection.xml files) — v2.x.
</deferred>

---

*Phase: 25-pyrekordbox-xml-import-debrief-architectural-slot*
*Context gathered: 2026-05-14 (smart discuss, fully autonomous)*
