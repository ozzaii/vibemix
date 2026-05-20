# Project Research Summary

**Project:** vibemix — AI DJ Co-Host
**Milestone:** v2.0 Research-Driven Ship
**Domain:** Cross-platform real-time AI desktop app (audio + screen + MIDI + LLM/TTS streaming) extending a shipped v0.1.0 base with a 12-bucket research-driven feature set + absorbed v0.1.0 ship infrastructure
**Researched:** 2026-05-14
**Confidence:** **HIGH** — anchored to 12 deep v2-bucket research artifacts (~28,000 words), the validated Phase 1–14 baseline (cohost_v4.py + shipping sidecar), and direct repo verification of livekit-agents 1.5.8 + google-genai 2.0.1 source. **MEDIUM** on the still-unresolved spikes (Gemini text-channel ordering for inline emote tags; AX-from-Rust-parent on installed binaries; sqlite-vec Windows wheel).

---

## Executive Summary

v2.0 is **not greenfield**. It is the strict additive layer on top of the already-shipped 3-process architecture (Tauri Rust shell + PyInstaller `--onedir` Python sidecar + remote FastAPI proxy on api.altidus.world). Phases 1–14 of v0.1.0 shipped the runtime, the wizard, the cascade Gemini path, the 19-message IPC schema, the mascot single-layer, and the v4-derived `MusicState`/`EventDetector`/`AICoach` core. v2.0 absorbs outstanding v0.1.0 ship work (recording browser, sign + notarize, GitHub release matrix, README rewrite, Day-Zero ops) into a single bulky milestone alongside the research-driven feature set. **No new processes. No new providers. No new frameworks. 5 new pip deps. 0 new Rust crates. 0 new npm packages.** The bundle grows from 242 MB to ~290 MB on Windows, well under the 350 MB hard cap.

The thesis is three compounded systems. **System 1: the latency stack** — `SpeechHandle.interrupt(force=True)` empirically verified, Gemini context caching with 1024-token-floor padding, ~40-sample OPUS ack bank, predictive firing gated 2 bars early, mascot anticipation layer — compresses sub-2s actual voice-to-voice to sub-300ms perceived first reaction. **System 2: the anti-slop stack** — citation grammar (`[ev:KICK_SWAP@t]` / `[aud:...]` / `[midi:...]` / `[track:...]`) baked into Gemini's system prompt, in-memory Evidence registry, stdlib `re` linter that strips response-level in live (ack-bank fallback) and sentence-level in debrief — makes "trust the audio" a contract instead of a prompt rule. **System 3: the viral demo stack** — djay Pro Mac AX overlay (12 hand-mapped pointable elements) + mascot anticipation lean-in + ack bank — yields three filmable beats (point-at-knob, anticipation-before-voice, 3-seconds-of-silence) feeding one 30s cut that anchors Twitter / IG / Reddit / HN posts. The viral demo is **the engineering critical path**, not a polish item.

The risks are bounded but concrete. **The hard gate is the Hallucination Verification Gate** — Kaan's DJ ear (per memory `project_phase_16_kaan_dj_testing`), NOT a 30-session formal eval harness. **The single-point-of-failure is the Apple Issuer ID** — supplied 2026-05-14, but Apple Developer Program Agreement update is outstanding (Francesco-action-required). **The architectural rule is AX-from-Rust-parent, never from sidecar** (Tauri #8329). **The economic rule is cap cancel-and-refire at 1 per 8s + 30 per session** or the 50€/mo per-user proxy budget breaks under Hard-Tek bursty events. **The two YELLOW items in the install footprint** — sqlite-vec Windows wheel absent + ffmpeg LGPL bundling on Windows (+20MB) — both have well-precedented workarounds (numpy fallback for sqlite-vec; gyan.dev LGPL build for ffmpeg). The full PITFALLS.md catalogs 41 distinct v2.0-specific failure modes with concrete prevention strategies — phases must encode the preventions, not the pitfalls.

---

## Key Findings

### Recommended Stack

