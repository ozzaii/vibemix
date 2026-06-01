# CODEX_READY: Learn Operator Action Bridge

Date: 2026-06-01
Author: Codex
Package: 7 - Learn Operator Action Bridge
Decision: LAND
Suggested commit: `feat(learn): bridge route-mismatch operator actions`

## Summary

This package is ready to land as the Learn operator-action bridge.

It gives Learn a small, grounded way to surface "do this one setup action now"
without turning the booth into a noisy diagnostics panel. Course 3 readiness can
publish route-fix/operator actions; the frontend normalizes them, bridges both
websocket and Tauri event sources, and renders one calm booth prompt while
keeping full route/step evidence in ARIA/title.

The package also fixes screen-only Learn controls (`headphone_cue`,
`lesson_continue`, `master_vol`) so they use the on-screen fallback action
instead of trying to paint missing controller SVG highlights and warning falsely.

## Files In Package

- `tauri/ui/src/learn/lesson/curriculum-meta.ts`
- `tauri/ui/src/learn/lesson/operator-action.ts`
- `tauri/ui/src/learn/ws-client.ts`
- `tauri/ui/src/learn/learn-window.ts`
- `tauri/ui/tests/learn/test_curriculum_meta.spec.ts`
- `tauri/ui/tests/learn/test_operator_action.spec.ts`
- `tauri/ui/tests/learn/test_practice_booth_shell.spec.ts`
- `tauri/ui/tests/learn/test_ws_client_filters_mascot.spec.ts`
- `tauri/ui/tests/learn/test_ws_client_tauri_bridge.spec.ts`
- `tests/learn/test_curriculum_projection.py`
- `.planning/handoffs/2026-05-30-learn-goal-complete-style-package.md`

## LAND Criteria

- Course 3 operator actions can ride inside `course3_lens.operator_action`.
- Generic future operator actions can ride as `learn_operator_action` or a flat prompt frame.
- Tauri can deliver `learn-operator-action` alongside the existing Course 3 lens bridge.
- Route mismatch evidence is preserved in full while the visible status line stays compact.
- Generic operator actions can be cleared.
- Screen-only Learn controls no longer generate false missing-highlight warnings.
- `learn.start_course` automation emits the canonical `ipc.learn.start_course` payload.
- Generated curriculum metadata still matches Python source.

## Source Evidence

### Operator-action normalization

- `tauri/ui/src/learn/lesson/operator-action.ts:9-18` defines the action payload,
  including current route, target route, route mismatch, steps, and recommended devices.
- `tauri/ui/src/learn/lesson/operator-action.ts:20-50` validates actions and rejects
  empty/non-string prompts.
- `tauri/ui/src/learn/lesson/operator-action.ts:53-81` collapses a full operator action
  into one booth-sized visible phrase.
- `tauri/ui/src/learn/lesson/operator-action.ts:83-102` preserves full prompt, route,
  mismatch, and step evidence in the assistive label.
- `tauri/ui/src/learn/lesson/operator-action.ts:117-148` keeps BlackHole/sample-rate
  route labels precise enough to distinguish BlackHole 2ch from 16ch and aggregate
  48k fixes.

### Transport bridge

- `tauri/ui/src/learn/ws-client.ts:65-68` declares the local `learn.operator_action`
  event and the Tauri `learn-operator-action` event name.
- `tauri/ui/src/learn/ws-client.ts:220-245` subscribes to the Tauri operator-action
  event, stores its unlistener, and cleans it up on close.
- `tauri/ui/src/learn/ws-client.ts:271-277` dispatches Course 3 lens and generic
  operator-action hints from flat shared-bus frames before dropping unrelated frames.
- `tauri/ui/src/learn/ws-client.ts:313-317` turns extracted actions into
  `learn.operator_action` browser events.
- `tauri/ui/src/learn/ws-client.ts:324-342` extracts `learn_operator_action`,
  `operator_action`, clear-null actions, and flat prompt frames without letting
  ordinary `ipc.*` frames masquerade as operator actions.
- `tauri/ui/src/learn/ws-client.ts:344-381` preserves nested
  `course3_lens.operator_action` in the Course 3 lens payload.

### Learn booth consumption

- `tauri/ui/src/learn/learn-window.ts:220-237` declares screen-only controls and
  maps course aliases to canonical start-course wire IDs.
- `tauri/ui/src/learn/learn-window.ts:588-596` routes screen-only highlights through
  the screen action fallback instead of trying to paint a missing SVG target.
- `tauri/ui/src/learn/learn-window.ts:624-642` consumes `learn.start_course` and emits
  `ipc.learn.start_course` with the normalized payload.
- `tauri/ui/src/learn/learn-window.ts:730-742` consumes `learn.course3_lens` and
  `learn.operator_action`, sending both into the status bar.
- `tauri/ui/src/learn/learn-window.ts:1026-1049` lets the on-screen action emit
  deterministic `ipc.learn.ack`.
