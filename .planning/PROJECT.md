# vibemix — AI DJ Co-Host

## What This Is

A free, open-source AI co-host for live DJ sets. Runs locally on macOS or Windows: listens to your master output, watches your DJ software's screen, ingests your controller actions over MIDI, and talks back into your headphones or speakers as either a hype-man (party mode) or a coach (feedback mode). Three user levels — Beginner / Intermediate / Pro — with prompt templates tuned to each, plus a curated library of ~10 popular MIDI controllers mapped out of the box.

Bravoh's first open-source release. Built as a polished, narrow-scope utility that warms an audience converting into Bravoh's waitlist.

## Core Value

The AI reacts to your set in a way that feels alive and grounded — never hallucinating, never breaking the flow, never sounding like generic AI slop. If reactions feel forced, late, fake, or scripted, the product fails. The bar is "real DJ friend in your ear", not "voice assistant doing music commentary".

## Current Milestone: v7.0 "Open House"

**Goal:** Turn the repo from "engineering-green, gated on external clock" into a **publishable, contributable, install-anywhere open-source project** that strangers can clone, install, run, and contribute to — warming visitors into Bravoh waitlist signups along the way. Four pillars, all closing existing loops (no new product capability):

1. **All tests pass** — every collected test green across the full marker grid (default + `macos_audio` + `windows_only` + `integration` + `slow` + `e2e` + `cli` + `network`); 65 opt-in tests verified on Kaan's Mac + a Windows VM (or explicitly justified as KAAN-ACTION on the external-clock surface); flake-hunt; CI matrix runs the full grid on push to `main`.
2. **All devices ready** — the 10 bundled MIDI controller profiles live-verified end-to-end (Pioneer DDJ-FLX4/FLX6/FLX10/400/1000/SX3 · XDJ-RX3 · Numark Party Mix Live · Hercules Inpulse 300/500); hot-plug solid across all profiles; the duplicate `src/vibemix/midi/controllers/` ↔ `src/vibemix/midi/profiles/` catalogs reconciled to a single source of truth; audio backends (macOS BlackHole + Windows WASAPI loopback) verified across the matrix; a documented contributor recipe for "add your controller in N steps".
3. **OSS fully integrated** — close out v4.0 SHIP carryover (`v0.1.0` public RC publish actually goes out once Apple Dev + SignPath cert land); ship `CONTRIBUTING.md` / `CODE_OF_CONDUCT.md` / `SECURITY.md` / `MAINTAINERS.md` (LICENSE is already Apache 2.0 — keep); Bravoh-side proxy hardened to production-ready (per-client rate limit, abuse handling, observability, graceful fallback when proxy is offline, clean "BYO key" docs for self-hosters); release artifact UX (homebrew tap scaffold + scoop bucket scaffold ready, even if publish itself stays manual for v1).
4. **GitHub sexified, generated, tested** — close the front-porch: replace the README `<video src="docs/assets/demo.mp4">` placeholder with the real 30-sec demo (§ASSETS-DEMO-CUT discharge); GitHub Pages landing in CDJ-Whisper aesthetic; OG/social card pinned at the right SHA; every visual asset auto-generated from sources (re-renders are reproducible — no hand-cut SVG bitrot); repo-presence test suite (badges resolve, demo asset under N MB, OG image present, hero hash matches sentinel); a "what is this in 30 seconds" landing-page hook that converts to the Bravoh waitlist.

**Scope rule (anti-creep, locked):** v7.0 is **WIRING + DISCHARGE + POLISH**. **Zero new product capability.** **Zero new AI providers / managed-memory frameworks** (CLAP, MERT, OpenL3, torch, Mem0, Letta, Zep, Cognee all out — unchanged from v6.0). v6.0's deferred future items (multimodal moment-audio · cross-session arc priors · memory-driven pre-set prep · ProDJ Link as primary source) all stay deferred to a future milestone — they're explicitly **out of scope** for v7.0. This milestone earns the "first OSS release" stamp; it doesn't grow the product.

**Out of scope (this milestone):** any new feature, any new dep (red-class), any new ws port, any new IPC envelope (one-socket invariant unchanged), v6.0's `VIBEMIX_RECALL_ENABLED=1` flip (still gated on §RECALL-EAR Kaan-ear pass — independent KAAN-ACTION clock), `/hatch` user-gen mascot (still v2.x stretch — unchanged).

**Acid test for any v7.0 phase:** *"does this turn an existing engineering-green capability into something a stranger can install, verify, contribute to, or see — without growing the surface?"* If neither, defer.

**Last shipped:** v6.0 "The Memory Turn" — 2026-05-23 (`tech_debt` accepted; memory-grounded copilot via local sqlite-vec store + ~50-line `MemoryStore` wrapper + off-hot-path session-ingest + existence-only `recall` evidence source + two visible copilot moves. Ships behind `VIBEMIX_RECALL_ENABLED=0` until §RECALL-EAR Kaan-ear pass).

**v4.0 status:** "SHIP" (Phases 51–58) remains **engineering-complete (8/8)** but stays open alongside v7.0 — v7.0's OSS pillar actually **consumes** the v4.0 publish (§SHIP-V4 discharge → real `gh release create`). When v7.0 ships, v4.0 closes with it.

(v5.0 "The Useful Cut" shipped 2026-05-22. v4.0 "SHIP" engineering-complete 2026-05-21, publish on signature clock. v3.1 shipped 2026-05-18. v3.0 "Clean OSS Ship" 2026-05-17. v2.1 "The Unified Cut" 2026-05-16. v2.0 2026-05-14. v0.1.0 2026-05-13. Full archives in `.planning/milestones/`.)

<details>
<summary>📦 v6.0 The Memory Turn (shipped 2026-05-23, status <code>tech_debt</code>) — archived narrative</summary>

4 phases (63–66) shipped engineering-green under `gsd-autonomous fully` mode. 12 plans, 14/14 v6.0 REQ-IDs satisfied, 6/6 cross-phase integration seams WIRED, 53/53 must-haves verified, 247/247 v6.0 surface tests GREEN. A **WIRING / REUSE milestone with ZERO net-new dependencies** — built entirely on the shipped `src/vibemix/library/` primitives (sqlite-vec, cosine_topk, embed-cache, grounding pattern, EVIDENCE_SOURCES schema).

**Highlights:**

- **Memory Store (Phase 63)** — Local per-install `memory.db` (`SqliteVecMemoryStore` vec0 primary + `NumpyStore` fallback) + ~50-line `MemoryStore` wrapper with `add_record` / `query_topk`. Raw-in/raw-out records (never LLM-extracted "insight"). Mac/Win bit-identical `cosine_topk` parity (`pytest -m parity` GREEN; sqlite-vec loads on host). Path-traversal-defended atomic `delete_session` cascade + oldest-session-first whole-session retention sweep + boot `reconcile_orphans`. Model resolved via `model_router.resolve("embedding")` on FLEX cost lane (no hardcoded literal). All 19 `tests/memory/` GREEN.
- **Session Ingest (Phase 64)** — Off-hot-path post-session batch + boot sweep via `run_in_executor`. ONE v1 moment kind: `coach_line` (emitted `ai_text` + preceding-event context + inline citation tokens) — the only artifact that closes a hallucination class AND unlocks a P66 copilot move. `moment` (bare structural event) CUT; `audio_moment` (multimodal) DEFERRED. CI-guarded: ingest path calls only `embed_content` (never any generative model — extraction structurally impossible). Idempotent re-ingest via signature-keyed embed cache + `memory_ingested` marker. Static gate: ingest never imports the coach loop.
- **Memory Retrieval Seam (Phase 65) — ANTI-SLOP RELEASE GATE** — New existence-only `recall` evidence source added across 3 schema-mirror sites (`EVIDENCE_SOURCES`, `_SOURCE_ALT` regex, `CITATION_GRAMMAR_BLOCK`) with **zero new linter code** (à la P59 `key:`). `MemoryRecall` service (Grounding clone): event-gated, 0.7 cosine floor, current-session-excluded, single FLEX `embed_query` per track-aware event. Gated PAST-tense `recall[…]` block in `state/coach.py::evidence_line` — when memory is cold/empty/below-floor, prompt is **byte-identical** to v5.0 baseline. Anti-poisoning by construction: register-before-snapshot, unconditional per-turn rescope, fabricated `[recall:<unregistered>]` strips whole turn (pinned by headline RED test).
- **Visible Copilot Move (Phase 66)** — Linter-grounded transition-shape callback + vocabulary/register callback templates in `coach.py::recall_fragment_for_event`. Recall chip rides existing `cohost-reaction` IPC envelope (no new socket — one-socket invariant verified). 120s cooldown discipline with arm-on-emit at both bus + bus-less paths. Static anti-feature gate (`tests/repo/test_no_recall_antifeatures.py`) catches 20 forbidden phrases × coach.py + matrix.py. Engineering ships behind `VIBEMIX_RECALL_ENABLED=0`; Kaan flips after §RECALL-EAR ear-pass.

