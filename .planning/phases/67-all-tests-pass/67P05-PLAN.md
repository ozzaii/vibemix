---
phase: 67-all-tests-pass
plan: 67P05
type: execute
wave: 4
depends_on: [67P01, 67P02, 67P03, 67P04]
files_modified:
  - docs/flake-hunt.md
  - tests/  # quarantine decorators only if flake-hunt surfaces non-determinism
autonomous: true
requirements: [TEST-03]
must_haves:
  truths:
    - "10 consecutive `pytest -q` runs all exit 0 OR every flake found is quarantined with `@pytest.mark.flaky` + linked GH issue"
    - "The flake-hunt protocol is documented in `docs/flake-hunt.md` for future contributors"
    - "`tests/repo/test_no_silent_flakes.py` (from P03) still passes after any quarantine added in this wave"
  artifacts:
    - path: docs/flake-hunt.md
      provides: "Reproducible 10× flake-hunt protocol contributors can run before opening a PR with a `@pytest.mark.flaky` decorator"
      contains: "10×"
      min_lines: 30
  key_links:
    - from: docs/flake-hunt.md
      to: tests/repo/test_no_silent_flakes.py
      via: "documentation references the static gate that enforces issue-link adjacency"
      pattern: "test_no_silent_flakes"
    - from: any new `@pytest.mark.flaky` decorator (if added)
      to: a GitHub issue under ozzaii/vibemix/issues
      via: "# issue: https://github.com/ozzaii/vibemix/issues/N comment within 3 lines"
      pattern: "# issue: https://github.com"
---

<objective>
Wave 4 — Run a 10× consecutive `pytest -q` flake-hunt on Kaan's Mac; quarantine any test that doesn't hit 100% pass rate behind `@pytest.mark.flaky` + a new GitHub issue + a `# issue:` link comment (which the P03 gate enforces); document the protocol at `docs/flake-hunt.md` so future contributors run the same hunt before adding a flaky decorator.

Purpose: TEST-03 says "any non-deterministic test (10× consecutive run reveals < 100% pass) is either stabilized via test surgery, OR quarantined behind a `@pytest.mark.flaky` decorator with a linked GitHub issue." This wave is the actual hunt — earlier waves built the gates that would catch a silent flaky decorator, but only an actual 10× run reveals real non-determinism. CONTEXT D-TRIAGE says "Default to Tier B over Tier C" — prefer test-surgery over quarantine; only flag-quarantine if surgery is non-trivial or genuinely external (e.g. timing-sensitive Gemini API mock that occasionally hits a real edge). Per Assumption A7, shell loop is sufficient — no `pytest-repeat` dependency (zero net-new deps).

