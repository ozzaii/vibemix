# Phase 55: Feedback Mode Live + Citation Integrity - Context

**Gathered:** 2026-05-21
**Status:** Ready for planning
**Mode:** Orchestrator-grounded — live-source findings injected directly (autonomous `fully`). Depends on Phase 52 (grounded audio features back the coaching); benefits from Phase 54 (latency/cooldown tuning carries over).

<domain>
## Phase Boundary

On **real audio**, **feedback (coach) mode** produces **grounded, in-bar, non-slop coaching** across **≥2 genres**, AND the **EvidenceRegistry citation strip reflects real session events** with **zero orphaned or hallucinated citations**. Covers **LIVE-02** (coach-mode grounded reactions ≥2 genres) + **LIVE-04** (citation integrity).

**Out of this phase:** hype mode (Phase 54 — but its grounding/latency tuning carries over), mascot (56), perf (56). This phase is about **coaching that's correct + every citation provably real**.

**LIVE-04 is the strongest *automatable* gate in the live-validation block** — citation integrity is testable without Kaan's ears: a citation either resolves to a real registered evidence item or it's an orphan/hallucination. That makes it the deepest engineering target here; LIVE-02's "is the coaching useful" feel is the Kaan-ear part.
</domain>

<decisions>
## Implementation Decisions (Claude's discretion, autonomous `fully`)

- **Citation integrity (LIVE-04) is provable engineering — make it airtight.** The stack exists: `EvidenceRegistry` (registers library tracks + an evidence corpus of events/audio/mix), `citation_linter.py` (strips unverified/hallucinated citations, tracks `slop_ratio` + 15s stripped-rate), the `[track:<id>]` / evidence-corpus citation grammar baked into coach prompts, and the `ipc.session.citation` surface to the diagnostics drawer. This phase's automatable work: regressions that replay real session traffic and assert (a) **every citation emitted resolves to a real registered evidence item — zero orphans**; (b) the linter **strips a deliberately-hallucinated citation** and the slop metrics move correctly; (c) the UI citation strip payload reflects the real stripped/verified counts. If a real orphan/leak path is found, close it.
- **Coach-mode grounding (LIVE-02) mirrors Phase 54's anti-slop spine, for COACH_* prompts.** Trace-replay: real psytrance + house/techno traces → coach reactions fire grounded on real events, in-bar, citing real evidence; empty/weak evidence → no hallucinated coaching (no-fire or safe grounded ack). Reuse/extend whatever grounding harness Phase 54 builds (don't duplicate it).
- **Don't rebuild the coach/evidence machinery — validate + harden it.** `state/coach.py` (`evidence_line`, `build_prompt`, `task_for_event`, evidence-corpus footer) is v4-byte-identical in the load-bearing branches; treat as baseline. Any change is data-driven + test-pinned.
- **The "is coaching genuinely useful across ≥2 genres" call is the Kaan-ear gate** ([[project_phase_16_kaan_dj_testing]]) — engineering proves grounding + zero-orphan citations; Kaan's live drive judges usefulness.
</decisions>

<code_context>
## Existing Code Insights (verified live this session)

- **EvidenceRegistry**: `src/vibemix/state/evidence_registry.py` — `register_library(lib)` (wired in `__main__.py:801`, "closes v2.0 register_library orphan P48"); holds the evidence corpus counted as `evidence_corpus[ev=N,aud=M,mix=K]` in the prompt footer.
- **Citation linter**: `src/vibemix/coach/citation_linter.py` — strips unverified citations; the anti-slop enforcement point. Produces `slop_ratio` (cumulative stripped/total) + 15s rolling stripped-rate + last-unverified-response + `bypass_active`.
- **Citation IPC**: `src/vibemix/ui_bus/schemas/citation.py` (`SessionCitationPayload`) → `ipc.session.citation` → Tauri Settings → Diagnostics drawer. The "citation strip" Kaan sees. Single source for the field set; wrapper `ui_bus.messages.SessionCitation`.
- **Coach prompt build**: `src/vibemix/state/coach.py` — `evidence_line` (grounded-state string; track-name floor at confidence 0.3), `_evidence_line_compact` (diet path, ~400-char saving), evidence-corpus footer (Plan 18-02), citation grammar (Plan 18-03), `build_prompt`, `task_for_event`. `runtime/coach.py` is the loop.
- **Mode prompts**: `vibemix/prompts/matrix.py` — COACH_* templates (3 skill levels), `build_system_instruction(skill, mode)`.
- **Debrief** (`src/vibemix/debrief/`) — post-session chapters/tldr/drills also consume evidence + citations; LIVE-04's integrity contract should hold there too (chapters.py references evidence). Confirm the citation strip is consistent live vs debrief.
</code_context>

<specifics>
## Specific Ideas

- **Zero-orphan citation test:** replay a real session trace → collect every `[track:<id>]` / evidence citation the coach emits → assert each resolves to a real `EvidenceRegistry` entry; assert count of orphans == 0.
- **Hallucination-strip test:** inject a model response citing a non-existent evidence id → assert `citation_linter` strips it, `slop_ratio` rises, and the stripped line surfaces in `last_unverified_response`.
- **Coach grounding test:** real traces (≥2 genres) → coach fires grounded on real events, in-bar; empty evidence → no hallucinated coaching.
- **Live-drive recipe (Kaan-action):** run coach/feedback mode, play ≥2 genres, watch the diagnostics citation strip — `slop_ratio` stays low, no orphan citations, coaching feels grounded + useful.

<deferred>
## Deferred Ideas (Kaan-action — real hardware, autonomous carveout)

- The **"does coach mode coach usefully across ≥2 genres" live drive on Kaan's Mac** is the LIVE-02 felt-quality sign-off (his ears). Engineering ships the grounding + zero-orphan-citation regressions + the linter hallucination-strip proof + the live-drive recipe. This + Phase 54 together feed the v4.0 hallucination hard gate (Gate 2b) — release blocks until Kaan signs both modes off.
</deferred>
