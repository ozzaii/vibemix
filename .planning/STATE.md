---
gsd_state_version: 1.0
milestone: v9.0
milestone_name: Lesson One
status: verifying
last_updated: "2026-05-28T04:02:06.853Z"
last_activity: 2026-05-28
progress:
  total_phases: 14
  completed_phases: 2
  total_plans: 20
  completed_plans: 15
  percent: 14
---

# vibemix — State

## Current Position

Phase: 92 (Lesson Runtime + AI Highlight Contract) — EXECUTING
Plan: 7 of 7 (92-01 SHIPPED — commits 2214911f → 3020dfba → 56c3a0be → fcdda017 on 2026-05-28 — python-statemachine ^3.1.2 dep + learn_tutor router path + 11 ipc.learn.* envelope schemas + regenerated ajv validator + 11 Python wrapper dataclasses with shared _VALIDATOR + 24 ui_bus re-exports + hardened count-parity heuristic across 5 test files at 77/77; foundation wave for the entire v9.0 lesson runtime. 92-02 SHIPPED — commits eb95b43e → 7722a403 → dd6dd43c on 2026-05-28 — 18 new test files: 5 Python AST + invariant stubs (LESSON-01 / TONE-02 / TONE-04), 5 Python wiring + parity tests (LESSON-02 / 03 / 05 / 06 + Pitfall 6 cadence), 8 TS test scaffolds (RENDER-04 ≤16ms paint, 5 a11y Playwright stubs, settings drawer, mascot regression). 3 AST gates LIVE day-one; 11-envelope round-trip parity at 13 Learn $refs LIVE; learn_tutor route LIVE; 6 module-level skips name Plan 92-03/04 dependencies. 92-03 SHIPPED — commits 7144fd2f (Task 1: LearnState + curriculum.py + prompts.py + JSON fixture; 7 tests flipped skip→PASS) → 3838e1d9 (Task 2: LessonRuntime FSM 8 states/5 transitions/1 Hz tick_loop/575 lines; 7 more tests flipped skip→PASS) → 66b50397 (docstring grep-gate fix) on 2026-05-28 — the Python brain of P92: LessonRuntime as sole writer of LearnState (Invariant #1 binding via AST gate), 4-forbidden-moves tutor lock LAST for recency (TONE-04), hand-authored JSON fixture as sole source of tutor_speak.text (TONE-02). All 22 tests/learn/ pass; 1 skip (test_progress_persistence.py awaits 92-04). P91 verification complete — all 7 P91 plans SHIPPED with commits da2aa70c → e85fae9d. 92-04 SHIPPED — commits 2971d4dc (Task 1: atomic progress.py with corruption recovery, mirror of config_store.save() os.replace pattern, 5/6 tests pass) → f3a687f9 (Task 2: vibemix learn reset CLI subcommand wired into cli_entry mirroring library/bench precedent, 6/6 tests pass) → 419997cb (Task 3: LessonRuntime wired into __main__.main() alongside MidiMirror via _LessonRuntimeIpcAdapter sync→async bridge + 1 Hz lesson_tick_task, 30 Hz cadence test flipped RED→GREEN via duration discriminator fix). Live boot now shows BOTH `-> midi_mirror wired` AND `-> lesson_runtime wired`; 283/283 pass across tests/learn/ + tests/runtime/. Plan 92-04 closes LESSON-03. 92-05 SHIPPED — commits dc969092 (Task 1: applyHighlight + clearHighlight + setHighlightHintIntensity exports on controller-stage.ts with single-active invariant + ZERO-new-token additive learn.css extension with 4 keyframes for lesson-mode HUD/dock/skip; highlight-paint.test.ts rewritten from collect-time-resolved itLive() getter stub into 3/3 LIVE PASS, P95 = 0.547 ms in jsdom, 29× under the 16 ms RENDER-04 budget) → 80f9ab91 (Task 2: 3 new lesson components under tauri/ui/src/learn/lesson/ — LessonHud factory with progress dots + course chip + lesson title + index, TutorSpeakDock factory with .speak choreography inherited verbatim from rebuild-session mock, LessonSkipButton factory with 45 s anti-speedrun lockout + verbatim tooltip) → 1d86762d (Task 3: 11 envelope listeners on learn-window.ts — 2 P91 inherited + 9 new sidecar→shell handlers + 1 additive midi_position listener for ipc.learn.ack emit on controlled-position deltas while a lesson is active; lazy-mount lesson components on first lesson_loaded; .lesson-mode class flips the grid to 5 rows; emitIpc("ipc.learn.complete_lesson", { reason: "user_skip" }) on skip-button fire post-lockout; showLearnToast helper for progress_state acks). Plan 92-05 closes RENDER-04; LESSON-02 + LESSON-04 already complete from prior plans. Test suite: 1029 passed | 2 skipped | 15 todo (was 1027 passed | 4 skipped baseline — the +2 is the highlight-paint tests flipping skip → PASS). All AST gates STAY GREEN. 92-06 SHIPPED — commit 509915f5 on 2026-05-28 — LearnGroup component (215 lines) added to tauri/ui/src/settings/components/learn-group.ts (mirror of MascotGroup/HelpGroup pattern; local .vmx-settings-row + .vmx-settings-row--destructive CSS scoped under [data-component="learn-group"]); SettingsDrawer.ts gains 1 import + 6-line annotated body.append block between CALIBRATION (line 902) and MASCOT (line 916). Destructive confirm dialog with heading "reset learn progress?", body "all 36 lessons across 3 courses will reset to not started. your library and DJ profile are not affected.", primary "reset" (--led-fault danger variant), secondary "cancel". Confirm fires emitIpc("ipc.learn.progress_state", { action: "reset" }) fire-and-forget; sidecar's reset_ack arrives at the Learn-window surface as showLearnToast("learn progress reset.") (Plan 92-05). Optimistic-repaint via let dialog + queueMicrotask(dismiss) to handle synchronous test-mock onConfirm without TDZ; production behavior unchanged. Flipped tests/settings/learn-group.spec.ts from "awaiting Plan 92-06" skip → 1/1 LIVE PASS (52 ms). Full settings test suite 82/82 across 8 spec files; full vitest suite 1029 passed | 2 skipped | 15 todo. tsc --noEmit exits 0; npm run build clean. Zero new design tokens; zero hex literals; zero forbidden fonts; zero exclamation marks. Plan 92-06 closes the LESSON-03 second half (settings-drawer UI surface); LESSON-03 acceptance gate fully closed — CLI half landed in 92-04 Task 2 + GUI half lands here.)
Status: Phase complete — ready for verification
Last activity: 2026-05-28

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
/gsd:execute-phase 93
```

P93-01 SHIPPED — commits 563a39c3 → 73600a83 on 2026-05-28. 11 RED-state test scaffolds covering EXEMPLAR-01..05 under `tests/learn/test_exemplar_*.py` + `tests/ipc/test_settings_set_envelope_learn_field.py`. Module-level skips named to each downstream plan (93-02..93-06) so the suite stays green today and downstream plans flip the skip → live assertions when their production code lands. Verbatim copies from RESEARCH §Pattern 3 (kick-guard fixtures) / §Pattern 10 (4-site lock test) / §Pattern 11 (grounding e2e). Self-gated skip probes for CLI (`__main__.py` grep) and schema (SettingsSet enum probe) — auto-lift when downstream lands. Pure-additive island; zero touches to existing source. Baseline preserved: 1479 passed / 12 skipped (11 new + 1 pre-existing) / 0 new red across 5-directory merge gate. P92 invariant pins (no_new_ws_port + runtime_invariants + tutor_system_instruction_lock) still 5/5 PASS. Proceed with Plan 93-02 (storage engine + ranker + kick-guard implementation).
