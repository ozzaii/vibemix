# Phase 60: Harmonic-Feedback Confidence Gate - Context

**Gathered:** 2026-05-21
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous `fully` — recommended grey-area answers auto-accepted; the Kaan-ear veto on HARMONIC-03 surfaces as the one human gate)

<domain>
## Phase Boundary

This phase makes the co-host's harmonic + transition feedback **provably correct**. It owns the **firing logic** that Phase 59 deliberately deferred: detect a key clash only when the *code* has deterministically confirmed one on simultaneous melodic content in clashing keys, withhold it on percussive/atonal or breakdown content, and stay conservative against wrong key tags. This is the **hard hallucination gate** — a false clash is the most credibility-destroying failure for a tool claiming harmonic expertise — so it gets a **Kaan-ear veto** before it can ship.

**In scope:** the deterministic Camelot relationship logic (`harmonics.is_clash`/`compatible` — the slots Phase 59 grep-gated to 0); the `KEY_CLASH` + `TRANSITION_OPPORTUNITY` *detectors* (firing the event types Phase 59 registered); the percussive/atonal + breakdown suppression gate; the conservative confidence gate (adjacent-Camelot = safe, low-confidence keys suppressed, ambiguous deck-resolution suppressed); the actionable transition-execution feedback notes; the Kaan-ear veto harness.

**Out of scope:** the deck-state data + `key:` evidence source + event-type registration (all shipped in Phase 59 — build on them); the actionable-not-hype persona refactor (Phase 61 — this phase produces the *grounded harmonic facts*, Phase 61 sharpens the *voice* that delivers them); the pill UI (Phase 62).
</domain>

<decisions>
## Implementation Decisions

### Deterministic Camelot Logic (the anti-slop core)
- Camelot-wheel relationships are a **deterministic Python lookup table** in `harmonics.py` (extends the shipped `to_camelot`). `is_clash(a, b)` / `compatible(a, b)` are pure, unit-table-tested functions. **The LLM NEVER computes key intervals** — it only narrates a clash the code already confirmed, with both decks' keys cited (`[key:A:...]` + `[key:B:...]`).
- The wheel encodes: perfect match (same Camelot), adjacent (±1 number, same letter = energy ±; safe), relative major/minor (same number, swap A/B; safe), +7/−7 (5 hours around = perfect-fifth, reachable). A genuine **clash = the dissonant cases** (notably one-semitone-apart melodic overlap), NOT a one-step Camelot move.
- Critical theory rule (from research): a one-step Camelot move (8A→9A) is SAFE; the disaster is two melodic tracks **a semitone apart overlapping**. Reason about *simultaneous melodic overlap*, not endpoint key.

### Suppression Gate (runs BEFORE any clash note fires)
- **Percussive/atonal + breakdown suppression runs first.** No clash call on two drum/tool tracks, and none during a breakdown/acapella where keys don't matter. Require simultaneous **melodic** overlap in both decks above an energy floor with `audible_deck == "mix"` (both decks contributing).
- Reuse the existing phase/energy signals (`phase.py` semantics, the `PEAK_FLOOR_RMS` family) for the breakdown/melodic-content determination — do NOT invent a new detector stack.

### Conservative Confidence Gate (the headline risk control)
- **Conservative by default.** Suppress: one-step-off-Camelot pairs (adjacent = safe), low-confidence keys (below the deck-cite floor from Phase 59), and ambiguous deck-resolution (the cross-deck-suppression path — if the 2nd deck isn't independently resolved, no clash).
- Tuning **accounts for the ~57–70% library key-tag accuracy band** — when in doubt, stay silent. Under-flagging is acceptable; over-flagging (a false clash on a pair Kaan would happily mix) is the failure mode that trips the gate.
- **Ships only after a Kaan-ear veto** pass against his real disagreed-pairs corpus (the one human gate this phase — surfaced as KAAN-ACTION, conservative default = detector stays gated/quiet until validated).

### Transition-Execution Feedback
- Concrete, actionable **blend notes** (EQ bass-swap, phrase alignment, where to start/end the blend), scoped strictly to what is grounded in deck-state. **Retrospective / past-tense** — no mid-blend present-tense imperatives the co-host can't time precisely.
- **No advice emitted when the underlying signals aren't available** (e.g. no phrase grid → no phrase-alignment note). Silence over a guess.
- Anti-features held (from REQUIREMENTS Out of Scope): no next-track recommendation, no 1–10 transition scoring.

### Claude's Discretion
- Exact clash-confidence thresholds, the energy floor for "melodic content", the cooldown interplay with the Phase-59-registered values (KEY_CLASH 28s / TRANSITION_OPPORTUNITY 20s), and the Kaan-ear corpus format — set at plan time from research + the shipped `phase.py`/`event_detector.py` patterns.
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets (shipped in Phase 59)
- `src/vibemix/state/harmonics.py` — `to_camelot()` shipped; `is_clash`/`compatible` are the deferred slots (grep-gated to 0 in Phase 59) this phase implements.
- `MusicState.deck_state` (decks + per-deck camelot/confidence) — the grounded input the detectors read.
- `key:` evidence source + `CitationLinter` (existence-only) — harmonic claims are already citable; the detector must only cite keys the registry observed.
- `KEY_CLASH` (priority 7, 28s cooldown) + `TRANSITION_OPPORTUNITY` (priority 5, 20s) registered in `EVENT_PRIORITY`/`MIN_EVENT_GAP_PER_TYPE` — this phase adds the *firing* in `event_detector.py`.
- `phase.py` semantics + `PEAK_FLOOR_RMS` family — for breakdown/melodic-content suppression.
- The coach stub arms (`task_for_event`) Phase 59 left for these two event types.

### Established Patterns
- `EventDetector.detect()` reads `MusicState` diffs → typed `Event`s with per-type cooldowns (the firing pattern to follow).
- Anti-slop: the detector must register/cite real `key:` evidence; the linter strips any uncited harmonic claim.
- "Trust the audio" / honest `unknown`; conservative-by-default; Kaan-ear veto as the human gate (precedent: Phase 42/16 ear-test regime).

### Integration Points
- `harmonics.py` (is_clash/compatible), `event_detector.py` (the two new detectors), `coach.py`/`prompts/matrix.py` (the grounded harmonic fragment the detector hands the coach — Phase 61 sharpens the voice).
- Research: `.planning/research/{FEATURES,PITFALLS,SUMMARY}.md` (FEATURES has the harmonic theory depth; PITFALLS has the false-clash risk + percussive-suppression mandate).
</code_context>

<specifics>
## Specific Ideas

- The harmonic feature is the **strongest anti-slop play in the product** — a Camelot clash is math-checkable, so the AI can be *proven* right. Lean into that: the detector confirms, the LLM narrates.
- The percussive-suppression gate is the canonical-slop guard — flagging a clash on two atonal techno/tool tracks is exactly the failure to prevent (and vibemix's genres are percussion-heavy, where key tags are least reliable).
- Kaan-ear veto: the detector ships **gated/quiet by default**; Kaan validates against his disagreed-pairs corpus (pairs he'd happily mix that must NOT flag) before it goes live. Conservative default means no false clash can reach the audience before sign-off.
</specifics>

<deferred>
## Deferred Ideas

- Per-deck low-band/bass-clash DSP (dual-deck separation from a single master stream) — future; the bass-clash note stays P2 until feasible.
- Live audio key-detection as a clash input — only the numpy fallback exists; promoting it is future.
- The actionable-not-hype *voice* refactor — Phase 61 (this phase produces grounded facts, not the persona).
</deferred>
