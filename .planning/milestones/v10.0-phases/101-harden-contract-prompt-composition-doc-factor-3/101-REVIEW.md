---
phase: 101-harden-contract-prompt-composition-doc-factor-3
reviewed: 2026-05-28T00:00:00Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - docs/PROMPT-COMPOSITION.md
  - CLAUDE.md
findings:
  critical: 0
  warning: 0
  info: 3
  total: 3
status: clean
---

# Phase 101: Code Review Report

**Reviewed:** 2026-05-28
**Depth:** standard
**Files Reviewed:** 2 (1 new doc, 1 single-line pointer insert)
**Status:** clean (3 Info items, no Critical, no Warning)

## Summary

Doc-only phase closing Factor 3 ("own your context window") from the 2026-05-28 humanlayer/12-factor-agents audit. The 269-line `docs/PROMPT-COMPOSITION.md` enumerates the live-co-host prompt composition contract; `CLAUDE.md` gains a one-line pointer in the Architecture section.

Adversarial verification ran the doc's own Loop 1 grep-verify sweep against current source: **82 path.py:line cites extracted, 0 stale, 0 OOB, 0 blank, 0 file-missing.** Loop 2 anchor-symbol grep passed all 14 expected symbols at the expected lines (including the load-bearing `self._fire(` count of exactly 10 — 9 unique EventTypes + 1 genre-chain re-emit). Spot-checked: `EVIDENCE_SOURCES` frozenset contains the 11 documented tokens exactly; `ACK_ELIGIBLE_EVENTS` contains the 4 documented tokens exactly; the 9-row event table maps 1:1 to `self._fire(...)` call sites at lines 239, 243, 273, 289, 312, 340, 383, 443, 469; cooldown table values match `MIN_EVENT_GAP_PER_TYPE` (TRACK_CHANGE=5.0, PHASE=10.0, LAYER_ARRIVAL=10.0, MIX_MOVE=14.0, HEARTBEAT=45.0, MIC=3.0, MANUAL=1.5, KEY_CLASH=28.0, TRANSITION_OPPORTUNITY=20.0, plus the Phase-17/30 genre-detector cooldowns).

Disjointness verified: `git diff --stat` shows exactly 2 files / 271 insertions; CLAUDE.md gains exactly two lines (a blockquote + the trailing blank), inserted between Cardinal invariant #5 and the "Threading & generation model" subsection. No cardinal invariants altered, no other text touched.

No Critical or Warning findings. Three Info items below note minor drift-risk seams a future maintainer would want to know about — none are bugs.

## Info

### IN-01: Section 8 prose claims a `STALE:` prefix the script never emits

**File:** `docs/PROMPT-COMPOSITION.md:240`
**Issue:** The prose immediately after the Loop 1 script reads "Any line beginning with `STALE:`, `OOB:`, `BLANK:`, or `FILE_MISSING:` is a cite that needs fixing." The script itself only emits three prefixes (`FILE_MISSING:`, `OOB:`, `BLANK:`) — `STALE:` is never appended. Cosmetic only (the loop still functions as documented), but the prose names a prefix that does not exist in the script's output, which will confuse a future contributor running the appendix sweep for the first time.
**Fix:** Either drop `STALE:` from the prose list, or add a fourth `stale.append(f"STALE: ...")` branch covering a fourth failure mode (e.g. a path that resolves but no longer compiles as Python). Lowest-touch fix:
```markdown
Expected output: `stale=0`. Any line beginning with `OOB:`, `BLANK:`, or `FILE_MISSING:` is a cite that needs fixing.
```

### IN-02: §6 quote of `coach.py:818-819` ASCIIfies a Unicode `≥` to `>=` without flagging the substitution

**File:** `docs/PROMPT-COMPOSITION.md:165`
**Issue:** The doc says "Cited from `src/vibemix/state/coach.py:818-819`: 'Saves >=500ms TTFT on the four ack-eligible event classes...'". Source actually reads "Saves ≥500ms TTFT..." (Unicode U+2265 GREATER-THAN OR EQUAL TO). The doc is committed to ASCII-only output (REQ-CONTRACT-04), so the ASCIIfication is correct — but the doc frames it as a verbatim quote ("Cited from ... :") without noting the glyph substitution. A future contributor diffing the quote against source will see a mismatch. Same pattern applies to the em-dashes inside the source docstring at lines 816, 819, 821 (the doc paraphrases around them rather than quoting).
**Fix:** Either soften the framing from "Cited from" to "Paraphrased from" / "Per the docstring at", or add a one-line footnote at first use noting that all quotes are ASCII-rendered.

### IN-03: Doc quotes a specific TTFT savings (`≥500ms`) that depends on Gemini-side latency

**File:** `docs/PROMPT-COMPOSITION.md:165`
**Issue:** The TTFT claim is sourced directly from the `coach.py:818-819` docstring, so this is faithful to current source — but the underlying number is a measurement against a specific Gemini version + a specific prompt size that can drift silently. The cite is accurate today; the number itself is the latent rot risk. Not actionable inside this phase (REQ-FUTURE-A territory — "future model swaps may require re-measuring"), flagged so the contract maintainer knows where to re-measure on the next Gemini model bump.
**Fix:** No code change. If/when the source docstring re-measures, the doc auto-stays-correct because it pulls verbatim — no doc edit needed unless the source number changes.

