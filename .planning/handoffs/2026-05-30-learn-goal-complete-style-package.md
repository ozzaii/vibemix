# Learn Beginner Module, Completion-Style Package

Status: release-candidate package, not a release-ready claim.

This file packages the Learn rebuild as if it were being handed off at goal
completion, with one explicit honesty boundary: the current verifier still
reports `release_ready=false` because Course 3 routed audio has not produced
strict count-in proof. Do not use this file to mark the persistent goal
complete. Use it to hand the work to an integration/release session cleanly.

## Executive Read

vibemix Learn now behaves like a real beginner DJ practice booth instead of a
syllabus wall:

- 36 beginner lessons compile into structured flows.
- The default surface stays one prompt, one action, one grounded response.
- Lessons can be started by recommendation or chosen from an opt-in map.
- Hardware and screen practice both route through the same lesson contract.
- The backstage loop is explicit: observe -> decide -> teach -> verify -> adapt.
- Tutor/model routing stays behind `vibemix.llm.model_router`.
- Evidence grounding, controller state, progress, replay, unlocks, debrief, and
  session seams are wired into the package.
- Course 2 now has a melody/library-first branch: `L2.11` can teach Camelot
  through a real compatible pair from the user's Rekordbox library.

The technical package is green. The remaining release gate is external desk
state: route Rekordbox master audio into the capture path and prove Course 3
count-in with live audio.

## Current Verification

Artifact:

`/tmp/vibemix-live-learn-proof/learn-perfection-package-current.json`

Current result:

- `passed=true`
- `non_external_ready=true`
- `release_ready=false`
- `internal_blocker_ids=[]`
- `deferred_external_blocker_ids=["course3_live_audio_play_mode"]`
- `release_blocker_recipe_ids=["course3_live_audio_play_mode"]`
- completion matrix: `21/22` proven
- objective audit: `8/9` proven
- only blocking objective: `course3_live_play_mode`

Package commands in the artifact all passed:

- `python_quality`
- `frontend_quality`
- `desktop_quality`
- `package_verifier`

Frontend build also passed separately:

```bash
npm --prefix tauri/ui run build
```

## Remaining Gate

Current cue card:

- Current Rekordbox route: `DDJ-FLX4 @ 48000Hz`
- Target capture route: `BlackHole 16ch @ 48000Hz`
- `route_mismatch=true`
- diagnosis: `loopback_route_healthy_external_playback_absent`

Primary next action:

```text
In Rekordbox Audio preferences, set the audio output from DDJ-FLX4 @ 48000Hz to BlackHole 16ch @ 48000Hz.
```

Then load and play a real Rekordbox library track with channel fader, trim,
crossfader, and master up. After that, run:

```bash
uv run python scripts/run_learn_live_proof.py --start-app --no-screen --course3 --seed-course3-unlocked --auto-master-input --nudge-rekordbox-playback --require-count-in --say-course3-prompts --wait-loopback-signal-seconds 30 --wait-capture-signal-seconds 30 --wait-course3-seconds 120 --course3-context-seconds 5 --loopback-signal-seconds 2 --loopback-self-test-seconds 1 --capture-matrix-seconds 2 --out /tmp/vibemix-live-learn-proof/proof-course3-auto-master-current.json
```

## Product Package

The shipped user experience should be described like this:

The learner opens Learn, sees a calm practice booth, and gets one action. They
can use a plugged physical controller or the on-screen deck. Vibemix highlights
or names the control, waits for the action, verifies it deterministically,
responds with grounded coaching, and advances. The full 36-lesson path exists
behind the booth, but the learner sees a recommended next move and an optional
map, not a course spreadsheet.

The module's personality is now in the intelligence, not in visual clutter:

- It notices wrong controls and gives specific adaptive hints.
- It remembers hardware versus screen practice.
- It rewards clean passes and recovered passes with compact booth copy.
- It keeps retry state human: "hint ready for retry", not a cold reset.
- It can teach melody through the user's own library when keyed tracks exist.

## Architecture Package

Core files:

- `src/vibemix/learn/curriculum.py`: canonical course and lesson metadata.
- `src/vibemix/learn/lesson_flow.py`: structured flow compiler.
- `src/vibemix/learn/runtime.py`: deterministic lesson FSM and sole
  `LearnState` writer.
- `src/vibemix/learn/teaching_loop.py`: observe/decide/teach/verify/adapt turn
  records through `model_router`.
- `src/vibemix/learn/harmonic_practice.py`: library-grounded Camelot pair picker.
- `tauri/ui/src/learn/learn-window.ts`: practice booth surface.
- `tauri/ui/src/learn/lesson/curriculum-meta.ts`: generated frontend mirror.
- `scripts/verify_learn_package.py`: package verifier and release gate recipe.
- `scripts/run_learn_perfection_package.py`: complete local quality package.

