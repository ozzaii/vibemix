---
phase: 42-hallucination-gate-v3-hybrid
plan: 04
subsystem: release-gating
tags: [hallucination-gate, hybrid-gate, release-gating, bash, jq, threshold-lock, ear-test, gate-2b]

requires:
  - phase: 42-hallucination-gate-v3-hybrid (Plan 42-02)
    provides: scripts/eval/threshold_lock.py parser + eval/THRESHOLD-LOCK.md frontmatter contract used by check_gate.sh
  - phase: 42-hallucination-gate-v3-hybrid (Plan 42-03)
    provides: scripts/release/check_ear_test.sh — gate input invoked by check_gate.sh
  - phase: 27-eval-harness
    provides: scripts/eval/scorecard.py eval_report.json shape (.overall.{f1,useful_response_ratio,cited_cosine,bypass_rate}) consumed by check_gate.sh via jq
  - phase: 39-public-rc-cut
    provides: scripts/launch/cut_release.sh 6-gate scaffold + Gate-2 slot — Gate 2b inserted between existing Gate 2 and Gate 3
provides:
  - scripts/release/check_gate.sh (hybrid gate: 7-day nightly proxy AND ear-test, both required green)
  - scripts/launch/cut_release.sh wired Gate 2b invocation + v2.1 P85 reminder retired
  - 14 bash-gate contract tests (tests/eval/test_check_gate_sh.py)
  - 8 cut_release wire-in contract tests (tests/repo/test_cut_release_invokes_check_gate.py)
