---
phase: 102-skill-tree-engine-data-model-competent-stage
reviewed: 2026-05-28T22:50:22Z
depth: deep
files_reviewed: 5
files_reviewed_list:
  - src/vibemix/learn/skill_tree.py
  - src/vibemix/learn/progress.py
  - src/vibemix/learn/ipc_handlers.py
  - tests/learn/test_skill_tree.py
  - tests/learn/test_skill_tree_invariants.py
  - tests/learn/test_skill_tree_migration.py
findings:
  critical: 0
  warning: 1
  info: 3
  total: 4
status: issues_found
---

# Phase 102: Code Review Report

**Reviewed:** 2026-05-28T22:50:22Z
**Depth:** deep
**Files Reviewed:** 5 (3 source + 3 test suites)
**Status:** issues_found

## Summary

Phase 102 ships the skill-tree engine (`skill_tree.py`, NEW), the v1→v2 schema
migration + `skills` live-portion block (`progress.py`), and the reset
skills-ledger clear (`ipc_handlers.py`). The core logic is sound: the COMP-02
recital AND-gate is correct (per-skill gate source, no off-by-one, no
wrong-flag), `compute()` is genuinely pure (no clock/random, no input mutation,
instance-isolated `default_factory`), the v1→v2 migration preserves lesson
history + unlock flags and is idempotent on v2 (P103 live data not clobbered),
and the three invariant grep-gates (#1 no MusicState, #4 no port, privacy)
verify substantively, not by naive substring. All 29 phase tests green; float
boundary math at the 0.6 threshold is exact for every manifest skill (no
accumulation drift). Conventions clean: snake_case, `from __future__`, no
pydantic, atomic-write pattern mirrors `progress.py` / `config_store.py`.

One real robustness bug: `compute()` coerces the STORED `live_proof_count` with
a bare `int(...)` that has NO `try/except` — unlike the sibling `_weight_for`
helper, which guards it. A parseable v2 JSON carrying a non-numeric
`live_proof_count` (hand-edit, partial Phase-103 write, future drift) survives
`from_dict` untouched and then crashes `compute()` with an uncaught `ValueError`.
That is the one finding worth fixing before P103 starts writing the live-portion.

The remaining items are doc-vs-reality drift and a pre-existing silent-wipe seam
(not introduced by this phase). NOTE: `ipc_handlers.py` carries a large amount of
unrelated in-flight "One Mind" learn-island edits absorbed by the whole-file
commit (`32e5fbfc`) — those (`_canonical_lesson_id`, `_normalize_ack_control`,
ack routing, lesson-unlock gating) are a concurrent session's work and are
**out of scope** per the review brief. Only the DATA-03 reset clear was reviewed.

## Warnings

### WR-01: `compute()` crashes on a non-numeric stored `live_proof_count` (uncaught ValueError)

**File:** `src/vibemix/learn/skill_tree.py:260`
**Issue:** The live-portion coercion is a bare `int(...)`:

```python
live_proof_count = int(live.get("live_proof_count", 0) or 0)
```

This raises an uncaught `ValueError` if the stored value is a non-numeric string.
The sibling `_weight_for` helper (lines 206-209) carefully wraps the identical
`int()` call in `try/except (TypeError, ValueError)` — so the module is internally
inconsistent: the lesson-row coercion is defensive, the live-portion coercion is
not. Confirmed reproducible through the real load path (NOT a synthetic-only edge):

```python
raw = {"schema_version": 2, "lessons": {},
       "skills": {"deck_control": {"live_proof_count": "x", "mastered": False, "first_mastered_at": None}}}
p = LearnProgress.from_dict(raw)   # survives — from_dict only isinstance-checks the
                                   # top-level skills dict, NOT inner value types
SkillTree().compute(p)             # ValueError: invalid literal for int() with base 10: 'x'
```

A parseable JSON file (hand-edit, a partial/aborted Phase-103 write that lands a
string, or any future schema drift) thus wedges the engine on every load. The
module docstring (lines 20-25) and `compute`'s own docstring (step 4, "with safe
defaults") both assert the engine "never raises" / reads the live-portion safely —
this contradicts that contract. `from_dict` (progress.py:360-363) only guards
`isinstance(skills, dict)` at the top level; it never sanitizes inner skill-value
types, so the corrupt value flows straight through to `compute()`.

**Fix:** Mirror `_weight_for`'s guard so a garbage value degrades to the safe
default instead of crashing:

```python
try:
    live_proof_count = int(live.get("live_proof_count", 0) or 0)
except (TypeError, ValueError):
    live_proof_count = 0
```

(Optionally also coerce `mastered` defensively, though `bool(...)` never raises —
the `int()` is the only crashing path.) A one-line test pinning
`compute()` on `{"live_proof_count": "x"}` would lock the regression.

## Info

### IN-01: Module docstring under-states the uncovered "no-op" lessons (manifest coverage drift risk)

**File:** `src/vibemix/learn/skill_tree.py:99-100`
**Issue:** The SKILL_MANIFEST comment claims only `L0.00-press-play` and `L1.01`
"feed no skill — valid no-ops". In reality the curriculum has FIVE uncovered
lessons: `L0.00-press-play`, `L1.01` (opening dialog), `L1.15` (**load two
tracks**), `L1.16` (course 1 recital), `L2.14` (course 2 recital). The two
recitals are correctly excluded (recitals are the GATE, not fill), and `L0.00` /
`L1.01` are intro stubs — but `L1.15` "load two tracks" is a genuine teaching
lesson that fills no skill. Whether it SHOULD map to `deck_control` is a
product-design call, not provably a bug, but the inaccurate comment will mislead
the next person editing the manifest into thinking coverage is intentional and
complete. `deck_control` covers L1.02–L1.09 contiguously then jumps to course 2,
silently leaving L1.15 orphaned.
**Fix:** Either add `L1.15` to `deck_control.lesson_ids` (if "load two tracks" is
a deck-control competency) or correct the comment to name all five uncovered
lessons and state explicitly that `L1.15` is a deliberate non-fill. Don't leave
the comment asserting a 2-lesson exclusion when it's actually 5.

### IN-02: Pre-existing wipe seam silently destroys progress on a string/unknown `schema_version` (no toast)

**File:** `src/vibemix/learn/progress.py:355-359`
**Issue:** `from_dict` routes anything that is not `== 1` and not `== SCHEMA_VERSION`
to `cls()` (fresh-empty), and `load_progress` returns `was_corrupt=False` for this
path — so a user's entire lesson history is wiped with NO toast and NO log line.
Two realistic-ish triggers: (a) a hand-edited `"schema_version": "1"` (string)
fails `== 1` (`'1' != 1`) and hits the wipe seam, silently destroying v1 history
that the migration was supposed to preserve; (b) a genuine future v3 file wipes
silently. The file is left on disk untouched until the next `save_progress`, so the
loss is recoverable in principle, but the user gets zero signal. This is
**pre-existing** behavior (the v1 schema already wiped on any non-1 version) —
Phase 102 only widened the migrated set to {1,2}, it did not introduce the silent
seam — so it is not a phase regression. Flagging because the phase docstrings
(progress.py:44-52) now lean heavily on the wipe seam as a designed contract.
**Fix:** Low-priority hardening, not blocking: coerce the version through
`int(...)` defensively before comparison (so `"1"`/`1.0` both migrate), and/or set
a distinct flag for the forward-incompatible wipe so the caller can surface a "your
progress was on an unsupported version" toast instead of silently vanishing. Out of
strict Phase-102 scope; note for the milestone backlog.

### IN-03: Manifest gate names are not import-time validated (only test-checked)

**File:** `src/vibemix/learn/skill_tree.py:157-168, 253`
**Issue:** `_assert_manifest_matches_curriculum()` runs at import time and catches a
typo'd LESSON id, but there is no equivalent import-time guard that each
`SkillSpec.gate` names a real `LearnProgress` attribute. `compute()` reads the gate
via `getattr(progress, spec.gate, False)` (line 253) with a `False` fallback, so a
typo'd gate (e.g. `course_99_unlocked`) silently pins that skill to `locked`
forever with no error — a far quieter failure than the lesson-id assertion it sits
next to. `test_manifest_gates_are_recital_unlock_flags` covers it, but the asymmetry
(lesson ids fail loud at import, gate names fail silent at runtime) is a latent foot-
gun for future skill additions.
**Fix:** Extend `_assert_manifest_matches_curriculum` (or add a sibling assertion) to
verify each `spec.gate in {"course_2_unlocked", "course_3_unlocked"}` — or
`hasattr(LearnProgress(), spec.gate)` — so a gate typo fails at module load exactly
like a lesson-id typo does. Cheap, consistent with the existing anti-drift posture.

---

_Reviewed: 2026-05-28T22:50:22Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
