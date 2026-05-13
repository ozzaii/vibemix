---
phase: 14
slug: cdj-whisper-v5-migration-polish
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-13
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for the CDJ Whisper v5 migration. This phase is **visual-contract migration + shim deletion**, not new feature dev — validation is dominated by static-analysis grep gates + visual screenshot diffs + a small set of vitest assertions.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest 2.1 (existing — installed Phase 12 W2) + jsdom (existing) |
| **Config file** | `tauri/ui/vitest.config.ts` (existing) |
| **Quick run command** | `cd tauri/ui && npm run test` |
| **Full suite command** | `cd tauri/ui && npm run test && cd ../.. && npm run check:ipc 2>/dev/null || true && python -m pytest -q` |
| **Estimated runtime** | ~25s (vitest); full repo gates ~90s |

Additional Phase-14-specific verifiers (scripts created by this phase):

| Script | Purpose |
|--------|---------|
| `scripts/check_v5_migration.sh` | grep gate — zero legacy-token refs in `tauri/ui/src/**/*.{ts,tsx,css}` |
| `scripts/check_v5_fonts.sh` | grep gate — zero forbidden-family `font-family:` declarations (Workbench, DM Mono, DSEG7, Caveat, Geist, Fraunces, Inter, system-ui) |
| `scripts/check_v5_copy.sh` | grep gate — zero purge-dictionary terms in user-facing strings (brushed, anodised, phosphor, retro-futurist, knob/fader physics, hardware-context "tactile") |

---

## Sampling Rate

- **After every task commit:** `npm run test --reporter=dot` (vitest unit/component) — ~5s
- **After every plan wave:** Full vitest suite + relevant `check_v5_*.sh` grep gates for the migrated surface
- **Before `/gsd-verify-work`:** All gates green: vitest + all three `check_v5_*.sh` gates with `--strict` mode + `npm run check:ipc` (Phase 11 carryover) + `cargo test` (Phase 12 carryover) + `python -m pytest -q` (Phase 12 carryover)
- **Max feedback latency:** 30 seconds (vitest run; grep gates are sub-second)

---

## Per-Task Verification Map

