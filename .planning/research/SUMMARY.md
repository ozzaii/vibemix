# Project Research Summary

**Project:** vibemix — open-source AI DJ co-host (Bravoh's first OSS release)
**Domain:** Cross-platform real-time AI desktop app (audio capture + screen capture + MIDI ingest + multimodal LLM + streaming TTS), live music context
**Researched:** 2026-05-11
**Confidence:** HIGH on stack and pitfalls; HIGH on architecture's load-bearing pieces, MEDIUM on edge cases (LiveKit standalone-no-room option, ScreenCaptureKit migration ergonomics); MEDIUM on feature psychology (no shipping product like vibemix exists, so user-mode predictions are reasoned not observed)

## Executive Summary

vibemix is product-greenfield in a well-trodden technology landscape. The four parallel research tracks converge on the same shape: **keep the LiveKit Agents pipeline already running in the POC, swap the brain from Gemini Live Native Audio to a Gemini 3 Flash multimodal + Gemini TTS Flash cascade, add Windows support via PyAudioWPatch + mss + pywin32, route every API call through a FastAPI proxy on the existing `api.altidus.world` infrastructure, and ship as a Tauri + Python-sidecar desktop bundle.** The technical risks are well-mapped — none of the load-bearing pieces are speculative — and the existing POC has already validated the hardest parts (audio capture, phase detection, mic gating, audible-deck detection, session recording).

The *product* risks dominate, not the technical ones. The single existential failure mode is **AI slop** (Pitfall 1): if the AI sounds like ChatGPT-in-a-costume rather than a real DJ friend, the Bravoh-first-OSS positioning collapses on first contact. Closely behind sits **multimodal hallucination** (Pitfall 2) — the audio-and-screen grounding has to be evidence-anchored, with raw RMS/band numbers rather than paraphrases, audio bytes rather than descriptions, and a hand-graded reaction reel as the pre-release ship gate. These two pitfalls aren't engineering problems with libraries; they're prompt-engineering and evaluation problems that need a dedicated verification phase before any installer goes out the door. The 3-4 week timeline survives only if Phase ordering puts the cross-platform foundation and the architectural pivot (RealtimeModel → Flash+TTS cascade) early, runs Windows port in parallel, and reserves the final 4-5 days for slop/hallucination verification rather than for last-week feature creep.

The marketing-coordinated launch dimension is unusual: this is open-source as Bravoh's funnel wedge, not open-source as a community project. That means the GitHub repo is the front door (every section of PROJECT.md's "GitHub Presence — Maximum Sexification" is load-bearing), the installer must work on day one (Pitfall 6 — Gatekeeper/SmartScreen modals would kill paid IG ad conversion), and the SignPath Foundation OSS code-signing application has to be filed **now** because approval takes 1-3 weeks and the marketing wave can't wait. The proxy + abuse protection (Pitfall 3) is non-negotiable: a leaked Gemini key drains the budget for every user inside hours and is the kind of "Bravoh ships their API key in plain text" Hacker News story that turns a launch into a postmortem.

## Key Findings

### Recommended Stack

The stack is overwhelmingly continuity from the POC, plus three additions and two surgical swaps. The brain swap (RealtimeModel → Flash+TTS cascade) is the architectural pivot but it's a one-file constructor change because both code paths already use `session.generate_reply(instructions=...)`. The Windows port adds three libraries; the macOS path needs a forward-compatibility migration (Quartz → ScreenCaptureKit) because Apple obsoleted the old API in macOS 15.

