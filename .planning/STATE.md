---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: prompt-only)
status: completed
last_updated: "2026-05-14T03:30:00.000Z"
last_activity: 2026-05-14 -- Phase 18 Plan 04 complete (citation_count telemetry shipped → Phase 18 fully shipped)
progress:
  total_phases: 12
  completed_phases: 2
  total_plans: 21
  completed_plans: 13
  percent: 62
---

# vibemix — State

**Last updated:** 2026-05-14 (Milestone v2.0 roadmap generated — 12 phases P15–P26 derived from 94 v2.0 REQ-IDs anchored to research/SUMMARY.md 12-phase decomposition; Phase 14 ✅ shipped 2026-05-13; outstanding v0.1.0 work absorbed into v2.0)

---

## Project Reference

- **Project:** vibemix — open-source AI DJ co-host (Bravoh's first OSS release)
- **Core value:** "Real DJ friend in your ear" — never hallucinating, never breaking flow, never AI slop.
- **Current focus:** Phase 15 — Recording Browser + Retention Enforcement (entry phase for v2.0).
- **Milestone:** v2.0 Research-Driven Ship — target ship ~3-4 weeks (~early June 2026, before Bravoh public launch).
- **Project mode:** standard.
- **Granularity:** fine (12 phases for v2.0).
- **Model profile:** quality (all agents on Opus, all checkpoints on).

---

## Current Position

Phase: 18 — COMPLETE (all 4 plans shipped)
Plan: Not started
Status: Phase 18 complete — prompt-only seeding loop closed end-to-end (registry → corpus footer → grammar block → telemetry). ROADMAP success #4 closed.
Last activity: 2026-05-14 -- Phase 18 Plan 04 complete (citation_count telemetry shipped)

## Performance Metrics

| Metric | Value |
|--------|-------|
| Phases complete (v0.1.0) | 14 / 14 |
| Phases complete (v2.0) | 0 / 12 |
| v2.0 REQ-IDs mapped | 94 / 94 ✓ |
| v2.0 REQ-IDs complete | 0 / 94 |
| Critical pitfalls (v2.0) mitigated in plan | 9 / 9 (encoded in phase plans; verification at execute time) |
| Hallucination verification (Kaan's DJ ear) | Phase 16 — Not yet measured |
| Hero asset shipped (architecture SVG + hero PNG) | ✅ (Phase 19 absorbed; commit 137200b + 4d20511) |
| AIza scan zero matches | ✅ 0 / 482 files (Phase 11 W1) |

---

## Accumulated Context

### Decisions Locked (v0.1.0 carry-forward — see prior STATE.md history)

All Phase 1–14 decisions remain locked. Highlights for v2.0 plan-checker:

- **Brain swap**: `AgentSession` cascade (`stt=None`, `vad=None`, `llm=google.LLM`, `tts=google.beta.gemini_tts.TTS`). Native Audio path stays in repo as opt-in.
- **3-process architecture**: Tauri Rust shell + Python sidecar (PyInstaller `--onedir`) + FastAPI proxy on `api.altidus.world`. **v2.0 adds ZERO new processes** — debrief = sidecar `--debrief` flag, overlay = second Tauri WebviewWindow.
- **Bundle ID `world.bravoh.vibemix`** LOCKED — TCC permissions break on any change.
- **No pydantic in `src/vibemix/ui_bus/`** — hand-written `@dataclass(frozen=True, slots=True)` + jsonschema Draft-07.
- **POC files (`cohost_v4.py`, `cohost_lk.py`, `cohost_v2.py`, `cohost.py`, `mascot.html`) UNTOUCHED** across every phase — reference port-from only.
- **AIza leak gate** at build time, 0 matches. v2.0 new bundled assets (ack-bank OPUS, sqlite-vec/numpy, GLBs, controller JSONs) re-scan; must stay 0.
- **macOS 12.3+ / Windows 10/11**. Linux excluded.
- **Apache 2.0 + DCO** license; signing via Apple Developer ID + SignPath OSS (filed Day-1 of P21).

### Decisions Locked (v2.0 — new this milestone)

- **Phase numbering CONTINUES from v0.1.0.** Phase 14 closed 2026-05-13; v2.0 starts at Phase 15.
- **Outstanding v0.1.0 work absorbed into v2.0** — recording browser (P15), Apple Developer ID sign + notarize + DMG + SignPath MSI + GitHub release matrix (P21), README full rewrite + Day-Zero ops + viral demo (P26). v0.1.0 milestone closes-by-absorption, not by separate ship.
- **12-phase decomposition P15-P26** with two parallel bundles (P17||P18, P22||P23). Critical-path total ~10-12 weeks engineering, binary shippable from P21 close.
- **P21 = ship gate.** Phases after P21 cuttable to v2.0.1 if Bravoh-launch timeline slips. Cut order documented in ROADMAP.md notes.
- **Phase 16 = Kaan's DJ ear, NOT formal 30-session eval suite** (per memory `project_phase_16_kaan_dj_testing`). Calendar-blocking, runs ALONGSIDE P17–P20 as those phases ship features.
- **Debrief in v2.0 = architectural slot ONLY** (sidecar `--debrief` flag + port 8766 + 3 IPC schema reservations). Full UI feature deferred to v2.1.
- **Event detector count = 6 baseline** in P17 v2.0 (per PROJECT.md). 2 Hard Tek overlay (`DISTORTION_CLIMB`, `ACID_LINE_ENTRY`) deferred to v2.1.
- **5 new pip deps** for v2.0 (per STACK.md): `pyrekordbox==0.4.4`, `sqlite-vec==0.1.9` (Mac/Linux only, Win numpy fallback), `pydub==0.25.1`, `mutagen==1.47.0`, `watchdog==6.0.0`. 0 new Rust crates. 0 new npm packages. Bundle stays under 350 MB hard cap.
- **AX from Rust parent, NEVER from Python sidecar** (Tauri #8329). Codebase grep gate in P24 fails CI on AX-from-sidecar.
- **Cancel-and-refire CAPPED**: `CANCEL_COOLDOWN_S = 8.0` hard + 30 cancels per session soft. Auto-disable on cap breach. Mandatory in P19, not v2.x follow-up.
- **Citation linter telemetry guard**: `stripped_rate_15s > 0.4` triggers next-response bypass. Mandatory in P20, shipped Wave 1.
- **Mascot anticipation timeout = 2.5s** + cancel-aware + linter-strip-aware crossfades. Mandatory in P22, shipped Wave 1.
- **Wave 0 day-1 spikes reserved**: P22 (Gemini text-channel ordering), P24 (AX-from-Rust-parent on signed bundle), P25 (`pyrekordbox` SQLCipher dep tree).
- **Apple Issuer ID**: `3f60cc6b-df70-4ff8-9ceb-865dac6c1b4b` supplied 2026-05-14. **Apple Developer Program Agreement update outstanding — Francesco-action-required** (flagged in P21 plan).
- **Predictive drop firing OFF-by-default in v2.0** (per memory `feedback_no_scope_creep_clean_utility`). Telemetry guard pre-wired for v2.1 turn-on after Phase 16 ear-test baseline.

### Open To-dos

- **Schedule Kaan's DJ-set ear-test sessions** to land BEFORE P22/P24 dependencies on Phase 16 tuning signal — calendar-blocking.
- **File SignPath Foundation OSS application** on Day-1 of P21 (lead time ~1 week). Re-verify status if v0.1.0 Phase 1 application already filed.
- **Resolve Apple Developer Program Agreement update** — Francesco-action-required surface in P21 plan.
- **DDJ-FLX4 Sync note 5-min mido sniff** (0x60 vs 0x58) — needs Kaan + hardware; first task of P23.
- **Collect Hard Tek + 9 SKU reference tracks** for P17 detector tuning harness. Hard Tek 7-10 anchor tracks especially — Kaan-owned.
- **Bravoh ops endpoint deployment**: `api.altidus.world/vibemix/updates/upload` (P21) + `api.altidus.world/healthz` (P26). Both Bravoh-team carry-forwards.
- **Discord server setup** Day-1 of P26 (Pitfall 34 mitigation — roles + channels + bot deferred to v2.1).
- **30-day staleness nudge UX copy** for P25 Pyrekordbox import (Pitfall 15) — surfaces "Looks like you've added new tracks — re-import to keep me grounded."

### Blockers

- **Apple Developer Program Agreement update** — Francesco-action-required. Does NOT block roadmap creation, but DOES block P21 sign step.
- **SignPath OSS approval status** unknown — needs verification before P21 entry gate. Assumed re-file required Day-1 of P21.

### Risks (v2.0 — carried from PITFALLS.md, 41 total)

- **Critical (9 pitfalls)**: P1 cancel-budget blowout (P19 mitigation), P2 linter silence streak (P20 mitigation), P3 AX-from-sidecar (P24 grep gate), P4 fullscreen Spaces (P24 toast), P5 Apple Issuer ID (P21 Kaan-action), P6 SignPath OSS SLA (P21 Day-1 file), P7 updater secret-name (P21 audit), P8 ack rotation collision (P19 deque), P9 mascot anticipation misfire (P22 crossfades).
- **High (9 pitfalls)**: P10 predictive misfire rate, P11 cache 1024-token floor, P12 linter registry race, P13 multi-monitor Y-flip, P14 Windows DPI, P15 Pyrekordbox staleness, P16 track title fuzzy collision, P17 stapler missing, P18 citation timestamp tolerance.
- **Medium/Low (23 pitfalls)**: P19-P41 documented in PITFALLS.md with phase mapping. P41 (Bravoh launch overlap slip) is roadmap-level — weekly slip review baked into milestone close gate.

---

## Session Continuity

### Last Session

- 2026-05-13 — Phase 14 (CDJ Whisper v5 Migration + Polish) ✅ shipped end-to-end. Backward-compat shim deleted; Saira + JetBrains Mono vendored; legacy fonts removed; all four surfaces (wizard, session, settings, mascot) consume v5 primitives directly. POLISH-01/02/04/06 closed; POLISH-03 closed in 14-05; POLISH-05 perf verification on Kaan rig deferred to `npm run tauri dev` review session.
- 2026-05-14 — Milestone v2.0 roadmap generated. 12 phases P15-P26 derived from 94 v2.0 REQ-IDs anchored to research/SUMMARY.md 12-phase decomposition. Outstanding v0.1.0 work absorbed into v2.0 (recording browser → P15, sign+release → P21, README + Day-Zero ops + viral demo → P26). All 9 Critical pitfalls encoded into phase plans (P1 → P19, P2 → P20, P3 → P24, P4 → P24, P5 → P21, P6 → P21, P7 → P21, P8 → P19, P9 → P22). Two parallel bundles (P17||P18, P22||P23). Critical-path total ~10-12 weeks engineering, binary shippable from P21 close. Cross-document contradictions reconciled (debrief = architectural slot only in v2.0; 6 baseline detectors in v2.0, 2 Hard Tek overlay deferred to v2.1). Wave 0 day-1 spikes reserved in P22 / P24 / P25 plan files.

### Next Session

- Run `/gsd-plan-phase 15` to plan Phase 15 — Recording Browser + Retention Enforcement (REC-07, REC-08). Cheap, no upstream dependencies — knock it out first.
- Schedule Kaan's first DJ-set ear-test session to land alongside P17/P18 ship — Phase 16 is calendar-blocking on tuning signal.
- Optional pre-P21: re-verify SignPath OSS application status (file Day-1 of P21 if not approved).
- Kaan-side outstanding (Phase 14 deferred): (a) `npm run tauri dev` visual review of all four CDJ Whisper v5 surfaces; (b) performance toggle persistence rehearsal; (c) macOS prefers-reduced-motion rehearsal; (d) Windows transparency rehearsal (deferred to Phase 26 fresh-VM).

---

*State managed by gsd-roadmapper at 2026-05-11; updated by gsd-roadmapper on 2026-05-14 (milestone v2.0 roadmap generated — 12 phases P15-P26; Phase 15 entry ready).*
