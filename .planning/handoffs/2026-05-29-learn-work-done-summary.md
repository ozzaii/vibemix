# Learn Work Done Summary

**Date:** 2026-05-29
**Status:** technically green, non-external ready, release not complete
**Primary handoff:** `.planning/handoffs/2026-05-29-learn-integration-handoff.md`
**Current package artifact:** `/tmp/vibemix-live-learn-proof/learn-perfection-package-current.json`

## Bottom Line

The Learn beginner module is now a real structured 36-lesson teaching system,
not a syllabus wall. The current package passes Python quality, frontend
quality, desktop quality, and the consolidated package verifier. With the
current user boundary, it is `non_external_ready=true`: there are no internal
package blockers, and the packaged EQ exemplar loops now have a durable human
ear-pass approval. The only remaining release gate is Course 3 routed-audio
count-in proof with real Rekordbox/deck evidence.

Do not mark the full Learn goal complete until that Course 3 gate is proven in
a fresh artifact, but do not keep looping on internal code as if more package
work is blocking release.

The verifier now makes that boundary easy to hand off. The current
`learn-package-verification-current.json` includes a compact
`release_gate_cue_card` with status `waiting_on_external_gates`, the first
action, the remaining Course 3 prompt, route, diagnosis code, current
Rekordbox route, target capture route, route-mismatch boolean,
spoken-prompt flag, run command, and verify command. Use
`uv run python scripts/verify_learn_package.py --cue-card --out
/tmp/vibemix-live-learn-proof/learn-package-verification-current.json` to print
only that small cue card while refreshing the full report on disk. Add
`--say-cue-card` when you want macOS to speak the cue-card headline and first
gate prompt before a hands-on proof pass. The top-level perfection artifact now
carries the same cue card too, so
`/tmp/vibemix-live-learn-proof/learn-perfection-package-current.json` is the
single status handoff for package health plus the next external proof steps.

## Character Direction

The product character decision is restraint plus recognition. Learn should make
the beginner feel, "it noticed the exact thing my hand just did," without
turning into a game layer or a data wall.

- Flair comes from source-aware receipts in the existing tutor dock, for
  example `eq turn · hardware · 01` or `cue hit · screen · 02`, not from badges.
- Value comes from one grounded correction at the moment of action, with a
  visible citation to the control or evidence that caused it.
- Admiration comes from tiny competence payoffs: `clean pass · 1 move`, a clear
  next practice action, and `retry` when a lesson is already in progress.
- Character comes from useful memory, not decoration: if an unfinished lesson
  already needed hints, the booth can say `hint ready for retry` while keeping
  the exact hint count in accessible text instead of adding a dashboard.
- Intelligence comes from the backstage loop and validator contracts: observe,
  decide, teach, verify, adapt, with prompt limits, evidence citations, and
  future-course authoring rules enforced by tests.
- Data should stay backstage unless it changes the next action: progress,
  strikes, surfaces, expected controls, and course-pack checks power the coach
  without becoming the learner's main screen.
- Hardware/screen practice-source memory is now stored in progress rows, so
  future coaching, debrief, profile, and course-pack logic can adapt to how the
  learner actually practiced without adding another surface.
- Course 3 graduation now uses that same memory in its existing grounded status
  line, for example `practice: mostly hardware deck`, giving the learner a
  small "it knows my path" payoff without showing counts or a dashboard.

## Melody/Library Course Direction

The next high-value course direction should be melody-first and library-first,
not another generic theory syllabus. Keep the same practice-booth surface, but
let the learner choose a track from their own crate and teach from what vibemix
can already observe: key/Camelot, cue and section anchors, phrase boundaries,
energy, track familiarity, and library suggestions. The frontstage should still
be one prompt at a time, for example: "Loop the melodic intro on deck A", "bring
in a compatible key on deck B", "swap bass after the phrase turn", then show
the exact melodic/key/section evidence that made the coaching grounded.

The winning UX is not "open a melody course." It is "pick a track you love, and
I will teach you through it." The learner should feel that Learn has taste:
vibemix finds a usable hook, a safe phrase entry, a compatible second track, or
a likely clash in the user's own library, then turns that into one physical
mission. Example frontstage lines:

- "Loop the hook on deck A. Keep it alive for 8 bars."
- "Bring in this 9A intro under the last 16 bars."
- "Kill the bass on B until the vocal phrase turns."
- "Save this as a practice pair if it felt clean."

Backstage, every melody/library mission should carry a structured exemplar:
`track_id`, `section_id`, `cue_anchor`, key/Camelot evidence, phrase span,
energy delta, and a short reason such as `compatible_key`, `hook_to_intro`,
`vocal_clash_risk`, or `melodic_release`. The UI should not expose that as a
table. It should use the evidence to render one calm reason chip and one
coaching sentence. If the user's library is unavailable or too sparse, fall
back to packaged exemplars, but make that a graceful fallback rather than the
default product identity.

Course 4 should probably be organized as six hidden mission families rather
than a visible syllabus wall: hook spotting, phrase alignment, key-safe blends,
melody-clash control, tension/release, and a tiny personal routine built from
the learner's own tracks. The existing course-pack authoring rules should still
apply: canonical IDs, observable controls, deterministic verification,
adaptive hints, replay/jump support, progress/unlocks, and tests.

Treat this as a future course pack, likely Course 4, using the existing
`validate_course_pack_draft(...)` path. It should add value by making practice
feel personalized to the user's own library, while the current release gate
stays unchanged: do not merge melodic-library lessons into the 36-lesson
beginner release unless they pass the same structured-flow, prompt, hint,
grounding, progress, and frontend contracts.

## What Was Built

### Curriculum And Lesson Flows

- Added a canonical 36-lesson beginner path across Course 1 anatomy, Course 2
  transitions, and Course 3 play mode.
- Every beginner lesson now compiles into structured `LessonFlow` steps with
  canonical IDs, expected actions, deterministic verification specs, observable
  control IDs, input surfaces, citations, TTS markers, and adaptive hints.
- The curriculum audit proves 36 beginner lessons, 76 compiled steps, 3+
  adaptive hints per step, hardware/screen input-surface coverage, and claimed
  transcript fixtures.
- The frontend curriculum projection is generated and checked rather than
  manually maintained.

### Calm Practice-Booth Frontstage

- The default Learn surface is a practice booth: one prompt, one action, one
  visible response. The lesson map stays opt-in.
- Users can follow the recommended path, replay completed lessons, or choose
  visible lessons gracefully.
- Completed HUD progress dots now announce that they can replay the lesson;
  current and pending dots also name their state, so jump/replay support is
  understandable without showing more UI.
- The opt-in lesson map now carries the same clarity: completed rows announce
  `press to replay`, in-progress rows announce retry, and locked rows keep the
  exact unlock reason in aria/title text.
- The optional chooser is now a proper disclosure control: `choose lesson`
  reflects `aria-expanded`, points at the chooser with `aria-controls`, closes
  on Escape or lesson pick, and restores focus when dismissed.
- Locked lessons are no longer dead clicks. The UI pulses the existing
  `lock_reason` without starting the lesson or opening a syllabus wall.
- Mid-lesson controller disconnect falls back to the on-screen deck and
  preserves the active highlighted control.
- If a lesson expects a control that is not represented in the active SVG, the
  single fallback screen-action button now names the exact fallback in
  aria/title text while preserving the deterministic ACK path.
- Action receipts now respond to the move just made, for example `eq turn`,
  `jog nudge`, `fader lift`, and `cue hit`.
- Action receipts now remember the input surface when the booth knows it:
  matched MIDI/control moves display `hardware`, and on-screen deck moves
  display `screen`, without adding another panel.
- Those receipts are now announced through the tutor live region and named in
  the package verifier evidence, so the character pass is accessible and
  regression-checked instead of being only visual polish.
- Lesson completion now keeps the visible payoff tiny (`clean pass · 1 move`)
  but gives assistive tech and hover state the refreshed next practice action,
  for example `next practice: start meet your controller`.
- When the booth knows the matched source, that same completion payoff now
  names it without adding UI, for example `clean pass · hardware · 1 move` or
  `clean pass · screen · 1 move`. Mixed-source lessons say
  `hardware + screen` in the same compact line.
