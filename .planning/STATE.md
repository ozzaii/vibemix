# vibemix — State

**Last updated:** 2026-05-11 (Phase 3 complete)

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

- **Phase:** 04 — LiveKit Cascade Agent Pivot (next).
- **Plan:** None active.
- **Status:** Phase 3 ✅ complete (wave commits `c923025` / `8106a16` / `9104052` / `8e04dfc`). Six v4 sensing/state primitives ported verbatim into `vibemix.state` and `vibemix.platform`: MusicState (22-field single source of truth + threading.Lock), Event + EventDetector (7-event taxonomy + MUSIC_PRESENCE anti-hallucination gate + DDJ-FLX4 maps byte-identical to v4), AICoach (static-method-only, `phase=` omitted per v4:1350-1351), state_refresh_loop (10Hz single writer, lock-protected), and three macOS backends satisfying Phase 1 Protocols (ScreenMacOS via mss+Quartz, MidiMacOS via mido daemon thread, TrackMacOS via nowplaying-cli subprocess). Pioneer DDJ-FLX4 play-state limitation reproduced verbatim from v4; Phase 9 fix docketed. macOS ScreenCaptureKit migration docketed for Phase 8. POC files untouched (v4 still runnable via run_v4.sh). Full suite 270 green.
- **Progress:** 3/20 phases complete.

```
[███                 ] 15% (3/20 phases)
```

---

## Performance Metrics

(Populated as phases complete.)

| Metric | Value |
|--------|-------|
| Phases complete | 3 / 20 |
| v1 requirements mapped | 128 / 128 |
| v1 requirements complete | 9 / 128 |
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

### Next Session

- Continue from Phase 4 (LiveKit Cascade Agent Pivot). Imports `from vibemix.state import MusicState, Event, EventDetector, AICoach, state_refresh_loop` and `from vibemix.platform import ScreenMacOS, MidiMacOS, TrackMacOS` directly — no scavenger hunt.
- Phase 4 wires `DJCoHostAgent.llm_node` override + AgentSession cascade (stt=None, vad=None, llm=google.LLM, tts=google.beta.gemini_tts.TTS), feeds `AICoach.build_prompt(event)` output into Gemini Flash multimodal, and produces the first true end-to-end audible smoke test.
- Kaan-side outstanding: SignPath OSS application (Phase 1 carry-forward). ~1 week SLA.

---

*State managed by gsd-roadmapper at 2026-05-11; updated by /gsd-autonomous on 2026-05-11 (Phase 3 complete).*
