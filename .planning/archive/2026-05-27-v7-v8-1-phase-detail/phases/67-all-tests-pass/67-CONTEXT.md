# Phase 67: All Tests Pass - Context

**Gathered:** 2026-05-23
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase, autonomous mode — `gsd-autonomous fully`)

<domain>
## Phase Boundary

Turn the existing test suite into a stranger-installable, CI-proven contract:

- Every collected test green across the full marker grid (default + each opt-in marker individually) on Mac + Windows.
- `.github/workflows/full-test-matrix.yml` runs the entire grid on `macos-13` + `macos-14` + `windows-latest` for every push to `main` and every PR.
- Flake-hunt: 10× consecutive `pytest -q` re-runs at 100% pass rate, OR non-deterministic tests quarantined behind `@pytest.mark.flaky` + linked GitHub issue (enforced by `tests/repo/test_no_silent_flakes.py`).
- Every existing `skip`/`xfail`/`xpass` carries `# reason:` OR is converted to a `KAAN-ACTION-LEGAL.md §V7-LIVE` external-clock item.
- README badges row gets a green badge for the new workflow.
- Zero net-new product capability. Zero net-new dependencies. No phase modifies the reaction path.

**Out of scope:** Anything not directly serving the four cardinal invariants of testing (everything-collects, everything-green, no-graveyards, CI-proves-it). No new product features. No reaction-path changes.

</domain>

<decisions>
## Implementation Decisions

### Marker Grid Coverage
- Run default + each opt-in marker (`macos_audio`, `windows_only`, `integration`, `slow`, `e2e`, `cli`, `network`) individually.
- Per-marker job in CI so failures are isolated to the marker, not lost in a combined run.
- Use `pytest -m "<marker>"` per job; do NOT collapse markers into one big `or` filter (per-marker isolation is the point).

### Failure-Mode Triage (the 65 currently-deselected opt-in tests)
- **Tier A** — passes on real hardware → CI-green and we're done.
- **Tier B** — fails on CI but explainable (real hardware required, e.g. FLX4 USB, BlackHole) → document failure mode in `KAAN-ACTION-LEGAL.md §V7-LIVE` with a concrete fix path; mark `xfail(strict=False)` with `# reason:` adjacent. NOT skip-without-reason.
- **Tier C** — flaky/non-deterministic → `@pytest.mark.flaky(reruns=N)` + linked GitHub issue, enforced by `tests/repo/test_no_silent_flakes.py`.
- **Default to Tier B over Tier C.** Trust the audio (and the real hardware) more than retries.

### CI Workflow Shape
- `.github/workflows/full-test-matrix.yml` — separate workflow from any existing test workflow (don't conflate "fast PR feedback" with "full marker grid").
- Triggers: every push to `main`, every PR. NOT scheduled cron (no value here yet).
- Matrix: `[macos-13, macos-14, windows-latest] × [default, macos_audio, windows_only, integration, slow, e2e, cli, network]` — runner OS filters incompatible markers (e.g. `windows-latest` skips `macos_audio`).
- Concurrency group cancels in-flight runs on same PR (saves CI minutes).
- Green badge URL pinned in README badges row.

### Flake Quarantine Gate
- `tests/repo/test_no_silent_flakes.py` — static AST scan for `@pytest.mark.flaky` decorators; FAIL the build if any decorator lacks a `# issue: https://github.com/.../issues/N` comment within 3 lines.
- Verified by a scratch PR adding a no-link flaky decorator → CI must go red.

### Reason Tagging
- Every `skip`/`xfail`/`xpass` gets a `# reason: <one-liner>` comment within 2 lines above or on the decorator line.
- Static gate at `tests/repo/test_no_silent_skips.py` (if not already present — extend if so) enforces this.

### Badge
- Add a `[![Full Test Matrix](https://github.com/bravoh-ai/vibemix/actions/workflows/full-test-matrix.yml/badge.svg)](...)` line to the README badges row.
- README repo-presence test (`test_github_presence.py` lands in P70 — for P67 we just add the badge; P70's suite catches drift).

### Claude's Discretion
- Number of parallel CI jobs (matrix expansion) — pick whatever's cheapest while preserving per-marker isolation.
- Reruns count for `@pytest.mark.flaky` — pick a sensible default (3) if used; quarantine + issue is preferred over high rerun counts.
- Exact text of `# reason:` comments — write tightly, no padding.
- Whether to use `pytest-rerunfailures` for `flaky` (already a marker option) — yes if it cleanly integrates; otherwise plain `@pytest.mark.flaky` custom marker.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `pyproject.toml` `[tool.pytest.ini_options]` already declares the marker set (`macos_audio`, `windows_only`, `integration`, `slow`, `e2e`, `cli`, `network`) — extend with `flaky` if not present.
- `tests/repo/test_repo_scrub.py::test_retired_poc_files_stay_gone` — pattern for repo-presence tests; the new `test_no_silent_flakes.py` follows the same shape.
- Existing GitHub Actions workflows under `.github/workflows/` — reuse setup steps (uv install, Python 3.12, deps caching).

### Established Patterns
- `uv` is the runner; `uv run pytest -q` is canonical.
- `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q` for non-uv contexts.
- Tests live in `tests/` with markers from `pyproject.toml`.
- No formatter config — discipline-enforced, not tool-enforced.

### Integration Points
- `.github/workflows/full-test-matrix.yml` — new file.
- `tests/repo/test_no_silent_flakes.py` — new static gate.
- `README.md` badges row — add one line.
- `KAAN-ACTION-LEGAL.md §V7-LIVE` — new section (or extend existing) for Tier-B documented failures.
- `pyproject.toml` `[tool.pytest.ini_options]` — add `flaky` marker if missing.

</code_context>

<specifics>
## Specific Ideas

- The 65-deselected-tests number from REQUIREMENTS.md is the current snapshot; the actual triaged count is whatever `pytest --collect-only -q -m "macos_audio or windows_only or integration or slow or e2e or cli or network"` reports at planning time.
- `os: macos-13` covers Intel Mac; `macos-14` covers Apple Silicon. Both are needed because the audio backend (CoreAudio) and `nowplaying-cli` behave subtly differently.
- Windows-VM testing on Kaan's side uses Parallels or UTM (whichever he has); CI uses `windows-latest`. Real-hardware FLX4 testing on Win VM is out-of-scope for P67 (lands in P68 via §V7-LIVE).

</specifics>

<deferred>
## Deferred Ideas

- Coverage reporting — not required for P67; could be a future polish.
- Test-time profiling / slow-test alerts — not in scope.
- Mutation testing — not in scope.
- Scheduled cron runs — explicitly rejected (no value yet).

</deferred>