- If the learner needed an adaptive hint before completing the lesson, the same
  payoff becomes `recovered pass`, for example
  `recovered pass · screen · 1 move`, which is more honest than calling a
  hinted recovery clean.
- If the recommended lesson is started but unfinished, the primary booth
  action says `retry` instead of `start` while still sending the deterministic
  `level="fresh"` start path to the runtime.
- If that unfinished lesson has persisted hint strikes, the booth pulse now
  says `hint ready for retry`; exact hint counts live in aria/title text so the
  learner gets a useful memory cue without seeing a stat panel.
- Learn progress now remembers whether practice actions came from the physical
  controller or the on-screen deck via `practice_sources` and
  `last_practice_source`, giving the backstage coach useful learner data while
  keeping the booth visually unchanged.
- Course 3 route-mismatch evidence now survives the Learn UI runtime path. A
  flat `course3_lens.operator_action` frame can carry
  `current_rekordbox_route`, `target_capture_route`, and `route_mismatch`; the
  normalizer preserves them, and the status rail collapses the fix into one
  calm line such as `route Rekordbox to BlackHole 16ch` while keeping the exact
  current/target routes in aria/title text.
- The runtime `course3_lens` itself still stays honest: if it only knows
  `MusicState`, it says `selected by readiness` and does not invent
  BlackHole/DDJ route details. Route-specific fixes come from the readiness
  doctor, verifier cue card, or generic operator-action seam where that
  evidence exists.
- The generic `learn.operator_action` seam now has inbound transport: flat
  ws frames can carry `learn_operator_action`, and Tauri can emit
  `learn-operator-action`. Both paths normalize into the same one-action status
  rail, so future course doctors can show one grounded action without extending
  the Learn IPC schema or adding another UI surface.
- The shared IPC schema, generated TypeScript IPC types, generated validator,
  and Learn window progress payload type now accept those fields, so the real
  WebSocket/Tauri progress path stays schema-clean.
- The L3.06 graduation handoff can now fold the persisted practice-source
  memory into the existing debrief/profile status line, keeping the capstone
  grounded and personal without adding UI.

### One-Clear-Prompt Contract

- Added shared `frontstage_prompt_metrics(...)` in
  `src/vibemix/learn/lesson_flow.py`.
- The governed prompt caps are:
  - `max_chars=150`
  - `max_words=24`
  - `max_sentences=2`
  - single line only
  - no inline bullet or numbered-list shape
- The shipped curriculum audit records
  `flow_contract_summary.prompt_contract.ok=true` with observed governed
  maxima of `115 chars / 23 words / 2 sentences`.
- `L1.01.beat.3` is the only prompt-contract exemption because the opening
  dialog line is byte-locked by tone tests and is not a practice instruction.
- Future course packs now emit `validation.prompt_contract` and per-step
  `prompt_metrics`; syllabus-wall draft prompts fail before merge.

### Adaptive Coaching And Runtime Loop

- The teaching loop now follows observe, decide, teach, verify, adapt through
  deterministic runtime records.
- Added `teaching_turn_is_grounded(...)` so every tutor turn can be checked
  against the active lesson, expected control, input surfaces, EvidenceRegistry
  lens, and verification spec.
- The curriculum audit now also proves
  `teaching_grounding_contract.ok=true` with `76/76` normal teaching turns
  grounded, `76/76` cited, and zero failing lessons.
- The curriculum audit now proves `hint_grounding_contract.ok=true` with
  `228/228` beginner hint turns grounded, `228/228` cited, and zero failing
  lessons.
- Empty authored teaching/hint citations now fall back to a deterministic
  `[screen:<control>]` atom for the highlighted control. Runtime timed hints
  cite the same screen evidence the lesson highlight already wrote.
- The tutor dock now lights the existing citation chip for hint lines as well
  as active tutor lines, keeping the grounded coaching visible without adding
  a second surface.
- Browser/Python proof now asserts the learner sees that evidence: a wrong
  on-screen EQ move must render `SCREEN DECK A MID EQ` in the tutor dock before
  the correct move can complete L1.03.
