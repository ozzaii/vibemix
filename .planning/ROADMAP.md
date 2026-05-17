# vibemix — Roadmap

**Project:** vibemix — AI DJ Co-Host
**Last shipped:** v3.0 Clean OSS Ship — 2026-05-17 (status: `tech_debt` accepted — KAAN-ACTION-LEGAL §SHIP-01..13 pending external clock for public RC publish)
**Current milestone:** 🚧 v3.1 Distribution-Ready Pass — Phases 46–50

---

## Milestones

- ✅ **v0.1.0 MVP Foundation** — Phases 1–14 (shipped 2026-05-13) — see `.planning/milestones/v0.1.0/`
- ✅ **v2.0 Research-Driven Ship** — Phases 15–26 (shipped 2026-05-14, tech_debt accepted) — see `.planning/milestones/v2.0-ROADMAP.md`
- ✅ **v2.1 The Unified Cut** — Phases 27–39 (shipped 2026-05-16, tech_debt accepted) — see `.planning/milestones/v2.1-ROADMAP.md`
- ✅ **v3.0 Clean OSS Ship** — Phases 40–45 (shipped 2026-05-17, tech_debt accepted) — see `.planning/milestones/v3.0-ROADMAP.md`
- 🚧 **v3.1 Distribution-Ready Pass** — Phases 46–50 (planning, started 2026-05-17)

---

## 🚧 v3.1 Distribution-Ready Pass (In Progress)

**Milestone Goal:** Make vibemix install-and-run anywhere — true one-click on Win + Mac with audited/pinned deps and the mascot fully visible across all emotional states — verified by Kaan's end-to-end pass on his MacBook.

**Mode:** `gsd-autonomous fully` — engineering proceeds unblocked alongside the v3.0 external clock (Apple Dev + SignPath approvals). Soft Kaan-discharge gates (§VIS-04 Mixamo retargets, companion-driver signing via SignPath) surface to KAAN-ACTION-LEGAL but do NOT pause work; placeholders / pre-stage scaffolds ship engineering-green; final discharge required before milestone close.

**Granularity:** fine. **Coverage:** 44 / 44 v3.1 REQ-IDs mapped ✓ (no orphans, no duplicates).

**Build order:**
- **Phase 46 ↕ Phase 47 run in parallel** (share zero files; 46 unblocks 48, 47 must precede 50).
- **Phase 48 depends on Phase 46** (`dep_ratings.json` schema established by 46 is appended-to in 48).
- **Phase 49 depends on Phase 46 + Phase 48** (installer companion pulls only green-rated deps; opportunity scan informs which integrations land).
- **Phase 50 depends on Phase 47 + Phase 49** (real GLBs for visual snapshots; built DMG to drive e2e).
- All five preserve the v3.0 invariants (POC immutability, ModelRouter seam, anti-slop blocklist, privacy rule, IPC contract).

### Phases

- [ ] **Phase 46: Dependency Audit + Lockfile + AUDIT.md** — Pin every Python+Rust+JS dep with rationale + license + install-impact rating; CycloneDX SBOM; CI freshness gate; dep-cull pass.
- [ ] **Phase 47: Mascot Real GLB Land + Full Emotion Coverage** — 23 real GLB clips (3 Base + 5 Emotion + 5 Anticipation + 10 Reaction) wired to 4-layer additive state machine across every event class.
- [ ] **Phase 48: New-Dep + Integration Opportunity Scan** — Dated discovery artifact rating v3.x candidates with 4-color rubric (Red-constraint / Red-risk / Yellow-defer / Green-adopt); ADR sidecars per green adoption.
- [ ] **Phase 49: Win + Mac One-Click Installer Chain** — Signed `.dmg` + signed `.msi`/`.exe`; companion driver fetch chain; first-launch wizard ≤60s on fresh-VM matrix; uninstall path; a11y pass.
- [ ] **Phase 50: End-to-End MacBook + OS-Matrix Pass** — Split 50a Kaan-ear (subjective) + 50b OS-matrix smoke (objective, ≥2 of 5 configs); visual regression on real GLBs; report.html gates SHIP-CUT.

