---
phase: 58-ship-readiness
plan: 01
subsystem: infra
tags: [release, pyinstaller, tauri, dmg, integration-audit, gate, sidecar, codesign]

# Dependency graph
requires:
  - phase: 11-packaging
    provides: scripts/build_sidecar.py (PyInstaller onedir + AIza-leak scan + triple staging)
  - phase: 37-integration-audit
    provides: scripts/integration_audit.py (--write-milestone-audit generator + 5-seam evaluator)
  - phase: 34-signing
    provides: scripts/dist/verify_signed.py (Gate 2 checksum-only / --require-signed)
provides:
  - Rebuilt + AIza-clean vibemix-core sidecar staged for both apple-darwin triples
  - An unsigned local macOS .dmg in dist/ for Gate 2's verify_signed.py to inspect (dry-run path)
  - .planning/v4.0-MILESTONE-AUDIT.md (generator-produced, overall_verdict WIRED, Gate 4 input)
  - tests/repo/test_v4_milestone_audit_present.py (pins audit exists + WIRED + generator marker)
  - integration_audit.py seam-runner PYTHONPATH fix + milestone-from-filename derivation
affects: [58-02, 58-03, 58-04, cut_release.sh Gate 2, cut_release.sh Gate 4, REL-01]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Milestone audit identity derived from output filename (not hardcoded), backward-compatible default"
    - "Seam-test subprocess propagates PYTHONPATH=src so generator runs honest under either interpreter"

key-files:
  created:
    - .planning/v4.0-MILESTONE-AUDIT.md
    - tests/repo/test_v4_milestone_audit_present.py
    - dist/vibemix_0.1.0-rc1_aarch64-unsigned.dmg (gitignored build artifact, for Gate 2)
  modified:
    - scripts/integration_audit.py

key-decisions:
  - "cargo tauri build auto-attempts notarization (Francesco Developer ID in tauri.conf.json5); blocked HTTP 403 (Apple Dev Agreement EXTERNAL) — used the pre-notarize unsigned .dmg as the Gate 2 inspect artifact, did NOT force/disable signing"
  - "Generated v4.0 audit read MISSING under system python3.14 (wrong google-genai); fixed the generator subprocess + ran under the venv 3.12 → all 5 seams WIRED. Never hand-edited the verdict."
  - "Fixed integration_audit.py seam-runner to derive milestone identity (v4.0/SHIP) from the output filename instead of emitting a stale v2.1 label"

patterns-established:
  - "Don't-Hand-Roll honored: the audit verdict is generator-truth; a false-MISSING was a tooling bug, fixed at the tool, not papered over in the file"

requirements-completed: [REL-01]

# Metrics
duration: 9min
completed: 2026-05-21
---

# Phase 58 Plan 01: Real Release Artifacts (sidecar + unsigned .dmg + v4.0 audit) Summary

**Rebuilt the AIza-clean vibemix-core sidecar for both apple-darwin triples, produced an unsigned macOS `.dmg` for Gate 2 to inspect (notarization blocked on the EXTERNAL Apple agreement — documented, not forced), and GENERATED `.planning/v4.0-MILESTONE-AUDIT.md` reading `overall_verdict: WIRED` after fixing a generator bug that was reporting false-MISSING seams.**

## Performance

- **Duration:** 9 min
- **Started:** 2026-05-21T08:40:09Z
- **Completed:** 2026-05-21T08:49:15Z
- **Tasks:** 2
- **Files modified:** 3 committed (+ gitignored build artifacts)

## Accomplishments
- Sidecar rebuilt via `build_sidecar.py`: exit 0, AIza-leak scan clean (508 files, zero `AIza` matches). Both triples staged + executable (`vibemix-core-aarch64-apple-darwin` rebuilt today; `vibemix-core-x86_64-apple-darwin` staged from May 18 — `build_sidecar.py` builds only the host triple, the Intel one stays valid).
- Unsigned macOS `.dmg` in `dist/` (`vibemix_0.1.0-rc1_aarch64-unsigned.dmg`, 254 MB, valid UDIF image, sha256 `785acf6de8cb0757…`); `verify_signed.py --artifact` (checksum-only, the dry-run path) exits 0 on it.
- `.planning/v4.0-MILESTONE-AUDIT.md` GENERATED (never hand-written), 5/5 seams WIRED, `overall_verdict: WIRED`, carries the `**Generated:** by … --write-milestone-audit` marker — Gate 4's `cut_release.sh:127` regex matches.
- `tests/repo/test_v4_milestone_audit_present.py` (5 tests) pins existence + Gate 4 verdict regex + generator marker (rejects a hand-written substitute) + v4.0 label + v2.1-audit-untouched.