Output: A documented 10× hunt protocol; the actual hunt log (10 run-counts + their pass/fail status); for any flake found, a quarantine commit pattern (decorator + issue + reason). Under `gsd-autonomous fully` if no flakes surface, the wave closes with the empty protocol and a "10× clean" record.
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
@.planning/phases/67-all-tests-pass/67P03-SUMMARY.md
@.planning/phases/67-all-tests-pass/67P04-SUMMARY.md
@tests/repo/test_no_silent_flakes.py
@CLAUDE.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Write `docs/flake-hunt.md` protocol + run the 10× hunt locally</name>
  <read_first>
    - .planning/phases/67-all-tests-pass/67-CONTEXT.md (`### Flake Quarantine Gate` + `### Claude's Discretion` re: rerun counts)
    - .planning/phases/67-all-tests-pass/67-RESEARCH.md (Code Examples — "Wave 3 — Local 10× flake-hunt loop" gives the exact `for i in $(seq 1 10); do ...` bash; Standard Stack — `pytest-repeat` REJECTED; `pytest-rerunfailures` REJECTED; "trust the audio more than retries"; Assumption A7)
    - tests/repo/test_no_silent_flakes.py (from P03 — confirm the issue-link regex the doc must teach contributors)
    - CLAUDE.md "Commands" section (canonical invocations)
    - ls docs/ (confirm where to put the new file; `docs/contributing/` exists per ROADMAP P68 reference; create `docs/flake-hunt.md` at docs root for visibility)
  </read_first>
  <action>
    Create new file `docs/flake-hunt.md`. Sections: (1) **Why** — non-determinism kills CI trust; TEST-03's quarantine gate is anti-rot, not anti-investigation; default to test-surgery over quarantine per CONTEXT "Tier B over Tier C". (2) **Run the hunt** — exact bash invocation: `set -euo pipefail; for i in $(seq 1 10); do echo "=== Run $i/10 ==="; uv run pytest -q --tb=line || exit 1; done && echo "10× GREEN — flake-hunt clean"` (per RESEARCH.md Wave 3 code example). Document expected wall-clock (~36 min per RESEARCH.md — 3.6 min × 10). (3) **If a test fails on run N but passed on run N-1** — first try test surgery: read the failing test, identify the non-determinism source (timing, hash ordering, fixture leak, network flake), fix it. If surgery is non-trivial or genuinely external (e.g. a Gemini API mock that 1-in-N runs hits an edge): file a GitHub issue at `https://github.com/ozzaii/vibemix/issues/new` titled "Flake: <test_id> non-deterministic", add `@pytest.mark.flaky` decorator with `# issue: https://github.com/ozzaii/vibemix/issues/N` comment within 3 lines, link the issue from the decorator. (4) **The gate** — `tests/repo/test_no_silent_flakes.py` enforces the issue-link adjacency; a `@pytest.mark.flaky` without an issue link fails CI. Show the exact decorator + comment pattern per RESEARCH.md Code Examples ("TEST-03 — Mark a flaky test"). (5) **Zero net-new deps** — `pytest-rerunfailures` and `pytest-repeat` are explicitly NOT installed; the marker is a quarantine signal, not auto-retry; shell loop is the hunt vehicle. After writing the doc, RUN the actual 10× hunt on Kaan's Mac: `set -euo pipefail; for i in $(seq 1 10); do echo "=== Run $i/10 ==="; uv run pytest -q --tb=line 2>&1 | tee /tmp/p67p05-run-$i.log | tail -3; done` and capture each run's tail line. If all 10 exit 0, record the clean result. If any exit non-zero: identify the failing test_id, re-run it 5× in isolation (`for i in 1 2 3 4 5; do uv run pytest tests/path/test_x.py::test_y -v; done`) to characterize the flake, then proceed to Task 2 (quarantine). If runs exceed time budget (~40 min × N), the hunt can be backgrounded; SUMMARY records the actual elapsed wall-clock.
  </action>
  <verify>
    <automated>test -f docs/flake-hunt.md && grep -c "10×\|seq 1 10\|test_no_silent_flakes" docs/flake-hunt.md && ls /tmp/p67p05-run-*.log 2>/dev/null | wc -l</automated>
  </verify>
  <done>`docs/flake-hunt.md` exists with the 5 sections above. The 10× hunt was actually executed: 10 log files at `/tmp/p67p05-run-{1..10}.log` exist with their tail lines. Either: (a) all 10 runs exited 0 → SUMMARY records "10× GREEN — flake-hunt clean" and Task 2 has no work, OR (b) ≥1 run failed → flake test_id and characterization recorded in working notes for Task 2. Mandatory implements: TEST-03 success criterion ("10× consecutive re-run reveals no test below 100% pass rate" — the hunt that proves it — per D-TEST-03); ZERO net-new dependencies (shell loop only).</done>
</task>

