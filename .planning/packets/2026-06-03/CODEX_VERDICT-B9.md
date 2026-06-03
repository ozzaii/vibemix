# CODEX VERDICT - B9 ZPD course routing

- Item: B9 - Wire the ZPD drill router into lessons.
- SHA: `efd863d6 feat(learn): route course starts to the skill frontier`
- User value: a Pro Learn user who re-enters a course now lands on the current skill frontier drill, giving Sven the right lesson context instead of replaying the first scripted step every time.

## By-eye / live artifact

- Launched current source with `VIBEMIX_DEV_SIDECAR=1 VIBEMIX_OUTPUT_DEVICE='Multi-Output Device' uv run python -m vibemix`.
- Boot confirmed meeting-safe audio routing:
  - `AI voice -> Multi-Output Device @ 24000Hz`
  - `djay passthrough -> Multi-Output Device @ 48000Hz`
- Live session: `20260603-143615`.
- Drove `ipc.learn.start_course {"course_id":"course_1","controller_id":"pioneer_ddj_flx4"}` over the live ws bus.
- The reply and UI log showed `ipc.learn.lesson_loaded` with `lesson_id:"L1.02"`, title `meet your controller`, not the opening-dialog first lesson `L1.01`.
- `events.jsonl` recorded `learn_lesson_loaded` for `L1.02`, followed by the tutor line and cited `play:A` teaching-loop payload.

## Checks

- `uv run pytest -q tests/learn/test_ipc_handlers_dispatch.py tests/learn/test_coaching_aim.py tests/learn/test_skill_tree.py` - 52 passed.
- `uv run ruff check src/vibemix/learn/ipc_handlers.py tests/learn/test_ipc_handlers_dispatch.py` - passed.
- `git diff --check` - passed.

## Notes

- This is a data/context routing wire, not a new speech gate: `start_course` now asks the existing `resolve_coaching_aim(progress)` helper and picks a lesson from the selected skill when that course contains one.
- Explicit `start_lesson` behavior is unchanged.
- If no ZPD aim exists, or the aim has no lesson in the requested course, the old first-lesson fallback remains.