**Cardinal invariants verified** (4/4 hold by construction with named-test pinning): single-writer (memory never writes MusicState) · citation-grounding (every emitted `[recall:<id>]` resolves in CitationLinter) · trust-the-audio (live evidence renders before recall fence) · one-socket (zero new ws bindings).

**Open at close (KAAN-ACTION, ride forward):** §RECALL-EAR felt-quality discharge (4 items: transition feel, voice/register match, FELT cooldown rhythm, runtime anti-feature drift). §LIVE-EMBED real-session FLEX-tier round-trip. Two doc-drifts where code is correct (RECALL-02 traceability row + KAAN-ACTION-LEGAL.md §RECALL-EAR bus-less arm description). STORE-03 recordings-UI delete-button call-site (out of v6.0 scope; future recordings-UI phase). All in `KAAN-ACTION-LEGAL.md §RECALL-EAR` + `66-HUMAN-UAT.md`.

Full archive: `.planning/milestones/v6.0-ROADMAP.md` · Requirements: `.planning/milestones/v6.0-REQUIREMENTS.md` · Audit: `.planning/milestones/v6.0-MILESTONE-AUDIT.md`. Retrospective: `.planning/RETROSPECTIVE.md`.

</details>

<details>
<summary>📦 v4.0 SHIP (engineering-complete 2026-05-21, publish on signature clock) — archived narrative</summary>

8 phases (51–58) shipped engineering-green under `gsd-autonomous fully` mode. 26 plans. **Goal:** take vibemix from engineering-complete to a co-host Kaan plugs into his MacBook and plays full sets with — validated live on real hardware (audio + controller), both modes feeling like a real DJ friend in the ear, polished to peak, release one button away once external signatures land.

**Highlights:**
- Real-hardware bring-up split into three input seams — boot/stability (51), audio + feature grounding (52, incl. live BPM=200 grounding fix), controller (53) — each green before the modes that consume it.
- Hype mode (54) + feedback mode (55) validated as dedicated phases (different live failure shapes); feedback-mode citation integrity airtight (zero-orphan replay + hallucination-strip on a real registry).
- Performance + live mascot (56) — `LIVE_TTFT_BUDGET_MS=1500`, zero soak underruns, dispatch p95 ~0.22ms; mascot retargeted to the shipped Three.js GLB rig.
- Sexify finish (57) — impeccable CDJ-Whisper pass; v0.1.0-rc1 carryover bugs regression-pinned.
- Ship readiness (58) — `cut_release.sh --dry-run v0.1.0-rc1` exits GREEN; publish hard-guard regression-pinned (never auto-runs); `v4.0-MILESTONE-AUDIT.md` generated.

**Open at close (external clock):** Apple Dev Agreement (Francesco) + SignPath OSS cert (Kaan) gate the public RC publish; recorded §E2E walk + Gate-2b ear-passes are KAAN-ACTION. All in `KAAN-ACTION-LEGAL.md §SHIP-V4` + per-phase `*-HUMAN-UAT.md`.

Roadmap: `.planning/ROADMAP.md` (v4.0 section) · Audit: `.planning/v4.0-MILESTONE-AUDIT.md`. Milestone intentionally left unarchived per Kaan directive 2026-05-21.

</details>

<details>
<summary>📦 v3.1 Distribution-Ready Pass (shipped 2026-05-18, status <code>tech_debt</code>) — archived narrative</summary>

5 phases shipped engineering-green under `gsd-autonomous fully` mode. 32 plans, 61 commits since `v3.0` tag, net ~+57.5k LOC across `installer/`, `tauri/`, `scripts/`, `tests/`, `docs/`, `.github/workflows/`. 44 / 44 v3.1 REQ-IDs engineering-satisfied. 7 Kaan-action carveouts deferred to KAAN-ACTION surface (external-clock dependent — SignPath cert, Tart VM walk, Adobe Mixamo walk, Kaan-ear MacBook pass, VB-Audio OEM email). All 5 cross-phase integration seams audited WIRED.

**Highlights:**

- **Dependency audit + lockfile shipped (Phase 46)** — hermetic `uv.lock` regen in `python:3.12-slim-bookworm`; `cargo-deny` license allowlist with GPL ban; CycloneDX + SPDX SBOMs on release assets; `docs/AUDIT.md` 3-table surface with green/yellow/red install-impact ratings; freshness gate fails any PR with stale AUDIT.md; Dependabot wired for 4 ecosystems. 45 passing + 1 xfail (pinact mechanical rewrite deferred to CI).
- **Mascot real-GLB-land scaffolded (Phase 47)** — retarget CLI extended from 5 to 28 slots across 5 families; MANIFEST.yaml provenance schema + MIXAMO-CLIP-SOURCES.md selection guidance; 23 placeholder GLB stubs at slot paths so dev loader doesn't 404; EVENT_LAYER_PRIORITY_MAP single-source-of-truth for 15 event classes × 4-layer state machine; 63 Python + 177 TypeScript tests pass. §VIS-04 Mixamo discharge pending.
- **Opportunity scan locked steady state (Phase 48)** — `docs/dep-opportunities/2026-05-scan.md` rates 24 candidates (1G / 8Y / 9R-constraint / 6R-risk); ADR sidecar for the one green-adopt (OBS browser-source docs-only); 8 Yellow stubs in `.planning/research/v3-buckets/`; zero new runtime deps introduced; exclusion-set memories quoted verbatim.
- **Win + Mac one-click installer chain live (Phase 49)** — Inno Setup `[Run]` + `[Code]` license dialog for VB-CABLE silent install; `fetch_drivers.{sh,ps1}` + `driver_manifest.json` with SHA-256 verify; `companion-sign` workflow + verifier (SignPath cert pending Kaan discharge); `INSTALL_READY` event with 60s CI gate (median 41,000 ms across simulated SHIP-04 matrix); BlackHole 48 kHz post-install probe; WCAG-AA a11y on wizard; uninstall preserves user data unless opt-in clean. 68 passing + 1 platform-gated skip.
- **End-to-end MacBook + OS-matrix harness shipped (Phase 50)** — `tests/e2e/macbook/` with privacy-fixture asserting zero off-limits writes; Playwright + pixelmatch at `maxDiffPixelRatio: 0.02` baselined on Phase 47 placeholders; audio-loopback VCR cassette pinned to v3.0 GATE-02 (zero live Gemini); Gate 6b wired into `cut_release.sh`; 50a Kaan-walk checklist + Nielsen 10 + screencast capture rig; 50b OS-matrix smoke composes Phase 49 `install_vm_matrix.sh`. 16 passing + 5 CI-tolerant skips.

Full archive: `.planning/milestones/v3.1-ROADMAP.md` · Requirements: `.planning/milestones/v3.1-REQUIREMENTS.md` · Audit: `.planning/milestones/v3.1-MILESTONE-AUDIT.md`.

