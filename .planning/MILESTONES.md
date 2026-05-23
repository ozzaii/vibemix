# vibemix — Milestones

## v6.0 The Memory Turn (Shipped: 2026-05-23 — tech_debt accepted)

**Phases completed:** 4 phases (63–66), 12 plans, ~19 tasks
**Audit:** 14/14 requirements satisfied · 6/6 integration seams WIRED · 53/53 must-haves verified · 247/247 v6.0 surface tests GREEN · 4 cardinal invariants HOLD · 3 anti-feature gates GREEN · zero new dependencies · zero new IPC ports
**Status:** Engineering-green; `VIBEMIX_RECALL_ENABLED=0` default until §RECALL-EAR Kaan-ear pass

**Delivered:** vibemix shifts from a *reactive* co-host to a *forward-leaning* **copilot**. A local per-install `memory.db` + ~50-line `MemoryStore` wrapper land entirely on the shipped `src/vibemix/library/` primitives (zero net-new deps). An off-hot-path post-session ingest job (+ boot sweep) turns each session's `events.jsonl`+evidence+`ai_text` into deterministic TEXT "reaction moment" records — no audio, no LLM-extraction (CI-guarded). The coach prompt grounds in top-k past moments via a new existence-only `recall` evidence source (zero new linter code, mirror of P59 `key:`) + a PAST-tense-fenced gated block in `evidence_line` (cold/empty-memory golden byte-identical). A fabricated `[recall:<id>]` strips the whole turn. Two visible copilot moves (transition-shape callback + vocabulary callback) bottom out in real registered past moments — linter-grounded, cited, warm, non-nagging. The four cardinal invariants (single-writer / citation-grounding / trust-the-audio / one-socket) hold by reuse.

**Key accomplishments:**

- **Phase 63 — Memory Store** (STORE-01..04): MemoryStore storage spine with `SqliteVecMemoryStore` (vec0 primary) + `NumpyStore` fallback, Mac/Win bit-identical `cosine_topk` parity, raw-in/raw-out records, model resolved via `model_router.resolve("embedding")` on FLEX. Path-traversal-defended atomic `delete_session` cascade + boot `reconcile_orphans` + `run_memory_retention_sweep` (oldest-session-first whole-session eviction). All 19 `tests/memory/` GREEN; zero new deps.
- **Phase 64 — Session Ingest** (INGEST-01..03): `ingest.py` ships `build_coach_line_signature` (deterministic, model-free) + `ingest_session` (one `coach_line` per emitted `ai_text`; silenced citation strips skipped; signature-keyed embed-cache idempotency) + `run_ingest_sweep` (boot path-traversal-defended). Wired into `session_loop` at boot + close via `run_in_executor`. Static gate: ingest never imports the coach loop.
- **Phase 65 — Memory Retrieval Seam (ANTI-SLOP RELEASE GATE)** (RECALL-01..04): new existence-only `recall` source added to `EVIDENCE_SOURCES` + `_SOURCE_ALT` + `CITATION_GRAMMAR_BLOCK` (3 schema-mirror sites, lockstep) with zero new linter code. `MemoryRecall` service (event-gated, 0.7-cosine-floored, current-session-excluded). Gated PAST-tense `recall[…]` block in `evidence_line` (byte-identical when cold). Agent pre-dispatches off-loop with hard deadline; survivors registered BEFORE per-turn snapshot. Fabricated `[recall:<id>]` strips the whole turn — pinned by a static gate.
- **Phase 66 — Visible Copilot Move** (COPILOT-01..03): transition-shape callback + vocabulary/register callback templates in `coach.py::recall_fragment_for_event`. Recall chip rides the existing `cohost-reaction` IPC envelope (no new socket). 120s cooldown discipline with arm-on-emit at both bus + bus-less paths. Static anti-feature gate (`tests/repo/test_no_recall_antifeatures.py`) catches 20 forbidden phrases × coach.py + matrix.py. Engineering ships behind `VIBEMIX_RECALL_ENABLED=0`; Kaan flips after §RECALL-EAR ear-pass.

