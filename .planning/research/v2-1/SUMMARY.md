# v2.1 The Unified Cut — Research Synthesis

**Project:** vibemix — AI DJ Co-Host
**Milestone:** v2.1 "The Unified Cut" — public OSS RC
**Phase numbering:** continues from Phase 27 (v2.0 closed at Phase 26, status `tech_debt`)
**Researched:** 2026-05-14
**Mode:** `gsd-autonomous fully`
**Overall confidence:** HIGH — research anchors on a live audit (`v2.0-MILESTONE-AUDIT.md`), 1961 passing tests, 220 commits since `v0.1.0-rc1`, and 41 already-mitigated v2.0 pitfalls. The 13 buckets map cleanly to existing v2.0 seams; no architectural surprises.

---

## TL;DR (read first — for roadmapper)

- **Scope is ~80% wiring, 20% genuinely new code.** Every v2.1 bucket either (a) closes a v2.0 orphan, (b) extends a v2.0 slot, or (c) docks into an architectural reservation Phase 25 / 22 / 21 / 26 explicitly left behind. There is **no architectural redesign** in v2.1 — the 3-process Tauri-shell + Python-sidecar + FastAPI-proxy model is locked.
- **3 new runtime deps. Total.** `sqlite-vec==0.1.9` (Python, +0.4-0.6 MB) + `wavesurfer.js ^7.10` (npm, +180 KB) + `tauri-plugin-macos-permissions = "2.3.0"` (Rust, +200 KB Mac / 0 Win). Net bundle delta **<1 MB**; ~10 dev/CI-only adds. Bundle stays at **~201 MB** vs 350 MB cap.
- **Proposed decomposition: 13 phases (27 → 39).** One phase per v2.1 bucket. Architecture research already maps each bucket to a specific seam + integration pattern (EXTEND / DOCK-TO-SLOT / NEW out-of-band).
- **Hot path = 4 sequential phases gated by external approval:** `external Apple/SignPath approval → Phase 38 (real sign) → Phase 33 (install harden + fresh-VM rehearsal) → Phase 37 (integration audit) → Phase 39 (RC cut)`. Apple Dev Agreement + SignPath OSS approvals are **legal-capacity carveouts that CANNOT discharge autonomously** (Pitfall P46) — Kaan/Francesco must click submit themselves.
- **Anti-slop bar is the gate.** Phase 27 (autonomous hallucination proxy) is the substitute for Kaan's Phase 16 ear-test. Pitfalls P42-P45 are all flavors of "gate passes but reactions are still slop"; the phase plan must encode 2-judge cross-check + corpus diversity + substance metric + cited-but-irrelevant orthogonal check OR the autonomous gate becomes a paper contract.

---

## Stack additions (locked recommendations)