## Task Commits

1. **Task 1: Rebuild + verify sidecar; attempt unsigned .dmg** — no commit (all outputs are gitignored build artifacts: `dist/`, `target/`, `tauri/src-tauri/binaries/`). Verification is the deliverable; recorded here + in this SUMMARY.
2. **Task 2: Generate v4.0 milestone audit + pin it** — `06c7732` (feat)

_No plan-metadata commit yet — orchestrator owns STATE.md/ROADMAP.md per the sequential-main-checkout constraint._

## Files Created/Modified
- `.planning/v4.0-MILESTONE-AUDIT.md` — Gate 4 input; generator-produced, WIRED.
- `tests/repo/test_v4_milestone_audit_present.py` — structural pin for the v4.0 audit (Gate 4 + T-58-02 tamper guard).
- `scripts/integration_audit.py` — seam-runner PYTHONPATH=src propagation + `milestone_meta_for_path()` (filename-derived milestone identity); body f-string parameterized.
- `dist/vibemix_0.1.0-rc1_aarch64-unsigned.dmg` — gitignored; the real unsigned artifact Gate 2 inspects under the dry-run.

## Decisions Made
- **Did NOT force or disable signing.** `cargo tauri build --bundles dmg` compiled + bundled the `.app` cleanly, then auto-attempted codesign (Francesco's `Developer ID Application` from the WIP `tauri.conf.json5`) + notarization, which returned **HTTP 403 — "A required agreement is missing or has expired."** That is exactly the EXTERNAL Apple Developer Program Agreement (KAAN-ACTION, P46 hard rule). Per the plan I did not touch `tauri.conf.json5` to disable signing — I used the unsigned `.dmg` the bundler had already produced (pre-notarize stage) as Gate 2's inspect artifact. The whl fallback (`dist/vibemix-0.1.0.dev0-py3-none-any.whl`) remains available for the dry-run regardless.
- **The audit verdict is generator-truth.** The first generation read `overall_verdict: MISSING` (seams P19__agent MISSING, P25__P28 PARTIAL). I investigated rather than editing the file. Root cause: the generator's seam-test subprocess imported `vibemix` via the ambient interpreter; under bare `python3` that resolves to system Python 3.14 with an old `google-genai` (no `ServiceTier`) → ImportError → false MISSING. Run under the `.venv` (3.12 + pinned deps) all 5 seams are WIRED. I also hardened the subprocess to carry `PYTHONPATH=src`. Never hand-edited the verdict (Pitfall 2 honored).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] integration_audit.py seam-runner reported false-MISSING/PARTIAL verdicts**
- **Found during:** Task 2 (generate v4.0 milestone audit)
- **Issue:** `evaluate_seam()` ran the seam e2e tests via `subprocess.run([sys.executable, "-m", "pytest", …], cwd=REPO)` with no `PYTHONPATH`. When the generator is invoked outside an active venv, `vibemix` fails to import (`ModuleNotFoundError`) and every vibemix-importing seam reports MISSING — green-blocking Gate 4 on a false signal (directly contrary to T-58-02: a wrong verdict falsely reds/greens a release).
- **Fix:** Propagate `PYTHONPATH=<repo>/src` into the subprocess `env` (the canonical CLAUDE.md test path). Combined with running the generator under the `.venv`, all 5 seams report WIRED.
- **Files modified:** scripts/integration_audit.py
- **Verification:** `--seam-tests` under venv → 5/5 WIRED; 22 existing generator tests still pass.
- **Committed in:** 06c7732

**2. [Rule 2 - Missing Critical] v4.0 audit was internally labelled v2.1**
- **Found during:** Task 2
- **Issue:** `compose_milestone_audit()` hardcoded `milestone: v2.1` / "The Unified Cut" / "Phase 37" in the frontmatter + title, so the file written to `.planning/v4.0-MILESTONE-AUDIT.md` was internally a v2.1 document — a correctness gap for a v4.0 Gate 4 input. The plan forbids hand-writing the audit, so the fix belongs in the generator (in-scope `scripts/`), not in the file.
- **Fix:** Added `milestone_meta_for_path()` deriving `(milestone, milestone_name, phase_line)` from the output filename (v4.0/SHIP/Phase 58), parameterized the body f-string, defaulted to the original v2.1 identity for backward compatibility.
- **Files modified:** scripts/integration_audit.py
- **Verification:** v4.0 audit now reads `milestone: v4.0` / `milestone_name: SHIP` / `Phase: 58`; `test_integration_audit_v2_1.py` (22 tests) still green (v2.1 path unchanged).
- **Committed in:** 06c7732

---

**Total deviations:** 2 auto-fixed (1 Rule 1 bug, 1 Rule 2 missing-critical). Both in `scripts/integration_audit.py` — in-scope, disjoint from Kaan's WIP. No scope creep; both required for an honest WIRED Gate 4 input.
**Impact on plan:** Necessary for correctness. The audit verdict is now genuine generator-truth, not a fabricated green.

## Issues Encountered
- **Unsigned `.dmg` not headlessly buildable end-to-end** (RESEARCH Open-Q3 confirmed): the bundler reaches the codesign+notarize step automatically because the WIP `tauri.conf.json5` carries a Developer ID. Notarization is the EXTERNAL gate (Apple Dev Agreement, 403). Resolution: used the bundler's pre-notarize unsigned `.dmg` for Gate 2; the SIGNED/notarized `.dmg` is **KAAN-ACTION** (Apple Dev Agreement via Francesco + SignPath cert) and must NEVER be attempted autonomously (P46). The CI/real-signed path requires the in-effect Apple agreement; until then Gate 2's dry-run uses the unsigned `.dmg` (or the `.whl` fallback) under the checksum-only path.

## Git Discipline
- Staged only my files by explicit path. Kaan's 17 WIP files + the untracked `scripts/_probe_or_audio.py` left untouched/unstaged. `tauri.conf.json5` READ-only (consumed by the bundler, never written). STATE.md / ROADMAP.md not modified. No `gh release create`. No `git add -A/.`/stash/reset.

## Known Stubs
None. The v4.0 audit is generator-produced with a real WIRED verdict on real seam tests; the `.dmg` is a real (unsigned) build artifact, not a placeholder.

## Threat Flags
None. No new network endpoints, auth paths, or trust-boundary surface introduced. T-58-01 (AIza scan) clean; T-58-02 (audit tamper guard) pinned by the new test; T-58-03 (signature) correctly deferred EXTERNAL.

## Next Phase Readiness
- **Gate 4 ready:** `.planning/v4.0-MILESTONE-AUDIT.md` reads WIRED on the exact regex `cut_release.sh:127` greps; pinned.
- **Gate 2 ready (dry-run):** a real unsigned `.dmg` is in `dist/` for `verify_signed.py` checksum-only; the `--require-signed` (real-cut) path stays EXTERNAL.
- **Plan 04 (gate run):** the artifacts these gates inspect now exist. Sidecar current + AIza-clean.
- **Carry-forward / KAAN-ACTION:** signed+notarized `.dmg` (Apple Dev Agreement + SignPath cert) — EXTERNAL, surfaced for Plan 03's consolidated cookbook.

## Self-Check: PASSED
- `.planning/v4.0-MILESTONE-AUDIT.md` — FOUND
- `tests/repo/test_v4_milestone_audit_present.py` — FOUND
- `dist/vibemix_0.1.0-rc1_aarch64-unsigned.dmg` — FOUND
- sidecar both triples — FOUND (executable)
- commit `06c7732` — FOUND

---
*Phase: 58-ship-readiness*
*Completed: 2026-05-21*
