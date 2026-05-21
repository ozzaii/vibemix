# Phase 61: Actionable-Not-Hype Coach Persona - Research

**Researched:** 2026-05-21
**Domain:** Prompt-persona engineering on a grounded local AI DJ co-host — sharpening the COACH (feedback) voice into a prescriptive DJ mentor while regression-fencing the validated HYPE voice
**Confidence:** HIGH (all claims codebase-verified by direct read; no external library research needed — this is a prompt-text + golden-test phase, not a dependency phase)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Persona Contract (the actionable-not-hype core)**
- **observed → impact → prescribe** is the structural spine (maps onto the existing citation contract: cite the observed event, state the impact, prescribe the fix). Use real **DJ verbs**: kill, swap, cut, filter, wait, tighten, ride, pull, push.
- **NOT narration/cheerleading.** Hype names an event then celebrates; coach names the same event then *prescribes*. Audit each COACH cell for residual narration and sharpen it.
- **NO new mode.** Extend the existing COACH_BEGINNER/INTERMEDIATE/PRO cells (`prompts/matrix.py`) + `task_for_event` arms (`state/coach.py`). Preserve `_CELLS`/`_VALID_MODES` (`{"hype","coach"}`) — the env-var contract. The persona flows through BOTH the genai and OpenRouter brain/TTS paths for free via the prompt body.
- Per skill level: BEGINNER = one specific improvement nudge, gentle; INTERMEDIATE = concrete technical critique; PRO = peer-level, no hand-holding. (Already the cell structure — sharpen, don't restructure.)

**Deck / Harmonic Awareness in the Coach Voice**
- The coach now has deck-state + KEY_CLASH/TRANSITION_OPPORTUNITY events available (Phases 59/60). The persona should naturally deliver transition + harmonic notes when those events fire — but **only the grounded/cited fragments** Phase 60 produces (harmonic fragments injected only when the tier supplies them, so the model can't be tempted to invent a key/clash).
- Deck-aware coaching stays anti-slop: every note ties to an observed deck-state or event; uncited harmonic claims are stripped by the existing linter.

**Anti-Regression (the load-bearing risk)**
- **Hype mode is regression-fenced with goldens.** The Phase-54-validated hype voice must not silently break or go cold from the shared-prompt edits. Any hype-golden change is a deliberate, reviewed decision (Pitfall 5: investigate a tripped golden, do NOT re-baseline reflexively).
- Phase 60's harmonic arms + the live-tuning WIP must keep passing — audit before editing shared files.
- **Over-correction guard:** don't swing hype→robotic/cold. Preserve the warm "friend in your ear" tone while becoming prescriptive. Cooldown/pacing prevents the coach from nagging (no constant stream of corrections).

### Claude's Discretion
- Exact wording sharpening of each COACH cell, the DJ-verb vocabulary surfaced in the prompt, and the pacing/cooldown interplay — set at plan time from the existing cells + the live-tuning WIP + research FEATURES "actionable vs hype" example lines.

### Deferred Ideas (OUT OF SCOPE)
- The pill UI surface for the coach (Phase 62).
- Any new persona mode / multi-persona — explicitly out (env-var contract held).
- Multi-session coaching arc / drill packs — future (v3.x candidate).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| COACH-01 | Feedback (coach) mode delivers concrete, prescriptive DJ notes (observed→impact→prescribe, real DJ verbs: kill, swap, cut, filter, wait, tighten) — not narration or cheerleading. | Audit below shows COACH_PRO/COACH_INTERMEDIATE/COACH_BEGINNER are mostly there; the GAP is BEGINNER (still a "nudge"-only register, no impact-clause), the COACH_BEGINNER anchor set predates the observed→impact→prescribe spine, and the deck/harmonic verbs aren't surfaced in the cell vocab. FEATURES §"GOOD actionable lines" + §"Prescribe in DJ verbs" are the lift-targets. |
| COACH-02 | Persona refactor EXTENDS the in-flight `live-tuning-or-brain` work; does NOT add a new mode (preserves `_CELLS`/`_VALID_MODES`); flows through both genai and OpenRouter paths. | `dj_cohost.py` feeds ONE `self._prompt_body` to both `generate_content_stream` (genai) and `stream_or` (OpenRouter) — verified. No new key in `_CELLS` needed; sharpen the 3 existing COACH cell constants + the 2 harmonic `task_for_event` arms. |
| COACH-03 | Hype mode is regression-fenced with goldens. | The fence already exists and is GREEN (122 tests): `tests/state/test_coach.py` (task goldens byte-pinned), `tests/prompts/test_matrix.py` (HYPE_INTERMEDIATE byte-identity + per-cell anchor pins), `tests/agent/test_hype_prompt_grounding.py`, `tests/agent/test_persona.py`. Plan adds coach-side anchor-update + a cross-mode "hype untouched" assertion. |
| COACH-04 | Every prescriptive note stays anti-slop/cited; warm tone preserved; no robotic over-correction; cooldown/pacing prevents nagging. | `CitationLinter` strips the whole turn on a fabricated `[key:...]` (existence-only branch) — structural guarantee, verified. Warmth/balance is a prompt-text concern (COACH_PRO already has PROPS + NUDGE-FORWARD arms; BEGINNER/INTERMEDIATE need a positive-callout balance rule). Pacing is the existing event cooldown + single-in-flight gate — no new mechanism. |
</phase_requirements>

## Summary

Phase 61 is a **prompt-text sharpening + golden-fence** phase, not a build. The two layers it must extend already exist and pass tests: (1) the `live-tuning-or-brain` COACH cells in `prompts/matrix.py` (which already carry "BE A REAL COACH", "ONE THING PER TURN", English output, the calm-only TTS tag set, and the `COACH_CLOSING_BLOCK` recency directive) and (2) Phase 60's `KEY_CLASH` / `TRANSITION_OPPORTUNITY` arms in `state/coach.py` (already cited, narrate-only, past-tense, with DJ verbs and a structural anti-invention guard). The real work is: **audit each COACH cell against the observed→impact→prescribe contract, sharpen the gaps (chiefly COACH_BEGINNER), surface the deck/harmonic DJ-verb vocabulary, add a positive-callout balance rule to fence the over-correction-to-cold pitfall, and lock the hype voice behind its existing goldens.**

The observed→impact→prescribe spine is NOT a new framework — it IS the project's existing citation contract (cite the observed event → state impact → prescribe), and it maps directly onto the SBI/AID coaching model from FEATURES. The anti-slop guarantee is **structural, not prompt-trust**: the `CitationLinter` strips the entire turn if the model fabricates a `[key:...]` the registry never observed (existence-only branch). So "prescriptive but grounded" is enforced by code, and the persona layer only needs to teach the *voice*, not police the facts.

**Primary recommendation:** Audit-then-sharpen the three COACH cell constants in `matrix.py` (BEGINNER needs the most: add an impact clause + balance rule + deck/harmonic-verb vocab; INTERMEDIATE/PRO are close — add the balance rule + verb-consistency); leave the Phase-60 harmonic arms in `coach.py` as-is (they already deliver the deck/harmonic voice the grounded way — the persona layer adds nothing structural there, only consistency of verbs); and treat every existing hype + coach golden as a hard fence, updating only the COACH anchor-phrase pins as a deliberate, noted decision.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Coach persona *voice* (tone, verbs, balance) | Prompt cell (`prompts/matrix.py` COACH_* constants) | — | The persona is system-instruction text; it is mode-selected and shared by both LLM paths. |
| Per-event *task* framing (what to say about THIS event) | `state/coach.py` `task_for_event` arms | — | Event-specific instruction tail; harmonic arms (KEY_CLASH/TRANSITION) already own the deck/harmonic voice. |
| Grounded *facts* (keys, decks, moves) | `state/coach.py` `evidence_line` + Phase-60 detector | EvidenceRegistry | The model never computes facts; the system hands pre-decided verdicts + cited atoms. |
| Anti-slop *enforcement* (strip uncited claims) | `coach/citation_linter.py` (response-level) | `prompts/negative_dict.py` (ban list) | Structural binary strip — not prompt-trust. Persona phase relies on it, does not modify it. |
| Mode/skill *selection* | `agent/dj_cohost.py` env-var dispatch (`VIBEMIX_MODE`/`VIBEMIX_SKILL_LEVEL`) | `prompts/matrix.py` `_CELLS`/`_VALID_MODES` | The env-var contract is the no-new-mode invariant. |
| Path independence (genai vs OpenRouter) | `agent/dj_cohost.py` `llm_node` (one `self._prompt_body`) | `agent/openrouter_llm.py` `stream_or` | Both paths consume the SAME system instruction → persona flows through both for free. |

## Standard Stack

No new dependencies. This phase edits prompt-text constants and adds/updates pytest goldens only. The relevant existing modules:

| Module | Role in this phase | Action |
|--------|--------------------|--------|
| `src/vibemix/prompts/matrix.py` | The 6 cell constants + `build_system_instruction` dispatcher + `COACH_TAG_DSL_BLOCK` + `COACH_CLOSING_BLOCK` | EDIT the 3 COACH_* cell constants (sharpen wording) |
| `src/vibemix/state/coach.py` | `task_for_event` (incl. Phase-60 KEY_CLASH/TRANSITION arms), `evidence_line` | AUDIT; likely leave harmonic arms as-is; possibly verb-align MIX_MOVE |
| `src/vibemix/coach/citation_linter.py` | Response-level strip of fabricated cites | DO NOT TOUCH — relied upon, not modified |
| `src/vibemix/agent/dj_cohost.py` | env-var dispatch + dual-path `llm_node` | DO NOT TOUCH — confirm both paths share `self._prompt_body` |
| `tests/prompts/test_matrix.py` | HYPE byte-identity + per-cell anchor pins | UPDATE coach anchor pins (deliberate); HYPE pins stay frozen |
| `tests/state/test_coach.py` | `task_for_event` byte goldens | Verify still green; update only if a coach arm is reworded (noted decision) |
| `tests/agent/test_coach_prompt_grounding.py` | COACH grounding scaffold pins | Extend with new persona assertions |

**Installation:** None.

**Version verification:** Not applicable — no package installs.

## Package Legitimacy Audit

Not applicable — this phase installs no external packages. (Confirmed: edits are to in-repo `.py` prompt constants and pytest files only.)

## Architecture Patterns

### How the persona flows through BOTH LLM paths (COACH-02, verified)

```
                          env: VIBEMIX_MODE=coach, VIBEMIX_SKILL_LEVEL=pro
                                          │
                                          ▼
        dj_cohost.py _resolve_system_instruction()
        → build_system_instruction(skill, "coach", mood)
                                          │
                          ┌───────────────┴────────────────┐
                          ▼  (one string: self._prompt_body)│
                  ┌───────────────────┐          ┌──────────▼──────────┐
                  │ genai path        │          │ OpenRouter path     │
                  │ generate_content_ │          │ openrouter_llm.     │
                  │ stream(           │          │ stream_or(          │
                  │  system_instr=    │          │  system_instruction=│
                  │  self._prompt_body│          │  self._prompt_body) │
                  └─────────┬─────────┘          └──────────┬──────────┘
                            └──────────────┬─────────────────┘
                                           ▼
                       SAME llm_node loop: speculative-head,
                       CitationLinter, filter_for_slop — all intact
```

**Key fact (verified, `dj_cohost.py:811-821` + `447`):** the genai call passes `system_instruction=` from `self._gen_cfg` and the OpenRouter call passes `system_instruction=self._prompt_body` — both derive from the SAME `build_system_instruction(...)` result. **Sharpening the COACH cell text propagates to both paths with zero path-specific code.** COACH-02's "flows through both paths" is satisfied automatically; the plan only needs a test asserting it (e.g. the coach `_prompt_body` substring appears in both the genai `_gen_cfg.system_instruction` and the value passed to `stream_or`).

### Pattern: observed → impact → prescribe IS the citation contract

From `FEATURES.md` §"How to stay grounded while prescriptive" + §SBI/AID:
- **observed** = the cited event/state (`[ev:KEY_CLASH@45.2]`, `[key:A:8A]`, the `recent_moves[8s]` entry, the `decks[...]` block).
- **impact** = what that did to the mix ("they're fighting where the melodies overlap", "muddied the breakdown").
- **prescribe** = the DJ-verb move ("kill B's mids", "cut on the drop", "filter A out").

Hype mode stops after *observed* and *celebrates*; coach mode continues to *impact + prescribe*. **Same grounding, different verb.** Do NOT bolt on a separate SBI/AID framework — lean on the existing `[ev:]`/`[key:]` grammar (`matrix.CITATION_GRAMMAR_BLOCK`).

### Pattern: harmonic facts are pre-decided, voice is narrate-only (Phase 60, verified)

`coach.py:267-316` — the `KEY_CLASH` and `TRANSITION_OPPORTUNITY` arms already:
- hand the model the **system's** verdict ("HARMONIC CLASH confirmed by the system (you do NOT decide this)"),
- supply both decks' cited keys + pre-computed semitone gap,
- instruct DJ-verb prescription ("kill {b_side}'s mids, cut on the drop, filter one out, don't ride the pads"),
- FORBID inventing a key or computing intervals,
- enforce PAST-TENSE on TRANSITION (latency guard, Pitfall 3),
- offer the single-space silence escape.

The `coach.py:266` comment literally says *"Phase 61 owns the persona voice; this phase keeps to the grounded FACTS."* **The persona layer's job re: harmonic awareness is consistency, not new logic** — ensure the COACH cell vocab uses the same DJ verbs these arms emit (kill/cut/filter/swap/ride), so a harmonic turn reads in the same voice as a MIX_MOVE turn. Likely NO edit to these arms is needed; verb-align the cell prose to them.

### Anti-Patterns to Avoid

- **Adding a 7th cell / new mode key.** Forbidden — breaks `_VALID_MODES` env-var contract. Sharpen the 3 existing COACH constants.
- **Re-baselining a tripped hype golden to "make it pass."** Pitfall 5/8 — investigate the diff, revert the shared-scaffold change, re-route as mode-specific. Any hype-golden change is a deliberate noted decision.
- **Teaching the model to compute keys/intervals/clash verdicts in the prompt.** The detector decides; the linter strips fabrications. Prompt stays narrate-only on harmonic facts.
- **Swinging to pure-critique (over-correction).** Pitfall 7 — a coach that only flags problems is slop in a different costume. Add/keep the balance rule (COACH_PRO already has it via the PROPS/NUDGE-FORWARD arms; BEGINNER/INTERMEDIATE need it).
- **Present-tense imperatives on transitions.** LLM+TTS latency makes "bring the fader down now" arrive 5-10s late. Past-tense only (already enforced on TRANSITION_OPPORTUNITY).

## COACH Cell Audit (the core deliverable — what's already actionable vs what still narrates)

Direct read of `matrix.py` (baseline `92f2a67` live-tuning WIP, lines cited):

### COACH_PRO (`matrix.py:502-543`) — ALREADY STRONG, minor verb-consistency only
**Already actionable (keep):**
- The DESERVED CRITIQUE + FIX arm explicitly bans bare-weakness endings and demands the fix in the same line: *"NEVER end on a bare weakness ... thin lead — push 3-5k", "dry mids — touch of plate reverb"* (`:506`). This IS observed→impact→prescribe.
- The NUDGE FORWARD arm ("this is begging for a darker roller", "good spot to bring the sub back") and the PROPS arm — these are the **built-in over-correction guard** (Pitfall 7): not a relentless critic. (`:507-508`)
- "Every line gives him something to ACT on" + "Vary the shape turn to turn — don't run the same ... line every time" (`:510`, `:520`) = anti-nag + anti-repeat.
- DJ verbs already present: kill/cut/filter/swap implied via "pull deck B's low EQ", "dip 2-4k", "duck the pads".
- Calm DELIVERY block + calm-only tags (`:528`) = the warmth/non-robotic anchor.

**Gap to sharpen:** the verb vocabulary in the prose is rich but doesn't include the explicit DJ-verb LIST from FEATURES (kill, swap, cut, filter, wait, tighten, ride, pull, push). Surface the canonical verb set so harmonic turns (which use exactly these verbs) read in the same register. LOW-effort: a one-line verb anchor.

### COACH_INTERMEDIATE (`matrix.py:463-493`) — MOSTLY ACTIONABLE, needs balance rule
**Already actionable (keep):**
- CONCRETE FEEDBACK arm: "name what + when. 'Kicks stepped on each other for a half-bar' beats 'kicks were off'" (`:474`). Observed + impact.
- HONEST arm: "flattery is worse than silence ... say what wasn't and how to fix" (`:476`) — has the prescribe half.
- Anchor phrases already prescriptive: "build released on the 3 — try the 1", "EQ killed the lows too aggressively" (`:464-472`).

**Gaps to sharpen:**
1. **No positive-callout balance rule** — unlike COACH_PRO, the intermediate cell has no "roughly half your turns are a quick 'that worked'" rule. This is the over-correction-to-cold risk (Pitfall 7). ADD a balance rule mirroring PRO's PROPS arm.
2. **"how to fix" is implied, not structurally required** — tighten to the observed→impact→prescribe spine ("name it AND say the move in the same line", borrowed from PRO).
3. **Deck/harmonic verbs absent** — surface the canonical DJ-verb set.

### COACH_BEGINNER (`matrix.py:426-455`) — WEAKEST, needs the most sharpening
**Already partially there:**
- "ONE THING PER TURN ... Pick the most actionable nudge. If everything sounded clean, just say so" (`:437`) — single-note + don't-invent-a-problem (good).
- "ENCOURAGING TONE — when something works, say it works" (`:439`) — the balance rule IS here for beginner (good, keep).
- Anchor phrases mix narration + prescription: "the cut felt early — try 8 bars later" (prescriptive ✓) but also bare "more space", "rushing the blend" (`:434-436`) which name a problem without the *impact* clause.

**Gaps to sharpen (this cell is the headline COACH-01 work):**
1. **No impact clause.** Beginner anchors jump observed→prescribe and skip *why it matters* — exactly the level where the impact ("muddied the breakdown" = why) teaches most. Reframe anchors to the full observed→impact→prescribe shape (the existing "low boost muddied the breakdown" is the model — extend the rest to match).
2. **"nudge"-only register risks vagueness.** "give the build more space" / "more space" name no observed mechanic. Sharpen toward a cited observation + a concrete DJ verb, kept gentle ("the build felt rushed — try holding it 8 bars longer").
3. **No deck/harmonic awareness** — beginner cell never mentions decks/keys. Add a gentle, grounded-only path so a KEY_CLASH event at beginner level reads as "those two tracks were fighting a bit — try cutting one in cleaner" (verb: cut, gentle framing).

### Concrete GOOD-vs-BAD targets (lift from FEATURES.md §126-147)

GOOD (the sharpening target — observed→impact→prescribe, DJ verbs):
- "Both basslines are running — kill the lows on the outgoing deck."
- "Deck B's 2A against your 8A — three steps off. Cut it on the drop, don't ride the pads."
- "That blend's been 32 bars and the keys don't sit — tighten it or filter A out."
- "You're in the breakdown — good window, bring B's intro in now." (past-tense in our prompts: "that was a good window — you could've brought B's intro in there")

BAD (retire residuals of these from cells):
- "This is fire! The energy is unreal right now." (pure narration)
- "Nice transition!" (names nothing — the difference between hype and coaching is the prescription)
- Adjective-soup ("vibey", "epic", "deeply").

**Rule from FEATURES §147:** "Prescribe in DJ verbs: kill, swap, cut, filter, wait, ride, tighten, bring in. Never adjective-soup." Surface this verb list in each COACH cell.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Stripping fabricated harmonic/key claims | A new prompt-side "don't invent keys" enforcement loop | The existing `CitationLinter` existence-only `[key:...]` strip | Structural binary strip already proven (Phase 59/60); prompt-trust is weaker. |
| Deciding clash verdict / semitone gap | Prompt asking the LLM to "check if these clash" | Phase-60 detector pre-computes it; arm hands the verdict | LLM key-math is a hallucination class; the code already owns it. |
| Pacing / anti-nag throttle | A new cooldown timer in the persona layer | The existing per-event cooldown + single-in-flight `trigger_state` gate | No new mechanism — pacing is already enforced upstream of the prompt. |
| Mode/skill selection | A new config key or persona registry | `VIBEMIX_MODE`/`VIBEMIX_SKILL_LEVEL` env vars → `_CELLS` | The env-var contract IS the no-new-mode invariant. |
| Positive/critique balance | A turn-counter that forces 50/50 | A prompt-text balance RULE (like COACH_PRO's READ THE MOMENT) | Forcing a quota produces fake props; the rule + the repeat-ban is the validated approach. |

**Key insight:** Almost everything load-bearing already exists. The phase's value is *consistency + completeness of the voice* over a grounding/enforcement stack that's already structural. Resist building new machinery.

## Common Pitfalls

### Pitfall 1: Shared-prompt edit silently regresses hype (PITFALLS §8, the load-bearing risk)
**What goes wrong:** `matrix.py` and `coach.py` are shared across hype + coach. A coach-only wording change in a *shared* block (the `_ANTI_SLOP_FOOTER`, `CITATION_GRAMMAR_BLOCK`, or a shared `task_for_event` arm like MIX_MOVE/HEARTBEAT) shifts hype output too.
**Why it happens:** The COACH cells are separate constants, but the appended blocks (footer, grammar, TTS DSL) and the `task_for_event` arms are shared.
**How to avoid:** Edit ONLY the three COACH_* cell constants and (if needed) the harmonic arms that fire only in coach contexts. Keep mode-specific text in mode-specific constants. Run the full fence after every edit: `tests/prompts/test_matrix.py` + `tests/agent/test_hype_prompt_grounding.py` + `tests/agent/test_persona.py` + `tests/state/test_coach.py` must stay green.
**Warning signs:** HYPE_INTERMEDIATE byte-identity test trips; any hype anchor test fails; `test_persona_03` substring drift.

### Pitfall 2: Re-baselining a tripped hype golden (PITFALLS §5/8)
**What goes wrong:** A hype golden trips and the reflex is to update the expected string "to make it pass."
**Why it happens:** Goldens feel like noise when they break on an "unrelated" change.
**How to avoid:** A tripped hype golden = a real regression. INVESTIGATE the diff, revert the shared-scaffold change, re-route the coach change as mode-specific. Any deliberate hype-golden change requires an explicit decision note (as the live-tuning silence-bias divergence at `matrix.py:269-276` was documented).

### Pitfall 3: Over-correction to cold/robotic (PITFALLS §7)
**What goes wrong:** "Actionable, not hype" gets read as "remove warmth, add critique" → the coach becomes a fault-finding QC bot, a nag.
**Why it happens:** Sharpening prescriptiveness without preserving the positive-callout balance.
**How to avoid:** Keep/add the balance rule to all three cells (PRO already has it; BEGINNER has ENCOURAGING TONE; INTERMEDIATE needs it). Keep the calm-but-warm DELIVERY block + `COACH_CLOSING_BLOCK` ("trust your own ears and judgment"). Validate with a Kaan-ear pass — "~half turns are a fresh positive callout, no praise phrase repeats" (PITFALLS §300).
**Warning signs:** Every turn is a critique; praise lines repeat; tone reads clipped/QC.

### Pitfall 4: Present-tense imperative on a transition (PITFALLS §3, latency)
**What goes wrong:** Coach says "bring the fader down now" — arrives 5-10s late, after the moment passed.
**Why it happens:** Live-imperative phrasing on time-sensitive moves.
**How to avoid:** Already enforced on TRANSITION_OPPORTUNITY (past-tense only). Keep beginner/intermediate transition wording past-tense too ("that was a good window").

### Pitfall 5: Drifting the COACH_TAG_DSL into hype tags
**What goes wrong:** Coach mode leaks `[excited]`/`[fast]` → reads as fake hype.
**Why it happens:** The full DSL advertises those; coach must use the calm-only set.
**How to avoid:** `build_system_instruction` already routes coach mode to `COACH_TAG_DSL_BLOCK` (`matrix.py:789-793`) — do NOT undo this gate. The calm set is `[chill]/[whisper]/[slow]/[laugh]`.

## Code Examples

### Verified: dual-path persona propagation (the COACH-02 proof point)
```python
# Source: src/vibemix/agent/dj_cohost.py:811-821 (verified read)
if <openrouter selected>:
    from vibemix.agent.openrouter_llm import stream_or
    stream = stream_or(
        ...,
        model=self._or_model,
        system_instruction=self._prompt_body,   # <-- same body
    )
else:
    stream = await self._genai_client.aio.models.generate_content_stream(
        model=LLM_MODEL,
        ...,                                      # _gen_cfg.system_instruction
    )                                             #     also = self._prompt_body (line 447)
```

### Verified: the structural anti-slop guarantee (COACH-04)
```python
# Source: src/vibemix/coach/citation_linter.py:46-50 (verified read)
# `key` is EXISTENCE-ONLY: a fabricated [key:A:12B] never observed by the
# poller fails `body in snapshot["key"]` -> the WHOLE turn is stripped.
# Decision is response-level binary. The persona phase RELIES on this; it
# does NOT modify the linter. Prescriptive ≠ unguarded.
```

### Verified: the harmonic arm already owns the deck/harmonic voice (do-not-duplicate)
```python
# Source: src/vibemix/state/coach.py:280-290 (KEY_CLASH arm, verified read)
# "HARMONIC CLASH confirmed by the system (you do NOT decide this): ...
#  Tell Kaan the move in DJ verbs (kill {b_side}'s mids, cut on the drop,
#  filter one out, don't ride the pads). Cite BOTH keys exactly ...
#  Do NOT invent a key and do NOT compute intervals ..."
# Comment at :266 — "Phase 61 owns the persona voice; this phase keeps to FACTS."
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| COACH cells "never name a fader/EQ" hard ban | A real coach names the EQ/filter/blend when worth flagging; model decides topic | live-tuning WIP 2026-05-21 (`COACH_CLOSING_BLOCK`, `matrix.py:226-241`) | The actionable register already landed — Phase 61 audits + completes it. |
| MIX_MOVE arm: "Do NOT name faders/EQs/knobs/controls" | "Name the EQ, filter, or move ... you decide what matters this moment" | live-tuning WIP (`coach.py:238-251`, pinned in `test_coach.py:279-298`) | The knob-ban is GONE and golden-pinned as gone — do not reintroduce. |
| Coach mode used full hype TTS DSL | Calm-only `COACH_TAG_DSL_BLOCK` (no `[excited]`/`[fast]`) | live-tuning WIP (`matrix.py:209-223`) | Delivery stays even — keep the gate. |

**Deprecated/outdated:**
- The "byte-identical to v4, DO NOT EDIT" lock on HYPE_INTERMEDIATE is now a *constant-relative* identity (the silence-bias was deliberately relaxed `matrix.py:269-276`). It is STILL fenced by `test_prompt_01_hype_intermediate_byte_identical_to_persona` against `persona.SYSTEM_INSTRUCTION` — i.e. they must stay equal to each other. Treat as frozen unless a noted decision says otherwise.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | COACH_BEGINNER is the cell needing the most sharpening (no impact clause, vague nudges, no deck/harmonic path) | COACH Cell Audit | LOW — even if PRO/INTERMEDIATE need more, the audit lists all three; planner sets exact wording (Claude's Discretion per CONTEXT). |
| A2 | No edit to the Phase-60 harmonic `task_for_event` arms is required (only verb-consistency in cells) | Architecture Patterns | LOW — if a wording tweak is wanted, it trips `test_coach.py` goldens, forcing a deliberate noted decision (the correct fence behavior). |

**All other claims are VERIFIED by direct codebase read (file:line cited) and a green test run.**

## Open Questions

1. **Should COACH anchor-phrase pins in `test_matrix.py` be updated, or kept frozen?**
   - What we know: `ANCHOR_PHRASES[("beginner","coach")]` etc. are byte-pinned (`test_prompt_01_each_cell_has_eight_anchor_phrases`). Sharpening BEGINNER's anchors to the observed→impact→prescribe shape WILL trip this test.
   - What's unclear: whether to keep the existing 8 anchors verbatim (sharpen only the surrounding prose) or update the anchor set.
   - Recommendation: Updating COACH anchors is a *deliberate, noted* decision (allowed — unlike hype, coach anchors are this phase's scope). The plan should update `ANCHOR_PHRASES` for the three coach cells in lockstep with the cell edits, with a comment citing this phase. HYPE anchors stay frozen.

2. **Does any shared `task_for_event` arm (MIX_MOVE/HEARTBEAT) need verb-alignment, and would that touch hype?**
   - What we know: MIX_MOVE/HEARTBEAT arms are shared across modes; their goldens are byte-pinned in `test_coach.py`.
   - Recommendation: Prefer NOT editing shared arms. If verb-consistency demands it, it's a cross-mode change requiring both modes' goldens re-checked + a decision note (Pitfall 1). Default: leave shared arms; align verbs in the mode-specific COACH cells only.

## Environment Availability

Not applicable — this phase has no external dependencies (prompt-text + pytest changes only). Test runner is the existing `.venv` (Python 3.12 with livekit/google.genai installed; system python3.14 lacks them).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (with `pytest-mock` for `mocker`) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q tests/prompts/test_matrix.py tests/state/test_coach.py tests/agent/test_coach_prompt_grounding.py tests/agent/test_hype_prompt_grounding.py tests/agent/test_persona.py` |
| Full suite command | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q` (or `uv run pytest -q`) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| COACH-01 | Each COACH cell carries the observed→impact→prescribe spine + DJ-verb vocabulary; retired narration/cheerleading lines | unit | `pytest tests/prompts/test_matrix.py -k coach -x` | ✅ exists (anchor + scaffold pins) — extend with verb-presence + prescribe-clause assertions (Wave 0) |
| COACH-01 | A KEY_CLASH coach prompt prescribes a DJ-verb move and cites both keys | unit | `pytest tests/state/test_coach.py -k "KEY_CLASH or harmonic" -x` | ❌ Wave 0 — add a harmonic-arm voice assertion if not present |
| COACH-02 | No new mode key; `_VALID_MODES == {"hype","coach"}`; the 6-cell `_CELLS` shape unchanged | unit | `pytest tests/prompts/test_matrix.py -k "six_cells or modes" -x` | ✅ exists (`test_prompt_01_six_cells_exist_as_module_constants`) |
| COACH-02 | The COACH `_prompt_body` reaches BOTH the genai `system_instruction` AND `stream_or(system_instruction=...)` | integration | `pytest tests/agent/test_dj_cohost_matrix_dispatch.py -x` | ❌ Wave 0 — add a dual-path assertion (the proof point) |
| COACH-03 | HYPE_INTERMEDIATE byte-identical to `persona.SYSTEM_INSTRUCTION`; all hype anchors present; persona section markers + anti-hallucination substrings intact | unit | `pytest tests/prompts/test_matrix.py tests/agent/test_persona.py tests/agent/test_hype_prompt_grounding.py -x` | ✅ exists — the regression fence (must stay green through every coach edit) |
| COACH-03 | `task_for_event` byte goldens for shared arms (MIX_MOVE knob-ban-gone, HEARTBEAT anti-silence) held | unit | `pytest tests/state/test_coach.py -x` | ✅ exists (byte-pinned) |
| COACH-04 | Fabricated `[key:...]` strips the whole turn (anti-slop structural) | unit | `pytest tests/coach/ -k linter -x` (linter contract; verify path) | ✅ exists (CitationLinter) — add a coach-prompt-context assertion if missing (Wave 0) |
| COACH-04 | Coach cell carries a positive-callout balance rule (anti over-correction) per skill level | unit | `pytest tests/prompts/test_matrix.py -k "feedback_bias or balance" -x` | ✅ partial (`test_prompt_01_coach_mode_includes_feedback_bias`) — extend to assert the balance/positive rule (Wave 0) |
| COACH-04 | Calm-only TTS tag set in coach mode (no `[excited]`/`[fast]`) | unit | `pytest tests/prompts/test_matrix.py -k "tag" -x` | ❌/partial Wave 0 — assert `COACH_TAG_DSL_BLOCK` routing for coach |

### Sampling Rate
- **Per task commit:** the Quick run command above (the full fence subset — ~1.3s, all 5 fence files).
- **Per wave merge:** `PYTHONPATH=src python3 -m pytest -q` (full suite).
- **Phase gate:** Full suite green + a Kaan-ear pass (the anti-slop quality bar: ~half coach turns are fresh positive callouts, no repeated praise, prescriptive-not-narration) before `/gsd:verify-work`.

### Wave 0 Gaps
- [ ] `tests/prompts/test_matrix.py` — add per-COACH-cell assertions: (a) DJ-verb vocabulary present (kill/swap/cut/filter/tighten/ride), (b) a prescribe-clause / "in the same line" rule present, (c) a positive-callout balance rule present, (d) coach-mode routes to `COACH_TAG_DSL_BLOCK`. Update the three COACH `ANCHOR_PHRASES` sets in lockstep with cell edits (deliberate, noted).
- [ ] `tests/agent/test_dj_cohost_matrix_dispatch.py` — add the dual-path assertion: a coach `_prompt_body` substring appears in BOTH the genai `_gen_cfg.system_instruction` and the value passed to `stream_or` (COACH-02 proof).
- [ ] `tests/state/test_coach.py` — add (or confirm) a KEY_CLASH/TRANSITION voice assertion (DJ-verb move + both keys cited + no-invent guard) so the harmonic voice is fenced.
- [ ] `tests/agent/test_coach_prompt_grounding.py` — extend with an anti-slop assertion that a fabricated key strips (or that the cited-only contract holds in a coach context).
- Framework install: none — `.venv` already has pytest + pytest-mock.

*All hype-side fence files already exist and are GREEN (verified: 122 passed across `test_coach.py` + `test_matrix.py` + `test_coach_prompt_grounding.py`).*

## Security Domain

> `security_enforcement` not set to false; included.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth surface in this phase. |
| V3 Session Management | no | No sessions. |
| V4 Access Control | no | Local-only prompt text. |
| V5 Input Validation | yes | Persona fragments + harmonic facts are FIXED constants / detector-supplied — no user text enters the prompt body (anti-prompt-injection: `MOOD_PERSONAS`/`TTS_TAG_DSL_BLOCK` are fixed strings, `matrix.py:46-49`, `:157-163`). Maintain this — never interpolate user input into a COACH cell. |
| V6 Cryptography | no | None. |

### Known Threat Patterns for {prompt-text persona on local co-host}
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Prompt injection via persona/event fields | Tampering | Fixed-constant cells + enum-selected fragments; detector-supplied (not user-supplied) harmonic facts. No `.format()` on user data (cells use `.replace("{mood_persona}", ...)` with a fixed dict value). |
| Hallucinated key/clash leaking to user as fact | Information disclosure (false) | `CitationLinter` existence-only `[key:...]` strip — whole-turn binary strip on fabrication. Structural, not prompt-trust. |
| Library data exfiltration via harmonic feedback | Information disclosure | Out of this phase's scope; only derived/cited state leaves the prompt builder, never raw collection (matches Gemini-only + Bravoh-proxy model, PITFALLS §279). |

## Sources

### Primary (HIGH confidence — codebase, read directly this session)
- `src/vibemix/prompts/matrix.py` — the 6 cells, `build_system_instruction`, `COACH_TAG_DSL_BLOCK`, `COACH_CLOSING_BLOCK`, `MOOD_PERSONAS`, citation grammar block.
- `src/vibemix/state/coach.py` — `AICoach.evidence_line`/`task_for_event`/`build_prompt`, Phase-60 KEY_CLASH/TRANSITION arms, MIX_MOVE arm, no-`phase=` invariant.
- `src/vibemix/agent/dj_cohost.py` — env-var dispatch, dual-path `llm_node` (genai + `stream_or`) sharing `self._prompt_body`.
- `src/vibemix/agent/openrouter_llm.py` — `stream_or(system_instruction=...)` confirms persona-via-prompt-body on the OpenRouter path.
- `src/vibemix/coach/citation_linter.py` — existence-only `[key:...]` strip, response-level binary.
- `tests/state/test_coach.py`, `tests/state/test_coach_prompt_grounding.py`, `tests/state/test_coach_prompt_diet.py`, `tests/prompts/test_matrix.py`, `tests/agent/test_coach_prompt_grounding.py`, `tests/agent/test_hype_prompt_grounding.py`, `tests/agent/test_persona.py` — the regression fence (122 passed, verified).
- `.planning/REQUIREMENTS.md` — COACH-01..04 definitions.

### Secondary (project research, HIGH confidence — in-repo)
- `.planning/research/FEATURES.md` §"GOOD actionable lines" / §"BAD hype/slop lines" / §"Prescribe in DJ verbs" / §SBI-AID coaching model.
- `.planning/research/PITFALLS.md` §7 (over-correction to cold/nag), §8 (shared-prompt refactor breaks hype), §5 (re-baseline), §3 (latency past-tense).
- `.planning/phases/61-actionable-not-hype-coach-persona/61-CONTEXT.md`.

### Tertiary (LOW confidence)
- None — no external/web sources needed for a prompt-text + golden-fence phase.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no deps; all target modules read directly.
- Architecture (dual-path, harmonic-arms-own-the-voice, structural anti-slop): HIGH — file:line verified + green test run.
- COACH cell audit: HIGH — cells read line-by-line; gaps are concrete.
- Pitfalls: HIGH — pulled from in-repo PITFALLS.md cross-checked against the live code.

**Research date:** 2026-05-21
**Valid until:** 2026-06-20 (stable — internal prompt code, no fast-moving external surface). Re-check if the `live-tuning-or-brain` branch lands further COACH-cell edits before planning.
