---
phase: 103-live-mastered-grounding
reviewed: 2026-05-29T00:00:00Z
depth: deep
files_reviewed: 5
files_reviewed_list:
  - src/vibemix/learn/skill_recognizer.py
  - src/vibemix/learn/skill_tree.py
  - tests/learn/test_skill_recognizer.py
  - tests/learn/test_skill_tree.py
  - tests/learn/test_skill_tree_invariants.py
findings:
  critical: 0
  warning: 2
  info: 2
  total: 4
status: findings
---

# Phase 103: Code Review Report

**Reviewed:** 2026-05-29
**Depth:** deep (cross-file: event_detector.py, evidence_registry.py, event.py, progress.py traced)
**Files Reviewed:** 5
**Status:** findings

## Summary

Phase 103 (Live "Mastered" Grounding, MAST-01..04) ships two source files: `skill_tree.record_live_demo` + per-skill `mastered_threshold` (Plan 01) and the NEW citation-gated `skill_recognizer.recognize` (Plan 02). The MAST-03 anti-slop core is **sound**: the injected `citation_check` predicate is the sole arbiter of credit, it is checked before any `record_live_demo` call, it fails closed (False/no-match → `[]`), and an un-cited flood of N events never reaches Mastered. The off-by-one (`count >= threshold`), idempotent `first_mastered_at`, never-raises garbage handling, dedup identity, and `_seen` lifecycle are all correct. Determinism/purity holds — injected `now`, no clock/random, state/ imports are `TYPE_CHECKING`-only and the static gate pins it. Finding #1 (beatmatching/harmonic_mixing have no credit path) is verified accurate.

