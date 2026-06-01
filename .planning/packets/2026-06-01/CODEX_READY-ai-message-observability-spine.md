# CODEX_READY: AI Message Observability Spine

Date: 2026-06-01
Author: Codex
Status: LAND packet, observability backbone slice
Package: Package 1A - AI Message Observability Spine

## Decision

LAND this slice as `feat(observability): persist ai message evidence rows`.

This package gives the app a shared `ai_message` row shape for assistant-facing
engines. It preserves what was said, which engine/model/surface said it, prompt
and response artifacts where available, and the deck/move/lesson/tool evidence
that framed the turn.

## Files

- `src/vibemix/runtime/ai_observability.py`
- `src/vibemix/agent/dj_cohost.py`
- `src/vibemix/bench/run.py`
- `src/vibemix/debrief/drills.py`
- `src/vibemix/debrief/tldr.py`
- `src/vibemix/state/deck_vision.py`
- `src/vibemix/learn/observability.py`
- `src/vibemix/learn/runtime.py`
- `src/vibemix/__main__.py`
- `src/vibemix/library/codex_curate.py`
- `scripts/eval/judge.py`
- `.planning/handoffs/2026-05-31-ai-message-observability-handoff.md`
- `scripts/verify_ai_observability.py`
- `tests/runtime/test_ai_observability.py`
- `tests/agent/test_dj_cohost.py`
- `tests/bench/test_run_fake.py`
- `tests/scripts/test_verify_ai_observability.py`
- `tests/state/test_deck_vision.py`
- `tests/debrief/test_tldr_length_60_to_90s.py`
- `tests/debrief/test_drill_citations_resolve.py`
- `tests/eval/test_judge_pro_rubric.py`
- `tests/learn/test_observer_boot_wiring.py`
- `tests/learn/test_runtime_evidence_grounding.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`
- `.planning/packets/2026-06-01/INDEX.md`
- `.planning/packets/2026-06-01/CODEX_READY-ai-message-observability-spine.md`

## What Changed

- Added a shared AI-message builder/writer for session-scoped and global rows.
- Live co-host turns persist `ai_message` rows with response id, provider/model,
  prompt/response artifacts, deck mixer snapshot, recent/event moves, audio
  context, citation action/count, stop reason, and latency metadata.
- Viber/Codex curate/build/chat paths append global rows with reply/rationale,
  tool trace, tools used, track ids, move grades, playlist/export artifacts, and
  live context where present.
- Eval judges persist global rows for Pro/Flash judge responses and failures,
  including full judge prompt/raw response artifacts and parsed verdict data.
- Bench, deck vision, debrief TLDR/drills, and Learn tutor speech now write
  compatible rows or events so future verification can inspect every
  assistant-facing surface through one shape.
- `scripts/verify_ai_observability.py` verifies session/global rows, artifact
  paths, move context, deck mixer context, engine/surface filters, and latest
  session discovery.

## Evidence

Focused observability gates:

```text
uv run pytest -q tests/scripts/test_verify_ai_observability.py tests/runtime/test_ai_observability.py tests/eval/test_judge_pro_rubric.py tests/agent/test_dj_cohost.py::test_llm_node_logs_ai_message_observability_with_moves tests/agent/test_dj_cohost.py::test_llm_node_ai_message_uses_prompt_time_mixer_snapshot tests/agent/test_dj_cohost.py::test_llm_node_strips_emote_tags_and_sets_mascot_intent tests/bench/test_run_fake.py::test_successful_cell_records_ai_message_observability tests/bench/test_run_fake.py::test_parked_cell_records_ai_message_observability tests/state/test_deck_vision.py::test_vision_read_records_ai_message_observability tests/state/test_deck_vision.py::test_vision_error_records_parked_ai_message tests/learn/test_runtime_evidence_grounding.py::test_runtime_logs_learn_milestones_to_session_event_sink tests/learn/test_observer_boot_wiring.py::test_observer_tutor_speak_is_logged_as_ai_message tests/debrief/test_tldr_length_60_to_90s.py::test_generate_tldr_text_raises_on_gemini_exception tests/debrief/test_drill_citations_resolve.py::test_generate_drills_raises_after_retries_exhausted
38 passed in 1.64s
```

Deck vision default-off/read/error surface:

```text
uv run pytest -q tests/state/test_deck_vision.py tests/state/test_deck_poller.py -k 'vision or DeckVision or screen'
17 passed, 22 deselected in 0.53s
```

Lint:

```text
uv run ruff check src/vibemix/runtime/ai_observability.py src/vibemix/agent/dj_cohost.py src/vibemix/bench/run.py src/vibemix/state/deck_vision.py src/vibemix/learn/observability.py src/vibemix/learn/runtime.py src/vibemix/__main__.py src/vibemix/debrief/tldr.py src/vibemix/debrief/drills.py scripts/eval/judge.py scripts/verify_ai_observability.py tests/runtime/test_ai_observability.py tests/agent/test_dj_cohost.py tests/eval/test_judge_pro_rubric.py tests/bench/test_run_fake.py tests/state/test_deck_vision.py tests/learn/test_runtime_evidence_grounding.py tests/learn/test_observer_boot_wiring.py tests/debrief/test_tldr_length_60_to_90s.py tests/debrief/test_drill_citations_resolve.py tests/scripts/test_verify_ai_observability.py
All checks passed!
```

Fresh source live-coach artifact session:

```text
uv run python scripts/verify_ai_observability.py --session-dir "$HOME/Library/Application Support/vibemix/recordings/20260531-161228" --require-artifacts --require-deck-mixer --require-engine live_coach --require-surface session --json
```

Result:

```json
{
  "rows": 1,
  "artifact_pairs": 1,
  "move_rows": 0,
  "deck_mixer_rows": 1,
  "checked_artifact_paths": 8,
  "ok": true
}
```

Move-bearing bench/live session:

```text
uv run python scripts/verify_ai_observability.py --session-dir "$HOME/Library/Application Support/vibemix/recordings/20260531-154932" --require-artifacts --require-move-context --require-deck-mixer --require-engine live_coach --require-surface session --json
```

Result:

```json
{
  "rows": 20,
  "artifact_pairs": 20,
  "move_rows": 3,
  "deck_mixer_rows": 20,
  "checked_artifact_paths": 160,
  "ok": true
}
```

Global Viber/Codex artifacts:

```text
uv run python scripts/verify_ai_observability.py --skip-session --require-global --require-artifacts --json
```

Result:

```json
{
  "rows": 17,
  "artifact_pairs": 1,
  "checked_artifact_paths": 35,
  "ok": true
}
```

Debrief backend:

```text
uv run pytest -q tests/debrief
111 passed in 1.27s
```

Debrief UI:

```text
npm --prefix tauri/ui test -- src/debrief/__tests__/drills-panel-shape.spec.ts src/debrief/__tests__/tldr-player.spec.ts src/debrief/__tests__/error-banner.spec.ts src/debrief/__tests__/stripper-roundtrip.spec.ts src/debrief/__tests__/recording-row-debrief-button.spec.ts src/debrief/__tests__/recording-row-debrief-disabled.spec.ts
Test Files  6 passed (6)
Tests  35 passed (35)
```

Whitespace:

```text
git diff --check -- .planning/handoffs/2026-05-31-ai-message-observability-handoff.md src/vibemix/runtime/ai_observability.py src/vibemix/agent/dj_cohost.py src/vibemix/bench/run.py src/vibemix/state/deck_vision.py src/vibemix/learn/observability.py src/vibemix/learn/runtime.py src/vibemix/__main__.py src/vibemix/debrief/tldr.py src/vibemix/debrief/drills.py scripts/eval/judge.py scripts/verify_ai_observability.py tests/runtime/test_ai_observability.py tests/agent/test_dj_cohost.py tests/eval/test_judge_pro_rubric.py tests/bench/test_run_fake.py tests/state/test_deck_vision.py tests/learn/test_runtime_evidence_grounding.py tests/learn/test_observer_boot_wiring.py tests/debrief/test_tldr_length_60_to_90s.py tests/debrief/test_drill_citations_resolve.py tests/scripts/test_verify_ai_observability.py
```

## Boundaries

- No broad staging, no commit, and no product-release claim.
- The move-bearing verifier proof is historical evidence from session
  `20260531-154932`; it still exists and verifies, but it is not a fresh
  packaged-app proof.
- Deck Vision remains default-off as a live source. This package records its
  AI-message artifacts when used; it does not promote it to live deck identity.
- Shared files overlap several packages. Stage by hunk: this package owns the
  AI-message row construction, writers, verifier, and per-surface observability
  hooks.

## Next Required Proof

Before final release packaging, rerun the verifier against the final rebuilt app
or current source while an active controller move is present:

```text
uv run python scripts/verify_ai_observability.py --latest --require-artifacts --require-move-context --require-deck-mixer --require-engine live_coach --require-surface session --json
```
