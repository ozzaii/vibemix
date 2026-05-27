---
phase: 67-all-tests-pass
plan: 67P01
subsystem: testing

tags: [pytest, markers, ci-prep, test-as-contract, drift-fix, flaky-marker, anti-slop-wiring, cut-release-gates, readme-feature-matrix]

# Dependency graph
requires:
  - phase: 66
    provides: v6.0 "The Memory Turn" engineering-green default grid
provides:
  - "Default `pytest -q` exits 0 on `main` HEAD (4160 passed, 26 skipped, 0 failed)"
  - "`flaky` pytest marker registered under --strict-markers (downstream Wave 2 unblock)"
  - "Audit-trail annotation for Phase 16 P85 override restored in STATE.md (annotate-not-delete compliance)"
  - "README feature-matrix block resynced (phases 55-66 added — covers v4.0 SHIP / v5.0 / v6.0 close)"
  - "eval/corpus/sessions/*/events.jsonl scaffold placeholders committed (corpus diversity gate green)"
  - "Tag-regex / milestone-audit / RC-shape test pins re-aligned to current public-OSS v0.1.0-rc shape (P83)"
  - "Anti-slop wiring + cache-construction test contracts updated to accept post-2026-05-21 product evolution (citation_lint_enabled decoupling + cache≡agent invariant + wait_for-wrapped cache.create)"
affects: [67-all-tests-pass-wave-1, 67-all-tests-pass-wave-2, 68-all-devices-ready, 69-oss-fully-integrated, 70-github-sexified]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Test-as-contract drift policy: when product code evolves legitimately (post-2026-05-21 decouplings, public-OSS tag-shape renumbering, milestone-audit filename bumps), update the test pin to match the new source-of-truth rather than reverting the product. The test's INTENT (linter conditionally constructed, RC tag-shape locked, milestone-audit gate trips on miss) is preserved by accepting both old + new shapes via `or` predicates."
    - "Scaffold placeholders for empty-but-required artifacts: docstring spec `may be empty pending labeling` => commit empty files + a per-path `!` allowlist in .gitignore so a fresh clone passes the existence gate (corpus diversity, P67 / Plan 67P01)."
    - "Audit-trail annotations live forever even after the underlying override / decision is retired (annotate-not-delete — Plan 42-05 spec carried forward)."

key-files:
  created:
    - "eval/corpus/sessions/hard_tek_01/events.jsonl (empty placeholder)"
    - "eval/corpus/sessions/hard_tek_02/events.jsonl (empty placeholder)"
    - "eval/corpus/sessions/house_01/events.jsonl (empty placeholder)"
    - "eval/corpus/sessions/house_02/events.jsonl (empty placeholder)"
    - "eval/corpus/sessions/techno_01/events.jsonl (empty placeholder)"
    - "eval/corpus/sessions/techno_02/events.jsonl (empty placeholder)"
    - ".planning/phases/67-all-tests-pass/67P01-SUMMARY.md (this file)"
  modified:
    - "pyproject.toml (flaky marker registered)"
    - "tests/coach/test_main_anti_slop_wiring.py (W13 regex accepts citation_lint_enabled)"
    - "tests/repo/test_cut_release_invokes_bravoh_server.py (tag regex pin v2.1 -> v0.1.0)"
    - "tests/scripts/test_cut_release_preflight.py (RC tag-shape + audit path bumped)"
    - "tests/test_main_smoke.py (smoke_08 accepts cache_system_instruction + wait_for)"
    - ".planning/STATE.md (Phase 16 audit annotation restored)"
    - "README.md (feature-matrix block resynced)"
    - ".gitignore (allowlist for eval/corpus/sessions/*/events.jsonl)"

