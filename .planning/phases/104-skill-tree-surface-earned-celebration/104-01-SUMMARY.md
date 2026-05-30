# Summary 104-01 — Backend: what-remains payload + creditability fact + Mastered vocal

**Phase:** 104 · **Wave:** 1 of 2 · **Requirements:** SURF-01 (payload half) · SURF-03
**Commit:** `9242fc3d` · **Status:** SHIPPED (TDD, learn-island, surgical `--files`).

## What landed

- **SURF-01 (backend half).** `_what_remains(sp, spec)` in `learn/skill_tree.py` folds a
  deterministic, single-source-in-Python advance line into every `skill_wall_payload`
  row (`what_remains`): locked→"Finish the lessons"/"Pass the recital" (COMP-02 split on
  `learn_fill ≥ COMPETENT_THRESHOLD`), competent-creditable→"{N−count} more cited live
  demo(s) to Master", competent-uncreditable→honest non-promise, mastered→`""`. This is the
  half the concurrent `e15e9c66` render needed — the schema marks `what_remains` *required*,
  and the payload now emits it (the seam is whole).
- **Creditability as a manifest fact.** `SkillSpec.live_creditable: bool = True`;
  `beatmatching` is the sole `False` (the only v11.0 honest-uncreditable skill — no
  BEATMATCH/SYNC event). Drift-pinned vs `skill_recognizer._HONEST_UNCREDITABLE_V11` so the
  readable manifest stays the single source (SKILL-01/03) and `_what_remains` stays honest
  without importing the recognizer into the import-light engine.
- **SURF-03.** New `learn/mastered_vocal.py` — pure `mastered_unlock_line(skill_id, *,
  was_mastered, now_mastered)` returning the hand-authored copy ONLY on the
  not-mastered→mastered flip (fire-once by construction). Copy bank in
  `learn/vocals/mastered_vocals.json` (relocated OUT of `transcripts/`, which has a
  one-JSON-per-LessonMeta inventory contract; the same anti-slop + dash-glue gates are
  applied by the unit test instead). Wired into the live credit site:
  `_credit_live_skill_demo` gains a `speak` hook, snapshots `mastered` before crediting,
  and speaks once per flip; `coach_loop` builds the hook from the existing session's
  fixed-text path (`session.say`, no LLM, no new provider, never wedges the loop on a
  vocal failure).

## Tests (all GREEN)

- New: `test_skill_wall_what_remains.py` (8), `test_mastered_vocal_fires_once.py` (9 incl.
  slop-blocklist + dash-glue over the copy), `test_creditability_drift.py` (2).
- Extended: `test_coach_skill_credit.py` (+4 — flip speaks once, non-flip silent, un-cited
  silent, speak-failure never wedges credit), `test_skill_wall_payload.py` (+`what_remains` key).
- **`tests/learn` 751 passed / 1 skipped · `tests/runtime` 344 passed · ruff clean.**
- Fixed 3 gates the first fixture location tripped (em-dash glue, curriculum-audit orphan,
  package-verifier) by relocating the fixture + dash-free copy.

## Deviations / notes

- Fixture moved to `learn/vocals/` (not `transcripts/earned/`) to respect the transcript
  inventory contract — slop+dash gating preserved via `test_mastered_vocal_fires_once.py`.
- `test_skill_wall_payload.py` key-set assertion updated to include `what_remains`
  (requirement-driven, learn-island).

## Parked KAAN-ACTION
- 🔴 `§EARNED-MASTERED-VOCAL-EAR` — ear-pass on the vocal tone.
- 🔴 `§EARNED-LIVE-MASTERED-VERIFY` — real-FLX4 live verify (carried from P103).
