# vibemix — Requirements

**Milestone:** v3.2 "Plug In And Play" — Real-Hardware Bring-Up → Public Ship
**Started:** 2026-05-20
**Mode:** `gsd-autonomous fully` (recommended grey-area answers + defer blockers to KAAN-ACTION; only privacy rule + destructive risk pause)

## Goal

Take vibemix from engineering-complete (v3.1) to a co-host Kaan plugs into his MacBook and plays full sets with — validated **live on real hardware** (audio + controller), both modes feeling like a real DJ friend in the ear, polished to peak, with the public release one button away once external signatures land.

This milestone is the first time the built app is **driven on real hardware in a real session**, not simulated. Claude has Mac access: read Tauri console + sidecar logs, simulate UI clicks, play music through the path, and (when plugged) ingest the DDJ-FLX4. Engineering closes everything that does not require an external signature; the signed publish is surfaced as KAAN-ACTION.

---

## v3.2 Requirements

### Real-Hardware Bring-Up (BRINGUP)

- [ ] **BRINGUP-01**: The Tauri app + Python sidecar launch on Kaan's actual MacBook and reach a live "listening" session with no crash on boot.
- [ ] **BRINGUP-02**: BlackHole routing is live end-to-end — master output reaches the co-host at 48 kHz and audio levels register in real time.
- [ ] **BRINGUP-03**: DDJ-FLX4 MIDI events are ingested live during a real session, with verified graceful fallback when the controller is unplugged.
- [ ] **BRINGUP-04**: Runtime errors surfaced in the Tauri console + sidecar logs during a real session are triaged and fixed — no unhandled exceptions across a full-set run.
- [ ] **BRINGUP-05**: A ≥30-minute real session runs without dropout, hang, or unbounded memory growth.

### Live-Session Validation (LIVE)

- [ ] **LIVE-01**: Hype (party) mode produces grounded, in-time, non-slop reactions on real audio across ≥2 genres.
- [ ] **LIVE-02**: Feedback (coach) mode produces grounded, in-time, non-slop reactions on real audio across ≥2 genres.
- [ ] **LIVE-03**: Event cooldowns + reaction latency are tuned live so reactions land in-bar, not after the moment passes.
- [ ] **LIVE-04**: The EvidenceRegistry citation strip reflects real session events live — zero orphaned or hallucinated citations.
- [ ] **LIVE-05**: The reactive mascot (Neon Rebel) responds correctly to live audio/MIDI events in-session.

### Peak Performance (PERF)

- [ ] **PERF-01**: TTFT (trigger → first audio out) is measured on real hardware and meets the live-path latency budget.
- [ ] **PERF-02**: No audio glitches/dropouts in the playback path under real-session load.
- [ ] **PERF-03**: Mascot + UI hold 60fps on the integrated-GPU MacBook during a live session.

### Sexify Finish / Polish (POLISH)

- [ ] **POLISH-01**: Tier-1 live surfaces (session view, mascot overlay) get a final visual pass — zero HIGH findings, CDJ Whisper consistency held.
- [ ] **POLISH-02**: v0.1.0-rc1 carryover bugs closed — Tauri drag capability, mascot chrome strip, TCC list-population.
- [ ] **POLISH-03**: Fresh-account first-run → first-session flow is friction-checked and tightened.

### Ship (RELEASE)

- [ ] **REL-01**: All engineering-side release gates pass on real artifacts — `cut_release.sh` 6-gate pre-flight + Gate 2b (hallucination) + Gate 6b (e2e report) green.
- [ ] **REL-02**: §E2E-50A-WALK discharged by driving the real app end-to-end; walk artifact recorded.
- [ ] **REL-03**: External-clock items (Apple Dev Agreement, SignPath OSS cert) surfaced as KAAN-ACTION with the exact one-button SHIP-CUT sequence documented and pre-verified.

---

## Future Requirements (deferred — next milestone)

- **Vibe Mix prep module** — natural-language set creation, 3-track calibration, harmonic arc ordering, auto hot-cue write-back (spiked under `spikes/vibe_mix_slice*/`, 53 tests green). This is a **separate commercial BRAVOH product**, not the OSS live co-host. Graduates to its own milestone after the co-host ships. Do not fold into v3.2.
- **Mixxx OSC adapter + controller-map transpiler** (10 → 30+ controllers) — v3.x candidate per `project_v2_open_candidates`.
- **pyrekordbox integration depth, post-session debrief multi-session arc, library coach drill packs** — v3.x candidates.
- **§VIS-04 / §VIS-05 Mixamo retargets** — real GLB land; independent asset-discharge, parallel to ship.

## Out of Scope (this milestone)

- **The signed public binary publish itself** — gated on Apple Dev Agreement (Francesco) + SignPath OSS cert (~1wk SLA). Surfaced as KAAN-ACTION; engineering makes it one-button.
- **Vibe Mix prep module graduation** — separate product, separate milestone (see Future).
- **New AI/domain features** — this is bring-up + validation + polish + ship of what is already built. No new providers, no new detectors, no scope creep (`feedback_no_scope_creep_clean_utility`).
- **Full 30-session replay harness / LLM scorer** — hallucination gate is satisfied by Kaan's DJ ear + the autonomous proxy (`project_phase_16_kaan_dj_testing`).

## Traceability

| REQ-ID | Phase | Status |
|--------|-------|--------|
| _(filled by roadmap)_ | | |
