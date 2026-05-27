---
phase: 67-all-tests-pass
plan: 67P04
type: execute
wave: 3
depends_on: [67P01, 67P02, 67P03]
files_modified:
  - .github/workflows/full-test-matrix.yml
  - README.md
autonomous: true
requirements: [TEST-02, TEST-04]
must_haves:
  truths:
    - "`.github/workflows/full-test-matrix.yml` exists, valid YAML, triggers on every push to `main` and every PR"
    - "Matrix covers `[macos-13, macos-14, windows-latest] × [default, macos_audio, windows_only, integration, slow, e2e, cli, network]` with OS-incompatible markers excluded"
    - "A green badge for the workflow appears in the README badges row"
    - "Concurrency group cancels in-flight runs on the same PR"
  artifacts:
    - path: .github/workflows/full-test-matrix.yml
      provides: "Full marker × OS test matrix workflow"
      contains: "full-test-matrix"
      min_lines: 50
    - path: README.md
      provides: "Workflow status badge in badges row"
      contains: "full-test-matrix.yml"
  key_links:
    - from: README.md
      to: .github/workflows/full-test-matrix.yml
      via: "shields.io/github/actions/workflow/status URL pointing at the workflow file"
      pattern: "full-test-matrix.yml"
    - from: .github/workflows/full-test-matrix.yml
      to: pyproject.toml [tool.pytest.ini_options].markers
      via: "matrix.marker values map 1:1 to declared markers"
      pattern: "marker:"
---

<objective>
Wave 3 — Ship `.github/workflows/full-test-matrix.yml` running the full marker grid on `[macos-13, macos-14, windows-latest]` for every push to `main` and every PR, with a status badge in the README badges row.

Purpose: TEST-04 is the visible CI contract — without it, downstream P68/P69/P70 cannot trust the test suite as a green-by-default surface. CONTEXT D-CI locks the workflow shape: separate workflow file (not folded into `eval.yml`), per-marker job in matrix (not collapsed `or`-filter), OS-incompatible markers excluded, concurrency group cancels in-flight, `fail-fast: false`. The workflow follows the existing `.github/workflows/release.yml:247-310` matrix prior art + `.github/workflows/dep-audit.yml:49-51` concurrency prior art + `.github/workflows/eval.yml` uv setup prior art (RESEARCH.md Sources). All action `uses:` lines SHA-pinned per `dep-audit.yml` pinact-audit invariant.

Output: New workflow file + new badge line in README. After this plan completes and the workflow is pushed to `main`, the badge surfaces a real status on the next push. Tier-B xfails from P02 ensure the workflow runs amber (not red) on hosted runners where BlackHole/FLX4/Win11-desktop-SKU aren't available.
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
@.github/workflows/eval.yml
@.github/workflows/release.yml
@.github/workflows/dep-audit.yml
@README.md
@pyproject.toml
@CLAUDE.md

<interfaces>
<!-- Existing workflow patterns the executor MUST mirror. -->

From .github/workflows/eval.yml (uv + setup-python + pinned-SHA pattern):
```yaml
uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5  # v4.3.1
uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065  # v5.6.0
uses: astral-sh/setup-uv@caf0cab7a618c569241d31dcd442f54681755d39  # v3.2.4
```

From .github/workflows/release.yml:247-310 (mac+win matrix pattern):
```yaml
strategy:
  fail-fast: false
  matrix:
    os: [macos-13, macos-14, windows-latest]
```

From .github/workflows/dep-audit.yml:49-51 (concurrency pattern — must use a WORKFLOW-PREFIXED group name per RESEARCH.md Pitfall 4):
```yaml
concurrency:
  group: dep-audit-${{ github.ref }}
  cancel-in-progress: true
```

