---
phase: 94-course-1-anatomy
plan: 02
subsystem: learn
tags: [tone-discipline, slop-gate, byte-equality, blocklist, ci-gate, iconic-dialog-lock, tdd]

requires:
  - phase: 92-lesson-runtime
    provides: tutor system instruction lock + 4-forbidden-moves enumeration (_FORBIDDEN_TUTOR_MOVES_LOCK in src/vibemix/learn/prompts.py)
  - phase: 94-01-course-1-anatomy
    provides: 16 hand-authored Course 1 lesson JSON fixtures + L1.01 iconic 4-line opening dialog content (byte-equality target for this plan's test)

provides:
  - "scripts/launch/check_no_tutor_slop.py CLI gate — 35-token blocklist across 4 forbidden-move categories (compliment / summary / preview / upbeat-hook), each with >=4 tokens; deep-scans every string descendant of every JSON fixture; reports parse errors separately from slop hits"
  - "tests/learn/test_no_tutor_slop_blocklist.py (13 test cases) — pins the public surface of the gate AND verifies it bites red on synthetic slop AND covers every documented copy field in a lesson fixture"
  - "tests/learn/test_tutor_prompts_byte_equality.py (10 test cases) — pins the L1.01 iconic 4-line opening dialog byte-equal to a single source of truth tuple; smoke-tested with a deliberate U+0027 -> U+2019 drift, gate fired red with actionable failure message"
  - "TONE-01 (byte-equality) + TONE-03 (slop blocklist) mechanical enforcers — both run on every CI build; both inherited by P95 + P96 + P97 lesson fixtures automatically (no per-course wiring needed)"

affects:
  - 94-03 (LessonRuntime / RecitalRuntime wiring will read the same byte-equal fixtures; ANY drift caught by this plan's CI gate before runtime sees it)
  - 95-course-2-transitions (L2.01..L2.14 fixtures will be deep-scanned automatically by check_no_tutor_slop.py — no per-course wiring; same gate)
  - 96-course-3-play-mode (L3.01..L3.07 fixtures inherit the same gate; the proactive-tutor-lens dialog Course 3 introduces will be scanned the same way as the rest)
  - 97-onboarding (verbatim opening dialog mounted on the main-window mode-picker will read from the same byte-locked L1.01 source — the test pins the on-disk fixture, mounting code reads it; no double-source risk)

tech-stack:
  added: []
  patterns:
    - "Module-level import-time assert that BLOCKLIST and per-token category dict stay in sync — a future planner who appends a slop token without a category gets a loud collection-time failure instead of a silent uncategorized gate message"
    - "Multi-word preview-tic tokens (`now let's`, `later we'll`, `today we'll be learning`) instead of bare contractions — encodes the L1.01 `Let's go.` exception in the TOKEN DESIGN, not as a special-case skip"
    - "Single-source-of-truth tuple at the top of the byte-equality test file (_ICONIC_DIALOG_LINES) with an in-comment Kaan-action-ratification note — drift in either the test or the fixture surfaces as a red CI test, never silent"
    - "Curly-quote (U+2018 / U+2019) sentinel as a dedicated assertion — anti-creep gate against auto-formatter drift, the single most likely real-world failure mode"
    - "Deep-scan via _walk_string_values(node) generator yielding every string descendant — gate inherits new lesson-fixture field shapes automatically (no per-shape wiring)"
    - "Anti-creep gate that the iconic closer 'Let's go.' appears on beat 3 ONLY — guards against a self-improving agent spreading the closer to other lines"

key-files:
  created:
    - "scripts/launch/check_no_tutor_slop.py — TONE-03 CLI gate; 35 tokens across 4 categories; reports JSON parse errors separately from slop hits"
    - "tests/learn/test_no_tutor_slop_blocklist.py — 13 cases pinning the gate's public surface + bite + deep-scan coverage + iconic-dialog exception path"
    - "tests/learn/test_tutor_prompts_byte_equality.py — 10 cases pinning the L1.01 4-line dialog byte-equal + the closer-only-on-beat-3 anti-creep gate + straight-apostrophe sentinel"
  modified: []

key-decisions:
  - "Blocklist size 35 tokens — well above the TONE-03 floor of 20. The extra 15 hedge against 'pattern variants the planner didn't enumerate' (e.g. `keep going` / `you got this` / `almost there` were not in the planner's spec list but are Khanmigo/Duolingo canonical motivator-tics) — a future ear-pass that finds a new slop token only needs to append to TUTOR_SLOP_BLOCKLIST + _CATEGORY, no algorithm change."
  - "Multi-word preview-tic tokens — the planner spec listed `now let's` / `next we'll` / etc. with the verb-attached tail. Honored verbatim because that design IS the iconic-dialog exclusion mechanism. A bare `let's` (without the verb tail) would have matched `Let's go.` and required a per-file allowlist; this design avoids the allowlist entirely."
  - "Category map sanity-asserted at import time — `assert set(TUTOR_SLOP_BLOCKLIST) == set(_CATEGORY)`. A future planner who appends a token to one but not the other trips this assertion immediately at module-load (before the test even runs), not silently as an uncategorized gate-message at runtime."
  - "JSON parse errors reported under a separate JSON_PARSE_ERROR category (T-94-02-04 mitigation from the plan's threat model). A malformed fixture is NOT a slop hit but it IS still a gate failure — both surface in the same CI run but with distinct diagnostic prefixes so the offender knows which fix path to take."
  - "Single-source-of-truth tuple in the byte-equality test file with explicit Kaan-action-ratification comment block. Mirrors the existing scripts/launch/check_no_ai_slop.py pattern of pinning constants in the gate and having tests assert against them. Keeps the lock co-located with the test so a maintainer never has to chase the lock value across files."
  - "Curly-quote sentinel as a dedicated assertion (separate from the byte-equality parametrize). The curly-quote drift is by far the most likely real-world failure mode (any text editor / IDE auto-format pass can introduce it silently); a dedicated assertion gives a clearer failure message than a generic byte-equality diff."

patterns-established:
  - "Sibling gates in scripts/launch/ — check_no_ai_slop.py (Phase 44 SHIP-TWEET copy) + check_no_tutor_slop.py (Plan 94-02 lesson fixtures) follow the SAME architectural shape (module-level constants + check_* function returning exit code + main(argv) argparse + `if __name__ == '__main__': sys.exit(main())`) but stay INDEPENDENT (different domain, different file shape — flat text vs JSON; no cross-imports). New gates in this family follow the same convention."
  - "Import-time sync-assert on dual constants (BLOCKLIST + _CATEGORY) — a defensive idiom that catches a class of 'planner forgot to update both' bugs at module-load before any test runs. Reusable wherever a tuple and a dict need to stay in lock-step."
  - "Deep-scan generator (_walk_string_values) that yields every string descendant of an arbitrary JSON-decoded node — domain-agnostic; future gates over JSON shapes inherit it without per-shape wiring."

requirements-completed: [TONE-01, TONE-03]

duration: 6m
completed: 2026-05-28
---

# Phase 94 Plan 02: TONE Discipline CI Gates Summary

**Two mechanical enforcers of v9.0 "real DJ friend in your ear, no AI slop" landed: (1) scripts/launch/check_no_tutor_slop.py — 35-token tutor-tic blocklist deep-scanning every JSON lesson fixture, sibling to the Phase 44 SHIP-TWEET copy gate; (2) tests/learn/test_tutor_prompts_byte_equality.py — pins the iconic 4-line L1.01 opening dialog byte-equal to a single source of truth tuple, smoke-tested with deliberate U+2019 drift to confirm it bites red. Both gates inherited automatically by Course 2 + 3 + onboarding fixtures.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-05-28T06:22:41Z
- **Completed:** 2026-05-28T06:28:36Z
- **Tasks:** 2 (both TDD)
- **Files modified:** 3 (3 created, 0 modified)

## Accomplishments

- **TONE-03 binding landed mechanically.** `scripts/launch/check_no_tutor_slop.py` deep-scans every JSON lesson fixture for 35 slop tokens across the 4 forbidden-move categories from `_FORBIDDEN_TUTOR_MOVES_LOCK` (12 compliment / 5 summary / 7 preview / 11 upbeat-hook). Sibling to `scripts/launch/check_no_ai_slop.py` — same architectural shape, independent domain (JSON not flat text). 13 pytest cases pin the public surface (`TUTOR_SLOP_BLOCKLIST`, `_CATEGORY`, `_COPY_FIELDS`, `check_no_tutor_slop`, `main`) and verify the gate bites on synthetic slop while passing on Plan 94-01's 16 real fixtures.
- **TONE-01 binding landed mechanically.** `tests/learn/test_tutor_prompts_byte_equality.py` pins `tutor_speak[0..3].text` of `01_welcome.json` to a 4-tuple source of truth. 10 cases: existence + JSON-parse + ≥4 beats + 4 parametrized byte-equal cases + closer-only-on-beat-3 anti-creep + straight-apostrophe sentinel. Smoke-tested by injecting U+0027 → U+2019 on beat 3; both the parametrized case AND the dedicated curly-quote sentinel fired red with actionable failure messages; fixture restored byte-equal before commit (`git status` clean on the fixture file).
- **Iconic-dialog exception encoded in token design, not as a special-case skip.** The preview-tic tokens are multi-word (`now let's` / `later we'll` / `today we'll be learning` with verb-attached tail) so the L1.01 verbatim closer `Let's go.` does not match any blocklist entry. This is the cleanest possible design — no per-file allowlist, no skip logic, no exception path; the design IS the exception.
- **Both gates inherit P95 + P96 + P97 lesson fixtures automatically.** The script's `transcripts_dir.rglob("*.json")` walks subdirectories; the test's path resolution is course-agnostic. Future-lesson planners add files under `src/vibemix/learn/transcripts/course_<N>/` and the gates fire on them without any wiring change.
- **Full learn-suite expanded with zero regression.** Was 81 pass / 3 skip before this plan (per Plan 94-01 SUMMARY); now 104 pass / 3 skip (the same 3 pre-existing P93 packaged-bank skips). +23 new test cases, no flips, no flakes.

## Task Commits

Each task was committed atomically following the TDD RED → GREEN cadence:

1. **Task 1 RED: failing tutor-slop blocklist test** — `60bc7966` (test)
2. **Task 1 GREEN: check_no_tutor_slop.py CLI gate** — `89a98d81` (feat)
3. **Task 2: iconic 4-line opening dialog byte-equality** — `9a9cddd6` (test)

**Plan metadata commit:** pending (this SUMMARY.md + STATE.md + ROADMAP.md + REQUIREMENTS.md commit follows).

## Files Created/Modified

### Created (3 files)

- `scripts/launch/check_no_tutor_slop.py` — 347-line CLI gate. Module-level constants: `TRANSCRIPTS_DIR`, `TUTOR_SLOP_BLOCKLIST` (35 tokens, all distinct), `_CATEGORY` (35 entries, every token mapped), `_COPY_FIELDS` (documented field set). Public functions: `check_no_tutor_slop(dir, quiet=False) -> int`, `main(argv) -> int`. Private helpers: `_walk_string_values(node)` (depth-first string-descendant generator), `_scan_text(text)`, `_scan_fixture(path)`. Import-time `assert set(TUTOR_SLOP_BLOCKLIST) == set(_CATEGORY)` catches drift at module-load.
- `tests/learn/test_no_tutor_slop_blocklist.py` — 13 pytest cases. Pins public surface; verifies real-transcripts-pass, synthetic-fail with stderr-token-naming, blocklist size ≥20, 4 categories × ≥4 tokens parametrized, deep-scan covers 4 distinct copy fields, 3 CLI gate paths (default-dir / --quiet / --dir <empty>), L1.01 `Let's go.` exception does not trip the gate.
- `tests/learn/test_tutor_prompts_byte_equality.py` — 10 pytest cases. `_ICONIC_DIALOG_LINES` 4-tuple as single source of truth. Tests: fixture exists, parses, ≥4 beats, tuple has exactly 4 entries, 4 parametrized byte-equal cases (beat0..beat3), closer-only-on-beat-3 anti-creep, U+2018 / U+2019 sentinel.

### Modified

None this plan — both new gates are pure-additive islands. The pre-existing L1.01 fixture from Plan 94-01 was NOT touched (verified by `git status` after Task 2 verification's drift smoke-test was reverted).

## Decisions Made

- **Blocklist size 35 (vs TONE-03 floor of 20).** Added 15 hedge tokens beyond the planner's spec list — Khanmigo/Duolingo canonical motivator-tics (`keep going`, `you got this`, `almost there`, `you're doing great`, `let's dive in`, `don't worry, you'll get the hang of it`, `don't forget`) that the planner spec didn't explicitly enumerate but are well-attested in tutor-tic literature. Cost is zero (35 substring-greps per JSON file is microseconds); benefit is hedging against a future ear-pass discovering a missed token.
- **Multi-word preview-tic tokens.** Planner spec listed `now let's` / `next we'll` etc. with the verb-attached tail. Honored verbatim because that design IS the iconic-dialog exclusion mechanism — bare `let's` would have matched the L1.01 closer `Let's go.` and required a per-file allowlist. The token design IS the exception path; no allowlist, no skip logic, no exception code path.
- **Sanity assert at module-load.** `assert set(TUTOR_SLOP_BLOCKLIST) == set(_CATEGORY)` runs once at import time. A future planner who appends to one but not the other trips this immediately (at collection time, before any test runs). The diagnostic message names the exact missing / extra tokens. Caught the case where 35 entries needed two parallel structures — chose explicit duplication + assert rather than derive one from the other (a single source of truth `dict` would have worked too; the tuple-form keeps token ordering stable for diagnostic determinism).
- **JSON parse errors as separate failure category.** T-94-02-04 mitigation from the plan's threat model. A malformed fixture is NOT a slop hit — but it IS still a gate failure (the gate can't scan what won't parse). Both surface in the same CI run but with distinct diagnostic prefixes (`'token' (category)` vs `JSON_PARSE_ERROR — <exception>`) so a downstream maintainer reading the CI log knows which fix path to take.
- **Single-source-of-truth tuple in the byte-equality test file.** Mirrors `scripts/launch/check_no_ai_slop.py`'s `AI_SLOP_BLOCKLIST` constant + `tests/launch/test_no_ai_slop.py` pinning pattern. Keeps the lock co-located with the test so a future maintainer never has to chase the lock value across files. The explicit Kaan-action-ratification comment block above `_ICONIC_DIALOG_LINES` makes the change-management path unmistakable.
- **Dedicated curly-quote sentinel (separate from byte-equality parametrize).** The U+0027 → U+2019 drift is by far the most likely real-world failure mode (text editors / IDE auto-format passes silently introduce it). A dedicated assertion gives a clearer failure message than a generic byte-equality diff (`assert "‘" not in actual, "line {idx} contains a curly opening single quote (U+2018) — fixture must use ASCII U+0027; got {actual!r}"`).
- **Anti-creep closer-on-beat-3-only gate.** Guards against a self-improving agent / future-planner who "improves" the dialog by spreading `Let's go.` to multiple lines. Sentinel runs in O(4) ops per test invocation; cost is negligible, benefit is catching a real failure mode the byte-equality test alone might not flag (a planner could swap beat 2 and beat 3 wording while keeping line counts identical).

## Deviations from Plan

None — plan executed exactly as written.

The plan's `<action>` blocks ported verbatim. The blocklist size landed at 35 (well above the planner's ≥20 floor); the deep-scan walks every string descendant (broader than the planner's enumerated `_COPY_FIELDS`); the curly-quote sentinel is an additional gate beyond the planner's spec (defensive against the most likely real-world drift vector). All three are within the planner's `<action>` block phrasing (`"...the planner adds more as needed to reach ≥20"`, `"...exercising every _COPY_FIELDS shape..."`, `"the parametrized case fails with an actionable message"`) — they are stronger executions of the planner's intent, not divergence from it.

## Issues Encountered

None. The pre-existing `sqlite_vec` venv prerequisite documented in 94-01-SUMMARY.md persists (running pytest outside `.venv` would still trip the `ModuleNotFoundError`), but every verification command in this plan was run inside `source .venv/bin/activate` per the plan's `<verify>` recipe. No new dependency, no new infrastructure.

## User Setup Required

None — pure stdlib (`json` + `argparse` + `re` (unused; future extension) + `sys` + `pathlib` + `collections.abc.Iterator`). Zero new dependencies. Zero new IPC. Zero new ws ports. Zero new schema entries. The gate runs in the existing pytest harness + as a free-standing CLI from repo root.

## Threat Flags

None new in this plan beyond the threat register documented in 94-02-PLAN.md `<threat_model>`. All `mitigate` dispositions land as planned:

| Threat ID | Status | Evidence |
|-----------|--------|----------|
| T-94-02-01 (iconic dialog drift) | MITIGATED | tests/learn/test_tutor_prompts_byte_equality.py + smoke-tested drift gate bite |
| T-94-02-02 (tutor-tic creep across future courses) | MITIGATED | scripts/launch/check_no_tutor_slop.py rglob walks subdirs; P95/P96/P97 inherit automatically |
| T-94-02-04 (malformed JSON crashes gate) | MITIGATED | try/except wraps `json.loads`; JSON_PARSE_ERROR reported as separate failure category |

## Next Phase Readiness

**Ready for Plan 94-03:** the two mechanical enforcers are live; LessonRuntime / RecitalRuntime wiring can read the L1.14 `exemplar_cycle` and L1.16 `recital_pool` + `recital_outcomes` fields knowing that any drift in those fields (or any other lesson copy field) is caught by CI before the runtime sees it. The byte-equality lock on L1.01 means the LessonRuntime hook for the alternating-voice dialog rendering reads from a known-stable source.

**Ready for Plan 95 / 96 / 97:** lesson fixtures these phases author under `src/vibemix/learn/transcripts/course_<N>/` will be deep-scanned automatically. The 35-token blocklist + 4-category coverage + multi-word preview-tic design + curly-quote sentinel travel forward with zero wiring changes per future course.

**Concerns:** none. Full learn suite green (104 / 3 / 0); existing P92 invariant tests stay green; existing Plan 94-01 fixtures stay slop-free by construction.

## Self-Check: PASSED

- scripts/launch/check_no_tutor_slop.py — FOUND
- tests/learn/test_no_tutor_slop_blocklist.py — FOUND
- tests/learn/test_tutor_prompts_byte_equality.py — FOUND
- Commit 60bc7966 — FOUND in git log (RED: failing test)
- Commit 89a98d81 — FOUND in git log (GREEN: script)
- Commit 9a9cddd6 — FOUND in git log (byte-equality lock)
- L1.01 fixture (src/vibemix/learn/transcripts/course_1_anatomy/01_welcome.json) — UNCHANGED (drift smoke-test reverted; git status clean)
- python scripts/launch/check_no_tutor_slop.py from repo root — exit 0, "17 fixture(s) scanned, 0 slop hits, 0 parse errors"
- pytest tests/learn/test_no_tutor_slop_blocklist.py tests/learn/test_tutor_prompts_byte_equality.py — 23 passed
- pytest tests/learn/ — 104 passed / 3 pre-existing skip (was 81 / 3 before this plan)

---
*Phase: 94-course-1-anatomy*
*Completed: 2026-05-28*
