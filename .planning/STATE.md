---
gsd_state_version: 1.0
milestone: v0.1.0
milestone_name: milestone
status: executing
last_updated: "2026-05-11T20:03:38.326Z"
progress:
  total_phases: 20
  completed_phases: 3
  total_plans: 33
  completed_plans: 18
  percent: 55
---

# vibemix — State

**Last updated:** 2026-05-11 (Phase 7 ✅ complete)

---

## Project Reference

- **Project:** vibemix — open-source AI DJ co-host (Bravoh's first OSS release)
- **Core value:** "Real DJ friend in your ear" — never hallucinating, never breaking flow, never AI slop.
- **Current focus:** Phase 08 — macos-screencapturekit-migration
- **Milestone:** v1 (Bravoh-wedge drop) — target ship ~3-4 weeks (~early June 2026, before Bravoh public launch).
- **Project mode:** standard.
- **Granularity:** fine (20 phases).
- **Model profile:** quality (all agents on Opus, all checkpoints on).

---

## Current Position

Phase 7 ✅ complete — Windows Port (Audio + Screen) shipped: four Windows backends + selector + `_midi_common` refactor + windows-setup.md doc. Mocked-test verified on macOS; Phase 20 CI runs windows_only live tests on `windows-latest`.

Phase: 08 (macos-screencapturekit-migration) — EXECUTING
Plan: 1 of 2

- **Phase:** 08 — macOS ScreenCaptureKit Migration (replaces deprecated `Quartz.CGWindowListCreateImageFromArray`; parallelizes with Phase 9).
- **Plan:** None active.
- **Status:** Executing Phase 08
- **Progress:** 7/20 phases complete.

```
[███████             ] 35% (7/20 phases)
```

---

## Performance Metrics

(Populated as phases complete.)

| Metric | Value |
|--------|-------|
| Phases complete | 7 / 20 |
| v1 requirements mapped | 128 / 128 |
| v1 requirements complete | 22 / 128 |
| Critical pitfalls mitigated | 0 / 9 |
| High-severity pitfalls mitigated | 0 / 7 |
| Hallucination verification (≥95% grounded) | Not yet measured |
| Reaction-reel slop grading (≥4.0 avg) | Not yet measured |
| 60-minute soak test (zero `session_error`) | Not yet measured |
| Binary attack verification (zero `AIza` matches) | Not yet measured |

---

## Accumulated Context

### Decisions Locked

- Brain swap: `RealtimeModel` → `AgentSession` cascade (`stt=None`, `vad=None`, `llm=google.LLM`, `tts=google.beta.gemini_tts.TTS`). Native Audio code-path stays in repo as opt-in toggle, not the default.
- Architecture: 3-process — Tauri Rust shell + Python sidecar (PyInstaller `--onedir`) + remote FastAPI proxy on `api.altidus.world`.
- API key protection: install-UUID JWT in OS keychain + slowapi/Redis rate limit (60 rpm / 2000 rpd per UUID). Client never holds raw `AIza` key.
- Platforms: macOS 12.3+ and Windows 10/11 in v1. Linux excluded.
- Python: 3.12.x (drop from POC's 3.14 — widest wheel availability for PyInstaller / PyAudioWPatch / scipy).
- License: Apache 2.0 + DCO (per PITFALLS P14 — Bravoh's commercial-internal-use needs).
- Code signing: Apple Developer ID (Kaan has) + SignPath Foundation OSS cert (free for OSS). **Application filed day-1 of Phase 1** (3-week lead time).
- Granularity: fine — 20 phases. Critique → execute loop runs inside every phase (plan-checker before execute, verifier after, ui-checker/auditor between polish iterations, code-reviewer on output).
- Dedicated **Polish Phase (14)** between feature-complete and verification — FL-Studio quality bar, not a final-week sweep.
- Mascot (Avery) is a **first-class feature**, not decoration (Phase 13).
- **ARCH-06 re-mapped (Phase 4 retro)** — cascade `AgentSession` runs headless (no Room — v4:2031), so a bundled `livekit-server --dev` binary is unnecessary for the cascade path. Either drops or moves to Phase 11 (Tauri shell) if a Room-based protocol becomes useful for the desktop wrapper.
- **Phase 5 — Proxy paths Gemini-native + OpenAI-compat**: `/v1beta/models/{model}:streamGenerateContent` (LLM SSE) + sibling `:generateContent` (non-stream) + `/v1/audio/speech` (TTS, OpenAI-compat); plus `/api/vibemix/v1/register` (unauth, IP-limited) and `/healthz` (unauth). CONTEXT's `/api/vibemix/v1/llm/generate` superseded by RESEARCH Q1 verification of genai SDK URL builder.
- **Phase 5 — JWT HS256 only, alg=none blocked**: `algorithms=["HS256"]` explicit allowlist on every decode. PyJWT 2.12.1+ (CVE-2026-32597 patch). 90-day TTL (locked); ROADMAP's `15-30 min` was stale.
- **Phase 5 — slowapi via decorator, not middleware**: `@limiter.limit("60/minute")` runs `key_func` at handler time, AFTER `JWTMiddleware` sets `request.state.install_uuid`. `SlowAPIMiddleware` would invert ordering — explicitly avoided per RESEARCH Q2.
- **Phase 5 — IP-keyed `/register` limit**: install_uuid doesn't exist yet at register time. IP-keying blocks register-spam.
- **Phase 5 — NO silent fallback proxy → direct**: setup failures `sys.exit` non-zero with clear errors. Locked per CONTEXT — silent fallback would defeat the entire security goal.
- **Phase 5 — `mode='direct'` is the Phase 5 client default**. Phase 18 installer flips to `'proxy'` for distributed binaries. Kaan's dev rig (`.env` with `GEMINI_API_KEY`) keeps working unchanged.
- **Phase 5 — Redis 7.0+ required** for `EXPIRE NX`. Documented in `proxy/README.md`.
- **Phase 6 — Percentile thresholds: p30 / p70 / p95** drawn from the rolling 120s `long_arc_curve`; 3-tick hysteresis at 10Hz = 300ms minimum dwell; `silent` commits immediately (no hysteresis — anti-hallucination).
- **Phase 6 — Cold start uses profile's absolute thresholds**, not v4's global `SILENT_RMS`/`LOW_RMS`/`PEAK_RMS` constants. Pop and disco have a higher noise floor than techno.
- **Phase 6 — JSON profile schema frozen + hand-validated** (no pydantic dep — Critical Constraint 6). Validator raises ValueError on missing/malformed; silent defaults explicitly prohibited.
- **Phase 6 — `VIBEMIX_GENRE_PROFILE` env**: default `'techno'`, `'none'`/`'unknown'`/`''` = Phase 3 absolute-threshold fallback (Critical Constraint 8), invalid name = `sys.exit` listing valid choices.
- **Phase 6 — `classify_phase` dispatches**: positional / `profile=None` → v4 plain-str path (golden-equivalent pinned via test); `profile=<GenreProfile>` → tuple percentile path.
- **Phase 6 — Hysteresis state in `state_refresh_loop` local scope, NOT MusicState** (Critical Constraint 7 — MusicState holds consumer-readable evidence; hysteresis is internal detector machinery).
- **Phase 6 — BPM validator**: half→double order, zero/negative short-circuit. Out-of-range pass-through (downstream `BPM_VALID_MIN/MAX` filter handles it).
- **Phase 6 — VocalDetector**: 2-of-3 heuristic rules + 1.5s in / 2.5s out hysteresis. Profile parameter accepted but unused in v1 — reserved for future per-genre threshold tuning.
- **Phase 6 — EventDetector LAYER_ARRIVAL gated on `not state.vocal_active`**; other 5 event types byte-identical to v4. Baseline `last_band_signature` still updates inside gated branch so post-vocal jumps don't false-fire.

### Open To-dos

- File SignPath Foundation OSS application **on day 1 of Phase 1** (lead time ~3 weeks).
- Collect ~30 min recorded sets per genre (techno / house / D&B / disco / pop) for **Phase 16** validation harness (was Phase 6; Phase 6 ships the detector + Phase 16 measures per-genre F1 ≥85%). Francesco's DJ network is the obvious source. Collection can begin now in parallel with Phase 7.
- Confirm `.env` was never committed to git (`git log --all --full-history -- .env`); rotate Gemini API key if any doubt.
- Confirm `livekit-plugins-google.beta.gemini_tts.TTS` smoke test in CI (it's in `beta` namespace; need stability check).

### Blockers

None yet — all dependencies are pinned and verified.

### Risks (carried from PITFALLS.md)

- **Critical** P1 (AI slop) and P2 (multimodal hallucination) — existential. Mitigated by prompt-engineering iteration in Phase 10 + verification gates in Phases 16-17.
- **Critical** P3 (API key leakage) — fully mitigated by Phase 5 proxy + Phase 18 binary attack verification.
- **Critical** P6 (day-one installer broken) — mitigated by Phase 18 sign+notarize discipline + Phase 20 fresh-machine rehearsal.
- **High** P14 (license + CLA) — Apache 2.0 + DCO chosen for Bravoh commercial-internal-use compatibility.

---

## Session Continuity

### Last Session

- 2026-05-11 — Phase 2 (Audio Core Port + Ring Buffer Fix) shipped end-to-end: 4 wave commits (`bb63774` skeleton+constants+Levels, `59fdb62` ring-buffer rewrite fixes np.concatenate at v4:300+v4:462, `54e6432` features.py DSP + VoiceRecorder, `62413e9` AudioMacOS impl + sample-rate guard) + verification gate (8/8 pass) + phase SUMMARY. tracemalloc tests pin zero-alloc invariant on both buffer push paths. AudioMacOS satisfies @runtime_checkable AudioBackend Protocol via isinstance. SampleRateMismatchError raises with Audio MIDI Setup actionable message on both pre-open and post-open paths. Phase 1 firewall test relaxed to skip underscore-prefixed concrete impls (planned amendment per Plan 04 critical constraint). 78 tests green (10 Phase 1 + 14 W1 + 21 W2 + 20 W3 + 13 W4). 2 live BlackHole smoke tests collected under macos_audio marker.
- 2026-05-11 — Phase 3 (Sensing & State Port) shipped end-to-end: 4 wave commits (`c923025` MusicState + classify_phase + audible-deck/track resolvers v4 verbatim, `8106a16` Event + EventDetector with class-attrs removed/imported from vibemix.audio.constants, `9104052` AICoach static-method-only with phase= omitted per v4:1350-1351 anti-hallucination invariant, `8e04dfc` state_refresh_loop 10Hz single writer + macOS Screen/MIDI/Track backends satisfying Phase 1 Protocols structurally). 270 tests green (78 from Phase 2 + 192 new). All 11 acceptance gates PASS. DDJ-FLX4 _CC_MAP/_NOTE_MAP byte-identical to v4:582-598 (asserted by equality test). AICoach task strings byte-for-byte from v4:1391-1427 (golden-string tests). MUSIC_PRESENCE_MIN_SECONDS / BPM_VALID_MIN / BPM_VALID_MAX lifted from EventDetector class-attrs to vibemix.audio.constants module scope. Pioneer DDJ-FLX4 play-state limitation reproduced verbatim from v4 (Phase 9 fix docketed in _midi_macos.py docstring). macOS ScreenCaptureKit migration docketed for Phase 8. POC files untouched (v4 still runnable via run_v4.sh throughout the entire phase).
- 2026-05-11 — Phase 7 (Windows Port — Audio + Screen) shipped end-to-end: 5 wave commits (`76d3065` Wave 1 — platform selector + `_midi_common` extraction + Windows-only deps in pyproject with `sys_platform == 'win32'` markers, `6ebd5e5` Wave 2 plan 07-02 — AudioWindows WASAPI loopback impl + sample-rate guard, `84586ec` Wave 2 plan 07-03 — ScreenWindows + TrackWindows via winsdk SMTC + asyncio.run executor bridge, `df97dd3` Wave 3 — MidiWindows + cross-platform integration test, + final Wave 4 docs commit closing the phase). 614 tests green (531 Phase 6 baseline + 83 new across 5 mocked + 1 integration + 1 _midi_common test file + 4 live stubs gated on windows_only). All 10 acceptance gates PASS with 2 documented pre-existing items (test_audio_macos_live HEADPHONEMG env mismatch from Wave 1 baseline + ruff I001 in test_midi_common.py from Wave 1 — both in deferred-items.md). Selector + lazy-import contract pinned: `pyaudiowpatch` / `win32*` / `winsdk` never reach sys.modules on macOS, verified by integration test. winsdk async API bridged via `asyncio.run` inside `loop.run_in_executor` — mirrors macOS subprocess pattern (Phase 8 ScreenCaptureKit will adopt same pattern). Windows-only deps via `sys_platform == 'win32'` markers in `[project] dependencies` (chosen over `[project.optional-dependencies]` group — simpler for both `uv sync` and PyInstaller). DJ-app hint list expanded from macOS's djay-only to `("djay", "serato", "traktor", "rekordbox", "virtualdj")` — Windows is where Serato/Traktor/rekordbox/VirtualDJ users live. `docs/windows-setup.md` (92 lines, 8 sections) covers Phase 20 fresh-machine rehearsal + early Windows DJ-friend testers. ControllerState cross-imported from `_midi_macos` into `_midi_windows` — extraction to `_midi_common.py` deferred to Phase 9. POC files diff-untouched throughout (verified by Gate 10). Optional Kaan-verify checkpoint skipped — Kaan doesn't have Windows handy; Phase 20 CI matrix on `windows-latest` is the authoritative live gate.
- 2026-05-11 — Phase 6 (Genre-Aware Phase Detection) shipped end-to-end: 4 wave commits (`11d358a` genre profile system + 5 JSON profiles + active-profile singleton + hand-written schema validator, `1c4e264` crest factor + EMA smoother + BPM half/double validator + VocalDetector with 1.5s/2.5s hysteresis, `01ff963` percentile phase detector + MusicState +4 fields + state_refresh_loop wiring + Phase 3 golden equivalence pinned, `84b6978` EventDetector LAYER_ARRIVAL vocal gate + VIBEMIX_GENRE_PROFILE env + vibemix.state re-exports) + final docs commit closing the phase. 531 tests green (385 Phase 5 baseline + 146 new). All 10 acceptance gates PASS. 5 hand-tuned genre profile JSONs (techno / house / drum_and_bass / disco / pop) ship in the wheel via hatchling default package-data inclusion (verified via `uv build --wheel` + `unzip -l`). Phase 3 golden equivalence pinned across 10 parametric curves — `classify_phase(curve, audible, profile=None)` returns the SAME string as the original v4 body for the SAME inputs. MusicState gains 4 new fields (`crest_factor`, `vocal_active`, `bpm_corrected`, `genre_profile_name`) with backward-compat defaults — Phase 3's `test_music_state.py` passes unchanged. Hysteresis state in `state_refresh_loop` local scope, NOT MusicState (Critical Constraint 7). LAYER_ARRIVAL gate is the ONLY EventDetector change — other 5 event types byte-identical to v4. POC files diff-untouched (`cohost_v4.py` + `run_v4.sh` continue to function unchanged throughout the entire phase). SENSE-10's 30-min per-genre validation harness deferred to Phase 16 per CONTEXT out-of-scope clause. Open To-do: collect 30-min recorded sets per genre — can begin now in parallel with Phase 7.
- 2026-05-11 — Phase 5 (FastAPI Proxy + Install-UUID JWT) shipped end-to-end: 5 wave commits (`c04b403` proxy scaffold — FastAPI app + healthz + pydantic-settings + Redis quota helper + Dockerfile + compose, `1549130` JWT auth HS256-only with alg=none blocked + /register IP-keyed + slowapi limiter wiring, `ba8a013` LLM SSE + TTS PCM routes — Gemini-native paths verified vs SDK URL builder + circuit breaker + upstream-secret sanitization with zero-AIza leakage test, `3a3bc4c` client install_uuid + JWT cache + factory mode dispatch with NO silent fallback, + final docs commit). 385 vibemix tests green (346 baseline + 39 client-side) + 79 proxy tests green. All 8 acceptance gates PASS — G3 (zero AIza in src/vibemix/) and G6 (alg=none blocked) are the phase-level invariants. `proxy/` is an independent Python project with own pyproject.toml + uv.lock + .venv. Routes mirror genai SDK URL shape (`/v1beta/models/{model}:streamGenerateContent` + sibling + `/v1/audio/speech` OpenAI-compat); CONTEXT's `/api/vibemix/v1/llm/generate` superseded by RESEARCH Q1. JWT TTL 90 days (locked); ROADMAP's `15-30 min` reconciled. slowapi via @limiter.limit() decorator NOT SlowAPIMiddleware (RESEARCH Q2). google_plugin.LLM accepts http_options directly (verified at livekit/plugins/google/llm.py:117). Client-side install_uuid keyring + file fallback handles Pitfall 6 (null backend detection). NO silent fallback proxy → direct — setup failures sys.exit non-zero. POC files diff-untouched against Phase 4 close. Deployment runbook in proxy/README.md covers Docker + nginx + PM2 + Pitfalls 2/4/6; actual deployment to api.altidus.world pending Kaan's operational schedule (does NOT block phase close).
- 2026-05-11 — Phase 4 (LiveKit Cascade Agent Pivot) shipped end-to-end: 4 wave commits (`28f5f09` agent persona + config + LLM factory + TTS chain with OpenRouter monkey-patch, `1fa021a` DJCoHostAgent llm_node override + PlaybackQueueAudioOutput sink, `2b7ea9b` runtime loops — coach event pump + diag meter + WS mascot bus, `ede9e59` __main__ orchestrator + CI integration smoke). 346 tests green (270 from Phase 3 + 76 new across agent/runtime/smoke). All 12 acceptance gates PASS. SYSTEM_INSTRUCTION byte-identical to v4:150-213. OpenRouter monkey-patch active at module load (TTS-01 pins invariant). DJCoHostAgent.llm_node bypasses LiveKit's text-only cascade and calls `google.genai.aio.models.generate_content_stream` directly with last 18s of audio attached as multimodal Part. Single-modality `screen_jpeg = None` preserved (v4:1502-1503 anti-hallucination). Per-invocation dump folder structure preserved verbatim for live-debug parity. Twin AudioBuffer instances in main() (140s state + INVOKE_AUDIO_SECONDS+5.0 clean). session.output.audio assigned BEFORE session.start (v4:2030-2033 invariant). _HAS_WS feature flag dropped (Phase 2 anti-pattern fix). WS_HOST/WS_PORT centralized in vibemix.audio.constants. Integration smoke test runs in CI without devices via mocked AudioMacOS + LiveKit + Gemini. ARCH-06 re-mapped — cascade runs headless (no Room) per v4:2031, no bundled livekit-server binary needed; documented in 04-SUMMARY.md Deviations. POC files untouched throughout (v4 still runnable via run_v4.sh).

### Next Session

- Continue from Phase 8 (macOS ScreenCaptureKit Migration — ARCH-02 macOS-side hardening). Replace deprecated `Quartz.CGWindowListCreateImageFromArray` with `pyobjc-framework-ScreenCaptureKit`. Keep `Quartz.CGWindowListCopyWindowInfo` for window enumeration. Parallelizes with Phase 9 (MIDI controller library).
- Kaan-side outstanding: SignPath OSS application (Phase 1 carry-forward, ~1 week SLA). Optional live smoke verification of `python -m vibemix` vs `./run_v4.sh` on his rig. **Phase 5 carry-over**: deploy `proxy/` to `api.altidus.world` when ready. **Phase 6 + 7 carry-over**: collect 30-min recorded sets per genre (techno / house / D&B / disco / pop) for Phase 16; arrange Windows test access for Phase 20 fresh-machine rehearsal. **Phase 7 deferred items** (in `.planning/phases/07-windows-port-audio-screen/deferred-items.md`): test_audio_macos_live HEADPHONEMG env mismatch (broaden substring or mark macos_audio opt-in) + ruff I001 in test_midi_common.py (one-line `ruff check --fix`).

---

*State managed by gsd-roadmapper at 2026-05-11; updated by /gsd-autonomous on 2026-05-11 (Phase 7 complete).*
