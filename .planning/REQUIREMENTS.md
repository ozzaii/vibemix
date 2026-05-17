# Requirements — v3.1 Distribution-Ready Pass

**Milestone:** v3.1 Distribution-Ready Pass
**Goal:** Make vibemix install-and-run anywhere — true one-click on Win + Mac with audited/pinned deps and the mascot fully visible across all emotional states — verified by Kaan's end-to-end pass on his MacBook.
**Created:** 2026-05-17
**Status:** Mapped (roadmap scaffolded 2026-05-17)

Categories scoped to the 5 milestone target features:
- **DEPS** — Dependency audit / pin / lockfile / SBOM / license
- **MASCOT** — Real GLB land + full emotion coverage wiring
- **OPP** — New-dep / integration opportunity scan
- **INSTALL** — Win + Mac one-click installer chain
- **E2E** — End-to-end MacBook + OS-matrix pass

REQ-IDs continue alphabetically; numbering restarts per category since these are new categories. Anti-features and out-of-scope items captured at the bottom.

---

## v3.1 Requirements

### DEPS — Dependency Audit + Lockfile + SBOM

- [ ] **DEPS-01** — Python runtime deps regenerated from a curated `requirements.in` into a hermetic `uv.lock` produced inside a clean `python:3.12-slim-bookworm` container (no `pip freeze` from Kaan's local `.venv`).
- [ ] **DEPS-02** — Rust deps pinned in `Cargo.lock` with `cargo-deny` `deny.toml` enforcing license allowlist (Apache-2.0/MIT/BSD/ISC/Unicode-DFS-2016/MPL-2.0) and GPL bans; CI fails the build on policy violation.
- [ ] **DEPS-03** — JS deps pinned in `package-lock.json` (frozen lockfile install in CI); npm-audit signal surfaced as PR comment.
- [ ] **DEPS-04** — `docs/AUDIT.md` ships a 3-table surface (Python / Rust / JS) listing every direct dep + version + license + rationale + install-impact rating (green/yellow/red) per memory `project_one_click_install_hard_req`.
- [ ] **DEPS-05** — CI freshness gate (`scripts/audit/check_audit_freshness.sh` invoked by `.github/workflows/dep-audit.yml`) fails any PR whose lockfile mtime is newer than `docs/AUDIT.md`.
- [ ] **DEPS-06** — CycloneDX SBOM produced via `cyclonedx-python==7.3.0` alongside existing syft SPDX; both SBOMs attached to GH release assets.
- [ ] **DEPS-07** — GitHub Actions SHAs pinned via `pinact` v3.x (no `@vX` floating refs); audit script runs on PR.
- [ ] **DEPS-08** — Dep-cull pass culls or formally re-justifies `livekit-plugins-openai`, `google-cloud-speech`, `google-cloud-texttospeech` (any unused transitive carrying over from `pip freeze`); decision logged in `docs/AUDIT.md`.
- [ ] **DEPS-09** — README dep-health badges (uv lock status / cargo-deny / npm-audit / CycloneDX SBOM) wired to CI status.
- [ ] **DEPS-10** — Dependabot configured for Python (`uv` config) + Cargo + npm + GH Actions with weekly cadence and security-only patch policy.

### MASCOT — Real GLB Land + Full Emotion Coverage

- [ ] **MASCOT-01** — 23 real GLB clips ship at the existing `tauri/ui/assets/mascot/animations/` slot paths: 3 Base (idle / breathe / sway) + 5 Emotion (joy / trust / surprise / anticipation / focus) + 5 Anticipation (prep_kick / prep_breakdown / prep_drop / prep_layer / prep_mix) + 10 Reaction (kick_swap / sub_layer / breakdown / reentry / phrase_boundary / distortion_climb / acid_line / mix_in / mix_out / hype_peak).
- [ ] **MASCOT-02** — Each GLB is Mixamo-retargeted (or equivalent royalty-free auto-rigger output) via the existing `scripts/mascot/` Phase 43-05 CLI; source `.fbx` provenance documented under `assets/mascot/source/` (gitignored) with manifest in-repo.
- [ ] **MASCOT-03** — Bundle gate at `scripts/mascot/check_bundle_size.sh` exits 0 with real GLBs in place — either via draco retune under the existing 25 MB Tier-1 cap (preferred) or a documented 30 MB cap bump with audit-trail rationale.
- [ ] **MASCOT-04** — `tauri/ui/src/mascot/pools.ts` `clipName` mapping updated to address real GLB track names (no placeholder clipName regressions).
- [ ] **MASCOT-05** — The 4-layer additive state machine drives every shipped event class (TRACK_CHANGE / PHASE / LAYER_ARRIVAL / MIX_MOVE / HEARTBEAT / KAAN_SPOKE / MANUAL + Hard Tek detectors) through Base + Emotion + Anticipation + Reaction with priority-stacked crossfades; vitest coverage matrix proves each event hits at least one layer.
- [ ] **MASCOT-06** — A 30-second persona smoke (`scripts/mascot/persona_smoke.sh`) plays each emotion + reaction at least once and emits a screencast committed to `docs/mascot/persona_smoke.webm` (LFS or sized <5 MB).
- [ ] **MASCOT-07** — README hero renders an embedded GLB still (or short loop) alongside the locked-verbatim README hero text; rendered image gated by anti-slop blocklist and does not trip readme-hero-sync CI.
- [ ] **MASCOT-08** — Mascot tests exercise the v3.0 Tauri+Three.js production surface (not the `mascot.html` standalone easter egg); CI grep gate `! grep -rn "mascot.html" tests/ e2e/ scripts/ci/` enforced.

### OPP — New-Dep + Integration Opportunity Scan

- [ ] **OPP-01** — Dated discovery artifact at `docs/dep-opportunities/2026-05-scan.md` lists every candidate evaluated for v3.1 (Mixxx OSC, controller map transpiler, pyrekordbox depth extension, OS-coverage edge cases, hardware-coverage gaps, OBS browser-source mascot path).
- [ ] **OPP-02** — Each candidate rated using a 4-color rubric: Red-constraint (violates project rules like Linux-only or multi-AI), Red-risk (install-impact red), Yellow-defer (good but not v3.1 critical), Green-adopt (lands in v3.1).
- [ ] **OPP-03** — Scan plan quotes the exclusion set verbatim from memory entries (`feedback_no_clap_use_gemini_embedding` / `feedback_no_scope_creep_clean_utility` / `project_one_click_install_hard_req`) and auto-flags any constraint-violating candidate Red.
- [ ] **OPP-04** — For each Green-adopt outcome, an ADR sidecar at `.planning/decisions/DEP-OPP-<N>-<slug>.md` captures decision, rationale, integration plan, and rollback path.
- [ ] **OPP-05** — Final scan outcome documents zero (or near-zero) new runtime deps as the v3.1 expected steady state; deferred candidates (Yellow) carry forward into `.planning/research/v3-buckets/` for v3.x re-evaluation.
- [ ] **OPP-06** — OBS browser-source mascot-path callout shipped in README + `docs/integrations/obs-browser-source.md`, deriving on existing Tauri webview port; no new runtime code required (docs-only adoption).

### INSTALL — Win + Mac One-Click Installer Chain

- [ ] **INSTALL-01** — User on a clean Mac double-clicks `vibemix.dmg`, the app installs, first launch fires a wizard that probes BlackHole 2ch / TCC permissions / MIDI / Bravoh proxy and lands the user at a session-ready state within 60 seconds (per memory `project_one_click_install_hard_req`).
- [ ] **INSTALL-02** — User on a clean Windows box runs `vibemix-installer.exe`, the installer triggers VB-CABLE silent install where EULA permits (Inno Setup `[Run]` with NSIS `/S`) or falls back to detect-and-guide if redistribution is blocked; first launch wizard completes within 60 seconds.
- [ ] **INSTALL-03** — Wizard copy includes forewarning UX for the OS-mandated friction points: Windows driver-signature UAC ("Windows will ask permission to install an audio driver — click Yes"), macOS system-extension approval for BlackHole ("Allow BlackHole in System Settings → Privacy & Security"); zero copy lines trip the anti-slop blocklist.
- [ ] **INSTALL-04** — Companion driver fetch (`installer/companion/fetch_drivers.{sh,ps1}` + `driver_manifest.json`) downloads vendor installers from official URLs, SHA-256 verifies, and runs the vendor-signed installer; offline-installer fallback documented.
- [ ] **INSTALL-05** — Companion scripts are Bravoh-codesigned via a new `companion-sign` release.yml stage between BUILD and SIGN (Authenticode on Win via SignPath, codesign on Mac); release-publish gate verifies signatures.
- [ ] **INSTALL-06** — Tauri MSI target added to release.yml matrix; first-launch onboarding stopwatch fires `INSTALL_READY` event with elapsed wall-clock; CI gate fails if median across SHIP-04 fresh-VM matrix exceeds 60 s.
- [ ] **INSTALL-07** — Uninstall path on both OSes removes app + audio-routing config + caches but preserves user library / debrief data unless explicitly opted into a clean uninstall.
- [ ] **INSTALL-08** — Accessibility pass on the wizard: keyboard nav, screen-reader labels, contrast meets WCAG-AA on every CTA card.
- [ ] **INSTALL-09** — Routing config (Multi-Output Device on Mac, default-device on Win) is the surface that gets automated post-driver-install; kernel-mode install never silenced.
- [ ] **INSTALL-10** — Installer flow validated against memory `project_v4_canonical_baseline` BlackHole 48 kHz format requirement (post-install probe confirms 48 kHz default).

### E2E — End-to-End MacBook + OS-Matrix Pass

- [ ] **E2E-01** — `tests/e2e/macbook/` harness installs the SHIPPED `.dmg` to `/Applications`, launches with debug logging, exercises the live-session golden path, and asserts on a structured `report.html` covering functional + visual + aesthetic + usability dimensions.
- [ ] **E2E-02** — Pass is split into 50a (Kaan-ear, subjective) + 50b (OS-matrix smoke, objective ≥2 of {macOS 12.3 Intel, 14 AS, 15 AS, Win 10, Win 11}); both required for v3.1 close.
- [ ] **E2E-03** — Visual regression via Playwright + pixelmatch with `maxDiffPixelRatio: 0.02`; snapshots stored at `tests/e2e/macbook/__snapshots__/`, baselined on real mascot GLBs (depends on MASCOT-01).
- [ ] **E2E-04** — Audio-loopback fixture validates the sidecar↔BlackHole/VB-CABLE path without re-issuing live Gemini calls (VCR cassette pinned to v3.0 GATE-02 baseline) to avoid burning Gemini quota in CI.
- [ ] **E2E-05** — Hallucination gate re-run via `scripts/eval/check_gate.sh` Gate 2b returns engineering-clean for the v3.1 build before the e2e pass is marked PASS.
- [ ] **E2E-06** — Nielsen 10-heuristic checklist passes on Kaan's MacBook walk (50a) with paired `gsd-ui-checker` + `gsd-ui-auditor` zero HIGH findings on Tier-1 surfaces.
- [ ] **E2E-07** — Screencast of Kaan's 50a walk committed to `docs/e2e/2026-05-walk.webm` (sized < 25 MB or LFS).
- [ ] **E2E-08** — `cut_release.sh` Gate 6b (`scripts/e2e/check_e2e_report.sh`) blocks release publish if any dimension reports FAIL in the latest `dist/e2e-macbook-runs/<UTC>/report.html`.
- [ ] **E2E-09** — E2e harness explicitly forbidden from writing to off-limits paths (`~/.hermes/`, `~/hermes-rig/logs/`, `~/.lmstudio/`) per memory `feedback_privacy_scope_narrow`; pytest fixture asserts this on every test run.
- [ ] **E2E-10** — Anti-slop blocklist runs against every produced e2e report.html title/section to keep generated prose constraint-aligned.

---

## Future Requirements (Deferred to v3.2+)

- Linux distribution (`.deb` / `.AppImage`) — deliberate out-of-scope per project constraints; community-PR-only.
- Auto-update silent installs — release-cycle decision after v3.1 ships.
- Multi-session debrief arc — defer per scope guardrails.
- Mixxx OSC controller adapter — Yellow-defer outcome of OPP scan unless OPP-02 surfaces it as Green.
- Controller map transpiler — same.
- 10 → 30 controller library expansion — defer.
- `obs-websocket-py` event uplink — docs-only in v3.1 (OPP-06); code adoption defers to v3.x.
- `/hatch` user-generated mascot — v2.x stretch per memory `project_mascot_as_vtuber_personality_surface`.
- Inline emote-tag vocab integration in TTS — gated on v2.1 v2 Gemini text-channel-timing spike; ship if green, defer otherwise.
- Beat This! Rust sidecar (BPM verifier) — Yellow-defer.
- Quantified SUS / NASA-TLX usability metrics — out-of-scope for v3.1 (Kaan-ear gates instead).
- 30-session formal hallucination harness — explicitly NOT v3.1 per memory `project_phase_16_kaan_dj_testing`.

## Out of Scope (Hard Exclusions)

- **No CLAP / MERT / OpenL3** — memory `feedback_no_clap_use_gemini_embedding`; Gemini Embedding 2 only.
- **No new AI providers** — memory `feedback_no_scope_creep_clean_utility`; Gemini-only.
- **No stem separation features** — same memory.
- **No enterprise SBOM vendoring** (Snyk, Black Duck) — open-source tooling sufficient.
- **No bundled BlackHole `.pkg` redistribution** — license clarity; macOS uses Homebrew-first / detect-and-guide.
- **No App Store distribution** — out of scope for v3.1.
- **No POC file edits** — `cohost*.py` POCs are reference-only per memory `feedback_poc_is_reference` / `project_v4_canonical_baseline`.
- **No new IPC wrappers** — 38-wrapper schema frozen; 3-IPC-reservation contract preserved.
- **No new model literals** — ModelRouter seam enforced by existing CI grep gate.
- **No anti-slop gate relaxation** — 15-token + `\bdeeply\s+\w+` regex blocklist remains absolute.

---

## Traceability

**Coverage: 44 / 44 v3.1 REQ-IDs mapped ✓ (no orphans, no duplicates).**

| REQ-ID | Phase | Status | Verification |
|--------|-------|--------|--------------|
| DEPS-01 | Phase 46 — Dependency Audit + Lockfile + AUDIT.md | not started | hermetic `uv sync --locked` in `python:3.12-slim-bookworm` container; CI green |
| DEPS-02 | Phase 46 | not started | `cargo-deny check` green with license allowlist + GPL ban |
| DEPS-03 | Phase 46 | not started | frozen lockfile install in CI; npm-audit PR comment |
| DEPS-04 | Phase 46 | not started | `docs/AUDIT.md` 3-table surface present with rating column |
| DEPS-05 | Phase 46 | not started | `scripts/audit/check_audit_freshness.sh` fails PR with stale AUDIT.md |
| DEPS-06 | Phase 46 | not started | CycloneDX + SPDX SBOMs both on GH release assets |
| DEPS-07 | Phase 46 | not started | `pinact` audit shows all GH Actions SHA-pinned |
| DEPS-08 | Phase 46 | not started | dep-cull decision in `docs/AUDIT.md` § Decisions |
| DEPS-09 | Phase 46 | not started | 4 dep-health badges live in README + CI status wired |
| DEPS-10 | Phase 46 | not started | Dependabot weekly-cadence config for 4 ecosystems |
| MASCOT-01 | Phase 47 — Mascot Real GLB Land + Full Emotion Coverage | not started | 23 real GLBs at enumerated slot paths; file-size band 400 KB – 1200 KB per clip |
| MASCOT-02 | Phase 47 | not started | Mixamo provenance manifest in-repo; `.fbx` sources gitignored |
| MASCOT-03 | Phase 47 | not started | `scripts/mascot/check_bundle_size.sh` Tier-1 exit 0 with real GLBs |
| MASCOT-04 | Phase 47 | not started | `pools.ts` `clipName` mapping no placeholder regressions |
| MASCOT-05 | Phase 47 | not started | 4-layer × 7-event vitest coverage matrix green |
| MASCOT-06 | Phase 47 | not started | `persona_smoke.sh` + `docs/mascot/persona_smoke.webm` committed |
| MASCOT-07 | Phase 47 | not started | README hero GLB render passes `check_readme_hero_lock.py` |
| MASCOT-08 | Phase 47 | not started | CI grep gate `! grep -rn "mascot.html" tests/ e2e/ scripts/ci/` green |
| OPP-01 | Phase 48 — New-Dep + Integration Opportunity Scan | not started | `docs/dep-opportunities/2026-05-scan.md` exists with candidate inventory |
| OPP-02 | Phase 48 | not started | 4-color rubric applied to every candidate |
| OPP-03 | Phase 48 | not started | exclusion set quoted verbatim; constraint-violators auto-Red |
| OPP-04 | Phase 48 | not started | ADR sidecar `.planning/decisions/DEP-OPP-<N>-<slug>.md` per Green adoption |
| OPP-05 | Phase 48 | not started | zero (or near-zero) new runtime deps documented; Yellow → v3-buckets/ |
| OPP-06 | Phase 48 | not started | OBS browser-source mascot path docs-only in README + `docs/integrations/obs-browser-source.md` |
| INSTALL-01 | Phase 49 — Win + Mac One-Click Installer Chain | not started | clean Mac DMG → wizard → ≤60s session-ready (fresh-VM matrix) |
| INSTALL-02 | Phase 49 | not started | clean Win EXE → wizard → ≤60s session-ready (fresh-VM matrix) |
| INSTALL-03 | Phase 49 | not started | OS-mandated friction forewarning UX; anti-slop blocklist green |
| INSTALL-04 | Phase 49 | not started | `fetch_drivers.{sh,ps1}` + `driver_manifest.json` SHA-256 verified |
| INSTALL-05 | Phase 49 | not started | `companion-sign` release.yml stage between BUILD + SIGN; verifier gate |
| INSTALL-06 | Phase 49 | not started | Tauri MSI target + `INSTALL_READY` stopwatch + 60s CI gate |
| INSTALL-07 | Phase 49 | not started | uninstall path preserves user library / debrief unless clean-uninstall opt-in |
| INSTALL-08 | Phase 49 | not started | wizard a11y green (keyboard / screen-reader / WCAG-AA) |
| INSTALL-09 | Phase 49 | not started | routing config (Multi-Output Device / Win default-device) automated; kernel-mode install never silenced |
| INSTALL-10 | Phase 49 | not started | BlackHole 48 kHz post-install probe green per memory `project_v4_canonical_baseline` |
| E2E-01 | Phase 50 — End-to-End MacBook + OS-Matrix Pass | not started | `tests/e2e/macbook/` harness installs SHIPPED `.dmg`; `report.html` produced |
| E2E-02 | Phase 50 | not started | 50a Kaan-ear + 50b OS-matrix smoke (≥2/5 configs) both required for milestone close |
| E2E-03 | Phase 50 | not started | Playwright + pixelmatch `maxDiffPixelRatio: 0.02` on real GLB baselines |
| E2E-04 | Phase 50 | not started | audio-loopback fixture VCR cassette (v3.0 GATE-02 pinned, zero live Gemini) |
| E2E-05 | Phase 50 | not started | `check_gate.sh` Gate 2b green before pass marked PASS |
| E2E-06 | Phase 50 | not started | Nielsen 10 + paired gsd-ui-checker + gsd-ui-auditor zero HIGH on Tier-1 |
| E2E-07 | Phase 50 | not started | `docs/e2e/2026-05-walk.webm` committed (LFS or <25 MB) |
| E2E-08 | Phase 50 | not started | `cut_release.sh` Gate 6b blocks publish on FAIL dimension |
| E2E-09 | Phase 50 | not started | pytest fixture asserts zero writes to off-limits paths per memory `feedback_privacy_scope_narrow` |
| E2E-10 | Phase 50 | not started | anti-slop blocklist green on every `report.html` |

### Build-order dependencies (from ROADMAP.md)

- Phases 46 + 47 run in PARALLEL (zero shared files).
- Phase 48 depends on Phase 46 (`dep_ratings.json` schema).
- Phase 49 depends on Phase 46 + Phase 48 (companion pulls only Green-rated deps).
- Phase 50 depends on Phase 47 (real GLBs for visual snapshots) + Phase 49 (built signed `.dmg`).

### Soft Kaan-discharge gates (autonomous mode continues; KAAN-ACTION-LEGAL surface)

- **§VIS-04** (Phase 47) — Mixamo Adobe-account walk for 23 retargeted clips. Engineering ships placeholders + CLI scaffold; Kaan discharges asset selection.
- **§INSTALL-COMPANION-SIGN** (Phase 49) — companion driver Authenticode on Win via SignPath OSS Foundation cert (same cert v3.0 SHIP-CUT awaits). Engineering ships release.yml stage + verifier; Kaan discharges at SignPath approval time.
- **§INSTALL-VM-RUN** (Phase 49 / Phase 50) — fresh-VM matrix real execution. Engineering ships `install_vm_matrix.sh --check-60s`; Kaan discharges real-VM rehearsal.
- **§E2E-50A-WALK** (Phase 50) — Kaan's MacBook walk per memory `project_phase_16_kaan_dj_testing`. Engineering ships harness + report.html scaffolding; Kaan discharges walk + screencast.

---
*Last updated: 2026-05-17 — traceability filled in by `gsd-roadmapper`. 44 / 44 REQ-IDs mapped to 5 phases (P46–P50). Roadmap at `.planning/ROADMAP.md`.*
