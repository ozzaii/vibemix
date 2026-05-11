# vibemix — State

**Last updated:** 2026-05-11 (Phase 5 complete)

---

## Project Reference

- **Project:** vibemix — open-source AI DJ co-host (Bravoh's first OSS release)
- **Core value:** "Real DJ friend in your ear" — never hallucinating, never breaking flow, never AI slop.
- **Current focus:** Roadmap defined. Awaiting kickoff for Phase 1 (Platform Protocol Firewall).
- **Milestone:** v1 (Bravoh-wedge drop) — target ship ~3-4 weeks (~early June 2026, before Bravoh public launch).
- **Project mode:** standard.
- **Granularity:** fine (20 phases).
- **Model profile:** quality (all agents on Opus, all checkpoints on).

---

## Current Position

- **Phase:** 06 — Genre-Aware Phase Detection (next).
- **Plan:** None active.
- **Status:** Phase 5 ✅ complete (wave commits `c04b403` / `1549130` / `ba8a013` / `3a3bc4c` / +final docs). The FastAPI proxy in `proxy/` is an independent Python project that mounts five endpoints behind nginx on `api.altidus.world` (deployment runbook pending Kaan's operational schedule): `GET /healthz` (unauth), `POST /api/vibemix/v1/register` (unauth + IP-rate-limited; install_uuid → JWT exchange via PyJWT HS256 with `algorithms=["HS256"]` explicit allowlist blocking alg=none), `POST /v1beta/models/{model}:streamGenerateContent` (Gemini SSE pass-through), `POST /v1beta/models/{model}:generateContent` (non-streaming sibling), `POST /v1/audio/speech` (OpenAI-compatible TTS → OpenRouter PCM stream). Path shape per RESEARCH Q1 verified against genai SDK URL builder; CONTEXT's `/api/vibemix/v1/llm/generate` superseded. JWTMiddleware (BaseHTTPMiddleware) sets `request.state.install_uuid`; slowapi `@limiter.limit()` decorator (NOT `SlowAPIMiddleware`) reads it at handler time. 60 rpm per install_uuid + 2000 rpd via Redis `INCR + EXPIRE NX` (Redis 7.0+ required — documented). Circuit breaker (10 consec 5xx → 503 + Retry-After: 60). Upstream-secret sanitization tested with forged 401 carrying an AIza string — zero leakage in sanitized 502 response (LLM-07 pin). Client side: `vibemix.agent.install_uuid.get_or_create_install_uuid()` with keyring primary + file fallback at platform path + Pitfall-6 null-backend detection; `vibemix.agent.jwt_cache.get_or_refresh_jwt()` with 7-day-from-expiry refresh; `vibemix.agent.proxy_client.build_proxy_genai_client(jwt, base_url)` + `build_proxy_tts_chain(jwt, base_url)`. `build_llm` and `build_tts_chain` extended with `mode='direct'|'proxy'` dispatch — Phase 4 direct path byte-identical (regression-safe per G8); proxy path threads `HttpOptions(base_url, Authorization: Bearer JWT)` into `google_plugin.LLM` directly (verified at livekit/plugins/google/llm.py:117). `__main__.py` reads `VIBEMIX_LLM_MODE` + `VIBEMIX_PROXY_BASE_URL` + `VIBEMIX_CLIENT_VERSION`. NO silent fallback proxy → direct — setup failures `sys.exit` non-zero with clear errors. 385 vibemix tests green (346 baseline + 39 new client-side) + 79 proxy tests green. All 8 acceptance gates PASS (G3: zero AIza in `src/vibemix/`; G6: alg=none rejected — the phase-level invariants). POC files diff-untouched against Phase 4 close (`ede9e59`). Deployment runbook (`proxy/README.md`) covers Docker + nginx + PM2 + Pitfalls 2/4/6.
- **Progress:** 5/20 phases complete.

```
[█████               ] 25% (5/20 phases)
```

---

## Performance Metrics

(Populated as phases complete.)

| Metric | Value |
|--------|-------|
| Phases complete | 5 / 20 |
| v1 requirements mapped | 128 / 128 |
| v1 requirements complete | 16 / 128 |
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

### Open To-dos

- File SignPath Foundation OSS application **on day 1 of Phase 1** (lead time ~3 weeks).
- Collect ~30 min recorded sets per genre (techno / house / D&B / disco / pop) for Phase 6 validation harness; Francesco's DJ network is the obvious source.
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
- 2026-05-11 — Phase 5 (FastAPI Proxy + Install-UUID JWT) shipped end-to-end: 5 wave commits (`c04b403` proxy scaffold — FastAPI app + healthz + pydantic-settings + Redis quota helper + Dockerfile + compose, `1549130` JWT auth HS256-only with alg=none blocked + /register IP-keyed + slowapi limiter wiring, `ba8a013` LLM SSE + TTS PCM routes — Gemini-native paths verified vs SDK URL builder + circuit breaker + upstream-secret sanitization with zero-AIza leakage test, `3a3bc4c` client install_uuid + JWT cache + factory mode dispatch with NO silent fallback, + final docs commit). 385 vibemix tests green (346 baseline + 39 client-side) + 79 proxy tests green. All 8 acceptance gates PASS — G3 (zero AIza in src/vibemix/) and G6 (alg=none blocked) are the phase-level invariants. `proxy/` is an independent Python project with own pyproject.toml + uv.lock + .venv. Routes mirror genai SDK URL shape (`/v1beta/models/{model}:streamGenerateContent` + sibling + `/v1/audio/speech` OpenAI-compat); CONTEXT's `/api/vibemix/v1/llm/generate` superseded by RESEARCH Q1. JWT TTL 90 days (locked); ROADMAP's `15-30 min` reconciled. slowapi via @limiter.limit() decorator NOT SlowAPIMiddleware (RESEARCH Q2). google_plugin.LLM accepts http_options directly (verified at livekit/plugins/google/llm.py:117). Client-side install_uuid keyring + file fallback handles Pitfall 6 (null backend detection). NO silent fallback proxy → direct — setup failures sys.exit non-zero. POC files diff-untouched against Phase 4 close. Deployment runbook in proxy/README.md covers Docker + nginx + PM2 + Pitfalls 2/4/6; actual deployment to api.altidus.world pending Kaan's operational schedule (does NOT block phase close).
- 2026-05-11 — Phase 4 (LiveKit Cascade Agent Pivot) shipped end-to-end: 4 wave commits (`28f5f09` agent persona + config + LLM factory + TTS chain with OpenRouter monkey-patch, `1fa021a` DJCoHostAgent llm_node override + PlaybackQueueAudioOutput sink, `2b7ea9b` runtime loops — coach event pump + diag meter + WS mascot bus, `ede9e59` __main__ orchestrator + CI integration smoke). 346 tests green (270 from Phase 3 + 76 new across agent/runtime/smoke). All 12 acceptance gates PASS. SYSTEM_INSTRUCTION byte-identical to v4:150-213. OpenRouter monkey-patch active at module load (TTS-01 pins invariant). DJCoHostAgent.llm_node bypasses LiveKit's text-only cascade and calls `google.genai.aio.models.generate_content_stream` directly with last 18s of audio attached as multimodal Part. Single-modality `screen_jpeg = None` preserved (v4:1502-1503 anti-hallucination). Per-invocation dump folder structure preserved verbatim for live-debug parity. Twin AudioBuffer instances in main() (140s state + INVOKE_AUDIO_SECONDS+5.0 clean). session.output.audio assigned BEFORE session.start (v4:2030-2033 invariant). _HAS_WS feature flag dropped (Phase 2 anti-pattern fix). WS_HOST/WS_PORT centralized in vibemix.audio.constants. Integration smoke test runs in CI without devices via mocked AudioMacOS + LiveKit + Gemini. ARCH-06 re-mapped — cascade runs headless (no Room) per v4:2031, no bundled livekit-server binary needed; documented in 04-SUMMARY.md Deviations. POC files untouched throughout (v4 still runnable via run_v4.sh).

### Next Session

- Continue from Phase 6 (Genre-Aware Phase Detection — SENSE-03, SENSE-04, SENSE-06, SENSE-07, SENSE-08, SENSE-10, UX-03). Builds percentile-based phase detector + 5-genre profile JSON + crest-factor compression detection + BPM half/double validator + vocal-section detector.
- Kaan-side outstanding: SignPath OSS application (Phase 1 carry-forward, ~1 week SLA). Optional live smoke verification of `python -m vibemix` vs `./run_v4.sh` on his rig (run `VIBEMIX_LIVE_SMOKE=1 uv run pytest -m macos_audio tests/test_main_live.py`). **NEW (Phase 5 carry-over)**: deploy `proxy/` to `api.altidus.world` per `proxy/README.md` Production deployment when ready. Phase 5 closes regardless of deployment timing — code is complete and locally runnable.

---

*State managed by gsd-roadmapper at 2026-05-11; updated by /gsd-autonomous on 2026-05-11 (Phase 4 complete).*
