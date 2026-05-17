# Project Research Summary — v3.1 Distribution-Ready Pass

**Project:** vibemix (AI DJ Co-Host)
**Domain:** Cross-platform desktop AI distribution polish — Win + Mac one-click install, dep audit/pin, e2e MacBook validation, mascot real-asset land, narrow-scope OSS utility
**Researched:** 2026-05-17
**Confidence:** HIGH

## Executive Summary

v3.0 closed engineering-complete on 2026-05-17 — anti-slop audio path, latency stack v2, hybrid hallucination gate, CDJ-Whisper visual lock, README hero verbatim lock, EvidenceRegistry citation strip, and the KAAN-ACTION-LEGAL §SHIP-01..13 discharge cookbook are all in the repo. **The product itself is finished.** v3.1 is NOT new product scope — it is the distribution-polish layer that closes the gap between "Kaan's machine runs this" and "anyone on a clean Mac or Windows box can run this." Five target features map 1:1 to milestone scope: (1) one-click install Win+Mac, (2) dep audit/pin/lockfile/SBOM, (3) new-dep opportunity scan, (4) end-to-end MacBook pass, (5) mascot real GLBs with full emotion coverage.

The 4 research agents converged on a tight, opinionated recommendation: **zero new runtime AI deps, zero new IPC wrappers, zero new processes, every change either build-time / CI-time / test-time / asset-only.** Bundle stays under the 350 MB hard cap (Win +~6 MB VB-CABLE optional bundle; Mac detect-and-guide pattern). The mascot lands 23 GLB clips (3 Base + 5 Emotion + 5 Anticipation + 10 Reaction) anchored to the existing v2.1 4-layer additive state machine. Every dep choice carries an explicit green/yellow/red install-impact rating per memory `project_one_click_install_hard_req`. Two unavoidable OS-mandated friction points are reframed as forewarning UX rather than engineering problems: the Windows driver-signature security prompt (cannot be suppressed per VB-Audio confirmation) and the macOS BlackHole system-extension approval (cannot be silent-installed by Apple design).

The principal risk is **silent regression of the v3.0 engineering surface** while polishing distribution. The pitfalls catalogue 44 specific tripwires — top of the list: stale-`pip freeze`-from-Kaan-venv shipping unused deps into the lockfile; the "MacBook-only" trap that validates only Apple-Silicon Sonoma and rubber-stamps a build that fails on macOS 12.3 Intel; mascot tests built around the `mascot.html` easter egg instead of the v3.0 Tauri+Three.js production surface; the anti-slop blocklist false-tripping on installer prose and tempting a gate relaxation. Every pitfall has a grep-able plan-phase warning sign + a constraint-preserving prevention. The five v3.0 invariants — POC immutability, ModelRouter seam, anti-slop blocklist, privacy rule, IPC contract — are respected by every proposal and verified by the architecture research. v3.1 engineers in parallel with v3.0's external clock (Apple Dev + SignPath ~1-week SLA); when approvals land, v3.1 feeds straight into the v3.0 SHIP-CUT cookbook.

## Key Findings

### Recommended Stack

v3.1 is **strictly additive on the v3.0 baseline** — no row in the v3.0 stack changes. Net runtime delta: zero. Net dev/CI/test delta: 4 dev-only tools, 5 mascot asset files, and one bundled Win installer payload. See `.planning/research/STACK.md` for the full pin table.