key-decisions:
  - "Test-as-contract drift was the universal root cause for 8/9 failures — the v7.0 STATE.md/ROADMAP rewrite + the 2026-05-21 product fixes (citation-lint decoupling, cache≡agent invariant, cache.create timeout-wrapping) + the public-OSS tag renumbering (P83) + the milestone-audit filename bump (v2.1 -> v4.0) all evolved past test pins that hadn't moved with them. Updating the test pins is the legitimate fix — these tests exist to DETECT drift, and v7.0 milestone rewrites are exactly the legitimate drift class they watch for. No src/vibemix/ edits."
  - "The 1 non-drift failure (corpus diversity events.jsonl) was a pre-existing scaffold gap: the test's own docstring says `may be empty pending labeling`, but the empty files were never committed. Touch them + add a .gitignore allowlist; the corpus dir now passes a fresh-clone check."
  - "Audit-trail annotations are annotate-not-delete per Plan 42-05 spec. STATE.md rewrites for new milestones must carry forward audit annotations for retired overrides; the v7.0 rewrite dropped the Phase 16 P85 annotation, which a downstream test (`test_state_md_phase_16_line_is_annotated_retired`) is purpose-built to catch. Restored as a `## Historical Audit Annotations` section."

patterns-established:
  - "Pattern: shape-tolerant assertions via `or` predicates. When a product API has legitimately evolved (kwarg rename, conditional gate rename, expression wrapping), the test assertion accepts both the old and the new shape. The contract held is the SEMANTIC invariant (linter is conditionally constructed; cache is built with a system-instruction body; cache.create is awaited), not the syntactic exact-match."
  - "Pattern: corpus scaffold via per-path .gitignore allowlist. The existing `*.jsonl` global ignore stays in force (real session logs are user data, never committed). Specific test-fixture paths get `!path/...` overrides — already in use for tests/eval/fixtures/, tests/fixtures/, tests/scripts/fixtures/; extended to eval/corpus/sessions/*/events.jsonl for the corpus diversity gate."

requirements-completed: [TEST-01, TEST-03]

# Metrics
duration: 17min
completed: 2026-05-23
---

# Phase 67 Plan 67P01: All Tests Pass — Wave 0 (default-grid green + flaky marker registered) Summary

**Default `uv run pytest -q` flipped from 9-red to 0-red (4160 passed, 26 skipped) via 9 test-as-contract drift fixes (no src/vibemix/ edits) + a `flaky:` marker line in pyproject.toml that unblocks every downstream Phase 67 wave under `--strict-markers`.**

## Performance

- **Duration:** ~17 min (single task-fix-and-commit cycle after diagnosis)
- **Started:** 2026-05-23T08:45:44Z
- **Completed:** 2026-05-23T09:02:34Z
- **Tasks:** 2 (Task 1 = diagnosis-only no-commit; Task 2 = fix-all-9 + register marker single atomic commit)
- **Files modified:** 14 (8 mod + 6 new empty placeholders)
- **Test deltas:** 4151 passed -> 4160 passed (+9 newly green); 0 failed (was 9).

## Accomplishments

- **Default grid green end-to-end:** `uv run pytest -q` => exit code 0. The 9 default-grid failures the briefing listed are all closed; no new failures regressed in.
- **`flaky:` pytest marker registered:** pyproject.toml `[tool.pytest.ini_options].markers` now declares `"flaky: quarantined non-deterministic test; carries a # issue: https://... link enforced by tests/repo/test_no_silent_flakes.py"`. Wave 2's `tests/repo/test_no_silent_flakes.py` static gate is unblocked (no test can land a `@pytest.mark.flaky` decorator until the marker is declared, because `--strict-markers` is already in `addopts`).
- **Audit-trail annotation restored:** the v7.0 STATE.md rewrite dropped the Phase 16 ear-test memory override RETIRED annotation that Plan 42-05 explicitly spec'd as annotate-not-delete. Restored as a new `## Historical Audit Annotations` section with cross-ref to `.planning/decisions/P85-OVERRIDE-RETIRED.md`. Audit trail compliance held forward.
- **README feature-matrix resynced:** phases 55-66 (covering the v4.0 SHIP close + the entire v5.0 "Useful Cut" + v6.0 "Memory Turn") were missing from the auto-generated block; `scripts/launch/sync_feature_matrix.py --write` re-emitted all 16 phase rows.
- **Corpus diversity scaffold:** the 6 session dirs under `eval/corpus/sessions/` now each carry an empty `events.jsonl` placeholder (docstring spec: "may be empty pending labeling"); `.gitignore` got a per-path `!` override so the placeholders survive in tree while the global `*.jsonl` ignore (which protects user-recorded session logs under `recordings/`) stays in force.
- **Acid test held:** `git diff --stat src/vibemix/ a08594d^..a08594d` is empty. Zero reaction-path edits, zero new dependencies, zero new ws ports, zero new IPC envelopes — exactly per v7.0 acid test.