From existing README badges row (around line 40-43 per RESEARCH.md):
```markdown
<a href="https://github.com/.../actions/workflows/<workflow>.yml"><img alt="..." src="https://img.shields.io/github/actions/workflow/status/.../<workflow>.yml?label=...&branch=main&style=flat-square" /></a>
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Write `.github/workflows/full-test-matrix.yml`</name>
  <read_first>
    - .github/workflows/eval.yml (uv + setup-python step shapes; SHA-pinned `uses:` lines; `GEMINI_API_KEY` from secrets pattern at line 61)
    - .github/workflows/release.yml lines 247-310 (the `[macos-13, macos-14]` + (optionally) `windows-latest` matrix prior art)
    - .github/workflows/dep-audit.yml lines 49-51 (concurrency group + cancel-in-progress)
    - .planning/phases/67-all-tests-pass/67-RESEARCH.md (`### Pattern 2` — full workflow YAML template with the exclude grid; Pitfall 4 — concurrency group must be workflow-prefixed; Pitfall 5 — badge needs at least one run on `main`; Pitfall 6 — `fail-fast: false`; Open Question 1 + 2 — run `default` on all 3 OSes, `timeout-minutes: 30`; Assumption A5 — `GEMINI_API_KEY` is already a GH Secret)
    - .planning/phases/67-all-tests-pass/67-CONTEXT.md (`### CI Workflow Shape` — separate workflow, push-to-main + PR triggers ONLY, per-marker isolation, concurrency cancellation)
    - pyproject.toml (the 8 declared markers — `macos_audio`, `windows_only`, `integration`, `slow`, `parity`, `cli`, `e2e`, `network`; note `parity` is NOT in the opt-in grid per RESEARCH.md "Existing markers" table)
    - .planning/phases/67-all-tests-pass/67-RESEARCH.md `## Security Domain` (use `on: pull_request` NOT `pull_request_target` per fork-PR no-secret-leak posture)
  </read_first>
  <action>
    Create new file `.github/workflows/full-test-matrix.yml`. Top-level keys in order: `name: Full Test Matrix`; `on:` with `push.branches: [main]` and `pull_request:` (no `pull_request_target` per security posture); `concurrency` with `group: full-test-matrix-${{ github.ref }}` and `cancel-in-progress: true` (workflow-prefixed group per Pitfall 4); `permissions.contents: read` (minimal — no `write` scopes needed); single job `test` with `name: ${{ matrix.os }} · ${{ matrix.marker }}`, `runs-on: ${{ matrix.os }}`, `timeout-minutes: 30`, `strategy.fail-fast: false`, `strategy.matrix.os: [macos-13, macos-14, windows-latest]`, `strategy.matrix.marker: [default, macos_audio, windows_only, integration, slow, e2e, cli, network]`, and `strategy.matrix.exclude:` covering: `{os: windows-latest, marker: macos_audio}`, `{os: macos-13, marker: windows_only}`, `{os: macos-14, marker: windows_only}` (the 3 impossible OS×marker combinations per RESEARCH.md Pattern 2 — leave `default` on all 3 OSes per Open Question 1 recommendation). Steps: (1) `uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5 # v4.3.1`; (2) `uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065 # v5.6.0` with `python-version: '3.12'`; (3) `uses: astral-sh/setup-uv@caf0cab7a618c569241d31dcd442f54681755d39 # v3.2.4`; (4) `name: Install deps` → `run: uv sync --frozen --group dev`; (5) `name: Run tests (default)` with `if: matrix.marker == 'default'`, `env.GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}`, `run: uv run pytest -q --tb=short`; (6) `name: Run tests (opt-in marker — ${{ matrix.marker }})` with `if: matrix.marker != 'default'`, same env, `run: uv run pytest -q --tb=short -m "${{ matrix.marker }}"`. Verify YAML parses with `yq '.' .github/workflows/full-test-matrix.yml` (or `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/full-test-matrix.yml'))"` if yq unavailable). Verify the matrix shape: `yq '.jobs.test.strategy.matrix' .github/workflows/full-test-matrix.yml` should report `os`, `marker`, `exclude` keys. DO NOT push the workflow yet — that fires CI on hosted runners and the badge URL needs at least one run before going green (Pitfall 5 — workflow+badge ship in same plan but the badge will be gray for one push window after merge, which is fine).
  </action>
  <verify>
    <automated>test -f .github/workflows/full-test-matrix.yml && python3 -c "import yaml; d=yaml.safe_load(open('.github/workflows/full-test-matrix.yml')); print('OK' if d['on'].get('push',{}).get('branches')==['main'] and 'pull_request' in d['on'] and d['jobs']['test']['strategy']['fail-fast']==False else 'FAIL')" && grep -c '^      - uses: actions/checkout@[a-f0-9]\{40\} # v4' .github/workflows/full-test-matrix.yml</automated>
  </verify>
  <done>`.github/workflows/full-test-matrix.yml` exists, parses as valid YAML, has all required keys: `on.push.branches == [main]`, `on.pull_request` present, `concurrency.group == "full-test-matrix-${{ github.ref }}"`, `concurrency.cancel-in-progress == true`, `permissions.contents == "read"`, `jobs.test.strategy.fail-fast == false`, `jobs.test.strategy.matrix.os == [macos-13, macos-14, windows-latest]`, `jobs.test.strategy.matrix.marker == [default, macos_audio, windows_only, integration, slow, e2e, cli, network]`, exactly 3 `exclude` entries. All 3 `uses:` lines use SHA-pinned references with `# v...` comments (matches `dep-audit.yml` pinact-audit invariant). `timeout-minutes: 30` per Open Question 2. Mandatory implements: TEST-04 success criterion ("`.github/workflows/full-test-matrix.yml` exists, runs the full marker grid on macos-13 + macos-14 + windows-latest on every push to `main` and every PR" per D-TEST-04); TEST-02 secondary delivery (the CI matrix runs every opt-in marker individually so xfails surface as amber not red).</done>