Two WARNINGs are latent cross-file defects, both tied to the **deferred** live-wiring (the engine ships offline-only, so neither breaks this phase's shipped + tested scope — but both will silently misbehave the moment `§EARNED-LIVE-MASTERED-VERIFY` lands a real `Event`). The more serious one is a false "confirmed" claim in the VERIFICATION doc that masks the defect.

## Warnings

### WR-01: Citation `t_target` reads `event.t_session`, but the real `Event` dataclass has no such field — live credit will be denied for the entire set after t≈1s

**File:** `src/vibemix/learn/skill_recognizer.py:128-138` (`_event_time`), used at `:181` / `:195`
**Issue:**
`recognize` derives the citation `t_target` from `getattr(event, "t_session", None)` and falls back to `0.0` when absent. The synthetic test events (`SimpleNamespace(type=..., extra=..., t_session=t)`) carry `t_session`, so every test passes. But the **real** `state/event.py::Event` dataclass has exactly four fields — `type`, `state`, `extra`, `priority` — and **no `t_session`** (verified: `event.py` `@dataclass Event`).

Meanwhile the EventDetector writes the registry with `t_session = max(0.0, now - state.set_start_at)` (`event_detector.py:508-509`) — a value that grows for the whole set. So when the deferred live wiring passes a real `Event` into `recognize`:
- `_event_time(real_event)` → `0.0` (the field is missing),
- `citation_check("ev", type, 0.0)` → `registry.has(..., t_target=0.0, tol=1.0)`,
- which is `True` only while `set_start_at` is within ±1.0s of `now` (i.e. the first ~1 second of the set), and `False` for every event thereafter.

Net effect: in production **no live skill ever earns Mastered** — the exact behaviour MAST-04 exists to deliver is silently disabled. This is a fail-CLOSED bug (under-credit, not false-expertise), so it doesn't violate the anti-slop gate, but it makes the whole live-mastery feature inert. It is a WARNING (not a BLOCKER) only because the live call-site is an explicitly deferred KAAN-ACTION and is not in this phase's shipped/tested code.

The docstring at `:129-134` compounds the risk by asserting `t_session` is "the synthetic/real field carrying the value the EventDetector wrote" — it is real on the synthetic test stub but absent on the real object.

**Fix:** Either (a) document the wiring contract so the deferred hook supplies the registry-time explicitly:
```python
# Live hook (KAAN-ACTION) must pass the SAME t the registry was written with:
#   t_session = max(0.0, now - state.set_start_at)
#   recognize(event, citation_check=..., progress=..., now=iso, event_t=t_session)
def recognize(event, *, citation_check, progress, now, event_t=None, _seen=None):
    ...
    t = event_t if event_t is not None else _event_time(event)
```
or (b) have `_event_time` read the field the real Event actually exposes (none today — so it must come from the caller). The minimum acceptable fix is to make the dependency explicit so the live-wiring author cannot silently feed `0.0`.

### WR-02: VERIFICATION doc claims the citation-key `t_session` "matches event_detector.py:509" — it does not

**File:** `.planning/phases/103-live-mastered-grounding/103-VERIFICATION.md:29,56` (Phase-103 artifact, in scope as the correctness record for this code)
**Issue:** Two VERIFICATION rows assert the recognizer's citation key `("ev", type, t_session)` "matches `registry.write("ev", ev_type, t_session)` at event_detector.py:509" and mark it ✓ VERIFIED. The `source`+`key` halves match, but the `t_session` half does **not** — the recognizer reads it off an `Event` attribute that does not exist (see WR-01), so the claim is not just unverified, it is false. A reviewer or the live-wiring author trusting this row will ship the dead-credit path of WR-01. The danger is the false green, not the deferral itself.
**Fix:** Amend rows 7 and the wiring table to scope the match to `(source, key)` only and flag the `t_target` time-alignment as an OPEN live-wiring obligation (carry it on `§EARNED-LIVE-MASTERED-VERIFY`). Do not mark the time component VERIFIED until a real `Event`→`recognize` round-trip is exercised.

## Info

### IN-01: A `_filter:` MIX_MOVE is significant + citable but maps to no skill (silent under-credit)

**File:** `src/vibemix/learn/skill_recognizer.py:77` (`_MIX_MOVE_EQ_SUBSTRINGS`)
**Issue:** The EventDetector's MIX_MOVE significance set includes `_filter:` (`event_detector.py:333`), and `midi/state.py:348-355` emits filter twists as `"{deck}_filter: low→high (big twist)"`. A pure filter-sweep therefore fires a real, citable `ev`, but the recognizer's EQ substrings are `("_low:", "_mid:", "_hi:", "killed")` — no `_filter:`. So a filter-only mix move resolves to `[]` and credits nothing. This is conservative (under-credit, anti-slop-safe), and filter mixing arguably belongs to `eq_mixing`, so it reads as an unintended gap rather than a deliberate honest-uncreditable decision (which is documented for beatmatching/harmonic_mixing but not for filter). Flagging so it's a conscious call, not an oversight.
**Fix:** If filter sweeps should count toward `eq_mixing`, add `"_filter:"` to `_MIX_MOVE_EQ_SUBSTRINGS`. Otherwise add a one-line comment in the HONEST-UNCREDITABLE block stating filter is deliberately excluded, so the gap is documented like the other two.

### IN-02: `record_live_demo` assumes `progress.skills` is a settable dict, weaker than `compute`'s guard

**File:** `src/vibemix/learn/skill_tree.py:400` (`progress.skills.setdefault(...)`)
**Issue:** `compute` (the read path) defensively reads `getattr(progress, "skills", {}) or {}`, but `record_live_demo` (the write path) reaches `progress.skills.setdefault(...)` directly after the Competent gate. For a real `LearnProgress` this is safe (`skills` has a `default_factory`, always a dict), and the Competent gate at `:396` returns early for the degenerate cases the tests exercise — so it never raises in practice. It is noted only because the surrounding code makes a point of its "never-raises on garbage" posture (the count guard, `compute`'s isinstance checks), and this one line would `AttributeError`/`TypeError` on a `progress` whose `skills` is `None`/non-dict — a slightly inconsistent contract. Low severity: no current caller can hit it.
**Fix:** Cheap consistency hardening if desired:
```python
skills = getattr(progress, "skills", None)
if not isinstance(skills, dict):
    return progress  # malformed progress — never-raises posture
block = skills.setdefault(skill_id, {"live_proof_count": 0, "mastered": False, "first_mastered_at": None})
```

---

_Reviewed: 2026-05-29_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