- The package verifier's `teaching_loop_contract` now requires the same
  grounded hint contract before marking the teaching loop proven.
- Wrong on-screen moves reach the Python Learn sidecar and return grounded
  adaptive hints with citations.
- Browser-to-Python tests prove a wrong EQ move on L1.03 produces cited
  adaptive coaching and the correct EQ action completes the lesson.
- Runtime proof stays grounded in expected action, observed control, lesson
  state, and evidence registry data rather than free-form model claims.

### Hardware And On-Screen Deck

- The on-screen controller is no longer just a diagram. SVG hit testing can
  resolve controls from pointer coordinates when the click lands in a bounding
  box but not on a painted child.
- Strict physical app-bus proof cleared the DDJ-FLX4 slice: the live app loaded
  L1.07, observed the left jog as `jog:A=127`, sent the ACK, and advanced the
  lesson.
- Raw hardware sniffing also confirmed the DDJ-FLX4 left jog callback path and
  mapping.
- Bluetooth-MIDI-only readiness is explicitly diagnosed as insufficient for
  full Learn hardware/audio proof. USB/controller audio or a real Rekordbox
  loopback route is still required for release proof.

### Course 3 Live Play Mode

- Course 3 is simple frontstage but smart backstage: live audio, cue-section
  lookahead, prepared pool, library suggestions, session state, session
  recording, debrief, DJ profile, and recovery drill lenses are declared and
  audited.
- Course 3 phrase count-ins are gated on live audio, deck confidence,
  Rekordbox/Now Playing metadata, and cue/section anchors.
- Mix count-in anchoring refuses ambiguous duplicate titles and only proceeds
  when a citable deck title match is exact and unambiguous.
- Auto-master finder evidence now ranks live routes, saved Rekordbox output,
  macOS route, loopback fallbacks, sample rates, and route reasons.
- The route doctor now gives one operator action at a time, including
  sample-rate fixes, aggregate route hints, and start-playback steps.
- Spoken prompts are available for physical and Course 3 operator actions via
  `say(1)` flags.

### EQ Exemplar Ear-Pass Path

- Packaged self-authored EQ exemplar WAVs are present and technically audited.
- The audition CLI can play the current bank, speak band labels, and write a
  durable audition artifact.
- Human approval now requires a matching audition artifact and records the
  current bank fingerprint and track hashes.
- Stale approvals or changed WAV hashes keep release readiness false.

### Future Course Integration

- `validate_course_pack_draft(...)` validates future course packs before
  global curriculum tables are edited.
- The course-pack validator now emits:
  - `flow_preview`
  - `observed_capabilities`
  - `required_progress_fields`
  - `integration_plan`
  - `prompt_contract`
  - `teaching_grounding_contract`
  - `hint_grounding_contract`
  - `copy_truthfulness`
  - machine-readable errors
- Future course packs now have to prove every compiled teaching turn plans
  through `plan_teaching_turn(...)`, remains grounded, and carries a citation.
- Future course packs now have to prove the first three adaptive hint turns
  plan through `plan_hint_turn(...)`, remain grounded, and carry citations.
- `validate_learn_course_pack.py --init-template` now writes an
  `authoring_contract` into the starter manifest. New course authors start
  from the same one-prompt, one-action, grounded-response rule; hardware/screen
  input-surface defaults; starter expected cue action; hint floor; prompt caps;
  copy-truthfulness rule; and post-merge verification commands.
- Manifest validation now requires that `authoring_contract` on submitted
  course packs and reports it as
  `CoursePackValidation.authoring_contract`, so future-course scaffolds cannot
  silently shed the beginner Learn authoring rules.
- The integration plan names target files, `COURSE_REGISTRY` edits,
  `COURSE_FRAMES` edits, `CURRICULUM` lesson rows, transcript paths, progress
  fields for locked courses, and post-merge commands.
- The package verifier requires the course-extension contract, so new courses
  have a machine-checked path instead of a hand-maintained checklist.
- The same verifier now records both source-aware action receipts and the
  accessible next-practice completion reward under
  `frontstage_simplicity_contract.evidence`, keeping the booth's personality
  and QoL behaviors in the release evidence.
