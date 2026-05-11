# vibemix — State

**Last updated:** 2026-05-11 (Phase 1 complete)

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

- **Phase:** 02 — Audio Core Port + Ring Buffer Fix (next).
- **Plan:** None active.
- **Status:** Phase 1 ✅ complete (commit `2df2115`). Public repo live at `https://github.com/ozzaii/vibemix`. SignPath OSS submission pending Kaan-side (reCAPTCHA blocked autonomous submit).
- **Progress:** 1/20 phases complete.

```
[█                   ] 5% (1/20 phases)
```

---

## Performance Metrics

(Populated as phases complete.)

| Metric | Value |
|--------|-------|
| Phases complete | 1 / 20 |
| v1 requirements mapped | 128 / 128 |
| v1 requirements complete | 0 / 128 |
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

- 2026-05-11 — `/gsd-autonomous` kickoff. Phase 1 (Platform Protocol Firewall) shipped end-to-end: smart-discuss → research + pattern-mapping (parallel) → plan → plan-check PASS → execute (3 wave commits + Task 4.1 verification gate 10/10) → SUMMARY. Public repo live at `https://github.com/ozzaii/vibemix` (Apache 2.0, main branch, all Phase 1 commits pushed). Step A (gh repo create) done autonomously with Kaan's auth. Step B (SignPath form) blocked by reCAPTCHA — Kaan-side submission pending using `.planning/signpath-application.md` as field reference. Legacy `ozzaii/dj-set-ai` still public; cleanup needs `delete_repo` scope.

### Next Session

- Continue `/gsd-autonomous` from Phase 2 (Audio Core Port + Ring Buffer Fix).
- Pre-Phase-2 fact: Phase 2 implements `AudioBackend` Protocol from Phase 1 as `_audio_macos.py`. Pre-allocated ring buffers replace POC's `np.concatenate`-per-callback (CONCERNS.md / PITFALLS P5).
- Kaan-side outstanding: submit SignPath OSS application at https://signpath.org/apply using the prefilled checklist. ~1 week SLA. Approval unlocks Phase 18 (Windows MSI signing).

---

*State managed by gsd-roadmapper at 2026-05-11; updated by /gsd-autonomous on 2026-05-11 (Phase 1 complete).*