**Core technologies:**
- **Python 3.12** (drop from POC's 3.14): widest wheel availability for PyInstaller, PyAudioWPatch, scipy, numpy — the shipping floor.
- **`livekit-agents` 1.5.8 + `livekit-plugins-google` 1.5.8**: keep the `AgentSession` pipeline, switch to cascade mode (`stt=None`, `vad=None`, `llm=google.LLM(...)`, `tts=google.beta.gemini_tts.TTS(...)`) — RealtimeModel is rejected.
- **`livekit-plugins-google.beta.gemini_tts.TTS`** (the exact load-bearing class): 30 prebuilt voices, 24 kHz mono PCM, chunked-HTTP streaming via `ChunkedStream`. Streaming PR is livekit/agents #4189 (merged 2025-12-08).
- **`google-genai` 2.0.1**: direct Gemini SDK used by the proxy's server side.
- **`sounddevice` 0.5.5 (macOS input + cross-platform output) + `PyAudioWPatch` 0.2.12.8 (Windows WASAPI loopback)**: split at the OS boundary — sounddevice #281 confirms WASAPI loopback will never land upstream.
- **`pyobjc-framework-ScreenCaptureKit` 12.1 (macOS) + `mss` 10.2.0 + `pywin32` 308+ (Windows)**: macOS 15 obsoleted Quartz `CGWindowListCreateImageFromArray` (pyobjc #627), forcing the ScreenCaptureKit migration; `Quartz.CGWindowListCopyWindowInfo` stays for window enumeration.
- **`mido` 1.3.3 + `python-rtmidi` 1.5.8**: cross-platform MIDI; no change from POC.
- **PyInstaller 6.20.0 + create-dmg + Inno Setup 6**: packaging — Briefcase rejected (immature with heavy C-extension stacks), Nuitka rejected (5-10× build time kills sprint iteration).
- **Tauri 2.x + React/Vite UI sidecar shell**: 10× smaller installer than Electron (system webview), matches Bravoh's existing React skillset, lets Rust own native concerns (signing, tray icon, auto-update) while Python owns all realtime work.
- **FastAPI + `slowapi` + Redis on `api.altidus.world`**: API-key proxy with per-IP and per-install-UUID rate limiting; reuses the Bravoh stack.
- **Apple Developer ID + SignPath Foundation (free OSS OV cert)**: code signing — SignPath application takes 1-3 weeks; **apply immediately**. CUA (trycua/cua) explicitly rejected as wrong abstraction (sandbox/VM-oriented, no MIDI, no audio).

Critical version pins: `livekit-agents` and `livekit-plugins-google` must match minors (both 1.5.8); `numpy` 2.x requires `scipy` ≥1.13 and PyInstaller ≥6.14 for working hooks; `pyobjc-framework-ScreenCaptureKit` requires macOS 12.3+ (drop macOS 11 support).

### Expected Features

**Must have (table stakes — without these the product feels broken):**
- One-click signed/notarized installer (DMG + MSI) — open-source-with-Terminal-commands has ~5% conversion
- Auto-detect master output device (no hardcoded BlackHole)
- Output destination picker (headphones vs speakers)
- Voice picker (male/female, Gemini TTS prebuilt)
- Genre picker at session start (calibrates phase-detection thresholds; auto-detect is research-grade)
- 3 skill modes × 2 interaction modes (6 prompt templates: Beginner/Intermediate/Pro × Hype-man/Coach)
- Mic gating during AI talk (POC has it; preserve)
- 10 curated MIDI mappings (DDJ-FLX4/400/FLX6/FLX10/1000/SX3, XDJ-RX3, Numark Party Mix Live, Hercules Inpulse 300/500) + generic MIDI fallback
- Cross-platform macOS + Windows; Linux excluded
- Calibration wizard on first run (max 3-step fast path; permissions, devices, controller, smoke test)
- Session recording (input.wav + voice.wav + events.jsonl — POC behavior)
- Push-to-mute / quick-disable hotkey (universal voice-assistant complaint mitigation)
- Vocal-section gating (AI shuts up over lyrics — hard etiquette gate)
- Reaction frequency throttle + per-event cooldown (anti-chatty default)
- Hallucination grounding via audio-evidence packet (hard release gate per PROJECT.md)

**Should have (differentiators — drive shareability and the Bravoh-funnel function):**
- Live voice reaction to master output (no shipping product does this — the wedge)
- Magnitude-aware EQ/fader awareness in prompts ("slight high boost" vs "killed the lows")
- Absolute set-timeline awareness ("you're 2:44 into the set; drop 11s ago")
- Audible-deck detection (A/B/mix) — solves #1 hallucination class
- Coach scorecard at session end (qualitative, never numeric/leaderboard)
- Genre-tuned phase thresholds (percentile-based, not absolute — handles compressed masters too)
- Bravoh-managed API key (zero-config, no Gemini account)
- Open-source under bravoh/vibemix (the marketing wedge)

**Defer (v1.x, post-launch validation):**
- Highlight reel export (manual review, never auto-publish — marketing-funnel multiplier)
- Session replay UI (currently raw WAVs)
- "Coach this moment" manual trigger (post-feedback feature)
- Additional controller mappings beyond curated 10
- Live mid-mix Coach nudges (Pro mode opt-in only)

**Defer (v2+ / never):** Next-track recommendation (anti-feature for v1 — that's PulseDJ/Algoriddim's space), DAW integration, iOS/iPad, Linux, custom voice cloning, real-time numeric set-score, Twitch/YouTube streaming integration, multi-language UI.

### Architecture Approach

vibemix is a three-process system: a **Tauri Rust shell** (UI host, tray icon, installer, auto-update), a **Python sidecar** that owns all realtime work in a single asyncio loop (capture → sensing/state → LiveKit AgentSession → playback), and a **remote FastAPI proxy** on Bravoh's existing `api.altidus.world` that issues install-UUID JWTs and proxies every Gemini call. The architectural pivot vs. the POC is replacing `realtime.RealtimeModel` with `AgentSession` cascade mode using a custom `Agent.llm_node()` override — the canonical LiveKit pattern for non-realtime multimodal LLM integration. The override yields `str` chunks that `tts_node()` (running `google.beta.gemini_tts.TTS`) consumes and streams as AudioFrames. Audio I/O, MIDI, screen capture, and now-playing detection sit behind a `platform/` protocol firewall — one import (`from vibemix.platform import audio_input, screen, nowplaying`) that resolves to macOS or Windows implementations at import time. The recommended room transport is a bundled local `livekit-server --dev` binary on `127.0.0.1:7880`, which keeps all the AgentSession plumbing (turn management, mic-gate, interrupt handling) working as documented without sending audio over the internet.

**Major components:**
1. **`platform/` (OS abstraction firewall)** — every OS-specific call (sounddevice, PyAudioWPatch, ScreenCaptureKit, Quartz, mss, pywin32, nowplaying-cli, winsdk GSMTC) lives here, fronted by Protocol classes.
2. **`audio/` + `midi/` + `sense/` + `state/` (sensing layer)** — port verbatim from `cohost_v2.py`: AudioBuffer, MicBuffer, Levels, ControllerState, ScreenBuffer, TrackInfo, MusicState (10 Hz writer), EventDetector (diffs MusicState → typed Events).
3. **`agent/` (LiveKit Agents integration)** — `DJCoHostAgent` subclasses `Agent` and overrides `llm_node()`; `gemini_flash.py` wraps `google-genai` for the multimodal call; `session.py` wires AgentSession with `google.beta.gemini_tts.TTS`.
4. **`proxy/` (auth + Gemini routing)** — install-UUID JWT fetch on first launch; every Gemini call goes via `api.altidus.world` with Bearer token; per-IP slowapi rate limit + per-install-UUID Redis quota (60 req/min, 2000 req/day).
5. **`tauri/` (UI shell)** — React+Vite webview in Tauri 2.x; communicates with Python sidecar over Tauri IPC (config in) + WebSocket on `127.0.0.1:8765` (telemetry out at 30 Hz, same pattern as today's mascot.html).
6. **`midi/library/` (controller mappings)** — one file per supported controller (CC_MAP, NOTE_MAP, DECK_ASSIGNMENT); written from scratch using Pioneer/Hercules published MIDI charts, not copied from Mixxx (GPL infection risk on XML).
7. **`recording/` + `ui_bus/` + `calibration/`** — port recording from POC, new WS schemas, new wizard backend.

End-to-end latency: crossfader move → user hears AI reaction is **~800-1500ms** (Gemini Flash multimodal inference dominates). Local capture + state + event-detect overhead is <15ms; proxy hop adds ~80-150ms RTT; TTS first-byte arrives ~100-300ms after LLM first-token. Prompts must operate in past tense ("yo that mix you just did") — already documented in the POC system instruction.

### Critical Pitfalls

22 pitfalls catalogued total; 9 Critical, 7 High, 6 Medium. The top 5 by ship-blocking severity:

1. **AI slop in reactions (P1, existential)** — the *product* failure mode per PROJECT.md core value. AI says "great mix bro!" / "nice EQ adjustment!" — bland, ESL-tutor-cheerful, semantically empty. Prevention: surrounding-data prompting (raw RMS/bands/BPM numbers, never paraphrases like "energy rising"), persona anchored to specific vocabulary not adjectives (negative dictionary banning "amazing/awesome/great/let me know/delve/leverage"), per-session anti-repetition ring, silence as default, persona with *opinions* (not only praise). Hard pre-release gate: hand-graded reaction reel — 30 minutes of varied DJing blind-rated 1-5 by Kaan + 2-3 DJ friends, average ≥4.0 with zero 1-2 ratings, or no merge to main.

2. **Multimodal hallucination of musical events (P2)** — model says "loved that vocal sample" when there's no vocal; "into the breakdown" while still building. The other existential failure mode and the explicit hard gate in PROJECT.md Constraints. Prevention: send raw audio bytes (not descriptions), send evidence as raw numbers, force "describe before infer" anchoring, give the model permission to output `<silence/>`, run a 30-session offline verification suite with ≥95% grounded threshold before any installer build, never let the model OCR BPM off the screen JPEG.

3. **API key leakage from shipped binary (P3)** — anyone runs `strings vibemix.exe | grep AIza`, extracts the key, drains the Bravoh budget within hours. The PROJECT.md "API-key-protection problem of the year". Prevention: the binary **never** possesses the raw Gemini key. Period. FastAPI proxy on `api.altidus.world` + install-UUID JWT + per-IP slowapi rate limit + per-UUID Redis quota + no fallback path that uses a local key. Pre-release attack: `strings` / `pyinstxtractor` against the final binary, search for `AIza` and `^[A-Za-z0-9_-]{39}$` patterns — anything found blocks ship.

4. **Day-one installer broken on Windows or macOS (P6)** — Gatekeeper modal on un-notarized macOS apps, SmartScreen modal on unsigned Windows installers, PyInstaller `--onefile` triggering Defender false-positives. With paid IG ads driving traffic, day-one broken installer is the worst possible signal. Prevention: macOS — full notarization flow via `notarytool` (altool deprecated) + Hardened Runtime + correct entitlements + `Info.plist` permission strings; Windows — `--onedir` not `--onefile`, **SignPath Foundation OSS cert (apply NOW, takes 1-3 weeks)**, Defender pre-submission, sign every nested `.exe` and `.dll`. Test on fresh non-dev machines before launch.

5. **LiveKit session disconnects and dies silently mid-set (P9)** — RealtimeModel WebSocket drops 23 minutes in; session never reconnects; user keeps DJing, AI never speaks again. Many open LiveKit issues (#4609, #4135, #4676, #1679, #4414, #2274). Already mostly mitigated by PROJECT.md's decision to use Flash+TTS cascade (each turn is a fresh HTTP call, not a persistent WebSocket), but still need retry-with-backoff on transient errors, a 60s health-check heartbeat, a UI status pill on outage, and a 60-minute soak test as pre-release gate.

Additional Critical-severity items the roadmap must internalize:
- **P4 hardcoded device names** — current POC has `INPUT_DEVICE = "BlackHole 2ch"` as a module constant; crashes for every user that isn't Kaan. Calibration wizard + `~/.vibemix/config.json` is the answer.
- **P5 blocking work in sounddevice audio callback** — `np.concatenate` on a 4.5MB ring + FFT in callback causes dropouts; pre-allocated ring + move all features to `state_refresh_loop` at 10Hz.
- **P7 genre-calibrated heuristics that only work for one genre** — phase detector tuned for acid/techno at 150-160 BPM; house, D&B, disco, pop all break. Percentile-based normalization + per-genre profile JSON.
- **P8 cross-platform loopback churn** — BlackHole Sonoma sample-rate-halving bug (#524), WASAPI loopback alias quirks, Multi-Output Device ordering rules; sample-rate sanity test (1kHz tone round-trip) on every startup.

High-severity to track in roadmap planning: P10 TTS chunk boundary glitches (sentence buffering + 24kHz playback rate match), P11 MIDI hot-plug races + DDJ-FLX4 Windows USB recognition flakes, P12 mic feedback loop in speakers mode (hard-disable mic in speakers mode), P13 screen-capture privacy (mandatory window picker, never full-screen fallback), P14 license + CLA (Apache 2.0 + DCO, not MIT, for Bravoh's commercial-internal-use needs), P15 issue tsunami on launch day (templates + Discussions + second responder), P16 copyright on demo content (royalty-free music for marketing, no-lyrics rule in system prompt).

## Implications for Roadmap

Based on the four research files, the suggested phase structure is **7 phases over ~3-4 weeks**, organized so cross-platform foundation and the architectural pivot run early, Windows port parallelizes once protocols are pinned, MIDI library data-entry runs in parallel after the schema lands, and the final ~4-5 days are reserved for slop/hallucination verification + distribution-hardening rather than feature work.

### Phase 1: Foundation & Architectural Pivot
**Rationale:** Everything downstream depends on (a) the `platform/` protocol firewall existing so client code never imports OS-specific symbols, (b) the audio/state classes being ported from `cohost_v2.py` to the new package shape, and (c) the RealtimeModel → Flash+TTS cascade pivot landing so the brain is no longer the POC's brittle path. Three POC variants (`cohost.py`/`cohost_v2.py`/`cohost_lk.py`) get consolidated into one shipping `vibemix` package. Pre-allocated ring buffer (fix the `np.concatenate` audio-callback regression from CONCERNS.md) lands here.
**Delivers:** Unified `vibemix` Python package, `platform/` protocol surface, macOS audio I/O port, MusicState/EventDetector/AICoach port, `DJCoHostAgent(Agent)` with `llm_node` override, `AgentSession` wired with `google.beta.gemini_tts.TTS`, local bundled `livekit-server --dev` integration. End-to-end "macOS Kaan-machine" demo works.
**Addresses:** Live voice reaction to master output (P1 feature), absolute set-timeline awareness, audible-deck detection, magnitude-aware EQ events (FLX4 carry from POC), hallucination grounding via audio evidence packet.
**Avoids:** P5 (blocking audio callback) via pre-allocated ring, P9 (LiveKit disconnects) via cascade pattern over RealtimeModel, partial P2 (hallucination) via evidence-packet contract being locked here.

### Phase 2: API Proxy & Auth (parallel with Phase 1)
**Rationale:** The proxy is a hard architectural dependency, not a deployment afterthought — it must exist before any client-side Gemini code is built or you risk shipping with embedded keys. FastAPI on `api.altidus.world` reuses the Bravoh stack so this is two routes + Redis + JWT signing, not a new service. Server-side model name resolution here also defuses P18 (Gemini preview-model-name expiry).
**Delivers:** `POST /vibemix/v1/auth/token` (install-UUID JWT issue), `POST /vibemix/v1/gemini/generate-content` (multimodal pass-through, streaming SSE), `POST /vibemix/v1/gemini/tts` (chunked PCM pass-through), slowapi + Redis rate limit (60 rpm per UUID, 2000 rpd per UUID), `vibemix/proxy/` client module with OS-keychain JWT storage.
**Uses:** FastAPI 0.115+, slowapi 0.1.9+, Redis 7.x (Bravoh's existing), `keyring` 25.6.0 for Keychain/CredLocker JWT storage, `pyjwt` 2.10.1.
**Implements:** Proxy/auth component from ARCHITECTURE.md System Overview.
**Avoids:** P3 (API key leakage) — the entire pitfall; P18 (preview model name expiry) via server-side resolution.

### Phase 3: Sensing & Event Detection Hardening
**Rationale:** Genre-tuned phase thresholds (P7) and percentile-based normalization (P22 compression inflation) need to land before the prompting layer is finalized, because the AI's grounding context comes from these signals. Per-genre profile validation against recorded sets is the gate here.
**Delivers:** `genre_profiles.json` (techno/house/D&B/disco/pop with BPM range + drop_rms + build_dur_s + drop_sub_share per genre), percentile-based phase detector replacing absolute thresholds, crest-factor compression detection, BPM half/double validation window, vocal-section detection (hard etiquette gate), per-genre replay validation harness.
**Addresses:** Genre picker + genre-tuned thresholds, vocal-section gating, phase detection across all 5 v1 genres.
**Avoids:** P7 (single-genre calibration), P22 (compressed-master inflation).
**Implements:** `state/` and `state/events.py` from ARCHITECTURE.md.

### Phase 4: Cross-Platform Windows Port (parallel with Phase 3)
**Rationale:** Once `platform/` protocols are pinned in Phase 1, Windows implementations can run in parallel without blocking the macOS critical path. The Windows audio path (PyAudioWPatch WASAPI loopback) is a known-good replacement for sounddevice and avoids forcing users to install a virtual audio cable. macOS 15+ forward-compatibility (Quartz → ScreenCaptureKit migration) also lives here as a parallel macOS task.
**Delivers:** `platform/_audio_windows.py` (PyAudioWPatch), `platform/_screen_windows.py` (mss + pywin32 EnumWindows), `platform/_nowplaying_windows.py` (winsdk GSMTC — or defer to v1.1 if it's a time sink), `platform/_screen_macos.py` ScreenCaptureKit upgrade, sample-rate sanity tone-test infrastructure, calibration wizard backend (`calibration/` package).
**Uses:** PyAudioWPatch 0.2.12.8, mss 10.2.0, pywin32 308+, pyobjc-framework-ScreenCaptureKit 12.1.
**Implements:** OS-abstraction firewall for Windows + macOS-15-forward-compat.
**Avoids:** P4 (hardcoded device names — calibration wizard backend lands here), P8 (loopback library churn — sample-rate sanity test), P13 (screen privacy — mandatory window picker, no full-screen fallback).

### Phase 5: MIDI Controller Library (parallel with Phase 3 + 4)
**Rationale:** Data entry, parallel-friendly, can start any time after Phase 1's MIDI base lands. License-safe approach: use Mixxx XML as *reference* for MIDI message identity (CC numbers are uncopyrightable facts), write fresh mapping data in vibemix's own format. Per-controller magnitude-aware EQ mapping is the differentiation driver — Coach mode collapses without it.
**Delivers:** 10 controller mapping files (DDJ-FLX4 already carries from POC; DDJ-400, DDJ-FLX6, DDJ-FLX10, DDJ-1000, DDJ-SX3, XDJ-RX3, Numark Party Mix Live, Hercules Inpulse 300, Hercules Inpulse 500), generic MIDI fallback with positional inference, controller auto-detect + library matching, MIDI hot-plug re-enumeration (every 2s).
**Addresses:** Curated 10-controller mapping, generic MIDI fallback, magnitude-aware EQ/fader events.
**Avoids:** P11 (MIDI hot-plug + DDJ-FLX4 Windows USB flakes — documented in troubleshooting).

### Phase 6: Prompting, Persona & UX Shell
**Rationale:** The slop and hallucination work happens here, on top of the now-grounded evidence pipeline from Phase 3 and the controller-aware events from Phase 5. Calibration wizard UI (Tauri webview side), Settings UI, live session UI (mascot canvas + meters) all land here. The 6-cell skill-tier × interaction-mode prompt-template matrix lives here.
**Delivers:** 6 prompt templates (Beginner/Intermediate/Pro × Hype-man/Coach) with negative-dictionary anti-slop hard bans, per-session anti-repetition ring (`TurnHistory` port from cohost.py), `<silence/>` short-circuit, "describe-before-infer" anchoring, Coach scorecard at session end, voice picker (Gemini TTS 30 prebuilt voices), genre picker, push-to-mute hotkey, output destination picker, 3-step calibration wizard UI (window picker, output device, genre), live session UI in Tauri.
**Uses:** Tauri 2.x, React + Vite, Zustand, mascot canvas via WS bus.
**Addresses:** 3 skill modes × 2 interaction modes, voice picker, genre picker, calibration wizard, push-to-mute, vocal-section gating, reaction frequency throttle, mic gating.
**Avoids:** P1 (AI slop — the prompt engineering is the prevention), P10 (TTS chunk boundaries — sentence buffering lands here), P12 (mic feedback loop — speakers mode disables mic), P20 (heavy calibration wizard — max 3 questions).

### Phase 7: Verification, Distribution & Launch Readiness
**Rationale:** The two hard pre-release gates from PROJECT.md Constraints (hallucination grounding ≥95%, AI slop ≥4.0 with no 1-2 blind ratings) live here, alongside installer signing/notarization, the GitHub repo polish ("Maximum Sexification"), and launch-day operational readiness. SignPath Foundation OSS cert application must have been filed on day 1 of Phase 1 — it lands here.
**Delivers:** 30-session offline hallucination verification suite passing ≥95%, hand-graded reaction reel passing ≥4.0/5 with no 1-2 ratings, signed + notarized macOS DMG, SignPath-signed Windows MSI, GitHub repo with hero banner + demo GIF + install buttons + feature matrix + controller grid + screenshots + FAQ + Bravoh footer, CONTRIBUTING.md with DCO, SECURITY.md, NOTICE file, TRADEMARKS.md, Apache 2.0 LICENSE, issue templates (bug/feature/new-controller), second-responder rota for first 72h, 60-minute soak test passing zero `session_error` events, recording retention policy (7d default, settings UI), binary attack verification (`strings` + `pyinstxtractor` find zero `AIza`-pattern matches).
**Uses:** PyInstaller 6.20.0, create-dmg, Inno Setup 6, Apple Developer ID, SignPath Foundation, GitHub Actions matrix (macos-14 + windows-latest).
**Addresses:** One-click installer, hallucination grounding gate, AI slop gate, GitHub presence requirements, launch funnel preparation.
**Avoids:** P1 (slop — final gate), P2 (hallucination — final gate), P3 (key leak — final binary attack), P6 (installer broken on launch day — fresh-machine testing), P14 (license confusion — Apache 2.0 + DCO + NOTICE complete), P15 (issue tsunami — templates + Discussions + responder rota), P16 (copyright — marketing audit + no-lyrics rule), P21 (mascot leak — `VIBEMIX_DEV=1` flag gates the WS bus in release builds).

### Phase Ordering Rationale

- **Foundation before everything else** — Phase 1's `platform/` protocols and the cascade-pipeline pivot are gating dependencies; Windows port (4), genre tuning (3), MIDI library (5), UX (6) all assume these exist.
- **Proxy in parallel** — Phase 2 is independent infrastructure work on `api.altidus.world` that can be built and deployed while Phase 1 is in progress, so client integration in late Phase 1 has a working endpoint.
- **Parallel data + Windows tracks** — Phases 3, 4, 5 are independent enough to be assigned to different people once Phase 1 lands; this is the key to making the 3-4 week timeline.
- **Prompting late** — Phase 6 happens after the grounding pipeline (3) and controller events (5) are stable, because the prompt design depends on what evidence is reliably available.
- **Verification last, deliberately** — Phase 7 is not "polish week"; it's the gate week. The hand-graded reaction reel and the 30-session hallucination suite *cannot* be parallelized into earlier phases because they need the integrated end-to-end product. If gates fail, Phase 6 prompt-engineering loops, then Phase 7 re-runs.
- **SignPath application is a day-1 task that lands in Phase 7** — application takes 1-3 weeks; filing on roadmap day 1 makes approval coincide with installer-build time.

### Research Flags

Phases likely needing deeper research during planning (run `/gsd-research-phase` before kickoff):
- **Phase 1 (Foundation & Architectural Pivot):** Standard patterns are documented (LiveKit recipe "LLM Output Replacement" + PR #4189 for Gemini TTS streaming + `AgentSession` constructor shape), but the `Agent.llm_node` override consuming `chat_ctx.items[-1]` and the local `livekit-server --dev` bundling decision benefit from a focused-research pass on edge cases (mic-gate behavior via `AudioOutput` listener, sentence-boundary buffering in `google.TTS`).
- **Phase 3 (Sensing & Event Detection Hardening):** Percentile-based phase detection + crest-factor compression detection are research-grade DSP; need a focused-research pass on the algorithm + parameter choice before implementation. Per-genre validation harness design (what does the gold-standard event timeline for "house DJ doing a clean 8-bar transition" actually look like?) needs DJ-coaching domain input.
- **Phase 6 (Prompting, Persona & UX Shell):** The slop-avoidance prompt engineering is high-stakes and somewhat taste-bound; warrants a research pass on persona-anchoring patterns (specific vocabulary not adjectives), negative-dictionary maintenance across Gemini 3.x revisions, and the `<silence/>` short-circuit pattern. The Coach scorecard structure (qualitative bands, never numeric) also needs a small UX research pass.
- **Phase 7 (Verification, Distribution & Launch Readiness):** SignPath application logistics + Defender pre-submission flow + macOS Hardened Runtime entitlements specifics need a focused research pass close to actual launch — these are details that change quarterly. The hand-graded reaction reel grading rubric needs a deliberate design pass.

Phases with standard patterns (skip `/gsd-research-phase`, use what's in STACK.md / ARCHITECTURE.md):
- **Phase 2 (API Proxy & Auth):** FastAPI + slowapi + Redis + JWT is well-trodden territory; the threat model in PITFALLS.md P3 + ARCHITECTURE.md Pattern 5 is sufficient.
- **Phase 4 (Cross-Platform Windows Port):** PyAudioWPatch WASAPI loopback + mss + pywin32 + ScreenCaptureKit migration are documented in STACK.md with verified version pins and code snippets; the ScreenCaptureKit migration has a reference gist (mr-linch on GitHub).
- **Phase 5 (MIDI Controller Library):** Data entry from published Pioneer/Hercules MIDI charts; the FEATURES.md "Controller Mapping Availability" matrix is the playbook.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Every load-bearing version (livekit-agents 1.5.8, livekit-plugins-google 1.5.8, google-genai 2.0.1, PyAudioWPatch 0.2.12.8, pyobjc-framework-ScreenCaptureKit 12.1, PyInstaller 6.20.0) verified against PyPI + GitHub source. The `livekit-plugins-google.beta.gemini_tts.TTS` class signature and 30-voice list confirmed by reading the source directly. SignPath Foundation grant terms confirmed via cross-referenced developer community references (MEDIUM on the exact approval timeline — verify when filing). |
| Features | MEDIUM-HIGH | HIGH on existing-product landscape (djay Pro AI, VirtualDJ 2026, PulseDJ, BandLab AI surveyed directly), HIGH on controller mapping availability (Mixxx XML matrix confirmed), MEDIUM on user-mode psychology and anti-feature predictions (no shipping product like vibemix exists, so the 6-cell skill-tier × interaction-mode matrix is reasoned not observed; will need iteration in Phase 6). |
| Architecture | MEDIUM-HIGH | HIGH on LiveKit Agents internals (LLM Output Replacement recipe + PR #4189 + Agent class signatures confirmed), HIGH on cross-platform audio/MIDI split, HIGH on Gemini TTS streaming plugin, MEDIUM on LiveKit standalone-no-room option (documented but underdocumented edge case — recommendation is to bundle local `livekit-server --dev`, reasoned not benchmarked), MEDIUM on proxy security model details (multiple viable JWT-scope shapes; the recommended one is reasoned not adversarially tested). |
| Pitfalls | HIGH | Most pitfalls validated either against the existing POC's own CONCERNS.md, against named library issues (sounddevice #281, BlackHole #524, livekit/agents #4609 + #1679 + #4414, pyinstaller #6747, pyobjc #627), or against documented production failure modes (Apple notarization workflow, Microsoft Defender false-positive submission, SignPath Foundation OSS program). The prompt-design / "AI slop" pitfalls are MEDIUM because they are taste-bound rather than mechanically testable — the hand-graded reaction reel is the only honest gate. |

**Overall confidence:** HIGH on "we know how to build this" — the technical surface is mapped, the libraries are pinned, the architectural pivot is one constructor change. MEDIUM on "we know it will pass the slop gate" — that's the genuine product risk and the reason Phase 7's verification cycle is non-negotiable.

### Gaps to Address

- **Slop-avoidance prompt engineering effectiveness is unproven.** The negative dictionary, persona-vocabulary anchoring, and per-session anti-repetition patterns are best-guesses from voice-assistant UX research and chatbot-personality literature, not validated against real DJing sessions. Handle during planning: budget for 3-5 iteration cycles in Phase 6, with the hand-graded reaction reel as the truth signal. If the gate hasn't passed by day 18 of the 3-4 week timeline, scope-cut Coach mode v1 to "scorecard at session end only" (defer live Coach mid-mix) and ship Hype-man only — better narrow + good than wide + sloppy.

- **Per-genre phase-detector validation is sparse outside techno.** The POC's percentile-based + per-genre-profile approach is the right shape, but recordings of house/D&B/disco/pop sessions to validate against are not yet in hand. Handle during planning: collect ~30 minutes of recorded sets per genre during Phase 3, with Francesco's DJ network as the obvious source.

- **ScreenCaptureKit migration ergonomics under-tested.** Callback-based API with multiple nested `getShareableContentWithCompletionHandler` calls is heavier than `mss`. Reference gist exists but no shipping-quality Python wrapper. Handle during planning: 1-2 days budgeted in Phase 4; if it blocks, fall back to keeping Quartz `CGWindowList` for macOS 14 + ScreenCaptureKit only for macOS 15+, with a 2026 sunset plan.

- **`livekit-plugins-google.beta.gemini_tts.TTS` is in the `beta` namespace.** Production-readiness is implied but not guaranteed. Handle during planning: lock the version in `pyproject.toml`, add a smoke test in CI that the import + a 1-second synthesis succeeds, monitor PR #4189 follow-ups.

- **Windows `nowplaying` via winsdk GSMTC ergonomics unconfirmed.** WinRT bindings work but Python ergonomics are clunky. Handle during planning: explicit "defer to v1.1" decision in PROJECT.md; v1 Windows users get audible-deck detection + screen-OCR fallback but no track-title metadata. Acceptable degradation.

- **Audible-deck detection accuracy on non-FLX4 controllers.** The audible-deck detection from `cohost_v2.py` is tuned against MIDI events from one controller. Generalization to the 9 other curated controllers is reasoned but not measured. Handle during planning: per-controller validation pass during Phase 5.

- **SignPath Foundation approval is not guaranteed.** Application takes 1-3 weeks and OSS-qualification criteria are documented but case-dependent. Handle during planning: file the application **on day 1** of Phase 1; if rejected by Phase 6, fall back to Sectigo OV cert (~$277/yr) and accept the SmartScreen reputation-building cost; if neither works in time, ship unsigned with a documented SmartScreen-warning workaround and accept the day-one conversion hit, plan to re-release signed in v1.0.1 a week later.

## Sources

### Primary (HIGH confidence)
- `/Users/ozai/projects/dj-set-ai/.planning/research/STACK.md` — full stack with verified versions
- `/Users/ozai/projects/dj-set-ai/.planning/research/FEATURES.md` — feature landscape with competitor analysis
- `/Users/ozai/projects/dj-set-ai/.planning/research/ARCHITECTURE.md` — three-process layout + LiveKit cascade pattern + latency budget
- `/Users/ozai/projects/dj-set-ai/.planning/research/PITFALLS.md` — 22 pitfalls with phase mapping + recovery strategies
- `/Users/ozai/projects/dj-set-ai/.planning/PROJECT.md` — core value, requirements, constraints, key decisions
- `/Users/ozai/projects/dj-set-ai/.planning/codebase/CONCERNS.md` and `/ARCHITECTURE.md` — POC concerns mapped through PITFALLS.md
- [livekit-plugins-google source: `beta/gemini_tts.py`](https://github.com/livekit/agents/blob/main/livekit-plugins/livekit-plugins-google/livekit/plugins/google/beta/gemini_tts.py)
- [LiveKit recipe: LLM Output Replacement](https://docs.livekit.io/reference/recipes/replacing_llm_output/)
- [PR #4189: Gemini TTS streaming](https://github.com/livekit/agents/pull/4189)
- [pyobjc issue #627: Quartz CGWindowListCreateImageFromArray obsoleted on macOS 15](https://github.com/ronaldoussoren/pyobjc/issues/627)
- [python-sounddevice issue #281](https://github.com/spatialaudio/python-sounddevice/issues/281)
- [PyAudioWPatch](https://github.com/s0d3s/PyAudioWPatch)
- [Apple notarization workflow](https://developer.apple.com/documentation/security/customizing-the-notarization-workflow)
- [BlackHole sample-rate Issue #524](https://github.com/ExistentialAudio/BlackHole/issues/524)
- [PyInstaller SmartScreen Issue #6747](https://github.com/pyinstaller/pyinstaller/issues/6747)
- [LiveKit agents Issue #4609](https://github.com/livekit/agents/issues/4609)

### Secondary (MEDIUM confidence)
- [SignPath Foundation for OSS](https://signpath.org/foundation)
- [Tauri Embedding External Binaries (sidecar)](https://v2.tauri.app/develop/sidecar/)
- [Mixxx DDJ-FLX4 mapping XML](https://github.com/mixxxdj/mixxx/blob/main/res/controllers/Pioneer-DDJ-FLX4.midi.xml) — reference only, GPL-clean re-implementation in vibemix format
- [Hallucination of Multimodal LLMs: A Survey (arXiv 2404.18930)](https://arxiv.org/pdf/2404.18930)
- [NN/Group: Intelligent assistants have poor usability](https://www.nngroup.com/articles/intelligent-assistant-usability/)
- [Apache 2.0 license terms](https://www.apache.org/licenses/LICENSE-2.0) and [Developer Certificate of Origin](https://developercertificate.org/)

### Tertiary (LOW confidence)
- [Tauri vs Electron in 2026](https://blog.nishikanta.in/tauri-vs-electron-the-complete-developers-guide-2026)
- [Crossing the uncanny valley of conversational voice (HN thread)](https://news.ycombinator.com/item?id=43227881)
- WinRT GSMTC ergonomics — multiple community references, no single authoritative wrapper; verify in Phase 4

---
*Research completed: 2026-05-11*
*Ready for roadmap: yes*