</details>

<details>
<summary>📦 v3.0 Clean OSS Ship (shipped 2026-05-17, status <code>tech_debt</code>) — archived narrative</summary>

6 phases shipped engineering-green under `gsd-autonomous fully` mode. 41 plans, 250 commits since `v2.1.0` tag, net ~+61k LOC across `src/vibemix/`, `tauri/`, `scripts/`, `tests/`, `docs/`, `eval/`. 57 / 57 v3.0 REQ-IDs engineering-satisfied. 22 carveouts deferred to KAAN-ACTION-LEGAL (legal capacity P46 × 2 + customer-facing publishes × 8 + real-hardware × 3 + real-asset × 1 + corpus × 4 + spike × 1 + sign-off × 2 + visual-regression-test × 1). All 3 integration seams + 5 flows audited.

**Highlights:**

- **Anti-slop audio path closed (Phase 40)** — Mic-as-Part-2 (12s ring + AI-talk zero-fill at sounddevice callback boundary) + lookahead-as-Part-3 (3s `NOT YET HEARD BY AUDIENCE` from source file via ffmpeg+mdfind+nowplaying-cli). Closes "AI invents what Kaan said" + "AI reacts after the moment passed" hallucination classes. v4 chat-tested cooldowns re-tuned (PHASE 18→10s, LAYER_ARRIVAL 16→10s, MIX_MOVE 20→14s, HEARTBEAT 70→45s, TRACK_CHANGE 6→5s).
- **Latency stack v2 (Phase 41)** — `ModelRouter` config-driven seam with zero hardcoded model literals (CI grep gate); ServiceTier.FLEX wired for debrief / library auto-tag / embedding (50% cost cut on batch paths); live coach pinned Standard + thinking=MINIMAL; LLM→TTS streaming pipe with bracket-depth-aware sentence boundary; 3.1 Flash TTS 6-tag DSL.
- **Hybrid hallucination gate (Phase 42)** — Autonomous proxy fast-lane (PR + 7 nightly canary) + Kaan-ear release-cut veto wired via `check_gate.sh` Gate 2b in `cut_release.sh`. P85 Phase 16 ear-test override formally retired (`P85-OVERRIDE-RETIRED.md` Decision Log). Public `eval/README.md` documents regime + redacts ear-test session content per `feedback_privacy_scope_narrow`.
- **CDJ Whisper visual lock (Phase 43)** — Tier-1 surfaces (session, mascot overlay, wizard, calibration) pass paired `gsd-ui-checker` + `gsd-ui-auditor` with zero HIGH findings; 22-site `--glow-faint` hover-glow sweep; hardware-LED-strip meter rebuild (16 segments, amber peak-hold with 1.2s decay, silk-12 grid); Mixamo retarget pipeline scaffolded; 8-cut 30s storyboard re-mock with chip overlays.
- **Launch positioning pre-staged (Phase 44)** — README hero locked verbatim to "the only AI co-host that actually listens to your set" with 3-gate CI lock + AI-slop blocklist (15 tokens + `\bdeeply\s+\w+` regex); EvidenceRegistry citation strip in live UI (click → debrief 2s region highlight); Bravoh waitlist toggle (UTM-tracked, opt-in, default-OFF, no signed-out telemetry); 16 SVG wordmark placeholders (6 DJ-software + 10 canonical controllers); outreach calendar + T-7 → T+30 launch sequence locked.
- **External discharge cookbook (Phase 45)** — KAAN-ACTION-LEGAL §SHIP-01..13 ships 13 discharge runbooks in canonical 8-block format covering Apple Dev / SignPath / Bravoh-server / SHIP-CUT / 5-channel social / Discord / repo transfer / 24h rotation / SmartScreen / SHIP-V1-DECISION. `audit_ship_v1_decision.py` (610 lines) pre-fills 4 of 5 rubric "Current" cells from GH releases + Bravoh healthz + ear-test logs + GH issues at T+30; SHIP-CUT is one-button after approvals land.

Full archive: `.planning/milestones/v3.0-ROADMAP.md` · Requirements: `.planning/milestones/v3.0-REQUIREMENTS.md` · Audit: `.planning/milestones/v3.0-MILESTONE-AUDIT.md`.

</details>

<details>
<summary>📦 v2.1 The Unified Cut (shipped 2026-05-16, status <code>tech_debt</code>) — archived narrative</summary>

13 phases shipped engineering-green under `gsd-autonomous fully` mode. 96 plans, 633 phase-scope tests added on top of v2.0 baseline, 225 commits since `v2.0` tag, net ~+45k LOC. 105 / 105 v2.1 REQ-IDs engineering-satisfied. 15 carveouts deferred to KAAN-ACTION-LEGAL (legal capacity + customer-facing publish + real-hardware + real-asset + post-approval). All 5 cross-phase integration seams audited WIRED.

**Highlights:**

- **Autonomous hallucination-proxy gate (Phase 27)** — replay harness + 2-judge cross-check (Gemini 3 Pro + Flash) + corpus diversity + substance + cited-relevance filter. Substitutes for Kaan's Phase 16 ear-test for v2.1 only (override expires post-v2.1 per P85).
- **Library intelligence v1 (Phase 28)** — Gemini Embedding 2 + sqlite-vec (Mac) / numpy (Win) with bit-identical top-K parity + vibe-search NL CLI + drag-drop UX + 30-day staleness nudge + €50/month CI cost gate.
- **Post-session debrief MVP UI (Phase 29)** — chaptered review + 60-90s voiced TL;DR + 3 drills + WaveSurfer.js clickable timeline + cited-critique strip. Second Tauri WebviewWindow docks into v2.0 sidecar slot via port 8766.
- **4-layer mascot full additive state machine (Phase 31)** — Base + Emotion + Anticipation + Reaction with priority-stacked crossfades; v2.0 mascot tests port verbatim (P47); GLB bundle 21.67/25 MB.
- **Long-term DJ profile (Phase 32)** — ~2KB allowlist-only JSON cache-side injected into `GeminiContextCache` (P60 preserved); `additionalProperties: false`; default-OFF consent; ≥ 2 citations per tendency.
- **One-click install hardening (Phase 33)** — TCC permissions wizard (macOS 12.3 / 14 / 15 fallback ladder) + BlackHole probe + onboarding stopwatch + bundle-ID lock + no-API-key-surface assertion.
- **Open-source security pass (Phase 34)** — gitleaks + pip-audit + osv-scanner + cargo-audit + cargo-deny + syft SBOM + signed-binary verifier + STRIDE-lite threat model + SECURITY.md + telemetry opt-in default-OFF + capability allowlist lint.
- **Signing pipeline real execution (Phase 38)** — Apple notarytool + SignPath GH Action wired into `release.yml` + post-sign verifier release-publish gate + PowerShell local-rehearsal + P46 audit (Bash + PowerShell mirror).
- **Cross-phase integration audit (Phase 37)** — 5 critical seams (P18→P20, P19→agent, P25→P28, P27→eval-gate, P31→ws_bus) all WIRED with green e2e tests + orphan inventory CI gate + grey-area decision log (P87) + POC immutability gate against v2.0 git tag.
- **Day-zero ops automation (Phase 36) + Public RC cut scaffold (Phase 39)** — Discord auto-provision + 100 RPS load test + healthz watchdog + aligned-community star-seeding + T-30/T+0/T+5/T+24h launch trigger + 5-channel social publisher with NACK + `cut_release.sh` 6-gate pre-flight (NEVER calls `gh release create` autonomously).
- **2 Hard Tek detectors (Phase 30)** — `DISTORTION_CLIMB` + `ACID_LINE_ENTRY` complete v2.0's 6-detector taxonomy; GenreRouter `MappingProxyType` atomic-swap regression test (8 readers × 1000 swaps, no race).
- **Universal2 sidecar (Phase 27-06)** — research-corrected from lipo-merge to target-triple convention (PyInstaller PKG archive embeds only in last merged slice). Eliminates Rosetta prompt on Apple Silicon. WASAPI `IMMNotificationClient` subscription handles mid-session default-device-change on Windows.