### Phase Details

#### Phase 46: Dependency Audit + Lockfile + AUDIT.md

**Goal**: Every Python + Rust + JS runtime + dev dep pinned hermetically with rationale + license + green/yellow/red install-impact rating per memory `project_one_click_install_hard_req`; CycloneDX SBOM joins existing syft SPDX; dep-cull removes unused transitives carried over from `pip freeze`; CI freshness gate enforces AUDIT.md ↔ lockfile parity.

**Depends on**: v3.0 shipped (Phases 40–45 baseline); existing `python-cve.yml` + `rust-cve.yml` + `sbom.yml` workflows; existing `cargo-deny` config.
**Requirements**: DEPS-01, DEPS-02, DEPS-03, DEPS-04, DEPS-05, DEPS-06, DEPS-07, DEPS-08, DEPS-09, DEPS-10
**Invariants touched**: ModelRouter seam (AUDIT.md MUST NOT inline `gemini-*` literals) · Anti-slop blocklist (extend grep target paths to include `docs/AUDIT.md` and dep-audit generator output) · Privacy rule (audit script writes only to `docs/AUDIT.md` + `scripts/audit/` + `dep_ratings.json`; never to off-limits paths)

**Success Criteria** (what must be TRUE):
  1. Fresh clone + `uv sync --locked` succeeds inside a `python:3.12-slim-bookworm` container with zero drift warnings (DEPS-01 hermetic lockfile contract holds).
  2. CI shows green `cargo-deny check` with license allowlist (Apache-2.0/MIT/BSD/ISC/Unicode-DFS-2016/MPL-2.0) and explicit GPL ban policy enforced (DEPS-02).
  3. `docs/AUDIT.md` renders a 3-table surface (Python / Rust / JS) where every direct dep carries version + license + rationale + green/yellow/red install-impact rating per memory `project_one_click_install_hard_req`; a fresh PR that bumps a lockfile without touching AUDIT.md fails `scripts/audit/check_audit_freshness.sh` (DEPS-04, DEPS-05).
  4. GH release assets contain BOTH CycloneDX `vibemix.cdx.json` and syft SPDX `vibemix.spdx.json` SBOMs; `pinact` v3.x audit reports all GitHub Actions referenced via SHA pin (zero `@vX` floating refs) (DEPS-06, DEPS-07).
  5. Dep-cull decision logged in `docs/AUDIT.md` § Decisions — `livekit-plugins-openai`, `google-cloud-speech`, `google-cloud-texttospeech` either removed or formally re-justified with a transitive-pin paper trail; README dep-health badges (uv / cargo-deny / npm-audit / CycloneDX) wired to CI status; Dependabot configured for all 4 ecosystems with weekly cadence (DEPS-08, DEPS-09, DEPS-10).

**Plans**: TBD

#### Phase 47: Mascot Real GLB Land + Full Emotion Coverage

**Goal**: Swap the 5 placeholder `prep_*.glb` clips for 23 real Mixamo-retargeted GLBs (3 Base + 5 Emotion + 5 Anticipation + 10 Reaction) per memory `project_mascot_as_vtuber_personality_surface`, drive every shipped event class through the v2.1 4-layer additive state machine, and close v3.0 §VIS-04 pre-stage. Single VTuber-style 3D character (Neon Rebel) — no `/hatch` user-gen surface in this phase.

