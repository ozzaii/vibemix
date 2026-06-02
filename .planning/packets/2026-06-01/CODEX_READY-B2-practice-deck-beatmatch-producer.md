# CODEX_READY — Practice-Deck Loop: the `BEATMATCH_GRADED` Producer (B2)

> The headline DJ skill the product **cannot currently credit**. Beatmatching is permanently capped at "Competent" (`_HONEST_UNCREDITABLE_V11`) because the consumer exists but **no producer fires `BEATMATCH_GRADED`**. This is the single build that uncaps Mastered beatmatching and lights the whole owned-deck cluster (`MiniDeck`, `grade_beatmatch`, `BeatGrid`). It's the credibility floor of the paid coach tier (MONEY doc Phase 2, "non-optional").
> **Owner: Codex A.** Claude read-only (this packet + LIVE verify). Re-verified at HEAD `e49b2f63`. CRITIQUE L1, WIRING backlog #4 (the one BUILD that cascades), FUTURE B2, goldmine H1.

## Why this is a BUILD, not a wire (and why it's now lower-risk)
Every piece it needs already exists and is tested — only the **driver loop** is missing:
- **Consumer is waiting:** `learn/skill_recognizer.py:154` `if ev_type == "BEATMATCH_GRADED"` credits `"beatmatching"` **only** when `extra["tempo_matched"]` AND `extra["phase_locked"]` AND not `extra["abstain"]` (a LOCKED grade; drift/trainwreck/abstain credits nothing — anti-slop by design).
- **The grader is pure + tested:** `learn/beatmatch_judge.py:83` `grade_beatmatch(grid_a, grid_b, state) -> BeatmatchGrade`; `:63` `grade_to_event_extra(grade) -> dict` is **the canonical payload** and its docstring (`:69-74`) is the spec: *"a future owned-deck practice loop must fire a `BEATMATCH_GRADED` event carrying this payload AND register the matching `("ev","BEATMATCH_GRADED", t_session)` citation."*
- **The owned decks exist:** `audio/miniplayer.py:99` `MiniDeck` — fractional source-frame cursors, `render_block(n)` (`:130`), *"exact beat phase at every sample"* (`:6`). Because the learn module OWNS both decks, the grade is **MEASURED, not inferred** — no live-DSP risk, this is the one place a Mastered claim is fully grounded.
- **The grid exists:** `audio/grid.py:26` `BeatGrid` (constant-tempo `anchor + k·beat_len`, `from_anlz`).

The build is the loop that runs the two MiniDecks under user control, computes the grade against ground truth, and emits the cited event. NOT-FOUND today: `learn/practice_loop.py` / `practice_runtime.py` (verified `ls`).

## 1. New module — `learn/practice_loop.py` (+ `practice_runtime.py` if a session FSM helps)
A learn-mode interactive loop on two owned `MiniDeck`s:
- Load two tracks (or two regions of one), each with a `BeatGrid` (from ANLZ via `from_anlz`, or a known synthetic grid for the lesson). The user practices matching deck B to deck A (pitch/nudge controls — reuse the existing learn IPC surface).
- Each evaluation tick: build the live `DeckState` from the MiniDeck cursors (the decks give exact phase — `miniplayer.py:86`), call `grade_beatmatch(grid_a, grid_b, state)`.
- On a **LOCKED** grade (`tempo_matched ∧ phase_locked ∧ ¬abstain` — read the booleans, resilient to verdict-string drift, exactly as the consumer does): fire `Event(("ev","BEATMATCH_GRADED", t_session))` carrying `grade_to_event_extra(grade)` as `extra`, AND `evidence_registry.write("ev","BEATMATCH_GRADED", t_session)` so the citation resolves (the consumer + Earned Wall credit path then runs through `runtime/coach.py:177 recognize`).
- A drift/trainwreck/abstain grade emits **nothing creditable** (may still narrate "you're an eighth behind, nudge up" — the grade's `errors`/`score` are for narration, the booleans gate the credit). This preserves the anti-slop boundary.
- If `MiniDeck` lacks an explicit cursor-set/`seek`, add one (the cursor is already a fractional source-frame double — `:86` — a setter is trivial; the wiring map flagged this ~½d).

## 2. Drive it from learn mode (the surface)
Wire the loop into the learn FSM that already exists (`learn/runtime.py`, `learn/ipc_handlers.py:153` `register_learn_handlers`, live at `__main__.py:2523`). A "Beatmatch practice" lesson: load → practice → on LOCKED, the Earned Wall flips `beatmatching` toward Mastered (the fire-once Mastered vocal already exists). Reuse the existing learn IPC channels; do not invent a new transport. (The full lesson UX can be a thin first cut — the *producer* is the unlock; polish follows.)

## 3. Remove the honesty cap — ONLY once the producer is real
`skill_recognizer.py:105` `_HONEST_UNCREDITABLE_V11=("beatmatching",)` and `skill_tree.py:147` exist *because* no producer fired the event. Once the LOCKED-grade producer + citation are in and tested, lift `beatmatching` out of the uncreditable set so it can reach Mastered. **Do this in the SAME change as the producer** — never before (an uncapped skill with no producer would silently never credit, the worse failure). Keep the cap if the producer isn't wired.

## 4. Hard guardrails (Invariant #2/#3)
- **Only a LOCKED, measured grade credits.** Inferred / live-master / single-deck states never emit `BEATMATCH_GRADED`. The owned-deck loop is the only legitimate emitter.
- The citation `("ev","BEATMATCH_GRADED",t)` MUST be registered before/with the event so the credit resolves (un-cited → no credit, by the cardinal gate).
- No new third-party dep. Don't touch single-writer `MusicState`, the live co-host reaction loop, or the genre detectors.

## Acceptance
**SRC (Codex):** `tests/learn/test_practice_loop.py` — a LOCKED scenario (matched grids + locked phase) emits exactly one `BEATMATCH_GRADED` with the `grade_to_event_extra` payload + registered citation, and `recognize` credits `["beatmatching"]`; drift/trainwreck/abstain emit no creditable event; the honesty-cap removal is covered (beatmatching can now reach Mastered through the loop, and ONLY through it). Existing `skill_recognizer`/`skill_tree`/`beatmatch_judge` tests stay green; ruff clean.
**LIVE (Claude verifies on Kaan's rig):** run the beatmatch practice lesson, actually lock two decks → Earned Wall credits beatmatching toward Mastered with a resolved `[ev:BEATMATCH_GRADED]` citation; deliberately train-wreck → no credit. The headline skill becomes earnable.
**Proof tiers:** SRC → LIVE → PKG.

## Gate
**`vibemix-grounding-review` REQUIRED** — it creates a new creditable claim path and lifts an honesty cap; the review must confirm only a measured LOCKED grade credits and the citation always resolves. Effort ~2–3d (the loop + grid feed + the learn-mode surface; the grader/decks/consumer are done).
