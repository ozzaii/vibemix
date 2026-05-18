---
gsd_state_version: 1.0
milestone: v3.1
milestone_name: Distribution-Ready Pass
status: "Phase 49 (INSTALL) engineering-green; Phase 50 (E2E) ready to dispatch"
last_updated: "2026-05-18T13:00:00.000Z"
last_activity: 2026-05-18 — Phase 49 (Win+Mac One-Click Installer Chain) engineering-green; 6/6 plans + VERIFICATION.md + REVIEW.md (clean) + UI-REVIEW.md (3.67/4) committed; 10/10 INSTALL REQ-IDs covered; 68 tests pass; companion-sign workflow + verifier + Inno Setup [Run]+[Code]+[UninstallRun] + DMG firstrun hook + 60s simulated gate (median 41 000ms) + anti-slop sibling + uninstall preserve-default; Phase 50 (E2E) unblocked
progress:
  total_phases: 5
  completed_phases: 4
  total_plans: 26
  completed_plans: 26
  percent: 80
---

# vibemix — State

**Last updated:** 2026-05-17 — v3.1 "Distribution-Ready Pass" roadmap scaffolded via `gsd-roadmapper`. 5 phases (P46–P50), 44 v3.1 REQ-IDs mapped 100%, next: `/gsd:plan-phase 46` to kick off engineering. Engineering proceeds in PARALLEL with v3.0 external clock (Apple Dev + SignPath ~1-week SLA) — does NOT wait for SHIP-CUT.

---

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-17 after v3.0 milestone close)