## Task Commits

1. **Task 1: Enumerate the 9 failures + diagnose each** — no commit (diagnosis-only, working notes carried into Task 2)
2. **Task 2: Fix all 9 failures + register `flaky` marker** — `a08594d` (test)

**Plan metadata:** _this commit_ (docs: complete plan + STATE/ROADMAP updates)

## Files Created/Modified

| File | Change |
| --- | --- |
| `pyproject.toml` | +1 line: `flaky:` marker declared |
| `tests/coach/test_main_anti_slop_wiring.py` | W13 regex accepts both `anti_slop_enabled` and `citation_lint_enabled` gates |
| `tests/repo/test_cut_release_invokes_bravoh_server.py` | TAG_REGEX pin updated v2.1.0 -> v0.1.0 + docstring comment refreshed |
| `tests/scripts/test_cut_release_preflight.py` | RC tag-shape (v2.1.0-rc1 -> v0.1.0-rc1) + audit path (v2.1-MILESTONE-AUDIT.md -> v4.0-MILESTONE-AUDIT.md) |
| `tests/test_main_smoke.py` | smoke_08 accepts `cache_system_instruction` OR `SYSTEM_INSTRUCTION` for cache body; accepts `asyncio.wait_for(cache.create()` OR bare `await cache.create()` |
| `.planning/STATE.md` | New `## Historical Audit Annotations` section with Phase 16 RETIRED annotation + cross-ref to P85-OVERRIDE-RETIRED.md |
| `README.md` | AUTO-GEN feature-matrix block resynced (16 phase rows; phases 55-66 added) |
| `.gitignore` | `!eval/corpus/sessions/*/events.jsonl` allowlist |
| `eval/corpus/sessions/{6 dirs}/events.jsonl` | Empty placeholder files (one per session dir) |

## Decisions Made

- **Test-as-contract drift is the legitimate fix class, not "regression."** 8 of 9 failures were tests pinned to constants that the product has legitimately moved past since the pin was written:
  - `CitationLinter()` gate moved from `anti_slop_enabled` to a separate `citation_lint_enabled` per 2026-05-21 (gemini-3.x rarely emits the [cite] grammar; muzzling the co-host on every uncited reply is the regression, not the decoupling)
  - Tag regex moved from `v2.1.0-rc` to `v0.1.0-rc` per P83 / Phase 56 (the public OSS RC shape; v4.0 stays the INTERNAL milestone)
  - Milestone audit filename moved from `v2.1-MILESTONE-AUDIT.md` to `v4.0-MILESTONE-AUDIT.md`
  - `system_instruction_body=SYSTEM_INSTRUCTION` (hardcoded constant) -> `system_instruction_body=cache_system_instruction` (resolved local) per 2026-05-21 cache≡agent invariant fix
  - `await cache.create()` (bare) -> `await asyncio.wait_for(cache.create(), timeout=4.0)` per 2026-05-21 hard-timeout fix against indefinite hangs on free-tier keys

  Each test had a clearly-stated invariant intent in its docstring; the fix preserves the invariant + accepts both old and new shapes via `or` predicates. No product surface lost.

- **Scaffold placeholders > test changes for the corpus events.jsonl miss.** The test's own docstring says "may be empty pending labeling" — the test was correct to require existence; the previous skeleton just never committed the empty files. Touch + .gitignore allowlist is the docstring-faithful fix.

- **Audit annotation restored in STATE.md, not retired test.** The audit annotation lives there for compliance — Plan 42-05's spec said "annotate-not-delete." The v7.0 rewrite dropping it was the regression; the test catching it is doing its job. New section heading `## Historical Audit Annotations` keeps the annotation discoverable to future audits without cluttering the current-state surface.

## Deviations from Plan

The plan listed 8 failures (per RESEARCH.md frozen at 2026-05-23 planning time); the actual current-HEAD count was 9 — drift inside the planning-to-execution gap. RESEARCH.md's tolerance for ±2 drift covered it, and the extra failure (`test_each_session_has_events_jsonl_file`) was diagnosed in Task 1 + fixed in Task 2 alongside the other 8 with no plan-spec deviation. No Rule 4 architectural decisions; no KAAN-ACTION discharges; no `xfail` decorators needed (no failure turned out to be a real product regression — all 9 were test-as-contract drift or scaffold gaps).

