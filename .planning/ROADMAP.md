# vibemix — Roadmap

**Project:** vibemix — AI DJ Co-Host
**Current milestone:** v2.1 "The Unified Cut" (IN PROGRESS — started 2026-05-14)
**Last shipped:** v2.0 Research-Driven Ship — 2026-05-14 (status: `tech_debt` accepted)

---

## Milestones

- ✅ **v0.1.0 MVP Foundation** — Phases 1–14 (shipped 2026-05-13) — see `.planning/milestones/v0.1.0/`
- ✅ **v2.0 Research-Driven Ship** — Phases 15–26 (shipped 2026-05-14, tech_debt accepted) — see `.planning/milestones/v2.0-ROADMAP.md`
- 🚧 **v2.1 The Unified Cut** — Phases 27–39 (started 2026-05-14, mode `gsd-autonomous fully`) — see "Phases" section below

---

## Phases

<details>
<summary>✅ v0.1.0 MVP Foundation (Phases 1–14) — SHIPPED 2026-05-13</summary>

See `.planning/milestones/v0.1.0/` for full archive.

</details>

<details>
<summary>✅ v2.0 Research-Driven Ship (Phases 15–26) — SHIPPED 2026-05-14 (tech_debt accepted)</summary>

12 phases shipped — 10 Claude-side end-to-end + 2 deferred to Kaan-action (Phase 15 Plan 04 UAT + entire Phase 16 ear-test gate). 38 plans, 1961 passing tests, 220 commits since `v0.1.0-rc1`, ~45.7k LOC across `src/vibemix/`, `tauri/`, `scripts/`, `tests/`.