**Depends on**: v3.0 Phase 43-05 Mixamo+Adobe CLI scaffold; v2.1 Phase 31 4-layer state machine.
**Requirements**: MASCOT-01, MASCOT-02, MASCOT-03, MASCOT-04, MASCOT-05, MASCOT-06, MASCOT-07, MASCOT-08
**Invariants touched**: POC immutability (`mascot.html` stays byte-identical; tests target the Tauri+Three.js production surface only, NOT the easter-egg standalone) · Anti-slop blocklist (README hero mascot render copy passes the existing gate; extend grep target to mascot manifest rationales) · Bundle ceiling (25 MB Tier-1 cap preserved via draco retune; documented 30 MB bump only as fallback with audit-trail rationale)
**Kaan-action surface (autonomous mode continues; discharge required before milestone close)**: KAAN-ACTION-LEGAL §VIS-04 Mixamo Adobe-account walk — engineering ships scaffolds + placeholders + CLI; Kaan downloads + selects retargets at discharge time.

**Success Criteria** (what must be TRUE):
  1. `tauri/ui/assets/mascot/animations/` contains 23 real (non-placeholder) GLB clips at the enumerated slot paths (3 Base: idle / breathe / sway · 5 Emotion: joy / trust / surprise / anticipation / focus · 5 Anticipation: prep_kick / prep_breakdown / prep_drop / prep_layer / prep_mix · 10 Reaction: kick_swap / sub_layer / breakdown / reentry / phrase_boundary / distortion_climb / acid_line / mix_in / mix_out / hype_peak); placeholder file-size band (~50 KB) replaced with retargeted band (400 KB – 1200 KB per clip) (MASCOT-01, MASCOT-02).
  2. `scripts/mascot/check_bundle_size.sh` Tier-1 exits 0 with real GLBs in place (combined bundle ≤ 25 MB via draco retune, OR documented 30 MB cap bump with audit trail) — visible signal that v3.0 §VIS-04 pre-stage is discharged (MASCOT-03).
  3. `tauri/ui/src/mascot/pools.ts` `clipName` mapping addresses the real GLB animation track names (no placeholder-name regressions); 4-layer × 7-event-type vitest coverage matrix proves every shipped event class (TRACK_CHANGE / PHASE / LAYER_ARRIVAL / MIX_MOVE / HEARTBEAT / KAAN_SPOKE / MANUAL + Hard Tek detectors) hits at least one of Base / Emotion / Anticipation / Reaction with priority-stacked crossfades (MASCOT-04, MASCOT-05).
  4. 30-second persona smoke (`scripts/mascot/persona_smoke.sh`) plays each emotion + reaction at least once; screencast committed to `docs/mascot/persona_smoke.webm` (LFS or sized < 5 MB); README hero renders an embedded GLB still alongside the locked-verbatim hero text and passes both `check_readme_hero_lock.py` and `readme-hero-sync.yml` (MASCOT-06, MASCOT-07).
  5. CI grep gate `! grep -rn "mascot.html" tests/ e2e/ scripts/ci/` returns zero matches — closes Pitfall 4 (mascot tests built around easter-egg HTML instead of v3.0 Tauri+Three.js production surface) per `project_v0_1_0_rc1_open_bugs` regression class (MASCOT-08).

**Plans**: TBD
**UI hint**: yes

#### Phase 48: New-Dep + Integration Opportunity Scan

**Goal**: Surface every candidate dep / integration evaluated for v3.1 (Mixxx OSC, controller map transpiler, pyrekordbox depth, OS-coverage edge cases, hardware-coverage gaps, OBS browser-source mascot path) on a dated discovery artifact; rate each with the 4-color rubric (Red-constraint / Red-risk / Yellow-defer / Green-adopt); auto-flag any constraint-violator Red against the memory-enumerated exclusion set; emit ADR sidecars per green adoption; produce the v3.1 expected-steady-state of zero (or near-zero) new runtime deps.

**Depends on**: Phase 46 (`dep_ratings.json` schema established by 46; opportunity scan appends candidate evaluations to the same shape).
**Requirements**: OPP-01, OPP-02, OPP-03, OPP-04, OPP-05, OPP-06
**Invariants touched**: Anti-slop blocklist (scan rationale prose passes the 15-token + `\bdeeply\s+\w+` gate; extend grep target paths to `docs/dep-opportunities/`) · ModelRouter seam (scan output MUST NOT inline `gemini-*` literals; rejected candidates that violate Gemini-only constraint flagged Red per memory `feedback_no_clap_use_gemini_embedding`) · POC immutability (scan recommendations land at build-time / test-time / docs-only surfaces; zero runtime POC edits) · `feedback_no_scope_creep_clean_utility` upheld by auto-Red on stem separation / CLAP / multi-provider AI / DAW candidates.

