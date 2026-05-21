---
gsd_state_version: 1.0
milestone: v4.0
milestone_name: SHIP
status: executing
last_updated: "2026-05-21T09:20:00.000Z"
last_activity: 2026-05-21 -- Phase 55 (Feedback Mode + Citation Integrity) COMPLETE (3/3 plans; full suite 3821 passed; verify human_needed 8/8 engineering must-haves; review 0 critical, WR-01+IN-01 fixed). Live coach ear-pass + citation-strip drive = KAAN-ACTION. Next: plan + execute Phase 56
progress:
  total_phases: 8
  completed_phases: 5
  total_plans: 19
  completed_plans: 16
  percent: 62
---

# vibemix — State

**Last updated:** 2026-05-21 — **Phase 55 (Feedback Mode Live + Citation Integrity) COMPLETE** (3/3 plans; full suite 3821 passed; review 0 critical / 1 warning + 3 info, WR-01+IN-01 fixed). LIVE-04 made airtight provable engineering: zero-orphan replay + hallucination-strip on a real non-empty registry + live/debrief consistency (REAL CitationLinter+EvidenceRegistry, no mocks); the two `_citation_telemetry()` stubs closed with REAL signals — cumulative stripped/total `slop_ratio` + actual stripped text sourced from `StrippedRateTracker` (the `1/(1+mean)` placeholder is gone). LIVE-02 coach grounding pinned across ≥2 genres (REAL EventDetector real fixture + synthetic genre-2; empty/weak evidence→no fire). Verify = human_needed: 8/8 engineering must-haves green; 2 Kaan live-drive items persisted (`55-HUMAN-UAT.md`). Code-review fixes: WR-01 (live/debrief consistency test now drives the real `drills._citation_resolves`, not the dormant linter mode) + IN-01 (`drills.py` uses canonical `DEBRIEF_TOLERANCE_S`). IN-02/IN-03 deferred v2.x. **Phases 51–55 COMPLETE (5/8, 62%).** Next: plan + execute Phase 56 (performance + live mascot).

---

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-20 — v4.0 "SHIP" milestone started)