Full archive: `.planning/milestones/v2.1-ROADMAP.md` · Requirements: `.planning/milestones/v2.1-REQUIREMENTS.md` · Audit: `.planning/milestones/v2.1-MILESTONE-AUDIT.md`.

</details>

<details>
<summary>📦 v2.0 Research-Driven Ship (shipped 2026-05-14, status <code>tech_debt</code>) — archived narrative</summary>

12 phases shipped Claude-side end-to-end + 2 deferred-to-Kaan (Phase 15 Plan 04 UAT + Phase 16 ear-test). 1961 passing tests · 0 v2.0 regressions · 220 commits since `v0.1.0-rc1`.

**Highlights:**

- Anti-slop contract LIVE — every Gemini reaction citation-validated against `EvidenceRegistry`; un-cited responses strip to 40-OPUS ack-bank fallback. Phase 18 + Phase 20.
- 6 cross-genre event detectors (`KICK_SWAP`, `SUB_LAYER_ARRIVAL`, `BREAKDOWN_KICK_KILL`, `REENTRY_KICK_LAND`, `KICK_DENSITY_SHIFT`, `PHRASE_BOUNDARY`) + `GenreRouter` atomic dispatch. Phase 17.
- Latency Stack v1 — 40-OPUS `AckBank` + `GeminiContextCache` (1024-token floor / 4min refresh) + `CancelGate` (8s hard / 30 soft) + `TTFTMeter` + prompt diet. Phase 19.
- 10-SKU MIDI library + `MidiMapLoader`. Phase 23.
- djay Pro Mac overlay — Rust-parent AX bridge + second WebviewWindow + Canvas 2D amber ring. Phase 24.
- Mascot anticipation layer — `AdditiveLayer` + 5 `prep_*` GLB stubs + 30Hz ws_bus + cancel-aware crossfades. Phase 22.
- Pyrekordbox XML import + DEBRIEF architectural slot (sidecar `--debrief` flag + port 8766 + 3 IPC reservations). Phase 25.
- Recording browser + retention sweep. Phase 15.
- Sign + release CI scaffold (`release.yml` 4-target matrix + Pitfall-7 audit). Phase 21.
- README anti-slop hook + `BRANDING.md` + 4-channel post drafts + day-zero ops scripts. Phase 26.

Full archive: `.planning/milestones/v2.0-ROADMAP.md` · Requirements: `.planning/milestones/v2.0-REQUIREMENTS.md` · Audit: `.planning/milestones/v2.0-MILESTONE-AUDIT.md`.

</details>

<details>
<summary>📦 v2.0 milestone target features (archived — see <code>.planning/milestones/v2.0-ROADMAP.md</code>)</summary>

**Goal (v2.0):** Ship a public open-source AI DJ co-host that reacts in-bar, never hallucinates, with a viral demo arsenal earning 1000+ GitHub stars.

**Absorbed:** Outstanding v0.1.0 work (Phases 15-20 — recording, UAT, sign, release, day-zero ops) folded into a single bulky milestone alongside the research-driven feature set from the v2-bucket research swarm (`.planning/research/v2-buckets/SYNTHESIS.md` + 11 supporting artifacts).

**Target features (12 buckets — shipped):**

1. Ship infrastructure (absorb v0.1.0 outstanding) — recording browser + retention enforcement, UAT, Apple Developer ID sign + notarize + DMG, SignPath Windows MSI, GitHub release matrix, day-zero ops
2. Generalized event detector v1 — 6 cross-genre detectors
3. Latency stack — Gemini prompt diet + context caching + 40-OPUS ack bank + cancel-and-refire
4. Mascot 4-layer additive state machine (simplified for v2.0)
5. Citation linter — anti-slop tech impl
6. djay Pro Mac overlay highlight — viral demo Beat A anchor
7. Pyrekordbox XML one-shot library import
8. 10-SKU MIDI controller library
9. Post-session debrief — architectural slot only in v2.0
10. Library intelligence — deferred to v2.1
11. Cross-mode citation enforcement — live mode only in v2.0
12. Viral demo film + post arsenal

**v2.0 source-of-truth artifacts:**

- `.planning/research/v2-buckets/SYNTHESIS.md` — integration layer + priority matrix
- `.planning/research/v2-buckets/A-latency.md` + `A-followup-1-cancel-and-caching.md`
- `.planning/research/v2-buckets/B-industry-integrations.md` + `B-followup-1-v11-integration-spec.md`
- `.planning/research/v2-buckets/C-ui-overlay.md`
- `.planning/research/v2-buckets/D-mascot-emotion.md`
- `.planning/research/v2-buckets/E-debrief-pedagogy.md` + `E-followup-1-citation-linter.md`
- `.planning/research/v2-buckets/F-library-intelligence.md`
- `.planning/research/v2-buckets/G-genre-taxonomy.md` + `G-followup-1-hard-tek-dsp.md`
- `.planning/research/v2-buckets/synthesis-viral-demo.md`

</details>

## Requirements

### Validated

<!-- Inferred from existing codebase (cohost.py / cohost_v2.py / cohost_lk.py). -->

- ✓ Real-time audio capture pipeline (48kHz stereo → 16kHz mono) — `cohost.py:AudioBuffer`
- ✓ Streaming audio level extraction (RMS, frequency bands, onset density, BPM) — `cohost_v2.py:MusicState`
- ✓ Phase detection (silent/low/groove/build/drop/peak/breakdown) — `cohost_v2.py:EventDetector`
- ✓ Audible-deck detection (A/B/mix/none) — `cohost_v2.py`
- ✓ DJ-app screen capture with window-cropping (Quartz on macOS) — `cohost_v2.py:ScreenBuffer`
- ✓ DDJ-FLX4 MIDI controller event ingestion — `cohost.py:ControllerState`
- ✓ Now-playing track detection via macOS MediaRemote — `cohost.py:TrackInfo` (via `nowplaying-cli`)
- ✓ Gemini 3 Flash multimodal inference path (audio + screenshot + history) — `cohost.py:run_one_turn`
- ✓ Gemini 3.1 TTS streaming → PCM playback queue — `cohost.py:PlaybackQueue`
- ✓ LiveKit `RealtimeModel` integration (Gemini Live Native Audio) — `cohost_lk.py`, `cohost_v2.py`
- ✓ Heuristic event detector with cooldown + in-flight locking — `cohost.py:trigger_loop`
- ✓ Session recording (input.wav + voice.wav + events.jsonl per session) — `recordings/`
- ✓ Mascot WebSocket bus (canvas sprite reacts to RMS at 30Hz) — `mascot.html`
- ✓ Voice-aware mic gating (mic muted during AI talk) — `MicBuffer`

<!-- v3.0 shipped 2026-05-17 — Clean OSS Ship engineering-complete. -->

