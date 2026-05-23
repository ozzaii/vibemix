---
phase: 67-all-tests-pass
plan: 67P03
subsystem: testing

tags: [pytest, ast, static-gate, ci-prep, anti-drift, reason-tagging, flake-quarantine, repo-presence]

# Dependency graph
requires:
  - phase: 67
    plan: 67P01
    provides: "Default `pytest -q` GREEN baseline (4156 passed / 26 skipped / 4 xpassed / 0 failed) + `flaky` marker registered under --strict-markers"
  - phase: 67
    plan: 67P02
    provides: "11 Tier-B `@pytest.mark.xfail(strict=False, reason='… — see §V7-LIVE-NN')` decorators + adjacent `# reason:` comments (the dual-channel shape the new skip gate must accept on existing tree)"
provides:
  - "`tests/repo/test_no_silent_skips.py` — AST gate enforcing `reason=` kwarg OR `# reason:` comment on every `@pytest.mark.skip` / `@pytest.mark.skipif` / `@pytest.mark.xfail` decorator (TEST-01 anti-drift surface)"
  - "`tests/repo/test_no_silent_flakes.py` — AST gate enforcing `# issue: https://github.com/.../issues/N` adjacency on every `@pytest.mark.flaky` decorator (TEST-03 anti-drift surface — vacuously-green at landing, fires red on the first undocumented flake addition)"
affects: [67-all-tests-pass-wave-3, 67-all-tests-pass-wave-4, 68-all-devices-ready]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "AST-walk static gate (not regex on text). Both new gates use `ast.parse` + `ast.walk` over each test file's tree, then inspect `node.decorator_list` for matching decorators and read each Call node's `keywords` list for `reason=`. This handles multi-line decorators transparently (e.g. `tests/llm/test_tts_3_1.py:164` has a 7-line `@pytest.mark.skipif(...)` with the `reason=` value wrapped across 4 lines — AST sees one decorator with a `reason` keyword regardless of physical layout). Regex-on-text would have needed a fragile 4-line lookahead to match the wrapped form; AST is line-layout-agnostic by construction. This is now the project's static-gate idiom for any future decorator-shape invariant."
    - "Dual-acceptance gate (kwarg OR comment). The skip gate accepts EITHER a `reason=` keyword in the decorator call (machine-readable, surfaces in `--tb=short`) OR a `# reason:` comment within 2 lines above (human-readable, grep-friendly). Wave 1 Tier-B tests deliberately carry BOTH for audit redundancy — the gate validates that at least one is present. This means a future contributor can pick either style and the gate stays green; the dual-channel discipline is enforced by convention + code review, not by the static gate (which is the minimum-viable contract)."
    - "Self-exclusion guard for static-scan tests. Each gate excludes its own filename from the `tests/**/*.py` rglob (`_SELF_FILENAME` constant) so that any decorator-stem string literal in the gate's own source (regex sources, docstring mentions) cannot self-trip the assertion. AST-based scanning makes this defensive-only (string literals are not decorators), but the convention matches `tests/repo/test_repo_scrub.py`'s tokenize-based stripping and keeps the gates future-proof against accidental example code."

key-files:
  created:
    - "tests/repo/test_no_silent_skips.py (NEW — 148 lines · AST gate for skip/xfail reason-tagging)"
    - "tests/repo/test_no_silent_flakes.py (NEW — 126 lines · AST gate for flaky issue-link adjacency)"
    - ".planning/phases/67-all-tests-pass/67P03-SUMMARY.md (this file)"
  modified: []