- It also records the in-progress recommendation copy rule, so future UI work
  does not accidentally make a retry feel like a brand-new lesson.
- The verifier now also records
  `future_course_extension_contract.evidence.starter_template_contract`, so
  future course scaffolds must preserve the beginner Learn authoring rules,
  including the starter expected action and required post-merge checks.
- Its `draft_validator.result_fields` now includes `authoring_contract`.

### Package And Quality Gates

- Added consolidated Learn quality runners for Python, frontend, desktop, live
  proof validation, and full package verification.
- Added `objective_audit` to the package verifier. It maps the original Learn
  goal into nine concrete objective groups and shows which verifier rows prove
  or block each group.
- Added `non_external_ready` to the verifier/package runner. It only ignores
  the currently deferred EQ ear-pass and Course 3 routed-audio gates; any other
  blocker remains an internal blocker and keeps the package incomplete.
- The latest full package run passed:
  - `python_quality`
  - `frontend_quality`
  - `desktop_quality`
  - `package_verifier`
- The package artifact persists `release_blocker_recipe_ids` so handoff tools
  can read the remaining blocker ID directly.

### Melody/Library-First Course 2 Direction

- Added `src/vibemix/learn/harmonic_practice.py`, a deterministic
  library-grounded Camelot pair picker. It uses existing Rekordbox track facts,
  `TrackRelation`, and `harmonics.to_camelot`; it does not ask a model to
  compute keys and it does not play audio.
- `L2.11` now carries `library_melody_pair=true`, and `lesson_flow` declares
  the `library_suggestions` backstage lens for that lesson. Course 2 also
  declares the `library_suggestions` capability in both Python and the generated
  TypeScript curriculum mirror.
- `LessonRuntime` now accepts `harmonic_pair_loader` and, only for `L2.11`,
  emits one extra grounded tutor line when a compatible pair exists:
  `tts_marker="L211.library_pair"`, with `[track:<id>]` citations only when the
  shared `EvidenceRegistry` resolves the library tracks.
- `__main__.py` wires `harmonic_pair_loader=_load_learn_harmonic_pair`, reusing
  the already-loaded Rekordbox cache when present and falling back to
  `RekordboxLibrary.try_load_cache()` when Learn starts after a cold import.
- New tests cover pair selection, seed-track future wiring, prompt bounds,
  citation safety, runtime emission/no-pair fallback, frontend capability
  projection, and boot wiring.
- Product meaning: the Camelot lesson is no longer only a wheel/diagram. If the
  user's crate has compatible keyed tracks, Learn says "your library pair..." and
  teaches melody through music they already own while keeping the same calm
  one-action booth.

## Current Evidence

Use these as the latest local proof points:

- `/tmp/vibemix-live-learn-proof/learn-perfection-package-current.json`
  - `passed=true`
  - `verification_refreshed=true`
  - commands passed: Python, frontend, desktop, package verifier
  - `non_external_ready=true`
  - `internal_blocker_ids=[]`
  - `deferred_external_blocker_ids=["course3_live_audio_play_mode"]`
  - `release_ready=false`
  - objective audit: `8/9` proven
  - blocking objective IDs:
    - `course3_live_play_mode`
  - blocker IDs:
    - `course3_live_audio_play_mode`
- `/tmp/vibemix-live-learn-proof/learn-curriculum-audit-current.json`
  - `passed=true`
  - 36 beginner lessons
  - 76 compiled beginner steps
  - teaching grounding: `76/76` authored beginner teaching turns grounded and
    cited
  - hint grounding: `228/228` authored beginner hint turns grounded and cited
  - prompt contract passes with governed maxima
    `115 chars / 23 words / 2 sentences`
- `/tmp/vibemix-live-learn-proof/learn-python-quality-current.json`
  - `passed=true`
- `/tmp/vibemix-live-learn-proof/learn-frontend-quality-current.json`
  - `passed=true`
- `/tmp/vibemix-live-learn-proof/learn-desktop-quality-current.json`
  - `passed=true`

## Commands That Were Green

The most important current checks:

```bash
uv run pytest -q tests/learn/test_teaching_loop.py tests/learn/test_curriculum_audit.py tests/learn/test_verify_learn_package.py
uv run pytest -q tests/learn/test_teaching_loop.py tests/learn/test_adaptive_coaching_runtime_contract.py tests/learn/test_runtime_evidence_grounding.py tests/learn/test_curriculum_audit.py tests/learn/test_verify_learn_package.py
npm --prefix tauri/ui test -- tests/learn/test_tutor_speak_sr_announcement.spec.ts
npm --prefix tauri/ui test -- tests/learn/test_practice_booth_shell.spec.ts tests/learn/test_tutor_speak_sr_announcement.spec.ts
uv run pytest -q tests/learn/test_run_learn_frontend_quality.py tests/learn/test_verify_learn_package.py
uv run ruff check scripts/run_learn_frontend_quality.py scripts/verify_learn_package.py tests/learn/test_run_learn_frontend_quality.py tests/learn/test_verify_learn_package.py
npm --prefix tauri/ui run build
npm --prefix tauri/ui run test:e2e:learn -- tests/learn/browser-python-beginner-path.pw.ts
uv run python scripts/run_learn_python_quality.py --out /tmp/vibemix-live-learn-proof/learn-python-quality-current.json
uv run python scripts/run_learn_perfection_package.py --out /tmp/vibemix-live-learn-proof/learn-perfection-package-current.json
uv run python scripts/audit_learn_curriculum.py --out /tmp/vibemix-live-learn-proof/learn-curriculum-audit-current.json
uv run pytest -q tests/learn/test_lesson_flow_contract.py tests/learn/test_curriculum_audit.py tests/learn/test_course_pack.py tests/learn/test_verify_learn_package.py
uv run pytest -q tests/learn/test_course_pack.py tests/learn/test_curriculum_audit.py tests/learn/test_verify_learn_package.py tests/learn/test_run_learn_perfection_package.py
uv run pytest -q tests/learn/test_harmonic_practice.py tests/learn/test_harmonic_practice_runtime.py tests/learn/test_lesson_flow_contract.py tests/learn/test_course_2_curriculum.py tests/learn/test_observer_boot_wiring.py
npm --prefix tauri/ui test -- tests/learn/test_curriculum_meta.spec.ts
uv run python scripts/export_learn_curriculum_meta.py --check
```

## Remaining Release Work

### EQ Ear-Pass

Done. The current approval artifact is
`/tmp/vibemix-live-learn-proof/learn-exemplar-ear-pass-current.json`, approved
by `ozai` after playback through MacBook Pro Speakers. The approved bank
fingerprint digest is
`34e7aafe568b2e8badecb75fd28e0a8bd710f4fd1b1f2d84e7ff4a78584096e9`.

### Course 3 Routed Audio

The current blocker is not a port conflict and not an internal Learn-code
blocker. The latest proof attempt started the app, opened the socket, spoke the
Course 3 prompt with `say(1)`, and successfully nudged Rekordbox with Space,
but capture stayed silent. The remaining action is real Rekordbox master audio
and citable deck metadata:

1. Stop unrelated browser/system media or make Rekordbox the active source.
2. In Rekordbox Audio preferences, set the audio output from
   `DDJ-FLX4 @ 48000Hz` to `BlackHole 16ch @ 48000Hz` or a 48 kHz aggregate
   that includes it. The DDJ-FLX4 hardware route is visible and useful, but it
   is not the capture route that proves Course 3.
3. Load and play a real Rekordbox library track.
4. Raise channel fader, crossfader, trim, and master until capture has signal.
5. Rerun Course 3 live proof with spoken prompts.

## Guardrails For Next Work

- Keep the map opt-in. Do not turn Learn into a visible 36-row syllabus.
- Keep the frontstage one prompt, one action, one grounded response.
- Do not invent Course 3 audio, phrase, deck, or track claims.
- Preserve live-audio authority and EvidenceRegistry grounding.
- Keep tutor/model routing through `vibemix.llm.model_router`.
- Do not remove the `L1.01.beat.3` prompt-contract exemption without explicit
  approval and byte-equality test updates.
- Worktree is very dirty. Do not revert unrelated user or parallel-agent
  changes.
