# Phase 61: Actionable-Not-Hype Coach Persona - Context

**Gathered:** 2026-05-21
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous `fully` — recommended grey-area answers auto-accepted)

<domain>
## Phase Boundary

This phase makes the **feedback (coach) voice** a real DJ mentor: concrete, prescriptive notes a DJ can act on (observed → impact → prescribe), wired to the deck-state + harmonic events from Phases 59/60, while staying warm, cited, and never nagging. It is the **voice** layer over the grounded facts the prior two phases produce.

**Critical framing — this is a SHARPEN-AND-COMPLETE, not a from-scratch build.** Two layers already exist and must be *extended*, not duplicated or undone:
1. The in-flight `live-tuning-or-brain` WIP (committed baseline `92f2a67`): `prompts/matrix.py` COACH_BEGINNER/INTERMEDIATE/PRO cells already carry "BE A REAL COACH", "ONE THING PER TURN — pick the most actionable nudge", "don't invent a problem", English pro-feedback, pacing/persona fixes.
2. Phase 60's harmonic coach arms in `state/coach.py` (KEY_CLASH / TRANSITION_OPPORTUNITY `task_for_event` arms) + the matrix `[ev:]` grammar — these are GROUNDED + CITED and must keep working.

**In scope:** audit the existing COACH cells against the observed→impact→prescribe contract + real DJ verbs (kill, swap, cut, filter, wait, tighten); sharpen where they still narrate/cheerlead; ensure deck-state/transition awareness flows into the coach prompt the grounded way; regression-fence the hype goldens; keep every prescriptive note cited; cooldown/pacing so it doesn't nag.

**Out of scope:** adding a new mode (forbidden — preserve the `_CELLS`/`_VALID_MODES` env-var contract); the harmonic detection logic (Phase 60 — done); the pill UI (Phase 62); re-doing the live-tuning WIP that already landed.
</domain>

<decisions>
## Implementation Decisions

### Persona Contract (the actionable-not-hype core)
- **observed → impact → prescribe** is the structural spine (maps onto the existing citation contract: cite the observed event, state the impact, prescribe the fix). Use real **DJ verbs**: kill, swap, cut, filter, wait, tighten, ride, pull, push.
- **NOT narration/cheerleading.** Hype names an event then celebrates; coach names the same event then *prescribes*. Audit each COACH cell for residual narration and sharpen it.
- **NO new mode.** Extend the existing COACH_BEGINNER/INTERMEDIATE/PRO cells (`prompts/matrix.py`) + `task_for_event` arms (`state/coach.py`). Preserve `_CELLS`/`_VALID_MODES` (`{"hype","coach"}`) — the env-var contract. The persona flows through BOTH the genai and OpenRouter brain/TTS paths for free via the prompt body.
- Per skill level: BEGINNER = one specific improvement nudge, gentle; INTERMEDIATE = concrete technical critique; PRO = peer-level, no hand-holding. (Already the cell structure — sharpen, don't restructure.)

### Deck / Harmonic Awareness in the Coach Voice
- The coach now has deck-state + KEY_CLASH/TRANSITION_OPPORTUNITY events available (Phases 59/60). The persona should naturally deliver transition + harmonic notes when those events fire — but **only the grounded/cited fragments** Phase 60 produces (harmonic fragments injected only when the tier supplies them, so the model can't be tempted to invent a key/clash).
- Deck-aware coaching stays anti-slop: every note ties to an observed deck-state or event; uncited harmonic claims are stripped by the existing linter.

### Anti-Regression (the load-bearing risk)
- **Hype mode is regression-fenced with goldens.** The Phase-54-validated hype voice must not silently break or go cold from the shared-prompt edits. Any hype-golden change is a deliberate, reviewed decision (Pitfall 5: investigate a tripped golden, do NOT re-baseline reflexively).
- Phase 60's harmonic arms + the live-tuning WIP must keep passing — audit before editing shared files.
- **Over-correction guard:** don't swing hype→robotic/cold. Preserve the warm "friend in your ear" tone while becoming prescriptive. Cooldown/pacing prevents the coach from nagging (no constant stream of corrections).

### Claude's Discretion
- Exact wording sharpening of each COACH cell, the DJ-verb vocabulary surfaced in the prompt, and the pacing/cooldown interplay — set at plan time from the existing cells + the live-tuning WIP + research FEATURES "actionable vs hype" example lines.
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets (already shipped — audit + extend)
- `src/vibemix/prompts/matrix.py` — COACH_BEGINNER/INTERMEDIATE/PRO cells (live-tuning WIP already added "BE A REAL COACH"/"ONE THING PER TURN"); `_CELLS`/`_VALID_MODES`/`build()`; the `{mood_persona}` + `[ev:]`/`[key:]` citation grammar.
- `src/vibemix/state/coach.py` — `task_for_event` (Phase 60 added the KEY_CLASH/TRANSITION arms; live-tuning added pacing/persona); `recent_moves[8s]` freshness.
- The hype goldens (`tests/state/test_coach_prompt_grounding.py`, `test_coach_prompt_diet.py`, hype cells) — the regression fence.
- The OpenRouter brain+TTS path (live-tuning) — the persona must flow through it too.

### Established Patterns
- Anti-slop citation contract = observed→impact→prescribe already structurally (cite the event, the linter strips uncited).
- Goldens fence prompt changes; "investigate, don't re-baseline" on a tripped golden (Pitfall 5).
- No new mode; env-var-selected `_CELLS`.

### Integration Points
- `prompts/matrix.py` (COACH cell wording), `state/coach.py` (task_for_event), the golden tests (fence).
- Research: `.planning/research/FEATURES.md` (§ actionable-vs-hype GOOD vs BAD example lines — the SBI/AID coaching model), PITFALLS.md (§ persona-shift regression: over-correction-to-cold, nag, breaking hype).
</code_context>

<specifics>
## Specific Ideas

- Research FEATURES has concrete GOOD (prescriptive) vs BAD (hype) example lines — lift them as the cell-sharpening target.
- The SBI/AID coaching model (observed→impact→prescribe) IS the existing citation contract — lean on that, don't bolt on a new framework.
- Much of the actionable intent already landed in the live-tuning WIP — the phase's real value is (a) auditing it's consistent + complete, (b) wiring deck/harmonic awareness into the voice, (c) the hype regression fence so the sharpening can't cold-ify hype.
</specifics>

<deferred>
## Deferred Ideas

- The pill UI surface for the coach (Phase 62).
- Any new persona mode / multi-persona — explicitly out (env-var contract held).
- Multi-session coaching arc / drill packs — future (v3.x candidate).
</deferred>
