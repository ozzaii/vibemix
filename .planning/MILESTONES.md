# vibemix — Milestones

Living history of shipped milestones. One entry per milestone, newest first. Detailed archives in `.planning/milestones/`.

---

## v3.1 — Distribution-Ready Pass

**Shipped:** 2026-05-18 (engineering-complete; `tech_debt` accepted — 7 Kaan-action carveouts ride the v3.0 external clock per `gsd-autonomous fully` mode)
**Phases:** 5 (46 — 50) | **Plans:** 32 | **Mode:** `gsd-autonomous fully`
**Git range:** `v3.0` (2026-05-17) → `HEAD` (2026-05-18) — 61 commits, 382 files, +57,597 / -2,541
**Audit:** `.planning/milestones/v3.1-MILESTONE-AUDIT.md` (tech_debt accepted, 44/44 reqs, 5/5 phases, 5/5 integration, 4/4 flows)
**Known deferred items at close: 7** (see STATE.md Deferred Items — all 7 are `human_needed` external-clock carveouts: §INSTALL-COMPANION-SIGN, §INSTALL-VM-RUN, §SHIP-CONTACT-VBAUDIO, §E2E-50A-WALK, §VIS-04, §VIS-05, DEPS-07/DEPS-08 documented decisions).

### Key Accomplishments

1. **Dependency audit + lockfile shipped** — hermetic `uv.lock` regen in `python:3.12-slim-bookworm` container; `cargo-deny` license allowlist with GPL ban; CycloneDX + SPDX SBOMs on release assets; `docs/AUDIT.md` 3-table surface with green/yellow/red install-impact ratings; freshness gate fails any PR with stale AUDIT.md; Dependabot wired for 4 ecosystems with weekly cadence. 45 passing + 1 xfail (pinact mechanical rewrite deferred to CI).
2. **Mascot real-GLB-land scaffolded** — retarget CLI extended from 5 to 28 slots across 5 families (Base / Emotion / Anticipation / Reaction / legacy_prep); MANIFEST.yaml provenance schema + MIXAMO-CLIP-SOURCES.md selection guidance; 23 placeholder GLB stubs at slot paths so dev loader doesn't 404; EVENT_LAYER_PRIORITY_MAP single-source-of-truth for 15 event classes × 4-layer state machine; 63 Python + 177 TypeScript tests pass.
3. **Opportunity scan locked steady state** — `docs/dep-opportunities/2026-05-scan.md` rates 24 candidates under 4-color rubric (1 Green / 8 Yellow / 9 Red-constraint / 6 Red-risk); ADR sidecar for the one green-adopt (OBS browser-source docs-only); 8 Yellow stubs carry forward to `.planning/research/v3-buckets/`; zero new runtime deps introduced; exclusion-set memories quoted verbatim.
4. **Win + Mac one-click installer chain live** — Inno Setup `[Run]` + `[Code]` license dialog for VB-CABLE silent install; `fetch_drivers.{sh,ps1}` + `driver_manifest.json` with SHA-256 verify; `companion-sign` workflow + verifier (SignPath cert pending Kaan discharge); `INSTALL_READY` event with 60s CI gate (median 41,000 ms across SHIP-04 simulated matrix, p95 52,000 ms); BlackHole 48 kHz post-install probe; WCAG-AA a11y on wizard; uninstall preserves user data unless opt-in clean. 68 passing + 1 platform-gated skip.
5. **End-to-end MacBook + OS-matrix harness shipped** — `tests/e2e/macbook/` with privacy-fixture asserting zero off-limits writes; Playwright + pixelmatch at `maxDiffPixelRatio: 0.02` baselined on Phase 47 placeholders; audio-loopback VCR cassette pinned to v3.0 GATE-02 (zero live Gemini); Gate 6b wired into `cut_release.sh`; 50a Kaan-walk checklist + Nielsen 10 + screencast capture rig; 50b OS-matrix smoke composes Phase 49 `install_vm_matrix.sh`. 16 passing + 5 CI-tolerant skips.

### Status

- 44 / 44 v3.1 REQ-IDs engineering-satisfied (100% coverage).
- 7 Kaan-action carveouts deferred to STATE.md, all external-clock dependent: §INSTALL-COMPANION-SIGN (SignPath cert) → unblocks §INSTALL-VM-RUN (real Tart VM) → enables §E2E-50A-WALK full pass; §VIS-04 (28 Mixamo retargets via Adobe walk) + §VIS-05 (5 legacy_prep follow-up); §SHIP-CONTACT-VBAUDIO (future OEM optimization); DEPS-07 pinact mechanical-rewrite + DEPS-08 livekit-plugins-openai cull both documented in `docs/AUDIT.md § Decisions`.
- Local annotated git tag `v3.1` to be created on milestone-close commit (NOT pushed — Kaan publishes after external discharges land per §SHIP-CUT cookbook in v3.0).

