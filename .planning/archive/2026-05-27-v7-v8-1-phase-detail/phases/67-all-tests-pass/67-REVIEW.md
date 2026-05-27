---
phase: 67-all-tests-pass
reviewed: 2026-05-23T00:00:00Z
depth: standard
files_reviewed: 20
files_reviewed_list:
  - .github/workflows/full-test-matrix.yml
  - .gitignore
  - KAAN-ACTION-LEGAL.md
  - README.md
  - docs/flake-hunt.md
  - pyproject.toml
  - tests/coach/test_main_anti_slop_wiring.py
  - tests/repo/test_cut_release_invokes_bravoh_server.py
  - tests/repo/test_no_silent_flakes.py
  - tests/repo/test_no_silent_skips.py
  - tests/scripts/test_cut_release_preflight.py
  - tests/sidecar/test_wizard_entrypoint.py
  - tests/test_audio_macos_live.py
  - tests/test_audio_windows_live.py
  - tests/test_main_live.py
  - tests/test_main_smoke.py
  - tests/test_midi_macos_live.py
  - tests/test_midi_windows_live.py
  - tests/test_screen_windows_live.py
  - tests/test_track_windows_live.py
findings:
  critical: 0
  warning: 3
  info: 5
  total: 8
status: findings
---

# Phase 67: Code Review Report

**Reviewed:** 2026-05-23
**Depth:** standard
**Files Reviewed:** 20 (+ 6 zero-byte corpus stubs verified)
**Status:** findings (3 warnings, 5 info — no blockers)

## Summary

Phase 67 is a wiring + discharge + polish phase that adds zero `src/vibemix/`
source edits, zero net-new dependencies, and respects the autonomous-mode
hard rules (no `--no-verify`, no Apple/SignPath POSTs). All four cardinal
invariants hold:

1. **Zero `src/vibemix/` edits** — confirmed via `git diff b7c651a..HEAD -- src/vibemix/` (0 lines).
2. **Zero net-new deps** — `pyproject.toml` diff is one line (the `flaky` marker
   registration).
3. **No `--no-verify` / hook-skip in commit history** — `git log b7c651a..HEAD`
   commit messages contain zero matches for `no-verify`.
4. **Action SHA pins consistent with sibling workflows** — all three actions
   (`actions/checkout`, `actions/setup-python`, `astral-sh/setup-uv`) carry the
   same SHA hashes as the canonical pinned uses in `dep-audit.yml` / `eval.yml` /
   `release.yml`.

The 2 AST gates parse and run successfully end-to-end against the current
test tree (verified by direct module import + `test_no_silent_skips()` /
`test_no_silent_flakes()` invocation — both return without raising).

All 11 Tier-B `xfail(strict=False)` decorations carry both a `reason=` kwarg
**and** a `# reason:` comment within the 2-line window — the dual-channel
pattern documented in the gate. Each comment correctly references a
§V7-LIVE-NN cluster id matching an entry in `KAAN-ACTION-LEGAL.md`.

The §V7-LIVE section in `KAAN-ACTION-LEGAL.md` follows the established
§SHIP / §RECALL-EAR / §AUDIO shape (REQ-ID, Owner, Status, per-cluster
Tests/Why/Fix-path/Sign-off blocks, discharge-tracking table, sign-off
template).

Findings below are concentrated on the CI workflow surface and a small
number of static-gate edge cases. None block landing; the warnings are
fixable defensively in a follow-up commit.

## Warnings

### WR-01: `full-test-matrix.yml` interpolates matrix value into shell command — pattern fragility

**File:** `.github/workflows/full-test-matrix.yml:87`
**Issue:** The step `Run tests (opt-in marker — ${{ matrix.marker }})` uses
direct GitHub-expression interpolation into the `run:` shell:

```yaml
run: uv run pytest -q --tb=short -m "${{ matrix.marker }}"
```

