---
phase: 21-sign-notarize-github-release-matrix
plan: 01
subsystem: infra
tags: [release-pipeline, github-actions, code-signing, tauri-updater, signpath, apple-notarytool, pitfall-7]

# Dependency graph
requires:
  - phase: 18
    provides: "release.yml 2-target matrix + detect-signing-mode + placeholder-pubkey-gate + sign_manifest.sh + tauri/src-tauri/keys/README.md"
provides:
  - "21-DEFERRED.md tracker for the 2 known external blockers (Apple Developer Program Agreement update — Francesco-action; SignPath OSS Foundation application — Kaan-action ~1-week SLA)"
  - "secret-name-audit job in .github/workflows/release.yml (Pitfall 7 prevention: silent updater signature failure on TAURI_UPDATER_PRIVATE_KEY_PASSWORD vs TAURI_UPDATER_KEY_PASSWORD drift)"
  - "docs/signpath-application.md (Day-1 OSS application checklist + status tracker)"
  - "docs/release-process.md Pre-Flight refresh (steps 1 + 2 cross-reference 21-DEFERRED.md)"
affects: [21-02-PLAN (4-target matrix lift), 21-03-PLAN (macOS sign — unblocked by Blocker A close), 21-04-PLAN (Windows sign — unblocked by Blocker B close)]

tech-stack:
  added: []  # No new runtime deps — pure CI workflow + docs delta
  patterns: [usage-pattern-regex grep gate (avoids self-match), Phase-16-style deferred-tracker, downstream-block-naming-by-plan-id]

key-files:
  created:
    - .planning/phases/21-sign-notarize-github-release-matrix/21-DEFERRED.md
    - docs/signpath-application.md
  modified:
    - .github/workflows/release.yml
    - docs/release-process.md

key-decisions:
  - "Audit gate uses usage-pattern regex (env:/${{secrets.}}/$VAR/${VAR}/: ${VAR:?}), not bare substring — prevents the gate's own assertion strings from self-matching (Rule 1 auto-fix during Task 2)."
  - "Both blockers documented as 'deferred to' surface per feedback_autonomous_no_grey_area_pause; pipeline ships in mock-signing mode while externalities resolve."
  - "Plan 21-01 ships ONLY the scaffolding + audit gate. 4-target matrix lift = Plan 21-02. Real Apple/SignPath secret activation = Kaan-action after blockers close."

patterns-established:
  - "Pitfall-7 audit pattern: detect alternate-form env-var name drift across multiple files via usage-pattern regex (not substring), strip comments, require canonical hits ≥1 in each consumer file."
  - "Deferred-blocker tracker shape: status, owner, what's-needed, why-blocking, downstream-block (named plan), workaround, verification-when-resolved, activation-steps, resolution log."

requirements-completed: [DIST-09, DIST-11, DIST-13]

# Metrics
duration: 18min
completed: 2026-05-14
---

# Phase 21 Plan 01: Pre-Flight Blockers + Pitfall-7 Audit Gate Summary

**Surfaced 2 external blockers (Apple Developer Program Agreement update — Francesco-action; SignPath OSS Foundation — Kaan-action ~1-week SLA) as a single 21-DEFERRED.md tracker, shipped Pitfall-7 secret-name-audit job in release.yml that fails the build on TAURI_UPDATER_PRIVATE_KEY_PASSWORD vs TAURI_UPDATER_KEY_PASSWORD drift, and refreshed docs/release-process.md Pre-Flight steps to cross-reference the tracker.**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-05-14
- **Completed:** 2026-05-14
- **Tasks:** 3 / 3
- **Files modified:** 4 (2 created, 2 modified)
- **Commits:** 3 task + 1 plan-metadata (this commit)

## Accomplishments

- **Shipped scaffolding (unblocked work):**
  - `21-DEFERRED.md` — single canonical Kaan/Francesco-action surface; Apple Issuer ID `3f60cc6b-df70-4ff8-9ceb-865dac6c1b4b` + key ID `URMDRP5M3P` baked in (label-only; no key material); per-blocker activation steps listed for the post-resolution moment.
  - `secret-name-audit` job in `.github/workflows/release.yml` — runs on tag pushes + `workflow_dispatch`; usage-pattern regex prevents both the alternate-form drift AND the gate's own self-match; synthetic-drift test locally confirms gate trips when `$TAURI_UPDATER_PRIVATE_KEY_PASSWORD` is injected.
  - `docs/signpath-application.md` — Day-1 OSS application checklist with form-field table (vibemix-binaries slug matching release.yml line 297, Apache-2.0 license confirmed, identity email matching GitHub commit identity).
  - `docs/release-process.md` Pre-Flight refresh — steps 1 (SignPath) + 2 (Apple cert) now cross-reference 21-DEFERRED.md; all 8 sections of the runbook preserved (verified post-edit).