**Known deferred items at close: 18** (12 verification gaps + 6 UAT gaps — all intentional KAAN-ACTION carry-forwards; see STATE.md Deferred Items + KAAN-ACTION-LEGAL.md §SHIP-V4 / §RECALL-EAR). Of those, 11 are unchanged v4.0+v5.0 external-clock / live-confirm items; 6 are v6.0 P66 §RECALL-EAR felt-quality discharge (transition feel, voice/register match, FELT cooldown rhythm, runtime Gemini drift on anti-features). One STORE-03 call-site is deferred to a future recordings-UI-delete phase (out of v6.0 scope).

**Git tag deferred** (consistent with v4.0 + v5.0): the `v6.0` tag + branch merge are Kaan's call on his clock — `live-tuning-or-brain` is unmerged and v4.0 is also untagged/open.

Full archive: `.planning/milestones/v6.0-ROADMAP.md` · Requirements: `.planning/milestones/v6.0-REQUIREMENTS.md` · Audit: `.planning/milestones/v6.0-MILESTONE-AUDIT.md`

---

## v5.0 The Useful Cut (Shipped: 2026-05-21)

**Phases completed:** 12 phases, 42 plans, 67 tasks

**Key accomplishments:**

- Requirements:
- Requirements:
- Requirements:
- Requirements:
- Requirements:
- Requirements:
- Requirements:
- FLOOR (REAL `EventDetector`)
- Extended Phase 54's anti-slop spine to COACH (feedback) mode: the REAL CitationLinter strips an unbacked coach citation and passes the grounded one; coach-relevant events fire grounded across ≥2 genres through the REAL EventDetector; empty evidence never fires — all with real primitives, no mocks, no network.
- Registry from the real fixture.
- Closed the LIVE-05a anti-slop gap on the shipped Three.js rig: SnapshotSlice now carries music/voice levels and drop/peak/breakdown mode entry requires the music level to confirm the phase — a spurious `phase=drop` during a quiet section no longer fires the peak animation.
- Extended four existing perf tests to lock the PERF-01 TTFT telemetry floor and the MINIMAL-thinking gate, plus the PERF-02 zero-underrun floor under both-mode reaction traffic — all CI-runnable without real hardware, zero production code changed.
- Closed the remaining LIVE-05a contract items on the shipped Three.js rig: all six contract modes are proven reachable from real canonical bus events, the AI-speaking path provably overrides every music mode via the existing talk-block rule, mood/emotion are pinned as renderer tints (never FSM branches), and a synthetic mode-transition frame in the dispatch-latency test confirms the mode machine adds no measurable sidecar->client latency (p95 ~0.22ms, well under the 50ms PERF-03 budget).
- Five headless regression assertions (2 new pytest gates, 1 new vitest spec, 1 extended chrome spec) that pin the three v0.1.0-rc1 carryover-bug fixes shipped in `fac4c4a` so the drag capability, JS drag fallback, chrome strip hide, deep-link form, and TCC prime path can no longer silently regress.
- Task 1 — Friction audit (`docs/internal/first-run-friction-audit.md`):
- Rebuilt the AIza-clean vibemix-core sidecar for both apple-darwin triples, produced an unsigned macOS `.dmg` for Gate 2 to inspect (notarization blocked on the EXTERNAL Apple agreement — documented, not forced), and GENERATED `.planning/v4.0-MILESTONE-AUDIT.md` reading `overall_verdict: WIRED` after fixing a generator bug that was reporting false-MISSING seams.
- Fixed the latent REPO_ROOT double-`..` path bug in record_50a_walk.sh (now cwd-independent, target pinned to docs/e2e/2026-05-walk.webm) and proved the Gate-6b producer→consumer path green on a REAL rendered report with Hallucination honestly PARTIAL pending Kaan's ear.
- `cut_release.sh` re-pointed to the v0.1.0-rc public tag + v4.0 milestone audit, with a `--dry-run` signature-stub mode that exits GREEN on the real Plan-01/02 artifacts (everything but the EXTERNAL signature ready) while the `gh release create` hard guard stays absolute and regression-pinned.
- Task 1 — `harmonics.to_camelot` (the load-bearing pure function):
- Added a dedicated existence-only `key:` evidence source (body `<deck>:<camelot>`, e.g. `[key:A:8A]`) across all 5 schema-mirror touchpoints so the existing CitationLinter strips any fabricated harmonic clash — the un-cited-harmonic-feedback retrofit (Risk 2) lands BEFORE any Phase 60 harmonic prompt text.
- Registered KEY_CLASH (pri 7 / 28s) + TRANSITION_OPPORTUNITY (pri 5 / 20s) event types as plumbing-only, and landed the DECK-05 strictly-read-only repo test (tokenize-stripped two-tier scan + SQLCipher dormancy) that fails if any future commit writes a DJ-software DB.
- Task 2 — `_tick_once` single-writer wiring (TDD RED→GREEN):
- A SEPARATE structured-output Gemini deck-read (`DeckVisionReader`) + a real-screenshot accuracy eval harness + a KAAN-ACTION accuracy-floor gate — the universal cross-app fallback leg of the source ladder, shipped DORMANT (vision_enabled=False) behind the eval so it can never feed a misread key until Kaan signs off the real-rig corpus.
- Pure table-driven `is_clash`/`compatible`/`semitone_distance` on top of `to_camelot` — the anti-slop core where the LLM narrates a Camelot clash the code already proved, never computing intervals (HARMONIC-01).
- Wired `_melodic_overlap_gate` + the KEY_CLASH and TRANSITION_OPPORTUNITY branches into `EventDetector.detect()` behind a default-off `harmonic_clash_enabled` flag — a clash is structurally impossible to reach the audience unless the melodic-overlap gate passes, both decks clear the 0.6 cite floor, `is_clash()` returns True, AND the Kaan-ear ship gate flips the flag.
- Task 1 — corpus + veto test (`6c5805c`):
- Replaced the two Phase-59 stub coach arms with real cited harmonic fragments — KEY_CLASH hands the LLM a system-decided verdict + both decks' keys to cite + a hard "do NOT compute intervals" rule; TRANSITION_OPPORTUNITY is a strictly past-tense retrospective blend note — and reconciled the matrix [ev:<TYPE>] grammar.
- Built `pill_window.rs` as a clone-with-subtraction of `mascot_window.rs` (transparent/on-top/decoration-less/non-focus-steal, interactive — NOT click-through), with pill-scoped 200ms-debounced geometry persistence, a display-change re-clamp hook, the macOS focus-non-steal Accessory FLOOR plus a gated NSPanel STRETCH, and the `"pill"` capability-allowlist entry that closes the v0.1.0-rc1 drag-capability debt.
- Added the `primary_surface` tri-state config (`pill` default | `mascot` opt-in | `none`) to `config.rs` and wired `main.rs` setup() to create the pill, the mascot, or neither at session start — making the floating pill the primary in-set surface while keeping the mascot buildable on demand and the mascot-audit fence green.
- Additive read-only `deck_state` field ({side: {title, camelot, key, bpm, confidence}}) serialized onto the EXISTING flat 30Hz mascot frame on ws://127.0.0.1:8765 — honest-null keys, golden-equivalence on empty, single-writer untouched, no new port.
- The pill consumes the existing ws:8765 bus (direct-WS, no new port) and renders idle/listening/speaking/expand from real wire data — a pure 4-state machine, a real voice.rms TTS waveform (meter.ts tokens), and a verbatim citation strip — all decoupled from src/mascot/ so the mascot-audit fence stays green.
- Honest deck-context chips (`a · 8a · 128`, dim `unknown` on null, `decks · unknown` when nothing resolves) consuming the 62-03 `deck_state` wire field, wired into the pill expand panel, plus the explicit `var(--glass-3)` rgba surface that guarantees mac+win transparency parity (no OS vibrancy, DMG-#13415-resistant).

---

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
