# vibemix — Milestones

Living history of shipped milestones. One entry per milestone, newest first. Detailed archives in `.planning/milestones/`.

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
