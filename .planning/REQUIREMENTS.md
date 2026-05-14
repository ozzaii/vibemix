# vibemix — v2.1 Requirements

**Milestone:** v2.1 "The Unified Cut" — ship a public open-source RC where every v2.0 component is fully integrated, validated, securely packaged, and one-click-installable; every missed integration opportunity closed; every human-needed surface autonomously discharged (except legal-capacity carveouts).

**Mode:** `gsd-autonomous fully` (Phase 16 ear-test memory override accepted for this milestone — autonomous proxy gate substitutes).

**Phase numbering:** Continues from Phase 27 (v2.0 closed at Phase 26).
**REQ-IDs:** Continue from v2.0 (94 REQ-IDs shipped). Categories: existing (SENSE / GROUND / LATENCY / MASCOT / OVERLAY / LIBRARY / MIDI / DEBRIEF / REC / DIST / GH / OPS / VIRAL / VERIFY) + new (EVAL / PROFILE / INSTALL / SEC / ASSETS / AUDIT / SHIP).

**Coverage target at close:** 100% satisfied end-to-end (no orphan-but-shipped surfaces, no "Kaan-action" surface left except the two legal-capacity items: Apple Developer Program Agreement update + SignPath OSS application submission).

**Source documents:** `.planning/research/v2-1/SUMMARY.md` (synthesis) + `STACK.md` + `FEATURES.md` + `ARCHITECTURE.md` + `PITFALLS.md`.

---

## v2.1 Evaluation & Hallucination Gate — Autonomous Proxy (P27)

Substitutes for Kaan's Phase 16 ear-test in v2.1 only. Bar = "real DJ friend, no AI slop" measured by 2-judge cross-check + F1 + substance + cited-relevance.

- [ ] **EVAL-01**: Replay harness — `scripts/eval/replay_harness.py` reads `recordings/<session>/events.jsonl` + `input.wav` + `voice.wav` + replays through shipped P17 detectors + P18 EvidenceRegistry + P19 ack bank + P20 linter + P22 anticipation. Single-binary, deterministic, no GPU.
- [ ] **EVAL-02**: 2-judge cross-check — Gemini 3 Pro + Gemini 3 Flash with different rubric prompts. Both must score ≥ 0.80 F1 for pass (Pitfall P42 mitigation).
- [ ] **EVAL-03**: Corpus diversity gate — ≥ 3 sourced public-domain DJ sets (archive.org / CCMixter / Free Music Archive) covering ≥ 3 genres; Hard Tek/techno ≤ 70% of corpus; per-detector-per-genre F1 matrix (Pitfall P43).
- [ ] **EVAL-04**: Substance metric — `useful_response_ratio ≥ 0.65` (responses containing concrete observation or specific advice, not filler like "I'm listening"); per-event-class substance check (Pitfall P44).
- [ ] **EVAL-05**: Cited-but-irrelevant filter — embedding-relevance cosine ≥ 0.4 between cited evidence and response text; orthogonal to F1 (Pitfall P45).
- [ ] **EVAL-06**: F1 + substance + bypass-rate-ceiling 0.15 threshold lock in `THRESHOLD-LOCK.md` co-signed by Kaan at end of phase.
- [ ] **EVAL-07**: CI gate — `.github/workflows/eval.yml` runs replay harness on PR merge + nightly canary; fails build below threshold.
- [ ] **EVAL-08**: Eval report artifact — per-run scorecard (`eval_report_<hash>.json`) committed to `.planning/eval-runs/` for audit trail.

## v2.1 Carry-Forward Close-Out — v2.0 Tech-Debt Wired (P27)

- [ ] **LIBRARY-09**: `EvidenceRegistry.register_library` invoked from `__main__.py:~698-717` when `~/.cache/vibemix/library.pkl` exists (closes v2.0 orphan `LIBRARY-08`); invocation test + end-to-end live citation test (Pitfall P48).
- [ ] **REC-09**: Universal2 sidecar — `lipo` merge of arm64 + x86_64 PyInstaller outputs; eliminates Rosetta prompt on Apple Silicon (Pitfall P69).
- [ ] **LATENCY-14**: WASAPI loopback `IMMNotificationClient` subscription — mid-session default-device-change handled without session crash on Windows (Pitfall P70).
- [ ] **MASCOT-11**: Anticipation-layer real GLBs land (closes v2.0 placeholder — handled in Phase 35 ASSETS-04).
- [ ] **LATENCY-15**: 40 Achird-voice OPUS ack recordings — replace v2.0 silent placeholders one-for-one via offline Gemini TTS Achird voice batch render; re-run AIza-key scan on new bytes.
- [ ] **MIDI-20**: DDJ-FLX4 Sync note disambiguation locked — autonomous synthetic MIDI replay against fixture sniff; defensive both-bindings (0x60 + 0x58) confirmed or narrowed.

## v2.1 Library Intelligence v1 (P28)

Closes the v2.0 architectural-slot reservation (LIBRARY-08) with a full feature surface.

