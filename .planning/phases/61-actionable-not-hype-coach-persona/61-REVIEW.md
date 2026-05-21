---
phase: 61-actionable-not-hype-coach-persona
reviewed: 2026-05-21T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - src/vibemix/prompts/matrix.py
  - tests/prompts/test_matrix.py
  - tests/state/test_coach.py
  - tests/agent/test_coach_prompt_grounding.py
  - tests/agent/test_dj_cohost_matrix_dispatch.py
findings:
  critical: 0
  warning: 2
  info: 3
  total: 5
status: issues_found
---

# Phase 61: Code Review Report

**Reviewed:** 2026-05-21
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Phase 61 sharpened the three COACH prompt cells (`COACH_BEGINNER`, `COACH_INTERMEDIATE`, `COACH_PRO`) in `src/vibemix/prompts/matrix.py` — pure LLM prompt-template prose edits — plus added test fences across four test files. The production code change is small (29 lines in `matrix.py`) and exclusively prompt-string text; no control-flow, dispatcher, or wiring was touched.

I verified the phase's hard invariants against the actual code rather than the docstrings:

- **HYPE goldens byte-stable** — confirmed: the diff touches only `COACH_*` cells. `HYPE_INTERMEDIATE == persona.SYSTEM_INSTRUCTION` and the triple-opt-out returns the constant byte-for-byte. HYPE mode still gets the full 6-tag DSL and never the coach closing block. PASS.
- **No new mode** — `_VALID_MODES == frozenset({"hype","coach"})` unchanged. PASS.
- **Citation grounding intact** — every COACH cell still carries the `--- CITATION GRAMMAR` marker and the `DO NOT SAY` ban footer (appended via `+ _ANTI_SLOP_FOOTER`, unaffected by the prose edits). The existence-only `CitationLinter` contract (fabricated `[key:...]` strips the whole turn) is pinned by a new coach-context test and verified live. PASS.
- **Mode routing isolation** — coach mode routes to the calm-only TTS tag set (`[chill]`/`[whisper]`, no `[excited]`/`[fast]`) and the live production path (`_resolve_prompt_cell` → `build_system_instruction(skill, mode, mood)` with all defaults True) ships the closing block. PASS.
- **Dual-path equality (COACH-02)** — `_gen_cfg.system_instruction` and `_prompt_body` are literally the same `prompt_body` object (dj_cohost.py:447 + :816). The dual-path test asserts genuine behavior, not a tautology. PASS.
- **No anchor regression** — all 8 `COACH_PRO`/`COACH_INTERMEDIATE`/`COACH_BEGINNER` anchors still literally present; new anchors do not collide with `NEGATIVE_PHRASES` (no self-ban). PASS.
- **Full suite** — 153 tests pass across the four test files.

No correctness, security, or grounding defects found. The findings below are quality/robustness observations on the test fences and one prompt-policy risk worth flagging for the hallucination gate.

## Warnings

### WR-01: Coach prose lifts the EQ/control-naming bans — verify against the hallucination gate

**File:** `src/vibemix/prompts/matrix.py:226-241` (`COACH_CLOSING_BLOCK`) and `src/vibemix/state/coach.py:246-248` (MIX_MOVE task)
**Issue:** The new `COACH_CLOSING_BLOCK` ("trust your own ears and judgment, and YOU decide what's worth saying") together with the already-lifted MIX_MOVE clause ("Name the EQ, filter, or move if that's genuinely what's worth flagging — you're a pro, you decide what matters") deliberately removes the old hard ban on naming faders/EQ/knobs. This is a Kaan-directed product decision (documented in the inline comments and `test_coach.py:279-298`), not a code bug. However, the project's central principle is "grounded Gemini, not better prompting" with a hard hallucination gate (CLAUDE.md: "No release until verification phase confirms reactions are tied to real events"). Telling the model "you decide what matters" while it only receives `recent_moves[8s]` labels (not which physical EQ band moved) widens the surface for the model to assert a specific control move that the evidence packet did not actually ground. The `[key:...]`/`[ev:...]` citations are linter-enforced, but a bare prose claim like "you killed the deck-B lows" carries no citation and is NOT caught by the response-level `CitationLinter` (it only validates emitted `[...]` atoms).
**Fix:** No code change required — this is a prompt-policy / verification-gate concern. Confirm in the Phase 16 DJ-ear verification pass that coach mode does not invent specific EQ-band/control moves the `recent_moves` evidence didn't supply. If hallucinated control-naming surfaces, re-tighten the MIX_MOVE clause to "name a control only when `recent_moves[8s]` cites that exact move." Flagging so the lifted ban is an explicit, tested item in the hallucination gate rather than an assumed-safe prose change.

