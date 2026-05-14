# Phase 20: Citation Linter ENFORCEMENT (Live Mode) - Context

**Gathered:** 2026-05-14
**Status:** Ready for planning
**Mode:** Auto-generated (gsd-autonomous fully — auto-accepted recommended decisions)

<domain>
## Phase Boundary

The anti-slop contract goes LIVE. Every spoken Gemini reaction is citation-validated against the `EvidenceRegistry` (Phase 18). Responses that fail citation grammar strip entirely — no partial-strip, no "best effort" — and trigger ack-bank fallback (Phase 19). Telemetry guard prevents the linter itself from inducing a silence-streak failure mode (Pitfall 2).

**Critical scope boundary:** This is the phase where vibemix's "real DJ friend, no AI slop" thesis becomes load-bearing in production. Per STATE locked decision, the telemetry guard + bypass + prompt-side mitigation ALL ship Wave 1, NOT v2.x follow-up — `stripped_rate_15s > 0.4` triggers next-response bypass with `[unverified]` log marker. Linter enforces against Phase 18's EvidenceRegistry sibling-writer contract; per-mode tolerance bands ±1.0s live and ±2.0s debrief (Phase 25 reserves the debrief slot but does NOT surface UI in v2.0).

</domain>

<decisions>
## Implementation Decisions

### Linter Implementation (LOCKED — per ROADMAP success criteria)
- `CitationLinter` class lives in `src/vibemix/coach/citation_linter.py`.
- Stdlib `re` ONLY — no third-party dep (regex/regex2/pyparsing forbidden, keeps PyInstaller bundle lean).
- Validation level: response-level (whole utterance), NOT token-level. Failing responses strip entirely.
- Stripped responses trigger ack-bank fallback via `PROMPT-09` integration (Phase 19 ack bucket).

### Telemetry Guard (LOCKED — per STATE + Pitfall 2)
- `stripped_rate_15s > 0.4` triggers next-response bypass.
- Bypassed response logged with `[unverified]` marker in `events.jsonl` (audit trail for Phase 16 ear-test review).
- Per-session `slop_ratio` metric surfaced via new `ipc.session.citation` IPC message.
- Synthetic stripped-heavy session test in `tests/coach/test_linter_silence_streak.py` verifies the bypass fires before silence-streak crosses Pitfall 2 threshold.

### Tolerance Bands (LOCKED — per Pitfall 18)
- Live mode: ±1.0s timestamp tolerance on `[ev:<TYPE>@<t>]` validation.
- Debrief mode: ±2.0s tolerance (Phase 25 architectural slot reserves but does not surface).
- Single tolerance constant per mode in `src/vibemix/coach/constants.py` — no per-event-type override in v2.0.

### Prompt-Side Mitigation (LOCKED — per success criteria)
- Append to live system instruction: `"If you cannot cite, say 'I'm listening' — never reply with empty text."`
- Failure-mode shifts from "silent strip = void" to "graceful unsourced-but-honest line" — Gemini learns to fail safely.
- Mitigation copy frozen in `src/vibemix/coach/prompt_fragments.py` — single source.

### Registry Race Mitigation (LOCKED — per Pitfall 12)
- `EvidenceRegistry` read path uses async lock matching Phase 18's sibling-writer contract.
- Read-during-write returns most-recent committed registry snapshot (no torn reads).
- Single-tick atomicity: `state_refresh_loop` writes registry + EventDetector fires + linter reads ALL within the same 100ms tick.

### Replay Validation (LOCKED — per success criteria)
- Recorded Kaan session (from Phase 16 ear-test pool) replayed through linter; `stripped_rate < 0.15` overall.
- Replay harness lives at `scripts/replay_linter.py`; reads `events.jsonl` + `voice.wav` + Gemini text channel from session dir.

### Bypass Audit Surface (Claude's Discretion within constraint)
- Each bypass event also logs the response text + the failed citation grammar parse — feeds Phase 16 ear-audit Kaan-action surface.
- Dashboard surface: live `slop_ratio` + 15s-rolling `stripped_rate` in settings → diagnostics.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/vibemix/coach/evidence_registry.py` — Phase 18 sibling-writer registry; linter is the primary read consumer.
- `src/vibemix/coach/prompt_builder.py` — Phase 4/10 prompt builder; v2.0 system-instruction append lands here.
- `src/vibemix/audio/ack_bank/` — Phase 19 ack bucket directory; linter triggers fallback via `runtime/ack_player.py`.
- `src/vibemix/runtime/session_loop.py` — Phase 4 LiveKit cascade; linter hooks into the post-LLM-pre-TTS step.
- `cohost_v4.py` POC — port-from reference for citation grammar shape (DO NOT modify per CLAUDE.md POC rule).

### Established Patterns
- `events.jsonl` audit trail (`VoiceRecorder.log_event`) — used for `[unverified]` marker + bypass audit.
- `ipc.session.*` IPC bus — citation telemetry surface joins existing diagnostics channel.
- Hand-written `@dataclass(frozen=True, slots=True)` + jsonschema Draft-07 for IPC (no pydantic per STATE).
- Single-writer state pattern preserved (linter is read-only consumer).

### Integration Points
- Hook between LiveKit `llm_node()` text emission and `tts_node()` audio synthesis — interception point for response-level strip.
- Phase 19 ack bank `play_fallback(event_class)` API — called on strip.
- Phase 18 EvidenceRegistry `lookup(citation, t_now, tolerance) -> bool` API — single validation primitive.
- `ipc.session.citation` new schema in `src/vibemix/ui_bus/schemas/`.

</code_context>

<specifics>
## Specific Ideas

- Wave 1: `CitationLinter` core + EBNF parser (stdlib re) + response-level strip + ack-bank fallback wiring + telemetry guard ALL together (Pitfall 2 requires bundled ship).
- Wave 2: prompt-side "I'm listening" mitigation append + system-instruction freeze.
- Wave 3: replay harness + Kaan-session validation (`stripped_rate < 0.15` gate).
- Wave 4: settings diagnostics dashboard surface (`slop_ratio` + 15s-rolling stripped rate).

</specifics>

<deferred>
## Deferred Ideas

- Token-level partial strip (v2.x — only response-level in v2.0).
- Per-event-type tolerance band override (v2.x — single live/debrief constant in v2.0).
- Citation grammar v1.1 expansions (e.g., `[ctx:...]` for session-memory citations) — v2.1+, Phase 25 architectural slot reserves namespace.
- Linter-specific i18n message bundle — English-only for v2.0.
- Auto-promotion of bypassed responses to "ack-only" mode for next N events on sustained breach — v2.x guard layer.
</deferred>

---

*Phase: 20-citation-linter-enforcement-live-mode*
*Context gathered: 2026-05-14 (smart discuss, fully autonomous)*