This is **safe today** because the matrix values are statically declared in
the YAML (`default`, `macos_audio`, `windows_only`, `integration`, `slow`,
`e2e`, `cli`, `network`). If a future contributor moves the matrix list to
a workflow input (`workflow_dispatch.inputs.marker`) or reads it from
`repository_dispatch`, the same shape becomes a script-injection vector.
This is the documented GitHub anti-pattern: `${{ }}` interpolation into a
shell command is templated-before-shell-quoting, so a value containing
backticks or `$()` would execute.

**Fix:**
```yaml
- name: Run tests (opt-in marker — ${{ matrix.marker }})
  if: matrix.marker != 'default'
  env:
    GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
    MATRIX_MARKER: ${{ matrix.marker }}
  run: uv run pytest -q --tb=short -m "$MATRIX_MARKER"
```

Same defensive pattern recommended by GitHub Actions security docs
(<https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions#using-an-intermediate-environment-variable>).
The matrix-static defense is fine for v1; the env-var indirection is a
defense-in-depth for the day someone adds `workflow_dispatch` inputs.

---

### WR-02: README badge URL targets `bravoh-ai/vibemix` but repo lives at `ozzaii/vibemix`

**File:** `README.md:44`
**Issue:** The new full-test-matrix badge:

```html
<a href="https://github.com/bravoh-ai/vibemix/actions/workflows/full-test-matrix.yml">
  <img alt="full test matrix" src="https://img.shields.io/github/actions/workflow/status/bravoh-ai/vibemix/full-test-matrix.yml?label=tests&branch=main&style=flat-square" />
</a>
```

points at `bravoh-ai/vibemix`, but `pyproject.toml:122` and the §V7-LIVE-05
entry explicitly state the repo currently lives at `ozzaii/vibemix` and
will transfer to `bravoh/vibemix` (NOT `bravoh-ai/vibemix`) only when
§SHIP-10 / SHIP-TRANSFER fires.

The badge URL therefore resolves to a 404 / "no status" gray state right
now, and will continue to until the repo transfer. The other badges
(release, build, license, stars, uv-lock, cargo-deny, npm-audit, SBOM) on
lines 32-43 use the **same** `bravoh-ai/vibemix` slug, so this is
**consistent with the rest of the file** — but the inconsistency between
the badge URLs (`bravoh-ai`) and the project URL (`ozzaii`) plus the
declared transfer destination (`bravoh`) is a pre-existing landmine, not
introduced by this phase. The new badge inherits the same defect.

**Fix:** Defer (matches existing convention). Track the org-slug
unification under §SHIP-TRANSFER discharge — when the repo transfers,
every badge URL needs the same one-line sed pass. Add a tracker note
under §SHIP-TRANSFER pointing at README.md badges as the affected surface.

If a same-phase fix is desired, change `bravoh-ai` → `ozzaii` in
README.md line 44 (the new badge only) so it actually resolves to a real
workflow URL today; the other 7 badges' URL slugs stay on the
`bravoh-ai` placeholder per the file's existing convention. But that
creates inconsistency among badge URLs — preferable to keep all badges
on the same placeholder slug and discharge them together at transfer
time.

---

### WR-03: `test_smoke_08` regex accepts a non-awaited `asyncio.wait_for(cache.create()` form

**File:** `tests/test_main_smoke.py:770-773`
**Issue:** The widened assertion:

```python
assert (
    "await cache.create()" in src
    or "asyncio.wait_for(cache.create()" in src
), "cache.create not awaited (bare or wait_for-wrapped form)"
```

passes if `asyncio.wait_for(cache.create()` appears anywhere in the source
— **regardless of whether it's awaited**. A line like:

```python
_unused = asyncio.wait_for(cache.create(), timeout=4.0)   # missing await
```

would satisfy the assertion. `asyncio.wait_for(...)` returns a coroutine;
the coroutine is never started unless awaited or scheduled. A future
refactor that drops the leading `await` would silently regress the cache
boot-fail-fast guarantee, and this test would not catch it.

**Fix:**
```python
assert (
    "await cache.create()" in src
    or "await asyncio.wait_for(cache.create()" in src
), "cache.create not awaited (bare or wait_for-wrapped form must be awaited)"
```

The `await ` prefix needs to be inside the substring check on the
`asyncio.wait_for(...)` branch too. One character difference; closes the
regression hole.

## Info

### IN-01: `test_no_silent_flakes.py` documents behavior on module-level `pytestmark` but the gate's own docstring doesn't repeat the caveat

**File:** `tests/repo/test_no_silent_flakes.py:1-21`
**Issue:** The sibling `test_no_silent_skips.py:122-124` explicitly documents
that module-level `pytestmark = ...` assignments are NOT scanned (they're
`Assign` nodes, not decorators). `test_no_silent_flakes.py` doesn't repeat
the caveat. If a future contributor adds `pytestmark = pytest.mark.flaky`
at module level without an issue link, the gate silently passes.

This is the same documented limitation as the skip gate. Today the repo
has zero flaky module-level pytestmarks, so the vacuously-green claim
holds. But the gate's docstring should note the same caveat for parity.

**Fix:** Add a paragraph to the module docstring (line ~14):

```python
"""
...
NOTE: Like ``test_no_silent_skips.py``, this gate inspects decorator nodes
only — module-level ``pytestmark = pytest.mark.flaky`` assignments are
``Assign`` nodes, not decorators, and are deliberately NOT scanned. The
project today has zero module-level flaky pytestmarks; if that changes,
either add per-test ``@pytest.mark.flaky`` decoration (which the gate
catches) or extend the gate to also walk ``Assign`` targets.
"""
```

---

### IN-02: `secrets.GEMINI_API_KEY` env passed even when not needed

**File:** `.github/workflows/full-test-matrix.yml:80,86`
**Issue:** Both `Run tests (default)` and `Run tests (opt-in marker)` steps
pass `GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}` unconditionally. Most
matrix combinations (`default`, `windows_only`, `macos_audio`, `cli`,
`slow`, `integration`, `e2e`) don't actually need it — only the `network`
marker exercises live-net code with the real key.

On fork PRs the secret is empty string anyway (GitHub strips secrets from
PR runs from forks), so this isn't a leak path. But scoping the env to
only the markers that need it would tighten the surface.

**Fix:** Move the env block down a level so only the network marker run
receives the key:

```yaml
- name: Run tests (opt-in marker — ${{ matrix.marker }})
  if: matrix.marker != 'default'
  env:
    GEMINI_API_KEY: ${{ matrix.marker == 'network' && secrets.GEMINI_API_KEY || '' }}
  run: uv run pytest -q --tb=short -m "$MATRIX_MARKER"
```

Defer to a follow-up; not blocking.

---

### IN-03: `parity` marker is in `pyproject.toml` but absent from full-test-matrix.yml matrix

**File:** `.github/workflows/full-test-matrix.yml:47-55` vs
`pyproject.toml:204`
**Issue:** The `parity` marker (8 tests under `tests/library/test_store_parity.py`
+ `tests/memory/test_store_parity.py`) is registered in `pyproject.toml`
but not in the workflow's `marker:` list. These tests still run inside the
`default` matrix slot (no auto-deselect logic in conftest), so they ARE
exercised — but the `pytest -m parity` slice is not isolated.

Per the workflow's header comment ("Per-marker isolation: one job per
marker per OS — a failure must be attributable to the marker"), parity
should arguably be in the grid. It was likely omitted because parity tests
are platform-cross-cutting (they run on both Mac and Win and assert
bit-identity), so a per-OS marker slice is less meaningful than for
`macos_audio` / `windows_only`.

**Fix:** Either (a) add `parity` to the marker list with no excludes, or
(b) document the omission in the workflow header comment. Defer.

---

### IN-04: `test_main_live.py` body calls `pytest.skip(...)` inside an `xfail(strict=False)` test

**File:** `tests/test_main_live.py:32-43`
**Issue:** The test is decorated `@pytest.mark.xfail(strict=False)` AND its
body skips via `pytest.skip(...)` if `VIBEMIX_LIVE_SMOKE` env var is not
set. Under pytest semantics, an explicit `pytest.skip` inside an xfail
body resolves to **SKIPPED**, not XFAIL — the skip short-circuits before
xfail evaluation.

This is *correct* behavior for the test's purpose (Kaan-only opt-in via
env var), but it makes the §V7-LIVE-04 discharge slightly confusing: the
test never reports XFAIL/XPASS on a runner that doesn't have
`VIBEMIX_LIVE_SMOKE=1`, it reports SKIPPED. The cluster table at
KAAN-ACTION-LEGAL.md:3892 says "1 test" under §V7-LIVE-04, but on Kaan's
manual discharge run the test will report XPASS only when he sets the env
var; otherwise it'll be SKIPPED and not contribute to the cluster's green
state.