key-decisions:
  - "AST over regex. The plan's must_haves description used the phrase \"regex scan\" but the user's execution-time prompt mandated `ast.parse` + walk. AST is the correct call regardless: pytest's `@pytest.mark.skipif(cond, reason=...)` accepts arbitrarily-wrapped multi-line forms (the 7-line `test_tts_3_1.py:164` skipif is the live witness in this tree), and a regex-only gate would either miss multi-line `reason=` (false-negative — silent skip slips through) or false-fire on multi-line non-reason kwargs (false-positive — noisy CI). AST inspects `Call.keywords` directly, getting both right by construction."
  - "All three of skip/skipif/xfail in scope (not skip+xfail only). The 67P03-PLAN.md task description proposed a `(?!\\w)` negative lookahead to EXCLUDE `skipif` (\"pytest already requires `reason=` on skipif\"). The user's execution prompt was explicit: require reason on all three. The tree-wide evidence confirms this is correct — every existing `skipif` decorator does carry a `reason=` (28 of them), so including it in the gate's scope is zero-cost on the current tree AND it's the conservative invariant going forward. A `@pytest.mark.skipif(cond)` without `reason=` is technically pytest-legal but would be a silent skip exactly the kind this gate exists to prevent."
  - "Two-line window above the decorator (skip gate). Per the 67-CONTEXT.md `### Reason Tagging` spec, the comment search window is lines `[lineno-2, lineno-1, lineno]` (up to 2 lines above OR on the decorator line). Wave 1's 11 Tier-B decorators carry `# reason:` comments 2-3 lines above the decorator they tag — when the decorator is multi-line (e.g. `tests/test_audio_macos_live.py:42`'s 8-line list-form pytestmark), the comment sits 3 lines above the `pytestmark = [...]` opening but the AST `lineno` for those is the assignment line, and `pytestmark` is NOT a decorator (it's an Assign), so it never enters the scan. Net: the 2-line window is sufficient for every real-world decorator in the tree."
  - "Three-line window above the flaky decorator (flake gate). Per 67-CONTEXT.md `### Flake Quarantine Gate` spec, the issue-link search window is `[lineno-3, lineno-2, lineno-1, lineno]`. Larger than the skip gate's window because an issue-link comment is naturally longer-form (multi-line URL or rationale block), so 3 lines of cushion is appropriate. Vacuous-green at landing (0 flaky decorators in tree); the window matters when Wave 4's flake-hunt adds the first one."
  - "Vacuous-green is correct for the flake gate, not a smell. The 67-CONTEXT.md is explicit: \"the static gate may go vacuous-green at landing — that's fine\". A test that exits 0 with no flaky decorators present is exactly the anti-drift surface we want; the gate's value is the failure it surfaces on the FIRST undocumented flake addition, not a populated assertion at landing."

patterns-established:
  - "Pattern: AST-walk static gate. Module structure: `from __future__ import annotations` → constants (REPO_ROOT, TESTS_DIR, _SELF_FILENAME) → private helpers (`_decorator_stem`, `_has_reason_kwarg`, `_has_reason_comment_nearby`, `_iter_test_files`) → single `def test_*` function that walks every test file's AST and accumulates an offender list. Final `assert not offenders, '...:\\n  ' + '\\n  '.join(offenders)` mirrors the offender-list-in-assertion-message idiom from `tests/repo/test_repo_scrub.py`. This shape is the project's new static-gate template for any decorator-shape invariant going forward — Wave 4 (flake-hunt) and future v7.0 phases can copy-modify it for their own invariants."
  - "Pattern: dual-channel reason-tagging on Tier-B tests. The Wave 1 fleet established (machine-readable `reason=` kwarg) + (human-readable `# reason:` comment) as the conservative shape for any test whose failure-mode points at a `KAAN-ACTION-LEGAL.md §V7-LIVE-NN` discharge cluster. The static gate (this plan) enforces minimum-viable \"at least one\" — code review enforces \"both for Tier-B\". The pattern scales: any future external-clock test should mirror it."
  - "Pattern: negative-control verification in plan execution. Both gates were verified twice — once for green-on-clean-tree (the engineering contract: today's tree must pass), once by introducing a scratch violation file under `tests/` and confirming the gate goes red with the offender listed at file:line, then deleting the scratch and confirming green restoration. The flake gate also got a positive-control sanity check (scratch with a valid `# issue: https://github.com/.../issues/42` line above the decorator → green). Belt-and-braces: green-against-current isn't enough proof; the gate must demonstrably trip on the exact violation shape it claims to catch."

requirements-completed: [TEST-01, TEST-03]

# Metrics
duration: 8min
completed: 2026-05-23
---

# Phase 67 Plan 67P03: All Tests Pass — Wave 2 (Static AST Gates) Summary

**Two new AST-walk static gates under `tests/repo/` lock the TEST-01 reason-tagging invariant + TEST-03 flake-issue-link invariant at CI collection time — `test_no_silent_skips.py` (148 lines) inspects every `@pytest.mark.skip` / `@pytest.mark.skipif` / `@pytest.mark.xfail` decorator and demands `reason=` kwarg OR `# reason:` comment within 2 lines above; `test_no_silent_flakes.py` (126 lines) demands `# issue: https://github.com/.../issues/N` within 3 lines above on every `@pytest.mark.flaky` (vacuously-green at landing, anti-drift surface for Wave 4). Both gates use `ast.parse` + `ast.walk` to handle multi-line decorators transparently (the 7-line `test_tts_3_1.py:164` skipif with wrapped `reason=` is the live witness). Default `uv run pytest -q` still GREEN (4158 passed / 26 skipped / 4 xpassed / 0 failed — exactly +2 from Wave 1 baseline, the two new gates). Zero `src/vibemix/` edits, zero net-new deps (stdlib `ast` + `pathlib` + `re` only).**

