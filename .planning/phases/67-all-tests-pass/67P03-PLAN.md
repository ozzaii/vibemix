---
phase: 67-all-tests-pass
plan: 67P03
type: execute
wave: 2
depends_on: [67P01, 67P02]
files_modified:
  - tests/repo/test_no_silent_skips.py
  - tests/repo/test_no_silent_flakes.py
autonomous: true
requirements: [TEST-01, TEST-03]
must_haves:
  truths:
    - "Adding `@pytest.mark.skip` or `@pytest.mark.xfail` without an adjacent `# reason:` comment OR `reason=` kwarg fails CI"
    - "Adding `@pytest.mark.flaky` without an adjacent `# issue: https://github.com/.../issues/N` link comment fails CI"
    - "The existing 28 `skipif` + the new Wave-1 `xfail` decorators all pass the skip-reason gate today"
  artifacts:
    - path: tests/repo/test_no_silent_skips.py
      provides: "Static AST/regex gate enforcing reason-tagging on skip/xfail decorators"
      min_lines: 30
      exports: ["test_no_silent_skips"]
    - path: tests/repo/test_no_silent_flakes.py
      provides: "Static AST/regex gate enforcing issue-link comment on flaky decorators"
      min_lines: 30
      exports: ["test_no_silent_flakes"]
  key_links:
    - from: tests/repo/test_no_silent_skips.py
      to: every test file under tests/
      via: "rglob('*.py') + regex scan for @pytest.mark.skip/xfail"
      pattern: "rglob"
    - from: tests/repo/test_no_silent_flakes.py
      to: every test file under tests/
      via: "rglob('*.py') + regex scan for @pytest.mark.flaky + issue-link window"
      pattern: "issue:"
---

<objective>
Wave 2 — Build the two static gates that prevent future drift: `tests/repo/test_no_silent_skips.py` (enforces `# reason:` or `reason=` adjacency on every `@pytest.mark.skip` and `@pytest.mark.xfail` decorator) and `tests/repo/test_no_silent_flakes.py` (enforces `# issue: https://github.com/.../issues/N` adjacency on every `@pytest.mark.flaky` decorator).

Purpose: TEST-01 says every skip/xfail/xpass must carry a `# reason:` OR be converted to a `§V7-LIVE` external-clock item; TEST-03 says any `@pytest.mark.flaky` must carry a linked GitHub issue. The repo today has 0 `@pytest.mark.skip` and 0 `@pytest.mark.xfail` and 0 `@pytest.mark.flaky` decorators (RESEARCH.md "Existing skip/xfail patterns" verified), so the gates are primarily anti-drift — but Wave 1 (P02) added the first xfail decorators on Tier-B tests, so the skip gate must accept them. Gates follow the existing `tests/repo/test_repo_scrub.py::test_retired_poc_files_stay_gone` pattern (regex scan over `git ls-files` / `rglob('*.py')`).

Output: Two new static gate test files at `tests/repo/test_no_silent_skips.py` and `tests/repo/test_no_silent_flakes.py`. Both pass against `main` after Wave 0 + Wave 1. A negative-control verification confirms each gate fires red when a no-reason / no-issue-link decorator is introduced.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/67-all-tests-pass/67-CONTEXT.md
@.planning/phases/67-all-tests-pass/67-RESEARCH.md
@.planning/phases/67-all-tests-pass/67P02-SUMMARY.md
@tests/repo/test_repo_scrub.py
@CLAUDE.md

<interfaces>
<!-- Existing static-gate prior art the executor must mirror. -->

From tests/repo/test_repo_scrub.py (existing pattern):
```python
REPO_ROOT = Path(__file__).resolve().parent.parent.parent

def _git_ls_files() -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=REPO_ROOT,
                         capture_output=True, text=True, check=True)
    return [line for line in out.stdout.splitlines() if line]

def test_retired_poc_files_stay_gone() -> None:
    # regex/membership scan + assert with offender list in failure message
```