**Fix:** No code change required — this is documented behavior. Optionally
add a clarifying note to §V7-LIVE-04 (KAAN-ACTION-LEGAL.md:3771):

> Note: `test_live_startup_shutdown` reports SKIPPED (not XFAIL) when
> `VIBEMIX_LIVE_SMOKE` is unset. Kaan must export the env var for the
> discharge run; otherwise the test contributes a skip, not an xpass, to
> the cluster sign-off.

---

### IN-05: `tests/repo/test_no_silent_skips.py` would flag positional-arg `@pytest.mark.skip("reason")` as silent

**File:** `tests/repo/test_no_silent_skips.py:68-75`
**Issue:** `_has_reason_kwarg` checks `kw.arg == "reason"` — only `keyword`
arguments with the keyword name `reason`. Pytest also accepts the
positional form `@pytest.mark.skip("Some reason")` per its docs (the
reason is the first positional arg to the marker). The gate would flag
that as a silent skip and require a `# reason:` comment.

This is **arguably correct strict-mode behavior** — pytest's docs do
recommend `reason=` kwarg as best practice — but it's not what the gate's
docstring claims ("reason= kwarg OR # reason: comment"). The kwarg-only
check is stricter than the prose suggests.

**Fix:** Either (a) update the gate to also accept the first positional
arg if it's a `Constant` of type `str` (relaxes to match pytest's actual
contract), or (b) update the gate's docstring to reflect that only the
kwarg form counts (status quo). Today the repo has zero positional-form
skips (verified via `grep -rn "pytest.mark.skip(['\"]" tests/`), so this
is theoretical. Defer.