**Total deviations:** 0 — plan executed as written (with the ±2 drift tolerance the plan explicitly carried).

## Issues Encountered

- **smoke_08 had a second hidden drift line:** after fixing the `system_instruction_body=` assertion to accept `cache_system_instruction`, the next line (`assert "await cache.create()" in src`) still tripped because the 2026-05-21 timeout-wrapping changed the expression to `await asyncio.wait_for(cache.create(), timeout=4.0)`. Fixed with the same `or` predicate pattern. Caught by re-running the targeted test before running the full suite.
- **events.jsonl was gitignored by the global `*.jsonl` rule.** First commit attempt would have produced an empty diff for the corpus path; the .gitignore allowlist entry (`!eval/corpus/sessions/*/events.jsonl`) is required to actually track the placeholders. Followed the existing precedent pattern (`!tests/scripts/fixtures/synthetic_session/events.jsonl`, `!tests/eval/fixtures/synthetic_session/events.jsonl`, `!tests/fixtures/hype_trace_genre1.jsonl`).

## Threat Flags

None. This plan modifies only test files + scaffold placeholders + .gitignore + README + STATE.md + pyproject markers. No new network endpoints, no auth paths, no file access patterns at trust boundaries, no schema changes. The single touched product-adjacent file is pyproject.toml's marker declaration — no security surface.

## Known Stubs

None introduced by this plan.

The 6 `events.jsonl` placeholders are intentional empty scaffolds — the test docstring explicitly says "may be empty pending labeling" and they're slotted for KAAN-ACTION-item-4 corpus acquisition. The manifest.json `_note` field already documents them as pending population.

## User Setup Required

None. All changes land in the existing repo + pyproject toolchain — no env vars, no dashboards, no external service config.

## Next Phase Readiness

Wave 0 of Phase 67 closes Wave 1's prerequisites:
- **TEST-01 SC#1** ("a third-party engineer cloning `main` and running `pytest -q` sees exit code 0") => SATISFIED (4160/0/26 = green).
- **TEST-03 prerequisite** (`flaky` marker declared under --strict-markers) => SATISFIED (line 209 of pyproject.toml).

Open follow-ups for Phase 67 downstream waves:
- Wave 1: marker-grid green per individual opt-in marker (`macos_audio`, `windows_only`, `integration`, `slow`, `e2e`, `cli`, `network` — each one collected and either green or `xfail(strict=False)`+`# reason:` -> §V7-LIVE).
- Wave 2: `.github/workflows/full-test-matrix.yml` + `tests/repo/test_no_silent_flakes.py` static gate (consumes the `flaky:` marker registration this plan landed).
- Wave 3: flake-hunt 10× consecutive `pytest -q` runs at 100% pass.
- Wave 4: README badges row gets the green badge for `full-test-matrix.yml`.

No new blockers surfaced. The acid test holds: every fix in this plan turns an existing engineering-green capability into something a stranger cloning main can verify (default `pytest -q` exits 0) — nothing grew the product surface.

## Self-Check: PASSED

Verified before STATE/ROADMAP writes:
- `eval/corpus/sessions/hard_tek_01/events.jsonl` => FOUND (size 0, in tree)
- `eval/corpus/sessions/hard_tek_02/events.jsonl` => FOUND
- `eval/corpus/sessions/house_01/events.jsonl` => FOUND
- `eval/corpus/sessions/house_02/events.jsonl` => FOUND
- `eval/corpus/sessions/techno_01/events.jsonl` => FOUND
- `eval/corpus/sessions/techno_02/events.jsonl` => FOUND
- `.planning/phases/67-all-tests-pass/67P01-SUMMARY.md` => FOUND (this file)
- Task 2 commit `a08594d` => FOUND in `git log --oneline`
- `grep -c '"flaky:' pyproject.toml` => 1
- `uv run pytest -q` => 4160 passed, 26 skipped, 0 failed (exit 0)
- `git diff --stat src/vibemix/ a08594d^..a08594d | wc -l` => 0

---
*Phase: 67-all-tests-pass*
*Plan: 67P01*
*Completed: 2026-05-23*