## Performance

- **Duration:** ~8 min (build both gates in parallel + verify + 2 negative controls + 1 positive control + commit)
- **Started:** 2026-05-23T~09:25 (post 67P02 SHIP)
- **Completed:** 2026-05-23
- **Tasks:** 2 (Task 1 = skip gate; Task 2 = flake gate)
- **Files modified:** 2 new test files + 1 SUMMARY (this file)

## Accomplishments

- **TEST-01 anti-drift surface enforced**: `tests/repo/test_no_silent_skips.py` walks every `tests/**/*.py` and AST-inspects each def's `decorator_list` for `@pytest.mark.skip` / `skipif` / `xfail` decorators, requiring `reason=` kwarg in the Call OR `# reason:` comment within 2 lines above. Passes against the current tree (28 existing `skipif` decorators all carry `reason=`; 11 Wave 1 Tier-B `xfail` decorators carry both `reason=` AND `# reason:` comment).
- **TEST-03 anti-drift surface enforced**: `tests/repo/test_no_silent_flakes.py` walks every `tests/**/*.py` and AST-inspects each def's `decorator_list` for `@pytest.mark.flaky`, requiring `# issue: https://github.com/<owner>/<repo>/issues/<N>` comment within 3 lines above. Vacuously-green at landing (zero flaky decorators in tree) — fires red the moment a future contributor adds an undocumented flaky marker.
- **AST over regex.** Both gates use `ast.parse` + `ast.walk` rather than regex on raw text. This handles multi-line decorators transparently — the 7-line `@pytest.mark.skipif(...)` at `tests/llm/test_tts_3_1.py:164` with its `reason=` string wrapped across 4 physical lines is exactly the kind of shape that breaks a regex-only gate (either misses the multi-line reason or false-fires on similar multi-line non-reason kwargs). AST inspects `Call.keywords` directly.
- **Negative controls verified locally for both gates.** Scratch violation files (`tests/_scratch_skip_violation.py` carrying a bare `@pytest.mark.skip` without reason; `tests/_scratch_flaky_violation.py` carrying `@pytest.mark.flaky(reruns=3)` without an issue link) were introduced, each gate fired red with offender file:line listed in the assertion message, then the scratch files were deleted and green was restored.
- **Positive control verified for flake gate.** A scratch file with a valid `# issue: https://github.com/vibemix/dj-set-ai/issues/42` comment 1 line above an `@pytest.mark.flaky(reruns=3)` decorator passed the gate green — confirming the issue-link pattern accepts the spec'd shape.
- **Default suite + tests/repo/ green.** `uv run pytest tests/repo/ -q` exits 0 (282 passed — was 280 in Wave 1, +2 for the new gates). `uv run pytest -q` exits 0 (4158 passed / 26 skipped / 4 xpassed / 13 warnings — was 4156 passed in Wave 1, +2 for the new gates; same 26 skipped + 4 xpassed; Wave 0+1 baseline preserved).

## Task Commits

1. **Task 1: `tests/repo/test_no_silent_skips.py` skip-reason gate** — `e5b7c98` (test) — 148-line AST-walk gate; passes on current tree; negative control verified.
2. **Task 2: `tests/repo/test_no_silent_flakes.py` flake-issue-link gate** — `dc29e3d` (test) — 126-line AST-walk gate; vacuously-green at landing; negative control + positive control verified.

**Plan metadata:** _this commit_ (docs: complete plan + STATE/ROADMAP updates)

## Files Created/Modified

| File | Change |
| --- | --- |
| `tests/repo/test_no_silent_skips.py` | NEW · 148 lines · AST gate for `@pytest.mark.{skip,skipif,xfail}` reason-tagging |
| `tests/repo/test_no_silent_flakes.py` | NEW · 126 lines · AST gate for `@pytest.mark.flaky` issue-link adjacency |
| `.planning/phases/67-all-tests-pass/67P03-SUMMARY.md` | NEW · this file |

## Verification Output (the green pytest lines)

```
$ uv run pytest tests/repo/test_no_silent_skips.py -v --tb=short
tests/repo/test_no_silent_skips.py::test_no_silent_skips PASSED          [100%]
============================== 1 passed in 0.29s ===============================

$ uv run pytest tests/repo/test_no_silent_flakes.py -v --tb=short
tests/repo/test_no_silent_flakes.py::test_no_silent_flakes PASSED        [100%]
============================== 1 passed in 0.30s ===============================

$ uv run pytest tests/repo/ -q --tb=short
282 passed in 14.93s
   (was 280 in Wave 1; +2 for the new gates; zero regression on prior 26 repo-presence tests)

$ uv run pytest -q --tb=no
4158 passed, 26 skipped, 4 xpassed, 13 warnings in 216.75s (0:03:36)
   (was 4156 / 26 / 4 in Wave 1; +2 for the new gates; same exit-0; 4 xpasses unchanged)
```

