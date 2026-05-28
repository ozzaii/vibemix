# Phase 97: Onboarding + Verbatim Tone Locks + Mode Picker — Context

**Gathered:** 2026-05-28
**Status:** Ready for planning
**Mode:** Smart discuss (auto-accepted per `/gsd-autonomous fully`)

<domain>
## Phase Boundary

P97 ships the **first-run onboarding** that lets a stranger open vibemix → pick Learn from a mode picker on the main window → first-launch MIDI probe detects their controller and announces it by name → user sees the verbatim opening dialog (L1.01 from P94) → advances seamlessly through L1.01.

Also lands: disclaimer copy in app footer + repo README (RENDER-08 from P91 deferred), Hercules Inpulse 300/300-MK2 detection (`§LEARN-MK2-DETECTION` KAAN-ACTION discharge), headphone device picker in the existing wizard (`§LEARN-AUDIO-ROUTING-WIZARD-DISCHARGE`), lesson progress list UI in Learn window.

**REQ-IDs:** RENDER-08, ONBOARD-01, ONBOARD-02, ONBOARD-03, ONBOARD-04, ONBOARD-05, ONBOARD-06, ONBOARD-07.

**Out of scope:**
- Hardware-free "Explore" mode for Course 1 → v9.1
- Per-controller MIDI self-test auto-fix → v9.x
- BlackHole/Multi-Output wizard discharge → KAAN-ACTION `§LEARN-AUDIO-ROUTING-WIZARD-DISCHARGE` doc (P97 ships the picker; advanced routing is doc-only)

</domain>

<decisions>
## Implementation Decisions

### Mode picker on main window (ONBOARD-01 + ONBOARD-02)

- **Extend `tauri/ui/src/session/state.ts`** with `mode: "cohost" | "learn" | "build" | "debrief"` enum.
- **Mode picker component**: 4-mode toggle on the main window. Adopts the rocker pattern (mirrors `tauri/ui/src/session/components/rocker.ts`).
- **Optimistic-repaint pattern** (CLAUDE.md rule): click handler flips `data-active` LOCALLY immediately → `ipc.session.set_mode` round-trip self-corrects. NO settling on the ipc.settings.state echo.
- **First-launch MIDI probe:** on app boot, the existing `mido.get_input_names()` + `midi/registry.find_mapping(port_name)` chain runs (already from P91); if known controller detected, render its SVG; if unknown, generic SVG + manual picker.
- **Announce by name:** the tutor speaks "I see your DDJ-FLX4 — let's go" (or matching controller name). This is the SECOND permitted "Let's go." exception (the first was L1.01).

### Hercules Inpulse 300 vs 300-MK2 detection (ONBOARD-03)

- **TWO profile files** ship: `src/vibemix/midi/profiles/hercules_inpulse_300.json` (existing) + NEW `hercules_inpulse_300_mk2.json`.
- **MIDI-signature probe**: pick by `iSerialNumber` per Pitfalls §P3 (DJUCED treats as different controllers).
- **Live-verify on real MK2 rides forward as `§LEARN-MK2-DETECTION` KAAN-ACTION** (P98 ear-pass).

### Headphone device picker in wizard (ONBOARD-04)

- **Extend the existing wizard** (`tauri/ui/src/wizard/`) with a headphone device picker row.
- User selects which output device hosts tutor exemplar playback (default = system output).
- Persists via `ipc.settings.set` envelope with `learn.headphone_device_index` (the field landed P93-03).
- Advanced BlackHole+Multi-Output Device routing → DOC-only at `docs/audio-routing.md`; ride forward as `§LEARN-AUDIO-ROUTING-WIZARD-DISCHARGE` KAAN-ACTION.

### Lesson progress list UI (ONBOARD-05 + ONBOARD-06)

- **New component** at `tauri/ui/src/learn/lesson/progress-list.ts`.
- Each lesson shows a dot: empty / in-progress / completed (color states from existing tokens).
- User can pick up where left off OR replay any completed lesson.
- Consumes `ipc.learn.progress_state` (already wired P92).
- Empty-state copy: "no controller? plug one in" (lowercase, tone-disciplined).
- Keyboard-nav for users browsing curriculum without hardware.

### Disclaimer copy (RENDER-08 + ONBOARD-07)

- **App footer copy:** *"Visual representation for instructional use. DDJ-FLX4, XDJ-RX3, etc. are trademarks of AlphaTheta / Pioneer DJ. Inpulse is a trademark of Hercules. Numark is a trademark of inMusic Brands. vibemix is not affiliated with or endorsed by these manufacturers."*
- **Repo README:** add a "Trademarks" section with the same text.
- **Test gate:** `tests/learn/test_disclaimer_present.py` — verifies disclaimer present in both surfaces.

### Schema-regex normalization follow-up (from P94-04)

- Optional opportunistic fix: rename CURRICULUM keys `L1.NN` → `L1.NN-<slug>` to match the runtime schema regex `^L[0-9]+\.[0-9]+-.+$`. Same rename in the fixture `lesson_id` fields.
- This unblocks strict-mode schema validation on `complete_lesson` envelopes.
- Can defer if scope-creeps; not blocking for ear-pass.

### Claude's Discretion

- Exact mode-picker visual treatment (pill rocker vs segmented control — UI-SPEC delegates).
- Exact wizard layout for the headphone picker row.
- Exact "Explore" mode deferral copy ("hardware-free mode coming in v9.1" or simpler).

</decisions>

<code_context>
## Existing Code Insights

### Reusable assets (shipped P91-P95)
- `tauri/ui/src/session/state.ts` — add `mode` enum
- `tauri/ui/src/session/components/rocker.ts` — pattern to mirror for mode picker
- `tauri/ui/src/wizard/controllers/` — existing controller profile dir
- `src/vibemix/midi/registry.py::find_mapping` — first-launch probe
- `src/vibemix/midi/profiles/hercules_inpulse_300.json` — existing; add MK2 sibling
- `src/vibemix/runtime/config_store.py` — `learn.headphone_device_index` persistence (P93)
- `src/vibemix/learn/transcripts/course_1_anatomy/01_welcome.json` — verbatim dialog precedent
- `tauri/ui/src/learn/learn-window.ts` — extend with lesson progress list mount

### Concurrent-session discipline
- Multiple SHARED file edits (`session/state.ts`, `wizard/`, README, etc.)
- Named-path commits only

</code_context>

<deferred>
## Deferred Ideas

- Live audit + rc1 smoke + Kaan ear-pass → P98
- BlackHole/Multi-Output routing wizard → KAAN-ACTION doc-only
- §LEARN-CURR-KEY-NORMALIZATION → can fold into P97 opportunistically OR defer

</deferred>