- [ ] **LIBRARY-10**: Gemini Embedding 2 client wrapper — `src/vibemix/library/embed.py` using `google-genai` 2.0.1 native `embed_content`. Caches embeddings keyed by track-hash + model-id (Pitfall P56 cost guard).
- [ ] **LIBRARY-11**: sqlite-vec index — `src/vibemix/library/index_sqlite_vec.py` (Mac); numpy fallback `index_numpy.py` (Windows); identical cosine + stable argsort + float32 (Pitfall P55).
- [ ] **LIBRARY-12**: Library vibe-search query interface — natural-language English query → top-K matches with confidence scores; CLI test surface + IPC for renderer.
- [ ] **LIBRARY-13**: "What's playing" grounding — current track audio (3-excerpt strategy to handle Gemini Embedding 2 180s cap, Pitfall P54) cross-referenced against library; emits `[track:<id>]` citation when confidence ≥ 0.7.
- [ ] **LIBRARY-14**: Track-to-track similarity — DJ next-track suggestion via cosine top-K against active deck embedding. (Anti-feature watch: NOT "AI suggests your next track" prescription — surfaces only when user asks.)
- [ ] **LIBRARY-05**: Drag-drop + file-picker UX in Settings → Library tab (closes v2.0 `LIBRARY-05` deferred surface).
- [ ] **LIBRARY-15**: 30-day staleness nudge — UI prompt "Looks like you've added new tracks — re-import to keep me grounded" (closes v2.0 `LIBRARY-06` deferred surface; Pitfall P15 v2.0 carry).
- [ ] **LIBRARY-16**: Embedding cost projection — runtime telemetry + 24h query cache + budget table ≤ €50/month (Pitfall P56).
- [ ] **LIBRARY-17**: 4 new IPC schemas on existing ws_bus port 8765 — `ipc.library.import_progress`, `ipc.library.search_result`, `ipc.library.confidence`, `ipc.library.staleness_nudge`.

## v2.1 Post-Session Debrief MVP UI (P29)

Docks into v2.0 architectural slot (DEBRIEF-01 + DEBRIEF-02 + sidecar `--debrief` flag + port 8766).

- [ ] **DEBRIEF-03**: Chaptered review — auto-derived chapter markers from session event timeline (`events.jsonl`); persists in `session_debrief.json`.
- [ ] **DEBRIEF-04**: 60-90s voiced TL;DR — Gemini TTS rendering of session summary; playable in renderer via WaveSurfer.js (audio format: MP3, cross-platform webview parity verified Pitfall P81).
- [ ] **DEBRIEF-05**: Clickable timeline — WaveSurfer.js regions overlaid on session waveform; click → seek + show citation tooltip.
- [ ] **DEBRIEF-06**: 3 drills generated per session — concrete practice exercises grounded in cited critique (SBI / STAR-AR pattern from FEATURES.md).
- [ ] **DEBRIEF-07**: Cited critique surfaces — every advice line in debrief references `[ev:*]`, `[track:*]`, or `[mix:*]` from session EvidenceRegistry snapshot; un-cited critique stripped.
- [ ] **DEBRIEF-08**: Tauri `open_debrief_window` command — second WebviewWindow (label="debrief", standard chrome, 1280×720); spawns `--debrief <session_dir>` sidecar child via existing port 8766 schema.
- [ ] **DEBRIEF-09**: Sidecar child lifecycle on WebviewWindow close — Rust `WindowEvent` listener pattern from v2.0 mascot; `Arc<Mutex<Option<CommandChild>>>` in `sidecar.rs` (Pitfall P81 open-question resolution).
- [ ] **DEBRIEF-10**: Debrief schema lock — `debrief.v1` jsonschema additive-only; no breaking changes across v2.1 (Pitfall P82).
- [ ] **DEBRIEF-11**: Settings → Recordings → click row → "Open Debrief" button — entry point integration with Phase 15 recording browser.

## v2.1 Sensing — 2 Hard Tek Detectors (P30)

Completes v2.0's 6-detector taxonomy; extends `GenreRouter.build_hard_tek_chain()` per Phase 17 pre-committed comment.

- [ ] **SENSE-17**: `DISTORTION_CLIMB` detector — band-limited spectral-flatness rise + harmonic-distortion proxy + sustained kick density; cooldown 6s; cite `[ev:DISTORTION_CLIMB@<t>]` with `chain_position` and `distortion_db` fields.
- [ ] **SENSE-18**: `ACID_LINE_ENTRY` detector — TB-303-style 200-800Hz formant-sweep autocorr + resonance-rise envelope; cooldown 8s; cite `[ev:ACID_LINE_ENTRY@<t>]` with `formant_hz` and `resonance_q` fields.
- [ ] **SENSE-19**: GenreRouter atomic-swap regression test — 1000-cycle stress test under 8 detectors registered (Pitfall P49); construct-time registration only via `MappingProxyType`.
- [ ] **SENSE-20**: `scripts/tune_detectors.py` extended with Hard Tek reference tracks (Kaan-curated set sourced; documented in `eval/corpus/hard_tek/README.md`).

## v2.1 4-Layer Mascot Full Additive State Machine (P31)