## Negative-Control Demonstrations

### Skip gate

Introduced `tests/_scratch_skip_violation.py`:
```python
import pytest

@pytest.mark.skip
def test_dummy_no_reason():
    pass
```

Gate fired red with the assertion:
```
E   AssertionError: Silent skip/skipif/xfail decorators detected — every such decorator
E   must carry EITHER a `reason=` kwarg inside the call OR a `# reason:` comment
E   within 2 lines above (TEST-01 invariant). Offenders:
E       tests/_scratch_skip_violation.py:4: @pytest.mark.skip without `reason=` kwarg
E       or `# reason:` comment within 2 lines above
```

Deleted the scratch file → gate green again.

### Flake gate (negative)

Introduced `tests/_scratch_flaky_violation.py`:
```python
import pytest

@pytest.mark.flaky(reruns=3)
def test_dummy_no_issue():
    pass
```

Gate fired red with the assertion:
```
E   AssertionError: Silent @pytest.mark.flaky decorators detected — every flaky
E   marker must carry an adjacent `# issue: https://github.com/.../issues/N` comment
E   within 3 lines above (TEST-03 invariant). Offenders:
E       tests/_scratch_flaky_violation.py:4: @pytest.mark.flaky without
E       `# issue: https://github.com/.../issues/N` comment within 3 lines above
```

Deleted the scratch file → gate green again.

### Flake gate (positive)

Introduced `tests/_scratch_flaky_valid.py`:
```python
import pytest

# issue: https://github.com/vibemix/dj-set-ai/issues/42
@pytest.mark.flaky(reruns=3)
def test_dummy_with_issue():
    pass
```

Gate passed green (confirming the spec'd issue-link shape is accepted). Deleted the scratch file.

## Decisions Made

- **AST over regex.** Plan task wording mentioned `regex scan`; user's execution-time prompt mandated `ast.parse` + walk. AST is the correct call regardless — the live witness in this tree (`tests/llm/test_tts_3_1.py:164`'s 7-line skipif with wrapped `reason=` across 4 lines) breaks a regex-only gate. AST inspects `Call.keywords` directly, line-layout-agnostic by construction.

- **All three of skip/skipif/xfail in the scope of the skip gate.** Plan task wording proposed excluding `skipif` via `(?!\w)` negative lookahead, on the theory that "pytest already requires `reason=` on skipif". User's execution prompt countered: include all three. The tree-wide evidence confirms this is right — all 28 existing `skipif` decorators carry `reason=` already, so including it in the gate is zero-cost on the current tree AND it's the conservative invariant going forward. `@pytest.mark.skipif(cond)` without `reason=` is pytest-legal but exactly the silent skip the gate exists to prevent.

- **Two-line window for skip gate, three-line window for flake gate.** Per the 67-CONTEXT.md spec. The skip gate's `# reason:` comment is short-form (one line); 2 lines of cushion (above + on decorator line) is enough for every real decorator in the tree. The flake gate's `# issue:` line is longer-form (URL); 3 lines of cushion gives the contributor room for either a one-liner above the decorator OR a 2-line context-then-link block.

- **Vacuous-green is correct for the flake gate.** Per 67-CONTEXT.md explicitly. The gate's value is the failure on the FIRST undocumented flake addition, not a populated assertion at landing. The current 0 flaky decorators in tree → gate exits 0 → that's exactly what TEST-03 specifies.

