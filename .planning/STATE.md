---
gsd_state_version: 1.0
milestone: v9.0
milestone_name: Lesson One
status: executing
last_updated: "2026-05-27T20:47:12.944Z"
last_activity: 2026-05-27 -- Plan 91-01 SHIPPED (IPC contract + Vite/Tauri scaffolding)
progress:
  total_phases: 14
  completed_phases: 0
  total_plans: 7
  completed_plans: 1
  percent: 14
---

# vibemix — State

## Current Position

Phase: 91 (Controller Renderer + MIDI Mirror) — EXECUTING
Plan: 2 of 7 (Plan 01 SHIPPED 2026-05-27, commits 905e1550 → de4808ce)
Status: Ready to execute
Last activity: 2026-05-27 — 91-01 SHIPPED: 2 ipc.learn.* envelopes + Vite/Tauri scaffolding; 6 tests fixed; 66 oneOf == 66 wrappers

## Milestone Reference

See: `.planning/PROJECT.md` § Current Milestone (updated 2026-05-27)
See: `.planning/ROADMAP.md` § v9.0 (just added 2026-05-27)
See: `.planning/REQUIREMENTS.md` (72 v9.0 REQ-IDs across 9 categories)
See: `.planning/research/SUMMARY.md` (locked 14-axis reconciliation)

**Goal:** Turn vibemix into the AI teaching module beginner DJs need. Three progressive courses (Anatomy / Transitions / Play Mode) driven by a real-time interactive vector visualization of the user's MIDI controller. Every lesson grounded — controls highlighted on the rendered controller, EQ bands demonstrated audibly via library-pulled exemplar tracks, Course-3 live coaching grounded on CueAnchor + phrase detection.

**Phase numbering:** continues from P88 (P89/P90 = direct wire-ins) → milestone runs **P91 → P98**.

## Phase Spine (P91-P98)

```
P91 (Controller Renderer + MIDI Mirror) ──┬──► P92 (Lesson Runtime + AI Highlight Contract)
                                          │         │
                                          └──► P93 (Exemplar Engine + [exemplar:] evidence) ──┐
                                                                                              │
   P92 ───► P94 (Course 1 Anatomy) ───► P95 (Course 2 Transitions) ◄──────────────────────────┘
                                                            │
                                                            └────► P96 (Course 3 Play Mode + tutor lens proactive)
                                                                              │
                                                                              └─► P97 (Onboarding + Tone Locks + Mode Picker)
                                                                                              │
                                                                                              └─► P98 (Live Audit + Ear-Pass + rc1 Regression Smoke)
```

`P91 ∥ P93` parallelizable. `P93` feeds cite-grounding for `P95` and `P96`.

## Active Sources

- `.planning/PROJECT.md` § Current Milestone — vision + constraints + invariants
- `.planning/ROADMAP.md` § v9.0 "Lesson One" — 8-phase plan + KAAN-ACTION queue
- `.planning/REQUIREMENTS.md` — 72 v9.0 REQ-IDs · 100% traceability
- `.planning/research/SUMMARY.md` — 14-axis reconciliation (locked)
- `.planning/research/{STACK,FEATURES,ARCHITECTURE,PITFALLS}.md` — depth sources
- `.planning/handoffs/2026-05-27-session-end.md` — concurrent rc1 ship work (parked, Kaan ear-pass)

## Pre-Milestone Direction (carried forward)

From Kaan's verbatim brief (2026-05-27):

- **Iconic opening dialog (verbatim-locked, byte-equality test in P94):**
  - user: "Hello vibemix, what are you?"
  - vibemix: "I'm the best DJ app in the world."
  - user: "If you are the best, then who the fuck am I?"
  - vibemix: "Oh bestie, don't worry. You know why? Because I'm the beginner module of vibemix. Let's go."
- **The teaching mechanic:** AI highlights a control on the rendered visualization of the user's MIDI controller → user touches the physical control → lesson advances. For EQ lessons, the AI plays a library track exemplifying that band so the user HEARS the change.
- **Three courses:** (1) Anatomy of a Deck (16 lessons), (2) Transitions (14 lessons), (3) Play Mode (6 lessons + proactive tutor lens) = 36 total.
- **Default-YES on every candidate feature** — fully-comprehensive curriculum.
- **All-opus agents · maximum effort · best-of-the-best UI · impeccable skills.**
- **Kaan will plug DJ set into computer for autonomous overnight testing** — full computer access for fuck-around-find-out.

## Anti-Creep Acid Test (v9.0, LOCKED)

> *"Does this phase deliver a working slice of the BEGINNER (level 1, all 10 mapped controllers, 36-lesson curriculum, library exemplar engine + packaged fallback, scripted curriculum with grounded AI interjections) module — WITHOUT adding a new AI provider, new ws port, new IPC envelope family beyond `learn.*`, new DSP library, new content beyond the 36 hand-authored lessons, or new community/multi-user feature surface? Does it NOT regress any of the 4 cardinal invariants or the rc1 bundle fix?"*

If a phase doesn't pass → defer to v9.x or Bravoh.