- **Project:** vibemix — open-source AI DJ co-host (Bravoh's first OSS release)
- **Core value:** "Real DJ friend in your ear" — never hallucinating, never breaking flow, never AI slop.
- **Current focus:** Phase 56 — Performance + Live Mascot
- **Last shipped:** v3.1 Distribution-Ready Pass — 2026-05-18 (status: `tech_debt` accepted; 7 Kaan-action carveouts on external clock).
- **Project mode:** standard.
- **Granularity:** fine.
- **Model profile:** quality (all agents on Opus, all checkpoints on).
- **Autonomy mode:** `gsd-autonomous fully` — every blocker + human-needed item discharged autonomously, only privacy rule + destructive risk + legal-capacity carveouts (Apple Dev Agreement + SignPath OSS) still pause. Soft Kaan-discharge gates surface to KAAN-ACTION but do NOT pause work.

---

## Current Position

Phase: 55 (Feedback Mode Live + Citation Integrity) — COMPLETE (engineering green; Kaan live-drive = KAAN-ACTION)
Plan: 3 of 3
Status: Phase 55 complete — ready to plan + execute Phase 56 (Performance + Live Mascot)
Last activity: 2026-05-21 -- Phase 55 complete (3/3 plans, suite 3821 green, verify human_needed, review fixes applied)

## Performance Metrics

| Metric | Value |
|--------|-------|
| Phases complete (v0.1.0) | 14 / 14 |
| Phases complete (v2.0) | 10 / 12 code-shipped (2 deferred to Kaan-action) |
| Phases complete (v2.1) | 13 / 13 engineering-green |
| Phases complete (v3.0) | 6 / 6 engineering-green (22 carveouts → KAAN-ACTION-LEGAL §SHIP-01..13) |
| Phases complete (v3.1) | 5 / 5 engineering-green (7 carveouts on external clock) |
| Plans complete (v3.0) | 41 / 41 |
| Plans complete (v3.1) | 32 / 32 |
| v3.0 REQ-IDs mapped + satisfied | 57 / 57 ✓ (100% coverage, no orphans) |
| v3.1 REQ-IDs mapped + satisfied | 44 / 44 ✓ (100% coverage, no orphans) |
| v4.0 REQ-IDs mapped | 22 / 22 ✓ (100% coverage, no orphans, no duplicates — +GENRE-01/02 to P52, +LIVE-05a to P56 per Kaan 2026-05-21) |
| v4.0 phase count | 8 (Phases 51–58) |
| v3.0 cross-phase integration seams WIRED | 3 / 3 |
| v3.1 cross-phase integration seams WIRED | 5 / 5 |
| v3.0 commits since `v2.1.0` tag | 250 |
| v3.1 commits since `v3.0` tag | 61 |
| v3.0 LOC delta | +62,215 / -1,029 across 529 files (net ~+61k) |
| v3.1 LOC delta | +57,597 / -2,541 across 382 files (net ~+55k) |
| v3.0 git tag | `v3.0` (annotated, LOCAL ONLY — not pushed) |
| v3.1 git tag | `v3.1` (pending milestone-close commit; LOCAL ONLY when created — not pushed) |
| v3.0 carveouts deferred to KAAN-ACTION-LEGAL | 22 |
| v3.1 carveouts deferred to KAAN-ACTION | 7 (SignPath cert + Tart VM walk + Kaan MacBook walk + Mixamo Adobe walk + VB-Audio email + 2 dep-audit documented decisions) |

---

## Accumulated Context

### v4.0 Roadmap RE-SPLIT to 8 Phases (2026-05-20)

v4.0 "SHIP" re-roadmapped from the prior 4-phase cut into **8 phases (51–58)** per Kaan's explicit directive for finer granularity. Numbering continues from v3.1 (closed at Phase 50) — NO reset. 19/19 REQ-IDs re-mapped to exactly one phase — 100% coverage, no orphans, no duplicates. The split breaks bring-up into three independent input seams and gives each interaction mode its own validation phase, so every real-hardware path is independently green before the modes that consume it are validated.

| Phase | Goal | Requirements (count) | UI |
|-------|------|----------------------|----|
| 51 — Real-Hardware Bring-Up | Boot + stabilize the built app on the real Mac; clean startup logs (incl. ws_bus empty-frame fix); ≥30-min full-set run with zero unhandled exceptions / bounded RSS | BRINGUP-01/04/05 (3) | — |
| 52 — Audio Path + Feature Grounding | BlackHole 48 kHz capture live; ground every derived feature — fix live BPM=200-on-129BPM bug; out-of-range values never reach bus/UI | BRINGUP-02 (1) | yes |
| 53 — Controller Live + Graceful Fallback | DDJ-FLX4 MIDI ingested live; clean degrade when unplugged / absent at boot | BRINGUP-03 (1) | — |
| 54 — Hype Mode Live | AI voice ACTUALLY FIRES on real drops/builds (close 32s-silent-on-drop bug); grounded in-bar non-slop across ≥2 genres; cooldowns/latency tuned live | LIVE-01/03 (2) | yes |
| 55 — Feedback Mode Live + Citation Integrity | Coach mode grounded/in-bar/non-slop across ≥2 genres; EvidenceRegistry citation strip reflects real events, zero orphaned/hallucinated citations | LIVE-02/04 (2) | yes |
| 56 — Performance + Live Mascot | TTFT to budget; no dropouts under live load; 60fps; Neon Rebel mascot reacts correctly to live audio/MIDI | PERF-01/02/03 + LIVE-05 (4) | yes |
| 57 — Sexify Finish | Final Tier-1 visual pass (zero HIGH); close v0.1.0-rc1 carryover bugs; tighten fresh-account first-run | POLISH-01/02/03 (3) | yes |
| 58 — Ship Readiness | All engineering gates green on real artifacts; §E2E-50A-WALK discharged; one-button SHIP-CUT documented + pre-verified | REL-01/02/03 (3) | — |

**Build-order rationale (8-phase):**

- **Phase 51 MUST be first** — every downstream validation depends on a running app booting to a live listening session on real hardware with clean startup.
- **Phases 52 + 53 are the two input seams** — audio (52) and controller (53) are independent of each other (53 needs only a running app from 51), but both must be live + grounded before any mode that consumes them is validated. Audio comes first because both modes react primarily to audio; controller is a secondary input + graceful-fallback contract.
- **Phases 54 + 55 are the two interaction modes**, split because they have different live failure shapes: hype's hard bug is "the AI voice did not fire on a detected drop in 32s" (54); feedback's hard bug class is citation integrity (55). Each is its own Kaan-ear pass + autonomous-proxy clean. Both depend on grounded audio features (52).
- **Phase 56 (perf + live mascot)** lands after both modes generate real reaction traffic — TTFT/dropouts/60fps are measured against real load, and the mascot is validated reacting to the live audio/MIDI events the prior phases proved.
- **Phase 57 (polish)** depends on a running app to inspect (51) and benefits from all live observations (52–56), but its work — visual pass, carryover bugs, first-run — is independent of validation outcomes.
- **Phase 58 (ship)** is last: Gate 2b (hallucination) is fed by Phases 54 + 55 live validation; Gate 6b (e2e report) and §E2E-50A-WALK need the real app driven end-to-end; final artifacts cut after polish (57) lands.

**Real-hardware findings folded into phases as concrete success criteria / known issues:**

- **Audio capture path is LIVE** (music level registers when a track is routed into BlackHole 2ch) → Phase 52 SC-1 confirms the live capture path.
- **BUG: live BPM read 200 on a ~129 BPM track** (BPM_VALID_MAX=180; out-of-range value reaching bus/UI) → Phase 52 SC-2: grounding fix at the source so a ~129 track reads ~129 and out-of-range BPM never reaches bus/UI.
- **BUG: AI voice did NOT fire in a 32s window despite a detected drop** → Phase 54 SC-1: the AI voice must actually fire on real drops/builds — the 32s-silent-on-drop bug is closed.
- **ws_bus emits intermittent empty `{}` frames between real frames** (minor) → Phase 51 SC-2 + known-issues note: bring-up cleanliness, close here.

**Locked invariants carried into v4.0 (all preserved from v3.0/v3.1):**

- POC immutability — `cohost*.py` retired (deleted, scrub-gated); `mascot.html` byte-stable + CI `mascot-audit`. No resurrection.
- ModelRouter seam — zero new hardcoded model literals; CI grep gate extends to v4.0 artifacts.
- Anti-slop blocklist — 15-token + `deeply\s+\w+` regex; live reactions + any new UI copy must pass.
- Privacy rule (`feedback_privacy_scope_narrow`) — off-limits LLM-transcript paths absolute; e2e harness asserts zero writes to `~/.hermes/` / `~/hermes-rig/logs/` / `~/.lmstudio/`. Bring-up debugging reads Tauri console + sidecar logs ONLY (vibemix's own logs), never Kaan's OZ/Hermes/local-AI surfaces.
- Gemini-only (`feedback_no_clap_use_gemini_embedding`) — no new providers/detectors; this is bring-up, not feature work.
- `gsd-autonomous fully` — engineering closes everything not requiring an external signature; the signed publish (Apple Dev Agreement via Francesco + SignPath OSS cert) stays KAAN-ACTION. Phase 58 makes the release one-button-after-signatures; it does NOT depend on the signatures landing.
- Hallucination gate is hard (`project_phase_16_kaan_dj_testing`) — satisfied by Kaan's DJ ear + autonomous proxy, NOT a 30-session replay harness. No release until live reactions (Phases 54 + 55) are confirmed grounded.
- Frontend-enforcement skill applies to Phases 52, 54, 55, 56, 57 (UI hint: yes) — CDJ Whisper, 20/80 accent rule, textured material feel, no AI-slop typography.

**Reuses already-built engineering (do NOT rebuild):** v3.1 e2e harness (`tests/e2e/macbook/`), 50a Kaan-walk checklist + `record_50a_walk.sh`, `cut_release.sh` with Gate 2b + Gate 6b wired, EvidenceRegistry citation strip, Neon Rebel 4-layer mascot state machine, BlackHole 48 kHz probe, TTFTMeter, installer/first-run wizard. v4.0 DRIVES and TUNES these on real hardware — it does not re-implement them.

### Phase 50 Outcome (2026-05-18, engineering-green)

v3.1 end-to-end MacBook + OS-matrix pass landed engineering-green. All 10 E2E REQ-IDs covered across 6 plans. Headline artifacts:

- **`tests/e2e/macbook/`** — canonical harness root per ARCHITECTURE.md § 4. 5-dimension dataclasses (Functional / Visual / Aesthetic / Usability / Hallucination) + worst-of overall status; Jinja2 `report_template.html` implementing 50-UI-SPEC.md verbatim (Geist Mono, 10-token palette, locked section labels)
- **Privacy fixture** — session-autouse `_privacy_guard` in `conftest.py` asserts zero file-count growth in `~/.hermes/` / `~/hermes-rig/logs/` / `~/.lmstudio/` on every test session (memory `feedback_privacy_scope_narrow`)
- **Anti-slop sibling** — `scripts/audit/check_no_slop_e2e.py` imports `AI_SLOP_BLOCKLIST` from canonical via `importlib`; scoped to `dist/e2e-macbook-runs/**/report.html`; 6 tested cases (clean / banned / word-boundary / no-report / missing-dir / canonical-import)
- **Visual regression** — Playwright + pixelmatch `maxDiffPixelRatio: 0.02` (REQ E2E-03 verbatim); persona-smoke + library-page + live-session specs target Tauri+Three.js production surfaces; baselines = Phase 47 placeholder GLBs (re-baseline at §VIS-04 discharge); CI-tolerant skips on Tauri dev-server unreachable per PITFALLS § 8
- **Audio loopback** — `audio_loopback_fixture.py` + VCR cassette at `tests/e2e/macbook/cassettes/gate_02_v3_0_baseline.yaml` (pinned to v3.0 GATE-02 baseline; zero live Gemini calls); AST-based ModelRouter seam-check rejects `gemini-N` SKU literals in executable code
- **48 kHz probe** — `test_blackhole_48khz_probe.py` re-asserts Phase 49 INSTALL-10 contract (48000 → ok, 44100 → fail, missing → fail); memory `project_v4_canonical_baseline`
- **Gate 6b** — `scripts/e2e/check_e2e_report.sh` (POSIX bash + grep + sed; 4 tested cases); wired into `scripts/launch/cut_release.sh` immediately after Gate 2b; blocks release publish on any dimension FAIL
- **50b OS-matrix smoke** — `os_matrix_smoke.py` composes Phase 49 `install_vm_matrix.sh --check-e2e`; 4-step smoke (install / launch / first-event / shutdown); dry-run wire-check across all 5 OS configs; Tart-image-required configs SKIPPED-with-reason
- **50a Kaan-walk scaffold** — `50a_kaan_walk_checklist.md` (10 steps + PASS/FAIL marks) + `nielsen_10_checklist.json` (10 heuristics × Tier-1 surfaces) + `scripts/e2e/record_50a_walk.sh` (macOS screencast + ffmpeg transcode); per memory `project_phase_16_kaan_dj_testing` — Kaan-ear, NOT 30-session harness

**Test verification:** 18 e2e tests added; harness foundation tests green (7 pass), audio fixtures green-or-skipped (4 skipped per CI-tolerant fallbacks), Gate 2b rerun + OS-matrix smoke green (3 pass + 1 skip), anti-slop sibling green (6 pass), Gate 6b bash test green (4/4 cases).

**Kaan-action surface (deferred for v3.1 close):**

1. **§E2E-50A-WALK** — Kaan executes the 50a walk on his MacBook + real DJ-set audio + records `docs/e2e/2026-05-walk.webm` per checklist at `tests/e2e/macbook/50a_kaan_walk_checklist.md`
2. **§INSTALL-VM-RUN downstream** (carry-forward from Phase 49) — 50b real-VM execution on all 5 OS configs (engineering ships dry-run + 2 reachable configs; full execution waits on Tart images + §INSTALL-COMPANION-SIGN)

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

- **DEPS-07: DISCHARGED 2026-05-19** (commit `f164c5c`). `brew install pinact` + `bash scripts/audit/run_pinact.sh --apply` rewrote 19 workflow files to the SHA + version-comment form. `dtolnay/rust-toolchain@stable` exempted via `.pinact.yaml::ignore_actions` (branch ref convention — pinning gives no real supply-chain hardening since the toolchain is fetched from rust-lang.org regardless). Upstream typo `signpath/github-action-submit-signing-request@v1.2.0` corrected to `@v1.2` (no v1.2.0 tag exists in the action's repo). `test_every_uses_is_sha_pinned` xfail removed — now passes green. Companion test rebases in `tests/security/test_sbom_workflow_shape.py` + `test_release_yml_signing_skips.py`.

- **DEPS-08: `livekit-plugins-openai` cull is CULL-BLOCKED**. `rg` found direct imports at `src/vibemix/agent/tts_chain.py:25` (`from livekit.plugins.openai import tts as _openai_tts_mod`) plus 3 test files (`tests/agent/test_proxy_client.py`, `tests/agent/test_config.py`, `tests/agent/test_tts_chain.py`). Removal requires rewiring the TTS proxy fallback chain — explicitly out-of-scope for Phase 46. `google-cloud-speech` + `google-cloud-texttospeech` are pure transitives of livekit-plugins-google with zero direct imports; retained-as-transitive (no Kaan-action needed there). **To close `livekit-plugins-openai`**: open a focused refactor phase post-v3.1 that rewires `tts_chain.py` to drop the OpenAI adapter path.

### v3.1 Roadmap Decisions Locked (2026-05-17)

- **5-phase decomposition P46–P50** with build-order: parallel cluster (46 + 47) → sequential cluster (48 → 49 → 50). Phase 46 + 47 share zero files. Phase 48 gated on Phase 46 `dep_ratings.json` schema. Phase 49 gated on Phase 46 + Phase 48 (companion pulls Green-rated deps only). Phase 50 gated on Phase 47 (real GLBs for visual snapshots) + Phase 49 (built signed `.dmg`).
- **Phase numbering CONTINUED** from v3.0 — v3.0 closed at Phase 45. v3.1 starts at Phase 46 (no `--reset-phase-numbers` semantics).
- **Five v3.0 invariants preserved** in every v3.1 phase: POC immutability (`cohost*.py`, `mascot.html` byte-identical to v2.0 tag), ModelRouter seam (zero new hardcoded model literals; CI grep gate extended to v3.1 artifacts), anti-slop blocklist (15-token + `\bdeeply\s+\w+` regex; grep target paths extended to `docs/AUDIT.md`, `docs/dep-opportunities/`, installer wizard copy, e2e report.html), privacy rule (project-scoped FS only; e2e harness asserts zero writes to off-limits paths per `feedback_privacy_scope_narrow`), 3-IPC-reservation contract (zero new IPC wrappers; v3.1 is build-time / test-harness / asset-only).
- **`gsd-autonomous fully` mode applied** — engineering proceeds unblocked in PARALLEL with v3.0 external clock (Apple Dev + SignPath ~1-week SLA). Soft Kaan-discharge gates surface to KAAN-ACTION-LEGAL but do NOT pause work.
- **Worktree-subagent Step-0 invariant** mandated for every plan per memory `feedback_worktree_must_sync_main_first` — every subagent prompt skeleton MUST include `git fetch origin main && git merge origin/main --no-edit` Step-0 block. Plan-checker rejects any plan lacking this. (Phase 40 worktree-isolation learning: stale base = ~161k-line regression on merge.)
- **Phase 50 split: 50a Kaan-ear (subjective) + 50b OS-matrix smoke (objective)** per memory `project_phase_16_kaan_dj_testing` — NOT a formal 30-session replay harness; Kaan walks his MacBook with real DJ-set audio.
- **Mascot scope locked to single VTuber character (Neon Rebel)** per memory `project_mascot_as_vtuber_personality_surface`.
- **No CLAP / no multi-provider AI** per memory `feedback_no_clap_use_gemini_embedding` + `feedback_no_scope_creep_clean_utility`.
- **BlackHole 48 kHz format requirement** per memory `project_v4_canonical_baseline`.
- **One-click install ≤ 60s ceiling** per memory `project_one_click_install_hard_req`.

### Decisions Locked (v3.0 — shipped, see v3.0-ROADMAP.md for full list)

All Phase 40–45 decisions remain locked. Highlights:

- Mic-as-Part-2 + lookahead-as-Part-3 closes "AI invents what Kaan said" + "AI reacts after the moment passed" hallucination classes (Phase 40).
- ModelRouter config-driven seam with zero hardcoded model literals + ServiceTier.FLEX on batch paths + STANDARD pinned to live coach (Phase 41).
- Hybrid hallucination gate: autonomous proxy fast-lane (PR + 7 nightly canary) + Kaan-ear release-cut veto via `check_gate.sh` Gate 2b; **P85 Phase 16 ear-test memory override is RETIRED** (Phase 42) — see [.planning/decisions/P85-OVERRIDE-RETIRED.md](.planning/decisions/P85-OVERRIDE-RETIRED.md).
- CDJ Whisper visual lock: Tier-1 surfaces zero HIGH findings; hardware-LED-strip meter rebuild; 22-site `--glow-faint` hover-glow sweep (Phase 43).
- README hero "the only AI co-host that actually listens to your set" verbatim lock + EvidenceRegistry citation strip in live UI + Bravoh waitlist toggle default-OFF UTM-tracked (Phase 44).
- KAAN-ACTION-LEGAL §SHIP-01..13 discharge cookbook ships 13 runbooks in canonical 8-block format; `audit_ship_v1_decision.py` (610 lines) pre-fills 4/5 rubric cells at T+30 (Phase 45).

### Decisions Locked (v0.1.0 + v2.0 + v2.1 — see prior STATE.md history)

All Phase 1–39 decisions remain locked. Highlights preserved:

- 3-process architecture (Tauri shell + Python sidecar + FastAPI proxy on `api.altidus.world`).
- Bundle ID `world.bravoh.vibemix` LOCKED (Pitfall P63) — Phase 33-07 CI grep enforces.
- AIza leak gate held: 0 / 482 files match at v2.0 close + 0 new bytes in v2.1 + 0 new bytes in v3.0 (gitleaks Phase 34-01).
- macOS 12.3+ / Windows 10/11. Linux excluded.
- Apache 2.0 + DCO license; signing via Apple Developer ID + SignPath OSS.
- Gemini-only AI (no Anthropic / OpenAI / Ollama / CLAP / OpenL3 / MERT / sentence-transformers / torch).
- Three.js (single 3D engine); vanilla TS in `tauri/ui/src/` (NOT React); WaveSurfer.js for Phase 29 debrief timeline.
- POC files retired (deleted, scrub-gated); `mascot.html` byte-stable + CI `mascot-audit`.

### Deferred Items (v3.1 close — 2026-05-18, carry forward as Kaan-action external clock)

Acknowledged per `gsd-autonomous fully` mode at v3.1 milestone close 2026-05-18. All 7 are external-clock dependent; critical-path discharge order: §INSTALL-COMPANION-SIGN → §INSTALL-VM-RUN → §E2E-50A-WALK; §VIS-04 + §VIS-05 (Mixamo) independent and parallel; §SHIP-CONTACT-VBAUDIO + 2 dep-audit decisions independent. v4.0 drives several of these to discharge: §E2E-50A-WALK is Phase 58 SC-2; the engineering-side gates feed Phase 58 SC-1.

| Category | Item | Status |
|----------|------|--------|
| ship-blocker | §INSTALL-COMPANION-SIGN — SignPath OSS Foundation cert grant for companion `.ps1` + `.py` Authenticode | external_clock (same cert as v3.0 SHIP-CUT) |
| ship-blocker | §INSTALL-VM-RUN — Real Tart VM execution macOS 12.3 / 14 / 15 + Win 10 / 11 | gated on §INSTALL-COMPANION-SIGN |
| kaan-walk | §E2E-50A-WALK — Kaan's MacBook walk + record `docs/e2e/2026-05-walk.webm` via `scripts/e2e/record_50a_walk.sh` | v4.0 Phase 58 SC-2 |
| asset-discharge | §VIS-04 — 28 Mixamo retargets via Adobe-account walk (Phase 47 scaffold ready) | independent (parallel) |
| asset-discharge | §VIS-05 — 5 pre-existing legacy_prep_* slot retargets (bundle with §VIS-04) | independent (parallel) |
| ship-optimization | §SHIP-CONTACT-VBAUDIO — VB-Audio OEM/bundle redistribution email | email drafted at `.planning/decisions/SHIP-CONTACT-VBAUDIO.md` (Kaan-action: send) |
| tech-debt | ~~DEPS-07~~ — DISCHARGED 2026-05-19 (commit `f164c5c`) | closed |
| tech-debt | DEPS-08 — `livekit-plugins-openai` cull blocked by `tts_chain.py:25` direct imports; scheduled post-v3.1 TTS proxy fallback chain refactor | tech_debt (docs/AUDIT.md § Decisions) |

### Blockers

- **None engineering-side at v4.0 start.** All 8 phases (51–58) are engineering work on real hardware; none requires an external signature.
- **External clock (v3.0 + v3.1 carryover, does NOT block v4.0 engineering):** Apple Developer Program Agreement update (Francesco, P46 legal-capacity) + SignPath OSS Foundation approval (Kaan, ~1-week SLA, P46 legal-capacity). These gate only the literal signed publish — surfaced as KAAN-ACTION in Phase 58; the SHIP-CUT is made one-button-after-signatures. No v4.0 phase depends on signatures landing.

### Risks (v4.0 — to mitigate during plan-time)

1. **"It works on Kaan's MacBook" trap** — v4.0 validates only Apple-Silicon real hardware; the OS matrix (macOS 12.3 Intel + Win) stays simulated/VM-pending. Mitigation: v4.0 explicitly scopes to Kaan-ear + real-Mac; OS-matrix coverage stays the v3.1 50b smoke + KAAN-ACTION §INSTALL-VM-RUN.
2. **Out-of-range derived features leak past the source guard** (Phase 52) — the BPM=200 bug shows feature validation is not airtight at the bus/UI boundary. Mitigation: clamp/reject at the producer, assert valid-range in the bus snapshot test, not just at the consumer.
3. **AI-voice-fires fix masks a deeper trigger/in-flight bug** (Phase 54) — the 32s-silent-on-drop could be cooldown, in-flight lock not clearing, or generate_reply not landing. Mitigation: instrument the trigger→generate→first-audio path end-to-end before tuning constants; do not paper over with shorter cooldowns.
4. **Privacy rule during live bring-up debugging** — reading logs to triage runtime errors must NEVER touch Kaan's OZ/Hermes/local-AI surfaces. Mitigation: bring-up debugging reads vibemix's own Tauri console + sidecar logs ONLY; off-limits paths in CLAUDE.md are absolute (`feedback_privacy_scope_narrow`).
5. **Anti-slop blocklist false-trips on live reaction copy** (Phases 54 / 55) — temptation to relax corrodes the v3.0 anti-slop thesis. Mitigation: NEVER relax the gate; tune the prompt/grounding, not the blocklist.

---

## Session Continuity

### Last Session

- 2026-05-20 — v4.0 "SHIP" roadmap RE-SPLIT from 4 phases into **8 phases (51–58)** per Kaan's explicit directive for finer granularity. Bring-up split into three input seams (boot/stability 51, audio+grounding 52, controller 53); the two interaction modes get dedicated phases (hype 54, feedback 55); perf+live-mascot 56; sexify 57; ship 58. 19/19 REQ-IDs re-mapped to exactly one phase (100% coverage, no orphans, no duplicates). Real-hardware findings folded in: ws_bus empty-frame fix (51), live BPM=200 grounding fix (52), AI-voice-must-fire fix (54). ROADMAP.md rewritten, REQUIREMENTS.md traceability re-mapped, STATE.md total_phases → 8, Current Position → Phase 51.
- 2026-05-20 (earlier) — v4.0 milestone started via `/gsd:new-milestone`; initial 4-phase roadmap created.
- 2026-05-18 — v3.1 "Distribution-Ready Pass" milestone SHIPPED + archived (5 phases P46–P50, 32 plans, 44/44 REQ-IDs).

### Next Session

- **`/gsd:plan-phase 51`** — decompose Phase 51 (Real-Hardware Bring-Up) into executable plans. This is the foundation: boot the app + sidecar on the real Mac, reach a stable live listening session, clean startup logs (ws_bus empty-frame fix), survive a ≥30-min full-set run with zero unhandled exceptions / bounded RSS. Everything downstream (52–58) depends on a running app.
- **Track external clock (v3.0 + v3.1 share the same one)**: Apple Developer Program Agreement update (Francesco) + SignPath OSS Foundation approval (Kaan, ~1-week SLA). Gates only the literal signed publish; surfaced as KAAN-ACTION in Phase 58. Engineering proceeds unblocked.

---

*State managed by gsd-roadmapper at 2026-05-20 (v4.0 "SHIP" roadmap RE-SPLIT to 8 phases 51–58; ready for `/gsd:plan-phase 51`).*

## Operator Next Steps

- Plan the first phase with /gsd-plan-phase 51