- [x] Phase 15: Recording Browser + Retention Enforcement (3/4 plans — Plan 04 deferred) — completed 2026-05-14
- [ ] Phase 16: Hallucination Verification Gate (Kaan's DJ Ear) — DEFERRED entire phase (`16-DEFERRED.md`); replaced for v2.1 by Phase 27 autonomous proxy
- [x] Phase 17: Hard Tek Detectors v1 + GenreRouter + MusicState Extension (6/6 plans) — completed 2026-05-14
- [x] Phase 18: Evidence Registry + Citation Grammar (4/4 plans) — completed 2026-05-14
- [x] Phase 19: Latency Stack v1 — Ack Bank + Cached Content + Cancel-and-Refire (5/5 plans) — completed 2026-05-14
- [x] Phase 20: Citation Linter ENFORCEMENT (Live Mode) (5/5 plans) — completed 2026-05-14
- [x] Phase 21: Sign + Notarize + GitHub Release Matrix (1/1 plan; external approvals = Kaan-action) — completed 2026-05-14
- [x] Phase 22: Mascot Anticipation Layer + Beat-Coupled Hip-Bob (2/2 plans; real GLBs = artist) — completed 2026-05-14
- [x] Phase 23: 10-SKU MIDI Controller Library + MidiMapLoader (2/2 plans; hardware sniff = Kaan) — completed 2026-05-14
- [x] Phase 24: djay Pro Mac Overlay Highlight (2/2 plans; signed-bundle verdict = Kaan) — completed 2026-05-14
- [x] Phase 25: Pyrekordbox XML + DEBRIEF Architectural Slot (3/3 plans) — completed 2026-05-14
- [x] Phase 26: README + Branding + Day-Zero Ops + Viral Demo + Channel Posts (4/4 plans; Waves 3/4/6-Discord/7 = Kaan) — completed 2026-05-14

Full archive: `.planning/milestones/v2.0-ROADMAP.md` · Requirements: `.planning/milestones/v2.0-REQUIREMENTS.md` · Audit: `.planning/milestones/v2.0-MILESTONE-AUDIT.md`

</details>

### 🚧 v2.1 The Unified Cut (Phases 27–39, IN PROGRESS)

Started 2026-05-14 via `/gsd-new-milestone`. Public OSS RC milestone — close every v2.0 carry-forward + ship integration + library + debrief + 4-layer mascot + DJ profile + Hard Tek + install harden + security + viral + day-zero + RC.

**Mode:** `gsd-autonomous fully` — every blocker + human-needed item discharged autonomously (only privacy rule + destructive risk + legal-capacity carveouts still pause). Phase 16 ear-test memory override accepted for v2.1 only (autonomous replay + LLM-judge proxy gate substitutes for Kaan-ear-only path).

**Phase summary checklist:**

- [ ] **Phase 27: Eval Harness + v2.0 Carry-Forward Close-Out** — Autonomous hallucination proxy gate + sidecar universal2 + WASAPI subscription + Achird OPUS render + FLX4 sync sniff + `register_library` 5-min orphan patch. REQ count: 14. Pitfalls: P42, P43, P44, P45, P48, P63, P69, P70 (+ P46 legal-carveout prep).
- [ ] **Phase 28: Library Intelligence v1** — Gemini Embedding 2 + sqlite-vec / numpy fallback · vibe search · "what's playing" grounding · drag-drop UI · 30-day staleness nudge. REQ count: 9. Pitfalls: P48, P54, P55, P56.
- [ ] **Phase 29: Post-Session Debrief MVP UI** — Chaptered review · 60–90s voiced TL;DR · 3 drills · clickable timeline · cited critique. REQ count: 9. Pitfalls: P81, P82.
- [x] **Phase 30: 2 Hard Tek Detectors** — `DISTORTION_CLIMB` + `ACID_LINE_ENTRY` (taxonomy completion). REQ count: 4. Pitfalls: P49. Shipped 2026-05-15 — 45 tests pass, 1000-cycle race gate green, 0 code-review findings.
- [x] **Phase 31: 4-Layer Mascot Full Additive State Machine** — Base + Emotion + Anticipation + Reaction (EXTENDS v2.0, never rewrites). REQ count: 8. Pitfalls: P47, P62, P72. Shipped 2026-05-15 — 17/17 mascot tests pass, 8/8 plans committed, GLB sub-budget 21.67/25 MB green.
- [x] **Phase 32: Long-Term DJ Profile (~2KB JSON)** — Post-session regen + verbatim cache-side inject + content allowlist. REQ count: 7. Pitfalls: P51, P53, P60. Shipped 2026-05-15 — 6/6 plans committed, 61 backend tests + 6 UI tests green, P51/P53/P60 privacy gates enforced.
- [ ] **Phase 33: One-Click Install Hardening** — TCC pre-grant wizard + BlackHole auto-detect + fresh-VM rehearsal + sidecar polish + first-launch onboarding. REQ count: 9. Pitfalls: P50, P63, P67, P69, P71.
- [ ] **Phase 34: Open-Source Security Pass** — Secret scanner + dep CVE + SBOM + STRIDE-lite + signed-binary verify + SECURITY.md + telemetry opt-in default-OFF. REQ count: 10. Pitfalls: P64, P65, P67.
- [ ] **Phase 35: Real GLB Animations + 30s Viral Demo Film** — Meshy v6 / Hunyuan3D + Mixamo auto-rig + 5 `prep_*` replacement + ffmpeg 3-beat cut + bundled `demo.mp4`. REQ count: 7. Pitfalls: P52, P57, P58, P61, P68.
- [ ] **Phase 36: Day-Zero Ops Automation** — Discord auto-provision + 100 RPS × 5min real load test + pre-seeded star coordination + launch trigger sequence + healthz live. REQ count: 6. Pitfalls: P59, P78.
- [ ] **Phase 37: Cross-Phase Integration Audit Gate** — `tests/e2e/test_seam_*` + integration audit script + orphan inventory + grey-area decision log. REQ count: 7. Pitfalls: P48, P66, P87.
- [ ] **Phase 38: Signing Pipeline Real Execution** — Apple notarytool + SignPath GH Action wired with real secrets + post-sign verifier + Kaan local rehearsal script. REQ count: 7. Pitfalls: P46 (legal carveout — autonomous discharge FORBIDDEN).
- [ ] **Phase 39: Public RC Cut + Ship** — Signed binary tagged · `gh release create` · 4-channel social · Discord launch · README hero finalized · post-launch monitoring rotation. REQ count: 8. Pitfalls: P59, P68, P78, P79, P83, P85, P86, P87.

**Critical path:** External Apple Developer Program Agreement update (Francesco-action) + SignPath OSS Foundation application (Kaan-action) → **Phase 38** → **Phase 33** → **Phase 37** → **Phase 39**. Approvals are **legal-capacity carveouts** that NEVER autonomously discharge (Pitfall P46). Engineering is parallelizable to fit; the external clock is the bottleneck.

**Day-1 unblock action:** File SignPath OSS Foundation application + start Apple Developer Program Agreement update prep on day 1, in parallel with Phase 27 execution. Track in `.planning/phases/38-signing-pipeline-real-execution/KAAN-ACTION-LEGAL.md` once Phase 38 scaffolds.

**Parallel cluster A (foundation, start day 1):** Phases 27 + 28 + 29 + 30 + 34.
**Sequential cluster B (after cluster A):** Phase 31 (needs 30) → Phase 32 (needs 28+30) → Phase 35 (needs 31).
**External-gated sequential (after approvals):** Phase 38 → Phase 33 → Phase 36.
**Ship prep sequential (after ALL):** Phase 37 → Phase 39.

**Estimated wall-clock to RC:** **5–7 weeks of focused engineering** (research-grade confidence). External clock (Apple + SignPath approvals) is the critical path; engineering is parallelizable to fit. No hard calendar target — ship-when-ready per `gsd-autonomous fully` mode.

**Bar:** 1000+ GitHub stars · "real DJ friend in your ear, no AI slop" · clean install zero friction · autonomous discharge of every Kaan-action surface except the two legal-capacity items.

Full archive when shipped: `.planning/milestones/v2.1-ROADMAP.md`.

---

## Phase Details

### Phase 27: Eval Harness + v2.0 Carry-Forward Close-Out
**Goal:** Autonomous hallucination-proxy gate satisfies the v2.1 ship bar in place of Phase 16's Kaan-ear-only test; every v2.0 tech-debt carry-forward closed at runtime.
**Depends on:** v2.0 shipped (Phases 15–26)
**Requirements:** EVAL-01, EVAL-02, EVAL-03, EVAL-04, EVAL-05, EVAL-06, EVAL-07, EVAL-08, LIBRARY-09, REC-09, LATENCY-14, LATENCY-15, MASCOT-11, MIDI-20
**Success Criteria** (what must be TRUE):
  1. A recorded DJ session in `recordings/<session>/` can be replayed end-to-end through shipped P17 detectors + P18 EvidenceRegistry + P19 ack bank + P20 linter + P22 anticipation via `scripts/eval/replay_harness.py` — deterministic, single-binary, no GPU.
  2. Both Gemini 3 Pro and Gemini 3 Flash judges (different rubric prompts) score the corpus ≥ 0.80 F1; substance metric `useful_response_ratio ≥ 0.65`; cited-but-irrelevant cosine ≥ 0.4; bypass rate ≤ 0.15. Thresholds locked in `THRESHOLD-LOCK.md` co-signed by Kaan.
  3. `.github/workflows/eval.yml` runs the harness on PR merge + nightly canary and fails the build below threshold; per-run scorecards committed under `.planning/eval-runs/`.
  4. `EvidenceRegistry.register_library` is invoked from `__main__.py:~668-689` (research-corrected from prior `698-717`) when `~/.cache/vibemix/library.pkl` exists; invocation test + end-to-end live citation test both pass.
  5. macOS sidecar ships per Tauri target-triple convention (`vibemix-sidecar-aarch64-apple-darwin` + `vibemix-sidecar-x86_64-apple-darwin`) — research-corrected from `lipo`-merge approach which is technically infeasible per PyInstaller upstream (PKG archive embedded in only the last merged slice). Apple Silicon users never see a Rosetta prompt; Windows WASAPI loopback subscribes to `IMMNotificationClient` so a mid-session default-device change no longer crashes the session.
  6. 40 silent Achird-voice OPUS placeholders are replaced one-for-one via offline Gemini TTS Achird voice batch render; AIza-key scan re-runs zero matches.
  7. DDJ-FLX4 Sync note disambiguation is locked via autonomous synthetic MIDI replay against fixture synthesized from `cohost_v4.py` `_NOTE_MAP` (POC-confirmed: note 0x60 verified, note 0x58 alt = tentative).
**Critical pitfalls:** P42 (LLM-judge self-bias → 2-judge cross-check), P43 (corpus overfit → diversity gate, ≥ 3 sets, Hard Tek ≤ 70%), P44 (lenient F1 → substance metric), P45 (cited-but-empty → embedding-relevance), P46 (legal carveout NEVER autonomous → `KAAN-ACTION-LEGAL.md` prep starts here), P48 (`register_library` orphan), P63 (bundle ID lock), P69 (universal2 sidecar — RESEARCH critical correction → target-triple convention not lipo-merge), P70 (WASAPI device change).
**Parallel-with:** P28, P29, P30, P34.
**Plans:** 2/9 plans executed
- [x] 27-01-PLAN.md — Replay Harness Core (EVAL-01 + EVAL-08): scripts/eval/replay_harness.py + AudioBuffer.fill_from_wav + F1 math + scorecard renderer
- [ ] 27-02-PLAN.md — 2-Judge Cross-Check Architecture (EVAL-02 + EVAL-04 + EVAL-05): Pro+Flash rubrics + Gemini Embedding 2 cited-relevance + VCR cassettes
- [ ] 27-03-PLAN.md — Corpus Assembly + Diversity Gate (EVAL-03): 6 public-domain DJ sessions + manifest.json + LICENSES.md + git-LFS
- [ ] 27-04-PLAN.md — Threshold Lock + CI Gate (EVAL-06 + EVAL-07 + EVAL-08 commit lifecycle): autonomous-signed THRESHOLD-LOCK.md + .github/workflows/eval.yml + KAAN-ACTION-LEGAL.md
- [x] 27-05-PLAN.md — register_library Wire-In (LIBRARY-09): 5-line patch in __main__.py + invocation test + end-to-end citation test
- [ ] 27-06-PLAN.md — REC-09 Tauri Target-Triple Sidecars (CRITICAL CORRECTION over lipo-merge): build_sidecar.py --target-arch + release.yml matrix + tauri.conf.json5 externalBin
- [ ] 27-07-PLAN.md — WASAPI IMMNotificationClient Subscription (LATENCY-14): non-blocking COM callback + worker thread soft-restart + macOS stub
- [ ] 27-08-PLAN.md — 40 Achird OPUS Ack Regeneration (LATENCY-15): scripts/generate_ack_audio.py + manifest.json + AIza scan zero matches
- [ ] 27-09-PLAN.md — FLX4 Sync Sniff Disambiguation + MASCOT-11 Tracking Pointer (MIDI-20 + MASCOT-11): synthesized fixture from cohost_v4.py POC + ddj-flx4.json verdict + MASCOT-11 carry-forward documented as Phase 35 ASSETS-03 pointer

### Phase 28: Library Intelligence v1
**Goal:** vibemix's spoken reactions can cite tracks from the user's library by name + the user can vibe-search the library in plain English — closing the architectural-slot reservation left in v2.0 Phase 25.
**Depends on:** v2.0 Phase 25 (`register_library` slot + Rekordbox XML parser).
**Requirements:** LIBRARY-10, LIBRARY-11, LIBRARY-12, LIBRARY-13, LIBRARY-14, LIBRARY-05, LIBRARY-15, LIBRARY-16, LIBRARY-17
**Success Criteria** (what must be TRUE):
  1. After dragging a folder onto Settings → Library, the user sees an import progress indicator, and every imported track gets a Gemini Embedding 2 vector cached locally (sqlite-vec on Mac, numpy on Windows — identical cosine + stable argsort + float32).
  2. Typing a natural-language English query ("driving acid techno around 138 BPM, dark intro") returns ranked matches with confidence scores via CLI + IPC.
  3. While the user is mixing, vibemix emits `[track:<id>]` citations identifying the currently playing track when its 3-excerpt audio embedding matches the library at cosine ≥ 0.7.
  4. 30 days after the last import, the UI prompts "Looks like you've added new tracks — re-import to keep me grounded".
  5. Embedding cost stays under €50/month via 24h query cache + sampled grounding + content-hash dedupe.
**Critical pitfalls:** P48 (register_library final-mile orphan), P54 (180s embedding cap → 3-excerpt strategy), P55 (Mac/Win top-k divergence), P56 (embedding cost runaway).
**Parallel-with:** P27, P29, P30, P34.
**Plans:** 8/9 plans executed
- [x] 28-01-PLAN.md — Gemini Embedding 2 client + content-hash cache + shared cosine_topk (LIBRARY-10)
- [x] 28-02-PLAN.md — sqlite-vec + numpy store backends + Mac/Win parity gate (LIBRARY-11; Wave 0 ARM64 Win probe)
- [x] 28-03-PLAN.md — Vibe-search NL query + 24h cache + CLI subcommand (LIBRARY-12)
- [x] 28-04-PLAN.md — Event-gated grounding + DJCoHostAgent citation injection + P48 invocation/E2E tests (LIBRARY-13; Wave 0 Bravoh proxy probe)
- [x] 28-05-PLAN.md — Track-to-track similarity USER-ASKED-only (LIBRARY-14; anti-feature regression guard)
- [x] 28-06-PLAN.md — Drag-drop import UX + Tauri 2 dedupe + progress bar (LIBRARY-05; vanilla TS)
- [x] 28-07-PLAN.md — 30-day staleness nudge + UI banner + 7-day snooze (LIBRARY-15)
- [ ] 28-08-PLAN.md — Cost projection + runtime telemetry + CI hard gate ≤ €50 (LIBRARY-16; Option B locked)
- [x] 28-09-PLAN.md — 10 new IPC schemas on port 8765 + Python/TS codegen parity (LIBRARY-17)
**UI hint:** yes

### Phase 29: Post-Session Debrief MVP UI
**Goal:** After a session, the user can open a Debrief window that walks them through what happened — chapters, voiced TL;DR, drills, and a clickable waveform timeline — every advice line cited from session evidence.
**Depends on:** v2.0 Phase 25 (DEBRIEF sidecar `--debrief` flag + port 8766 + 3 IPC reservations) + v2.0 Phase 15 (recording browser).
**Requirements:** DEBRIEF-03, DEBRIEF-04, DEBRIEF-05, DEBRIEF-06, DEBRIEF-07, DEBRIEF-08, DEBRIEF-09, DEBRIEF-10, DEBRIEF-11
**Success Criteria** (what must be TRUE):
  1. From Settings → Recordings, clicking "Open Debrief" on any past session opens a second WebviewWindow (label="debrief", 1280×720) and spawns the existing PyInstaller binary with `--debrief <session_dir>` on port 8766.
  2. The window renders auto-derived chapter markers, plays a 60–90s Gemini-TTS voiced TL;DR (MP3) inside WaveSurfer.js, and lets the user click any region to seek + see the citation tooltip.
  3. Every advice line in the debrief references `[ev:*]`, `[track:*]`, or `[mix:*]` from the session EvidenceRegistry snapshot; un-cited critique is stripped.
  4. The Rust `WindowEvent::CloseRequested` handler tears down the debrief sidecar child via `Arc<Mutex<Option<CommandChild>>>` in `sidecar.rs` — no orphan processes.
  5. `debrief.v1` jsonschema is locked additive-only — no breaking changes across v2.1.
**Critical pitfalls:** P81 (audio format cross-webview parity → MP3 verified on WKWebView + WebView2), P82 (schema lock additive-only).
**Parallel-with:** P27, P28, P30, P34.
**Plans:** 1/9 plans executed
- [x] 29-00-PLAN.md — Wave 0 unblock: capability allowlist + EvidenceRegistry snapshot + __main__ short-circuit + Wave 0 probes (A1/A3/A5/A7)
- [ ] 29-01-PLAN.md — Python debrief/ package: chapters / tldr / drills / stripper / persistence / session_loader (DEBRIEF-03/04/06/07)
- [ ] 29-02-PLAN.md — --debrief sidecar mode + ws_server on 127.0.0.1:8766 + progressive emit (DEBRIEF-08/09)
- [ ] 29-03-PLAN.md — debrief.v1 schema lock: 5 new wrappers + P82 additive-only baseline gate (DEBRIEF-10)
- [ ] 29-04-PLAN.md — Rust debrief_window.rs: open_debrief_window command + DebriefSidecarHandle + close-event handler (DEBRIEF-08/09)
- [ ] 29-05-PLAN.md — Vanilla TS UI: debrief.html + 6 components + WaveSurfer v7.12.7 + CDJ Whisper styling (DEBRIEF-03/04/05/06)
- [ ] 29-06-PLAN.md — Settings → Recordings Open Debrief 5th button + disable gate (DEBRIEF-11)
- [ ] 29-07-PLAN.md — Cited-critique stripping integration into TLDR + drills + TS defense-in-depth (DEBRIEF-07 hard gate)
- [ ] 29-08-PLAN.md — End-to-end smoke + cross-platform verdict (Mac WKWebView + Win WebView2)
**UI hint:** yes

### Phase 30: 2 Hard Tek Detectors (DISTORTION_CLIMB + ACID_LINE_ENTRY)
**Goal:** Complete the v2.0 6-detector taxonomy with the 2 Hard Tek overlays Phase 17 pre-committed to, so Hard Tek sessions get the same DSP-grounded event firing as techno/house.
**Depends on:** v2.0 Phase 17 (GenreRouter + `build_hard_tek_chain` slot).
**Requirements:** SENSE-17, SENSE-18, SENSE-19, SENSE-20
**Success Criteria** (what must be TRUE):
  1. During a Hard Tek session, `DISTORTION_CLIMB` fires on band-limited spectral-flatness rise + harmonic-distortion proxy + sustained kick density (6s cooldown), citing `[ev:DISTORTION_CLIMB@<t>]` with `chain_position` + `distortion_db` fields.
  2. `ACID_LINE_ENTRY` fires on TB-303-style 200–800Hz formant-sweep autocorr + resonance-rise envelope (8s cooldown), citing `[ev:ACID_LINE_ENTRY@<t>]` with `formant_hz` + `resonance_q` fields.
  3. `GenreRouter` registers all 8 detectors at construct time only (immutable `MappingProxyType`); a 1000-cycle stress test passes without race or atomic-swap regression.
  4. `scripts/tune_detectors.py` runs against Kaan-curated Hard Tek reference tracks (documented in `eval/corpus/hard_tek/README.md`) and produces tuning evidence.
**Critical pitfalls:** P49 (GenreRouter atomic swap break during add).
**Parallel-with:** P27, P28, P29, P34.
**Plans:** TBD

### Phase 31: 4-Layer Mascot Full Additive State Machine
**Goal:** The mascot reacts on 4 simultaneous channels (base breathing + emotion + anticipation + reaction) with priority-stacked crossfades — extends the v2.0 simplified anticipation subset without breaking it.
**Depends on:** v2.0 Phase 22 (anticipation priority 70 + ws_bus) + Phase 30 (genre-driven emotion mapping).
**Requirements:** MASCOT-20, MASCOT-21, MASCOT-22, MASCOT-23, MASCOT-24, MASCOT-25, MASCOT-26, MASCOT-27
**Success Criteria** (what must be TRUE):
  1. Base layer (idle breathing + sway, priority 50) plays continuously and is never canceled; Emotion layer (4 states {neutral, focused, hyped, concerned}, priority 60) shifts based on `MusicState.active_genre` + `energy_band`; Anticipation layer (priority 70) keeps v2.0 cancel-aware behavior verbatim; Reaction layer (priority 80) fires on cited `[emote:*]` tags from Gemini.
  2. All v2.0 mascot test names port verbatim into the 4-layer rig and pass — including priority-70 + 2.5s timeout + cancel-aware + linter-strip-aware (P47 evidence).
  3. Simultaneous layer transitions cross-fade with 100ms stagger; vitest perf test holds frame budget p99 < 22ms; cancel = priority 999 flushes the queue.
  4. `additive-layer.ts` extends 3 → 4 channels (per v2.0 marker comment) and passes SkeletonHelper visual regression.
  5. Total mascot GLB bundle ≤ 25 MB on CI gate (sub-budget under 350 MB hard cap).
**Critical pitfalls:** P47 (additive-only refactor — NEVER clean-slate rewrite), P62 (Three.js single-mixer race → 100ms stagger), P72 (cancel-aware dropped mid-anticipation → priority 999 + queue flush).
**Parallel-with:** none (sequential after P30).
**Plans:** TBD
**UI hint:** yes

### Phase 32: Long-Term DJ Profile (~2KB JSON)
**Goal:** vibemix remembers what kind of DJ the user is across sessions via a tiny content-allowlisted JSON profile that gets cache-side injected into every new live prompt — personalizing coaching without leaking track titles or letting the profile drift generic.
**Depends on:** v2.0 Phase 25 (DEBRIEF data) + v2.0 Phase 10 (prompt matrix) + Phase 28 (library citations).
**Requirements:** PROFILE-01, PROFILE-02, PROFILE-03, PROFILE-04, PROFILE-05, PROFILE-06, PROFILE-07
**Success Criteria** (what must be TRUE):
  1. After each session, `src/vibemix/profile/builder.py` regenerates a profile ≤ 2048 UTF-8 bytes containing only allowlist fields (`preferred_genre`, `avg_session_duration`, `mix_style_tags` ≤ 8 items, `tempo_preference_bin`, `event_type_response_preferences`) — jsonschema `additionalProperties: false` rejects anything else (no `recent_tracks`, no free-form strings).
  2. The profile lives in `GeminiContextCache` (NOT per-turn prompt prefix), preserving the 1024-token floor + 4min refresh contract.
  3. `DJCoHostAgent.__init__` accepts a 5th kwarg `profile=` (kwargs-only); `None` keeps v2.0 4-kwarg path byte-identical (P53 prevention).
  4. First-launch wizard exposes a default-OFF "Build a profile?" consent toggle with field-set disclosure; Settings → Profile lets the user view + delete + regenerate-now.
  5. Each tendency field requires ≥ 2 session citations from EvidenceRegistry to regenerate, preventing generic-tendency drift.
**Critical pitfalls:** P51 (privacy → content allowlist + size cap), P53 (kwargs-only constructor), P60 (cache 1024-token floor preserved by cache-side inject).
**Parallel-with:** P33, P34, P35, P36 (after P28 + P30 land).
**Plans:** TBD
**UI hint:** yes

### Phase 33: One-Click Install Hardening
**Goal:** "Icon tap → grant permissions → ready to mix" zero-friction onboarding on a fresh Mac + Windows VM in ≤ 60s; no API key entry surface ever exists.
**Depends on:** v2.0 Phase 11 (wizard) + Phase 38 (signed binary — HARD prereq).
**Requirements:** INSTALL-01, INSTALL-02, INSTALL-03, INSTALL-04, INSTALL-05, INSTALL-06, INSTALL-07, INSTALL-08, INSTALL-09
**Success Criteria** (what must be TRUE):
  1. On a fresh macOS 12.3 / 14 / 15 VM, the TCC permissions wizard deep-links to Microphone + Screen Recording + Accessibility + Automation Settings panes via the right URL for that macOS version (fallback ladder verified) — with "Why we need this" copy per permission.
  2. On a fresh Windows 10/11 VM, the signed MSI installs without Defender SmartScreen warning (publisher reputation seeded via SignPath OSS chain); fallback KB article linked if reputation hasn't propagated yet.
  3. If BlackHole 2ch is absent on Mac, the sidecar offers a one-click install button; first-launch onboarding finishes (permissions + audio device pick + controller probe + AI test reaction) within 60 seconds.
  4. If the user revokes a TCC permission mid-session, vibemix toasts "Microphone access lost — paused" and degrades gracefully without crashing.
  5. CI grep asserts `world.bravoh.vibemix` bundle ID at every build; v2.0 → v2.1 upgrade test verifies TCC permissions carry over; no UI surface accepts a user-supplied Gemini key (assertion test).
**Critical pitfalls:** P50 (macOS 15 Settings reorg → multi-version VM matrix + fallback ladder), P63 (bundle ID change → TCC reset → CI grep lock), P67 (telemetry opt-in default-OFF), P69 (universal2 sidecar carry-forward verified), P71 (TCC revoke mid-session graceful degrade).
**Parallel-with:** P36 (after P38).
**Plans:** TBD
**UI hint:** yes

### Phase 34: Open-Source Security Pass
**Goal:** vibemix's repo + binary + runtime claims survive public-OSS scrutiny — no leaked secrets, no critical CVEs, signed binary verifiable, telemetry opt-in default-OFF, threat model documented.
**Depends on:** v2.0 Phase 21 (CI scaffold) + Bravoh proxy infrastructure.
**Requirements:** SEC-01, SEC-02, SEC-03, SEC-04, SEC-05, SEC-06, SEC-07, SEC-08, SEC-09, SEC-10
**Success Criteria** (what must be TRUE):
  1. gitleaks pre-commit + GitHub Actions secret-scan job blocks any commit/PR with a real key; surgical `.secrets.baseline` allowlist documents AIza-fixture placeholders.
  2. `pip-audit` + `osv-scanner` (Python) and `cargo-audit` + `cargo-deny` (Rust) gate the build at severity HIGH+ on direct deps and CRITICAL on transitives.
  3. Each release publishes a syft-generated `sbom.spdx.json` + a post-sign verifier job that checksum+signature-validates artifacts before publish.
  4. `SECURITY.md` (disclosure policy + PGP key + supported versions) + `docs/threat-model.md` (STRIDE-lite covering proxy rate-limit bypass + key extraction + telemetry exfil + supply chain) ship + are linked from README first-screen.
  5. First-run wizard shows an explicit default-OFF telemetry consent screen with field-set disclosure; `runtime/sec_check.py` boot banner makes the "audio + MIDI + screen never leaves machine" claim auditable from outbound-connection inventory.
  6. Tauri capabilities snapshot is git-tracked; CI diff-fails on unexpected capability addition.
**Critical pitfalls:** P64 (secret-scan FP flood → surgical baseline), P65 (CVE flood → severity gate), P67 (telemetry consent default-OFF, no dark pattern).
**Parallel-with:** P27, P28, P29, P30.
**Plans:** TBD

### Phase 35: Real GLB Animations + 30s Viral Demo Film
**Goal:** Replace the v2.0 placeholder GLBs with real Mixamo-rigged animations + ship a 30s viral demo film embedded in the GitHub release + README hero.
**Depends on:** Phase 31 (4-layer mascot rig) + v2.0 Phase 22 (`prep_*` stubs) + v2.0 Phase 24 (overlay) + v2.0 Phase 26 (day-zero scaffold) + v2.0 Phase 15 (recording).
**Requirements:** ASSETS-01, ASSETS-02, ASSETS-03, ASSETS-04, ASSETS-05, ASSETS-06, ASSETS-07
**Success Criteria** (what must be TRUE):
  1. A winning 3D mascot model is selected via Meshy v6 vs Hunyuan3D 3.0 A/B against a ~$50 credit budget; output is content-hash cached.
  2. The mascot is Mixamo-auto-rigged with 8–12 motion clips (idle, walk, lean-in, react-hyped, react-concerned, react-cancel, speak-open, speak-close); SkeletonHelper visual QA passes; Rokoko fallback documented.
  3. The 5 v2.0 `prep_*` placeholder clips are replaced one-for-one with real GLBs while preserving Phase 22-02 idle-zero lower-body delta contract; per-clip ≤ 600 KB DRACO L7+ + KTX2/WebP; total mascot ≤ 25 MB on CI.
  4. A 30s viral demo film (`demo.mp4`) is cut from a real DJ session screen capture via manual ffmpeg editing (cut count ≤ 8 per anti-slop bar); 3-beat structure (Beat A overlay highlight, Beat B mascot lean-in BEFORE voice, Beat C cited reaction); voiceover is Kaan/Francesco-written or no VO.
  5. `demo.mp4` ships in the GitHub Release assets + is embedded in the README hero block; CI sync test fails if the README hero hash drifts from the released `demo.mp4`.
**Critical pitfalls:** P52 (350 MB bundle cap → sub-budget enforcement), P57 (AI auto-cut pacing → manual editing, ≤ 8 cuts), P58 (AI voiceover slop → human or no VO), P61 (Mixamo IK retarget drift → SkeletonHelper QA + Rokoko fallback), P68 (README hero stale after ship → sync test).
**Parallel-with:** P36.
**Plans:** TBD
**UI hint:** yes

### Phase 36: Day-Zero Operations Automation
**Goal:** Public launch day operates from version-controlled scripts — Discord up, healthz live, proxy load-tested at real RPS, star coordination ready, launch trigger sequence one command away.
**Depends on:** v2.0 Phase 21 (CI) + v2.0 Phase 26 (day-zero scaffold) + Bravoh proxy.
**Requirements:** OPS-09, OPS-10, OPS-11, OPS-12, OPS-13, OPS-14
**Success Criteria** (what must be TRUE):
  1. `scripts/dayzero/discord_provision.py` creates the `vibemix` Discord server end-to-end with roles (founder / contributor / DJ / lurker) + channels (#announcements, #help, #show-and-tell, #controllers, #ai-misbehavior, #dev).
  2. A real 100 RPS × 5 minute load test against `api.altidus.world/vibemix` passes p99 < 500ms; pass artifact archived under `.planning/eval-runs/`.
  3. `scripts/dayzero/healthz_check.sh` runs as a real cron and alerts to a Discord webhook on failure; `api.altidus.world/healthz` returns 200 OK on canary.
  4. 15+ pre-seeded stars are sourced from aligned communities (Bravoh team + DJ network + ARRAY community + contributor friends — NOT 15 random friend-favors that unstar next week); Day-1 list logged.
  5. `scripts/dayzero/launch_trigger.sh` orchestrates the T-30 / T+0 / T+5 / T+24h sequence with `--dry-run` preview before any post publishes.
**Critical pitfalls:** P59 (15-friend star-unstar pattern → aligned-community sourcing), P78 (launch timing drift → dry-run preview gate).
**Parallel-with:** P35.
**Plans:** TBD

### Phase 37: Cross-Phase Integration Audit Gate
**Goal:** Penultimate gate — every cross-phase seam is end-to-end verified + fresh-VM smoke-tested + zero orphan-but-shipped surfaces remain + every grey-area autonomous decision is logged.
**Depends on:** all v2.1 phases shipped (27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 38).
**Requirements:** AUDIT-01, AUDIT-02, AUDIT-03, AUDIT-04, AUDIT-05, AUDIT-06, AUDIT-07
**Success Criteria** (what must be TRUE):
  1. `tests/e2e/test_seam_*.py` covers ≥ 5 critical seams (P18 → P20, P19 → agent, P25 → P28, P27 → eval-gate, P31 → ws_bus) and passes on a fresh VM.
  2. `scripts/integration_audit.py` extends v2.0's `gsd-integration-checker` and produces a fresh `v2.1-MILESTONE-AUDIT.md` with WIRED/PARTIAL/MISSING per seam — PASS requires a real source line + a fresh-VM smoke result.
  3. `.planning/codebase/CONCERNS.md` orphan inventory is current; CI fails on any new orphaned-but-shipped surface added in v2.1.
  4. The Kaan-action surface roll-up contains only the two legal-capacity items (Apple Developer Program Agreement update + SignPath OSS application) — nothing else is allowed.
  5. `v2.1-MILESTONE-AUDIT.md` includes a dedicated "Grey-Area Decisions" section listing every recommended autonomous answer with rationale (P87 enforcement).
  6. `test_g5_poc_files_untouched.py` v2.1 modified-files allowlist still holds — `cohost*.py` POC files untouched.
**Critical pitfalls:** P48 (register_library final-mile verified ONCE MORE), P66 ("every seam validated" false confidence → source line + fresh-VM smoke required), P87 (grey-area drift → dedicated log).
**Parallel-with:** none (sequential).
**Plans:** TBD

### Phase 38: Signing Pipeline Real Execution
**Goal:** Real Apple notarytool + real SignPath GH Action wired into `release.yml`; signed binaries verifiable end-to-end. The two legal-capacity human-signature submissions remain in `KAAN-ACTION-LEGAL.md` and are NEVER autonomously discharged.
**Depends on:** v2.0 Phase 21 CI scaffold + EXTERNAL: Apple Developer Program Agreement update (Francesco-action) + SignPath OSS Foundation application (Kaan-action).
**Requirements:** DIST-15, DIST-16, DIST-17, DIST-18, DIST-09, DIST-11, DIST-19
**Success Criteria** (what must be TRUE):
  1. `release.yml` invokes real `xcrun notarytool` with real Apple Developer ID secrets injected; staple + validate run post-sign.
  2. `release.yml` invokes real SignPath GH Action with real SignPath credentials; Windows MSI signs successfully and publisher reputation is propagating.
  3. A post-sign verifier job validates checksum + signature on every artifact before release publish blocks pass.
  4. `scripts/dist/sign_windows.ps1` lets Kaan rehearse the Windows signing flow on his machine before relying on CI.
  5. Kaan runs `bash tauri/src-tauri/spike/sign-and-test.sh` on the signed binary (closes v2.0 OVERLAY-02 Wave-0 verdict).
  6. `KAAN-ACTION-LEGAL.md` documents the Apple Developer Program Agreement update (Francesco-action) + SignPath OSS Foundation application (Kaan-action) protocols; CI bash audit grep against POST/PUT to apple/signpath endpoints catches any autonomous-discharge attempt.
**Critical pitfalls:** P46 (legal-capacity carveouts NEVER autonomous — Apple + SignPath identity submissions must be human-clicked).
**Parallel-with:** P36 (once external approvals start moving).
**Plans:** TBD

### Phase 39: Public RC Cut + Ship
**Goal:** Cut the public RC — tag the signed binary, publish the GitHub Release, push 4-channel social, light up Discord, embed the demo film in the README hero, monitor the first 24h.
**Depends on:** all v2.1 phases shipped (27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38).
**Requirements:** SHIP-01, SHIP-02, SHIP-03, SHIP-04, SHIP-05, SHIP-06, SHIP-07, SHIP-08
**Success Criteria** (what must be TRUE):
  1. A signed binary is tagged and `gh release create v2.1.0-rc1` (or `v0.2.0-rc1` per Kaan's pick at cut) publishes with a real changelog enumerating v2.0 close + v2.1 buckets + any remaining tech-debt items.
  2. README hero embeds the finalized `demo.mp4` (ASSETS-07); feature matrix syncs with shipped v2.1 surfaces (P68 sync test green); Bravoh-funnel footer link is active.
  3. 4-channel social posts (Twitter / IG Reels IT+EN / Reddit / HN Show HN) publish via `scripts/launch/publish_social_posts.py` with a `--dry-run` Discord webhook preview before publish — auto-publish 5 min later if no NACK.
  4. Discord `#announcements` posts the launch with the pre-seeded community role pinged; first-24h Discord watch + GitHub Issues triage + healthz dashboard run on a coordinated Kaan/Francesco/Bravoh rotation.
  5. GitHub topics + repo description optimized for search; `gh org view bravoh` confirms repo location + repo transferred to `bravoh/vibemix` if not already.
  6. RC labeling is honest — `v2.1.0-rc1` not premature `v1.0.0`.
**Critical pitfalls:** P59 (star quality), P68 (README hero sync), P78 (launch timing), P79 (post-launch monitoring gaps), P83 (cut labeling), P85 (Phase 16 override expires post-v2.1), P86 (defer-to-v2.2 creep audit), P87 (grey-area decision log).
**Parallel-with:** none (final).
**Plans:** TBD

---

## Progress

| Milestone | Phases | Status | Shipped |
|-----------|--------|--------|---------|
| v0.1.0 MVP Foundation | 1–14 | ✅ Shipped | 2026-05-13 |
| v2.0 Research-Driven Ship | 15–26 | ✅ Shipped (tech_debt) | 2026-05-14 |
| v2.1 The Unified Cut | 27–39 | 🚧 In progress (planning → execution) | — |

### v2.1 Phase Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 27. Eval Harness + Carry-Forward Close-Out | 2/9 | In Progress|  |
| 28. Library Intelligence v1 | 8/9 | In Progress|  |
| 29. Post-Session Debrief MVP UI | 1/9 | In Progress|  |
| 30. 2 Hard Tek Detectors | 0/0 | Not started | — |
| 31. 4-Layer Mascot Full Additive | 0/0 | Not started | — |
| 32. Long-Term DJ Profile | 0/0 | Not started | — |
| 33. One-Click Install Hardening | 0/0 | Not started | — |
| 34. Open-Source Security Pass | 0/0 | Not started | — |
| 35. Real GLBs + Viral Demo Film | 0/0 | Not started | — |
| 36. Day-Zero Ops Automation | 0/0 | Not started | — |
| 37. Cross-Phase Integration Audit | 0/0 | Not started | — |
| 38. Signing Pipeline Real Execution | 0/0 | Not started | — |
| 39. Public RC Cut + Ship | 0/0 | Not started | — |

---

*ROADMAP appended 2026-05-14 by gsd-roadmapper — v2.1 The Unified Cut milestone scaffolded from `.planning/research/v2-1/SUMMARY.md` 13-bucket decomposition. v2.0 details remain at `.planning/milestones/v2.0-ROADMAP.md`.*