### Carveouts at close (`gsd-autonomous fully` mode)

Critical-path discharge order (per audit):
1. §INSTALL-COMPANION-SIGN — SignPath OSS Foundation cert grant (Authenticode for `.ps1` + `.py`).
2. §INSTALL-VM-RUN — Real Tart VM execution on macOS 12.3 / 14 / 15 + Win 10 / 11.
3. §E2E-50A-WALK — Kaan's MacBook walk with real DJ-set audio; `docs/e2e/2026-05-walk.webm` capture.
4. §VIS-04 / §VIS-05 — Mixamo Adobe-account retarget walk (independent of 1-3, runs in parallel).
5. §SHIP-CONTACT-VBAUDIO — VB-Audio OEM redistribution email (future Win optimization).

### Tech Debt Acknowledged

- DEPS-07: pinact binary unavailable on local executor; mechanical SHA rewrite deferred to first CI run.
- DEPS-08: `livekit-plugins-openai` cull blocked by direct imports in `src/vibemix/agent/tts_chain.py` + 3 test files; documented for a focused TTS proxy fallback refactor post-v3.1.

### Archives

- Roadmap: `.planning/milestones/v3.1-ROADMAP.md`
- Requirements: `.planning/milestones/v3.1-REQUIREMENTS.md`
- Audit: `.planning/milestones/v3.1-MILESTONE-AUDIT.md`

---

## v3.0 — Clean OSS Ship

**Shipped:** 2026-05-17 (engineering-complete; `tech_debt` accepted — KAAN-ACTION-LEGAL discharges pending external clock for public RC publish)
**Phases:** 6 (40 — 45) | **Plans:** 41 | **Mode:** `gsd-autonomous fully`
**Git range:** `v2.1.0` (2026-05-16) → `2aeb020` (2026-05-17) — 250 commits, 529 files, +62,215 / -1,029
**Audit:** `.planning/milestones/v3.0-MILESTONE-AUDIT.md` (passed, 57/57 reqs, 6/6 phases, 3/3 integration, 5/5 flows)
**Known deferred items at close: 6** (see STATE.md Deferred Items — all 6 are `human_needed` verification carveouts that are by-design Kaan-action under autonomy mode; all routed to `KAAN-ACTION-LEGAL.md` §AUDIO-05..07 / §LAT-09 / §GATE-01..05 / §VIS-04 / §LAUNCH-03/04/06/07/08 / §SHIP-01..13 discharge runbooks).

### Key Accomplishments

1. **Anti-slop audio path closed** — Mic-as-Part-2 (12s ring + AI-talk zero-fill) + lookahead-as-Part-3 (3s `NOT YET HEARD BY AUDIENCE` from source file via ffmpeg+mdfind+nowplaying-cli). Closes "AI invents what Kaan said" + "AI reacts after the moment passed" hallucination classes; v4 chat-tested cooldowns re-tuned.
2. **Latency stack v2 shipped** — `ModelRouter` config-driven seam with zero hardcoded model literals (CI grep gate); ServiceTier.FLEX wired for batch paths (50% cost cut); live coach pinned Standard + thinking=MINIMAL; LLM→TTS streaming pipe with bracket-depth-aware sentence boundary; 3.1 Flash TTS 6-tag DSL.
3. **Hybrid hallucination gate in force** — Autonomous proxy fast-lane (PR + 7 nightly canary) + Kaan-ear release-cut veto wired via `check_gate.sh` Gate 2b in `cut_release.sh`; P85 Phase 16 ear-test override formally retired (`P85-OVERRIDE-RETIRED.md`); public `eval/README.md` documents regime + redacts session content.
4. **CDJ Whisper visual lock** — Tier-1 surfaces (session, mascot overlay, wizard, calibration) pass paired `gsd-ui-checker` + `gsd-ui-auditor` with zero HIGH findings; 22-site `--glow-faint` hover-glow sweep; hardware-LED-strip meter rebuild (16 segments, amber peak-hold, silk-12 grid); Mixamo retarget pipeline scaffolded; 8-cut 30s storyboard re-mock with chip overlays.
5. **Launch positioning pre-staged** — README hero locked to "the only AI co-host that actually listens to your set" with 3-gate CI lock + AI-slop blocklist; EvidenceRegistry citation strip in live UI (click → debrief 2s region highlight); Bravoh waitlist toggle (UTM-tracked, opt-in, default-OFF); 16 SVG wordmark placeholders; outreach calendar + T-7 → T+30 launch sequence locked.
6. **External discharge cookbook complete** — KAAN-ACTION-LEGAL §SHIP-01..13 (45-06) ships 13 discharge runbooks in canonical 8-block format covering Apple Dev / SignPath / Bravoh-server / SHIP-CUT / 5-channel social / Discord / repo transfer / 24h rotation / SmartScreen / SHIP-V1-DECISION; SHIP-CUT is one-button after approvals land.