**EXTENDS** v2.0 simplified anticipation subset, does NOT rewrite from scratch (Pitfall P47). Adds Base + Emotion + Reaction layers; Anticipation priority 70 preserved verbatim.

- [ ] **MASCOT-20**: Priority-stack manager — `tauri/ui/src/mascot/priority-stack.ts`; resolves 4 channels by priority (Base 50, Emotion 60, Anticipation 70, Reaction 80) with cancel-priority 999 (Pitfall P72).
- [ ] **MASCOT-21**: Crossfade policy — `crossfade-policy.ts`; 100ms stagger across simultaneous layer transitions; p99 frame budget < 22ms vitest perf test (Pitfall P62).
- [ ] **MASCOT-22**: Base layer — idle breathing + sway loop; constant priority 50; never canceled.
- [ ] **MASCOT-23**: Emotion layer — 4-state {neutral, focused, hyped, concerned} driven by `MusicState.active_genre` + `energy_band`; ws_bus payload extension with `emotion` field.
- [ ] **MASCOT-24**: Reaction layer — fires on cited reaction events with inline `[emote:*]` tag parsed from Gemini response text; priority 80; cancel-aware; ws_bus payload extension with `reaction_intent` field.
- [ ] **MASCOT-25**: v2.0 priority-70 + 2.5s timeout + cancel-aware + linter-strip-aware tests port verbatim to 4-layer rig — all v2.0 mascot test names preserved (Pitfall P47 mitigation evidence).
- [ ] **MASCOT-26**: `additive-layer.ts` extends from 3 → 4 channels per v2.0 marker comment; SkeletonHelper visual regression test.
- [ ] **MASCOT-27**: Mascot GLB total budget ≤ 25 MB CI gate (Pitfall P52 sub-budget).

## v2.1 Long-Term DJ Profile (~2KB JSON) (P32)

- [ ] **PROFILE-01**: Profile builder — `src/vibemix/profile/builder.py`; post-session regenerates profile from EvidenceRegistry snapshot + session events; UTF-8 bytes hard cap 2048 (Pitfall P51 size).
- [ ] **PROFILE-02**: Profile field allowlist — jsonschema `additionalProperties: false`; allowed fields: `preferred_genre`, `avg_session_duration`, `mix_style_tags` (≤ 8 items), `tempo_preference_bin`, `event_type_response_preferences`; NO `recent_tracks`, NO `library_titles`, NO free-form strings (Pitfall P51 privacy).
- [ ] **PROFILE-03**: Profile cache — stored in GeminiContextCache (NOT per-turn prompt prefix) to preserve 1024-token floor (Pitfall P60); cache invalidation on profile regen.
- [ ] **PROFILE-04**: Profile injection — DJCoHostAgent constructor 5th kwarg `profile=` (kwargs-only — Pitfall P53); `None` default keeps v2.0 4-kwarg path byte-identical.
- [ ] **PROFILE-05**: User consent screen — first-launch wizard adds "Build a profile to personalize coaching?" toggle; default-OFF; surfaces what's stored.
- [ ] **PROFILE-06**: Tendency regeneration rule — each tendency field requires ≥ 2 session citations from EvidenceRegistry; prevents generic-tendency drift.
- [ ] **PROFILE-07**: Settings → Profile panel — view + delete + regenerate-now; privacy disclosure inline.

## v2.1 One-Click Install Hardening (P33)

EXTENDS Phase 11 wizard; sequenced after Phase 38 signed binary lands.

- [ ] **INSTALL-01**: TCC permissions pre-grant wizard — macOS Settings deep-links for Microphone + Screen Recording + Accessibility + Automation per macOS version (12.3 / 14 / 15 fallback ladder, Pitfall P50); "Why we need this" inline copy per permission.
- [ ] **INSTALL-02**: `tauri-plugin-macos-permissions = "2.3.0"` Rust crate wired with `#[cfg(target_os = "macos")]`.
- [ ] **INSTALL-03**: BlackHole 2ch auto-detect — sidecar probes for system loopback device; first-launch downloads + installs BlackHole automatically (or prompts user with single-click install button) when absent.
- [ ] **INSTALL-04**: Windows Defender SmartScreen handling — signed binary publisher reputation seeded via SignPath OSS chain (Pitfall P22 v2.0 carry); fallback "How to allow on first launch" KB article linked from wizard.
- [ ] **INSTALL-05**: First-launch onboarding flow — Tauri WebviewWindow walks through TCC grants + audio device pick + controller probe + AI test reaction; "icon tap → ready to mix" target ≤ 60 seconds.
- [ ] **INSTALL-06**: TCC permission revoke mid-session graceful degrade (Pitfall P71) — per-launch re-check + in-session toast "Microphone access lost — paused" without crash.
- [ ] **INSTALL-07**: Bundle ID `world.bravoh.vibemix` lock — CI grep assertion against `tauri.conf.json` + v2.0 → v2.1 upgrade test (Pitfall P63).
- [ ] **INSTALL-08**: Fresh-VM rehearsal automation — `scripts/install_rehearsal/` + tart VM matrix (macOS 12.3 + 14 + 15, Windows 10 + 11); gated on `workflow_dispatch` + nightly cron (not every PR for cost).
- [ ] **INSTALL-09**: API key entry NEVER — explicit assertion test that no UI surface accepts user-provided Gemini key (proxy-only path enforced per memory `project_one_click_install_hard_req`).