---

## What was verified

1. **Loop 1 (mechanical cite resolution):** Ran the doc's own Appendix §8.1 Python script. Output: `total_cites=82, stale=0`. Zero `FILE_MISSING`, zero `OOB`, zero `BLANK`.
2. **Loop 2 (anchor-symbol grep):** All 14 expected symbols resolve at the expected lines:
   - `EVIDENCE_SOURCES: frozenset[str]` → line 129 (expected ~129)
   - `EVIDENCE_CITATION_RE: re.Pattern[str]` → line 199 (expected ~199)
   - `_SOURCE_ALT` → line 174 (expected ~174)
   - `ACK_ELIGIBLE_EVENTS: frozenset[str]` → line 54 (expected ~54)
   - `def recall_fragment_for_event` → line 158 (expected ~158)
   - `TRANSITION_SHAPE_RECALL_FRAGMENT_TPL` → line 109 (expected ~109)
   - `VOCABULARY_RECALL_FRAGMENT_TPL` → line 141 (expected ~141)
   - `def build_prompt` → line 796 (expected ~796)
   - `def _evidence_line_compact` → line 533 (expected ~533)
   - `if diet:` → line 826 (expected ~826)
   - `MIN_EVENT_GAP_PER_TYPE: dict` → line 77 (expected ~77)
   - `EVENT_GLOBAL_MIN_GAP` → line 58 (expected ~58)
   - `self._fire(` → 10 hits (expected 10: 9 unique EventTypes + 1 genre-chain re-emit at line 464)
   - `_build_citation_strip` → line 181 (expected ~181)
3. **Completeness — 9 EventTypes:** Sec 3 table maps 1:1 to source `_fire` sites. All present: `KAAN_SPOKE`@239, `MANUAL`@243, `TRACK_CHANGE`@273, `PHASE`@289, `LAYER_ARRIVAL`@312, `MIX_MOVE`@340, `KEY_CLASH`@383, `TRANSITION_OPPORTUNITY`@443, `HEARTBEAT`@469.
4. **Completeness — 11 EVIDENCE_SOURCES:** Source frozenset = `{"ev", "aud", "midi", "track", "screen", "mix", "tend", "key", "recall", "exemplar", "cue"}` (11 members). Sec 4 table has 11 rows in the same order. Match.
5. **Completeness — 4 ACK_ELIGIBLE_EVENTS:** Source frozenset = `{"HEARTBEAT", "MIX_MOVE", "LAYER_ARRIVAL", "KAAN_SPOKE"}` (4 members). Sec 6 cite + Sec 3 "Diet-mode eligible" column match exactly.
6. **Cooldown values:** Sec 7 table reproduces `MIN_EVENT_GAP_PER_TYPE` exactly (TRACK_CHANGE=5.0, PHASE=10.0, LAYER_ARRIVAL=10.0, MIX_MOVE=14.0, HEARTBEAT=45.0, MIC=3.0, MANUAL=1.5, KICK_SWAP=14.0, SUB_LAYER_ARRIVAL=16.0, KICK_DENSITY_SHIFT=18.0, BREAKDOWN_KICK_KILL=20.0, REENTRY_KICK_LAND=12.0, PHRASE_BOUNDARY=24.0, DISTORTION_CLIMB=6.0, ACID_LINE_ENTRY=8.0, KEY_CLASH=28.0, TRANSITION_OPPORTUNITY=20.0). 17 rows, all values match.
7. **CLAUDE.md disjointness:** `git diff` confirms +2 lines, 0 deletions, inserted between Cardinal invariant #5 (line 95) and the "Threading & generation model" subsection. No other CLAUDE.md text touched.
8. **ASCII discipline (doc body):** `grep -P '[^\x00-\x7F]' docs/PROMPT-COMPOSITION.md` returns zero matches. Doc body is ASCII-clean. (The CLAUDE.md inserted pointer line uses an em-dash + multiplication sign × — both non-ASCII — but this matches the surrounding CLAUDE.md house style, which already uses em-dashes throughout; flagging this would be a style preference, not a finding.)
9. **Doc-only security:** Section 8.1's heredoc Python script reads files via `pathlib.Path(...).read_text()` with paths constrained by the `[a-zA-Z0-9_/.-]+\.py` regex character class — no shell interpolation, no `exec`, no `os.system`. The `<<'PYEOF'` is single-quoted so no shell expansion inside the heredoc. Safe to copy-paste.

## What was skipped (per review_context)

- Style preferences ("section X could be tighter") — out of scope.
- Feature requests (e.g. "add a Viber-side equivalent doc") — explicitly deferred to HARDEN-FUTURE per Sec 1.
- CI-gate suggestions — REQ-CONTRACT-05 explicitly marks the CI smoke check OPTIONAL; Appendix §8 IS the canonical check.

## REVIEW COMPLETE

---

_Reviewed: 2026-05-28_
_Reviewer: Claude (gsd-code-reviewer, Opus 4.7)_
_Depth: standard (per phase nature: documentation-only, no executable changes)_
