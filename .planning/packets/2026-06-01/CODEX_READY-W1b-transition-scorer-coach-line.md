# CODEX_READY — Wire the 10-dim Transition Scorer into the Live Coach Line (W1b)

> The other half of W1. The spoken **next-track** recommendation already landed and is cited (`runtime/suggestion_voice.py`, `[track:]`/`[mix:]`, abstains when un-citable — verified `coach.py:708`). What's still orphaned is the *richer* engine: the **10-dimension `score_transition_slate`** that grades the blend the DJ is executing — it runs only in the silent pill + Viber, with **zero callers in either coach loop**. This is the line that makes the co-host sound like a coach ("9A→4A, phrases aligned, energy holds — bring it in over the next phrase") instead of a narrator.
> **Owner: Codex A.** Claude read-only (this packet + LIVE verify). Re-verified at HEAD `e49b2f63`. CRITIQUE L2/D2, GOLD Card 4, WIRING backlog #1.

## Why (the gap, precisely)
- `intel/transition_scorer.py:154` `score_transition_slate(...)` → returns a result carrying `.components` (`TransitionScoreComponents:111`), `.risk_flags` (`:150`, e.g. `off_phrase`/`energy_cliff`/`tempo_jump`), `.reasons` (`:151`), and a measured `confidence` (`:381`). Ten signals: semantic/harmonic/bpm/energy_shape/role/phrase/cue_operability/taste/novelty/risk.
- It is **wired into the pill** (`library/next_suggestion.py:688-691` import, `:753` call) and Viber (`toolset.py`) — **NOT into the coach** (`grep score_transition src/vibemix/runtime/coach.py src/vibemix/state/coach.py` = empty, verified).
- So the live co-host can pick a next track and even speak it, but it **never voices a verdict on the transition itself**. The shallow 2-signal `transition_judge` is the only live blend verdict; the rich one sits idle.

## The insertion point is already perfect
`runtime/coach.py:698-716` already has the exact block to extend — it fires on `ev.type in ("TRACK_CHANGE","TRANSITION_OPPORTUNITY")`, holds the `suggestion_service`, the `state`, and the `evidence_registry`, and builds `next_suggestion_voice_line` via a small grounded helper. **Mirror that helper for the transition verdict — same event types, same registry, same abstain-first discipline.**

## 1. New helper — `runtime/transition_verdict_voice.py` (mirror `suggestion_voice.py`)
```python
def build_transition_verdict_voice_line(
    state, *, event_type: str, evidence_registry: EvidenceRegistry | None
) -> str | None:
    """A coach line grounded in the live blend the DJ is executing.
    Derived state, not raw audio proof — so cite like suggestion_voice does:
      [mix:<A_cam>-><B_cam>] for the executed harmonic move (already a citation source),
      [track:<id>] for the incoming candidate if known.
    Abstain (return None) when: no two-deck blend context, score confidence below
    floor, or the verdict can't be represented in the citation grammar."""
```
- Assemble the `scoring_input`/`destination`/`harmonic`/`bpm` exactly as `next_suggestion.py:688-753` does (reuse those builders — do not re-derive), call `score_transition_slate(...)`, and turn `.reasons`/`.risk_flags` into ONE short line. **Speak the risk vocabulary verbatim** (it's already deduped + bounded) — never paraphrase into vibe-slop.
- **Confidence gate:** only speak when the scorer's measured `confidence` (`:381`) clears a floor; below it, abstain (the co-host stays quiet rather than narrate a low-confidence guess — Invariant #3).
- **Citation:** register/emit only atoms that resolve — reuse the `[mix:]` source `suggestion_voice.py` already writes (`evidence_registry.write("mix", ...)`); if you need a new fact, write it to the registry first or abstain. No new citation grammar.

## 2. Wire into the coach loop
In the existing `coach.py:698-716` block, after the suggestion line, build the transition line the same way and stash it (e.g. `ev.extra["transition_verdict_voice_line"]`) for the prompt composer to pick up — single source, no second code path. One blend → at most one verdict line. Respect the in-flight/cooldown discipline already around this block.

## 3. Hard guardrails (anti-slop — Invariant #2/#3)
- **Abstain-first stays the default.** A spoken verdict is the exception, gated by (two-deck context ∧ confidence floor ∧ citable). Never speak on one signal or on the master-only narration case.
- Reuse the existing risk/reason strings — do not invent adjectives. The scorer already refuses to over-claim; keep that refusal.
- Don't touch single-writer `MusicState`, the citation grammar, the slop filter, or the suggestion-voice path that already works.
- No new third-party dep, no spec change.

## Acceptance
**SRC (Codex):** `tests/runtime/test_transition_verdict_voice.py` — emits a risk-cited line when a high-confidence two-deck blend is present; **abstains** (None) when confidence is low / no blend / un-citable; the citation it emits resolves in `EvidenceRegistry`. Extend `tests/runtime/test_coach.py` for the wired call-site. Existing suggestion-voice + coach tests stay green; ruff clean.
**LIVE (Claude verifies on Kaan's rig):** a real harmonic transition with two audible decks → co-host speaks a grounded transition verdict citing `[mix:...]`, `slop_ratio<1`. A master-only / single-deck moment → **no transition line** (abstained). Narrator→coach on the transition axis, proven.
**Proof tiers:** SRC → LIVE → PKG.

## Gate
**`vibemix-grounding-review` REQUIRED** — this changes what the co-host SAYS. The review must confirm the abstain-first default is intact and the confidence/citation double-gate can't license a slop verdict. Effort ~0.5–1d (the engine + inputs are already assembled in `next_suggestion`; this is a helper + one call-site).