- `tauri/ui/src/learn/learn-window.ts:1247-1249` centralizes the screen-only action test.
- `tauri/ui/src/learn/learn-window.ts:1354-1383` normalizes snake_case/camelCase
  start-course details and defaults controller ID to `pioneer_ddj_flx4`.
- `tauri/ui/src/learn/components/status-bar.ts:142-169` chooses operator actions over
  generic blocker copy when Course 3 provides a concrete action.
- `tauri/ui/src/learn/components/status-bar.ts:223-229` supports generic external
  operator actions and clear-to-default.
- `tauri/ui/src/learn/components/status-bar.ts:273-283` renders one compact visible
  phrase while preserving the full action in ARIA/title.

### Curriculum projection

- `tauri/ui/src/learn/lesson/curriculum-meta.ts:1-4` declares the file as generated by
  `scripts/export_learn_curriculum_meta.py` from Python curriculum source.
- `tauri/ui/src/learn/lesson/curriculum-meta.ts:21-25` mirrors course registry,
  frontstage mode, and capabilities.
- `tauri/ui/src/learn/lesson/curriculum-meta.ts:60-98` mirrors the canonical 36-lesson
  order including Course 3 Play Mode.
- `tauri/ui/src/learn/lesson/curriculum-meta.ts:112-170` projects progress into
  list entries with unlock gates and lock reasons.

## Test Evidence

### Frontend Unit Tests

Command:

```bash
npm --prefix tauri/ui test -- tests/learn/test_curriculum_meta.spec.ts tests/learn/test_operator_action.spec.ts tests/learn/test_practice_booth_shell.spec.ts tests/learn/test_ws_client_filters_mascot.spec.ts tests/learn/test_ws_client_tauri_bridge.spec.ts
```

Result:

```text
Test Files  5 passed (5)
Tests       55 passed (55)
```

Coverage highlights:

- `tauri/ui/tests/learn/test_operator_action.spec.ts:11-106` verifies route-fix,
  exemplar ear-pass, aggregate 48k, route-mismatch, and invalid-prompt projection.
- `tauri/ui/tests/learn/test_ws_client_filters_mascot.spec.ts:150-202` verifies
  `course3_lens.operator_action` survives a flat shared-bus frame without warnings.
- `tauri/ui/tests/learn/test_ws_client_filters_mascot.spec.ts:204-261` verifies
  generic `learn_operator_action` bridge and explicit null clear.
- `tauri/ui/tests/learn/test_ws_client_tauri_bridge.spec.ts:80-213` verifies Tauri
  `learn-operator-action` subscription, event dispatch, and unlisten cleanup.
- `tauri/ui/tests/learn/test_practice_booth_shell.spec.ts:334-468` verifies Course 3
  operator-action, aggregate-rate, and route-mismatch prompts render as one calm booth fix.
- `tauri/ui/tests/learn/test_practice_booth_shell.spec.ts:470-501` verifies future
  generic operator actions render and clear.
- `tauri/ui/tests/learn/test_practice_booth_shell.spec.ts:545-571` verifies
  `learn.start_course` emits canonical `ipc.learn.start_course`.
- `tauri/ui/tests/learn/test_practice_booth_shell.spec.ts:1548-1630` verifies
  screen-only controls use fallback actions, emit deterministic acks, and do not log
  false missing-highlight warnings.

### Python Projection Tests

Command:

```bash
uv run python scripts/export_learn_curriculum_meta.py --check
```

Result: passed with exit code 0.

Command:

```bash
uv run pytest -q tests/learn/test_curriculum_projection.py
```

Result:

```text
4 passed in 0.26s
```

### Build And Diff Hygiene

Command:

```bash
npm --prefix tauri/ui run build
```

Result:

```text
tsc --noEmit && vite build passed
```

Command:

```bash
git diff --check -- tauri/ui/src/learn/lesson/curriculum-meta.ts tauri/ui/src/learn/lesson/operator-action.ts tauri/ui/src/learn/ws-client.ts tauri/ui/src/learn/learn-window.ts tauri/ui/tests/learn/test_curriculum_meta.spec.ts tauri/ui/tests/learn/test_operator_action.spec.ts tauri/ui/tests/learn/test_practice_booth_shell.spec.ts tauri/ui/tests/learn/test_ws_client_filters_mascot.spec.ts tauri/ui/tests/learn/test_ws_client_tauri_bridge.spec.ts tests/learn/test_curriculum_projection.py .planning/handoffs/2026-05-30-learn-goal-complete-style-package.md
```

Result: passed with no output.

## Boundaries

- This package does not run GSD.
- This package does not run the Learn beginner-path suites listed as excluded in `AGENTS.md`.
- This package does not claim Course 3 routed-audio release readiness. The included handoff
  explicitly keeps `release_ready=false` until strict live Course 3 routed-audio/count-in proof exists.
- This package does not claim a live DDJ/FLX4 proof run. It proves the operator-action UI/transport
  bridge and curriculum projection on current source.

## Verdict

LAND as `feat(learn): bridge route-mismatch operator actions`.