- ✓ Mic-as-Part-2 Gemini multimodal contract (12s ring + AI-talk zero-fill at sounddevice callback boundary) — v3.0 (Phase 40 / AUDIO-01)
- ✓ Lookahead-as-Part-3 (3s `NOT YET HEARD BY AUDIENCE` via ffmpeg+mdfind+nowplaying-cli; graceful skip on streaming-only) — v3.0 (Phase 40 / AUDIO-02 + AUDIO-04)
- ✓ Event cooldowns re-tuned to v4 chat-tested values (PHASE 10s, LAYER_ARRIVAL 10s, MIX_MOVE 14s, HEARTBEAT 45s, TRACK_CHANGE 5s) — v3.0 (Phase 40 / AUDIO-03)
- ✓ `ModelRouter` config-driven seam + zero hardcoded model literals (CI grep gate) — v3.0 (Phase 41 / LAT-01)
- ✓ Implicit caching default-on + 60min explicit cache TTL + EvidenceRegistry-mutation-driven refresh + cache_hit telemetry — v3.0 (Phase 41 / LAT-02 + LAT-03)
- ✓ LLM→TTS streaming pipe-through with bracket-depth-aware sentence boundary + 3.1 Flash TTS 6-tag DSL — v3.0 (Phase 41 / LAT-04 + LAT-05)
- ✓ Gemini Embedding 2 GA + MRL 768-dim + 4× smaller library index + bit-identical top-K parity — v3.0 (Phase 41 / LAT-06)
- ✓ ServiceTier.FLEX routing for batch paths (debrief / library_auto_tag / embedding) + STANDARD pinned to live coach — v3.0 (Phase 41 / LAT-07)
- ✓ `thinking_level=MINIMAL` enforced on live path + FLEX-on-live Pitfall 3 defense — v3.0 (Phase 41 / LAT-08)
- ✓ Hybrid hallucination gate — autonomous proxy fast-lane (PR + 7 nightly canary) + Kaan-ear release-cut veto via `check_gate.sh` Gate 2b — v3.0 (Phase 42 / GATE-06)
- ✓ Ear-test protocol + JSON Schema + debrief capture surface + 30min/≥2-genre/14d-window release gate — v3.0 (Phase 42 / GATE-05 + GATE-07)
- ✓ P85 Phase 16 ear-test override formally retired + Decision Log committed — v3.0 (Phase 42 / GATE-08)
- ✓ Public `eval/README.md` with threshold-mirror tests + ear-test content redaction privacy contract — v3.0 (Phase 42 / GATE-09)
- ✓ Tier-1 UI surfaces zero HIGH findings (paired gsd-ui-checker + gsd-ui-auditor) + 22-site `--glow-faint` hover-glow sweep — v3.0 (Phase 43 / VIS-01)
- ✓ Hardware-LED-strip meter rebuild (16 segments, amber peak-hold 1.2s decay, silk-12 grid) — v3.0 (Phase 43 / VIS-03)
- ✓ Mood→animation pool runtime validation (Hype-man / Teacher / Coach 30s smoke) + integrated-GPU 60fps p99 perf — v3.0 (Phase 43 / VIS-05 + VIS-06)
- ✓ Memory + doc drift cleaned ("DJ bat" → "Neon Rebel"; storyboard Workbench/DSEG7 → Saira/Geist on 5-warm-blacks + 1-amber palette) — v3.0 (Phase 43 / VIS-07)
- ✓ Hero demo storyboard 8-cut 30s v5 + ≤8-cut CI gate + chip overlays in cuts 2-6 — v3.0 (Phase 43 / VIS-08)
- ✓ Francesco pre-production handoff (deterministic 30-event demo-mode sequencer + 4-doc package + §VIS-09 runbook) — v3.0 (Phase 43 / VIS-09)
- ✓ README hero "the only AI co-host that actually listens to your set" verbatim lock + "No AI slop" H2 + 3-gate CI lock + AI-slop blocklist — v3.0 (Phase 44 / LAUNCH-01)
- ✓ EvidenceRegistry citation strip in live UI + tag→debrief deep-link + 2s waveform region highlight — v3.0 (Phase 44 / LAUNCH-02)
- ✓ DJ-software 6-cell grid + canonical-10 controllers grid (reconciled to `midi/controllers/*.json`) + 4-gate a11y CI + 16 SVG placeholders — v3.0 (Phase 44 / LAUNCH-03 + LAUNCH-04)
- ✓ Bravoh waitlist toggle (UTM-tracked, opt-in, default-OFF, no signed-out telemetry) — v3.0 (Phase 44 / LAUNCH-05)
- ✓ Outreach calendar (DJ TechTools + DDJ Tips + Mixmag + r/DJs + r/Beatmatch + r/edmproduction) + T-7 → T+30 launch sequence + `check_launch_docs.py` CI gate — v3.0 (Phase 44 / LAUNCH-09 + LAUNCH-10)
- ✓ `launch_trigger.sh` 5-channel × 4-stage cadence orchestrator + `--live` triple-env gate + sign-off footer gate + JSONL audit — v3.0 (Phase 45 / SHIP-08)
- ✓ `check_bravoh_server_ready.sh` 3-endpoint probe + `cut_release.sh` Gate 5b wire-in — v3.0 (Phase 45 / SHIP-06 engineering)
- ✓ `audit_ship_v1_decision.py` (610 lines) + `SHIP-V1-DECISION-TEMPLATE.md` + 5 synthetic fixtures + 20 hermetic tests + T-45-04-{01..05} threat mitigations — v3.0 (Phase 45 / SHIP-13 engineering)
- ✓ `docs/launch-rotation.md` §SHIP-11 24h solo rotation + 7-monitoring-source list + triage decision tree — v3.0 (Phase 45 / SHIP-11 engineering)
- ✓ KAAN-ACTION-LEGAL §SHIP-01..13 discharge cookbook (canonical 8-block format) — v3.0 (Phase 45 / 45-06)

<!-- v3.1 shipped 2026-05-18 — Distribution-Ready Pass engineering-complete. -->

- ✓ Hermetic `uv.lock` regen in `python:3.12-slim-bookworm` + cargo-deny GPL ban + frozen npm CI + dep-cull docs/AUDIT.md § Decisions — v3.1 (Phase 46 / DEPS-01..03 + DEPS-08)
- ✓ `docs/AUDIT.md` 3-table surface (Python / Rust / JS) with green/yellow/red install-impact + freshness gate via git log commit-time + CycloneDX + SPDX SBOMs + pinact audit scaffold + 4 dep-health badges + Dependabot 4-ecosystem weekly cadence — v3.1 (Phase 46 / DEPS-04..07 + DEPS-09 + DEPS-10)
- ✓ Retarget CLI extended 5 → 28 slots across 5 families + MANIFEST.yaml provenance schema + MIXAMO-CLIP-SOURCES.md + 23 placeholder GLB stubs + Phase 47 pools + EVENT_LAYER_PRIORITY_MAP (15 event classes × 4 layers) — v3.1 (Phase 47 / MASCOT-01..05)
- ✓ Bundle gate Tier-2 per-family bands + draco retune target (~23.2 MB / 25 MB cap) + persona-smoke harness with WebM screencast + README hero PNG/WebM scaffold + mascot.html grep-gate (6-file allowlist) + mascot-audit.yml CI aggregation — v3.1 (Phase 47 / MASCOT-06..08)
- ✓ `docs/dep-opportunities/2026-05-scan.md` rates 24 candidates under 4-color rubric (1G / 8Y / 9R-constraint / 6R-risk) + ADR sidecar for OBS browser-source docs-only + 8 Yellow stubs in `.planning/research/v3-buckets/` + zero new runtime deps + exclusion-set memories quoted verbatim — v3.1 (Phase 48 / OPP-01..06)
- ✓ Inno Setup `[Run]` + `[Code]` license dialog for VB-CABLE silent install + `fetch_drivers.{sh,ps1}` + `driver_manifest.json` SHA-256 verify + `companion-sign.yml` workflow + verifier + `audio_config.py --configure-routing` Multi-Output Device (Mac) + WASAPI default (Win) + BlackHole 48 kHz post-install probe — v3.1 (Phase 49 / INSTALL-02 + INSTALL-04 + INSTALL-05 + INSTALL-09 + INSTALL-10)
- ✓ `INSTALL_READY` event + 60s CI gate (median 41,000 ms / 60,000 ms budget across SHIP-04 simulated matrix) + forewarning copy passes anti-slop sibling-script + WCAG-AA a11y on wizard 3-step surface + uninstall preserves recordings/debriefs/ghost_calibration unless --clean opt-in — v3.1 (Phase 49 / INSTALL-01 + INSTALL-03 + INSTALL-06..08)
- ✓ `tests/e2e/macbook/` harness foundation + Jinja2 report.html + privacy fixture asserting zero writes to `~/.hermes/` / `~/hermes-rig/logs/` / `~/.lmstudio/` + audio-loopback VCR cassette pinned to v3.0 GATE-02 (zero live Gemini) + Playwright + pixelmatch `maxDiffPixelRatio: 0.02` against Phase 47 placeholder baselines — v3.1 (Phase 50 / E2E-01 + E2E-03 + E2E-04 + E2E-09)
- ✓ Gate 6b wired immediately after Gate 2b in `cut_release.sh` + 50a Kaan-walk checklist + nielsen_10_checklist.json × Tier-1 surfaces + macOS-only screencast capture rig (`record_50a_walk.sh`) + 50b OS-matrix smoke composing Phase 49 `install_vm_matrix.sh` + anti-slop sibling-script scoped to `dist/e2e-macbook-runs/**/report.html` — v3.1 (Phase 50 / E2E-02 + E2E-05..08 + E2E-10)