**Core additions:**
- **`uv==0.11.14`** (Apache-2.0/MIT): cross-platform universal Python lockfile — CI fails fast on lock drift via `uv sync --locked`. Dev/CI only.
- **`cyclonedx-python==7.3.0`** (Apache-2.0): CycloneDX SBOM alongside existing syft SPDX. CI only.
- **`tauri-plugin-playwright==0.1.0`** (MIT, dev-dep, gated under `[features] test`): native-webview Playwright bridge for e2e. **0.1.0 maturity flagged for plan-time spike; fallback is `tauri-driver` (pre-alpha) or WebView2-only on Win.**
- **`@playwright/test==1.50.x`** + **`pixelmatch==7.1.0`**: visual-regression assertions with `maxDiffPixelRatio: 0.02`.
- **`pinact` v3.x**: GH Actions SHA pinning.
- **Mixamo + Adobe auto-rigger** (free, royalty-free commercial): production mascot retargeting — already scaffolded at `scripts/mascot/` (Phase 43-05). Rejects Ready Player Me (ARKit blendshape mismatch), Auto-Rig Pro ($40 paid), AccuRIG (FBX/USD only).
- **VB-CABLE NSIS `/S` silent install bundled inside Inno Setup `[Run]` section** (Win only, ~6 MB). EULA-redistribution gate flagged for plan-time legal confirm; fallback Mac-style detect-and-guide.
- **`cargo-deny` `deny.toml`** (already in v3.0 CI): tighten with license allowlist (Apache-2.0/MIT/BSD/ISC/Unicode-DFS-2016/MPL-2.0) + GPL bans.

**Explicit non-additions (REJECTED in opportunity-scan):** Loopback Audio, Dante Via, Soundflower, Pioneer ProDJ Link / cdj-link-py, CLAP/MERT/OpenL3, stem separators, additional LLM providers, `testdriver.ai`, Poetry/Pipenv, Linux support, DAW integration, Mixxx OSC (DEFERRED v3.x), Beat This! Rust crate (DEFERRED v3.x).

### Expected Features

**Must have (table stakes):**
- Signed `.dmg` + signed `.msi`/`.exe` from `releases/latest` (gates on SHIP-01/02 external clock).
- First-launch wizard end-to-end walk: install → probes (BlackHole/VB-CABLE/TCC/MIDI/Bravoh proxy) → session-ready ≤60s.
- BlackHole 2ch auto-detect-and-prompt Mac (Homebrew-first / `.pkg`-fallback) + VB-CABLE auto-prompt Win with forewarning copy.
- Every Python+Rust+Tauri runtime dep pinned in `uv.lock`/`Cargo.lock`/`package-lock.json` with rationale + license + install-impact in `docs/AUDIT.md`.
- 23 mascot GLB clips covering Base(3)+Emotion(5)+Anticipation(5)+Reaction(10), wired to 4-layer state machine across every event class.
- E2E MacBook walk: functional + visual + aesthetic + usability + hallucination dimensions with gap-closure routing.
- Onboarding stopwatch ≤60s validated on SHIP-04 fresh-VM matrix (macOS 12.3/14/15 + Win 10/11).

**Should have (competitive):**
- First-session demo button reusing v3.0 VIS-09 deterministic 30-event sequencer.
- Single-binary universal2 sidecar audited GREEN ("no Python needed" verifiable on fresh VM).
- `AUDIT.md` + CI badges + Dependabot + lockfile-diff bot on PRs.
- License-policy gate via `cargo-deny licenses` allowlist.
- Inline emote-tag vocab integration (gated on v2.1 v2 text-channel-timing spike; defer to v3.2 if spike fails).
- Mascot README hero render alongside locked verbatim hero text.
- OBS browser-source mascot-path callout in README.

**Defer (v3.2+ or v3.x):** `/hatch` user-gen mascot, Mixxx OSC adapter, controller map transpiler, 10→30 controller library, multi-session debrief arc, Beat This! Rust sidecar, `obs-websocket-py` event uplink, external usability testers, A/B onboarding flows, quantified SUS/NASA-TLX metrics.

**Anti-features (REJECTED to preserve clean-utility constraint):** Bundle BlackHole `.pkg` redistribution, auto-update silent installs, Linux/`.deb`/`.AppImage`, macOS App Store distribution, 30-session formal hallucination harness, Snyk/Black Duck enterprise SBOM tooling, vendoring all Python deps.

### Architecture Approach

v3.1 lives at three existing roots — `installer/`, `scripts/release/`, `tauri/ui/assets/mascot/animations/` — plus three new generated/test surfaces (`docs/AUDIT.md`, `docs/dep-opportunities/`, `tests/e2e/macbook/`). **Zero new processes. Zero new IPC messages. Zero changes to the runtime sidecar↔Tauri contract.**