The two new gates follow the same conventions: module constants at top, helper functions prefixed `_`, single `def test_*` function per file, offender list joined into assertion message, `from __future__ import annotations`.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Write `tests/repo/test_no_silent_skips.py` skip-reason gate</name>
  <read_first>
    - tests/repo/test_repo_scrub.py (the static-gate idiom — module constants, helpers, single test function, offender-list assertion)
    - .planning/phases/67-all-tests-pass/67-RESEARCH.md (Code Examples — "New gate template (TEST-01 — test_no_silent_skips.py)" gives the exact regex + 2-line-window + reason= multi-line fallback logic; Pitfall 8 — must accept both `# reason:` comment AND `reason=` kwarg within ~4 lines)
    - .planning/phases/67-all-tests-pass/67-CONTEXT.md (`### Reason Tagging` — comment within 2 lines above or on decorator line)
    - tests/llm/test_tts_3_1.py (RESEARCH.md Pitfall 8 cites lines 164-170 — multi-line `skipif` with `reason=` split across lines, must pass the gate)
    - tests/repo/ (run `ls tests/repo/` to confirm directory layout + any conftest.py shape)
  </read_first>
  <action>
    Create new file `tests/repo/test_no_silent_skips.py`. Module structure: `from __future__ import annotations`; imports `re` + `pathlib.Path`; constants `REPO_ROOT = Path(__file__).resolve().parent.parent.parent` and `TESTS_DIR = REPO_ROOT / "tests"`. Define `SKIP_DECORATOR_PATTERN = re.compile(r"^\s*@pytest\.mark\.(skip|xfail)\b(?!\w)")` — the `(?!\w)` negative lookahead prevents matching `@pytest.mark.skipif` (already pytest-required to carry `reason=`). Define `_has_reason_nearby(lines: list[str], idx: int) -> bool` per RESEARCH.md template: accept a `# reason:` comment in lines `[idx-2, idx-1, idx]` OR `reason=` substring in lines `[idx, idx+1, idx+2, idx+3]` (multi-line decorator support per Pitfall 8). Define `test_no_silent_skips()` that rglobs `TESTS_DIR / "*.py"`, reads each file as utf-8 splitlines, iterates lines, and accumulates an `offenders` list of `f"{relpath}:{lineno}: {line.strip()}"` for any matching decorator without nearby reason. Final `assert not offenders, "Silent skip/xfail decorators...:\n  " + "\n  ".join(offenders)`. CRITICAL: exclude `tests/repo/test_no_silent_skips.py` itself from the rglob if the regex literal in this file would otherwise be detected (the regex source string `@pytest\.mark\.(skip|xfail)` does NOT match `@pytest.mark.skip` literally because of the backslashes, but to be paranoid, add `if py.name == "test_no_silent_skips.py": continue` skip at the top of the rglob loop). Verify by running the gate against the current repo: it must PASS (0 offenders, because all existing skips are `skipif` and all Wave-1 xfails carry both `reason=` kwarg AND `# reason:` comment). Then do a negative-control: in a scratch worktree or via `git stash` save-point, add `@pytest.mark.skip\ndef test_dummy(): ...` to any test file without a `# reason:` — re-run the gate, confirm it fails red listing the new offender, then `git stash pop` / discard the scratch change.
  </action>
  <verify>
    <automated>uv run pytest tests/repo/test_no_silent_skips.py -v --tb=short 2>&1 | tail -3</automated>
  </verify>
  <done>`tests/repo/test_no_silent_skips.py` exists with the structure above. The test passes against `main` HEAD (0 offenders today). Negative-control verified: a bare `@pytest.mark.skip` introduction without `# reason:` triggers an assertion failure listing the offender. The gate respects the `(?!\w)` lookahead — `@pytest.mark.skipif` calls are NOT matched. Mandatory implements: TEST-01 success criterion #1's "every existing skip / xfail / xpass carries a one-line `# reason:` adjacent to its marker" (the gate is the static enforcement of this invariant — per D-TEST-01).</done>
</task>

