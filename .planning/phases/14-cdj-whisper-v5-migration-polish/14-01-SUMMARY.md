---
phase: 14-cdj-whisper-v5-migration-polish
plan: 01
subsystem: ui
tags: [migration, tooling, vitest, fonts, woff2, grep-gate, polish-log]

# Dependency graph
requires:
  - phase: 11-tauri-shell-wizard
    provides: vanilla TS pure-function component pattern + registerStyle() singleton (the migration target's existing convention)
  - phase: 12-live-session-ui-settings
    provides: vitest + jsdom harness at tauri/ui/tests/, SettingsDrawer canonical v5 glass surface (Wave-3 analog)
  - phase: 13-mascot-overlay
    provides: mascot overlay window + renderer.ts (Wave-4 surface)
provides:
  - Three executable shell-script grep gates (check_v5_migration.sh / check_v5_fonts.sh / check_v5_copy.sh) with --strict / --baseline / --warn-only / --surface flags
  - Four vendored WOFF2 binaries (Saira variable + JetBrains Mono 400/500/600) at tauri/ui/public/fonts/ with SHA-256 attestation captured in 14-01-FONT-ATTESTATION.md
  - Five vitest specs (1 RED-proof for the legacy-token detector + 4 describe.skip per-surface fixtures that Waves 1-4 unskip)
  - tauri/ui/tests/**/*.test.ts now routed under jsdom (vitest config update)
  - 14-POLISH-LOG.md skeleton with Critique Cycles / Side-by-Side Screenshots / Perf Verification sections per CONTEXT Area 3
  - audits/ subdirectory for per-cycle ui-checker / ui-auditor captures
  - ROADMAP Phase 14 success-criterion #4 reconciled to Saira + JetBrains Mono
affects: [14-02-wizard, 14-03-session, 14-04-settings, 14-05-mascot, 14-06-shim-delete]

# Tech tracking
tech-stack:
  added: [vendored Saira variable WOFF2 (Fontsource jsdelivr mirror), vendored JetBrains Mono 400/500/600 WOFF2 (Fontsource jsdelivr mirror)]
  patterns: [bash grep-gate with --strict/--warn-only/--surface scoping, python comment-stripping preprocess for ts/tsx purge-dict gate, vitest describe.skip wave-unskip pattern]

key-files:
  created:
    - scripts/check_v5_migration.sh
    - scripts/check_v5_fonts.sh
    - scripts/check_v5_copy.sh
    - tauri/ui/public/fonts/Saira-VariableFont_wdth,wght.woff2
    - tauri/ui/public/fonts/JetBrainsMono-Regular.woff2
    - tauri/ui/public/fonts/JetBrainsMono-Medium.woff2
    - tauri/ui/public/fonts/JetBrainsMono-SemiBold.woff2
    - tauri/ui/tests/tokens.legacy-detect.test.ts
    - tauri/ui/tests/wizard.tokens.test.ts
    - tauri/ui/tests/session.tokens.test.ts
    - tauri/ui/tests/settings.tokens.test.ts
    - tauri/ui/tests/mascot.chrome.test.ts
    - .planning/phases/14-cdj-whisper-v5-migration-polish/14-01-FONT-ATTESTATION.md
    - .planning/phases/14-cdj-whisper-v5-migration-polish/14-POLISH-LOG.md
    - .planning/phases/14-cdj-whisper-v5-migration-polish/deferred-items.md
  modified:
    - tauri/ui/vitest.config.ts
    - .planning/ROADMAP.md

key-decisions:
  - "Vendored WOFF2 from Fontsource jsdelivr mirror — provides canonical Google Fonts WOFF2 builds without depending on fonts.gstatic.com runtime. Saira variable WOFF2 includes both wdth (75-125) and wght (300-800) axes in a single 99k file."
  - "Vitest config extended to route tests/**/*.test.ts under jsdom (Rule 3 fix — plan filenames standardized on .test.ts, harness only had .spec.ts routed)"
  - "Per-surface specs (wizard/session/settings.tokens, mascot.chrome) wrapped in describe.skip(...) so Wave 0 CI stays green. Waves 1-4 each unskip their own surface as the migration commits land — the spec is the per-wave acceptance gate."
  - "REQUIREMENTS.md POLISH-04 still references 'Geist + Fraunces' — plan explicitly scoped that edit OUT. Documented as DEF-14-01 in deferred-items.md for Wave 5 (Plan 14-06) to resolve."

patterns-established:
  - "Scripted grep gate: bash script + --strict (block) / --baseline (informational header) / --warn-only (default informational) / --surface=<name> (scope to subset) — Wave 5 wires --strict as one-shot pre-commit hook"
  - "Vitest detector parity: containsLegacyToken() helper's regex mirrors LEGACY_TOKEN_PATTERN in check_v5_migration.sh byte-for-byte, so per-surface specs and bash gate agree on what counts as a legacy ref"
  - "Wave-unskip pattern: per-surface specs land in Wave 0 as describe.skip(), Wave 1-N unskips them as the corresponding surface migrates and stays green for the rest of the phase"
  - "Comment-stripped copy gate: python preprocessor strips // and /* */ from .ts/.tsx before grep, so jsdoc residue doesn't trip the purge dict (Pitfall 9 fix)"

requirements-completed: [POLISH-01, POLISH-04, POLISH-06]

# Metrics
duration: ~6min
completed: 2026-05-13
---

# Phase 14 Plan 01: CDJ Whisper v5 Wave 0 Reconciliation Surface Summary

**Three scripted grep gates + four vendored WOFF2 fonts + five vitest specs + polish-log skeleton + ROADMAP typeface reconciliation — Wave 0 validation contract for the v5 migration is locked.**

## Performance

- **Duration:** ~6 min (active execution; system clock skew showed +3h delta)
- **Started:** 2026-05-13T11:18:23Z
- **Completed:** 2026-05-13T11:24:05Z
- **Tasks:** 3 / 3 complete
- **Files created:** 14
- **Files modified:** 2

## Accomplishments

- **Scripted gates** — three bash scripts (`check_v5_migration.sh`, `check_v5_fonts.sh`, `check_v5_copy.sh`) with `--strict` / `--baseline` / `--warn-only` / `--surface=` flags. Wave 5 wires `--strict` as a one-shot pre-commit hook; Waves 1-4 run them in warn-only mode as a progress dashboard.
- **Vendored WOFF2** — Saira variable (wdth + wght axes, 99k) + JetBrains Mono Regular/Medium/SemiBold (~22k each). SHA-256 attestations captured in `14-01-FONT-ATTESTATION.md` (4 hash lines, Wave 5 reflects into `LICENSE-3RD-PARTY.md` per plan-checker I-1 resolution).
- **Vitest harness** — RED-proof detector (`tokens.legacy-detect.test.ts`) with 5 always-green test cases + 4 `describe.skip(...)` per-surface specs that Waves 1-4 unskip. The detector regex mirrors the bash gate byte-for-byte.
- **Polish log skeleton** — `14-POLISH-LOG.md` with 12 critique-cycle rows + 4 side-by-side screenshot rows + 2 perf-verification rows per CONTEXT Area 3.
- **ROADMAP reconciliation** — Phase 14 success-criterion #4 now reads "Saira variable wdth + wght axes for chrome + JetBrains Mono for numerics" (was "Geist for chrome + Fraunces for headlines"), plus the explicit reconciliation note.

## Task Commits

1. **Task 14-01-01:** Vendor Saira + JBM WOFF2 + write three scripted grep gates — `ca79ac9` (feat)
2. **Task 14-01-02:** Write 5 vitest specs + 14-POLISH-LOG.md skeleton — `3881c37` (test)
3. **Task 14-01-03:** Reconcile ROADMAP success-criterion #4 typeface text — `c579385` (docs)

## Baseline Grep Counts (Wave-0 starting state — Waves 1-4 will drive these to zero)

### check_v5_migration.sh (legacy CSS-token refs)

| Surface  | Legacy refs | Target by end-of-Wave |
|----------|-------------|------------------------|
| repo-wide | 160 | 0 (Wave 5 strict pass) |
| wizard   | 139 | 0 (Wave 1 — Plan 14-02 close) |
| session  | 7   | 0 (Wave 2 — Plan 14-03 close) |
| settings | 8   | 0 (Wave 3 — Plan 14-04 close) |
| mascot   | 6   | 0 (Wave 4 — Plan 14-05 close) |

Note: wizard count (139) is lower than RESEARCH.md's "225 across 15 files" — RESEARCH counted both code refs AND jsdoc references; the gate's grep matches both unless a comment-strip preprocess is added, but it still scopes to legitimate `--prefix` token spellings, so 139 is the actual count of `--phosphor` / `--brushed-*` / `--bezel-*` / `--panel*` / `--groove` / `--ink*` / `--col-mascot` tokens visible in wizard files (mix of code and jsdoc — Waves 1 cleans both).

### check_v5_fonts.sh (forbidden font-family declarations)

- Workbench / DM Mono / DSEG7 / Caveat / Geist / Fraunces / Inter in font-family declarations: **42**
- consumer-side `font-family: system-ui` (outside tokens.css): **0**
- Target: 0 / 0 in Wave 5

### check_v5_copy.sh (purge dictionary)

- Hardware-vocab residue (brushed/anodised/phosphor/retro-futurist/knob-fader physics/knurled): **52** (all in jsdoc — comment strip per Pitfall 9 means these are warn-only counts; they'll drop as Waves 1-4 rewrite affected files)
- General AI slop (amazing/awesome/great mix/let me know/delve/leverage/etc.): **0**
- tactile (manual review only — never blocks): **0**
- Target hard-purge: 0 in Wave 5

## SHA-256 Attestations (for Wave 5 LICENSE-3RD-PARTY.md)

```
d5f1ee1ce85a2f6611d76bcd98738132f4706b099dc167f02c2093a1ec5eb975  Saira-VariableFont_wdth,wght.woff2
14425ba9c695763c1547f48a206b7aa60350a33ae23de09f0407877f3fcd89eb  JetBrainsMono-Regular.woff2
cb182feeed4d798ff6961d3c79f7026279448fca0676438aaecb21f3fc39553a  JetBrainsMono-Medium.woff2
400c6bfda18d5d14acad1c15d6dcb9f8e13c015e7286317e0b9a482539bef147  JetBrainsMono-SemiBold.woff2
```

Source: Fontsource jsdelivr CDN (`https://cdn.jsdelivr.net/fontsource/fonts/{saira:vf,jetbrains-mono}@latest/...`). Licenses: OFL-1.1 (both families). Wave 5 (Plan 14-06) updates `tauri/ui/LICENSE-3RD-PARTY.md` to drop the four legacy families (Workbench, DM Mono, DSEG7, Caveat) and add these two new entries with the hashes above.

## Vitest Status

```
Test Files  22 passed (22)
     Tests  242 passed | 13 skipped (255)
  Duration  ~3s
```

Of the 13 skipped: 2 in `wizard.tokens.test.ts`, 3 in `session.tokens.test.ts`, 4 in `settings.tokens.test.ts`, 4 in `mascot.chrome.test.ts`. Each Wave (1-4) unskips its own surface's `describe.skip(...)` wrapper.

## Scripts: Flag Reference

```
scripts/check_v5_migration.sh [--strict|--warn-only|--baseline] [--surface=wizard|session|settings|mascot]
scripts/check_v5_fonts.sh     [--strict|--warn-only|--baseline] [--surface=wizard|session|settings|mascot]
scripts/check_v5_copy.sh      [--strict|--warn-only|--baseline] [--surface=wizard|session|settings|mascot]
```

- `--strict` blocks the commit on any hard-purge / legacy-ref hit. Used in Wave 5 pre-commit hook.
- `--warn-only` (default) prints counts only; exits 0 regardless.
- `--baseline` prints a "BASELINE capture" header and behaves identically to `--warn-only`. Used to capture the Wave-0 starting state.
- `--surface=<name>` scopes the grep to one surface subtree (e.g., `tauri/ui/src/wizard/`).

## Vitest Specs: Wave Activation Map

| Spec | Wave 0 status | Wave that unskips |
|------|----------------|---------------------|
| `tokens.legacy-detect.test.ts` | ✅ always-green (5 cases) | n/a — stays always-green |
| `wizard.tokens.test.ts` | ⏸ describe.skip (2 cases) | Wave 1 — Plan 14-02 |
| `session.tokens.test.ts` | ⏸ describe.skip (3 cases) | Wave 2 — Plan 14-03 |
| `settings.tokens.test.ts` | ⏸ describe.skip (4 cases) | Wave 3 — Plan 14-04 |
| `mascot.chrome.test.ts` | ⏸ describe.skip (4 cases) | Wave 4 — Plan 14-05 |

## Decisions Made

- **Fontsource jsdelivr CDN over a manual fonts.google.com download:** Reproducible, deterministic, no browser-style "best WOFF2 for this UA" negotiation. Variable WOFF2 served at `latin-wdth-normal.woff2` carries both axes (verified via `file`: "Web Open Font Format (Version 2), TrueType, length 98912"). License (OFL-1.1) and hash are stable across regenerations.
- **`--surface=` scoping early:** plan only required repo-wide gates but the per-surface flag is what makes Waves 1-4's per-plan verify clean. Adding `--surface=` in Wave 0 means each wave's verify block can call `bash scripts/check_v5_migration.sh --surface=$wave --strict` directly without grep-and-filter shell pipelines in plan YAML.
- **Comment-stripping preprocessor in check_v5_copy.sh:** RESEARCH §Pitfall 9 calls this out specifically — jsdoc references to "brushed metal" inside `*.ts` files should NOT block the gate. Python regex-based comment strip is sufficient (not a full TS parser, but the gate is grep-based discovery, not source-of-truth analysis).
- **Vitest config update:** `tests/**/*.test.ts` was not in the include list (only `.spec.ts`). Per task 14-01-02's `<files>` spec the new specs land at `.test.ts` — extending the config under jsdom routing was a Rule 3 blocking fix.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] BSD grep rejected pattern starting with `--`**
- **Found during:** Task 14-01-01 (running `bash scripts/check_v5_migration.sh --baseline` for the first time)
- **Issue:** `grep -rnE "$LEGACY_TOKEN_PATTERN"` where the pattern starts with `--(phosphor|...)`. BSD grep on macOS interprets the leading `--` as the end-of-options marker AND as a flag prefix, printing `grep: unrecognized option`. The Linux GNU grep doesn't have this problem but the macOS dev environment does.
- **Fix:** Use `grep -rnE -e "$LEGACY_TOKEN_PATTERN"` — the `-e` flag makes the next arg an explicit pattern, bypassing the option-parser stage. Applied at every `grep -rnE` call site in `check_v5_migration.sh`.
- **Files modified:** scripts/check_v5_migration.sh
- **Verification:** `bash scripts/check_v5_migration.sh --baseline` now exits 0 and reports 160 legacy refs across the repo.
- **Committed in:** ca79ac9 (Task 14-01-01 commit — fix landed before initial commit)

**2. [Rule 3 - Blocking] Vitest config did not include `tests/**/*.test.ts`**
- **Found during:** Task 14-01-02 (after creating the 5 vitest specs with `.test.ts` filenames per plan)
- **Issue:** `tauri/ui/vitest.config.ts` `include` array listed `src/**/*.spec.ts`, `src/**/*.test.ts`, `tests/**/*.spec.ts` — but NOT `tests/**/*.test.ts`. The 5 new specs would not be discovered by `npm run test` until the config was extended.
- **Fix:** Added `tests/**/*.test.ts` to both `include` and `environmentMatchGlobs` (routed under jsdom — the per-surface specs render components / parse HTML and need a DOM environment). Updated the header comment to attribute the config extension to Phase 14 Plan 14-01.
- **Files modified:** tauri/ui/vitest.config.ts
- **Verification:** Full `npm run test` run picks up all 5 new specs (1 file + 4 skipped surface specs), 22 test files total, 242 passed + 13 skipped, all green.
- **Committed in:** 3881c37 (Task 14-01-02 commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking infra)
**Impact on plan:** Both fixes essential for the verify gates to succeed. No scope creep — neither fix added new functionality beyond what the plan already specified.

## Issues Encountered

None. The plan executed cleanly. The one in-scope wrinkle (the REQUIREMENTS.md POLISH-04 stale "Geist + Fraunces" text) was deferred per plan instruction and logged as DEF-14-01 in `deferred-items.md` for Wave 5 (Plan 14-06) to resolve.

## Deferred Items

See `.planning/phases/14-cdj-whisper-v5-migration-polish/deferred-items.md`:

- **DEF-14-01:** REQUIREMENTS.md POLISH-04 typeface text still reads "Geist for chrome + Fraunces for headlines" (and the traceability row reads "Geist + Fraunces only"). Plan explicitly scoped this edit OUT of Task 14-01-03; recommended fix in Wave 5 is the same surgical text-swap pattern.

## Threat Surface Scan

No new security-relevant surface introduced. The vendored WOFF2 binaries are already covered by T-14-01 (supply-chain) in the plan's threat_model — SHA-256 attestations were captured per the mitigation plan and live in `14-01-FONT-ATTESTATION.md` for Wave 5 to fold into `LICENSE-3RD-PARTY.md`.

## Self-Check: PASSED

Verified each claim before finalizing:

- ✅ `scripts/check_v5_migration.sh` exists, executable (`-rwxr-xr-x`)
- ✅ `scripts/check_v5_fonts.sh` exists, executable
- ✅ `scripts/check_v5_copy.sh` exists, executable
- ✅ `tauri/ui/public/fonts/Saira-VariableFont_wdth,wght.woff2` exists (99k, valid WOFF2)
- ✅ `tauri/ui/public/fonts/JetBrainsMono-Regular.woff2` exists (21k, valid WOFF2)
- ✅ `tauri/ui/public/fonts/JetBrainsMono-Medium.woff2` exists (22k, valid WOFF2)
- ✅ `tauri/ui/public/fonts/JetBrainsMono-SemiBold.woff2` exists (22k, valid WOFF2)
- ✅ `tauri/ui/tests/tokens.legacy-detect.test.ts` exists, 5 tests passing
- ✅ `tauri/ui/tests/wizard.tokens.test.ts` exists, describe.skip wrapper
- ✅ `tauri/ui/tests/session.tokens.test.ts` exists, describe.skip wrapper
- ✅ `tauri/ui/tests/settings.tokens.test.ts` exists, describe.skip wrapper
- ✅ `tauri/ui/tests/mascot.chrome.test.ts` exists, describe.skip wrapper
- ✅ `14-01-FONT-ATTESTATION.md` exists, 4 SHA-256 lines (matches `^[a-f0-9]{64}` × 4)
- ✅ `14-POLISH-LOG.md` exists, contains "Critique Cycles" + "Perf Verification" + "Side-by-Side Screenshots"
- ✅ ROADMAP.md grep "Saira variable wdth + wght axes for chrome + JetBrains Mono" → 1 hit
- ✅ ROADMAP.md grep "Geist for chrome + Fraunces for headlines" → 0 hits
- ✅ Commits in git log: `ca79ac9` (feat), `3881c37` (test), `c579385` (docs)

## Next Phase Readiness

Wave 0 deliverables locked. Waves 1-4 can each:
1. Run `bash scripts/check_v5_migration.sh --surface=<wave> --strict` as the per-plan verify gate
2. Run `cd tauri/ui && npm run test -- <wave>.tokens.test.ts --run` after unskipping that wave's describe wrapper
3. Append cycle rows to `14-POLISH-LOG.md` for the ui-checker → fix → ui-auditor loop
4. Reach `--strict` zero-hit and unskip-passes-green as the surface acceptance condition

Wave 5 (Plan 14-06 — shim-delete commit) can wire `.git/hooks/pre-commit` to invoke `check_v5_migration.sh --strict` repo-wide for that one commit, with all four WOFF2 binaries already vendored so the tokens.css surgery is purely a `@font-face` block swap.

---
*Phase: 14-cdj-whisper-v5-migration-polish*
*Plan: 14-01*
*Completed: 2026-05-13*