> Populated by the planner. Each per-surface plan (14-02 wizard, 14-03 session, 14-04 settings, 14-05 mascot) gets a row per task. 14-01 reconciliation + 14-06 subtractive shim-delete are scripted gates.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 14-01-01 | 01 | 0 | POLISH-01 | — | scripts/check_v5_*.sh return 0 on a no-op state (baseline capture) | scripted gate | `bash scripts/check_v5_migration.sh --baseline` | ❌ W0 | ⬜ pending |
| 14-01-02 | 01 | 0 | POLISH-01 | — | vitest red on a fixture proving a `--phosphor` ref triggers failure | unit | `npm run test -- tokens.legacy-detect.test.ts` | ❌ W0 | ⬜ pending |
| 14-02-NN | 02 | 1 | POLISH-01, POLISH-02 | — | each wizard component reads v5 primitives only | unit + grep | `npm run test wizard.tokens.test.ts && bash scripts/check_v5_migration.sh --surface=wizard --strict` | ❌ W0 | ⬜ pending |
| 14-03-NN | 03 | 2 | POLISH-01, POLISH-02, POLISH-05 | — | session components read v5 primitives + perf toggle wires correctly | unit + grep + RTL | `npm run test session.tokens.test.ts && bash scripts/check_v5_migration.sh --surface=session --strict` | ❌ W0 | ⬜ pending |
| 14-04-NN | 04 | 3 | POLISH-01, POLISH-02, POLISH-03 | — | settings drawer reads v5 primitives + Performance group renders | unit + grep | `npm run test settings.tokens.test.ts && bash scripts/check_v5_migration.sh --surface=settings --strict` | ❌ W0 | ⬜ pending |
| 14-05-NN | 05 | 4 | POLISH-01, POLISH-02, POLISH-05 | — | mascot overlay window chrome reads v5 primitives + animated border surrounds frame | unit + visual | `npm run test mascot.chrome.test.ts && bash scripts/check_v5_migration.sh --surface=mascot --strict` | ❌ W0 | ⬜ pending |
| 14-06-01 | 06 | 5 | POLISH-01, POLISH-04 | — | shim-delete commit — all four grep gates pass repo-wide with `--strict` | scripted gate | `bash scripts/check_v5_migration.sh --strict && bash scripts/check_v5_fonts.sh --strict && bash scripts/check_v5_copy.sh --strict` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `scripts/check_v5_migration.sh` — token grep gate (legacy tokens: `--phosphor*`, `--brushed-*`, `--bezel-*`, `--panel*`, `--groove`, `--ink*`, `--charcoal`, `--col-mascot`). Supports `--baseline`, `--surface={wizard,session,settings,mascot}`, `--strict`.
- [ ] `scripts/check_v5_fonts.sh` — forbidden-font-family grep gate.
- [ ] `scripts/check_v5_copy.sh` — purge-dictionary grep gate.
- [ ] `tauri/ui/tests/tokens.legacy-detect.test.ts` — vitest assertion that the grep helper module reports legacy hits when fed a fixture (RED test for migration completeness).
- [ ] `tauri/ui/tests/{wizard,session,settings,mascot}.tokens.test.ts` — one vitest spec per surface that imports rendered component output and asserts zero legacy token names in inline styles or class strings.
- [ ] `tauri/ui/tests/mascot.chrome.test.ts` — snapshot test for the mascot overlay window chrome (animated border markup present, glass panel anatomy correct).
- [ ] `tauri/ui/public/fonts/Saira-Variable.woff2` + `JetBrainsMono-Variable.woff2` — vendored WOFF2 (replaces remote `@import`).
- [ ] `tauri/ui/LICENSE-3RD-PARTY.md` updated with Saira + JetBrains Mono SHA-256 attestations.
- [ ] `14-POLISH-LOG.md` skeleton (markdown table for the per-cycle ui-checker → ui-auditor → fix loop).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Side-by-side screenshot parity per surface | POLISH-01, POLISH-02 | Visual equivalence against `mocks/vibemix-direction-final.html` is a human-judgment call after objective gates pass | For each surface (wizard, session, settings, mascot): run `cd tauri/ui && npm run tauri dev`, screenshot the surface, place next to the corresponding mock section, attach pair to `14-POLISH-LOG.md` |
| Backdrop-filter perf on non-dev Windows machine | POLISH-05 | Tauri WebView2 transparent-window backdrop bug ([tauri#10064](https://github.com/tauri-apps/tauri/issues/10064)) requires real Windows hardware; macOS doesn't repro | Build the Tauri release on Windows; open the live session; visually verify mascot overlay window renders chrome correctly; toggle Settings → Performance → "Lighter blur" and verify CSS variable swap takes effect (no visual stutter) |
| Mascot mood swap composes with v5 chrome | POLISH-05 | Mood transitions need live Gemini reaction to verify amber accent stays consistent across hype-man / teacher / coach | Run a real DJ session with all three moods triggered; verify chrome amber tone is identical across moods; verify animated border sweep is uninterrupted by mood swap |
| `gsd-ui-checker` zero findings per surface | POLISH-01 | Skill invocation with screenshot capture is interactive | Per surface, run `Skill(skill="gsd-ui-checker", args="14 --surface=<name>")`, attach output ref to `14-POLISH-LOG.md` |
| `gsd-ui-auditor` 3 audits green per surface | POLISH-02, POLISH-03 | Same as above | Per surface, run `Skill(skill="gsd-ui-auditor", args="14 --surface=<name>")`, attach output ref to `14-POLISH-LOG.md` |

---

## Validation Sign-Off

- [ ] All tasks have automated verify OR Wave 0 dependencies declared
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify (grep gates count as automated)
- [ ] Wave 0 covers all MISSING references (`scripts/check_v5_*.sh`, vitest specs, vendored WOFF2, polish log skeleton)
- [ ] No watch-mode flags (vitest runs in CI mode via `--reporter=dot`)
- [ ] Feedback latency < 30s (vitest unit); < 90s (full repo gates)
- [ ] `nyquist_compliant: true` set in frontmatter once planner fills per-task map and Wave 0 lands

**Approval:** pending
