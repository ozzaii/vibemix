---
phase: 60-harmonic-feedback-confidence-gate
reviewed: 2026-05-21T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - src/vibemix/state/harmonics.py
  - src/vibemix/state/event_detector.py
  - src/vibemix/state/coach.py
  - src/vibemix/prompts/matrix.py
  - eval/harmonic/run_veto.py
findings:
  critical: 0
  warning: 3
  info: 4
  total: 7
status: issues_found
---

# Phase 60: Code Review Report

**Reviewed:** 2026-05-21
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Reviewed the Phase 60 harmonic-feedback confidence gate: the deterministic Camelot
clash predicate (`harmonics.py`), the suppression + clash/transition firing logic
(`event_detector.py`), the narrate-only coach fragments (`coach.py`), the citation
grammar (`matrix.py`), and the Kaan-ear veto scorer (`run_veto.py`).

**The core hallucination gate is sound.** I independently re-derived the
hour→semitone table against the circle of fifths (`+1 hour = +7 semitones mod 12`)
and confirmed every entry is correct. The clash predicate is conservative and
internally consistent: I exhaustively checked all 24×24 Camelot pairs and found
**zero** cases where a pair is simultaneously `is_clash` and `compatible`, all
`None`/garbage inputs return `False` (never raise), the open-key anchor (`1m→8A`,
`1d→8B`) is correct, relative major/minor is treated safe, and the veto scorer
exits 0 against the shipped corpus with all 11 pairs matching. Default-off,
cite-floor, and melodic-overlap gating are all wired as described. 143 harmonics +
event-detector tests pass.

No BLOCKER-class defects found. Findings are quality/robustness issues — the most
material being a stale comment + dead set member in the clash table that does not
match the implemented `_hour_distance` range, and a looser-than-documented gate on
the `TRANSITION_OPPORTUNITY` branch.

## Warnings

### WR-01: `_CLASH_HOURS` contains an unreachable member (7); docstring claims a "hour 7" branch that can never execute

**File:** `src/vibemix/state/harmonics.py:139` (and the docstring at lines 113-133)
**Issue:** `_CLASH_HOURS = frozenset({5, 6, 7})` but `_hour_distance` returns a
*circular* distance clamped to `min(d, 12-d)`, range **0..6**. Hour 7 is
mathematically unreachable — a 7-hour separation folds to 5. I verified this by
enumerating all 12×12 number pairs: the produced distances are exactly `{0,1,2,3,4,5,6}`.
The docstring table (lines 124-125) explicitly lists "hour 7 → 1 SEMITONE → CLASH"
as a distinct row, implying the code distinguishes hours 5 and 7. It does not, and
cannot. This is not a correctness bug today (folding 7→5 is the *right* answer), but
it is a latent trap: a future maintainer who changes `_hour_distance` to return a
signed/0..11 distance would suddenly activate the dead `7` member and the dead
`_HOUR_TO_SEMITONES` would `KeyError` (the table has no key `7`). The set and the
table disagree about their own domain.
**Fix:** Drop the unreachable member and align the comment with the implemented
circular range:
```python
# Same-letter circular hour-distances (0..6, post-fold) that clash.
# A 7-hour separation folds to 5 via _hour_distance — there is no
# separate "hour 7" case at runtime.
_CLASH_HOURS = frozenset({5, 6})
```
Then trim the "hour 7 →" row from the docstring table so the documented contract
matches the code.

### WR-02: `TRANSITION_OPPORTUNITY` fires WITHOUT the `_melodic_overlap_gate` — looser than the KEY_CLASH path it sits beside

**File:** `src/vibemix/state/event_detector.py:379-410`
**Issue:** The KEY_CLASH branch (line 342) is gated on `_melodic_overlap_gate(state)`
(both decks melodic, audible, non-breakdown, non-vocal, tonal). The
`TRANSITION_OPPORTUNITY` branch immediately below does **not** apply that gate — it
fires on `both_cited and structural_blend` alone, where `structural_blend` is any
`killed/_low:/_mid:/_hi:/_filter:/xfader` move anywhere in `state.recent_moves`
(a 12-second window, set in `refresh.py:504`). So a blend note can fire during a
breakdown, during a vocal acapella, or on a structural move that landed up to ~12s
ago — exactly the conditions KEY_CLASH suppresses. The 20s cooldown bounds the rate
but not the *grounding quality*. The phase docstring frames this branch as
"groundable-only," yet it is the less-grounded of the two. It is default-off and
narrated past-tense, which contains the blast radius, but a clash verdict (`clash:
is_clash(...)`) reaching the audience during a breakdown is the precise false-
expertise class this phase guards against.
**Fix:** Apply the same precondition to keep the two branches symmetric:
```python
if (
    self._harmonic_clash_enabled
    and self._melodic_overlap_gate(state)
    and self._cooldown_ok("TRANSITION_OPPORTUNITY", now)
):
```
If a transition note is *intended* to fire outside melodic overlap (e.g. report on
a blend that just happened in a breakdown), document that divergence explicitly at
the branch — right now the asymmetry reads as an oversight rather than a decision.