**Success Criteria** (what must be TRUE):
  1. `docs/dep-opportunities/2026-05-scan.md` exists with every candidate evaluated rated under the 4-color rubric; scan plan quotes the exclusion set verbatim from memory entries (`feedback_no_clap_use_gemini_embedding`, `feedback_no_scope_creep_clean_utility`, `project_one_click_install_hard_req`); `scripts/audit/scan_opportunities.py` auto-flags any candidate that names CLAP / MERT / OpenL3 / a non-Gemini provider / stem-sep / DAW as Red-constraint (OPP-01, OPP-02, OPP-03).
  2. Every Green-adopt outcome carries an ADR sidecar at `.planning/decisions/DEP-OPP-<N>-<slug>.md` capturing decision + rationale + integration plan + rollback path; ADR existence verified by CI from the scan markdown front-matter (OPP-04).
  3. v3.1 final scan outcome documents zero (or near-zero per CONTEXT `feedback_no_scope_creep_clean_utility`) new runtime deps; Yellow-defer candidates carried forward into `.planning/research/v3-buckets/` for v3.x re-evaluation (OPP-05).
  4. OBS browser-source mascot path lands in README + `docs/integrations/obs-browser-source.md` as docs-only adoption (Tauri webview WS port 8765 already serves; zero new runtime code); README cross-link verified by CI (OPP-06).
  5. `dep_ratings.json` schema established in Phase 46 extended with `opportunity_evaluations` block; downstream Phase 49 installer companion fetches drivers from the Green-rated subset ONLY (auditable trail from rating → install-time fetch).

**Plans**: TBD

#### Phase 49: Win + Mac One-Click Installer Chain

**Goal**: Single-action installer on both platforms — user double-clicks `vibemix.dmg` (Mac) or runs `vibemix-installer.exe` (Win) and lands at a session-ready state within 60 seconds per memory `project_one_click_install_hard_req`. Post-install companion fetches BlackHole / VB-CABLE from official sources (license-clean, signed), runs vendor installers, configures audio routing, verifies BlackHole 48 kHz format per memory `project_v4_canonical_baseline`. OS-mandated friction points (Win driver-signature UAC + Mac BlackHole system-extension approval) reframed as forewarning UX, NOT engineering-suppressed. Closes v3.0 SHIP-04 + SHIP-05 + AUDIO-07 pre-stage.

**Depends on**: Phase 46 (lockfile + AUDIT.md cite vendor versions) + Phase 48 (companion pulls only Green-rated deps).
**Requirements**: INSTALL-01, INSTALL-02, INSTALL-03, INSTALL-04, INSTALL-05, INSTALL-06, INSTALL-07, INSTALL-08, INSTALL-09, INSTALL-10
**Invariants touched**: Bundle ceiling (companion driver fetch is post-install, OUT of the 350 MB app bundle) · Bundle ID `world.bravoh.vibemix` (companion script spawns under same bundle ID; TCC permissions wizard unchanged) · Anti-slop blocklist (every wizard string + UAC forewarning copy passes the 15-token gate; vocabulary substitution dictionary at `docs/internal/copy-substitutions.md` for "seamless → one-tap" etc., NEVER relax the gate) · Bravoh-proxy-only key custody (companion + audio_config NEVER inline AIza pattern; Pitfall-7 scan stays at zero matches) · Onboarding 60s ceiling (driver install step lands INSIDE the envelope via parallelized driver pull during app extract, NOT by expanding the ceiling).
**Kaan-action surface (autonomous mode continues; discharge required before milestone close)**: KAAN-ACTION-LEGAL §INSTALL-COMPANION-SIGN — companion driver script Authenticode signing on Win via SignPath (same OSS Foundation cert v3.0 SHIP-CUT awaits); engineering ships the `companion-sign` release.yml stage scaffold + verifier; Kaan discharges the actual cert at SignPath approval time.