## Concurrent Work (other sessions)

3 Codex sessions active on `live-tuning-or-brain` — commit by named paths only, never `git add -A`. rc1 product-sweep open in this branch; v9.0 work additive (new `src/vibemix/learn/` subpackage, extends but does not modify existing engines).

## Hard Rules (carried)

- **Privacy** — all OZ/Hermes/LM-Studio off-limits paths (see CLAUDE.md) — Kaan's overnight autonomous run does NOT extend this permission. Per-turn permission still expires at turn end.
- **One-socket invariant (#4)** — every `learn.*` IPC envelope rides `127.0.0.1:8765` (pinned by `tests/learn/test_no_new_ws_port.py` in P92).
- **Single-writer (#1)** — `MusicState` write-locked to `state/refresh.py`. `LearnState` lives separately under `src/vibemix/learn/`, sole writer = `LearnRuntime` (pinned by `tests/learn/test_runtime_invariants.py` in P92).
- **Trust-the-audio (#3)** — Course 3 tutor narration grounded on `[cue:<anchor_id>]` evidence + bpm/phrase confidence gates; never invents upcoming structure. `tests/learn/test_no_speculative_phrase.py` AST gate lands in P96 BEFORE Gemini wiring.
- **Citation-grounding (#2)** — AI tutor claims about exemplar tracks resolve via `EvidenceRegistry` through NEW `[exemplar:<track_id>]` source (4-site mirror in P93); fabricated `[exemplar:bogus]` strips whole turn.
- **Apache-clean** — no AGPL/GPL deps (essentia excluded); stylized controller renders, not Pioneer faceplate art; Mixxx-precedent nominative fair use posture.
- **Honest green** — every learn-engine module offline-unit-testable; live-app verification HARD per `feedback_verify_live_app_not_just_tests` (cargo tauri dev + ui.log). rc1 standalone sidecar smoke MUST PASS unregressed (P98 gate).
- **AI-slop blocklist** — every lesson copy runs through `scripts/launch/check_no_ai_slop.py` + NEW `scripts/launch/check_no_tutor_slop.py` v2 blocklist (≥20 tutor-tic tokens) — both CI-gated (P94).
- **codegen:ipc** — MANDATORY after every `messages.schema.json` edit (ajv validator pre-compiled — per `feedback_schema_edit_needs_codegen_ipc`).

## v9.0 KAAN-ACTION Queue (parked, never faked)

**BLOCKING (must resolve before v9.0 public ship):**

- `§LEARN-LEGAL-DISCLAIMER` (P98 / AUDIT-03) — Francesco/lawyer sight-check on rendered controllers + disclaimer copy
- `§LEARN-EAR-COURSE-1` (P98 / AUDIT-01) — Kaan ear-pass on Course 1 (16 lessons) on real FLX4
- `§LEARN-EAR-COURSE-2` (P98 / AUDIT-01) — Kaan ear-pass on Course 2 (14 lessons) on real FLX4
- `§LEARN-EAR-COURSE-3` (P98 / AUDIT-01) — Kaan ear-pass on Course 3 (6 lessons) on real FLX4 mid-set
- `§LEARN-CUE-DECISION` (P96 ratify) — Course 3 proactive count-ins (needs `[cue:]`) OR retrospective-only? Default-YES = count-ins

**NON-BLOCKING (ride forward):**

- `§LEARN-CONTROLLER-EAR` — 9 non-FLX4 controllers live-verify (FLX4 = canonical golden)
- `§LEARN-AUDIO-ROUTING-WIZARD-DISCHARGE` — BlackHole/Multi-Output Device wizard for master+cue split
- `§LEARN-CLAP-FIRST-RUN-UX` — CLAP ONNX model first-run download UX
- `§LEARN-OVERNIGHT-DISCIPLINE` — One-page overnight-run handoff doc
- `§LEARN-LATENCY-CONTINGENCY` — If P91 measures >80 ms P95, Rust-direct `midir` amendment
- `§LEARN-MK2-DETECTION` — Hercules Inpulse 300 vs 300-MK2 live-verify
- `§LEARN-FIRMWARE-VARIANTS` — DDJ-FLX4 v1.07 variant detection
- `§LEARN-OFFLINE-TONE-PATH` — Codex tutor parity deferred to v9.x
- `§LEARN-LOCALIZATION-IT-TR` — en-only v9.0; v9.1 drops `tr.py`/`it.py`
- `§LEARN-PEDAGOGY-INSTRUCTOR-REVIEW` — 36-lesson ordering past beginner-track DJ instructor

## Carried-Forward KAAN-ACTION (from prior milestones)

- rc1 ear-pass + signed-release A/B/C decision (`.planning/handoffs/2026-05-27-session-end.md`)
- v8.2 UI-02 funded-key ear-pass (PROJECT.md)
- v8.0 §GH-BILLING / §SHIP-V4 / §V7-LIVE

## Next Action

```
/gsd:plan-phase 91
```

P91 = Controller Renderer + MIDI Mirror. Standalone-verifiable; NO lessons yet — Kaan ear-pass available the moment this lands.