- **Self-exclusion guard.** Each gate excludes its own filename from the `tests/**/*.py` rglob. AST-based scanning makes this defensive-only (decorator-stem string literals in the gate's own source code are never AST decorators), but it matches the existing `tests/repo/test_repo_scrub.py` tokenize-based stripping convention and keeps both gates future-proof against accidental example-code references.

- **Two atomic task commits, not one combined.** Plan structure (`<task type="auto">` × 2) called for atomic per-task commits. Even though both gates are tiny + tightly coupled in intent, the per-task discipline keeps the audit history clear: Task 1 = skip gate landing; Task 2 = flake gate landing. If a future bisect ever needs to attribute a behavior change to one gate, the per-task commits are the right granularity.

## Deviations from Plan

None — plan executed as written. The only delta from plan task wording was the AST-vs-regex pivot (covered under Decisions Made above), which was an explicit user directive at execution time, not an autonomous discovery. Zero Rule 1/2/3 auto-fixes were needed (no bugs found, no missing critical functionality, no blockers). Zero Rule 4 architectural decisions. Zero auth gates.

## Issues Encountered

None. Both gates worked on first write; both negative controls fired as expected on first scratch-file introduction; positive control passed on first try. The cleanest of the three plans in Phase 67 so far — the work was all done by Wave 0 + Wave 1 establishing the baseline + the decorator shape; this wave just locks them in static.

## Threat Flags

None. This plan modifies only test files (two new files under `tests/repo/` + this SUMMARY). No new network endpoints, no auth paths, no file access patterns at trust boundaries, no schema changes, no `src/vibemix/` edits. Zero new dependencies — both gates use stdlib `ast` + `pathlib` + `re` only.

## Known Stubs

None introduced. Both gates are fully-implemented contracts — they assert on real conditions over the real tree.

## User Setup Required

None. All changes land in the existing repo + pyproject toolchain — no env vars, no dashboards, no external service config. The two new gates run as part of `uv run pytest -q` by default (no marker, no opt-in).

## Next Phase Readiness

Wave 2 of Phase 67 ships the anti-drift surfaces that Waves 3 + 4 + downstream phases will rely on:

- **TEST-01 SC#1 anti-drift surface** => SATISFIED. Any future skip/xfail without a reason fails CI at collection time. The 11 Wave 1 Tier-B decorators all pass; the 28 existing `skipif` decorators all pass; future drift is caught.
- **TEST-03 SC#3 anti-drift surface** => SATISFIED. Any future `@pytest.mark.flaky` without a GitHub issue link fails CI. Wave 4's flake-hunt has a clear contract: if a non-deterministic test surfaces, the contributor must EITHER fix it OR open a GitHub issue + link it in a `# issue:` comment above the decorator.
- **Wave 3 prerequisite** (`.github/workflows/full-test-matrix.yml`): both new gates run as part of the default `pytest -q` matrix that the workflow will invoke. No special wiring needed — the gates piggyback on the default-green invariant Wave 0 established.

Open follow-ups for Phase 67 downstream waves:
- **Wave 3:** `.github/workflows/full-test-matrix.yml` runs the marker grid on `macos-13` + `macos-14` + `windows-latest` for every push to `main` + every PR.
- **Wave 4:** 10× consecutive `uv run pytest -q` flake-hunt; document protocol in `docs/flake-hunt.md`; quarantine any non-deterministic test surfaced behind `@pytest.mark.flaky` + `# issue:` link (the gate from this wave will then enforce the link).
- **README badges row:** lands in Phase 70 (GH pillar), not here.

No new blockers. No Kaan-discharge surfaces created in this wave (the gates are pure engineering — they don't introduce any §V7-LIVE clusters).

## Self-Check: PASSED

Verified before STATE/ROADMAP writes:
- `tests/repo/test_no_silent_skips.py` => FOUND (148 lines)
- `tests/repo/test_no_silent_flakes.py` => FOUND (126 lines)
- `.planning/phases/67-all-tests-pass/67P03-SUMMARY.md` => FOUND (this file)
- Task 1 commit `e5b7c98` => FOUND in `git log --oneline`
- Task 2 commit `dc29e3d` => FOUND in `git log --oneline`
- `uv run pytest tests/repo/test_no_silent_skips.py -q --tb=no | tail -1` => `1 passed in 0.29s` (exit 0)
- `uv run pytest tests/repo/test_no_silent_flakes.py -q --tb=no | tail -1` => `1 passed in 0.30s` (exit 0)
- `uv run pytest tests/repo/ -q --tb=no | tail -1` => `282 passed in 14.93s` (exit 0; +2 from Wave 1's 280)
- `uv run pytest -q --tb=no | tail -1` => `4158 passed, 26 skipped, 4 xpassed, 13 warnings in 216.75s` (exit 0; Wave 0+1 baseline preserved, +2 from the new gates)
- Negative control (skip gate, scratch `@pytest.mark.skip` without reason) => RED with offender at file:line listed; revert → GREEN
- Negative control (flake gate, scratch `@pytest.mark.flaky` without issue link) => RED with offender at file:line listed; revert → GREEN
- Positive control (flake gate, scratch with valid `# issue: https://github.com/.../issues/42`) => GREEN; revert
- `git diff --stat src/vibemix/ HEAD~2..HEAD` => empty (zero `src/vibemix/` edits — acid test held)

---
*Phase: 67-all-tests-pass*
*Plan: 67P03*
*Completed: 2026-05-23*