| Bucket / Phase | New runtime add | Version | License | Bundle Δ | Install impact | Existing-covers? |
|----------------|------------------|---------|---------|----------|----------------|------------------|
| 27 — Hallucination gate | none | (pytest-asyncio dev-only if absent) | Apache-2.0 | 0 | GREEN | mostly |
| 28 — Library intelligence | **`sqlite-vec==0.1.9`** (Python) | 0.1.9 (2026-03-31) | Apache-2.0/MIT dual | +0.6 MB Mac / +0.4 MB Win | GREEN | partial |
| 29 — Debrief UI | **`wavesurfer.js ^7.10`** (npm) | 7.10+ | BSD-3-Clause | +180 KB (60 KB gz) | GREEN | partial |
| 30 — Hard Tek detectors | none | — | — | 0 | GREEN | fully |
| 31 — 4-layer mascot | none | — | — | 0 | GREEN | fully (Three.js native) |
| 32 — DJ profile | none | — | — | 0 | GREEN | fully |
| 33 — Install hardening | **`tauri-plugin-macos-permissions = "2.3.0"`** (Rust) | 2.3.0 (2025-05-06) | MIT | +200 KB Mac / 0 Win | GREEN | partial |
| 34 — Security pass | dev/CI only: gitleaks, pip-audit, cargo-audit, cargo-deny, osv-scanner, syft | latest | mixed Apache-2.0/MIT | 0 | GREEN (CI) | nothing |
| 35 — Real GLB + viral demo | dev only: Meshy v6 API, Mixamo, ffmpeg | — | API ToS / LGPL-2.1+ | -2 to -10 MB after compression | N/A (off-machine) | fully |
| 36 — Day-Zero ops | none (reuse `httpx`, `gh` CLI) | — | — | 0 | GREEN | fully |
| 37 — Integration audit | dev/CI: `tauri-driver` + WebdriverIO (Win only — Mac WKWebView gap irreducible) | latest | MIT | 0 | YELLOW (mac E2E doc'd gap) | partial |
| 38 — Signing pipeline | CI: SignPath GH Action, `rcodesign` (fallback) | — | mixed | 0 | GREEN once approvals land | partial |
| 39 — RC cut + ship | CI: `gh` CLI (already present) | — | MIT | 0 | GREEN | fully |
| **Total v2.1** | **3 net runtime deps** | — | — | **+0.5 to +1.0 MB** | **GREEN** | — |

**Locked decisions (do NOT relitigate during phase planning):**

- **Bundle ID `world.bravoh.vibemix` — never edit.** Pitfall P63: any rename = TCC permissions reset for every v2.0 user.
- **Apache 2.0 + DCO** — every new dep MUST be Apache-2.0 / MIT / BSD / ISC compatible.
- **Gemini-only AI** — no Anthropic, OpenAI, Ollama. No CLAP/OpenL3/MERT — `feedback_no_clap_use_gemini_embedding` is absolute.
- **Single 3D engine: Three.js** — no Babylon, no Lottie.
- **Vanilla TS in `tauri/ui/src/`** — vibemix UI is NOT React. Reject React for Debrief.
- **macOS 12.3+ / Windows 10-11.** Linux excluded.
- **No new external processes beyond Tauri parent + Python sidecar + FastAPI proxy.**

**Rejected alternatives:** Chromadb / Qdrant / faiss-cpu (server-bound or +30-100MB), sentence-transformers / torch (+800MB), langchain (multi-provider tax), scikit-learn for F1 (+30MB for 20 lines), tiktoken (wrong tokenizer for Gemini), Trivy (March 2026 supply-chain compromise), Safety CLI (commercial restriction), discord.py (5MB for one REST POST), Locust / k6 (overkill at 100 RPS), pytest-playwright (WebKit mismatch with Tauri), React/Vue/Svelte for debrief, @tweenjs/tween.js / gsap (Three native covers), mem0 / motorhead (wrong primitive for 2KB JSON), Veo 3.1 as primary editor ($22/iteration, non-deterministic), Multipass / Vagrant (broken on Apple Silicon), fastlane (Ruby bloat), `osascript` programmatic TCC reset (Apple-deprecated).

---

## Feature priority matrix

| # | Phase | Bucket | Table-stakes | Differentiator | Anti-feature watch | Complexity | v2.0 dependency |
|---|-------|--------|--------------|-----------------|---------------------|------------|------------------|
| 27 | 27 | Hallucination autonomous proxy | recorded-session replay + Gemini judge + F1 + CI gate | 2-judge cross-check + cited-relevance + corpus diversity | real-time eval-in-prod, multi-judge ensemble, BLEU/ROUGE | **L (~8-10 E-days)** | P17/P18/P19/P20/P22 + `recordings/*/events.jsonl` |
| 28 | 28 | Library intelligence v1 | Rekordbox XML import + Gemini Embedding 2 + sqlite-vec + drag-drop + 30-day nudge | citation-grounded `[track:<id>]` + vibe-search in English + library-local only | "AI suggests your next track" prescription, CLAP, vector-DB server, pre-embedded library | **L (~7-9 E-days)** | P25 `register_library` orphan + P5 proxy + P18 EvidenceRegistry |
| 29 | 29 | Post-session debrief MVP UI | chapters + clickable timeline + 60-90s voiced TL;DR + 3 drills + cited critique | first AI-grounded DJ debrief; SBI/STAR-AR; audio scrub per citation | metrics dashboard, social/leaderboard, per-track ✓/✗, interactive Q&A, badges | **L (~8-10 E-days)** | P25 DEBRIEF slot + P15 + P20 + P18 |
| 30 | 30 | Hard Tek 2 detectors | `DISTORTION_CLIMB` + `ACID_LINE_ENTRY` DSP + tune + grammar | DSP-grounded vs vibes-based; per-genre dispatch | 20+ micro-detectors, ML-on-every-frame, citing internals user-facing | **S (~3-4 E-days)** | P17 GenreRouter + Hard Tek chain |
| 31 | 31 | 4-layer mascot | base + emotion + anticipation + reaction additive priority | beat-coupled hip-bob; cited reactions; inline `[emote:*]` tags | procedural visemes, multi-character, webcam eye-tracking, 30+ vocab | **M (~5-7 E-days)** | P22 simplified subset (EXTENDS, not REPLACES — P47) |
| 32 | 32 | Long-term DJ profile | ~2KB JSON post-session regen + verbatim system-prompt inject | "always inject" (ChatGPT-pattern); 8-12 cap forces summarization quality | vector DB, append-only growth, cross-user sharing, "style names" | **S (~3-4 E-days)** | P25 DEBRIEF + P10 prompt matrix + Phase 28 library |
| 33 | 33 | One-click install hardening | signed DMG + MSI + TCC pre-grant wizard + BlackHole auto-detect + sidecar bundle + fresh-VM | "icon tap → ready to mix"; "Why we need this" inline; no API key entry, ever | bundled Homebrew, programmatic TCC, auto-update default-on, Linux installer | **M (~5-7 E-days)** | P21 + P14 wizard + Phase 38 signed binaries (HARD prereq) |
| 34 | 34 | OSS security pass | API-key audit + gitleaks + pip-audit + cargo-audit + binary-verify + SECURITY.md + STRIDE-lite + telemetry opt-in default-OFF | "audio + MIDI + screen never leaves machine" auditable claim | per-user OAuth, SOC 2, bug bounty, E2E recording encryption, PII classifier | **M (~4-6 E-days)** | P21 + Bravoh proxy |
| 35 | 35 | Real GLB + 30s viral demo | Meshy/Hunyuan3D → Mixamo → 8-12 clips + 5 prep_* replacement; ffmpeg 3-beat cut | autonomously generated; single placeholder character; anti-slop tax via real source | photorealistic mascot, multi-character, AI auto-editor pacing, AI VO script | **M (~5-7 E-days)** | P22 prep_* stubs (REPLACES) + P24 + P26 + P15 |
| 36 | 36 | Day-Zero ops live | Discord auto-provision + 15+ pre-seeded stars + 100 RPS × 5min load test + healthz + T-30/T+0/T+5/T+24h triggers | scripts version-controlled; Bravoh+vibemix coordinated push | paid launch ads at scale, influencers, pre-launch waitlist, staggered launch, AI launch posts | **M (~4-5 E-days)** | P26 day-zero + Bravoh proxy + P21 signed |
| 37 | 37 | Cross-phase integration audit | `gsd-integration-checker` re-run + orphan inventory + wiring matrix + fresh-VM smoke | gate is code-traceable; plan-ladder tracking; CRITICAL Kaan-action roll-up | live obs dashboard, distributed tracing, auto-fix orphans, 100% coverage gate | **S (~2-3 E-days)** | ALL v2.0 surfaces |
| 38 | 38 | Signing pipeline real exec | xcrun notarytool + SignPath GH Action + verifier + entitlements | autonomous after approvals; rest scripted in `release.yml` | fastlane, self-signed, DigiCert paid | **S (~1-2 E-days code; HIGH external)** | P21 + EXTERNAL Apple + SignPath |
| 39 | 39 | Public RC cut + ship | signed binary tag + `gh release create` + README finalized + 4-channel social | 30s demo film embedded in release notes; honest RC labeling; Bravoh-funnel footer | premature `v1.0.0`, bundled auto-update, cross-promo, press embargo, localized launch | **S (~2-3 E-days)** | ALL phases above |

---

## Architecture integration map

The 3-process locked architecture is **untouched**. Every v2.1 feature fits via one of three patterns: EXTEND / DOCK-TO-SLOT / NEW out-of-band.

| Phase | Bucket | Pattern | Primary integration seam |
|-------|--------|---------|--------------------------|
| 27 | Hallucination gate | **NEW out-of-band** | `scripts/eval/{replay_harness,judge,f1}.py` + `.github/workflows/eval.yml`. Only runtime touch: tiny `AudioBuffer.fill_from_wav()` helper |
| 28 | Library intelligence | **DOCK-TO-SLOT** (closes v2.0 `register_library` orphan) + **EXTEND** `EvidenceRegistry` | `__main__.py:~698-717` wires `register_library`; new `src/vibemix/library/{embed,index_sqlite_vec,index_numpy,store,search,staleness}.py`; renderer panel; 4 new IPC schemas on existing port 8765 |
| 29 | Debrief UI | **DOCK-TO-SLOT** (fills Phase 25 reservation: `--debrief` flag + port 8766 + 3 IPC reservations) | `src/vibemix/debrief/*`; `tauri/ui/src/debrief/*`; new Tauri command `open_debrief_window` |
| 30 | Hard Tek detectors | **EXTEND** Phase 17 chain (`events/genres/hard_tek.py` comment literally pre-commits) | `src/vibemix/state/detectors/{distortion_climb,acid_line_entry}.py` + extends chain + `_constants.py` |
| 31 | 4-layer mascot | **EXTEND** Phase 22 (NOT REWRITE — P47) — add Base + Emotion, keep Anticipation priority 70 + Reaction crossfades verbatim | `tauri/ui/src/mascot/state-machine.ts` + `additive-layer.ts` extends to 4 channels; NEW `priority-stack.ts` + `crossfade-policy.ts`; extend `ws_bus.py` payload with `emotion` + `reaction_intent` |
| 32 | DJ profile | **EXTEND** `DJCoHostAgent.__init__` (kwargs-only — P53) | `src/vibemix/profile/{builder,profile,cache,disclosure,sanitize}.py`; Settings panel; 1 new IPC schema |
| 33 | Install hardening | **EXTEND** Phase 11 wizard | Extend `permissions.rs` with TCC commands; `wizard/step1-permissions.ts` + `step4-onboarding.ts`; `tauri-plugin-macos-permissions` Rust crate; `install_rehearsal/` scripts + tart VM matrix |
| 34 | Security pass | **EXTEND** CI + ADD docs | NEW `.github/workflows/security.yml` (4 jobs); `.pre-commit-config.yaml`; `SECURITY.md` + `docs/threat-model.md`; `runtime/sec_check.py` |
| 35 | GLB + viral demo | **EXTEND** assets + **NEW** out-of-band pipeline | `scripts/mascot_pipeline/*` (Meshy + Mixamo); `scripts/demo_film/*` (ffmpeg 3-beat + TTS narrator); replaces 5 stub GLBs |
| 36 | Day-Zero ops | **EXTEND** Phase 26 scripts | NEW `scripts/dayzero/{discord_provision,release_publish,healthz_exporter}.py`; EXTEND `proxy_load_test.py` + `launch_trigger.sh` |
| 37 | Integration audit | **EXTEND** subagent + NEW e2e harness | NEW `tests/e2e/*`; `scripts/integration_audit.py`; `.github/workflows/integration-audit.yml` |
| 38 | Signing real exec | **EXTEND** `release.yml` (Phase 21 scaffold) | Wire real Apple + SignPath secrets; post-sign verifier; `scripts/dist/sign_windows.ps1` local rehearsal |
| 39 | RC cut + ship | **NEW** launch scripts + EXTEND `release.yml` | `scripts/launch/{publish_release,publish_social_posts,finalize_readme,cut_rc}.sh`/`.py` |

**Cross-cutting architecture invariants (DO NOT BREAK):**

1. AX bridge from **Rust ONLY** (Tauri gh #8329) — grep gate stays green
2. `state_refresh_loop` is the **only writer of MusicState** (one exception in `coach_loop`)
3. Single in-flight Gemini generation (`trigger_state["in_flight"]` + 12s stale-clear)
4. POC files (`cohost*.py`, `mascot.html`) UNTOUCHED — `test_g5_poc_files_untouched.py` gate
5. Anti-slop wired path default-on (4-kwarg `DJCoHostAgent` all-or-nothing)
6. Tauri capability allowlist locks at Wave 2
7. **Zero new processes** — DEBRIEF spawns a 2nd instance of the SAME PyInstaller binary via `--debrief` flag
8. **Zero new buses** — all v2.1 IPC fits on existing ports 8765 (live) + 8766 (debrief)
9. Shared-state discipline: extend existing stores; never create siblings

---

## Critical pitfalls (must encode in phase plans)

87 total — 46 new for v2.1 (P42-P88) + 41 v2.0 carry-forward (P1-P41).

### Critical (ship-blockers — RC cannot cut)

| ID | Pitfall | Phase | Encode in plan as |
|----|---------|-------|---------------------|
| **P42** | LLM-judge bias inflation (Gemini judges itself) | 27 | **2-judge cross-check** (Pro + Flash, different prompts, both ≥0.80) + cited-but-empty embedding-relevance filter (cosine <0.4 fails) + Kaan-veto bookmark |
| **P43** | Replay-harness corpus overfit (Kaan-only audio) | 27 | **Corpus diversity gate** — Hard Tek/techno ≤70%; ≥3 sourced public-domain sets; per-detector-per-genre F1 matrix |
| **P44** | F1 too lenient — gate accepts "I'm listening" filler | 27 | Add `useful_response_ratio ≥0.65` substance metric; per-event-class substance; bypass-rate ceiling 0.15 |
| **P45** | Citation linter gamed via "Yeah. [ev:...]" | 27, 32 | Min-8-words-around-citation rule; embedding-relevance check (orthogonal to F1) |
| **P46** | Apple Dev / SignPath autonomously "closed" via impersonation | 27, 38 | **Legal-capacity carveout — NEVER autonomously discharge.** Separate `KAAN-ACTION-LEGAL.md`. Bash audit grep against POST/PUT to apple/signpath endpoints. Memory `feedback_legal_capacity_not_autonomous` |
| **P47** | 4-layer mascot rewrite breaks v2.0 priority 70 | 31 | **Additive-only refactor, NOT clean-slate.** All v2.0 mascot tests port verbatim. Priority-70 + 2.5s timeout + cancel-aware tests preserved by exact name |
| **P48** | `register_library` final-mile orphan ships AGAIN | 28, 37 | Invocation test (not import test); end-to-end live citation test; CI grep gate; Phase 37 audit "WIRED" requires source line + fresh-VM smoke |
| **P49** | GenreRouter atomic swap breaks during Hard Tek add | 30 | Construct-time registration only (immutable dict via `MappingProxyType`); 1000-cycle stress test under 8 detectors |
| **P50** | macOS 15 Settings reorg breaks TCC pre-grant | 33 | Multi-version VM matrix (12.3 + 14 + 15); dynamic URL fallback ladder; manual-fallback inline screenshots; detection-polling pattern |
| **P51** | DJ profile leaks track titles → privacy violation | 32 | **Profile content allowlist** (no `recent_tracks`/`library_titles`/free-form strings); jsonschema `additionalProperties: false`; user consent screen |
| **P52** | Real GLBs push bundle past 350 MB hard cap | 31, 35 | CI gate <350 MB; mascot-only sub-budget ≤25 MB; per-clip <600 KB DRACO-compressed; KTX2/WebP textures; DRACO level 7+ |

### High (degrade quality even if RC ships)

- **P53** (DJCoHostAgent 5th-kwarg signature drift) → kwargs-only constructor
- **P54** (Gemini Embedding 2 180s cap silent truncation) → 3-excerpt strategy
- **P55** (sqlite-vec / numpy fallback diverge top-k Mac vs Win) → cosine + stable argsort + float32
- **P56** (embedding cost runaway) → cost projection table ≤50€/month, 24h query cache, sampled grounding
- **P57** (AI-edit demo film TikTok-style auto-cuts) → **manual editing constraint**, cut count ≤8
- **P58** (AI-voiceover script smell) → Kaan/Francesco write OR no VO; forbidden-phrase grep gate
- **P59** (pre-seeded star quality — 15 friends → 14 unstars) → aligned-community seeding only
- **P60** (token budget overflow when profile injected) → profile in CACHE not per-turn
- **P61** (Mixamo IK retargeting GLB drift) → retarget QA + SkeletonHelper visual + Rokoko fallback
- **P62** (Three.js single-mixer race when 4 layers crossfade) → 100ms stagger; p99 <22ms; cancel-priority 999
- **P63** (bundle ID change → TCC reset) → CI grep lock assertion + v2.0→v2.1 upgrade test
- **P64** (secret-scan FP flood from `AIza` fixtures) → surgical `.secrets.baseline` + placeholder convention
- **P65** (CVE auto-fail flood from transitive deps) → severity gate HIGH+ direct, CRITICAL transitives
- **P66** ("every seam validated" false confidence) → source-line AND fresh-VM smoke required
- **P67** (telemetry consent dark-pattern) → **opt-in default-OFF**; first-run explicit screen
- **P68** (README hero stale after v2.1 ships) → feature-list sync test + hero re-shoot Phase 35
- **P69** (sidecar x86_64-only → Rosetta prompt) → universal2 sidecar via lipo-merge
- **P70** (WASAPI loopback fails mid-session device change) → subscribe `IMMNotificationClient`
- **P71** (TCC revoke mid-session) → per-launch re-check + in-session graceful degrade
- **P72** (cancel-aware crossfade dropped mid-anticipation) → cancel = priority 999, queue FLUSHED

---

## Proposed Phase 27-39 decomposition

### Phase 27 — Eval Harness + v2.0 Carry-Forward Close-Out
- **Closes:** Hallucination autonomous proxy + v2.0 carry-forward + `register_library` 5-min orphan patch
- **Rationale:** Foundation tier; no v2.1 prerequisites; absorbs v2.0 audit's outstanding items
- **Delivers:** `scripts/eval/*` + `.github/workflows/eval.yml` + universal2 sidecar + WASAPI subscription + Apple/SignPath `KAAN-ACTION-LEGAL.md` prep
- **Pitfalls:** P42, P43, P44, P45, P46, P48 (5-min patch), P63, P69, P70
- **Parallel-with:** 28, 29, 30, 34
- **Research flag:** **NEEDS research-phase** — judge prompt rubric + corpus diversity sourcing

### Phase 28 — Library Intelligence v1
- **Closes:** Library intelligence (Gemini Embedding 2 + sqlite-vec + drag-drop + 30-day nudge)
- **Rationale:** Foundation tier; closes `register_library` orphan; gates Phase 32
- **Delivers:** `src/vibemix/library/*` + 4 IPC schemas + Settings → Library panel
- **Pitfalls:** P48, P54, P55, P56, P73, P74, P80
- **Parallel-with:** 27, 29, 30, 34
- **Research flag:** **NEEDS research-phase** — model ID stability + sqlite-vec Win wheel + chunk strategy tuning

### Phase 29 — Post-Session Debrief MVP UI
- **Closes:** Debrief UI (chapters + voiced TL;DR + 3 drills + clickable timeline)
- **Rationale:** Foundation tier; docks into Phase 25 DEBRIEF slot
- **Delivers:** `src/vibemix/debrief/*` + `tauri/ui/src/debrief/*` + WaveSurfer.js + `open_debrief_window` Tauri command
- **Pitfalls:** P81 (audio format), P82 (schema lock additive-only)
- **Parallel-with:** 27, 28, 30, 34
- **Research flag:** standard patterns

### Phase 30 — 2 Hard Tek Detectors (DISTORTION_CLIMB + ACID_LINE_ENTRY)
- **Closes:** Hard Tek taxonomy completion
- **Rationale:** Foundation tier; Phase 17 pre-commits to this. Gates Phase 31 + Phase 32
- **Delivers:** 2 detectors + extends `build_hard_tek_chain()` + tune_detectors output
- **Pitfalls:** P49 (construct-time registration only)
- **Parallel-with:** 27, 28, 29, 34
- **Research flag:** standard patterns — DSP recipes already locked

### Phase 31 — 4-Layer Mascot Full Additive State Machine
- **Closes:** 4-layer mascot (base + emotion + anticipation + reaction)
- **Rationale:** Sequential after Phase 30. Gates Phase 35
- **Delivers:** EXTEND `state-machine.ts` + `additive-layer.ts`; NEW `priority-stack.ts` + `crossfade-policy.ts`; extend `ws_bus.py` payload
- **Pitfalls:** P47, P62, P72
- **Parallel-with:** none (sequential after 30)
- **Research flag:** **NEEDS research-phase** — base-layer pose vocabulary + Mixamo bat-rig compatibility (couples to Phase 35)

### Phase 32 — Long-Term DJ Profile (~2KB JSON)
- **Closes:** DJ profile
- **Rationale:** Sequential after 28 + 30
- **Delivers:** `src/vibemix/profile/*` + Settings panel + DJCoHostAgent 5th kwarg
- **Pitfalls:** P51, P53, P60, P75
- **Parallel-with:** 33, 34, 35, 36 (after 28+30 land)
- **Research flag:** standard patterns

### Phase 33 — One-Click Install Hardening
- **Closes:** One-click install hardening
- **Rationale:** **Hot path** — sequenced after Phase 38; blocks Phase 39
- **Delivers:** Extend `permissions.rs`; wizard steps; `tauri-plugin-macos-permissions`; `install_rehearsal/*`; tart VM matrix
- **Pitfalls:** P50, P63, P67, P69, P71
- **Parallel-with:** 36 (after 38)
- **Research flag:** **NEEDS research-phase** — macOS 15 Sequoia TCC URL ladder undocumented

### Phase 34 — Open-Source Security Pass
- **Closes:** OSS security pass
- **Rationale:** **Land EARLY** — parallel with 27/28/29/30 so subsequent phases ship clean
- **Delivers:** `.github/workflows/security.yml` (4 jobs); `SECURITY.md` + STRIDE-lite; `runtime/sec_check.py`
- **Pitfalls:** P64, P65, P67, P77, P84
- **Parallel-with:** 27, 28, 29, 30
- **Research flag:** standard patterns

### Phase 35 — Real GLB Animations + 30s Viral Demo Film
- **Closes:** Real GLB autonomously + viral demo film
- **Rationale:** Sequential after Phase 31
- **Delivers:** `scripts/mascot_pipeline/*` (Meshy v6 + Mixamo + GLB optimizer); `scripts/demo_film/*` (ffmpeg 3-beat + Gemini TTS narrator); replaces 5 stub GLBs; bundles `demo.mp4`
- **Pitfalls:** P52, P57, P58, P61, P68, P76
- **Parallel-with:** 36
- **Research flag:** **NEEDS research-phase** — Meshy v6 vs Hunyuan3D 3.0 A/B (~$50 budget), Mixamo retarget compatibility with stylized rig

### Phase 36 — Day-Zero Ops Automation
- **Closes:** Day-Zero ops live
- **Rationale:** Sequential after Phase 21 + 26; can run parallel with 35; hard prereq for Phase 39
- **Delivers:** `scripts/dayzero/{discord_provision,release_publish,healthz_exporter}.py`; real 100 RPS × 5min load test
- **Pitfalls:** P78, P84
- **Parallel-with:** 35
- **Research flag:** standard patterns

### Phase 37 — Cross-Phase Integration Audit Gate
- **Closes:** Cross-phase integration audit
- **Rationale:** Penultimate — verifies EVERY OTHER feature wired AND fresh-VM smoke-tested
- **Delivers:** `tests/e2e/test_seam_*.py` (5+ critical seams); `scripts/integration_audit.py`; `.github/workflows/integration-audit.yml`; `v2.1-MILESTONE-AUDIT.md`
- **Pitfalls:** P48, P66, P88
- **Parallel-with:** none (sequential)
- **Research flag:** standard patterns

### Phase 38 — Signing Pipeline Real Execution
- **Closes:** Signing pipeline autonomous execution (net of legal-capacity carveout)
- **Rationale:** **Hot path bottleneck** — HIGHEST external dependency. Apple Developer Agreement (Francesco) + SignPath OSS approval must land first
- **Delivers:** Real Apple notarytool + SignPath GH Action secrets in `release.yml`; post-sign verifier; `scripts/dist/sign_windows.ps1`
- **Pitfalls:** P5/P6 (carry-forward), P46 (legal-capacity)
- **Parallel-with:** 36 once approvals start moving
- **Research flag:** standard patterns

### Phase 39 — RC Cut + Ship
- **Closes:** Public RC cut + ship
- **Rationale:** **Final.** Needs EVERY OTHER feature. The milestone gate.
- **Delivers:** `scripts/launch/*`; `gh release create v2.1.0-rc1`; 4-channel social posts; Discord launch; README hero finalized with Phase 35 demo film embedded
- **Pitfalls:** P59, P68, P78, P79, P83, P85, P86, P87
- **Parallel-with:** none
- **Research flag:** standard patterns

---

## Build-order dependency graph

```
v2.0 shipped (Phases 15-26)
   │
   ├─→ Phase 27 (Eval + carry-forward)  ──┐
   ├─→ Phase 28 (Library) ────────────┐   │
   ├─→ Phase 29 (Debrief) ────────────┤   │   (parallel cluster A)
   ├─→ Phase 30 (Hard Tek detectors) ─┤   │
   └─→ Phase 34 (Security pass) ──────┤   │
                                      │   │
              ┌───────────────────────┘   │
              ▼                            │
   Phase 31 (4-layer mascot)               │  [needs 22 + 30]
              │                            │
              ▼                            │
   Phase 32 (DJ profile)                   │  [needs 28 + 30]
              │                            │
              ▼                            │
   Phase 35 (GLB + viral demo)             │  [needs 31]
                                           │
   EXTERNAL: Apple Dev Agreement update    │
            + SignPath OSS approval        │
                  │                        │
                  ▼                        │
   Phase 38 (Signing real execution)       │  [needs external]
                  │                        │
                  ▼                        │
   Phase 33 (Install hardening)            │  [needs 11 + 38]
                  │                        │
                  ▼                        │
   Phase 36 (Day-Zero ops)                 │  [needs 21 + 26]
                  │                        │
                  ▼                        │
   Phase 37 (Integration audit) ───────────┘  [needs ALL]
                  │
                  ▼
   Phase 39 (RC cut + ship)                   [needs ALL]
```

**Parallel clusters:**
- **Cluster A (foundation, parallel):** 27 + 28 + 29 + 30 + 34
- **Cluster B (sequential after A):** 31 → 32 → 35
- **External-gated (sequential after approvals):** 38 → 33 → 36
- **Ship-prep (sequential after all):** 37 → 39

---

## Critical-path analysis

**The launch is gated by external approvals, not engineering.** Once Apple Developer Agreement (Francesco) and SignPath OSS application (Kaan) approvals land, the hot path is **4 sequential phases**:

```
external approval → Phase 38 (~1-2 E-days code) → Phase 33 (~5-7 E-days)
                  → Phase 37 (~2-3 E-days) → Phase 39 (~2-3 E-days)
```

**~10-15 E-days** of strict-sequence work after external unblocks.

The 5-phase foundation cluster (Phases 27 + 28 + 29 + 30 + 34) runs **completely in parallel** at ~8-10 E-days each. Cluster B (31 → 32 → 35) is sequential at ~13-18 E-days total.

**Roadmapper recommendation:** start Phase 38 unblocking (file SignPath OSS application + Apple agreement update prep) on day 1 in parallel with Phase 27. The external clock is the critical path; everything else can shuffle around it.

**Estimated wall-clock to RC:** **5-7 weeks of focused engineering**, aligning with PROJECT.md's "early June 2026" timeline (researched 2026-05-14 → 5 weeks = mid-June, ~1 week slip risk).

---

## Open questions for phase planners

Aggregated from STACK.md (10) + FEATURES.md cross-deps + ARCHITECTURE.md (10) + PITFALLS.md (8).

**Phase 27 (Hallucination gate):**
1. Gate threshold tuning — lock F1 + 2-judge + substance + cited-but-irrelevant thresholds against pilot corpus. `THRESHOLD-LOCK.md` co-signed by Kaan.
2. Corpus sourcing — ≥3 public-domain DJ sets across genres (archive.org / CCMixter / Free Music Archive). License-cleared.
3. `pytest-asyncio` presence — confirm if `pytest-mock` pulls transitively.

**Phase 28 (Library):**
4. sqlite-vec Win ARM64 wheel availability at phase start.
5. Gemini Embedding 2 `gemini-embedding-2-preview` model ID stability vs GA promotion.
6. Indexing UX — background vs foreground vs explicit.

**Phase 29 (Debrief):**
7. Debrief sidecar child lifecycle on WebviewWindow close — recommend (a) Rust WindowEvent listener pattern from v2.0 mascot; add second `Arc<Mutex<Option<CommandChild>>>` to `sidecar.rs:SidecarHandle`.
8. Audio format — MP3 or AAC for cross-platform webview playback.

**Phase 31 (Mascot):**
9. Base-layer pose vocabulary — Mixamo bat-rig compatibility (couples to Phase 35).
10. Layer 4 reaction triggers — hot-cue press? drop hit? Beat A overlay sync?

**Phase 32 (Profile):**
11. Profile field allowlist — beyond `preferred_genre / avg_session_duration / mix_style_tags / tempo_preference_bin / event_type_response_preferences`, what else helps grounding?
12. Profile size enforcement — UTF-8 bytes hard cap 2048; token count is the prompt-budget side effect.

**Phase 33 (Install):**
13. macOS 15 TCC URL ladder — fallback chain verified on fresh VM at phase start.
14. Tart VM cost — gate rehearsal on `workflow_dispatch` + nightly cron, not every PR.

**Phase 34 (Security):**
15. Capability-baseline lint false positives — Git-tracked snapshot pattern.
16. Telemetry field set — minimum useful set requires Kaan signoff before shipping default-OFF wizard.

**Phase 35 (GLB + viral demo):**
17. Meshy v6 vs Hunyuan3D 3.0 A/B (~$50 credit budget).
18. Pipeline idempotency — content-hash cached GLBs.
19. Veo 3.1 pricing fluctuation revisit trigger.
20. WaveSurfer cross-platform render parity (WKWebView + WebView2).

**Phase 37 (Audit):**
21. E2E test runtime cost — gate on PR-merge, not PR-open; nightly canary.
22. Out-of-tree dormant surfaces — grep `.planning/codebase/CONCERNS.md` for `register_library`-style orphans.

**Phase 38 (Signing):**
23. SignPath signing latency — `timeout-minutes: 180` + polling retry with backoff.

**Phase 39 (Ship):**
24. RC tag — `v0.2.0-rc1` vs `v1.0.0-rc1`. Kaan picks at cut.
25. Launch channel sequence — Francesco owns; resolve at plan-time.
26. Social-post-publish gate — `--auto` default-on with `--dry-run` opt-out; Discord webhook DM preview (auto-post 5 min later if no NACK).
27. Bravoh org status — `gh org view bravoh` pre-flight.

---

## Watch Out For (cross-cutting concerns)

### AI-slop traps (every phase)
- Demo film auto-pacing (P57) — manual editing only
- AI voiceover script (P58) — Kaan/Francesco write or no VO
- README hero stale (P68) — sync test + re-shoot
- Citation-but-empty responses (P45) — 8-word minimum + embedding-relevance
- Mascot uncanny valley (P76) — stylization constraint
- Profile generic tendencies — regen requires ≥2 session citations per tendency

### Scope-creep traps
- CLAP / OpenL3 / MERT (memory-locked NO)
- Vector DB servers (Qdrant / Chroma / Weaviate / Milvus)
- Multi-provider AI wrappers (LangChain / LlamaIndex)
- Stem separation, real-time generative DSP, AI-curated playlists
- Mascot multi-character / customization / `/hatch` (v2.x stretch)
- Bug-bounty / SOC 2 / E2E recording encryption
- Live observability dashboards / distributed tracing

### Autonomous-mode traps
- Legal-capacity impersonation (P46) — Apple Dev + SignPath identity NEVER autonomously discharge
- "Defer to v2.2" creep (P86) — Phase 39 deferral audit
- Grey-area decision drift (P87) — dedicated section in `v2.1-MILESTONE-AUDIT.md`
- Memory override carry-forward (P85) — Phase 16 ear-test override is v2.1 ONLY

### Integration-regression traps
- `register_library` orphan ships AGAIN (P48) — invocation test
- 4-layer mascot breaks Phase 22 priority 70 (P47) — additive-only refactor
- GenreRouter atomic swap regression (P49) — module-import-time registration
- `DJCoHostAgent` constructor drift (P53) — kwargs-only
- Bundle ID change → TCC reset (P63) — CI grep lock
- Cache 1024-token floor disturbed by profile (P60) — profile in cache
- POC files modified — `cohost*.py` untouched gate

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | **HIGH** | Read directly from `pyproject.toml` + `Cargo.toml` + `package.json`. New-add versions verified via WebSearch May 2026. |
| Features | **HIGH** | v2.0 surface dependency map read from `v2.0-MILESTONE-AUDIT.md`. MEDIUM on Hard Tek DSP thresholds, LOW on day-zero timing. |
| Architecture | **HIGH** | Built on live audit + 1961 passing tests + 220 commits. Every seam names file + line. |
| Pitfalls | **HIGH** on autonomous + integration-regression + Gemini Embedding 2 + OSS security. **MEDIUM** on mascot rewrite + viral demo. |

**Overall:** **HIGH** — milestone is mostly wiring of pre-committed seams. Known unknowns concentrated in Phase 27 (judge calibration), Phase 31 (mascot rewrite preserving priority 70), Phase 33 (macOS 15 TCC reorg), Phase 35 (Meshy/Hunyuan3D quality), Phase 38 (external approval clock).

### Gaps to address during planning
- Judge corpus diversity (Phase 27) — public-domain sets sourced + license cleared
- Meshy/Hunyuan3D A/B (Phase 35) — $50 budget; artist hire fallback as Kaan-veto item
- External signing approvals (Phase 38) — Kaan/Francesco-action; Phase 38 plan must NOT autonomously discharge (P46)
- macOS 15 TCC ladder (Phase 33) — verify at phase start; manual-fallback screenshots are always-available safety
- Bravoh org status (Phase 39) — `gh org view bravoh` pre-flight

---

*Synthesis by gsd-research-synthesizer (Opus, 2026-05-14) from STACK.md (8554 w) + FEATURES.md (11270 w) + ARCHITECTURE.md (7974 w) + PITFALLS.md (16349 w) = ~44k input words → ~6.5k synthesis.*
