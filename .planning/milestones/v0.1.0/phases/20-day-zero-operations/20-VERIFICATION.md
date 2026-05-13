---
gsd_verification_version: 1.0
phase: 20
phase_name: Day-Zero Operations
status: human_needed
verified_at: 2026-05-13
---

# Phase 20 Verification

## Success criteria (from ROADMAP)

### 1. `git tag v0.1.0 && git push --tags` triggers the CI matrix in <30 min
**Autonomous side:** ✅ — `.github/workflows/release.yml` (Phase 18 Plan 18-05)
already implements the 2-OS × 5-stage matrix with mock-signing fallback.
**Human side:** untested — needs an actual tag push to verify end-to-end.
Will happen once the 11 GitHub secrets are configured (see Plan 20 Task 6
script for the inventory).

### 2. Fresh-machine install rehearsal in <10 minutes
**Autonomous side:** ✅ — `docs/install-rehearsal.md` is the stopwatch-able
11-step checklist for both platforms with a failure-class taxonomy.
**Human side:** Kaan must borrow / clean-spin a non-dev macOS Sequoia
machine and a non-dev Windows 11 machine and run through the checklist
once the v0.1.0 signed binaries are built. Results log to this file.

### 3. Second-responder rota + auto-label + Discord
**Autonomous side:** ✅
- Rota doc: `docs/day-zero-rota.md` (3 named owners, 8h shifts CET, 72h coverage, alert-class escalation table).
- Auto-label: `.github/workflows/issue-triage.yml` (runs on `issues.opened`, applies `triage` always + parses `Severity`/`Component` from Phase 19 templates).
- Discord placeholder in README footer with `<!-- TODO(kaan, pre-tag-v0.1.0) -->` marker for replacement.
**Human side:** Kaan creates the Discord server, drops the invite into
README, removes the TODO marker.

### 4. Day-zero analytics dashboard on api.altidus.world
**Autonomous side:** ✅ — alert math + classes documented in
`docs/day-zero-rota.md` ("Alert classes + who responds" section).
**Human side:** Musa wires the actual dashboard against
`/v1/telemetry/event` records on the Bravoh backend. Out of scope for
the vibemix repo.

## Test evidence

```
$ pytest tests/repo/test_phase20_docs.py -q
.................... 19 passed in 0.04s
```

19 tests covering every Phase 20 artifact's shape (existence,
expected content fields, executable bits where required).

## Pretag readiness today

```
$ scripts/dist/pretag_check.sh
[1/7] Phase 16 ear-test signed off       ✗
[2/7] Phase 17 grading ≥4 raters         ✗
[3/7] README has no unresolved TODOs     ✗
[4/7] Tauri pubkey not placeholder       ✗
[5/7] 11 GitHub secrets configured       ✗
[6/7] Discord invite real                ✗
[7/7] Apple Dev ID cert in Keychain      ✓
RESULT: 1 pass / 6 fail / 0 warn
```

The 6 failures are the v0.1.0 ship-list for Kaan. Phase 20 itself is
complete — the script + docs + workflow are the artifact.

## Threats from CONTEXT (status)

- **T-20-01** (rota-blind commit): Mitigation deferred — the pre-commit
  hook idea was scope-creep for v0.1.0. Plan 20 Task 1 (rota doc) tells
  responders to glance at `main`'s recent commits at shift start instead.
- **T-20-02** (auto-label drops): ✅ Mitigated — rota doc says responder
  owns the `is:open is:issue label:triage` sweep every 4h regardless.
- **T-20-03** (cost-spike false positive): ✅ Mitigated — playbook step
  4 ("first verify spike isn't launch traffic surge") + 24h baseline
  warm-up before alerts arm.

## Sign-off

**Autonomous portion: complete.** Phase 20 Plan 20 lands 6 files (1
workflow, 4 docs, 1 script) + 19 tests. Run `scripts/dist/pretag_check.sh`
to see the live state of the 6 remaining human-owned items.

**Phase 20 verification status flips from `human_needed` to `passed`** once:
- Pretag check returns exit 0
- Rehearsal log appended to this file with both platforms under 10 minutes
- v0.1.0 tag has been pushed and the matrix has produced a green Release