</task>

<task type="auto">
  <name>Task 2: Add status badge to README badges row</name>
  <read_first>
    - README.md lines 1-60 (find the existing badges row — RESEARCH.md says around line 40-43; confirm exact location and existing badge format)
    - .planning/phases/67-all-tests-pass/67-RESEARCH.md (Code Examples — "TEST-04 — Add the badge to README badges row" gives the exact `<a><img></a>` HTML snippet)
    - .planning/phases/67-all-tests-pass/67-CONTEXT.md (`### Badge` — pinned in README badges row; note v7.0 P70 ships `tests/repo/test_github_presence.py` to catch drift, so for P67 we just add the line)
    - .planning/phases/67-all-tests-pass/67-RESEARCH.md Pitfall 5 — badge will show "no status" gray until the workflow has run on `main` at least once; document this in SUMMARY as expected
  </read_first>
  <action>
    Locate the existing badges row in `README.md` (RESEARCH.md says ~line 40-43). Read the surrounding context to confirm the exact format — the existing badges use `<a href="..."><img alt="..." src="https://img.shields.io/..." /></a>` per RESEARCH.md Code Examples. Append one new badge line at the END of the badges row (after the last existing badge, before the row's closing context — DO NOT insert in the middle, DO NOT reorder existing badges): `<a href="https://github.com/ozzaii/vibemix/actions/workflows/full-test-matrix.yml"><img alt="full test matrix" src="https://img.shields.io/github/actions/workflow/status/ozzaii/vibemix/full-test-matrix.yml?label=tests&branch=main&style=flat-square" /></a>`. CRITICAL: use the `ozzaii/vibemix` org/repo pair per `pyproject.toml` line 122-124 (`Homepage = "https://github.com/ozzaii/vibemix"`) — NOT `bravoh-ai/vibemix` (despite CONTEXT examples using the bravoh-ai org; the repo currently lives at `ozzaii/vibemix` per the pyproject source-of-truth; the transfer to `bravoh-ai/vibemix` is a v7.0 P69 OSS-04 §SHIP-10 deliverable that hasn't fired yet). The `?branch=main&style=flat-square` query params match the existing badge style per RESEARCH.md Code Examples. After insertion, verify the README still renders by running `grep -c "full-test-matrix.yml" README.md` returns ≥1 (badge link + img src = 2 hits, count must be ≥2). Verify by reading the surrounding badges row to confirm no badge was overwritten and the row remains visually coherent.
  </action>
  <verify>
    <automated>grep -c "full-test-matrix.yml" README.md && grep -c "img.shields.io/github/actions/workflow/status" README.md</automated>
  </verify>
  <done>README.md has the new badge line inserted at the end of the badges row. `grep "full-test-matrix.yml" README.md` returns ≥2 hits (anchor href + img src). The org name matches `pyproject.toml` `Homepage` (`ozzaii/vibemix` — not `bravoh-ai/vibemix` — until §SHIP-10 transfer fires). The badge uses `flat-square` style + `?branch=main` matching the existing badge format. Expected: badge will be gray ("no status") for one push window after merge until the workflow runs on `main`; documented in SUMMARY as known transient state per Pitfall 5. Mandatory implements: TEST-04 success criterion ("Green badge appears in the README badges row" per D-TEST-04).</done>
</task>

</tasks>

<verification>
  - `.github/workflows/full-test-matrix.yml` exists, parses as valid YAML, has the matrix + exclude grid per CONTEXT
  - All `uses:` lines are SHA-pinned (no `@v4`/`@main` floating refs) per `dep-audit.yml` pinact-audit invariant
  - README.md has exactly one new badge line referencing `full-test-matrix.yml`
  - `uv run pytest -q` still exits 0 (no test-time regression from the workflow YAML addition — YAML is data, not code, but verify the test suite isn't accidentally including the workflow file in pytest's collection)
  - `uv run pytest tests/repo/ -q` exits 0 (P03 static gates still green)
</verification>

<success_criteria>
- TEST-04 deliverables landed: workflow file + badge.
- TEST-02 secondary delivery: every opt-in marker runs in CI under its own job (per-marker isolation per CONTEXT D-CI), failures surface on PR check page not silently.
- Zero net-new dependencies. The workflow uses only the existing pinned action SHAs already in use by other workflows.
- Security posture per RESEARCH.md `## Security Domain`: `pull_request` trigger (not `pull_request_target`), SHA-pinned actions, no echo of secrets, no `pull_request_target` privilege escalation surface.
</success_criteria>

<output>
Create `.planning/phases/67-all-tests-pass/67P04-SUMMARY.md` with: full workflow YAML excerpt, the new badge HTML line, the README badges-row before/after, and a note about the expected gray-badge window until first push-to-main triggers a run.
</output>
