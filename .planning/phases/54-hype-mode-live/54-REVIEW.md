---
status: clean
phase: 54-hype-mode-live
depth: standard
reviewer: inline (Agent subagent unavailable in this runtime — orchestrator-inline review)
files_reviewed: 6
findings:
  critical: 0
  warning: 0
  info: 2
  total: 2
---

# Phase 54 — Code Review (Hype Mode Live)

Reviewed at standard depth. Source surface for this phase:

- `src/vibemix/audio/constants.py` (1-line additive constant + comment)
- `tauri/ui/src/session/hype-mode-indicator.ts` (the only real logic module)
- `tests/state/test_hype_trace_replay.py`
- `tests/state/test_hype_cooldown_grounding.py`
- `tests/state/test_hype_anti_slop.py`
- `tests/agent/test_hype_prompt_grounding.py`
- `tests/eval/test_replay_harness_cooldowns.py` (additive test)
- `tauri/ui/src/session/hype-mode-indicator.test.ts`

(Reviewer note: the `Agent` subagent tool is not available in this runtime, so
the review was performed inline by the orchestrator per the runtime fallback —
a real read-through of the changed source, not a skipped gate.)

## Verdict: CLEAN — no Critical, no Warning.

### Bugs / correctness
- `deriveIndicatorState` decision ladder is exhaustive and ordered correctly
  (hidden → offline → pulse-window → active-window → idle). The `sinceReaction
  >= 0` guards correctly reject a future-skewed `lastReactionAtMs` (clock skew)
  so a negative delta falls through to LISTENING rather than a phantom pulse —
  pinned by `test_a_future-skewed_reaction_does_not_falsely_pulse`.
- `lastReactionArrivalMs` handles empty ring, `noUncheckedIndexedAccess`
  (the `latest == null` guard), and malformed `ts` (Date.parse → NaN → null).
- The Python tests drive the REAL `EventDetector` / `EvidenceRegistry` /
  `CitationLinter` (no mocks of the units under test) — the grounding +
  anti-slop contracts are pinned against real behavior.

### Security
- No injection surface: the indicator renders fixed string labels via
  `textContent` (never `innerHTML`); the CSS is a static template literal with
  no interpolation. No user input reaches the DOM.
- No new IPC/ws wire field, no new network call, no new dependency.

### Style / conventions
- ESM `.js` import extensions, token-only colors, `--type-display` font — all
  match the existing `session/` conventions.
- The constant edit is purely additive (verified by `git diff`); no v4 cooldown
  value changed.

## Info findings (non-blocking)

### INFO-1: `_styleInjected` is a module-global, not per-document
`ensureStyle` guards style injection with a module-level boolean. In a
hypothetical multi-document/multi-window Tauri scenario, only the FIRST
document would receive the `<style data-hype-indicator>` block; a second
document's indicator would render unstyled. Not a defect today (the live
session UI is single-window) and the module is not yet wired into the layout
(wiring is a documented follow-on). If multi-window mounting ever happens, key
the guard on the target `Document` (e.g. a `WeakSet<Document>`) instead of a
boolean. Filed as Info, not Warning, because the current usage is single-doc.

### INFO-2: pulse re-trigger relies on a forced reflow (`void led.offsetWidth`)
`update()` restarts the CSS keyframe on back-to-back reactions by removing the
class, forcing a synchronous reflow, then re-adding it. This is the standard,
correct technique for restarting a CSS animation deterministically, but it does
cost one layout flush per pulsing frame. At the real reaction cadence (seconds
apart, gated by the v4 cooldowns) this is negligible. Documented here only so a
future maintainer who sees the `void led.offsetWidth` line understands it is
intentional, not dead code.

## Tests / verification observed
- `pytest -q` (full default suite): 3768 passed, 26 skipped, 0 failed.
- `cd tauri/ui && npm test -- hype-mode-indicator`: 12 passed.
- `cd tauri/ui && npm run -s build`: BUILD_OK (tsc --noEmit + vite build).