**Success Criteria** (what must be TRUE):
  1. Clean macOS double-clicks `vibemix.dmg` → app installs → first-launch wizard probes BlackHole 2ch / TCC / MIDI / Bravoh proxy → session-ready in ≤ 60s median across SHIP-04 fresh-VM matrix (macOS 12.3 Intel / 14 AS / 15 AS); post-install probe confirms BlackHole 48 kHz default per memory `project_v4_canonical_baseline` (INSTALL-01, INSTALL-06, INSTALL-10).
  2. Clean Windows runs `vibemix-installer.exe` → Inno Setup `[Run]` invokes VB-CABLE NSIS `/S` (EULA-permitting) OR falls back to detect-and-guide if redistribution is blocked → first-launch wizard completes in ≤ 60s median across Win 10 / 11 fresh-VM rows; Tauri MSI target wired into `release.yml` matrix (INSTALL-02, INSTALL-06).
  3. Wizard copy forewarns OS-mandated friction (Win driver-signature UAC: "Windows will ask permission to install an audio driver — click Yes" · macOS BlackHole system-extension approval: "Allow BlackHole in System Settings → Privacy & Security"); every wizard string + dep-audit summary + onboarding card passes the anti-slop blocklist (`scripts/launch/check_no_ai_slop.py`) including the new artifact paths (INSTALL-03).
  4. `installer/companion/fetch_drivers.{sh,ps1}` downloads vendor installers from official URLs (existential.audio for BlackHole, vb-audio.com for VB-CABLE), SHA-256 verifies against `driver_manifest.json`, runs vendor-signed installers; companion scripts themselves Bravoh-codesigned via new `companion-sign` release.yml stage between BUILD and SIGN (Authenticode on Win via SignPath, codesign on Mac); release-publish gate verifies signatures; offline-installer fallback documented (INSTALL-04, INSTALL-05).
  5. Uninstall path on both OSes removes app + audio-routing config + caches but preserves user library / debrief data unless explicitly opted into clean uninstall; routing config (Multi-Output Device on Mac, default-device on Win) is what gets automated post-driver-install — kernel-mode install never silenced; a11y pass on the wizard (keyboard nav + screen-reader labels + WCAG-AA contrast on every CTA card) green (INSTALL-07, INSTALL-08, INSTALL-09).

**Plans**: TBD
**UI hint**: yes

#### Phase 50: End-to-End MacBook + OS-Matrix Pass

**Goal**: Validate the SHIPPED `.dmg` end-to-end across functional + visual + aesthetic + usability + hallucination dimensions, with the pass deliberately split per Pitfall 3: **50a Kaan-ear (subjective)** = Kaan's MacBook walk with real DJ-set audio per memory `project_phase_16_kaan_dj_testing` (NOT a formal 30-session replay harness); **50b OS-matrix smoke (objective)** = automated install / launch / first-event / shutdown on ≥ 2 of {macOS 12.3 Intel, 14 AS, 15 AS, Win 10, Win 11}. Both required for v3.1 close. Closes v3.0 INSTALL-VM-RUN gap and confirms zero regression of the v3.0 engineering surface.

**Depends on**: Phase 47 (real GLBs for visual snapshots) + Phase 49 (built signed `.dmg` to drive the e2e harness).
**Requirements**: E2E-01, E2E-02, E2E-03, E2E-04, E2E-05, E2E-06, E2E-07, E2E-08, E2E-09, E2E-10
**Invariants touched**: Privacy rule (e2e harness output lands in `dist/e2e-macbook-runs/` project-scoped ONLY; pytest fixture asserts zero writes to `~/.hermes/`, `~/hermes-rig/logs/`, `~/.lmstudio/` per memory `feedback_privacy_scope_narrow`) · Anti-slop blocklist (every produced `report.html` title / section passes the 15-token gate; extend grep target paths to e2e report artifacts) · POC immutability (e2e exercises the v3.0 Tauri+Three.js production surface; `mascot.html` standalone NEVER referenced in e2e tests) · IPC schema parity (e2e exercises BOTH WebviewWindow surfaces but introduces zero new IPC messages) · ModelRouter seam (audio-loopback fixture pins to VCR cassette baseline, NEVER inlines `gemini-*` literals).