### Active

<!-- v3.x candidate scope — strategic conversation is open per memory `project_v2_planning_active`; do NOT auto-create next milestone. Kaan drives. -->

**Pending external clock — v3.0 + v3.1 RC publish (KAAN-ACTION-LEGAL §SHIP + §INSTALL + §VIS + §E2E)**

- [ ] Apple Dev Agreement update signed by Francesco (SHIP-01 / P46 legal-capacity)
- [ ] SignPath OSS Foundation approval received (SHIP-02 / P46 legal-capacity, ~1-week SLA)
- [ ] DIST-19 signed-binary smoke + `verify_signed.py --require-signed` (SHIP-03)
- [ ] INSTALL-VM-RUN fresh-VM matrix (macOS 12.3/14/15 + Win 10/11) + INSTALL-60S-CHECK (SHIP-04 + SHIP-05)
- [ ] Bravoh server `/vibemix/updates/*` + `/vibemix/healthz` + `*/5 * * * *` cron (SHIP-06)
- [ ] `gh release create v3.0.0-rc1 --draft` after `cut_release.sh` 6-gate green + tag-regex bump prerequisite (SHIP-07)
- [ ] `launch_trigger.sh --live` 5-channel social publish on T-30 / T+0 / T+5 / T+24h cadence (SHIP-08)
- [ ] Discord #announcements + `discord_provision.py --real` execution (SHIP-09)
- [ ] Repo transfer to `bravoh/vibemix` (SHIP-10) — depends on LAUNCH-06 bravoh GH org standup
- [ ] 24h monitoring rotation execution per `docs/launch-rotation.md` (SHIP-11)
- [ ] Windows SmartScreen reputation propagation observation (SHIP-12 — passive, 1-2 wk post-signed release)
- [ ] SHIP-V1-DECISION T+30 audit + Kaan 3-way sign-off (cut v1.0.0 / cycle RC2 / pause) (SHIP-13)

**Pre-stage discharges (v3.0 carryover)**

- [ ] AUDIO-05 PGP key for `security@bravoh.com` published to `keys.openpgp.org` (Kaan custody)
- [ ] AUDIO-06 Tauri ed25519 updater key rotated to production value (Kaan custody + GH secret)
- [ ] AUDIO-07 BlackHole probe fresh-Mac walk (fresh macOS user account)
- [ ] LAT-09 Gemini 3.1 Flash Live music spike verdict (real 5-min DJ clip + offline listen)
- [ ] GATE-01 ack-bank 20/40 (Gemini TTS quota reset, ~$0.10)
- [ ] GATE-02 VCR cassettes populated via `VCR_RECORD_MODE=new_episodes`
- [ ] GATE-03 6 × 30-min DJ session WAVs in git-LFS corpus (200 MB)
- [ ] GATE-05 ear-test session execution (≥2 sessions ≥2 genres in 14d window)
- [ ] LAUNCH-03 / LAUNCH-04 real DJ-software + controller logos (16 SVG placeholders → real assets)
- [ ] LAUNCH-06 bravoh GH org standup (Bravoh Enterprise billing flag resolve)
- [ ] LAUNCH-07 SHIP-TWEET Kaan + Francesco mutual sign-off
- [ ] LAUNCH-08 Discord live execution (`discord_provision.py --real`)

**Pre-stage discharges (v3.1 carryover)**

- [ ] §INSTALL-COMPANION-SIGN — SignPath OSS Foundation cert grant for companion `.ps1` + `.py` Authenticode submission (v3.1 / Phase 49)
- [ ] §INSTALL-VM-RUN — Real Tart VM execution on macOS 12.3 / 14 / 15 + Win 10 / 11 (depends on §INSTALL-COMPANION-SIGN) (v3.1 / Phase 49 + Phase 50)
- [ ] §E2E-50A-WALK — Kaan walks `tests/e2e/macbook/50a_kaan_walk_checklist.md` on MacBook with real DJ-set audio; records `docs/e2e/2026-05-walk.webm` via `scripts/e2e/record_50a_walk.sh` (v3.1 / Phase 50)
- [ ] §VIS-04 — 28 Mixamo retargets via Adobe-account walk + per-family `retarget_to_neon_rebel.py --really` (v3.0 carryover + v3.1 Phase 47; independent of SignPath path)
- [ ] §VIS-05 — 5 pre-existing legacy_prep_* slot retargets (bundle with §VIS-04 discharge) (v3.1 / Phase 47)
- [ ] §SHIP-CONTACT-VBAUDIO — Kaan emails VB-Audio for OEM/bundle redistribution permission (future Win installer optimization) (v3.1 / Phase 49)
- [ ] DEPS-07 — `pinact` mechanical SHA rewrite of `.github/workflows/*.yml` (closes via `brew install pinact && bash scripts/audit/run_pinact.sh --apply` OR first CI run) (v3.1 / Phase 46)
- [ ] DEPS-08 — `livekit-plugins-openai` cull blocked by direct imports at `src/vibemix/agent/tts_chain.py:25`; TTS proxy fallback chain refactor scheduled post-v3.1 (v3.1 / Phase 46)

**v3.x candidate scope (confirmed per memory `project_v2_open_candidates` — Kaan drives commit to milestone)**

- [ ] Mixxx OSC adapter — vibemix subscribes to UDP `:7777`, maps to existing `MusicState` schema (GPL-2 IPC-only)
- [ ] Mixxx controller map transpiler — offline build-time XML+JS → vibemix semantic event JSON; separate `vibemix-maps` GPL-2 repo; core consumes as data
- [ ] 10 → 30+ controller library via Mixxx map corpus ingest (closes "10 controllers" promise; unlocks ~80% OSS DJ TAM)
- [ ] pyrekordbox integration — confirmed v3.x candidate per memory
- [ ] Post-session debrief depth — multi-session arc, weekly progress summary, energy-arc taxonomy lift
- [ ] Library coach drill packs — "harmonic mixing pratiği için library'nde bu 5 track Am ↔ C sırayla mix'le"
- [ ] Curriculum-mode lesson packs per user level (Beginner / Intermediate / Pro)
- [ ] Multimodal "sounds like this" library search from live 30s phrase window (Gemini Embedding 2 multimodal RAG)
- [ ] Phase 16 ear-test memory override choice (restored Kaan-ear-only gate OR permanent autonomous proxy adoption — Kaan drives at next-milestone scaffold)

**v3.x backlog (deferred / opt-in)**

- [ ] `/hatch` user-gen mascot pipeline — Imagen / Hunyuan3D user-uploaded image → custom 3D mascot (Codex Pets pattern)
- [ ] OBS browser source mascot path — README 2-line update (mascot.html already serves on `ws://127.0.0.1:8765`)
- [ ] `obs-websocket-py` uplink — vibemix events → OBS scene switch / lower-third subtitle
- [ ] Beat This! via Rust sidecar — non-Gemini beat-grid, closes "AI reacts off-beat" hallucination class; gated on install-size budget