---

## Cross-cutting verification

The following were checked and pass:

| Check | Result |
|---|---|
| `git diff b7c651a..HEAD -- src/vibemix/` (no source edits) | 0 lines |
| `git log b7c651a..HEAD --format=%B | grep -i no-verify` | 0 hits |
| Action SHA pins consistent across workflows | 4× checkout, 4× setup-python, 4× setup-uv all same |
| `.gitignore` allowlist for `eval/corpus/sessions/*/events.jsonl` | line 122 — correct shape |
| 6 empty corpus stubs | all 0 bytes, all tracked |
| `pyproject.toml` net-new deps | 0 (only the `flaky` marker line added) |
| AST gate `test_no_silent_skips.py` runs end-to-end | PASSED |
| AST gate `test_no_silent_flakes.py` runs end-to-end | PASSED |
| All 11 Tier-B `xfail(strict=False)` carry `reason=` kwarg | YES |
| All 11 Tier-B `xfail(strict=False)` carry `# reason:` comment within 2 lines | YES |
| §V7-LIVE-01..06 entries follow §SHIP-V4 / §RECALL-EAR shape | YES |
| §V7-LIVE-06 carries v7.0 baseline sign-off (10/10 GREEN @ 23c4203) | YES |
| Workflow YAML parses cleanly (PyYAML safe_load) | YES |
| Concurrency group is workflow-prefixed (`full-test-matrix-${{ github.ref }}`) | YES |
| `pull_request` trigger (NOT `pull_request_target`) | confirmed line 29 |
| `permissions.contents: read` (minimum scope) | confirmed lines 35-36 |
| `timeout-minutes: 30` per job | confirmed line 42 |
| `fail-fast: false` (one cell failure doesn't kill the grid) | confirmed line 44 |
| `--frozen` in `uv sync` (lock-file-respect) | confirmed line 75 |

---

_Reviewed: 2026-05-23_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