Important invariants:

- No second websocket. Learn uses the existing `127.0.0.1:8765` bus.
- Lesson runtime does not write `MusicState` or controller state.
- Tutor copy remains fixture-authored. Runtime can add grounded metadata and
  deterministic helper lines, but not live-generated lesson text.
- Live audio remains authoritative for Course 3.
- Track citations must resolve through `EvidenceRegistry`.
- Course 3 forward calls need cue/section grounding.

## Melody/Library Package

The latest product direction is now implemented in the first concrete place:
Course 2, lesson `L2.11`, the Camelot wheel.

Behavior:

- If a Rekordbox library cache exists and has compatible known keys, Learn picks
  one deterministic pair.
- The pair is scored from existing coded facts: Camelot compatibility, BPM
  compatibility, rating, and play count.
- The runtime emits `tts_marker="L211.library_pair"`.
- Track citations are included only when `EvidenceRegistry` resolves the track
  IDs.
- If no safe pair exists, the lesson falls back to the original fixture copy.

Why this matters:

The beginner does not learn harmonic mixing as a static wheel. They hear:
"your library pair..." and practice with tracks they already care about.
That gives the module character without adding pages.

## New-Course Package

Future courses should enter through the course-pack contract, not by manually
copying scattered lesson code.

Recommended path:

1. Start from `vibemix.learn.course_pack.course_pack_template(...)`.
2. Validate with:

```bash
uv run python scripts/validate_learn_course_pack.py <course-pack.json>
```

3. Add `COURSE_REGISTRY`, `COURSE_FRAMES`, and `CURRICULUM` rows.
4. Add transcript fixtures.
5. Regenerate the frontend mirror:

```bash
uv run python scripts/export_learn_curriculum_meta.py
```

6. Run:

```bash
uv run python scripts/export_learn_curriculum_meta.py --check
uv run pytest -q tests/learn/test_course_pack.py tests/learn/test_curriculum_audit.py tests/learn/test_lesson_flow_contract.py
uv run python scripts/run_learn_perfection_package.py --out /tmp/vibemix-live-learn-proof/learn-perfection-package-current.json
```

Authoring rules:

- Declare every backstage capability the compiled flow needs.
- Keep prompts under the frontstage contract.
- Add at least three adaptive hints per lesson.
- Keep actions observable through hardware, screen, or both.
- Do not promise automatic debrief/profile/session behavior unless wired.
- Keep the map opt-in.

## Demo Script

For a product demo without the unresolved Course 3 gate:

1. Start Learn.
2. Use the recommended lesson button.
3. Complete one basic controller action on screen or hardware.
4. Open the optional map only to show choice/replay.
5. Start `L2.11` with a keyed Rekordbox cache available.
6. Show the library pair prompt and the track citations.
7. Run the package verifier and show `passed=true`, `non_external_ready=true`.
8. State the remaining honest release gate: Course 3 routed audio.

## Green Checks From This Packaging Pass

```bash
uv run ruff check src/vibemix/learn/harmonic_practice.py src/vibemix/learn/runtime.py src/vibemix/learn/curriculum.py src/vibemix/learn/lesson_flow.py src/vibemix/learn/__init__.py src/vibemix/__main__.py tests/learn/test_harmonic_practice.py tests/learn/test_harmonic_practice_runtime.py tests/learn/test_lesson_flow_contract.py tests/learn/test_observer_boot_wiring.py
uv run pytest -q tests/learn/test_harmonic_practice.py tests/learn/test_harmonic_practice_runtime.py tests/learn/test_lesson_flow_contract.py tests/learn/test_course_2_curriculum.py tests/learn/test_observer_boot_wiring.py
npm --prefix tauri/ui test -- tests/learn/test_curriculum_meta.spec.ts
uv run python scripts/export_learn_curriculum_meta.py --check
uv run pytest -q tests/learn/test_course_pack.py tests/learn/test_curriculum_audit.py tests/learn/test_run_learn_python_quality.py tests/learn/test_run_learn_perfection_package.py
uv run python scripts/verify_learn_package.py --cue-card --out /tmp/vibemix-live-learn-proof/learn-package-verification-current.json
uv run python scripts/run_learn_perfection_package.py --out /tmp/vibemix-live-learn-proof/learn-perfection-package-current.json
npm --prefix tauri/ui run build
```

## Final Handoff Line

Treat this as a complete-style RC package. The module is technically packaged,
documented, and internally green. The one thing it still cannot honestly claim
is release completion, because Course 3 live routed audio has not yet produced
strict count-in proof.
