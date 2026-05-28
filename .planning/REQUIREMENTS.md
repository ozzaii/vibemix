# Requirements: vibemix — v10.0 "12-Factor Hardening"

**Defined:** 2026-05-28
**Core Value:** Real DJ friend in your ear, no AI slop. Reactions and curations grounded — never invented, never silently wrong.

## v10.0 Requirements

Requirements for milestone v10.0. Each maps to roadmap phases.

Background: derived from the today-2026-05-28 audit of vibemix against [humanlayer/12-factor-agents](https://github.com/humanlayer/12-factor-agents). vibemix scored 5 strong-pass + 2 pass + 3 partial + 2 N/A; this milestone closes the three partials without forcing the wrong abstraction on the live co-host streaming pipeline (Factor 10).

### HARDEN-RETRY — Viber Tool-Retry Policy (Factor 9)

Today Viber silently degrades on empty/error tool sequences. Codex's MCP harness retries internally but vibemix has no consecutive_errors counter or terminal `stop_reason` for tool starvation, so a curation run on an empty library returns "no playlist" with no diagnosis.

- [x] **HARDEN-RETRY-01**: `LibraryToolset` tracks consecutive empty `search_vibe` results and tool-error responses across one curation run via an additive per-instance counter (mirrors `seen` set lifetime).
- [x] **HARDEN-RETRY-02**: After N consecutive empty/error tool calls (N tunable module constant; default 3 — chosen for fast feedback on real failure modes without false-firing on a single missed search), the toolset surfaces a terminal `stop_reason="tool_starvation"` payload via a dedicated dispatch path or attribute readable by `codex_curate`.
- [x] **HARDEN-RETRY-03**: The `tool_starvation` payload carries an actionable user-facing hint identifying the most likely root cause: empty library / no matches for theme / specific tool starving (e.g. "library has 0 tracks — run `library ingest` first" / "no tracks matched 'uplifting 200 BPM ambient' — try a different theme or broaden BPM").
- [x] **HARDEN-RETRY-04**: CLI `library curate` and `library build-set` exit with non-zero status on `stop_reason="tool_starvation"`, distinct from successful "no playlist found" cases.
- [x] **HARDEN-RETRY-05**: Cardinal Invariant #2 holds — the error counter is additive telemetry on `LibraryToolset`, never relaxes the `seen` grounding gate or the `create_playlist` library re-validation. Counter writes are confined to handler-entry / handler-exit sites; no other code reads or mutates it.
- [x] **HARDEN-RETRY-06**: Failing-then-passing tests cover: zero-track library scenario, narrow theme with zero vibe-search hits, dispatch-error path (tool crash → counter increments), counter reset on successful tool call, interaction with `create_playlist` (a starvation termination MUST short-circuit before a partial-playlist write).
- [x] **HARDEN-RETRY-07**: `codex_curate.curate_with_codex` and `build_set_with_codex` parse `stop_reason="tool_starvation"` from MCP tool output and propagate it to `CodexCurateResult` / `CodexBuildSetResult` so callers (CLI + Telegram + GUI) see a uniform terminal stop_reason regardless of whether starvation originated inside the toolset or after the Codex harness exited.

### HARDEN-CLARIFY — Viber RequestClarification (Factor 7)

Today on an ambiguous theme ("uplifting" — for whom? bedroom-headphones or peak-time-club? 80 BPM ambient or 130 BPM driving?), Codex silently picks one heuristic. Per 12-factor-agents Factor 7, the right pattern is a structured `request_human_input` tool the LLM can call when it needs disambiguation.

- [x] **HARDEN-CLARIFY-01**: New `request_clarification(question: str, choices: list[str])` handler in `LibraryToolset`, callable from the dispatch table. Validates that `choices` length is 2-5 (rejects 0/1 — no real disambiguation; rejects 6+ — choice paralysis).
- [x] **HARDEN-CLARIFY-02**: MCP server (`library/mcp_server.py`) exposes `request_clarification` via FastMCP with explicit Python signature `(question: str, choices: list[str]) -> dict`. Tool docstring teaches Codex when to call it ("when the user theme is materially ambiguous and a single sensible default cannot be picked").
- [x] **HARDEN-CLARIFY-03**: Calling `request_clarification` terminates the toolset run with `stop_reason="clarification_needed"` and surfaces the question + choices payload via the same readable seam as `tool_starvation` (HARDEN-RETRY-02 — these two stop_reasons are siblings).
- [x] **HARDEN-CLARIFY-04**: CLI `library curate` / `library build-set` print the formatted clarification (question + numbered choices) on `stop_reason="clarification_needed"` and exit with a distinct non-zero code separate from `tool_starvation`, so scripts can distinguish "need user input" from "library starved".
- [x] **HARDEN-CLARIFY-05**: Telegram bridge's `format_reply` adds a branch that renders the clarification as a chat message with numbered choices; the existing playlist-template branch is unchanged.
- [x] **HARDEN-CLARIFY-06**: Single-turn semantics — the caller is responsible for re-invoking curation with the augmented theme (e.g. CLI prints "Re-run with: `library curate \"<theme> + <chosen option>\"`"). vibemix does NOT retain state across the clarification cycle. Codex is fully restarted on the next run.
- [x] **HARDEN-CLARIFY-07**: Failing-then-passing tests cover: tool handler args validation (0/1/6+ choices rejected), 2-5 choices accepted, CLI output formatting (numbered prefix, distinct exit code), Telegram `format_reply` branch (numbered choices, no path leakage via existing `strip_leaks`), `codex_curate` propagates `stop_reason="clarification_needed"` to the result dataclass.

### HARDEN-CONTRACT — Prompt Composition Contract (Factor 3)

Today the exact composition of what enters the live co-host prompt per event type is reverse-engineered each time someone touches `coach.py` / `dj_cohost.py` / `evidence_registry.py`. The Phase-3 audit found this is the highest-leverage Factor-3 audit gap.

- [x] **HARDEN-CONTRACT-01**: `docs/PROMPT-COMPOSITION.md` (NEW file) enumerates every EventType emitted by `EventDetector` with a table column showing the evidence fields populated for that event.
- [x] **HARDEN-CONTRACT-02**: Doc lists the 11 `EVIDENCE_SOURCES` (per `evidence_registry.py:129`) with the body grammar for each (`ev:<TYPE>@<t>`, `key:<deck>:<camelot>`, `recall:<record_id>`, `exemplar:<track_id>`, `cue:<anchor_id>`, etc.) and which event types may cite which sources.
- [x] **HARDEN-CONTRACT-03**: Doc shows the recall-fragment shape per event family (TRACK_CHANGE / MIX_MOVE / LAYER_ARRIVAL / PHASE) with concrete examples, cross-referenced to `coach.py:158 recall_fragment_for_event`.
- [x] **HARDEN-CONTRACT-04**: Doc identifies diet-mode-eligible events (per `ACK_ELIGIBLE_EVENTS` + `coach.py:824 if diet:`) vs full-prompt events, with the rationale (TTFT budget on ack-eligible events).
- [x] **HARDEN-CONTRACT-05**: Every file:line reference in the doc resolves against current source (verified by `grep` at write-time; a CI smoke check is OPTIONAL and not blocking).
- [x] **HARDEN-CONTRACT-06**: Doc is the named contract for new mood/lens contributors. CLAUDE.md "Architecture" section gains a one-line pointer to it ("for prompt composition, see `docs/PROMPT-COMPOSITION.md`").
- [x] **HARDEN-CONTRACT-07**: Doc cross-references the per-event-type cooldowns from `audio/constants.py:77 MIN_EVENT_GAP_PER_TYPE` so a reader can see in one place: "this event fires at most every Xs, surfaces these evidence fields, may cite these sources, follows this recall shape, eligible-or-not for diet mode."

## Future Requirements

Deferred to a future milestone. Tracked but not in this roadmap.

### HARDEN-FUTURE — Possible follow-ups identified during the audit

- **HARDEN-FUTURE-01**: Multi-turn Viber state persistence across Codex restarts (would enable conversational refinement of a curation; Factor 5/6/12 alignment). Deferred because today Viber is single-turn and the simplicity carries the weight.
- **HARDEN-FUTURE-02**: BAML/Pydantic-strict schema enforcement on the FastMCP tool surface (Factor 4 sertleştirme). Deferred — current FastMCP signature inference + dict-typed handlers are sufficient; Codex's harness validates upstream.
- **HARDEN-FUTURE-03**: Discord / iMessage trigger transports (Factor 11 expansion). Deferred — Telegram covers mobile today, additional transports add surface area without closing a gap.

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Forcing the live co-host into a tool-call agent loop | Factor 10 violation — the live streaming reaction pipeline is fundamentally a different shape (60Hz audio buffer + EMA RMS + event cooldowns + frame-to-frame continuity). 12-factor-agents Factor 10 explicitly warns against this. The live pipeline stays event-triggered streaming TTS. |
| Migrating to LangGraph / CrewAI / smolagents / Pydantic AI | The whole 12-factor-agents thesis is anti-framework. vibemix's hand-written async orchestration is the correct posture; this milestone reinforces it, never replaces it. |
| Stateless-reducer refactor of `MusicState` | Live co-host needs frame-to-frame continuity (cooldowns, debounce, EMA buffers) — Factor 12 is "mostly just for fun" per the source doc, and domain-mismatched here. |
| Persistent durable pause/resume between tool selection and execution | Factor 6 — Viber today is single-turn and that's the right scope. Multi-turn pause/resume is HARDEN-FUTURE-01. |
| New evidence sources for live co-host | Out of milestone scope. The 11 locked sources cover the live surface; this milestone documents them (Phase C), never extends them. |
| Touching `src/vibemix/agent/`, `src/vibemix/__main__.py`, `tauri/ui/`, `src/vibemix/intel/` | Disjointness contract with the two active parallel handoffs (LiveKit-upgrade in `__main__.py:1353`, frontend wiring in `tauri/ui/*`). `feedback_concurrent_sessions_one_tree` enforces island discipline. |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| HARDEN-RETRY-01 | Phase 99 | Complete |
| HARDEN-RETRY-02 | Phase 99 | Complete |
| HARDEN-RETRY-03 | Phase 99 | Complete |
| HARDEN-RETRY-04 | Phase 99 | Complete |
| HARDEN-RETRY-05 | Phase 99 | Complete |
| HARDEN-RETRY-06 | Phase 99 | Complete |
| HARDEN-RETRY-07 | Phase 99 | Complete |
| HARDEN-CLARIFY-01 | Phase 100 | Complete |
| HARDEN-CLARIFY-02 | Phase 100 | Complete |
| HARDEN-CLARIFY-03 | Phase 100 | Complete |
| HARDEN-CLARIFY-04 | Phase 100 | Complete |
| HARDEN-CLARIFY-05 | Phase 100 | Complete |
| HARDEN-CLARIFY-06 | Phase 100 | Complete |
| HARDEN-CLARIFY-07 | Phase 100 | Complete |
| HARDEN-CONTRACT-01 | Phase 101 | Complete |
| HARDEN-CONTRACT-02 | Phase 101 | Complete |
| HARDEN-CONTRACT-03 | Phase 101 | Complete |
| HARDEN-CONTRACT-04 | Phase 101 | Complete |
| HARDEN-CONTRACT-05 | Phase 101 | Complete |
| HARDEN-CONTRACT-06 | Phase 101 | Complete |
| HARDEN-CONTRACT-07 | Phase 101 | Complete |

**Coverage:**
- v10.0 requirements: 21 total
- Mapped to phases: 21 (100% — assigned 2026-05-28 by gsd-roadmapper)
- Unmapped: 0
- Distribution: HARDEN-RETRY-01..07 → Phase 99 (7) · HARDEN-CLARIFY-01..07 → Phase 100 (7) · HARDEN-CONTRACT-01..07 → Phase 101 (7)

---
*Requirements defined: 2026-05-28*
*Last updated: 2026-05-28 after milestone v10.0 initialization*
