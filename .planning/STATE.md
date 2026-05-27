---
gsd_state_version: 1.0
milestone: v9.0
milestone_name: Lesson One
status: planning
last_updated: "2026-05-27T20:00:00+03:00"
last_activity: "2026-05-27 - milestone v9.0 'Lesson One' started; 4 opus research agents in flight; rc1 product-sweep blockers parked"
progress:
  mode: planning
  research: in_flight
  requirements: pending
  roadmap: pending
  phases_complete: 0
  phases_total: tbd
---

# vibemix — State

## Current Position

Phase: Not started (defining requirements via 4 parallel opus research agents)
Plan: —
Status: Research in flight — STACK / FEATURES / ARCHITECTURE / PITFALLS opus agents launched
Last activity: 2026-05-27 — Milestone v9.0 "Lesson One" started under `gsd-autonomous fully`

## Milestone Reference

See: .planning/PROJECT.md § Current Milestone (updated 2026-05-27)

**Goal:** Turn vibemix into the AI teaching module beginner DJs need. Three progressive courses (Anatomy / Transitions / Play Mode) driven by a real-time interactive vector visualization of the user's MIDI controller. Every lesson grounded — controls highlighted on the rendered controller, EQ bands demonstrated audibly via library-pulled exemplar tracks, Course-3 live coaching grounded on CueAnchor + phrase detection.

**Phase numbering:** continues from P88 (P89/P90 = direct wire-ins) → milestone starts at **P91**.

## Active Sources

- `.planning/PROJECT.md` § Current Milestone — vision + constraints + invariants
- `.planning/research/{STACK,FEATURES,ARCHITECTURE,PITFALLS}.md` — IN FLIGHT
- `.planning/research/SUMMARY.md` — TBD (synthesizer after 4 researchers complete)
- `.planning/REQUIREMENTS.md` — TBD
- `.planning/ROADMAP.md` — TBD
- `.planning/handoffs/2026-05-27-session-end.md` — concurrent rc1 ship work (parked, Kaan ear-pass)

## Pre-Milestone Direction

From Kaan's verbatim brief (2026-05-27):
- **Iconic opening dialog (verbatim-locked):**
  - user: "Hello vibemix, what are you?"
  - vibemix: "I'm the best DJ app in the world."
  - user: "If you are the best, then who the fuck am I?"
  - vibemix: "Oh bestie, don't worry. You know why? Because I'm the beginner module of vibemix. Let's go."
- **The teaching mechanic:** AI highlights a control on the rendered visualization of the user's MIDI controller → user touches the physical control → lesson advances. For EQ lessons, the AI plays a library track exemplifying that band so the user HEARS the change.
- **Three courses:** (1) Anatomy of a Deck, (2) Transitions, (3) Play Mode (live coaching alongside actual DJing).
- **Default-YES on every candidate feature** — fully-comprehensive curriculum.
- **All-opus agents · maximum effort · best-of-the-best UI · impeccable skills.**
- **Kaan will plug DJ set into computer for autonomous overnight testing** — full computer access for fuck-around-find-out.

## Concurrent Work (other sessions)

3 Codex sessions active on `live-tuning-or-brain` — commit by named paths only, never `git add -A`. rc1 product-sweep open in this branch; v9.0 work additive (new `src/vibemix/learn/` subpackage, extends but does not modify existing engines).

## Hard Rules (carried)

- Privacy: all OZ/Hermes/LM-Studio off-limits paths (see CLAUDE.md) — Kaan's overnight autonomous run does NOT extend this permission. Per-turn permission still expires at turn end.
- One-socket invariant: every `learn.*` IPC envelope rides `127.0.0.1:8765`.
- Single-writer: `MusicState` write-locked to `state/refresh.py`. `LearnState` lives separately under `src/vibemix/learn/`.
- Trust-the-audio: Course 3 grounded on CueAnchor + phrase detection; never invents upcoming structure.
- Citation-grounding: AI tutor claims about exemplar tracks resolve via `EvidenceRegistry`.
- Apache-clean: no AGPL/GPL deps (essentia excluded); stylized controller renders, not Pioneer faceplate art.
- Honest green: every learn-engine module offline-unit-testable; live-app verification HARD per `feedback_verify_live_app_not_just_tests` (cargo tauri dev + ui.log).
- AI-slop blocklist: every lesson copy runs through `scripts/launch/check_no_ai_slop.py`.

## Carried-Forward KAAN-ACTION

- rc1 ear-pass + signed-release A/B/C decision (`.planning/handoffs/2026-05-27-session-end.md`)
- v8.2 UI-02 funded-key ear-pass (PROJECT.md)
- v8.0 §GH-BILLING / §SHIP-V4 / §V7-LIVE
- v9.0 KAAN-ACTION will accrue (controller-renderer aesthetic sign-off · 3-course full-run ear-pass · per-controller hardware verification on the 10 SKUs · "bestie" tone calibration)