**Success Criteria** (what must be TRUE):
  1. `tests/e2e/macbook/` harness installs the SHIPPED `.dmg` to `/Applications`, launches with debug logging, exercises the live-session golden path, and asserts on a structured `dist/e2e-macbook-runs/<UTC>/report.html` covering functional + visual + aesthetic + usability dimensions; 50a / 50b split enforced; both required for v3.1 close (E2E-01, E2E-02).
  2. Visual regression via Playwright + pixelmatch with `maxDiffPixelRatio: 0.02` baselines against the real mascot GLBs from Phase 47 (depends on MASCOT-01); snapshots stored at `tests/e2e/macbook/__snapshots__/`; audio-loopback fixture validates the sidecar ↔ BlackHole / VB-CABLE path against a VCR cassette pinned to v3.0 GATE-02 baseline (no live Gemini calls, zero CI quota burn) (E2E-03, E2E-04).
  3. Hallucination gate re-run via `scripts/eval/check_gate.sh` Gate 2b returns engineering-clean for the v3.1 build before pass is marked PASS; Nielsen 10-heuristic checklist passes on Kaan's 50a walk with paired `gsd-ui-checker` + `gsd-ui-auditor` zero HIGH findings on Tier-1 surfaces; screencast of 50a committed to `docs/e2e/2026-05-walk.webm` (LFS or < 25 MB) (E2E-05, E2E-06, E2E-07).
  4. `cut_release.sh` Gate 6b (`scripts/e2e/check_e2e_report.sh`) blocks release publish if any dimension reports FAIL in the latest `dist/e2e-macbook-runs/<UTC>/report.html`; gate wires in alongside the existing Gate 2b hallucination gate without duplicating its logic (E2E-08).
  5. Pytest fixture `tests/e2e/macbook/conftest.py::test_no_off_limits_write` asserts the e2e harness writes ZERO files under `~/.hermes/`, `~/hermes-rig/logs/`, `~/.lmstudio/` per memory `feedback_privacy_scope_narrow`; every produced `report.html` passes the anti-slop blocklist (`check_no_ai_slop.py` extended grep target) (E2E-09, E2E-10).

**Plans**: TBD
**UI hint**: yes

### Worktree-Subagent Invariant (applies to every Phase 46–50 plan)

Per memory `feedback_worktree_must_sync_main_first` (Phase 40 worktree-isolation learning), every subagent prompt spawned under Phases 46–50 MUST include the Step-0 invariant:

```
Step 0: cd <worktree> && git fetch origin main && git merge origin/main --no-edit
Verify: git rev-parse origin/main == merge-base with HEAD
```

Without this, worktrees created from a stale base produce ~161k-line regressions on merge (the v3.0 Phase 40 baseline). Plan-checker rejects any Phase 46–50 plan whose subagent prompt skeleton lacks the Step-0 block.

---

## Progress

**Execution Order:**
Phases 46–50 execute in numeric order with the build-order parallelism noted above: 46 ↕ 47 parallel → 48 (gated on 46) → 49 (gated on 46 + 48) → 50 (gated on 47 + 49).

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 46. Dependency Audit + Lockfile + AUDIT.md | v3.1 | 0/TBD | Not started | - |
| 47. Mascot Real GLB Land + Full Emotion Coverage | v3.1 | 0/TBD | Not started | - |
| 48. New-Dep + Integration Opportunity Scan | v3.1 | 0/TBD | Not started | - |
| 49. Win + Mac One-Click Installer Chain | v3.1 | 0/TBD | Not started | - |
| 50. End-to-End MacBook + OS-Matrix Pass | v3.1 | 0/TBD | Not started | - |