### WR-03: `TRANSITION_OPPORTUNITY` has no recency bound on the blend move — fires on a move up to 12s stale

**File:** `src/vibemix/state/event_detector.py:390-396`
**Issue:** `structural_blend` iterates `state.recent_moves` with no age filter:
```python
structural_blend = any(
    any(k in label for k in (...))
    for _age, label in state.recent_moves
)
```
Every consumer of `recent_moves` that cares about timeliness filters on age first
— `coach.py:120` uses `age <= 8.0`, and the MIX_MOVE significance loop only reacts
to *new* (unseen) moves. This branch ignores `_age` entirely, so a structural move
that landed 11s ago still triggers a "you just blended" past-tense note. Combined
with the 20s cooldown, the co-host can narrate a blend that is meaningfully stale
relative to "just." The note is past-tense so it does not claim *present* action,
but "you just blended A→B" at +11s is a weak grounding claim.
**Fix:** Bound the move recency to match the cited deck-state freshness, e.g.:
```python
structural_blend = any(
    age <= 8.0 and any(k in label for k in (...))
    for age, label in state.recent_moves
)
```

## Info

### IN-01: Veto scorer coerces missing `a`/`b` keys to the literal string `"None"`

**File:** `eval/harmonic/run_veto.py:98-107`
**Issue:** `a, b = entry.get("a"), entry.get("b")` then `PairResult(a=str(a), ...)`.
A corpus entry missing `"b"` yields `b=None`, `is_clash("8A", None)` → `False`
(correct, fail-closed), but the report prints the pair as `8A/None` because `str(None)`
== `"None"`. The verdict scoring is still correct (a malformed `safe` entry passes
because it doesn't flag; a `clash` entry correctly FAILs as VACUOUS). The cosmetic
problem: the report shows a literal string `"None"` rather than flagging the entry
as malformed, which could mask a corpus authoring typo (Kaan edits this file by
hand per the docstring).
**Fix:** Detect missing keys and surface them as an explicit authoring error rather
than silently stringifying:
```python
if a is None or b is None:
    # surface as a distinct "malformed" result instead of str(None)
```

### IN-02: Empty corpus exits non-zero with no diagnostic distinguishing it from a real failure

**File:** `eval/harmonic/run_veto.py:208`
**Issue:** `all_pass = all(r.passed for r in results) if results else False` — an
empty corpus returns `1` (gate FAIL), which is the correct fail-closed posture. But
`format_report` prints the standard "GATE FAIL: ... Fix the predicate or correct the
corpus" message, which is misleading: nothing is wrong with the predicate, the
corpus is just empty. A maintainer running against a freshly-created empty fixture
gets a confusing signal.
**Fix:** Special-case the empty corpus with its own message ("corpus is empty —
add pairs before running the gate") while still returning non-zero.

### IN-03: Stale docstring header — "verbatim port of cohost_v4.py" no longer holds

**File:** `src/vibemix/state/event_detector.py:2`, `src/vibemix/state/coach.py:2`
**Issue:** Both module docstrings open with "verbatim port of cohost_v4.py:NNNN-NNNN".
`cohost_v4.py` was deleted in the 2026-05-20 POC retirement (per CLAUDE.md), and
both files now carry substantial Phase 17/18/59/60 additions (genre router,
evidence registry, harmonic clash, deck-state block). The "verbatim port" framing
is no longer accurate and points at a file that no longer exists. The detailed
"THREE STRUCTURAL DEVIATIONS" / "TWO confidence thresholds" notes below it remain
useful, but the opening line misleads.
**Fix:** Reword the opening line to "originated as a port of the retired cohost_v4.py;
since extended through Phases 17/18/59/60" so the lineage is honest without implying
byte-identity to a deleted file.

### IN-04: `compatible()` is exported and documented but has no caller in the reviewed scope

**File:** `src/vibemix/state/harmonics.py:191-211`
**Issue:** `is_clash` and `semitone_distance` are both consumed in
`event_detector.py`. `compatible()` is fully implemented, documented, and tested,
but no production code path in the Phase 60 scope calls it (the detector fires on
`is_clash`, never on `not compatible`). This is fine as a public API surface for
Phase 61/future blend-suggestion work, but as shipped it is dead in the runtime
path. Worth confirming it is intentionally forward-looking rather than an unwired
branch. Note also the deliberate asymmetry it encodes: hours 3/4 are neither
`compatible` (returns False) nor `is_clash` (returns False) — the "silent neither
zone." This is correct and matches the corpus, but a caller that assumes
`compatible == not is_clash` would be wrong; the gap is real.
**Fix:** No code change required. If it is forward-looking, add a one-line note on
the function ("not yet wired into the detector — reserved for Phase 61 blend
suggestions") so a reader doesn't hunt for a missing call site. If it was meant to
gate something this phase, wire it.

---

_Reviewed: 2026-05-21_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