The shipped v0.1.0 stack stays put. v2.0 is a **strict additive layer** with 5 new pip deps, 0 new Rust crates, 0 new npm packages. Every new dep is rated 🟢 GREEN or 🟡 YELLOW on the one-click-install scale (per memory `project_one_click_install_hard_req`). Total bundle growth: +~12 MB on Mac, +~32 MB on Windows (including ffmpeg). All under 350 MB hard cap.

**v0.1.0 baseline (DO NOT change):** Python 3.12, livekit-agents 1.5.8, livekit-plugins-google 1.5.8, google-genai 2.0.1, sounddevice 0.5.5 (Mac BlackHole), PyAudioWPatch 0.2.12.8 (Windows WASAPI loopback), numpy 2.4.4 + scipy 1.17.1, mido 1.3.3, pyobjc-framework-ScreenCaptureKit 12.1, pillow 12.2.0, websockets 16.0, hand-written `@dataclass(frozen=True, slots=True)` + jsonschema Draft-07 (**NO pydantic** per Phase 6 D-Area-4.4), PyInstaller 6.20.0 `--onedir`, Tauri 2.x + Vite 6 + Vitest 2, tauri-plugin-shell 2.3 + tauri-plugin-store 2.4, FastAPI 0.115 + slowapi + Redis 7+ + PyJWT for the Bravoh-proxy, CDJ Whisper v5 tokens.css + Saira + JetBrains Mono.

**v2.0 additions (5 new pip deps + 0 Rust + 0 npm):**
- **pyrekordbox 0.4.4** (MIT, pure Python, 250 KB) — Rekordbox `collection.xml` parser; XML path only, SQLCipher path skipped (broken post-Rekordbox 6.6.5)
- **sqlite-vec 0.1.9** (MIT, ~500 KB ext, Mac/Linux wheels ✅, **Windows: numpy fallback**) — embedded vector store for Gemini Embedding 2 over user's library
- **pydub 0.25.1** (MIT, 50 KB) — MP3 transcoding for Gemini Embedding 2 (AAC/M4A/FLAC → MP3 since Embedding 2 only accepts MP3/WAV)
- **mutagen 1.47.0** (GPL-2.0, 250 KB) — ID3/Vorbis/MP4 tag reader; GPL-as-imported-package pattern, disclosed in `LICENSE-3RD-PARTY.md`
- **watchdog 6.0.0** (Apache 2.0, 150 KB) — cross-platform file watcher (FSEvents on Mac, ReadDirectoryChangesW on Windows)

**Bundled binaries:** ffmpeg LGPL static (Windows only, +20 MB; macOS uses native `afconvert` fallback), 40 OPUS ack samples (+5 MB), 8 new mascot GLBs (+6 MB), djay Pro v5 element coord map (+5 KB), 10 controller JSONs (+50 KB).