- **Deferred surface (Kaan-action-required for activation):**
  - Apple Developer Program Agreement update (Francesco-action) → unblocks Plan 21-03 macOS sign.
  - SignPath OSS Foundation application (Kaan-action Day-1) → unblocks Plan 21-04 Windows MSI sign.
  - Both blockers ship with mock-signing-mode workaround already wired in `release.yml` Wave 0 (`detect-signing-mode` → `SIGNING_AVAILABLE=false`).

## Task Commits

1. **Task 1: Create 21-DEFERRED.md surfacing both external blockers** — `2f6e211` (feat)
2. **Task 2: Add secret-name audit gate to release.yml** — `2befa8f` (feat)
3. **Task 3: Day-1 SignPath OSS application doc + release-process Pre-Flight refresh** — `d741250` (docs)

**Plan metadata commit:** [appended after SUMMARY write — see git log]

## Files Created/Modified

- `.planning/phases/21-sign-notarize-github-release-matrix/21-DEFERRED.md` (CREATED) — Single canonical deferred-blocker tracker. Two blockers with full status / owner / workaround / verification / activation-steps / resolution-log. Status board table. Reference links.
- `.github/workflows/release.yml` (MODIFIED) — New `secret-name-audit` job inserted between `detect-signing-mode` and `placeholder-pubkey-gate`. Two assertion steps: (a) only `TAURI_UPDATER_KEY_PASSWORD` (canonical per `tauri/src-tauri/keys/README.md`) used as env var across release.yml + tauri.conf.json5 + sign_manifest.sh, (b) `TAURI_UPDATER_PRIVATE_KEY` referenced in release.yml AND sign_manifest.sh. Comment stripping + usage-pattern regex prevents self-match.
- `docs/signpath-application.md` (CREATED) — Day-1 OSS Foundation application checklist: pre-application checklist, form-field table (Apache-2.0, `vibemix-binaries` slug), status tracker, EV-cert fallback gated on Kaan approval.
- `docs/release-process.md` (MODIFIED) — Pre-Flight steps 1 + 2 now end with cross-references to 21-DEFERRED.md (Blocker B + Blocker A respectively). All 8 sections (Pre-Flight / Cutting / Rolling back / Mock-signing / Manual rehearsal / Hand-offs / Release-day / Cross-references) preserved.

## Decisions Made

- **Usage-pattern audit, not substring audit.** Naive `grep -c "TAURI_UPDATER_PRIVATE_KEY_PASSWORD"` self-matches the audit's own assertion strings (the error message must name the forbidden token). Switched to a regex matching only ACTUAL env-var usage patterns: `env: KEY:`, `${{ secrets.KEY }}`, `$KEY`, `${KEY}`, `"${KEY:?...}"`. Locally simulated audit (post-fix): all 3 files report `forbidden_usages=0`. Synthetic-drift test (injecting `$TAURI_UPDATER_PRIVATE_KEY_PASSWORD` into sign_manifest.sh) trips the gate cleanly.
- **Audit independent of needs:** the audit fires standalone on tag pushes + `workflow_dispatch`, NOT chained to `detect-signing-mode` or `placeholder-pubkey-gate`. Rationale: secret-name drift is a config bug, not a signing-availability question; it should fail fast regardless of whether real secrets are configured.
- **Workaround path UN-changed:** the plan adds an audit gate, does NOT modify the existing mock-signing fallback (Phase 18 contract). `build-macos` + `build-windows` still run BUILD + VERIFY when `SIGNING_AVAILABLE=false`; `release-publish` stays tag-gated AND secrets-gated.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] Self-referential audit gate false positive**
- **Found during:** Task 2 verification step (initial implementation)
- **Issue:** First-draft audit used `grep -c "TAURI_UPDATER_PRIVATE_KEY_PASSWORD"` — matched the assertion's own error-message string inside release.yml itself, reporting `forbidden=1` for release.yml even when no actual env-var drift existed. Naive grep + self-referential audit body is a guaranteed false positive.
- **Fix:** Switched both grep blocks to a usage-pattern regex `(\$\{?|secrets\.|env:[[:space:]]+|: ?"?\$\{|^[[:space:]]*[A-Z_]*=)PASSWORD_NAME` that matches only ACTUAL env-var references (`${{ secrets.X }}`, `env: X:`, `$X`, `${X}`, `"${X:?...}"`, `X=...`). Mentions inside YAML strings or error-message bodies are now ignored.
- **Files modified:** `.github/workflows/release.yml` (single Edit) — same commit `2befa8f` (caught + fixed before commit)
- **Verification:** Locally simulated the audit (post-fix): all 3 files report `forbidden_usages=0 canonical_usages={3,0,2}` and `TAURI_UPDATER_PRIVATE_KEY usages={2,3}` (release.yml, sign_manifest.sh). Synthetic-drift test (injecting `$TAURI_UPDATER_PRIVATE_KEY_PASSWORD` into sign_manifest.sh) trips the gate (`forbidden_usages=1`).
- **Committed in:** `2befa8f` (no separate commit — the gate was never committed in its broken form; the fix was applied before staging)