## v2.1 Open-Source Security Pass (P34)

Lands EARLY (parallel with Phase 27/28/29/30) so subsequent phases ship clean.

- [ ] **SEC-01**: Secret scanner — gitleaks pre-commit hook + `.secrets.baseline` with surgical AIza-fixture allowlist (Pitfall P64); GitHub Actions secret-scan job blocks merge.
- [ ] **SEC-02**: Python dep CVE audit — pip-audit + osv-scanner; severity gate HIGH+ direct deps, CRITICAL transitives (Pitfall P65).
- [ ] **SEC-03**: Rust dep CVE audit — cargo-audit + cargo-deny; severity gate matches Python.
- [ ] **SEC-04**: SBOM — syft generates `sbom.spdx.json` per release; attached to GitHub Release artifacts.
- [ ] **SEC-05**: Signed-binary verifier job in CI — post-sign artifact checksum + signature validate before release publish.
- [ ] **SEC-06**: SECURITY.md — disclosure policy, PGP key, supported versions table; first-line link from README.
- [ ] **SEC-07**: STRIDE-lite threat model — `docs/threat-model.md`; covers proxy rate-limit bypass + key extraction + telemetry exfil + supply chain.
- [ ] **SEC-08**: Telemetry consent UX — opt-in default-OFF (Pitfall P67); first-run explicit screen "Help vibemix get better? (you can change later)" with field-set disclosure.
- [ ] **SEC-09**: Capability allowlist lint — Tauri capabilities snapshot tracked in git; CI diff-fails on unexpected capability addition (Wave 2 lock).
- [ ] **SEC-10**: Auditable privacy claim — "audio + MIDI + screen never leaves machine" verifiable from `runtime/sec_check.py` boot banner + outbound-connection inventory in SECURITY.md.

## v2.1 Real GLBs + 30s Viral Demo Film (P35)

Closes v2.0 MASCOT-11 + GH-20 (30s demo GIF NEW asset = was Kaan-action).