**Major components:**
1. **Installer companion chain** (`installer/companion/fetch_drivers.{sh,ps1}` + `audio_config.py` + `driver_manifest.json` + `onboarding_copy.json`) — post-install driver fetch from official vendor URLs, SHA-256 verified, runs vendor-signed installers; codesigned by Bravoh cert via new `companion-sign` release.yml stage between BUILD and SIGN.
2. **Dep audit surface** (`docs/AUDIT.md` + `scripts/audit/dep_audit.py` + `dep_ratings.json` + `check_audit_freshness.sh` + `.github/workflows/dep-audit.yml`) — generator consumes existing lockfiles, emits committed markdown 3-table; CI freshness gate fails PR if lockfile newer than AUDIT.md.
3. **Dep-opportunity scan** (`docs/dep-opportunities/<UTC>-scan.md` + `scripts/audit/scan_opportunities.py` + ADR sidecar `.planning/decisions/DEP-OPP-<N>-<slug>.md`) — dated discovery artifact, 4-color rubric (Red-constraint/Red-risk/Yellow-defer/Green-adopt), explicit exclusion-set upfront.
4. **E2E MacBook harness** (`tests/e2e/macbook/test_*.py` + `scripts/e2e/run_macbook_pass.sh` + `__snapshots__/` + `docs/e2e/MACBOOK-PASS-PROTOCOL.md` + `scripts/e2e/check_e2e_report.sh`) — installs SHIPPED `.dmg` to `/Applications`, launches with debug logging, runs 4 pytest suites, emits report.html. **Splits into 5a Kaan-aesthetic-ear pass (subjective) + 5b OS-matrix smoke (objective, ≥2 of 5 configs).**
5. **Mascot real-GLB swap** (drop-in at existing `tauri/ui/assets/mascot/animations/prep_*.glb` slot paths) — pure asset operation, zero state-machine code change, 23-clip enumeration anchored to Plutchik 8-primary set adapted for DJ-context, bundle stays within 25 MB Tier-1 cap via draco retune (preferred) or 30 MB cap bump with audit trail (fallback).

**Build order:** Phase A (parallel A1 dep-audit + A2 mascot) → Phase B (opportunity scan) → Phase C (installer) → Phase D (e2e). A2 must precede D for visual snapshots; C must precede D since e2e drives shipped DMG.

### Critical Pitfalls

44 pitfalls catalogued; top 5 by release-blocking impact:

1. **Stale `pip freeze` from Kaan's `.venv` ships as lockfile** — bakes unused transitives (`google-cloud-speech`, `google-cloud-texttospeech`, `openai`) + drifts off v3.0 GATE-02 VCR cassette pin. **Prevention:** lock in clean `python:3.12-slim-bookworm` container; `requirements.in` (curated) vs `requirements.lock` (resolved); `pip-deptree --reverse` prune gate.
2. **Silent BlackHole/VB-CABLE auto-install trips macOS endpoint security / Win driver-signature UAC** — produces "system extension blocked" modal that breaks HARD one-click req. **Prevention:** re-scope to "detect + one-tap fallback"; routing config (Multi-Output Device) is what gets automated, not kernel-mode install; wizard copy anticipates OS modal as expected step; verify BlackHole 48 kHz format post-install per memory `project_v4_canonical_baseline`.
3. **"It works on Kaan's MacBook" trap** — e2e validates only Apple-Silicon Sonoma, ignores macOS 12.3 Intel + Win matrix. **Prevention:** split target feature #4 into #4a Kaan-ear (subjective) + #4b OS-matrix smoke (objective, ≥2 of {12.3 Intel, 14 AS, 15 AS, Win 10, Win 11}); #4b prerequisite for milestone close; commit screencast.
4. **Mascot tests built around `mascot.html` easter egg instead of v3.0 Tauri+Three.js production** — emotion coverage appears green while real surface ships with placeholder GLBs (v0.1.0-rc1 "mascot chrome strip" bug class). **Prevention:** e2e mascot tests target Tauri WebviewWindow only; CI grep gate `! grep -rn "mascot.html" tests/ e2e/ scripts/ci/`; 4-layer × 7-event-type coverage matrix; vitest snapshot on transparent wrapper background.
5. **Anti-slop blocklist false-trips on installer/wizard/dep-audit copy** — 15-token blocklist + `\bdeeply\s+\w+` regex fires on legitimate installer prose; temptation to relax corrodes v3.0 anti-slop thesis. **Prevention:** vocabulary substitution dictionary at `docs/internal/copy-substitutions.md` ("seamless → one-tap", "robust → tested", "leverage → use"); plan-checker pre-commit runs `check_no_slop.py` on every PLAN.md/wizard copy/e2e report; **never** relax the gate.