**Locked anti-stack (memory-enforced — do not propose):** CLAP / OpenL3 / MERT (Gemini-only product per `feedback_no_clap_use_gemini_embedding`); mem0 / vector DB for DJ profile (~2KB JSON is the design); multi-provider LLM abstraction; stem separation; Pioneer ProDJ Link (wrong market); Mixxx OSC as a v2.0 hard ship (PR #14388 still draft upstream — ship behind `--enable-mixxx-osc` flag if at all); Rekordbox SQLCipher path; Mixamo ARKit blendshape lip-sync; pydantic in IPC layer.

See `.planning/research/STACK.md` for the full per-capability breakdown + license audit + install-impact matrix + plan-checker verification checklist.

### Expected Features

The 12 v2-bucket research artifacts mapped seven feature categories. The v2.0 cut is a **ruthless minimum** that closes the "feels surface-level" critique AND ships the viral demo arsenal.

**Must have (table stakes — v2.0 P1):**
- **Generalized event detector v1** — 6 cross-genre detectors (`KICK_SWAP`, `SUB_LAYER_ARRIVAL`, `BREAKDOWN_KICK_KILL`, `REENTRY_KICK_LAND`, `KICK_DENSITY_SHIFT`, `PHRASE_BOUNDARY`)
- **Latency stack v1** — prompt diet + Gemini caching with 1024-token-floor padding + 40-sample OPUS ack bank + cancel-and-refire (`SpeechHandle.interrupt(force=True)`)
- **Mascot anticipation layer (1-above-mood simplified)** + beat-coupled hip-bob
- **Citation grammar in prompts** (prompt-only seeding v1.0) → **Citation linter live-mode enforcement** (response-level strip + ack-bank fallback)
- **djay Pro Mac overlay highlight** (12 hand-mapped elements + AX-from-Rust-parent)
- **Pyrekordbox XML one-shot import**
- **10-SKU MIDI controller library + `MidiMapLoader`**
- **Hard Tek detector tuning** against 7-10 reference tracks
- **Ship infrastructure absorbed from v0.1.0:** Recording browser + retention enforcement, Apple Developer ID sign + notarize + DMG, SignPath OSS Windows MSI, GitHub release matrix, README full rewrite + branding + social assets, Day-Zero ops fresh-VM rehearsal
- **Hallucination Verification Gate (Kaan's DJ ear)** — hard release gate
- **30s viral demo film + 4 channel posts** (Twitter / IG IT+EN / Reddit / HN)

**Should have (competitive — v2.0 P2):**
- **Mixxx OSC bridge** behind `--enable-mixxx-osc` flag (~2 E-days, ~190 LOC)

**Defer to v2.1+ (explicitly OUT of v2.0):**
- **Predictive drop firing** — gated on Kaan ear-test with v2.0 baseline
- **4-layer mascot additive state machine** — full structural rewrite (~14 E-days); v2.0 ships only the anticipation-layer subset
- **Inline emote-tag vocabulary (15 tags)** — gated on 1-day Gemini text-channel-timing spike
- **Post-session debrief MVP** — chaptered + voiced TL;DR + 3 drills + clickable timeline
- **Long-term DJ profile** — ~2KB JSON regenerated each session
- **Cross-mode citation enforcement** — extend live linter to debrief + library + genre sentence-level
- **Library intelligence v1** (file watcher → Gemini Embedding 2 → sqlite-vec query)
- **Library-aware drill cards**
- **Rekordbox / Serato overlay** via template matching, Windows overlay parity, VirtualDJ OSC, genre expansion

See `.planning/research/FEATURES.md` for the 7-category catalog.

### Architecture Approach

v2.0 adds ~10 feature buckets to the already-shipped 3-process Tauri + Python-sidecar + remote-FastAPI architecture. **One process boundary, four kinds of work.** Tauri shell (Rust) owns OS-permission-bound work + window/overlay geometry — AX bridge lives HERE, not in sidecar (Tauri #8329). Python sidecar owns audio/DSP/AI/state. Bravoh proxy owns Gemini key + rate limit. **No new process types** — debrief is a sidecar `--debrief <dir>` FLAG, not a daemon. **The overlay is a SECOND Tauri WebviewWindow** (`label="overlay"`), not a new app.

**Major components added:**

1. **`src/vibemix/grounding/`** — `EvidenceRegistry` (in-memory dict `(source, key) → list[t_session]`), `CitationLinter` (stdlib `re` + regex catalog + per-mode strip semantics + telemetry), per-mode prompt fragments.
2. **`src/vibemix/events/genres/`** — `GenreRouter` + `hard_tek.py` with 8 detectors using shared `_impl/` DSP primitives. Baseline detectors stay verbatim from v4 when no genre-specific detector fires.
3. **`src/vibemix/latency/`** — `AckBank`, `CachedLLM`, `BuildupPredictor`, `interrupt.py` wrapper.
4. **`src/vibemix/library/`** — `RekordboxLibrary`, `embed.py` (80% Bravoh verbatim), `LibraryStore` (sqlite-vec + numpy fallback), `watcher.py`, `metadata.py`, `camelot.py`.
5. **`src/vibemix/overlay/`** + **`tauri/src-tauri/src/ax_bridge.rs`** + **`tauri/src-tauri/src/overlay_window.rs`** + **`tauri/ui/src/overlay/`** — element vocabulary parser (12 IDs), coord_map loader, AX query via Rust parent over IPC, transparent always-on-top Canvas 2D ring renderer. Mac-only in v2.0.
6. **`src/vibemix/debrief/`** (sibling sidecar mode, architectural slot only) — `--debrief <dir>` flag spawns separate child process on WS bus port 8766.
7. **`src/vibemix/mascot/anticipation.py`** + **`tauri/ui/src/mascot/`** modifications — sidecar fires `ipc.mascot.tick` with anticipation field at T=0 (BEFORE Gemini); shell mascot adopts 4-layer additive structure (mood + anticipation + speak + effect).

**The IPC schema is the load-bearing contract.** Schema count moves from 19 → 38 messages. `scripts/check_ipc_schema.py` drift gate updates from `assert wrapper_count == 19` to `assert wrapper_count == 38`. 19 new messages cover: typed event surfacing, citation telemetry, ack/predicted/cancel-refire visibility (3), overlay highlight/dismiss/window_bounds/ax_position (4), library import + lookup + embed progress (6), debrief start/status/result (3), mascot.tick promotion (1), session-event (1).

**Invariants preserved (non-negotiable):** MusicState single writer @10Hz; `_HAS_*` feature-flag pattern; no pydantic in `src/vibemix/ui_bus/`; AIza scan @ build time 0 matches; bundle ID `world.bravoh.vibemix` locked; `cohost_v4.py` POC files NEVER touched; LiveKit `session.output.audio` assigned BEFORE `session.start`; `allow_interruptions=False` at session level (`interrupt(force=True)` is the programmatic backdoor).

See `.planning/research/ARCHITECTURE.md` for the full module/class map + 3 trace walks + cross-process race-condition catalog.

### Critical Pitfalls

PITFALLS.md catalogs **41 v2.0-specific failure modes**: 9 Critical, 9 High, 13 Medium, 5 Low, 5 Cross-Cutting. The top 5 that MUST be encoded into phase plans:

1. **AX call from Python sidecar instead of Rust parent (Pitfall 3, Critical)** — Tauri #8329. **Prevention:** AX/Quartz call lives in Rust parent; codebase grep gate fails CI if AX called from Python.
2. **Cancel-and-refire blows the 50€/mo per-user proxy budget (Pitfall 1, Critical).** **Prevention:** Hard cap `CANCEL_COOLDOWN_S = 8.0`; soft cap 30 cancels per session; telemetry assertion auto-disables for the session.
3. **Citation linter strips entire live response → sustained silence streak (Pitfall 2, Critical).** **Prevention:** Telemetry guard — if `stripped_rate_15s > 0.4`, next response BYPASSES linter with `[unverified]` log marker.
4. **Mascot anticipation fires on misfire → false-positive lean-in then nothing (Pitfall 9, Critical).** **Prevention:** 2.5s anticipation timeout crossfades prep → `prep_settle`; cancel-aware crossfade; linter-aware crossfade.
5. **Apple Developer ID + agreement gating notarytool (Pitfall 5, Critical).** **Status:** Issuer ID `3f60cc6b-df70-4ff8-9ceb-865dac6c1b4b` supplied; URMDRP5M3P key matches but Apple Developer Program Agreement update is outstanding (Francesco-action). Deferred to Kaan-action-required surface.

See `.planning/research/PITFALLS.md` for the full 41-pitfall catalog.

---

## Implications for Roadmap

Recommended decomposition is **12 phases** (P15–P26 continuing from v0.1.0 Phase 14 close). Critical-path total: ~10-12 weeks engineering with 2 calendar weeks of parallel bundles. Phase ordering by criticality means the binary becomes shippable from P21 (sign + release) onwards.

### Phase 15: Recording Browser + Retention Enforcement
Cheap, no upstream dependencies — knock it out first. Standard file-system UI pattern.

### Phase 16: Hallucination Verification Gate (Kaan's DJ Ear Test)
Calendar-blocking; gates all downstream tuning. NOT a 30-session formal eval suite per memory.

### Phase 17 (parallel with P18): Hard Tek Detectors v1 + GenreRouter + MusicState Extension
Single biggest grounding win. 6 cross-genre detectors locked. PROJECT.md ↔ G-followup count contradiction (6 vs 8) — recommended: 6 baseline + 2 hard-tek overlay as Wave 2.

### Phase 18 (parallel with P17): Evidence Registry + Citation Grammar in Prompts (v1.0 prompt-only)
Technical implementation of anti-slop. Ships prompt-only-no-enforcement to seed corpus.

### Phase 19: Latency Stack v1 (Ack Bank + Cached Content + Cancel-and-Refire)
Sub-100ms first sound via ack bank. Cancel-cooldown cap from Day 1.

### Phase 20: Citation Linter ENFORCEMENT (Live Mode, Response-Level + Ack-Fallback)
Telemetry guard for strip-rate bypass. Depends on P18 + P19.

### Phase 21: Sign + Notarize + GitHub Release Matrix
Binary shippable AT PHASE CLOSE — any phase past this can be cut to v2.0.1 if launch timeline at risk.

### Phase 22 (parallel with P23): Mascot Anticipation Layer + Beat-Coupled Hip-Bob
Highest-leverage perceived-latency mask (400-1200ms covered).

### Phase 23 (parallel with P22): 10-SKU MIDI Controller Library + MidiMapLoader
Cross-platform grounding spine. Verified sniff data for 9 unverified SKUs.

### Phase 24: djay Pro Mac Overlay Highlight (12 Elements + AX-from-Rust-Parent)
Viral demo Beat A anchor. Mac-only in v2.0. Day-1 AX feasibility spike required.

### Phase 25: Pyrekordbox XML One-Shot Import + Fuzzy Lookup
Durable library source (post-SQLCipher breakage). 4-tier confidence ladder fuzzy lookup.

### Phase 26: README Full Rewrite + Branding + Social Assets + Day-Zero Ops + Viral Demo Film + Channel Posts
Composite launch phase. All assets ship together at the launch moment.

### Phase Ordering Rationale

- **Critical-path order: P15 → P16 → P17||P18 → P19 → P20 → P21 → P22||P23 → P24 → P25 → P26.** Two parallel bundles (P17||P18, P22||P23). Binary shippable from P21.
- **Phase 16 is calendar-blocking** — its tuning gates detector + ack + linter + anticipation phases.
- **P18 ships v1.0 prompt-only-no-enforcement** so Gemini learns grammar in prod → P20 enforces.
- **AX bridge has hardware-rig requirement** — ship later (P24) when binaries pipeline stable.
- **Library intelligence + post-session debrief explicitly v2.1+** — v2.0 ships only the architectural slot for debrief (sidecar `--debrief` flag + port 8766 + IPC reservations).

### Research Flags

**Needs `/gsd-research-phase` at planning time:** P17 (detector count contradiction), P22 (text-channel timing spike pre-phase), P24 (AX-from-Rust-parent feasibility spike on signed bundle), P25 (pyrekordbox SQLCipher dep verification), P26 (demo film storyboard validation).

**Skip research (standard patterns):** P15, P18, P19, P20, P21, P23 — all implementation-ready from research artifacts.

### Cross-Document Contradictions Flagged

1. **Debrief timing:** PROJECT.md lists as v2.0 table-stakes; FEATURES.md cuts to v2.1. **Recommended call:** ship architectural slot in v2.0 (sidecar --debrief flag + port 8766 + IPC reservations) without UI surface; full UI feature in v2.1.
2. **Event detector count:** PROJECT.md says 6 baseline; G-followup says 8 (6 baseline + 2 hard-tek overlay). **Recommended call:** 6 baseline in P17 v2.0; 2 hard-tek overlay (`DISTORTION_CLIMB`, `ACID_LINE_ENTRY`) as Wave 2 of P17, ear-test-gated, deferred to v2.1 if timeline at risk.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | **HIGH** | 5 new deps all verified on PyPI; sqlite-vec Windows wheel gap has documented numpy fallback. One YELLOW (ffmpeg LGPL on Win, +20MB) with industry-standard precedent. License audit clean. |
| Features | **HIGH** | 7-category catalog + complexity hints + dependency graph. **MEDIUM** on spike-gated items. PROJECT.md ↔ FEATURES.md contradictions flagged. |
| Architecture | **HIGH** | Existing-architecture surface verified; 19 → 38 IPC delta enumerated; 3 trace walks. **MEDIUM** on AX bridge + debrief sibling sidecar (first-time-integrated). |
| Pitfalls | **HIGH** | 41 v2.0-specific pitfalls + concrete prevention strategy per pitfall + pitfall-to-phase mapping. |

**Overall confidence:** **HIGH** — the v2-bucket research swarm did the heavy lifting; the 4 GSD research files integrate it into actionable artifacts; the spike-gated items have documented fallback paths that don't block v2.0 ship.

### Gaps to Address

- **PROJECT.md ↔ FEATURES.md contradiction on debrief:** Ship architectural slot in v2.0, full feature in v2.1.
- **PROJECT.md ↔ FEATURES.md contradiction on detector count:** 6 baseline in v2.0 P17, 2 hard-tek overlay as Wave 2.
- **Predictive firing default:** Gated on Kaan ear-test after first 3 sessions.
- **Inline emote-tag vocab:** 1-day spike pre-Phase 22.
- **AX-from-Rust-parent on installed bundle:** Day-1 spike of Phase 24.
- **sqlite-vec Windows wheel:** Re-check PyPI at Phase 25/26 kickoff.
- **`pyrekordbox==0.4.4` install dep tree:** Verify at Phase 25 plan-time.
- **`cached_content` field forwarded through `livekit-plugins-google`:** Plan-checker smoke test at Phase 19.
- **Bravoh-side proxy capacity under viral 10× spike:** Load test in Phase 26.
- **Phase 16 sample-size of 1:** Stretch — Francesco + 5-tester beta pool.
- **Apple Developer Program Agreement update:** Francesco-action-required.

---

## Sources

### Primary (HIGH confidence)

- `.planning/research/STACK.md`, `FEATURES.md`, `ARCHITECTURE.md`, `PITFALLS.md`
- `.planning/research/v2-buckets/SYNTHESIS.md` + 11 deep v2-bucket artifacts
- `.planning/PROJECT.md`, `.planning/STATE.md`
- `cohost_v4.py` (canonical port baseline)
- `livekit-agents==1.5.8` source verification — `interrupt(force=True)` empirically verified
- `google-genai==2.0.1` source verification — `caches.create()` + `cached_content`

### Memory anchors (locked decisions — load-bearing constraints)

- `project_v2_open_candidates`, `feedback_no_clap_use_gemini_embedding`, `project_one_click_install_hard_req`, `feedback_no_scope_creep_clean_utility`, `project_v4_canonical_baseline`, `project_phase_16_kaan_dj_testing`, `project_v0_1_0_rc1_open_bugs`, `project_anti_slop_grounded_gemini_thesis`, `project_mascot_as_vtuber_personality_surface`, `project_visual_direction_cdj_whisper`, `feedback_privacy_scope_narrow`, `feedback_autonomous_no_grey_area_pause` (extended to defer-blockers)

### Secondary (MEDIUM confidence — external sources)

- [Tauri #8329](https://github.com/tauri-apps/tauri/issues/8329), [#11488](https://github.com/tauri-apps/tauri/issues/11488), [#11461](https://github.com/tauri-apps/tauri/issues/11461)
- [PyPI — pyrekordbox 0.4.4](https://pypi.org/project/pyrekordbox/), [sqlite-vec 0.1.9](https://pypi.org/project/sqlite-vec/), [pydub 0.25.1](https://pypi.org/project/pydub/), [mutagen 1.47.0](https://pypi.org/project/mutagen/), [watchdog 6.0.0](https://pypi.org/project/watchdog/)
- [Gemini context caching support matrix](https://ai.google.dev/gemini-api/docs/caching)
- [Three.js makeClipAdditive docs](https://threejs.org/docs/#api/en/animation/AnimationUtils)
- [Apple notarytool docs](https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution)

### Tertiary (LOW confidence — flag for plan-time validation)

- sqlite-vec Windows wheel availability at planning time
- `pyrekordbox==0.4.4` SQLCipher dep tree (might need `--no-deps`)
- ffmpeg LGPL static build pinning for Windows
- AX-from-Rust-parent feasibility on installed code-signed bundle
- Gemini text-channel ordering vs TTS audio chunks (1-day spike pre-Phase 22)

---

*Research synthesis completed: 2026-05-14*
*Ready for `/gsd-roadmapper` decomposition: yes*
*Suggested phase count: 12 (P15-P26), critical path ~10-12 weeks engineering, two parallel bundles (P17||P18, P22||P23), shippable from P21 close*
