# Phase 18: Evidence Registry + Citation Grammar in Prompts (v1.0 prompt-only) - Context

**Gathered:** 2026-05-14
**Status:** Ready for planning
**Mode:** Auto-generated (gsd-autonomous fully — auto-accepted recommended decisions)

<domain>
## Phase Boundary

Every Gemini reaction in v2.0 emits `[ev:.../@t]`-style citations grounded in real MusicState events — corpus seeding for Phase 20 enforcement. **v1.0 = prompt-only seeding, NO enforcement yet** (Gemini learns the citation grammar in prod; enforcement lands in P20).

</domain>

<decisions>
## Implementation Decisions

### Architecture (LOCKED — per ROADMAP success criteria + STATE pitfall mitigations)
- **`EvidenceRegistry` is a SIBLING write-target to `MusicState`** — `state_refresh_loop` and `EventDetector._fire` write synchronously every tick; no separate writer coroutine. Closes Pitfall P12 (registry race).
- **Single synchronous writer** — no async queues between detector and registry. Locks via `threading.Lock` matching `MusicState` pattern.
- **Citation grammar EBNF (LOCKED):**
  - `[ev:<TYPE>@<t>]` — event citation (e.g., `[ev:KICK_SWAP@45.2]`)
  - `[aud:<key>@<t>]` — audio feature citation (e.g., `[aud:bpm@45.2]`)
  - `[midi:<event>@<t>]` — MIDI event citation
  - `[track:<id>]` — track citation
  - `[screen:<key>]` — screen capture citation
  - `[mix:<derived>]` — derived mix-state citation (e.g., `[mix:audible_deck=A]`)
  - `[tend:<profile-fact>]` — TenDency / Kaan-profile fact (Phase 26 hook)
  - Multi-citation form: `[ev:KICK_SWAP@45.2,aud:bpm@45.0]` — comma-separated.

### v1.0 Scope (LOCKED — per Pitfall P12 mitigation note)
- **Prompt-only seeding.** Citation grammar baked into Gemini system instruction via `AICoach.build_prompt`.
- **No enforcement, no stripping in v1.0** — Phase 20 lands the linter + ack-bank fallback. v1.0 just teaches Gemini to emit cites; if it doesn't, no harm.
- **Telemetry only:** `events.jsonl` records `citation_count_per_response` per AI turn — Phase 16 ear-test consumes rolling average as P20 readiness signal.

### Concurrency with Phase 17 (LOCKED)
- P17 + P18 are explicitly parallel-bundled in ROADMAP. Shared schema fixes coordinate via `MusicState` field additions (P17) + `Event` type additions (P17 detectors define types P18 cites).
- **Synchronization point:** P18 needs P17's `Event` types to bake into the citation grammar. If P17-02 not yet shipped, P18-02 (grammar) blocks; P18-01 (registry skeleton) can ship first.

### EBNF Grammar (Claude's Discretion within constraint)
- Timestamps: `t` is float seconds since session start, 1-decimal precision (matches events.jsonl convention).
- Event TYPE: UPPER_SNAKE_CASE matching detector class names (`KICK_SWAP`, `SUB_LAYER_ARRIVAL`, etc.).
- Multi-citation: comma-separated, no whitespace inside brackets.
- Invalid form: `[ev:foo bar]` (whitespace) → linter strips in P20.
- Empty citation: `[]` is invalid (linter strips in P20).

### Telemetry (LOCKED)
- `events.jsonl` line shape: `{kind: "citation_count", count: <int>, response_id: <id>, t: <float>}`.
- Rolling 50-response average computed in `AICoach.on_response_complete`.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/vibemix/state/music_state.py` — `MusicState` writer pattern (Phase 6, extended in P17).
- `src/vibemix/state/event_detector.py` — `EventDetector._fire` is the citation source-of-truth.
- `src/vibemix/runtime/coach.py` — `AICoach.build_prompt` bakes system instruction.
- `src/vibemix/audio/recorder.py` — `VoiceRecorder.log_event` for events.jsonl writes.
- `src/vibemix/runtime/session_loop.py` — `state_refresh_loop` @100ms (single writer).
- `cohost_v4.py` — POC reference for evidence-packet shape (port-from only).

### Established Patterns
- `threading.Lock` per shared dataclass (MusicState pattern).
- Synchronous writes to events.jsonl via `VoiceRecorder.log_event`.
- System instruction baked via f-string + grammar reference text in `coach.py`.

### Integration Points
- `EvidenceRegistry` lives in `src/vibemix/state/evidence_registry.py` (new).
- `state_refresh_loop` adds one synchronous write per tick.
- `EventDetector._fire` adds one synchronous write per fire.
- `AICoach.build_prompt` reads from registry via snapshot.
- Gemini response handler counts citation occurrences via regex `\[(?:ev|aud|midi|track|screen|mix|tend):[^\]]+\]`.

</code_context>

<specifics>
## Specific Ideas

- Wave 1: `EvidenceRegistry` skeleton + tests (no integration yet — P17 may still be shipping).
- Wave 2: `state_refresh_loop` + `EventDetector._fire` integration (sync writes); requires P17-01 + P17-02 shipped.
- Wave 3: `AICoach.build_prompt` grammar bake + EBNF system instruction; requires Wave 2.
- Wave 4: telemetry — `citation_count` events.jsonl line + rolling 50-response avg.

</specifics>

<deferred>
## Deferred Ideas

- **Citation enforcement / linter / stripping** — Phase 20.
- **Ack-bank fallback for un-cited responses** — Phase 19 (ack bank) + Phase 20 (linter wiring).
- **Multi-tier citation validation** (e.g., timestamp-tolerance) — Phase 20 (per Pitfall 18).
</deferred>
