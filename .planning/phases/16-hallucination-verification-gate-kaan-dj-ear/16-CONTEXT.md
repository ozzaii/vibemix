# Phase 16: Hallucination Verification Gate (Kaan's DJ Ear) - Context

**Gathered:** 2026-05-14
**Status:** Deferred to Kaan-action — calendar-blocking
**Mode:** Auto-generated (gsd-autonomous fully — defer instead of pause)

<domain>
## Phase Boundary

vibemix's reactions feel "real DJ friend in your ear" across 3-5 real DJ sessions — never hallucinating, never breaking flow, never AI slop.

**Memory anchor:** `project_phase_16_kaan_dj_testing` — "hallucination gate satisfied by personal DJ-set testing. Don't auto-build the 30-session replay harness / LLM scorer / F1 validator."

</domain>

<decisions>
## Implementation Decisions

### Method (LOCKED — per memory)
- **Kaan's personal DJ ear-test sessions** (3-5 real sessions, ad-hoc analyzed in-session) replace the 30-session formal replay harness + LLM scorer + F1 validator.
- **No auto-build of test infra.** No replay harness, no LLM scorer, no test corpus generator.
- **Calendar-blocking.** Phase 16 runs ALONGSIDE P17-P20 as those phases ship features (per STATE.md "Phase 16 = Kaan's DJ ear, NOT formal 30-session eval suite").

### Capture (Claude's Discretion when Kaan starts)
- Use existing recording infra from Phase 15 (input.wav + voice.wav + events.jsonl per session) as the on-disk evidence trail.
- Kaan reviews each session's events.jsonl + replays AI voice clips to flag hallucinations / forced reactions / late triggers.
- Findings feed back into P17 (detector tuning) + P19 (latency knobs) + P20 (citation linter rules).

### Sign-off (LOCKED)
- 3-5 sessions with PASS verdict from Kaan = Phase 16 closed.
- Each session signed off in `16-EAR-TEST-{NN}.md` with: track list, AI reactions list, flagged issues, fix-tickets opened against P17-P20.

</decisions>

<code_context>
## Existing Code Insights

- Recording infra: `src/vibemix/audio/recorder.py` (writes input.wav + voice.wav + events.jsonl) — Phase 15.
- Recording browser: `tauri/ui/src/settings/components/recording-browser.ts` — Phase 15.
- AI cohost loop: `src/vibemix/runtime/session_loop.py` — Phase 4-13 stack.
- Event detector: `src/vibemix/state/event_detector.py` — v4 baseline.

</code_context>

<specifics>
## Specific Ideas

- Sessions should span the genres Kaan plays (techno, house, hard tek) to surface genre-router gaps for Phase 17.
- Run sessions on the SHIPPED `npm run tauri dev` build (not `cohost_v4.py` POC) so the Tauri shell + sidecar IPC path is exercised end-to-end.
- After each session, capture in `16-EAR-TEST-{NN}.md`: date, duration, track list, AI reactions w/ timestamps, flagged hallucinations/AI-slop, fix tickets.

</specifics>

<deferred>
## Deferred Ideas

- **30-session formal replay harness** — explicitly cut per memory.
- **LLM scorer** — explicitly cut per memory.
- **F1 validator** — explicitly cut per memory.
- **Test corpus generator** — explicitly cut per memory.
</deferred>