<task type="auto">
  <name>Task 2: Quarantine any flake found (conditional — skip if Task 1 ran 10× clean)</name>
  <read_first>
    - Task 1's hunt log + characterization notes
    - tests/repo/test_no_silent_flakes.py (the gate the quarantine decorator must satisfy)
    - .planning/phases/67-all-tests-pass/67-RESEARCH.md (Code Examples — "TEST-03 — Mark a flaky test" — exact decorator + comment pattern; "Standard Stack — Alternatives Considered" confirms the marker is pure tagging not auto-retry)
    - .planning/phases/67-all-tests-pass/67-CONTEXT.md (`### Claude's Discretion` — preferred default is "no rerun count, just tag + issue link")
    - docs/flake-hunt.md (the doc just written — the quarantine pattern MUST match what the doc teaches contributors)
  </read_first>
  <action>
    **Conditional task.** If Task 1's 10× hunt ran 10× clean (all runs exit 0): record "no flakes found — task skipped" in SUMMARY and exit this task. Otherwise: for each flake characterized in Task 1, (a) open a new GitHub issue via `gh issue create --title "Flake: <test_id> non-deterministic on 10× run" --body "Surfaced by Phase 67 Wave 4 flake-hunt. Run N/10 failed; runs 1..N-1 + N+1..10 passed. Characterization: <one-paragraph diagnosis from Task 1>. Quarantined via @pytest.mark.flaky; this issue tracks the fix path."` and capture the issue URL (under `gsd-autonomous fully`, if `gh` is unavailable or auth-blocked, generate a "would-be-filed" issue body in SUMMARY and route the actual filing to KAAN-ACTION-LEGAL.md §V7-LIVE as a soft Kaan-discharge item under a new `### §V7-LIVE-FLAKE-N` sub-entry — do NOT block on issue filing). (b) Open the failing test file. Add `# issue: https://github.com/ozzaii/vibemix/issues/N` as a comment line directly above (within 3 lines) the existing test decorators. Add `@pytest.mark.flaky` decorator at the same indentation level. Example (per RESEARCH.md "TEST-03 — Mark a flaky test"):
    
        # issue: https://github.com/ozzaii/vibemix/issues/N
        @pytest.mark.flaky
        def test_known_flaky_thing():
            ...
    
    Do NOT add `(reruns=N)` arguments — per CONTEXT discretion default, the marker is pure tagging; do NOT install `pytest-rerunfailures`. Re-run the static gate: `uv run pytest tests/repo/test_no_silent_flakes.py -v` — must exit 0 (the new decorator carries the required issue link). Re-run the default suite: `uv run pytest -q` — the flaky test still runs (the custom `flaky` marker is pure tagging, doesn't skip/xfail/retry), so the result is whatever it was — but the test now CARRIES the quarantine signal for future maintainers.
  </action>
  <verify>
    <automated>uv run pytest tests/repo/test_no_silent_flakes.py -v --tb=short 2>&1 | tail -3 && uv run pytest -q --tb=line 2>&1 | tail -3</automated>
  </verify>
  <done>If no flake found: this task records "no-op" in SUMMARY with the 10× clean log lines. If flakes found: each flake has a quarantine commit pattern applied (decorator + issue-link comment), the static gate `test_no_silent_flakes.py` still passes (issue-link adjacency satisfied), and a new `§V7-LIVE-FLAKE-N` sub-entry exists in `KAAN-ACTION-LEGAL.md` if `gh issue create` was unavailable. Mandatory implements: TEST-03 success criterion #2 ("non-deterministic test is quarantined behind a `@pytest.mark.flaky` decorator with a linked GitHub issue" — per D-TEST-03).</done>
</task>

</tasks>

<verification>
  - `docs/flake-hunt.md` exists with the 5-section protocol
  - 10× hunt log captured (10 files at `/tmp/p67p05-run-{1..10}.log`)
  - If flakes found: quarantine pattern applied; `test_no_silent_flakes.py` still green; new issue filed (or §V7-LIVE-FLAKE-N entry created if gh unavailable)
  - `uv run pytest -q` exit code stable (Wave 0 invariant preserved)
  - Zero net-new dependencies — no `pytest-repeat`, no `pytest-rerunfailures` (verify via `grep -E "pytest-(repeat|rerunfailures)" pyproject.toml uv.lock` returns 0)
</verification>

<success_criteria>
- TEST-03 closed: either 10× clean (most likely outcome per RESEARCH.md confidence) OR quarantine pattern proven end-to-end.
- Contributor-facing flake-hunt doc lands at `docs/flake-hunt.md` for future PRs.
- Zero net-new dependencies. Zero reaction-path edits.
- All four cardinal v7.0 invariants held by zero-touch.
</success_criteria>

<output>
Create `.planning/phases/67-all-tests-pass/67P05-SUMMARY.md` with: the `docs/flake-hunt.md` excerpt, the 10× hunt log summary (10 run results), the quarantine ledger (empty if 10× clean, otherwise per-flake decorator diff + issue URL), and the final phase status declaration ("Phase 67 — All Tests Pass — engineering-green; TEST-01..04 closed; §V7-LIVE rides Kaan-ear clock for the 65-opt-in live confirmation").
</output>