### WR-02: `test_prompt_61_coach_carries_positive_callout_balance` marker list is broad enough to false-pass on incidental prose

**File:** `tests/prompts/test_matrix.py:665-687`
**Issue:** The balance-rule assertion accepts any of `["props", "encouraging", "balance", "when something works", "say it works", "when a move", "credit it", "call it"]`. Two of these (`"call it"`, `"credit it"`) are short, generic fragments that appear inside the DJ-verb / observed→impact prose for reasons unrelated to a positive-callout balance rule. I verified the current cells match on *intended* markers (beginner: `encouraging`/`when something works`; intermediate: `balance`/`credit it`; pro: `props`/`credit it`), so the test is currently sound. But a future edit that strips the explicit "POSITIVE-CALLOUT BALANCE" / "ENCOURAGING TONE" sections while leaving a stray "call it" in the prescribe prose would keep this test green — the test would no longer fence what its docstring claims ("fails if a cell has NO balance rule at all"). The fence is weaker than its stated contract.
**Fix:** Tighten to the intentional section markers per cell, e.g. require one of the strong markers `["props", "encouraging tone", "positive-callout balance", "credit it so the feedback"]` rather than the bare `"call it"`/`"credit it"` fragments, or assert per-cell against the specific marker each cell is meant to carry.

## Info

### IN-01: `test_prompt_61_coach_carries_prescribe_same_line_rule` is a literal-substring check that couples tests to one exact phrasing

**File:** `tests/prompts/test_matrix.py:653-662`
**Issue:** The rule check is `assert "same line" in body`. All three coach cells happen to use the exact lowercased phrase "same line" (BEGINNER: "three beats on the SAME line", INTERMEDIATE/PRO: "in the SAME line"). This works today but pins the contract to a single string — a synonym edit ("in one breath", "same breath", which the cells *also* use) would break the fence even though the observed→impact→prescribe rule is still present. Low risk since the phrasing is stable, but the fence asserts a wording, not a behavior.
**Fix:** Optionally broaden to `any(m in body for m in ("same line", "same breath", "one breath", "one line"))` to fence the rule rather than the exact words. Not blocking.

### IN-02: `_COACH_DJ_VERBS` token check can false-pass on unrelated prose

**File:** `tests/prompts/test_matrix.py:634, 639-650`
**Issue:** The DJ-verb fence tokenizes the whole prompt body and checks each verb is present as a word token. The verbs `kill`, `swap`, `cut`, `filter`, `wait`, `tighten`, `ride` are common English words; several (`cut`, `wait`, `ride`, `filter`) also appear in the appended `CITATION_GRAMMAR_BLOCK`, `_ANTI_SLOP_FOOTER`, and TTS-tag blocks that ride on `build_system_instruction(...)` output by default. The test builds the full instruction (`build_system_instruction(skill, "coach")`), so a verb could pass via the shared appended substrate rather than the cell's own DJ-VERB REGISTER. I confirmed all verbs are genuinely present in each cell body itself, so the contract holds — but the test does not actually prove the *cell* carries the register; it proves the *assembled prompt* contains the tokens.
**Fix:** For a stricter fence, tokenize the cell constant (`COACH_BEGINNER` etc.) directly rather than the assembled `build_system_instruction` output, so the test attributes the verbs to the cell under change. Not blocking — current behavior is correct.

### IN-03: Anchor-phrase test docstring claims byte-pinning that the implementation does not enforce

**File:** `tests/prompts/test_matrix.py:71-86` (comment) + `test_prompt_01_each_cell_has_eight_anchor_phrases:285-291`
**Issue:** The `ANCHOR_PHRASES["beginner","coach"]` comment states the list "is byte-pinned against the COACH_BEGINNER cell anchor lines by test_prompt_01_each_cell_has_eight_anchor_phrases." That test only checks each anchor is a substring (`a not in body`) — it does NOT byte-pin the anchor *lines* (it would still pass if the cell added extra anchors, reworded surrounding prose, or changed line order). The phrase "byte-pinned" overstates the guarantee. Cosmetic/doc accuracy only.
**Fix:** Reword the comment to "substring-pinned" (each anchor must appear literally) to match what the test actually asserts.

---

_Reviewed: 2026-05-21_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