**Other high-severity:** Dep-opportunity scan recommends Linux-only or multi-provider AI dep (mitigation: scan plan quotes exclusion set verbatim + 4-color rubric with auto-red constraint-violation rule); VB-CABLE EULA bundled-redistribution clause (mitigation: post-install fetch fallback); worktree-isolated subagents start from stale base per memory `feedback_worktree_must_sync_main_first` (mitigation: Step-0 `git merge origin/main` invariant in every subagent prompt).

## Implications for Roadmap

5-phase structure aligned 1:1 with PROJECT.md milestone scope, dependency-aware order:

### Phase 46: Dep Audit + Lockfile + AUDIT.md
**Rationale:** Independent; establishes `scripts/audit/` + `dep_ratings.json` schema that downstream phases append to. Cheapest; warm-up. Parallel with Phase 47.
**Delivers:** `uv.lock` hermetic-container generated; CycloneDX SBOM; `pinact` SHA-pinning; `cargo-deny` license allowlist; `docs/AUDIT.md` 3-table surface; CI freshness gate; dep-cull pass on `livekit-plugins-openai` + `google-cloud-speech` + `google-cloud-texttospeech` if non-transitive; README badges; Dependabot.
**Addresses:** FEATURES Category 2 (DEPS); target feature #2.

### Phase 47: Mascot Real GLB Land + Emotion Coverage Wiring
**Rationale:** Independent; parallel with Phase 46. **Must precede Phase 50** so visual snapshots baseline against real assets. Gated on KAAN-ACTION-LEGAL §VIS-04.
**Delivers:** 23 GLB clips retargeted via existing Phase 43-05 Mixamo+Adobe CLI; MANIFEST emotion-to-event mapping; bundle gate flips exit-2 → exit-0 via draco retune (or 30 MB bump fallback); 30s persona smoke; mascot README hero render.
**Addresses:** FEATURES Category 4 (MASCOT); target feature #5; closes v3.0 §VIS-04 pre-stage.

### Phase 48: Dep-Opportunity Scan
**Rationale:** Depends on Phase 46 `dep_ratings.json` schema. Informs Phase 49 installer.
**Delivers:** `docs/dep-opportunities/2026-05-scan.md` rating v3.x candidates (Mixxx OSC, map transpiler, pyrekordbox depth, DJ-software coverage gaps, hardware controller gaps, OS edge cases); 4-color rubric; exclusion-set upfront; ADRs per green adoption; OBS browser-source docs callout. Likely outcome: zero new runtime deps.
**Addresses:** FEATURES Category 5 (OPPORTUNITY-SCAN); target feature #3.

### Phase 49: One-Click Installer Chain (Win + Mac)
**Rationale:** Depends on Phase 46 + Phase 48. Most expensive; longest tail. Must complete BEFORE Phase 50.
**Delivers:** `installer/companion/fetch_drivers.{sh,ps1}` + `driver_manifest.json` + `audio_config.py`; wizard CTA cards with vendor download links + UAC forewarning; Inno Setup `[Run]` VB-CABLE `/S` (EULA-permitting) or detect-and-guide fallback; Tauri MSI target; uninstall path; a11y pass; SHIP-04 fresh-VM matrix real-run + SHIP-05 ≤60s gate.
**Addresses:** FEATURES Category 1 (INSTALL); target feature #1; closes SHIP-04 + SHIP-05 + AUDIO-07.

