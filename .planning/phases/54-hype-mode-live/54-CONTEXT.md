# Phase 54: Hype Mode Live - Context

**Gathered:** 2026-05-21
**Status:** Ready for planning
**Mode:** Orchestrator-grounded — live-source findings injected directly (autonomous `fully`). Depends on Phase 52 (grounded audio features are what hype reactions react to).

<domain>
## Phase Boundary

On **real audio**, **hype (party) mode** actually fires **grounded, in-bar, non-slop reactions** — the AI voice lands on real events (drops/builds/track-changes) across **≥2 genres**, with cooldowns/latency tuned live so nothing comes late. Covers **LIVE-01** (grounded hype reactions ≥2 genres) + **LIVE-03** (cooldowns + reaction latency tuned in-bar).

**Out of this phase:** feedback/coach mode (Phase 55), mascot reaction surface (56), performance budgets (56). This phase is about the **hype reaction loop landing on real moments**, grounded in Phase-52's now-trustworthy features.

**The bar (CLAUDE.md core value):** "real DJ friend in your ear" — if reactions feel forced, late, fake, or scripted, the product fails. This phase's success is judged on that feel, which makes the live drive the true gate.
</domain>

<decisions>
## Implementation Decisions (Claude's discretion, autonomous `fully`)

- **Engineering ships grounding + tuning; the "does it feel alive" call is Kaan-action.** The reaction machinery exists (event detector + cooldowns + hype persona). This phase's *automatable* engineering is: (1) grounding regressions that replay real captured traces and assert hype events fire at the real drops/builds (not on noise, not late), with the correct per-type cooldowns; (2) a check that the hype-mode prompt is built from REAL evidence (the evidence packet), so reactions are tied to events that happened — the anti-slop guarantee. The across-≥2-genres in-bar "feels real" confirmation is Kaan's ears on a live drive.
- **Tune cooldowns/latency against real traffic, don't redesign.** `event_detector.py` cooldowns are v4-tuned/byte-identical; `coach.py` already shaves ≥500ms TTFT via an ack footer on ack-eligible events. Treat these as the baseline. Any tuning is data-driven from real traces (e.g. is the PHASE/drop cooldown landing reactions in-bar at ~128–145 BPM?), with the change pinned by a test, not vibes.
- **Grounding is the anti-slop spine** ([[project_anti_slop_grounded_gemini_thesis]]). Every hype reaction must trace to a real `Event` + evidence. If the evidence packet is empty/weak, the reaction must NOT fire (or must be a safe grounded ack), never a hallucinated hype line. Verify the evidence→prompt path enforces this.
- **≥2 genres = use the real captured traces.** The psytrance trace already captured + the house/techno material are the ≥2-genre substrate for automated grounding tests; the live drive extends to Kaan's actual library.
</decisions>

<code_context>
## Existing Code Insights (verified live this session)

- **Prompt matrix:** `vibemix/prompts/matrix.py` — 3 skill levels × 2 modes (HYPE_* / COACH_*); `vibemix.prompts.build_system_instruction(skill, mode)` is the entry. `agent/persona.py` is a thin back-compat re-export (truth is the matrix).
- **Event detection:** `state/event_detector.py` — typed events (TRACK_CHANGE, PHASE, KAAN_SPOKE, MANUAL, MIC, HEARTBEAT) with per-type cooldowns via `_cooldown_ok`; gated by `MUSIC_PRESENCE_MIN_SECONDS` + a valid BPM (BPM_VALID_MIN/MAX). Registry write happens inside `_fire` AFTER cooldown bookkeeping (so a registry exception can't corrupt gates). Priority order documented (… > HEARTBEAT fallthrough).
- **Reaction/coach loop:** `runtime/coach.py` + `state/coach.py` (TTFT ack footer, ≥500ms saving on ack-eligible classes), `agent/dj_cohost.py` (the LLM agent — max_output_tokens recently 1024, model gemini-3.5-flash per Kaan's WIP e2d1156), `agent/_streaming_pipe.py`.
- **Emotion/mood:** `state/emotion_router.py` (RMS_LOW, LONG_PHASE_SEC=30 → mood mapping that also feeds the bus `mood` field the mascot will consume in Phase 56).
- **Evidence grounding:** the EvidenceRegistry (cited in LIVE-04/Phase 55) is the same substrate that should back hype reactions — confirm hype reactions cite real events.
- **Single in-flight generation:** enforced (`in_flight` flag) — new triggers while in-flight are dropped; relevant to "no late pile-up" latency feel.
</code_context>

<specifics>
## Specific Ideas

- **Trace-replay grounding test:** feed a real psytrance trace + a house/techno trace through the state→event→reaction path; assert hype events fire at the real drop/build timestamps (within an in-bar tolerance), respect cooldowns, and the built prompt references the real evidence — never fires on silence/noise.
- **Anti-slop guard test:** with an empty/weak evidence packet, assert hype mode does NOT emit a hallucinated hype line (no-fire or safe grounded ack).
- **Live-drive recipe (Kaan-action):** run hype mode, play ≥2 genres into BlackHole, listen — do reactions land in-bar on real drops, feel like a friend not a script, across genres? Tune cooldown/latency constants from what you hear.
</specifics>

<deferred>
## Deferred Ideas (Kaan-action — real hardware, autonomous carveout)

- The **"does hype mode feel alive across ≥2 genres, in-bar, no slop" live drive on Kaan's Mac** is the true LIVE-01/LIVE-03 sign-off (his ears — the hard quality gate per CLAUDE.md). Engineering ships the grounding regressions + anti-slop guards + the cooldown/latency tuning surface + the live-drive recipe; the felt-quality confirmation rides the Kaan-ear surface (per [[project_phase_16_kaan_dj_testing]]). This is the hallucination-grounding hard gate — release blocks until Kaan signs it off.
- Final cooldown/latency *values* may need a second tuning pass after the live drive — leave them adjustable + test-pinned so a value change is a one-line edit + restart ([[feedback_no_gsd_orchestra_for_trivial_tweaks]]).
</deferred>
