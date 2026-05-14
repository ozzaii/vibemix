# Phase 22: Mascot Anticipation Layer + Beat-Coupled Hip-Bob - Context

**Gathered:** 2026-05-14
**Status:** Ready for planning
**Mode:** Auto-generated (gsd-autonomous fully — auto-accepted recommended decisions)

<domain>
## Phase Boundary

The mascot leans forward 400-1200ms BEFORE Gemini voice arrives — masks perceived latency, sells AI as predictive not reactive. Beat B of the 30s viral demo (Phase 26). 4-layer additive animation simplified subset (mood + anticipation + speak/react) with full effect layer deferred to v2.1. 5 new `prep_*` GLB clips authored with idle-zero lower-body delta. Procedural hip-bob bone-driven by `MusicState.bpm + beat_phase`.

**Critical scope boundary:** Wave 0 day-1 spike gates inline emote-tag direction. Per STATE: 1-day Gemini text-channel ordering spike — does the text channel arrive BEFORE TTS audio chunks via `livekit-plugins-google`? If verified, ships path for v2.1 inline emote-tag vocab. If NOT verified, fall back to event-detector-driven anticipation only (no inline tags). Anticipation timeout = 2.5s + cancel-aware + linter-strip-aware crossfades ALL ship Wave 1 (Pitfall 9 — NOT v2.x polish).

</domain>

<decisions>
## Implementation Decisions

### Animation Layer Architecture (LOCKED — per STATE + ROADMAP success criteria)
- 4-layer additive simplified subset: mood + anticipation + speak/react. Full effect layer DEFERRED to v2.1.
- Wired via `AnimationUtils.makeClipAdditive` (Three.js stdlib).
- Single mascot rig per memory `project_mascot_as_vtuber_personality_surface` — placeholder "DJ bat", mood variation on the SAME rig.

### Anticipation Timing (LOCKED — per Pitfall 9 + STATE)
- Anticipation fires at T+50ms from `EventDetector.detect()` return — visible BEFORE Gemini round-trip on synthetic test.
- 5 new `prep_*` GLB clips authored: idle-zero lower-body delta (additive layer, doesn't fight hip-bob).
- 2.5s anticipation timeout — on Gemini misfire, crossfade `prep_*` → `prep_settle` (NOT snap-back-to-idle, that's the Pitfall 9 failure mode).
- Cancel-aware crossfade fires when Phase 19's `SpeechHandle.interrupt(force=True)` fires.
- Linter-strip-aware crossfade fires when Phase 20 total-strip + ack-only fallback triggers.
- ALL three crossfade scenarios ship Wave 1 (Pitfall 9 mandate — NOT v2.x polish per STATE locked decision).

### Hip-Bob Procedural (LOCKED — per success criteria + Pitfall 20)
- `Hips` bone Y-offset weighted by RMS (from `Levels` bus).
- Locked to `MusicState.bpm + beat_phase` (Phase 17 deliverable).
- Phase-locked >150 BPM (techno/Hard Tek): tight to beat grid.
- Amplitude-driven <130 BPM (house): smoother RMS-following.
- Re-syncs on EVERY downbeat detection (Pitfall 20 — BPM phase drift mitigation).

### Wave 0 Gemini Text-Ordering Spike (LOCKED — per STATE + Pitfall 21)
- 1-day spike, Day-1 of phase: instrument `livekit-plugins-google` to log text emission timestamps vs TTS audio chunk arrival.
- Verified-ordering outcome: design v2.1 inline emote-tag vocab (`<lean_in/>`, `<surprise/>`, etc.).
- Unverified outcome: anticipation stays event-detector-driven only; no inline tags in v2.0 OR v2.1.
- Spike output: `.planning/phases/22-.../WAVE-0-SPIKE.md` with verdict.

### Performance Gates (LOCKED — per success criteria + Pitfall 19, 23)
- Three.js renderer p99 frame budget ≤22ms verified via vitest perf test on 60-event burst (Pitfall 19 — crossfade discontinuity prevention).
- GLB clip TOTAL budget ≤15MB asserted in CI gate (Pitfall 23 — fail build on bloat).
- Bundle stays under 350MB hard cap (STATE.md decision).

### Asset Pipeline (Claude's Discretion within constraint)
- 5 prep_* GLB clips authored externally (Mixamo + manual delta-zero on lower body).
- Clip authoring brief lives at `.planning/phases/22-.../ASSETS.md` — references existing rig in `tauri/ui/public/mascot/`.
- Mascot color palette ties to CDJ Whisper amber per `project_visual_direction_cdj_whisper`.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tauri/ui/src/mascot/renderer.tsx` — Phase 13 single-layer mascot renderer; extends to 4-layer additive.
- `tauri/ui/public/mascot/dj_bat.glb` — placeholder rig (per memory `project_mascot_as_vtuber_personality_surface`).
- Phase 19's `SpeechHandle.interrupt(force=True)` wrapper — cancel-aware crossfade subscriber.
- Phase 20's `[unverified]` linter-strip telemetry — linter-strip-aware crossfade subscriber.
- Phase 17's `MusicState.beat_phase` + `active_genre` — hip-bob phase locking + per-genre tuning.

### Established Patterns
- IPC bus over WebSocket `127.0.0.1:8765` (mascot path); event push from sidecar to mascot is established.
- Three.js renderer + Canvas2D fallback (already shipped in Phase 13).
- `ipc.mascot.*` schema namespace (extend with `ipc.mascot.anticipate`, `ipc.mascot.crossfade`).

### Integration Points
- `EventDetector.detect()` consumer side — emits `ipc.mascot.anticipate` BEFORE `session.generate_reply()` is called.
- Phase 19 `runtime/cancel.py` — fires cancel signal that mascot subscribes to.
- Phase 20 `coach/citation_linter.py` — fires strip signal that mascot subscribes to.
- vitest perf test in `tauri/ui/tests/mascot/perf.test.ts`.

</code_context>

<specifics>
## Specific Ideas

- Wave 0 (Day-1, 1 day): Gemini text-channel ordering spike → WAVE-0-SPIKE.md verdict.
- Wave 1: 4-layer additive scaffold + prep_* GLB clip integration + anticipation T+50ms fire path.
- Wave 2: 2.5s timeout + cancel-aware + linter-strip-aware crossfades (Pitfall 9 bundled ship).
- Wave 3: procedural hip-bob bone driver + downbeat re-sync.
- Wave 4: vitest perf test (60-event burst, p99 ≤22ms) + GLB CI size gate (≤15MB).

</specifics>

<deferred>
## Deferred Ideas

- 4th effect layer (full effect layer deferred to v2.1 per STATE locked decision).
- Inline emote-tag vocab (v2.1 IF Wave 0 spike verifies text-before-audio ordering; ELSE indefinite).
- Multi-mascot or user-uploaded `/hatch` mascots (v2.x stretch per memory `project_mascot_as_vtuber_personality_surface`).
- Lip-sync to Gemini TTS audio (v2.1 — phoneme extraction not in v2.0 scope).
- Mood expression tied to AICoach prompt sentiment (v2.1).
- Procedural eye gaze tracking (v2.x).
</deferred>

---

*Phase: 22-mascot-anticipation-layer-beat-coupled-hip-bob*
*Context gathered: 2026-05-14 (smart discuss, fully autonomous)*