### Phase 50: End-to-End MacBook Pass (Split 5a + 5b)
**Rationale:** Last in order. Depends on Phase 47 (real GLBs) + Phase 49 (built DMG). **Must split per Pitfall 3.**
**Delivers (50a Kaan-ear, subjective):** functional flow walk; CDJ Whisper visual + aesthetic re-walk with paired gsd-ui-checker + gsd-ui-auditor; Nielsen 10 heuristic checklist; hallucination gate re-run via `check_gate.sh` Gate 2b; screencast committed; gap-closure routing.
**Delivers (50b OS-matrix, objective):** automated install/launch/first-event/shutdown on ≥2 of {macOS 12.3 Intel, 14 AS, 15 AS, Win 10, Win 11} via existing `tart` matrix; report.html PASS/FAIL per dimension; CI gate via `check_e2e_report.sh` Gate 6b in `cut_release.sh`.
**Addresses:** FEATURES Category 3 (TEST); target feature #4.

### Phase Ordering Rationale
- 46+47 parallel: share zero files; 46 unblocks 48; 47 must precede 50.
- 48 after 46: appends to `dep_ratings.json` schema.
- 49 after 46+48: installer companion pulls only green-rated deps.
- 50 last: validates SHIPPED `.dmg` + real GLBs.
- All five respect: zero new IPC wrappers; POC immutability; ModelRouter seam; anti-slop blocklist (extended grep target paths for 4 new artifact globs); privacy rule (project-scoped FS only).

### Research Flags

**Needs research (plan-time):**
- **Phase 49 (Installer):** `tauri-plugin-playwright==0.1.0` maturity 1-day spike; VB-CABLE EULA legal review; macOS 16 + Win 11 24H2 matrix additions; companion script signing semantics on Win (`.ps1` Authenticode via SignPath).
- **Phase 50 (E2E):** Pixelmatch SSIM threshold calibration on Retina M-series; e2e audio-loopback fixture timing-sensitivity with recorded WAV vs live PIE; macOS 12.3 FileVault edge case in `installer -pkg` flow.
- **Phase 47 (Mascot):** real GLB animation track naming vs placeholder — `pools.ts` may need one-line `clipName` mapping update; inline emote-tag vocab gated on v2.1 v2 Gemini text-channel-timing spike.

**Standard patterns (skip extra research):**
- **Phase 46:** `uv` + `cyclonedx-python` + `pinact` + `cargo-deny` well-documented; HIGH confidence.
- **Phase 48:** constraint enumeration + scan rubric are documentation/process; HIGH confidence on zero-new-runtime-deps outcome.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Direct PyPI/crates.io/official-source verification 2026-05-17. MEDIUM on `tauri-plugin-playwright==0.1.0` (flagged spike). MEDIUM on Mixamo asset selection (Kaan-aesthetic). |
| Features | HIGH | 1:1 mapped to PROJECT.md scope; anchored to shipped v2.1 + v3.0 surfaces. MEDIUM on Windows install-flow (driver-signature prompt OS-mandated, reframed as UX). |
| Architecture | HIGH | Verified against `.planning/codebase/ARCHITECTURE.md`, release.yml, IPC schema, mascot module tree. MEDIUM on new-component placements (first-time integrations, well-sited). LOW on bundled-driver signing semantics (KAAN-ACTION-LEGAL timing). |
| Pitfalls | HIGH | Anchored to v3-shipped P1–P41 + 44 v3.1-specific tripwires with grep-able warning signs. |

**Overall confidence:** HIGH