### Status

- 57 / 57 v3.0 REQ-IDs engineering-satisfied (100% coverage).
- 22 of 57 awaiting external clock + Kaan-discharge (legal capacity P46 × 2 + customer-facing publishes × 8 + real-hardware × 3 + real-asset × 1 + corpus × 4 + spike × 1 + visual-regression-test × 1 + sign-off × 2).
- Local annotated git tag `v3.0` created (NOT pushed — Kaan publishes when ready per §SHIP-07 discharge).

### Carveouts at close (`gsd-autonomous fully` mode)

- **Legal-capacity (P46)**: Apple Dev Agreement update (Francesco), SignPath OSS Foundation (Kaan, ~1-week SLA).
- **Customer-facing publishes**: SHIP-CUT (gh release create v3.0.0-rc1 --draft), SHIP-TWEET (5-channel social publish), SHIP-DISCORD, SHIP-TRANSFER, SHIP-ROTATE (24h monitoring rotation), SHIP-V1-DECISION (T+30 ~2-week bake verdict), LAUNCH-06 (bravoh GH org standup), LAUNCH-07 (SHIP-TWEET Kaan+Francesco sign-off), LAUNCH-08 (Discord live-execute).
- **Real-hardware**: INSTALL-VM-RUN matrix execution (SHIP-04), INSTALL-60S-CHECK (SHIP-05), AUDIO-07 fresh-Mac BlackHole probe walk, INSTALL-DEFENDER SmartScreen observation (SHIP-12).
- **Real-asset production**: VIS-04 5 Mixamo retargets (Adobe-account-gated download + Kaan-aesthetic Pioneer-CDJ-headbob selection).
- **Corpus**: GATE-01 ack-bank 20/40 (Gemini quota reset), GATE-02 VCR cassettes, GATE-03 6 × 30-min DJ session WAVs (200 MB git-LFS), GATE-05 ear-test session execution.
- **Spike**: LAT-09 Gemini 3.1 Flash Live music spike (real 5-min DJ clip + offline listen + verdict write).
- **Pre-stage**: AUDIO-05 PGP key, AUDIO-06 Tauri ed25519 updater key, LAUNCH-03/04 real logo swaps (16 SVG placeholders shipped).

### Tag

- `v3.0` (annotated, LOCAL ONLY — `git push origin v3.0` is documented Kaan-action in KAAN-ACTION-LEGAL §SHIP-07).

---

*See `.planning/milestones/v3.0-ROADMAP.md` for full phase narrative + decisions + technical debt. See `.planning/milestones/v3.0-REQUIREMENTS.md` for full REQ-ID traceability with outcomes.*

---

## v2.1 — The Unified Cut

**Shipped:** 2026-05-16 (`tech_debt` accepted) | **Phases:** 13 (27 — 39) | **Plans:** 96 | **Mode:** `gsd-autonomous fully`
**Git range:** `v2.0` → `8c6e668` — 225 commits, +114,845 / -69,617 across 947 files | **Tag:** `v2.1.0` (LOCAL)
**Audit:** `.planning/milestones/v2.1-MILESTONE-AUDIT.md` (105/105 REQ-IDs engineering-satisfied; 15 carveouts deferred to KAAN-ACTION-LEGAL)

Full archive: `.planning/milestones/v2.1-ROADMAP.md` · Requirements: `.planning/milestones/v2.1-REQUIREMENTS.md`.

---

## v2.0 — Research-Driven Ship

**Shipped:** 2026-05-14 (`tech_debt` accepted) | **Phases:** 12 (15 — 26) | **Plans:** 38 | **Tests:** 1961 passing
**Tag:** `v2.0` | **Audit:** `.planning/milestones/v2.0-MILESTONE-AUDIT.md`

Full archive: `.planning/milestones/v2.0-ROADMAP.md` · Requirements: `.planning/milestones/v2.0-REQUIREMENTS.md`.

---

## v0.1.0 — MVP Foundation

**Shipped:** 2026-05-13 | **Phases:** 14 (1 — 14) | **Tag:** `v0.1.0-rc1`

Full archive: `.planning/milestones/v0.1.0/`.