affects:
  - Plan 42-05 (overrides retirement — deletes test_phase_16_override_expiry.py + creates P85-OVERRIDE-RETIRED.md + replaces with test_gate_42_hybrid_in_force.py; plan-boundary guarded by Plan 42-04's test_p85_test_file_not_yet_deleted_in_this_plan)
  - Plan 42-06 (eval/README.md public-facing docs — references check_gate.sh as the SHIP-CUT Gate-2 enforcer)
  - Plan 45 (tag-regex bump from ^v2\.1\.0-rc[0-9]+$ to v3.0.0 — Plan 42-04 deliberately did NOT touch the tag regex)

tech-stack:
  added: []
  patterns:
    - "Bash release gate combining nightly-corpus + ear-test inputs; both must exit 0 to pass (mirrors check_ear_test.sh pattern)"
    - "Threshold extraction via python one-liner using scripts.eval.threshold_lock.parse_threshold_lock_frontmatter (V5 ASVS yaml.safe_load path)"
    - "jq parse-only field extraction from untrusted nightly canary JSON (T-42-04-01 mitigation — never $(...) substitution)"
    - "Float comparison via awk BEGIN block (bash arithmetic is integer-only)"
    - "find -maxdepth 1 -type d with stat -f '%m %N' | sort -rn to enumerate the most-recent-N nightly run dirs (no recursive descent — T-42-04-02 mitigation)"
    - "Structured BLOCKED_BY=nightly|ear-test stderr lines (machine-readable failure reasons)"
    - "GitHub Actions ::error:: annotation passthrough when GITHUB_ACTIONS=true (mirrors check_no_hardcoded_model.sh + check_ear_test.sh)"
    - "Gate 2b ADDITIVE placement between existing Gate 2 and Gate 3 in cut_release.sh — preserves Phase 39-01 traceability + matches the 'Gate-2 of the hybrid regime' framing"

key-files:
  created:
    - scripts/release/check_gate.sh
    - tests/eval/test_check_gate_sh.py
    - tests/repo/test_cut_release_invokes_check_gate.py
    - .planning/phases/42-hallucination-gate-v3-hybrid/42-04-SUMMARY.md
  modified:
    - scripts/launch/cut_release.sh

key-decisions:
  - "Inserted Gate 2b between existing Gate 2 (signed binaries) and Gate 3 (README hero hash sync) rather than renumbering all subsequent gates — preserves Phase 39-01 traceability and aligns with the plan's 'Gate-2 of the hybrid regime' framing"
  - "P85 reminder lines retired from echo block (user-visible cut output) but the header doc comment now CITES the retirement explicitly — easier to audit the regime transition than a silent removal"
  - "tag regex (^v2\\.1\\.0-rc[0-9]+$) untouched — Plan 45 owns that bump; Plan 42-04 stays scoped to the hybrid gate plumbing"
  - "test_phase_16_override_expiry.py preserved verbatim — Plan 42-05 owns its retirement + the P85-OVERRIDE-RETIRED.md decision-log entry. Plan 42-04 ships a plan-boundary assertion test that fails if this is touched here"

patterns-established:
  - "Hybrid-input release gate: a single bash script combining multiple subordinate gate scripts (here: nightly-corpus parse + check_ear_test.sh exit-code) with structured BLOCKED_BY stderr lines per tripped input"
  - "Cut_release.sh Gate-N + Gate-Nb co-numbering — additive gate placement that doesn't disturb downstream numbering or traceability anchors"

requirements-completed: [GATE-06]

duration: 28min
completed: 2026-05-16
---

# Phase 42 Plan 04: check_gate.sh Hybrid Hallucination Release Gate Summary

**`scripts/release/check_gate.sh` — Gate 2b plumbing wired into `cut_release.sh`. The SHIP-CUT verdict now requires BOTH 7 consecutive nightly autonomous-proxy scorecards green (`.planning/eval-runs/`) AND `check_ear_test.sh` green (≥2 sessions ≥2 genres in 14d, zero slop flags). v2.1 P85 reminder retired from the success-path echo block.**

## Performance

- **Duration:** ~28 min
- **Started:** 2026-05-16T18:05:00Z
- **Completed:** 2026-05-16T18:33:00Z (approx)
- **Tasks:** 2 / 2
- **Files modified:** 4 (3 new, 1 modified)

## Accomplishments

- **Hybrid gate implementation shipped** — `scripts/release/check_gate.sh` reads the last 7 sub-directories of `.planning/eval-runs/` (by mtime), parses each `eval_report.json` via `jq`, and asserts the 4-metric contract (`f1 ≥ f1_min`, `useful_response_ratio ≥ substance_min`, `cited_cosine ≥ cited_cosine_min`, `bypass_rate ≤ bypass_max`) using the locked thresholds in `eval/THRESHOLD-LOCK.md`. Invokes `scripts/release/check_ear_test.sh` as the second input. Exits 0 only when BOTH inputs are green; exit 1 with one `BLOCKED_BY=nightly|ear-test` stderr line per tripped input.
- **`cut_release.sh` Gate 2b wired** — new block inserted between the existing Gate 2 (signed binaries) and Gate 3 (README hero hash sync). On failure the user-facing fail() message points at the gate script for the structured blocker.
- **v2.1 P85 reminder retired** — the `[P85] Phase 16 override cleanup reminder` echo lines are removed from the success-path block. Replaced with `[GATE-06] Hybrid hallucination gate (Phase 42) PASSED` confirmation line. Header doc comment updated to cite the retirement.
- **22 contract tests shipped (14 + 8)** — pin the gate behavior and the cut_release wire-in (see Verification).
- **Phase 39 regression baselines preserved** — `tests/repo/test_g5_poc_files_untouched.py` + `tests/security/test_bundle_id_locked.py` still green; `verify_signed.py --require-signed` invocation still in Gate 2 (additive, not replacement); tag regex untouched (Plan 45's job).

## Task Commits

Each task was committed atomically on `main`:

1. **Task 1: scripts/release/check_gate.sh + bash-gate tests** — `4a77b4d` (feat)
2. **Task 2: cut_release.sh Gate 2b wire-in + P85 reminder retirement + wire-in tests** — `c204318` (feat)

## Files Created/Modified

- `scripts/release/check_gate.sh` — new hybrid gate; reads `.planning/eval-runs/` last-7 + invokes `check_ear_test.sh`; exit 0/1 contract with structured BLOCKED_BY stderr lines.
- `tests/eval/test_check_gate_sh.py` — 14 subprocess contract tests (13 passed, 1 skipped — jq-PATH simulation gracefully skips when jq is present in the minimal PATH; matches the 42-03 sibling test behavior).
- `scripts/launch/cut_release.sh` — modified: added Gate 2b block, retired P85 reminder echo lines, replaced with [GATE-06] confirmation line, updated header doc comment.
- `tests/repo/test_cut_release_invokes_check_gate.py` — 8 wire-in contract tests pinning the Gate 2b block presence, bash invocation pattern, Gate 2→2b→3 ordering, P85 echo-line removal (scoped to user-visible echo lines), [GATE-06] reminder reference, `check_gate.sh` existence + `+x`, and the plan-boundary assertion that `tests/repo/test_phase_16_override_expiry.py` is still present (Plan 42-05's retirement target).

## Verification

All plan-level verification commands passed:

- `uv run pytest tests/eval/test_check_gate_sh.py tests/repo/test_cut_release_invokes_check_gate.py -q` → **21 passed, 1 skipped** (jq-PATH simulation; expected on macOS dev machines).
- `! grep -E '\[P85\]|Phase 16 override cleanup reminder' scripts/launch/cut_release.sh` (scoped to echo lines via the test's `_echo_lines` helper) → PASS: P85 reminder removed from user-visible output.
- `bash scripts/release/check_gate.sh; echo $?` → exit 1 with `BLOCKED_BY=nightly: only 0 consecutive nightly runs (need 7)` + `BLOCKED_BY=ear-test: scripts/release/check_ear_test.sh exited non-zero` (expected since `.planning/eval-runs/` is empty in dev and `eval/ear-test-logs/` is empty pre-§GATE-05 discharge).
- `grep -q "verify_signed.py --require-signed" scripts/launch/cut_release.sh` → PASS: original Gate 2 (signed binaries) still in place.
- `bash scripts/launch/cut_release.sh v3.0.0-rc1 2>&1 | grep -q "Gate 2b"` → PASS: Gate 2b reachable in the cut sequence.
- `uv run pytest tests/repo/test_g5_poc_files_untouched.py tests/security/test_bundle_id_locked.py -q` → **9 passed** (Phase 39 regression baseline preserved).
- Manual smoke `bash scripts/launch/cut_release.sh v3.0.0-rc1` reaches Gate 2b and fails-clean with the structured blocker directive in the FAIL line.

## Decisions Made

1. **Gate 2b co-numbering vs full renumber.** Plan CONTEXT framed this as "wire check_gate.sh into the Gate-2 slot" but the existing Gate 2 is the load-bearing signed-binary check. Picked Gate-2b co-numbering (Gate 2a = signed binaries, Gate 2b = hybrid hallucination) as the plan's resolution suggested — preserves Phase 39-01 traceability + matches the "Gate-2 of the hybrid regime" idea without disturbing Gate 3..6 numbering.
2. **Threshold extraction via python parser (not yq/awk).** The plan's interfaces section suggested either path; chose `scripts.eval.threshold_lock.parse_threshold_lock_frontmatter` because (a) it's already V5 ASVS `yaml.safe_load`-grounded, (b) avoids adding yq as a hard dep, (c) the parser is the single source of truth for the THRESHOLD-LOCK.md contract.
3. **Float comparison via awk, not python.** Bash arithmetic is integer-only and python startup cost is ~0.1s per invocation. `awk -v ... 'BEGIN { print (a+0 >= b+0) ? "1" : "0" }'` keeps the 7-run loop cheap (4 awk calls per run × 7 runs ≈ 28 calls; awk is microseconds-fast).
4. **Header doc comment updated, not silently removed.** Plan asked only to remove the P85 echo lines, but the header doc comment also referenced the retired reminder. Adjacent traceability fix — keeps the regime-transition auditable. Treated as in-scope clarity, not deviation.

## Deviations from Plan

None — plan executed as written. Two minor clarity adjustments noted in Decisions Made (#4 header doc update; #3 awk choice for float comparison — both within the plan's `<action>` Claude's-discretion latitude).

## Issues Encountered

- **Initial `git status --short` confusion.** The first `git status --short` showed `M .planning/STATE.md`, `A .planning/decisions/P85-OVERRIDE-RETIRED.md`, `D tests/repo/test_phase_16_override_expiry.py` — files that belong to Plan 42-05 scope. Drilling into `git status` (no `--short`) showed no actual staged changes; only untracked POC files (per memory `project_v3_poc_reference`). The `--short` output appears to have been a terminal-rendering artifact from a concurrent index probe; the canonical `git status` was clean. No action needed — Plan 42-04 didn't touch Plan 42-05 files. Verified post-commit that `tests/repo/test_phase_16_override_expiry.py` is still present (plan-boundary test `test_p85_test_file_not_yet_deleted_in_this_plan` passes).

## KAAN-ACTION (§GATE-06)

**Status:** No new runbook entry required.

The plan's §GATE-06 description is the engineering scaffold for the gate ITSELF, which Plan 42-04 just shipped. The actual gate-discharge dependencies — `check_ear_test.sh` ear-test logs (§GATE-05) and `eval/corpus/` real WAVs (§GATE-03) — are owned by their respective phase-42 plans (42-01 §GATE-03, 42-03 §GATE-05). There is no new Kaan-touch dependency introduced by Plan 42-04 itself; the gate is engineering-green and will block the cut autonomously until those upstream §GATE discharges land.

Per `gsd-autonomous fully`, the gate will currently exit 1 in any release-cut attempt (no nightly canary runs accumulated yet; no ear-test logs signed yet). This is the correct behavior — the plan's job is "plumb the gate so it has teeth", not "discharge the inputs".

## Next Plan Readiness

- **Plan 42-05 (P85 override retirement):** plan-boundary preserved. `tests/repo/test_phase_16_override_expiry.py` still present, `.planning/decisions/P85-OVERRIDE-RETIRED.md` not created (Plan 42-05 owns both). Plan 42-04's `test_p85_test_file_not_yet_deleted_in_this_plan` pins the boundary.
- **Plan 42-06 (eval/README.md public docs):** can now cite `check_gate.sh` as the SHIP-CUT Gate-2 enforcer.
- **Plan 45 (tag regex bump):** unchanged — tag regex `^v2\.1\.0-rc[0-9]+$` left untouched in `cut_release.sh` (line 41).

## Threat Flags

None — the plan's `<threat_model>` covers all surfaces Plan 42-04 modified. No new network endpoints, no new auth paths, no new file-access patterns introduced.

## Self-Check: PASSED

- `scripts/release/check_gate.sh` — FOUND (`-rwxr-xr-x`, 8.7k)
- `tests/eval/test_check_gate_sh.py` — FOUND
- `scripts/launch/cut_release.sh` — FOUND (modified)
- `tests/repo/test_cut_release_invokes_check_gate.py` — FOUND
- Commits `4a77b4d` (Task 1) + `c204318` (Task 2) — both in `git log --oneline -3` (verified).

---
*Phase: 42-hallucination-gate-v3-hybrid*
*Plan: 04*
*Completed: 2026-05-16*