<!-- Legacy v1/v2 active scope (cross-platform, MIDI library, UX, prompting, distribution, GitHub presence, launch funnel) shipped across v0.1.0 → v2.0 → v2.1 → v3.0. See `.planning/milestones/v3.0-REQUIREMENTS.md` traceability table for full REQ-ID closure. -->


<!-- Launch funnel scope shipped via v3.0 Phase 44 + Phase 45 (README hero lock + EvidenceRegistry citation strip + Bravoh waitlist toggle + outreach calendar + 5-channel social publish orchestrator). Day-zero ops automation (Phase 36 v2.1) covers the remaining funnel mechanics (Discord auto-provision, 100 RPS load test, healthz watchdog). Marketing-ready demo cinematic awaits Francesco capture day per §VIS-09 runbook. -->

### Out of Scope

- **Gemini Live Native Audio modality** — Kaan tested it, doesn't generalize well enough for live music context. Code path stays in the repo but is not the default; future opt-in toggle possible.
- **Headphone cue listening** — Gemini conflates cue with master and produces wrong reactions.
- **User-supplied Gemini API keys** — friction kills virality; we eat the cost as marketing.
- **DAW integration** (Logic / Ableton / FL Studio) — mentioned as "the next conquest" after DJ software; defer entirely.
- **Mobile / iPad / iOS app** — desktop only.
- **Custom voice cloning** — Gemini TTS prebuilt voices only.
- **Linux support** — niche audience, doubles platform-engineering cost.
- **Multi-language UI** — English only in v1 (the AI itself can speak whatever Gemini supports, but the app chrome is English).
- **Track recommendation / library scanner AI feedback** — file-watcher exists in code but the "AI suggests your next track" feature defers to v1.1.
- **Mascot.html as a shipped UI** — kept as a fun easter egg / dev visualization, not part of the polished installer experience.
- **Real-time stream-to-Twitch/YouTube hook** — out of scope; recording for later sharing is enough.

## Context

**Where this comes from.** The codebase started as a personal Friday-night hobby experiment — Kaan wanted an AI co-host while DJing on his DDJ-FLX4. Three iterations explored different architectures: `cohost.py` (heuristic triggers + Gemini 3 Flash multimodal), `cohost_lk.py` (LiveKit + Gemini 2.5 Native Audio realtime), `cohost_v2.py` (single-source-of-truth `MusicState` + EventDetector + audible-deck detection). The v4 line (`cohost_v4.py` / `cohost_v4_tr.py`) became the canonical baseline — OpenRouter-primary TTS chain, tuned v4 chat-tested cooldowns, "trust the audio" anti-hallucination rule, BlackHole 48kHz format requirement, file-based 3s lookahead pattern. Phase 2–13 lifted FROM v4 into the `vibemix` package.

**Why open-source now.** Bravoh (the AI Artist Operating System) has a 140k-view reel on the project's Instagram account and a Closed Beta running since March 1, 2026. The DJ co-host is a fast-shipping, narrowly-scoped, demo-able artefact that lives downstream of Bravoh's positioning ("we build cool AI for musicians, here's a free taste") — it is the marketing wedge that turns "interested" into "watching the Bravoh waitlist".

**Current state (post-v3.1 close, 2026-05-18).** Distribution-ready engineering-complete. 5 milestones shipped (v0.1.0 / v2.0 / v2.1 / v3.0 / v3.1). 46 phases total. v3.1 added ~+57.5k LOC, 61 commits, 382 files changed since `v3.0` tag. 44/44 v3.1 REQ-IDs engineering-satisfied (100%); 7 carveouts deferred to KAAN-ACTION external surface per `gsd-autonomous fully` mode — all external-clock dependent (SignPath cert, Tart VM walk, Adobe Mixamo, Kaan-ear MacBook pass, VB-Audio OEM email, pinact binary). Installer chain ships one-click on Win + Mac with 41,000 ms median onboarding (60,000 ms budget); dep audit chain enforces hermetic lockfile + license allowlist + SBOMs + freshness gate; mascot scaffolded for full emotion coverage (28 slots × 4 layers, real GLB land pending Mixamo walk); e2e harness has audio-loopback VCR cassette + visual regression + privacy fixture + Gate 6b in `cut_release.sh`. Local `v3.0` tag created (NOT pushed); `v3.1` tag pending milestone-close commit. Awaiting external clock: Apple Dev Agreement (Francesco) + SignPath OSS Foundation (Kaan, ~1-week SLA) gates BOTH v3.0 SHIP-CUT and v3.1 companion-driver signing — v3.1 ride-along publishes after v3.0 lands.

**Existing user.** Kaan, primarily — the codebase started as his Friday-night experiment. The open-source release expands to "any DJ with a controller + a DJ software running on mac or windows" — beginner curiosity to pro feedback-loop.

**Stack baseline.** Python 3.12+ (current `.venv` is 3.14), LiveKit Agents framework, `google-genai`, `sounddevice` (mac) / WASAPI bindings (Windows), `mido` + `python-rtmidi`, `numpy` + `scipy` for DSP, `mss` / Quartz / win32 for screen capture. Heavy reliance on Gemini 3 family (Flash for inference, 3.1 Flash TTS for voice, Embedding 2 for library/RAG). Tauri shell + Python sidecar + FastAPI proxy on `api.altidus.world`. SQLite-vec (Mac) / numpy (Win) for library index.

**Open user feedback themes.** None yet — v3.0 not publicly shipped (engineering-complete; awaits Apple Dev + SignPath approvals). Anti-slop ship-gate satisfied by Phase 16 ear-test (memory override RETIRED post-v2.1) → Phase 42 hybrid regime (autonomous proxy + Kaan ear-test). T+30 SHIP-V1-DECISION audit will be first real user-signal moment.

**Known technical debt at close.** Tauri capability missing for drag (v0.1.0-rc1 carryover); mascot chrome strip + sidecar bundle schema path (v0.1.0-rc1 carryover); TCC list-population (v0.1.0-rc1 carryover); ack-bank 20/40 (Gemini quota); VCR cassettes (one-time population); 6 × 30-min corpus WAVs (200 MB git-LFS); Bravoh proxy probe still `MOCK_PROXY_FOR_DEV=1` pending Wave 0 real-host probe.

## Constraints

