# vibemix — State

**Last updated:** 2026-05-11 (post-roadmap synthesis)

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

- **Phase:** None active (roadmap just created).
- **Plan:** None active.
- **Status:** Roadmap initialized — ready for `/gsd-plan-phase 1`.
- **Progress:** 0/20 phases complete.

```
[                    ] 0% (0/20 phases)
```

---

## Performance Metrics

(Populated as phases complete.)

| Metric | Value |
|--------|-------|
| Phases complete | 0 / 20 |
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

- 2026-05-11 — Roadmap created from PROJECT.md + REQUIREMENTS.md (128 v1 reqs) + research synthesis (SUMMARY/STACK/ARCHITECTURE/PITFALLS/FEATURES). 7 research-suggested phases sliced into 20 finer-granularity phases per Kaan's directive. 100% requirement coverage validated. SignPath OSS day-1 task encoded into Phase 1 success criteria.

### Next Session

- Run `/gsd-plan-phase 1` to plan Phase 1 (Platform Protocol Firewall).
- Kick off SignPath Foundation OSS application as part of Phase 1 work.

---

*State managed by gsd-roadmapper at 2026-05-11.*