---

**Total deviations:** 1 auto-fixed (1 Rule 1 bug)
**Impact on plan:** Strengthens the Pitfall-7 gate. Without the usage-pattern regex, the gate is unshippable (always false-positive on its own release.yml). Same plan scope, stronger implementation.

## Issues Encountered

- None other than the deviation above. Pytest baseline preserved exactly (93 collection errors → 93 collection errors, delta = 0; pre-existing failure-mode unrelated to Plan 21-01 scope — these are Python 3.14 sounddevice/coreaudio collection issues from prior phases).

## User Setup Required

Both blockers are surfaced via `21-DEFERRED.md` (the deferred-blocker tracker IS the user-setup surface for this plan). No separate USER-SETUP.md needed — the plan's `user_setup` frontmatter (signpath-oss-foundation + apple-developer-program) maps 1:1 to Blocker B + Blocker A in 21-DEFERRED.md.

### What fires on the secret-name audit gate

- **Triggers:** tag pushes matching `v*` OR `workflow_dispatch` (covers rehearsal flow).
- **Pass condition (current state):** All 3 files (release.yml + tauri.conf.json5 + sign_manifest.sh) use ONLY `TAURI_UPDATER_KEY_PASSWORD` in env-var usage position. `release.yml` + `sign_manifest.sh` both reference `TAURI_UPDATER_PRIVATE_KEY` consistently. Tauri.conf.json5 references the PUBKEY not the password (canonical absence expected).
- **Fail condition:** Any file gains a usage-pattern reference to `TAURI_UPDATER_PRIVATE_KEY_PASSWORD` (the Tauri-docs alternate form) — fails the build with `::error::Pitfall 7 (silent updater signature failure): TAURI_UPDATER_PRIVATE_KEY_PASSWORD used in <file> — Tauri docs alternate the two names; pick TAURI_UPDATER_KEY_PASSWORD per tauri/src-tauri/keys/README.md and align all three files.` Or: canonical name disappears from release.yml / sign_manifest.sh (pipeline cannot sign manifest).
- **Why this matters:** Pitfall 7 (`PITFALLS.md` lines 178–195) is the SILENT failure class — updater signs `latest.json` with the wrong env var, manifest signature is technically valid but the updater client rejects because the pubkey doesn't match. CI green, real users see "update failed" toast on every check. The gate prevents that class from sliding past review.

## Threat Flags

None. No new network endpoints, auth paths, file-access patterns, or schema changes at trust boundaries introduced. All work is CI-config + Markdown docs.

## Next Phase Readiness

- **Plan 21-02 (4-target build matrix lift):** READY. Plan 21-01 deliberately did not touch the existing 2-target matrix — that's 21-02's owned scope. The audit gate is matrix-agnostic (it runs once on ubuntu-latest before any build job).
- **Plan 21-03 (macOS sign + notarize + stapler):** BLOCKED on Blocker A (Francesco-action). Mock-signing path live; real-signing path activates the moment Apple Developer Program Agreement update lands AND Kaan completes the activation-steps section of 21-DEFERRED.md Blocker A (cert export → base64 → 7 GH secrets pasted).
- **Plan 21-04 (Windows MSI SignPath + SmartScreen smoke test):** BLOCKED on Blocker B (Kaan-action Day-1). Mock-signing path live; real-signing path activates after SignPath approval lands (~1 week from filing) AND Kaan completes the activation-steps section of 21-DEFERRED.md Blocker B (4 SignPath secrets pasted).
- **Day-1 file action for Kaan:** File the SignPath OSS application TODAY using `docs/signpath-application.md` as the checklist. ETA = ~1 week; if not filed today, that 1 week starts later and the v2.0 ship gate gets pushed.

## Self-Check: PASSED

- `[ -f .planning/phases/21-sign-notarize-github-release-matrix/21-DEFERRED.md ]` → FOUND
- `[ -f docs/signpath-application.md ]` → FOUND
- Commit `2f6e211` in git log → FOUND
- Commit `2befa8f` in git log → FOUND
- Commit `d741250` in git log → FOUND
- YAML `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/release.yml'))"` → exits 0
- All 5 plan-verification clauses pass
- Pytest baseline preserved (93 collection errors → 93, delta = 0)

---
*Phase: 21-sign-notarize-github-release-matrix*
*Completed: 2026-05-14*