---

## Phase History (Archived)

<details>
<summary>✅ v0.1.0 MVP Foundation (Phases 1–14) — SHIPPED 2026-05-13</summary>

See `.planning/milestones/v0.1.0/` for full archive.

</details>

<details>
<summary>✅ v2.0 Research-Driven Ship (Phases 15–26) — SHIPPED 2026-05-14 (tech_debt accepted)</summary>

12 phases shipped — 10 Claude-side end-to-end + 2 deferred to Kaan-action (Phase 15 Plan 04 UAT + entire Phase 16 ear-test gate). 38 plans, 1961 passing tests, 220 commits since `v0.1.0-rc1`, ~45.7k LOC across `src/vibemix/`, `tauri/`, `scripts/`, `tests/`.

Full archive: `.planning/milestones/v2.0-ROADMAP.md` · Requirements: `.planning/milestones/v2.0-REQUIREMENTS.md` · Audit: `.planning/milestones/v2.0-MILESTONE-AUDIT.md`

</details>

<details>
<summary>✅ v2.1 The Unified Cut (Phases 27–39) — SHIPPED 2026-05-16 (tech_debt accepted)</summary>

13 phases shipped engineering-green under `gsd-autonomous fully` mode. 96 plans, 633 phase-scope tests added, 225 commits since `v2.0` tag, net ~+45k LOC across `src/vibemix/`, `tauri/`, `scripts/`, `tests/`, `docs/`, `eval/`. 105 / 105 v2.1 REQ-IDs engineering-satisfied. All 5 cross-phase integration seams audited WIRED.

- [x] Phase 27: Eval Harness + v2.0 Carry-Forward Close-Out (9/9 plans, 140 tests) — completed 2026-05-15
- [x] Phase 28: Library Intelligence v1 (9/9 plans, 258 tests) — completed 2026-05-15
- [x] Phase 29: Post-Session Debrief MVP UI (9/9 plans) — completed 2026-05-15
- [x] Phase 30: 2 Hard Tek Detectors (4/4 plans, 45 tests) — completed 2026-05-15
- [x] Phase 31: 4-Layer Mascot Full Additive State Machine (8/8 plans, 17 mascot tests, GLB 21.67/25 MB) — completed 2026-05-15
- [x] Phase 32: Long-Term DJ Profile ~2KB JSON (6/6 plans, 67 tests, P51/P53/P60 enforced) — completed 2026-05-15
- [x] Phase 33: One-Click Install Hardening (9/9 plans, 50 tests; INSTALL-VM-RUN = KAAN-ACTION-LEGAL) — completed 2026-05-15
- [x] Phase 34: Open-Source Security Pass (10/10 plans, 63 tests) — completed 2026-05-15
- [x] Phase 35: Real GLBs + 30s Viral Demo Film (6/6 plans, 35 tests; real assets = KAAN-ACTION-LEGAL) — completed 2026-05-15
- [x] Phase 36: Day-Zero Operations Automation (6/6 plans, 36 tests; 6 real-execution items = KAAN-ACTION-LEGAL) — completed 2026-05-15
- [x] Phase 37: Cross-Phase Integration Audit Gate (6/6 plans, 42 tests; 5/5 seams WIRED) — completed 2026-05-15
- [x] Phase 38: Signing Pipeline Real Execution (6/6 plans, 58 tests; DIST-09 + DIST-11 = P46 legal-capacity carveouts) — completed 2026-05-15
- [x] Phase 39: Public RC Cut + Ship (8/8 plans, 91 tests; §SHIP × 6 + §POST-RC-CLEANUP × 3 = KAAN-ACTION-LEGAL) — completed 2026-05-16