- **Project:** vibemix — open-source AI DJ co-host (Bravoh's first OSS release)
- **Core value:** "Real DJ friend in your ear" — never hallucinating, never breaking flow, never AI slop.
- **Current focus:** v3.1 Distribution-Ready Pass — one-click install Win+Mac + dep audit/pin + new-dep opportunity scan + e2e MacBook pass + mascot real GLBs.
- **Last shipped:** v3.0 Clean OSS Ship — 2026-05-17 (status: `tech_debt` accepted; awaiting external clock for public RC publish).
- **Project mode:** standard.
- **Granularity:** fine.
- **Model profile:** quality (all agents on Opus, all checkpoints on).
- **Autonomy mode:** `gsd-autonomous fully` — every blocker + human-needed item discharged autonomously, only privacy rule + destructive risk + legal-capacity carveouts (Apple Dev Agreement + SignPath OSS) still pause. Soft Kaan-discharge gates (§VIS-04 Mixamo retargets, companion-driver signing) surface to KAAN-ACTION-LEGAL but do NOT pause work.

---

## Current Position

**Milestone:** v3.1 Distribution-Ready Pass
**Next Phase:** Phase 50 — End-to-End MacBook + OS-Matrix Pass (E2E)
**Plan:** —
**Status:** Phase 49 engineering-green (6/6 plans); Phase 50 (E2E) ready to dispatch
**Last activity:** 2026-05-18 — Phase 49 complete; 6 plans + VERIFICATION + REVIEW (clean) + UI-REVIEW (3.67/4) committed; all INSTALL-01..10 engineering-green; 68 tests pass; companion-sign workflow + verifier + Inno Setup integration; Phase 50 unblocked

**v3.1 Progress:**

```
Phases:  4 / 5    ████████████████░░░░  80%
Plans:  26 / TBD  ████████░░░░░░░░░░░░  (P46: 6 + P47: 8 + P48: 6 + P49: 6 plans)
```

## Performance Metrics

| Metric | Value |
|--------|-------|
| Phases complete (v0.1.0) | 14 / 14 |
| Phases complete (v2.0) | 10 / 12 code-shipped (2 deferred to Kaan-action) |
| Phases complete (v2.1) | 13 / 13 engineering-green (4 carry `human_needed` carveouts: Phase 33 / 35 / 38 / 39) |
| Phases complete (v3.0) | 6 / 6 engineering-green (all 6 carry `human_needed` verification carveouts → KAAN-ACTION-LEGAL §SHIP-01..13) |
| Phases complete (v3.1) | 4 / 5 |
| Plans complete (v3.0) | 41 / 41 |
| Plans complete (v3.1) | 26 / TBD |
| v3.0 REQ-IDs mapped + satisfied | 57 / 57 ✓ (100% coverage, no orphans) |
| v3.1 REQ-IDs mapped | 44 / 44 ✓ (100% coverage, no orphans) |
| v3.0 cross-phase integration seams WIRED | 3 / 3 |
| v3.0 commits since `v2.1.0` tag | 250 |
| v3.0 LOC delta | +62,215 / -1,029 across 529 files (net ~+61k) |
| v3.0 git tag | `v3.0` (annotated, LOCAL ONLY — not pushed) |
| v3.0 carveouts deferred to KAAN-ACTION-LEGAL | 22 (legal capacity P46 × 2 + customer-facing publish × 8 + real-hardware × 3 + real-asset × 1 + corpus × 4 + spike × 1 + sign-off × 2 + visual-regression-test × 1) |

---

## Accumulated Context

### Phase 49 Outcome (2026-05-18, engineering-green)

v3.1 one-click installer chain landed engineering-green. All 10 INSTALL REQ-IDs covered across 6 plans. 68 tests pass. Headline artifacts:

- **`installer/companion/`** — `fetch_drivers.{sh,ps1}` + `driver_manifest.json` (SHA-256 placeholder pending §INSTALL-COMPANION-SIGN discharge) + `audio_config.py` (Mac CoreAudio + Win WASAPI 48 kHz probe + Multi-Output Device / default-playback routing) + `onboarding_copy.json` (single source-of-truth for wizard strings) + `uninstall.{sh,ps1}` (preserve-default + --clean opt-in)
- **`.github/workflows/companion-sign.yml`** — new parallel signing stage with Mac codesign + Win SignPath submission scaffold + cross-runner verifier gate
- **`scripts/audit/check_companion_signing.sh`** — tag-vs-branch fail-mode verifier; PLACEHOLDER_ SHA-256 emits §INSTALL-COMPANION-SIGN warning
- **Inno Setup integration** — `installer/windows/vibemix-installer.iss` extended with [Files] companion bundle + [Run] fetch_drivers.ps1 invocation + [UninstallRun] preserve-default + [Code] VB-CABLE license dialog gating InitializeSetup
- **DMG first-launch hook** — `installer/macos/firstrun_companion.sh` (Mac DMG cannot legally bundle BlackHole .pkg; deferred to first launch)
- **Tauri commands** — `tauri/src-tauri/src/wizard_cmds.rs` exposes `run_companion_fetch` + `run_audio_config` + `open_audio_settings`; `capabilities/default.json` `shell:allow-execute` extended (ZERO new permission identifier)
- **Wizard 3 new steps** — `step-forewarning.ts` (OS forewarning), `step-driver-fetch.ts` (companion orchestration + INSTALL_READY emit), `step-48k-probe.ts` (48 kHz format probe + fix-it CTA); all read from `copy.ts` typed loader; zero inline strings + zero hex literals gated by tests
- **Uninstall dialog** — `uninstall-dialog.ts` with preserve-default + clean opt-in checkbox + destructive border-color tint
- **VM matrix gate** — `scripts/dist/install_vm_matrix.sh --simulate --check-60s` produces synthetic run.json from `simulated_runs` stubs; `scripts/dist/check_60s_gate.py` computes median + p95; median across 5 SHIP-04 rows = 41 000 ms (well under 60 000 ms budget)
- **Anti-slop sibling** — `scripts/audit/check_no_slop_install.py` imports `AI_SLOP_BLOCKLIST` from `scripts/launch/check_no_ai_slop.py` (parent unchanged per sibling-pattern invariant); clean across 10 Phase 49 targets; `docs/internal/copy-substitutions.md` documents 20+ forbidden tokens

**Code review:** status `clean` — 0 critical, 2 warnings (pre-existing cargo build issue + audio_config regex parse fragility), 4 info findings (all Phase 50 polish, none block closure).

**UI review:** 3.67 / 4 overall — Visual Hierarchy 4/4, Color/Contrast 4/4, Typography 4/4, Motion 3/4 (stopwatch tween should extract to tokens.css), Copy 4/4, A11y 3/4 (focus trap on uninstall dialog deferred to Phase 50).

**Kaan-action surface (deferred):**
1. §INSTALL-COMPANION-SIGN — SignPath OSS Foundation cert grant
2. §INSTALL-VM-RUN — real Tart VM rehearsal on SHIP-04 5-row matrix
3. §SHIP-CONTACT-VBAUDIO — Kaan emails VB-Audio for OEM redistribution permission (future optimization)

### Phase 48 Outcome (2026-05-18, engineering-green)

v3.1 opportunity scan landed via `docs/dep-opportunities/2026-05-scan.md` with 24 candidates under the 4-color rubric. Headline:

| Bucket | Count | Surface |
|---|---|---|
| Green-adopt | 1 | docs-only (OBS browser-source via existing Tauri webview port 8765 + mascot bus) |
| Yellow-defer | 8 | `.planning/research/v3-buckets/v3.x-*.md` stubs |
| Red-constraint | 9 | none (CLAP / MERT / OpenL3 / OpenAI / Anthropic / Demucs / Spleeter / DAW APIs / Linux-only) |
| Red-risk | 6 | none (ProDJ Link / cdj-link-py / Dante Via / Loopback Audio / Soundflower / Auto-Rig Pro) |

**Net runtime-dep delta for v3.1: 0.** Phase 49 installer companion reads `scripts/audit/dep_ratings.yaml::opportunity_evaluations` to confirm OBS is docs-only (negative confirmation); positive companion pins (BlackHole + VB-CABLE) stay Phase 49 internal. No Kaan-action surface from Phase 48.

### Phase 47 Kaan-Action Surface (2026-05-18, deferred per `gsd-autonomous fully` mode)

One engineering-green-with-deferral item from Phase 47 — does NOT block Phase 48 (OPP) or any other v3.1 phase. Phase 50 visual-snapshot tests will hit the placeholder GLBs gracefully until discharge.

- **§VIS-04: 28 Mixamo Adobe-account retargets deferred to Kaan-action**. Engineering ships the full scaffold: 28-slot retarget CLI (`scripts/mascot/retarget_to_neon_rebel.py` — 5 families × per-family size bands), `assets/mascot/source/MANIFEST.yaml` audit-trail schema (28 placeholder rows), `MIXAMO-CLIP-SOURCES.md` with 18 new selection-guidance rows + per-family aesthetic guardrails (Pioneer-CDJ headbob; hands near body; static-foot-grounded; ~120 BPM equivalent), 23 placeholder GLBs at `tauri/ui/assets/mascot/animations/` (44 KB stubs aliasing prep_settle.glb), `docs/mascot/BUNDLE-DECISION.md` documenting draco-first / 30 MB bump-fallback. Bundle gate at `scripts/mascot/check_bundle_size.sh` exits 2 (Tier 2 placeholder fail) by design — `continue-on-error: true` in `mascot-audit.yml` until discharge. **To close**: (1) Mixamo Adobe-account walk per `scripts/mascot/MIXAMO-CLIP-SOURCES.md`; (2) `~/Downloads/mixamo_<slot>.glb` per slot; (3) `uv run python scripts/mascot/retarget_to_neon_rebel.py --slot-family <family> --really` per family; (4) `bash scripts/mascot/render_readme_hero.sh` regenerates README hero PNG+WebM after `react_hype_peak.glb` ships real Mixamo content. Bundle gate flips to exit 0 on full discharge.

### Phase 46 Kaan-Action Surface (2026-05-18, deferred per `gsd-autonomous fully` mode)

Two engineering-green-with-deferral items from Phase 46 — neither blocks Phase 47 (MASCOT) or Phase 48 (dep-opportunity scan); both are documented in `docs/AUDIT.md` § Decisions and `scripts/audit/dep_ratings.yaml::decisions[]` for the long-lived paper trail.

- **DEPS-07: pinact mechanical `--apply` deferred to CI**. `.pinact.yaml` + `scripts/audit/run_pinact.sh` + `dep-audit.yml::pinact-audit` job committed; mechanical SHA-pin rewrite of `.github/workflows/*.yml` deferred to first PR-triggered run (no pinact binary on local executor; no Go toolchain to bootstrap). Test `test_every_uses_is_sha_pinned` marked `xfail` with `strict=False` so future apply-pass that flips it green does not surprise-fail. **To close**: `brew install pinact && bash scripts/audit/run_pinact.sh --apply` then review + commit the SHA-churn diff, OR let the first CI PR surface the exact tag refs needing rewrite.

- **DEPS-08: `livekit-plugins-openai` cull is CULL-BLOCKED**. `rg` found direct imports at `src/vibemix/agent/tts_chain.py:25` (`from livekit.plugins.openai import tts as _openai_tts_mod`) plus 3 test files (`tests/agent/test_proxy_client.py`, `tests/agent/test_config.py`, `tests/agent/test_tts_chain.py`). Removal requires rewiring the TTS proxy fallback chain — explicitly out-of-scope for Phase 46. `google-cloud-speech` + `google-cloud-texttospeech` are pure transitives of livekit-plugins-google with zero direct imports; retained-as-transitive (no Kaan-action needed there). **To close `livekit-plugins-openai`**: open a focused refactor phase post-v3.1 that rewires `tts_chain.py` to drop the OpenAI adapter path.

### v3.1 Roadmap Decisions Locked (2026-05-17)

- **5-phase decomposition P46–P50** with build-order: parallel cluster (46 + 47) → sequential cluster (48 → 49 → 50). Phase 46 + 47 share zero files. Phase 48 gated on Phase 46 `dep_ratings.json` schema. Phase 49 gated on Phase 46 + Phase 48 (companion pulls Green-rated deps only). Phase 50 gated on Phase 47 (real GLBs for visual snapshots) + Phase 49 (built signed `.dmg`).
- **Phase numbering CONTINUED** from v3.0 — v3.0 closed at Phase 45. v3.1 starts at Phase 46 (no `--reset-phase-numbers` semantics).
- **Five v3.0 invariants preserved** in every v3.1 phase: POC immutability (`cohost*.py`, `mascot.html` byte-identical to v2.0 tag), ModelRouter seam (zero new hardcoded model literals; CI grep gate extended to v3.1 artifacts), anti-slop blocklist (15-token + `\bdeeply\s+\w+` regex; grep target paths extended to `docs/AUDIT.md`, `docs/dep-opportunities/`, installer wizard copy, e2e report.html), privacy rule (project-scoped FS only; e2e harness asserts zero writes to off-limits paths per `feedback_privacy_scope_narrow`), 3-IPC-reservation contract (zero new IPC wrappers; v3.1 is build-time / test-harness / asset-only).
- **`gsd-autonomous fully` mode applied** — engineering proceeds unblocked in PARALLEL with v3.0 external clock (Apple Dev + SignPath ~1-week SLA). Soft Kaan-discharge gates surface to KAAN-ACTION-LEGAL but do NOT pause work: §VIS-04 Mixamo Adobe-account walk (Phase 47) ships placeholders + scaffolds; §INSTALL-COMPANION-SIGN companion-driver Authenticode (Phase 49) ships `companion-sign` release.yml stage + verifier, awaits same SignPath OSS Foundation cert v3.0 SHIP-CUT awaits.
- **Worktree-subagent Step-0 invariant** mandated for every Phase 46–50 plan per memory `feedback_worktree_must_sync_main_first` — every subagent prompt skeleton MUST include `git fetch origin main && git merge origin/main --no-edit` Step-0 block. Plan-checker rejects any plan lacking this. (Phase 40 worktree-isolation learning: stale base = ~161k-line regression on merge.)
- **Phase 50 split: 50a Kaan-ear (subjective) + 50b OS-matrix smoke (objective)** per memory `project_phase_16_kaan_dj_testing` — NOT a formal 30-session replay harness; Kaan walks his MacBook with real DJ-set audio. 50b automates ≥ 2 of {macOS 12.3 Intel, 14 AS, 15 AS, Win 10, Win 11}.
- **Mascot scope locked to single VTuber character (Neon Rebel)** per memory `project_mascot_as_vtuber_personality_surface` — `/hatch` user-gen pipeline is v2.x stretch, NOT v3.1.
- **No CLAP / no multi-provider AI** per memory `feedback_no_clap_use_gemini_embedding` + `feedback_no_scope_creep_clean_utility` — Phase 48 opportunity scan auto-flags any constraint-violating candidate Red.
- **BlackHole 48 kHz format requirement** per memory `project_v4_canonical_baseline` — Phase 49 post-install probe confirms default at INSTALL-10.
- **One-click install ≤ 60s ceiling** per memory `project_one_click_install_hard_req` — Phase 49 INSTALL-06 wires `INSTALL_READY` event with elapsed wall-clock; CI gate fails if median exceeds 60s on SHIP-04 fresh-VM matrix; driver install step lands INSIDE the envelope via parallelized driver pull during app extract, NOT by ceiling expansion.

### Decisions Locked (v3.0 — shipped, see v3.0-ROADMAP.md for full list)

All Phase 40–45 decisions remain locked. Highlights:

- Mic-as-Part-2 + lookahead-as-Part-3 closes "AI invents what Kaan said" + "AI reacts after the moment passed" hallucination classes (Phase 40).
- ModelRouter config-driven seam with zero hardcoded model literals + ServiceTier.FLEX on batch paths + STANDARD pinned to live coach (Phase 41).
- Hybrid hallucination gate: autonomous proxy fast-lane (PR + 7 nightly canary) + Kaan-ear release-cut veto via `check_gate.sh` Gate 2b; P85 Phase 16 ear-test override formally retired (Phase 42).
- CDJ Whisper visual lock: Tier-1 surfaces zero HIGH findings; hardware-LED-strip meter rebuild; 22-site `--glow-faint` hover-glow sweep (Phase 43).
- README hero "the only AI co-host that actually listens to your set" verbatim lock + EvidenceRegistry citation strip in live UI + Bravoh waitlist toggle default-OFF UTM-tracked (Phase 44).
- KAAN-ACTION-LEGAL §SHIP-01..13 discharge cookbook ships 13 runbooks in canonical 8-block format; `audit_ship_v1_decision.py` (610 lines) pre-fills 4/5 rubric cells from GH releases + Bravoh healthz + ear-test logs + GH issues at T+30 (Phase 45).

### Decisions Locked (v0.1.0 + v2.0 + v2.1 — see prior STATE.md history)

All Phase 1–39 decisions remain locked. Highlights preserved:

- 3-process architecture (Tauri shell + Python sidecar + FastAPI proxy on `api.altidus.world`).
- Bundle ID `world.bravoh.vibemix` LOCKED (Pitfall P63) — Phase 33-07 CI grep enforces.
- AIza leak gate held: 0 / 482 files match at v2.0 close + 0 new bytes in v2.1 + 0 new bytes in v3.0 (gitleaks Phase 34-01).
- macOS 12.3+ / Windows 10/11. Linux excluded.
- Apache 2.0 + DCO license; signing via Apple Developer ID + SignPath OSS.
- Gemini-only AI (no Anthropic / OpenAI / Ollama / CLAP / OpenL3 / MERT / sentence-transformers / torch).
- Three.js (single 3D engine); vanilla TS in `tauri/ui/src/` (NOT React); WaveSurfer.js for Phase 29 debrief timeline.
- POC files BYTE-IDENTICAL to v2.0 tag — `cohost*.py`, `mascot.html`, `cohost.streaming.py.bak`; Phase 37-06 immutability gate enforces.

### Deferred Items (v3.0 close — 2026-05-17, carry forward to v3.1)

Acknowledged per `gsd-autonomous fully` mode at v3.0 milestone close 2026-05-17. v3.1 closes some of these as pre-stage discharges complete (especially AUDIO-07 BlackHole probe via Phase 49 wizard, VIS-04 Mixamo retargets via Phase 47, INSTALL-VM-RUN / INSTALL-60S-CHECK via Phase 49 + Phase 50).

| Category | Item | Status at v3.1 start |
|----------|------|----------------------|
| verification_gap | 40-VERIFICATION.md (AUDIO-05 PGP + AUDIO-06 Tauri key + AUDIO-07 BlackHole probe + ear-test) | human_needed; AUDIO-07 closes via Phase 49 wizard |
| verification_gap | 41-VERIFICATION.md (TTFT p95 ear-test + LAT-09 spike + FLEX live-billing) | human_needed |
| verification_gap | 42-VERIFICATION.md (ACK-BANK-REMAINING-20 + EVAL-VCR-CASSETTES + EVAL-CORPUS-WAVS + ear-test logs) | human_needed |
| verification_gap | 43-VERIFICATION.md (§VIS-04 Mixamo retargets + capture day) | human_needed; §VIS-04 closes via Phase 47 |
| verification_gap | 44-VERIFICATION.md (6+10 logo swaps + bravoh GH org standup + SHIP-TWEET sign-off + Discord live-execute) | human_needed |
| verification_gap | 45-VERIFICATION.md (Apple Dev + SignPath + Bravoh-server + SHIP-CUT/TWEET/DISCORD/TRANSFER/ROTATE + SmartScreen + SHIP-V1-DECISION) | human_needed; external clock |

### v3.1 Anticipated Kaan-Action Surface (will route to KAAN-ACTION-LEGAL during execution)

- **§VIS-04** (Phase 47) — Mixamo Adobe-account walk: download 23 retargeted clips from Mixamo + Kaan-aesthetic selection. Engineering ships scaffolds + placeholders; Kaan discharges asset selection.
- **§INSTALL-COMPANION-SIGN** (Phase 49) — companion driver Authenticode signing on Win via SignPath OSS Foundation cert (same cert v3.0 SHIP-CUT awaits). Engineering ships `companion-sign` release.yml stage + verifier; Kaan discharges at SignPath approval time.
- **§INSTALL-VM-RUN** (Phase 49 / Phase 50) — fresh-VM matrix real execution on Kaan's hardware. Engineering ships `install_vm_matrix.sh --check-60s` harness; Kaan discharges real-VM rehearsal.
- **§E2E-50A-WALK** (Phase 50) — Kaan's real-MacBook walk per memory `project_phase_16_kaan_dj_testing`. Engineering ships harness + report.html scaffolding; Kaan discharges the walk + screencast.

### Blockers

- **None engineering-side at v3.1 start.** All 5 phases parallelize around the v3.0 external clock.
- **External clock (v3.0 carryover, does NOT block v3.1):** Apple Developer Program Agreement update (Francesco, P46 legal-capacity) + SignPath OSS Foundation approval (Kaan, ~1-week SLA, P46 legal-capacity). When approvals land, the SignPath cert also satisfies Phase 49 §INSTALL-COMPANION-SIGN.

### Risks (v3.1 top 5 pitfalls — to mitigate during plan-time)

1. **Stale `pip freeze` from Kaan's `.venv` ships as lockfile** (Phase 46) — bakes unused transitives, drifts off v3.0 GATE-02 VCR cassette pin. Mitigation: hermetic `python:3.12-slim-bookworm` container regen + `pip-deptree --reverse` prune gate.
2. **Silent BlackHole / VB-CABLE auto-install trips macOS endpoint security / Win driver-signature UAC** (Phase 49) — produces "system extension blocked" modal that breaks one-click req. Mitigation: re-scope to "detect + one-tap fallback"; routing config (Multi-Output Device) is what gets automated, not kernel-mode install; wizard copy anticipates OS modal as expected step.
3. **"It works on Kaan's MacBook" trap** (Phase 50) — e2e validates only Apple-Silicon Sonoma, ignores macOS 12.3 Intel + Win matrix. Mitigation: split 50a Kaan-ear + 50b OS-matrix smoke (objective, ≥ 2 of 5 configs); 50b prerequisite for milestone close.
4. **Mascot tests built around `mascot.html` easter egg instead of v3.0 Tauri+Three.js production** (Phase 47) — emotion coverage appears green while real surface ships with placeholder GLBs (v0.1.0-rc1 "mascot chrome strip" bug class). Mitigation: e2e mascot tests target Tauri WebviewWindow only; CI grep gate `! grep -rn "mascot.html" tests/ e2e/ scripts/ci/`.
5. **Anti-slop blocklist false-trips on installer / wizard / dep-audit copy** (Phases 46 / 48 / 49 / 50) — temptation to relax corrodes v3.0 anti-slop thesis. Mitigation: vocabulary substitution dictionary at `docs/internal/copy-substitutions.md` ("seamless → one-tap", "robust → tested", "leverage → use"); NEVER relax the gate.

---

## Session Continuity

### Last Session

- 2026-05-17 — v3.1 "Distribution-Ready Pass" roadmap scaffolded via `gsd-roadmapper` under `gsd-autonomous fully` mode. 5 phases (P46–P50) derived from 44 v3.1 REQ-IDs (DEPS × 10 / MASCOT × 8 / OPP × 6 / INSTALL × 10 / E2E × 10) with 100% coverage. Build-order locked: 46 ↕ 47 parallel → 48 (gated on 46) → 49 (gated on 46 + 48) → 50 (gated on 47 + 49). Five v3.0 invariants preserved (POC immutability + ModelRouter seam + anti-slop blocklist + privacy rule + 3-IPC contract). Soft Kaan-discharge gates (§VIS-04 + §INSTALL-COMPANION-SIGN) routed to KAAN-ACTION-LEGAL but do NOT pause work. STATE.md reset to v3.1 counters. REQUIREMENTS.md traceability confirmed against intended phase mapping.
- 2026-05-17 — Plan 45-02 + Plan 45-04 + Plan 43-08 + Plan 43-07 + Plan 42-04 + Plan 42-03 sealed; v2.1 The Unified Cut SHIPPED + archived; v3.0 Clean OSS Ship SHIPPED + archived (see prior STATE.md history blocks in v3.0-ROADMAP.md for detail).

### Next Session

- **`/gsd:plan-phase 46`** to decompose Phase 46 Dependency Audit + Lockfile + AUDIT.md into plans. Independent — runs in parallel with Phase 47 planning if Kaan wants concurrent kickoff.
- **`/gsd:plan-phase 47`** can run in parallel — Mascot Real GLB Land + Full Emotion Coverage. Shares zero files with Phase 46. Soft §VIS-04 Kaan-discharge surface noted; engineering proceeds with scaffolds.
- **Phase 48 / 49 / 50 plan kickoff** deferred until Phase 46 (dep_ratings.json schema) lands; Phase 49 additionally waits for Phase 48 scan output; Phase 50 waits for Phase 47 GLBs + Phase 49 signed `.dmg`.
- **Track external clock**: Apple Developer Program Agreement update (Francesco) + SignPath OSS Foundation application (Kaan) discharge gates v3.0 SHIP-CUT — v3.1 does NOT wait. When approvals land, SignPath cert simultaneously unlocks Phase 49 §INSTALL-COMPANION-SIGN.
- **Soft Kaan-discharge gates to surface in KAAN-ACTION-LEGAL during execution**: §VIS-04 Mixamo retargets (Phase 47), §INSTALL-COMPANION-SIGN companion-driver Authenticode (Phase 49), §INSTALL-VM-RUN fresh-VM rehearsal (Phase 49 / 50), §E2E-50A-WALK Kaan's MacBook walk (Phase 50).

---

*State managed by gsd-roadmapper at 2026-05-17 (v3.1 "Distribution-Ready Pass" scaffolded; engineering ready to begin Phase 46 + Phase 47 in parallel).*