### Gaps to Address
- **VB-CABLE EULA bundled-redistribution clause** — plan-time legal review; fallback Mac-style detect-and-guide.
- **`tauri-plugin-playwright==0.1.0` production stability** — 1-day spike at Phase 50 plan time; fallback `tauri-driver` or WebView2-only Win e2e + Kaan-manual Mac walk. **Do NOT block v3.1 on this.**
- **macOS 16 release date relative to v3.1 ship** — verify at SHIP-04 real-run time.
- **VIS-04 Adobe-account Mixamo download** — KAAN-ACTION-LEGAL discharge; autonomous mode defers to Kaan-action-required surface but continues unblocked work.
- **`livekit-plugins-openai` cull decision** — verify `uv pip tree` for hard transitive dep.
- **23-clip emotion enumeration vs Mixamo library availability** — Kaan-aesthetic selection has latitude to swap intent labels if needed.
- **Worktree-isolated subagent base-sync invariant** — every Phase 46-50 subagent prompt MUST include Step-0 `git merge origin/main` per memory `feedback_worktree_must_sync_main_first`.

## Sources

### Primary (HIGH)
- `.planning/research/STACK.md` §XI — tool pin verification PyPI/crates.io 2026-05-17.
- `.planning/research/FEATURES.md` — shipped v2.1+v3.0 surfaces; Plutchik 8-primary reference; VTuber expression patterns.
- `.planning/research/ARCHITECTURE.md` §IX — codebase/ARCHITECTURE.md, release.yml, install_vm_matrix, IPC schema, mascot module tree, tauri.conf.json5 bundle-ID lock.
- `.planning/research/PITFALLS.md` — v3-shipped P1–P41 + 44 v3.1-specific.
- PROJECT.md (post-v3.0 close).

### Secondary (MEDIUM)
- v3.0 source-of-truth: release.yml, Cargo.toml, pyproject.toml, installer/windows/vibemix-installer.iss, scripts/dist/install_vm_matrix.{sh,json}, scripts/mascot/check_bundle_size.sh, tauri/ui/src/mascot/state-machine.ts.
- KAAN-ACTION-LEGAL §SHIP-01..13 cookbook 8-block format.
- v3.0 milestone archive (ROADMAP / REQUIREMENTS / MILESTONE-AUDIT).
- Inno Setup silent-install ref; NSIS silent-install ref; BlackHole Wiki; Tauri 2 WebDriver docs; Playwright visual comparison docs; MoCap/Tripo3D Mixamo alternative reviews.

### Tertiary (LOW — plan-time validation)
- `tauri-plugin-playwright==0.1.0` production stability.
- VB-CABLE EULA bundled-redistribution clause (vb-audio.com terms).
- VB-Audio forum UAC + driver-signature dialog suppressability.
- macOS 16 release date vs v3.1 ship.
- Bundled-driver signing semantics on Windows under SignPath OSS Foundation cert.

### Memory anchors (cite in plan-checker)
- `project_one_click_install_hard_req` — green/yellow/red dep rating.
- `feedback_no_clap_use_gemini_embedding` — Gemini-only embedding.
- `feedback_no_scope_creep_clean_utility` — no multi-provider, no stems, no enterprise, no DAW.
- `project_mascot_as_vtuber_personality_surface` — single VTuber 3D char; /hatch v2.x stretch.
- `project_visual_direction_cdj_whisper` — visual baseline.
- `project_v2_open_candidates` — confirmed/deferred/backlog inventory.
- `feedback_autonomous_no_grey_area_pause` — autonomous discharge; Kaan-action carveouts.
- `feedback_privacy_scope_narrow` — narrow rule (LLM-transcript paths only); project FS access fine.
- `feedback_worktree_must_sync_main_first` — Phase 40 worktree-isolation learning.
- `project_phase_16_kaan_dj_testing` — Kaan's DJ ear, not formal suite.
- `project_v4_canonical_baseline` — BlackHole 48 kHz format requirement.
- `project_v0_1_0_rc1_open_bugs` — mascot chrome strip regression class.
- `project_github_star_goal` — 500+ floor.
- `project_anti_slop_grounded_gemini_thesis` — 15-token + `\bdeeply\s+\w+` blocklist; never relax.

---
*Research completed: 2026-05-17*
*Ready for roadmap: yes*