- [ ] **ASSETS-01**: Mascot 3D model generation — Meshy v6 vs Hunyuan3D 3.0 A/B against ~$50 credit budget; pick winner; content-hash cached output (Pitfall P52 + open question #17).
- [ ] **ASSETS-02**: Mixamo auto-rig + 8-12 motion clips — idle + walk + lean-in + react-hyped + react-concerned + react-cancel + speak-open + speak-close; SkeletonHelper visual QA (Pitfall P61); Rokoko fallback path documented.
- [ ] **ASSETS-03**: 5 `prep_*` clips real GLB replacement — replaces v2.0 placeholders one-for-one (closes MASCOT-11); idle-zero lower-body delta preserved per Phase 22-02 contract.
- [ ] **ASSETS-04**: GLB optimization pipeline — DRACO level 7+ compression + KTX2/WebP textures; per-clip < 600 KB; total mascot GLB budget ≤ 25 MB (Pitfall P52).
- [ ] **ASSETS-05**: Viral demo film — `scripts/demo_film/`; 3-beat structure (Beat A overlay highlight, Beat B mascot lean-in BEFORE voice, Beat C cited reaction); ffmpeg manual edit (cut count ≤ 8, Pitfall P57); voiceover written by Kaan/Francesco OR no VO (Pitfall P58).
- [ ] **ASSETS-06**: Demo film source-of-truth recording — real DJ session screen capture (Quartz on Mac); minimum 3 minutes raw → cut to 30s; vibemix running live.
- [ ] **ASSETS-07**: `demo.mp4` bundled in release assets + embedded in README hero block; CI sync test ensures README hero references current `demo.mp4` hash (Pitfall P68).

## v2.1 Day-Zero Operations Live (P36)

Sequenced after Phase 21 + 26 scaffold; runs parallel with Phase 35; hard prereq for Phase 39.

- [ ] **OPS-09**: Discord server auto-provision — `scripts/dayzero/discord_provision.py`; creates `vibemix` server + roles (founder / contributor / DJ / lurker) + channels (#announcements, #help, #show-and-tell, #controllers, #ai-misbehavior, #dev); Day-Zero ready (closes v2.0 OPS-04).
- [ ] **OPS-10**: 100 RPS × 5min proxy load test — real run against `api.altidus.world/vibemix` proxy; p99 < 500ms gate; pass artifact archived (extends v2.0 OPS-06 scaffold).
- [ ] **OPS-11**: Healthz watchdog live — `scripts/dayzero/healthz_check.sh` running as a real cron; alerts to Discord webhook on failure (extends v2.0 OPS-03).
- [ ] **OPS-12**: 15+ pre-seeded star coordination — aligned-community sourcing (Bravoh team, DJ network, ARRAY community, contributor friends — NOT 15 random friend-favors, Pitfall P59); Day-1 stars logged.
- [ ] **OPS-13**: Launch trigger sequence — `scripts/dayzero/launch_trigger.sh`; T-30 / T+0 / T+5 / T+24h timing; dry-run preview before publish (Pitfall P78 timing).
- [ ] **OPS-14**: Bravoh ops endpoint deployment — `api.altidus.world/vibemix/updates/upload` (closes v2.0 DIST-14) + healthz alerts to Bravoh PagerDuty.

## v2.1 Cross-Phase Integration Audit (P37)

Penultimate phase — verifies every other feature wired + fresh-VM smoke-tested.

- [ ] **AUDIT-01**: `tests/e2e/test_seam_*.py` — 5+ critical end-to-end seam tests (P18→P20, P19→agent, P25→P28, P27→eval-gate, P31→ws_bus).
- [ ] **AUDIT-02**: `scripts/integration_audit.py` re-run extending v2.0 `gsd-integration-checker` — produces fresh `v2.1-MILESTONE-AUDIT.md` with WIRED/PARTIAL/MISSING per seam; PASS requires source line + fresh-VM smoke (Pitfall P66).
- [ ] **AUDIT-03**: Orphan inventory grep gate — `.planning/codebase/CONCERNS.md` updated; CI fails on new orphaned-but-shipped surface added.
- [ ] **AUDIT-04**: Kaan-action surface roll-up — final summary doc; CRITICAL items only (signing approvals if not yet landed; nothing else allowed).
- [ ] **AUDIT-05**: Grey-area decision log — dedicated section in `v2.1-MILESTONE-AUDIT.md` covering every recommended autonomous answer with rationale (Pitfall P87).
- [ ] **AUDIT-06**: `.github/workflows/integration-audit.yml` — nightly canary + pre-release gate.
- [ ] **AUDIT-07**: POC files untouched test — `test_g5_poc_files_untouched.py` extended to v2.1 modified files allowlist.

## v2.1 Signing Pipeline Real Execution (P38)

Highest external dependency; legal-capacity carveouts NEVER autonomously discharge (Pitfall P46).

- [ ] **DIST-15**: Apple notarytool wired in `release.yml` — real Apple Developer ID secrets injected; staple + validate post-sign (closes v2.0 DIST-10).
- [ ] **DIST-16**: SignPath OSS GH Action wired — real SignPath credentials; closes v2.0 DIST-11.
- [ ] **DIST-17**: Post-sign verifier job — checksum + signature validate; release publish blocks on verifier pass.
- [ ] **DIST-18**: `scripts/dist/sign_windows.ps1` — local-rehearsal script for Kaan to test signing flow on his machine before relying on CI; SignPath CLI integration.
- [ ] **DIST-09**: Apple Developer Program Agreement update — autonomous discharge FORBIDDEN (legal capacity); `KAAN-ACTION-LEGAL.md` documents Francesco-action step + countersign protocol (Pitfall P46); CI bash audit grep against POST/PUT to apple endpoints.
- [ ] **DIST-11**: SignPath OSS Foundation application — autonomous discharge FORBIDDEN; `KAAN-ACTION-LEGAL.md` documents Kaan-action step; ~1-week SLA from submission.
- [ ] **DIST-19**: Sign+verify smoke test on signed bundle — Kaan runs `bash tauri/src-tauri/spike/sign-and-test.sh` on signed binary (closes v2.0 OVERLAY-02 Wave-0 verdict).

## v2.1 Public RC Cut + Ship (P39)

Final phase — needs every other phase landed.

- [ ] **SHIP-01**: Signed binary tagged + `gh release create v2.1.0-rc1` (or `v0.2.0-rc1` — Kaan picks at cut, open question #24).
- [ ] **SHIP-02**: README hero finalized — embeds `demo.mp4` (ASSETS-07); feature matrix synced with shipped v2.1 surfaces (Pitfall P68); Bravoh-funnel footer link active.
- [ ] **SHIP-03**: 4-channel social posts published — Twitter / IG Reels (IT + EN) / Reddit / HN — `--dry-run` preview to Discord webhook before publish; auto-publish 5min later if no NACK (open question #26).
- [ ] **SHIP-04**: Discord launch announcement — `#announcements` channel post + role-ping pre-seeded community.
- [ ] **SHIP-05**: GitHub topics + repo description optimized for search (`dj`, `livekit`, `gemini`, `ai-assistant`, `audio`, `midi`, `pioneer-ddj`, `realtime-ai`, `open-source-dj`).
- [ ] **SHIP-06**: Bravoh org status pre-flight — `gh org view bravoh` confirms repo location + transfer to `bravoh/vibemix` if not already there (open question #27).
- [ ] **SHIP-07**: Honest RC labeling — `v2.1.0-rc1` not premature `v1.0.0`; changelog references v2.0 close + v2.1 buckets; tech-debt section enumerates remaining items if any.
- [ ] **SHIP-08**: Post-launch monitoring — first-24h Discord watch + GitHub Issues triage + healthz dashboard; Bravoh team + Kaan + Francesco coordinated rotation.

## v2.1 Carry-Forward Closures (V2.0 Items Closing in v2.1)

Cross-reference list — these v2.0 REQ-IDs flip from `[ ]` to `[x]` when their v2.1 phase ships:

| v2.0 REQ-ID | Status v2.0 | v2.1 phase | Closing REQ |
|-------------|-------------|------------|-------------|
| LIBRARY-08 (sqlite-vec slot) | reserved | P28 | LIBRARY-11 |
| LIBRARY-05 (drag-drop UX) | deferred | P28 | LIBRARY-05 (reused ID) |
| LIBRARY-06 (30-day nudge) | deferred | P28 | LIBRARY-15 |
| LIBRARY-03 (fuzzy ladder) | deferred | P28 | LIBRARY-13 (subsumed) |
| LIBRARY-04 (confidence rendering) | placeholder | P28 | LIBRARY-13 (subsumed) |
| DEBRIEF-01/02 (slot only) | architectural | P29 | DEBRIEF-03..11 |
| MASCOT-11 (real GLBs) | placeholder | P35 | ASSETS-03 |
| OVERLAY-02 (signed bundle AX verdict) | spike-only | P38/P33 | DIST-19 |
| MIDI-17 (9-SKU verification) | community-PR | P30/P37 | AUDIT-01 + community-PR ongoing |
| DIST-09/10/11/14 (signing real exec) | external pending | P38 | DIST-15/16/17 |
| OPS-01/02 (Fresh-VM rehearsals) | Kaan-action | P33 | INSTALL-08 |
| OPS-04 (Discord setup) | Kaan-action | P36 | OPS-09 |
| OPS-06 (proxy load test) | scaffolded | P36 | OPS-10 |
| OPS-08 (pre-seeded stars) | Kaan-action | P36 | OPS-12 |
| GH-20 (30s demo GIF) | Kaan-action | P35 | ASSETS-05 |
| VIRAL-01..10 (post drafts) | drafts | P39 | SHIP-03 |
| LATENCY-01 (40 ack recordings) | placeholders | P27 | LATENCY-15 |
| VERIFY-07/08/09/10 (Phase 16 ear-test) | Kaan-action | P27 | EVAL-01..08 (autonomous proxy) |

## Future Requirements (Deferred to v2.2 or Later)

- **`/hatch` user-generated mascot pipeline** — explicit v2.x stretch per memory `project_mascot_as_vtuber_personality_surface`
- **DAW integration** (Logic / Ableton / FL Studio) — "next conquest" after DJ software
- **Mobile / iPad / iOS app** — desktop only in v1/v2
- **Custom voice cloning** — Gemini TTS prebuilt voices only
- **Linux support** — niche audience, doubles platform-engineering cost
- **Multi-language UI** — English only in v1/v2
- **Real-time stream-to-Twitch/YouTube hook** — recording for later sharing is enough
- **Mixxx OSC integration + map transpiler + ProDJ Link** — v2 open candidates deferred to post-RC (per memory `project_v2_open_candidates`)
- **Stems separation** — explicitly deferred (per memory `project_v2_open_candidates`)
- **Predictive drop firing default-on** — off-by-default in v2.0; telemetry guard pre-wired; v2.1 keeps off; v2.x turn-on after live observability

## Out of Scope (Explicit Exclusions)

- **Gemini Live Native Audio modality** — Kaan tested it, doesn't generalize; opt-in only via `cohost_lk.py`
- **Headphone cue listening** — Gemini conflates cue with master; master-output-only path
- **User-supplied Gemini API keys** — friction kills virality; Bravoh-managed proxy is the path
- **CLAP / LAION-CLAP / MERT / OpenL3 / sentence-transformers / torch** — memory-locked NO (`feedback_no_clap_use_gemini_embedding`)
- **Vector-DB servers (Qdrant / Chroma / Weaviate / Milvus)** — local-only library intelligence per `project_one_click_install_hard_req`
- **Multi-provider AI wrappers (LangChain / LlamaIndex)** — Gemini-only
- **Real-time eval-in-prod / multi-judge ensemble (>2 judges) / BLEU/ROUGE** — autonomous proxy gate is offline only
- **Live observability dashboards / distributed tracing** — out of scope for v2.1
- **Bug bounty / SOC 2 / E2E recording encryption / PII classifier** — v2.x or never (`feedback_no_scope_creep_clean_utility`)
- **Trivy** (March 2026 supply-chain compromise) + **Safety CLI** (commercial restriction) + **discord.py** (5MB for one POST) + **Locust/k6** (overkill at 100 RPS) — see SUMMARY.md rejected alternatives
- **AI auto-edit demo film pacing / AI voiceover script** — anti-slop bar requires manual editing + Kaan/Francesco-written VO (Pitfalls P57/P58)
- **Mascot multi-character / customization / webcam eye-tracking / 30+ pose vocab / procedural visemes** — v2.x stretch (Pitfall P76 uncanny-valley guard)
- **Phase 16 Kaan ear-test as gate in v2.1** — autonomous proxy substitutes (memory `project_phase_16_kaan_dj_testing` overridden for v2.1 only per autonomous mode + Kaan instruction)
- **Autonomous discharge of Apple Developer Program Agreement update + SignPath OSS Foundation application** — legal-capacity carveouts (Pitfall P46) require human countersignature

## Traceability

Every v2.1 REQ-ID maps to exactly one v2.1 phase. 100% coverage validated 2026-05-14 by `gsd-roadmapper` at roadmap creation time. **Total: 105 / 105 v2.1 REQ-IDs mapped.**

> Note: the doc footer claims "87" — that was a count drafted while requirements were being added. The authoritative enumeration below counts 105 unique v2.1 REQ-IDs (8 EVAL + 6 v2.0 carry-forward + 9 LIBRARY new + 9 DEBRIEF + 4 SENSE + 8 MASCOT new + 7 PROFILE + 9 INSTALL + 10 SEC + 7 ASSETS + 6 OPS + 7 AUDIT + 7 DIST + 8 SHIP = 105). The "87 v2.1 REQ-IDs" sentence in the footer is corrected by this table.

### Eval & Hallucination Gate — Autonomous Proxy (Phase 27)

| REQ-ID | Phase | Status |
|--------|-------|--------|
| EVAL-01 | Phase 27 | Pending |
| EVAL-02 | Phase 27 | Pending |
| EVAL-03 | Phase 27 | Pending |
| EVAL-04 | Phase 27 | Pending |
| EVAL-05 | Phase 27 | Pending |
| EVAL-06 | Phase 27 | Pending |
| EVAL-07 | Phase 27 | Pending |
| EVAL-08 | Phase 27 | Pending |

### Carry-Forward Close-Out (Phase 27)

| REQ-ID | Phase | Status |
|--------|-------|--------|
| LIBRARY-09 | Phase 27 | Pending |
| REC-09 | Phase 27 | Pending |
| LATENCY-14 | Phase 27 | Pending |
| LATENCY-15 | Phase 27 | Pending |
| MASCOT-11 | Phase 27 | Pending (real-GLB execution lives in Phase 35 ASSETS-03) |
| MIDI-20 | Phase 27 | Pending |

### Library Intelligence v1 (Phase 28)

| REQ-ID | Phase | Status |
|--------|-------|--------|
| LIBRARY-10 | Phase 28 | Pending |
| LIBRARY-11 | Phase 28 | Pending |
| LIBRARY-12 | Phase 28 | Pending |
| LIBRARY-13 | Phase 28 | Pending |
| LIBRARY-14 | Phase 28 | Pending |
| LIBRARY-05 | Phase 28 | Pending (drag-drop UX — closes v2.0 deferred surface) |
| LIBRARY-15 | Phase 28 | Pending |
| LIBRARY-16 | Phase 28 | Pending |
| LIBRARY-17 | Phase 28 | Pending |

### Post-Session Debrief MVP UI (Phase 29)

| REQ-ID | Phase | Status |
|--------|-------|--------|
| DEBRIEF-03 | Phase 29 | Pending |
| DEBRIEF-04 | Phase 29 | Pending |
| DEBRIEF-05 | Phase 29 | Pending |
| DEBRIEF-06 | Phase 29 | Pending |
| DEBRIEF-07 | Phase 29 | Pending |
| DEBRIEF-08 | Phase 29 | Pending |
| DEBRIEF-09 | Phase 29 | Pending |
| DEBRIEF-10 | Phase 29 | Pending |
| DEBRIEF-11 | Phase 29 | Pending |

### 2 Hard Tek Detectors (Phase 30)

| REQ-ID | Phase | Status |
|--------|-------|--------|
| SENSE-17 | Phase 30 | Pending |
| SENSE-18 | Phase 30 | Pending |
| SENSE-19 | Phase 30 | Pending |
| SENSE-20 | Phase 30 | Pending |

### 4-Layer Mascot Full Additive (Phase 31)

| REQ-ID | Phase | Status |
|--------|-------|--------|
| MASCOT-20 | Phase 31 | Pending |
| MASCOT-21 | Phase 31 | Pending |
| MASCOT-22 | Phase 31 | Pending |
| MASCOT-23 | Phase 31 | Pending |
| MASCOT-24 | Phase 31 | Pending |
| MASCOT-25 | Phase 31 | Pending |
| MASCOT-26 | Phase 31 | Pending |
| MASCOT-27 | Phase 31 | Pending |

### Long-Term DJ Profile (Phase 32)

| REQ-ID | Phase | Status |
|--------|-------|--------|
| PROFILE-01 | Phase 32 | Pending |
| PROFILE-02 | Phase 32 | Pending |
| PROFILE-03 | Phase 32 | Pending |
| PROFILE-04 | Phase 32 | Pending |
| PROFILE-05 | Phase 32 | Pending |
| PROFILE-06 | Phase 32 | Pending |
| PROFILE-07 | Phase 32 | Pending |

### One-Click Install Hardening (Phase 33)

| REQ-ID | Phase | Status |
|--------|-------|--------|
| INSTALL-01 | Phase 33 | Pending |
| INSTALL-02 | Phase 33 | Pending |
| INSTALL-03 | Phase 33 | Pending |
| INSTALL-04 | Phase 33 | Pending |
| INSTALL-05 | Phase 33 | Pending |
| INSTALL-06 | Phase 33 | Pending |
| INSTALL-07 | Phase 33 | Pending |
| INSTALL-08 | Phase 33 | Pending |
| INSTALL-09 | Phase 33 | Pending |

### Open-Source Security Pass (Phase 34)

| REQ-ID | Phase | Status |
|--------|-------|--------|
| SEC-01 | Phase 34 | Pending |
| SEC-02 | Phase 34 | Pending |
| SEC-03 | Phase 34 | Pending |
| SEC-04 | Phase 34 | Pending |
| SEC-05 | Phase 34 | Pending |
| SEC-06 | Phase 34 | Pending |
| SEC-07 | Phase 34 | Pending |
| SEC-08 | Phase 34 | Pending |
| SEC-09 | Phase 34 | Pending |
| SEC-10 | Phase 34 | Pending |

### Real GLBs + Viral Demo Film (Phase 35)

| REQ-ID | Phase | Status |
|--------|-------|--------|
| ASSETS-01 | Phase 35 | Pending |
| ASSETS-02 | Phase 35 | Pending |
| ASSETS-03 | Phase 35 | Pending (closes v2.0 MASCOT-11 placeholder) |
| ASSETS-04 | Phase 35 | Pending |
| ASSETS-05 | Phase 35 | Pending |
| ASSETS-06 | Phase 35 | Pending |
| ASSETS-07 | Phase 35 | Pending |

### Day-Zero Operations (Phase 36)

| REQ-ID | Phase | Status |
|--------|-------|--------|
| OPS-09 | Phase 36 | Pending |
| OPS-10 | Phase 36 | Pending |
| OPS-11 | Phase 36 | Pending |
| OPS-12 | Phase 36 | Pending |
| OPS-13 | Phase 36 | Pending |
| OPS-14 | Phase 36 | Pending |

### Cross-Phase Integration Audit (Phase 37)

| REQ-ID | Phase | Status |
|--------|-------|--------|
| AUDIT-01 | Phase 37 | Pending |
| AUDIT-02 | Phase 37 | Pending |
| AUDIT-03 | Phase 37 | Pending |
| AUDIT-04 | Phase 37 | Pending |
| AUDIT-05 | Phase 37 | Pending |
| AUDIT-06 | Phase 37 | Pending |
| AUDIT-07 | Phase 37 | Pending |

### Signing Pipeline Real Execution (Phase 38)

| REQ-ID | Phase | Status |
|--------|-------|--------|
| DIST-15 | Phase 38 | Pending |
| DIST-16 | Phase 38 | Pending |
| DIST-17 | Phase 38 | Pending |
| DIST-18 | Phase 38 | Pending |
| DIST-09 | Phase 38 | Pending (legal-capacity carveout — Francesco-action) |
| DIST-11 | Phase 38 | Pending (legal-capacity carveout — Kaan-action) |
| DIST-19 | Phase 38 | Pending |

### Public RC Cut + Ship (Phase 39)

| REQ-ID | Phase | Status |
|--------|-------|--------|
| SHIP-01 | Phase 39 | Pending |
| SHIP-02 | Phase 39 | Pending |
| SHIP-03 | Phase 39 | Pending |
| SHIP-04 | Phase 39 | Pending |
| SHIP-05 | Phase 39 | Pending |
| SHIP-06 | Phase 39 | Pending |
| SHIP-07 | Phase 39 | Pending |
| SHIP-08 | Phase 39 | Pending |

### Coverage Summary

| Phase | REQ Count | Notes |
|-------|-----------|-------|
| Phase 27 | 14 | 8 EVAL + 6 carry-forward |
| Phase 28 | 9 | Library v1 + LIBRARY-05 carry-forward |
| Phase 29 | 9 | DEBRIEF MVP UI |
| Phase 30 | 4 | Hard Tek detectors |
| Phase 31 | 8 | 4-layer mascot |
| Phase 32 | 7 | DJ profile |
| Phase 33 | 9 | Install hardening |
| Phase 34 | 10 | Security pass |
| Phase 35 | 7 | Real GLBs + viral demo |
| Phase 36 | 6 | Day-zero ops |
| Phase 37 | 7 | Integration audit |
| Phase 38 | 7 | Signing real exec (incl. 2 legal carveouts) |
| Phase 39 | 8 | RC cut + ship |
| **Total** | **105** | **100% mapped (no orphans, no duplicates)** |

### v2.0 Carry-Forward Closures Cross-Reference

(See `## v2.1 Carry-Forward Closures (V2.0 Items Closing in v2.1)` above for the source-of-truth mapping from v2.0 REQ-IDs to their v2.1 closing REQ.)


---

*Requirements drafted 2026-05-14 from `.planning/research/v2-1/SUMMARY.md`. Coverage: 87 v2.1 REQ-IDs (EVAL × 8, carry-forward LIBRARY/REC/LATENCY/MASCOT/MIDI × 6, LIBRARY × 8 new, DEBRIEF × 9 new, SENSE × 4 new, MASCOT × 8 new, PROFILE × 7 new, INSTALL × 9 new, SEC × 10 new, ASSETS × 7 new, OPS × 6 new, AUDIT × 7 new, DIST × 7 new, SHIP × 8 new).*