- **Timeline**: No hard calendar target — ship-when-ready per `gsd-autonomous fully` mode. External Apple Developer Program Agreement + SignPath OSS approvals are the critical path; engineering parallelizes around the external clock.
- **Quality bar**: "Real DJ friend in your ear, no AI slop" — Kaan will block release if reactions feel scripted, late, hallucinated, or generic.
- **Budget**: 150-200 € launch marketing (IG ads, paid posts), ~50 €/month ongoing Gemini API for end-user requests. Reassess if usage scales.
- **Tech stack**: Locked on LiveKit pipeline + Gemini 3 Flash + Gemini TTS streaming. No other LLM providers (Bravoh is Gemini-only).
- **Platforms**: macOS + Windows in v1. Linux explicitly excluded.
- **Team**: Kaan (engineering + product), Francesco (cofounder — product/marketing/DJ network for outreach), Momo (Bravoh team). Bravoh main product takes priority — vibemix runs alongside.
- **Open-source license**: TBD (likely MIT or Apache 2.0). Must allow Bravoh to use the same code internally if needed.
- **Security**: API key embedded in distributed binary is the API-key-protection problem of the year — solve via Bravoh-side proxy with per-client rate limit, not by shipping a raw key.
- **Hallucination grounding**: No release until verification phase confirms reactions are tied to real events. This is a hard gate.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Product name = **vibemix**, repo = `bravoh/vibemix` | Distinct enough to be its own thing, "mix" hooks the DJ semantic, GitHub Enterprise being set up under bravoh org | ✓ Good — LAUNCH-06 bravoh GH org pending, repo transfer SHIP-10 cookbook ready |
| **macOS + Windows in v1**, no Linux | Doubles addressable market vs mac-only; Linux is small DJ audience and tripled platform-engineering cost | ✓ Good |
| **LiveKit pipeline + Gemini 3 Flash + Gemini TTS streaming** as default AI path | Kaan tested Gemini Live Native Audio (`cohost_v2.py`) — grounding was worse than explicit Flash + TTS (`cohost.py`) despite more plumbing. LiveKit architecture (rooms/agents/tracks/streaming) is loved; only the brain swaps. | ✓ Good — LAT-09 3.1 Flash Live spike still pending as v3.x opt-in toggle question |
| **Curated 10-controller MIDI library** + generic fallback | Covers the ~80% of mid-tier DJs (Pioneer DDJ family + Numark + Hercules) without forcing every user through a calibration wizard | ✓ Good — canonical 10 reconciled to `midi/controllers/*.json` (LAUNCH-04); v3.x Mixxx map transpile unlocks 30+ |
| **Master-output-only audio**, no headphone cue | Gemini conflates cue with master and produces wrong reactions — Kaan confirmed | ✓ Good |
| **3 user modes × 2 interaction modes** (Beginner/Intermediate/Pro × Hype-man/Coach) | Wide audience coverage with a small prompt-template matrix | ✓ Good |
| **Bravoh-managed API key**, free for end users | Friction kills virality; we treat cost as marketing spend | ✓ Good — Bravoh proxy with per-client rate limit; €50/month CI gate stays under budget |
| **Genre picker at session start** | Phase-detection (drop/build/breakdown) thresholds depend heavily on genre; "auto-detect genre" is research-grade and would block shipping | ✓ Good |
| **Open-source as Bravoh's first OSS** | Marketing wedge ahead of Bravoh public launch; gets attention, builds trust, funnels to waitlist | — Pending public RC publish (KAAN-ACTION-LEGAL §SHIP-07) |
| **Workflow profile: Fine granularity, all Opus, all checkpoints on** | Kaan's directive: "do your deep research, don't go blind into coding, all checkpoints will be every agent will be Opus". | ✓ Good — `gsd-autonomous fully` mode validated across 4 milestones |
| **Critique → execute → critique → execute loop per phase** | Kaan's directive: every phase runs a quality loop, not a one-shot. plan-checker before execute, verifier after execute, ui-checker/ui-auditor between polish iterations, code-reviewer on output. | ✓ Good — Phase 43 visual lock proved the loop end-to-end (zero HIGH findings on Tier-1 surfaces) |
| **Reactive mascot as v1 feature, dedicated polish phase** | The mascot isn't just brand decoration — it's the visual feedback loop that telegraphs back what the system saw. Inspired by OpenAI Pets, lives in-app, reacts to MIDI/audio in real time. | ✓ Good — VTuber-style 3D character "Neon Rebel"; 4-layer mascot full additive state machine in production (Phase 31 v2.1); §VIS-04 Mixamo retargets pending |
| **One-click install is a HARD requirement** | Memory `project_one_click_install_hard_req` — Mac+Win, app opens → auto-downloads deps → configures audio → ready. Every dep choice rated green/yellow/red on install impact. | ✓ Good — Phase 33 v2.1 install hardening shipped (TCC wizard + BlackHole probe + onboarding stopwatch); INSTALL-VM-RUN real execution pending external clock |
| **No scope creep — clean utility only** | Memory `feedback_no_scope_creep_clean_utility` — OUT: stem separation, CLAP, multi-provider AI, enterprise features. Optimize for "minimum useful surface" not feature parity. | ✓ Good — every v3.0 phase respected the constraint; no Demucs / no CLAP / no ProDJ Link / no DAW |
| **Anti-slop thesis: grounded Gemini, not better prompting** (v3.0 lock) | Memory `project_anti_slop_grounded_gemini_thesis` — every feature evaluated by "what hallucination class does it close?". Grounding stack: audio + screen + MIDI + now-playing + Rekordbox priors + Gemini Embedding 2 + session memory + mic-as-Part-2 + lookahead-as-Part-3 + EvidenceRegistry citation strip in live UI. | ✓ Good — Phase 40 closed "AI invents what Kaan said" + "AI reacts after the moment passed" classes; Phase 44-03 surfaces citations on-screen |
| **Hybrid hallucination gate** (v3.0 lock) | Phase 27 autonomous proxy fast-lane (PR + 7 nightly canary) + Kaan-ear release-cut veto. P85 Phase 16 ear-test override formally retired. | ✓ Good — `check_gate.sh` Gate 2b wired in `cut_release.sh`; `.planning/decisions/P85-OVERRIDE-RETIRED.md` committed |
| **POC files byte-identical to v2.0 tag** | `cohost*.py`, `mascot.html`, `cohost.streaming.py.bak` — trusted intuition preserved as reference. Phase 37-06 immutability gate enforces. | ✓ Good — preserved through v2.1 + v3.0 |
| **Honest RC labeling** (v3.0 lock) | `v3.0.0-rc1` not premature `v1.0.0`; v1.0.0 decision deferred to Kaan post-2-week bake per SHIP-V1-DECISION audit at T+30. | ✓ Good — `audit_ship_v1_decision.py` (Plan 45-04) ships 3-way decision template |
| **`gsd-autonomous fully` mode** | Memory `feedback_autonomous_no_grey_area_pause` — recommended grey-area answers + defer blockers (not pause) into Kaan-action-required surface. Continue with unblocked work. Only destructive risk + privacy rule still pause. Legal-capacity (P46) + customer-facing publish + real-hardware + real-asset = explicit autonomy carveouts. | ✓ Good — applied through v2.1 + v3.0; 22 v3.0 carveouts routed cleanly to KAAN-ACTION-LEGAL §SHIP-NN cookbook |
| **No CLAP — Gemini Embedding 2 only** | Memory `feedback_no_clap_use_gemini_embedding` — vibemix is Gemini-only; CLAP/MERT/OpenL3 forbidden even when research recommends. | ✓ Good — Embedding 2 GA + MRL 768-dim shipped (LAT-06); 4× smaller library index |
| **Visual direction: CDJ Whisper** | Memory `project_visual_direction_cdj_whisper` — Pioneer-grade hardware in library mode. 5 warm blacks, single amber accent (4 intensities), tactility via faint glow not faux-3D bevels, Geist + Fraunces typeface, readability + restraint. | ✓ Good — Phase 43 Tier-1 surfaces locked; hardware-LED-strip meter rebuild; 22-site `--glow-faint` hover-glow sweep; storyboard migrated to Saira + Geist |
| **Bravoh waitlist toggle: subtle, opt-in, default-OFF** (v3.0 lock) | Funnel integrity over conversion lift — Kaan rejects pushy CTAs. No signed-out telemetry. UTM-tracked link. | ✓ Good — Plan 44-04 `ConfigStore.bravoh_waitlist_opt_in` + verbatim UTM URL grep-gate + token-driven faint-amber-glow active state |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state (users, feedback, metrics)

---
*Last updated: 2026-05-23 — **v7.0 "Open House" STARTED** under `gsd-autonomous fully` mode. Finishing milestone: "all tests pass, all devices ready, OSS fully integrated, GitHub fully sexified / generated / tested". Four pillars (TEST · DEV · OSS · GH) = wiring + discharge + polish, **zero new product capability**, zero new AI providers, zero new deps (red-class), zero new ws ports. Closes v4.0 SHIP carryover (public RC publish on external Apple Dev + SignPath clock) and turns v6.0's engineering-green capabilities into a publishable OSS repo. v6.0's `VIBEMIX_RECALL_ENABLED=1` flip stays on its independent §RECALL-EAR Kaan-ear clock — not in v7.0 scope. Last shipped: v6.0 2026-05-23.*