<task type="auto">
  <name>Task 2: Write `tests/repo/test_no_silent_flakes.py` flake-issue-link gate</name>
  <read_first>
    - tests/repo/test_no_silent_skips.py (the just-written sibling — same shape, same module structure)
    - .planning/phases/67-all-tests-pass/67-RESEARCH.md (Code Examples — "New gate template (TEST-03 — test_no_silent_flakes.py)" gives the exact regex + 3-line window + issue-link pattern; CONTEXT decision: window is `lines[max(0, i-3): i+4]` — 3 lines above OR below)
    - .planning/phases/67-all-tests-pass/67-CONTEXT.md (`### Flake Quarantine Gate` — issue link must be `# issue: https://github.com/.../issues/N` within 3 lines of decorator; verification: scratch PR with no-link decorator must turn CI red)
    - pyproject.toml (confirm the `flaky` marker line landed in Wave 0)
  </read_first>
  <action>
    Create new file `tests/repo/test_no_silent_flakes.py`. Same module structure as `test_no_silent_skips.py`: `from __future__ import annotations`, `re` + `pathlib.Path` imports, `REPO_ROOT` + `TESTS_DIR` constants. Define `FLAKY_DECORATOR_PATTERN = re.compile(r"^\s*@pytest\.mark\.flaky\b")`. Define `ISSUE_LINK_PATTERN = re.compile(r"#\s*issue:\s*https://github\.com/[\w.\-]+/[\w.\-]+/issues/\d+")`. Define `test_no_silent_flakes()` that rglobs `TESTS_DIR / "*.py"`, iterates lines, and for any line matching `FLAKY_DECORATOR_PATTERN` checks the 7-line window `lines[max(0, i-3): i+4]` (3 above through 3 below inclusive — RESEARCH.md template) for any line matching `ISSUE_LINK_PATTERN`. If none, accumulate `f"{relpath}:{lineno}: @pytest.mark.flaky without `# issue: https://github.com/.../issues/N` comment within 3 lines"` to offenders. Final assertion same shape as Task 1. Exclude `tests/repo/test_no_silent_flakes.py` itself from the rglob (the regex source string contains `@pytest\.mark\.flaky` but the backslashes mean it won't literally match — still, defensive `if py.name == "test_no_silent_flakes.py": continue` skip per Task 1 convention). The gate must PASS against `main` HEAD today (0 `@pytest.mark.flaky` decorators in the repo per RESEARCH.md verified count = 0). Negative-control: in a scratch worktree, add `@pytest.mark.flaky\ndef test_flaky_dummy(): ...` to any test file without a nearby `# issue:` comment — re-run gate, confirm it fails red, then discard the scratch change. Verify the marker is declared by also running `uv run pytest --collect-only -q 2>&1 | grep -c "PytestUnknownMarkWarning"` — must be 0 (RESEARCH.md Pitfall 3 — Wave 0 declared the marker, this should be clean).
  </action>
  <verify>
    <automated>uv run pytest tests/repo/test_no_silent_flakes.py -v --tb=short 2>&1 | tail -3 && uv run pytest tests/repo/ -q --tb=short 2>&1 | tail -3</automated>
  </verify>
  <done>`tests/repo/test_no_silent_flakes.py` exists with the structure above. Gate passes against `main` (0 offenders, 0 flaky decorators exist today). Negative-control verified: a `@pytest.mark.flaky` without `# issue:` link triggers a failing assertion listing the offender. The entire `tests/repo/` directory passes (`uv run pytest tests/repo/ -q` exits 0) — both new gates green, no regression in the other 26 repo-presence tests. Mandatory implements: TEST-03 static gate ("`tests/repo/test_no_silent_flakes.py` catches new `@pytest.mark.flaky` decorators that don't carry an issue link" per D-TEST-03).</done>
</task>

</tasks>

<verification>
  - `uv run pytest tests/repo/test_no_silent_skips.py -v` exits 0
  - `uv run pytest tests/repo/test_no_silent_flakes.py -v` exits 0
  - `uv run pytest tests/repo/ -q` exits 0 (full repo-presence suite green incl. existing 26 tests)
  - `uv run pytest -q` exits 0 (Wave 0 default-green invariant preserved)
  - Negative controls verified locally and documented in SUMMARY
</verification>

<success_criteria>
- Both static gates exist, both pass, both can be demonstrated to fire red on violations.
- TEST-01's reason-tagging invariant + TEST-03's flake-issue-link invariant are now enforced at CI collection time.
- Zero net-new dependencies (pure stdlib regex + pathlib).
</success_criteria>

<output>
Create `.planning/phases/67-all-tests-pass/67P03-SUMMARY.md` with: the two static-gate source files (or excerpts), the green pytest output lines for both gates, and the negative-control demonstrations (the scratch decorator additions + their failure messages, then the revert).
</output>