Full archive: `.planning/milestones/v2.1-ROADMAP.md` · Requirements: `.planning/milestones/v2.1-REQUIREMENTS.md` · Audit: `.planning/milestones/v2.1-MILESTONE-AUDIT.md`

</details>

<details>
<summary>✅ v3.0 Clean OSS Ship (Phases 40–45) — SHIPPED 2026-05-17 (tech_debt accepted)</summary>

6 phases shipped engineering-green under `gsd-autonomous fully` mode. 41 plans, 250 commits since `v2.1.0` tag, net ~+61k LOC across `src/vibemix/`, `tauri/`, `scripts/`, `tests/`, `docs/`, `eval/`. 57 / 57 v3.0 REQ-IDs engineering-satisfied. All 3 integration seams + 5 flows audited.

- [x] Phase 40: Anti-Slop Audio Port (6/6 plans) — completed 2026-05-16 (AUDIO-01..04 GREEN; AUDIO-05/06/07 = KAAN-ACTION-LEGAL)
- [x] Phase 41: Gemini SKU Upgrade + Latency Stack v2 (7/7 plans) — completed 2026-05-16 (LAT-01..08 GREEN; LAT-09 spike = KAAN-ACTION-PROXY)
- [x] Phase 42: Hallucination Gate v3 — Hybrid (6/6 plans) — completed 2026-05-16 (GATE-05..09 GREEN; GATE-01/02/03/04 corpus = KAAN-ACTION-LEGAL)
- [x] Phase 43: Visual Ship Lock (9/9 plans) — completed 2026-05-16 (VIS-01..09 GREEN; VIS-04 Mixamo retargets = KAAN-ACTION-LEGAL)
- [x] Phase 44: Launch Positioning + Pre-stage (7/7 plans) — completed 2026-05-17 (LAUNCH-01..10 GREEN; LAUNCH-03/04/06/07/08 = KAAN-ACTION-LEGAL)
- [x] Phase 45: External Discharge + Public RC Publish (6/6 plans) — completed 2026-05-17 (SHIP-08/11/13 engineering GREEN; SHIP-01..13 cookbook in KAAN-ACTION-LEGAL)

**Critical path at close:** External clock — Apple Dev Agreement (Francesco, P46) + SignPath OSS Foundation (Kaan, ~1-week SLA, P46) gate the public RC publish. After approvals land, SHIP-CUT v3.0.0-rc1 is one-button via the §SHIP-01..13 discharge cookbook (45-06). **v3.1 engineers in PARALLEL with this external clock — it does not wait for SHIP-CUT.**

Full archive: `.planning/milestones/v3.0-ROADMAP.md` · Requirements: `.planning/milestones/v3.0-REQUIREMENTS.md` · Audit: `.planning/milestones/v3.0-MILESTONE-AUDIT.md`

</details>

---

## Milestone-Level Progress

| Milestone | Phases | Status | Shipped |
|-----------|--------|--------|---------|
| v0.1.0 MVP Foundation | 1–14 | ✅ Shipped | 2026-05-13 |
| v2.0 Research-Driven Ship | 15–26 | ✅ Shipped (tech_debt) | 2026-05-14 |
| v2.1 The Unified Cut | 27–39 | ✅ Shipped (tech_debt) | 2026-05-16 |
| v3.0 Clean OSS Ship | 40–45 | ✅ Shipped (tech_debt) | 2026-05-17 |
| v3.1 Distribution-Ready Pass | 46–50 | 🚧 Planning | - |

---

*Roadmap updated 2026-05-17 via `gsd-roadmapper` — v3.1 "Distribution-Ready Pass" scaffolded under `gsd-autonomous fully` mode. 5 phases derived from 44 v3.1 REQ-IDs (DEPS × 10 / MASCOT × 8 / OPP × 6 / INSTALL × 10 / E2E × 10) with 100% coverage. Engineering proceeds in parallel with the v3.0 external clock (Apple Dev + SignPath); soft Kaan-discharge gates surface to KAAN-ACTION-LEGAL but do not pause work.*
