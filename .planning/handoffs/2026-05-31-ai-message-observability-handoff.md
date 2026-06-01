# AI Message Observability Handoff - 2026-05-31

## Goal

Every assistant-facing AI message should be logged in a single inspectable shape,
saved with recoverable artifacts where the engine has a prompt/response body,
and tied to the deck/move evidence that made the turn happen.

This packet covers the current-source implementation, a fresh live runtime proof
from `20260531-161228`, and the move-bearing saved bench session
`20260531-154932`.

## Canonical Row

- Builder: `src/vibemix/runtime/ai_observability.py:217`
  `build_ai_message_record(...)`
- Session writer: `src/vibemix/runtime/ai_observability.py:281`
  `record_session_ai_message(...)`
- Session prompt/response artifacts:
  `src/vibemix/runtime/ai_observability.py:308`
  `_write_session_ai_artifacts(...)`
- Global writer: `src/vibemix/runtime/ai_observability.py:350`
  `append_global_ai_message(...)`

Important row fields:

- `engine`, `surface`, `direction`, `response_id`, `provider`, `model`
- `message`, `message_chars`, `prompt_chars`, `response_chars`
- `citation.count/action/valid/reason`
- `moves.recent_moves`, `moves.event_moves`, `moves.deck_mixer`,
  `moves.audio_delta`, `moves.live_context_*`
- `tools_used`, `tool_trace`, `move_grades`
- `artifacts.*`
- `extra.*`

## Storage

Session rows:

- Event row lands in the active recorder's `events.jsonl` as
  `kind="ai_message"`.
- When `prompt=` / `response=` is passed to `record_session_ai_message`,
  artifacts are written under:
  `recordings/<session>/ai_messages/artifacts/<response_id>/`.
- Artifact keys:
  `session_prompt_path`, `session_response_path`, `session_meta_path`.
- Real replay proof uses `RecordingsIndex.read_events(...)` in
  `tests/runtime/test_ai_observability.py:75`.

Global/non-session rows:

- Rows land under `<app_data>/ai_messages/ai_messages.jsonl`.
- Prompt/response/meta artifacts land under:
  `<app_data>/ai_messages/artifacts/<response_id>/`.
- Artifact keys:
  `prompt_path`, `response_path`, `meta_path`.
- `meta.json` now includes its own `artifacts.meta_path`; see
  `src/vibemix/runtime/ai_observability.py:410`.

## Covered Surfaces

| Surface | Writer | Saved Context |
| --- | --- | --- |
| Live coach Gemini / OpenRouter-through-cohost | `src/vibemix/agent/dj_cohost.py:3159` | Session `ai_message` row plus full final prompt/response artifacts at `src/vibemix/agent/dj_cohost.py:3173`; prompt-time mixer snapshot is taken before model latency. |
| Bench sweeps | `src/vibemix/bench/run.py:155` | Global row with prompt/response artifact; success, no-text, and exception cells are all recorded. |
| Eval Gemini judges | `scripts/eval/judge.py:133` | Global row for Pro/Flash judge responses and failures, with full judge prompt/raw response artifacts, `engine="eval_judge"`, `surface="eval_judge_pro"` / `eval_judge_flash`, parsed verdict metadata, and move context derived from `MIX_MOVE` evidence when present. |
| Deck vision | `src/vibemix/state/deck_vision.py:212` and `:229` | Global row for success and error, event `deck_vision_read`, plus prompt/response/error artifacts. |
| Debrief TLDR and TTS | `src/vibemix/debrief/tldr.py:119` | Global rows for success and parked failure cases; TTS stores spoken text and PCM-byte response marker. |
| Debrief drills | `src/vibemix/debrief/drills.py:207` | Global rows for model errors, parse failures, invalid citations, and valid drills. |
| Viber / Codex curate, build-set, chat | `src/vibemix/library/codex_curate.py:615` | Global row with Codex reply/rationale/error, tool trace, tools used, track ids, move grades, playlist/export artifacts, and live context for chat. |
| Learn runtime tutor | `src/vibemix/learn/observability.py:25` via `src/vibemix/learn/runtime.py:1288` | Session `learn_tutor_speak` plus `ai_message` row, `engine="learn_tutor"`, `provider="authored_fixture"`, source `learn_runtime`. |
| Learn observer tutor (exemplar + recital) | `src/vibemix/learn/observability.py:25` via `src/vibemix/__main__.py:2147` | Session `learn_tutor_speak` plus `ai_message` row, source `learn_observer`, covering `LearnTutorSpeak.make(...)` in exemplar and recital observers. |

Embedding calls in `src/vibemix/library/embed.py` are intentionally outside
`ai_message`; they produce vectors, not assistant text.

## Guards

- Static model-generation coverage:
  `tests/runtime/test_ai_observability.py:215`
  Scans both `src/vibemix/` and `scripts/eval/`.
- Static non-model assistant coverage:
  `tests/runtime/test_ai_observability.py:248`
- Real session artifact + replay/browser readback:
  `tests/runtime/test_ai_observability.py:75`,
  `tests/runtime/test_ai_observability.py:116`
- Global artifact/meta self-reference:
  `tests/runtime/test_ai_observability.py:155`
- Live cohost move/deck artifact proof:
  `tests/agent/test_dj_cohost.py:260`
- Prompt-time mixer snapshot proof:
  `tests/agent/test_dj_cohost.py:296`
- Bench success/parked rows:
  `tests/bench/test_run_fake.py:63`, `tests/bench/test_run_fake.py:93`
- Eval judge success/error rows:
  `tests/eval/test_judge_pro_rubric.py:150`,
  `tests/eval/test_judge_pro_rubric.py:192`
- Deck vision success/error rows:
  `tests/state/test_deck_vision.py:110`, `tests/state/test_deck_vision.py:196`
- Learn runtime row:
  `tests/learn/test_runtime_evidence_grounding.py:139`
- Learn observer boot row:
  `tests/learn/test_observer_boot_wiring.py:40`
- Debrief parked failures:
  `tests/debrief/test_tldr_length_60_to_90s.py:80`,
  `tests/debrief/test_drill_citations_resolve.py:115`
- Mixer low-kill contradiction guard:
  `tests/state/test_deck_context.py:1947`,
  `tests/state/test_deck_context.py:1964`
- Post-run verifier:
  `scripts/verify_ai_observability.py:151`,
  `scripts/verify_ai_observability.py:161`,
  `scripts/verify_ai_observability.py:177`,
  `scripts/verify_ai_observability.py:208`,
  `scripts/verify_ai_observability.py:286`
- Verifier tests:
  `tests/scripts/test_verify_ai_observability.py`

## Fresh Runtime Proof

Session:

```text
/Users/ozai/Library/Application Support/vibemix/recordings/20260531-161228/events.jsonl
```

Launch command:

```bash
VIBEMIX_AI_OBSERVABILITY=1 VIBEMIX_DEV_SIDECAR=1 VIBEMIX_LOCAL_TTS=0 \
  uv run python -m vibemix
```

Trigger command:

```bash
uv run python - <<'PY'
import asyncio, json, websockets

async def main():
    async with websockets.connect("ws://127.0.0.1:8765") as ws:
        await ws.send(json.dumps({"action": "trigger"}))
        print((await ws.recv())[:1000])

asyncio.run(main())
PY
```

Verifier command:

```bash
uv run python scripts/verify_ai_observability.py \
  --session-dir "$HOME/Library/Application Support/vibemix/recordings/20260531-161228" \
  --require-artifacts \
  --require-deck-mixer \
  --require-engine live_coach \
  --require-surface session \
  --json
```

Verifier result:

```json
{
  "total_events": 11,
  "rows": 1,
  "artifact_pairs": 1,
  "move_rows": 0,
  "deck_mixer_rows": 1,
  "checked_artifact_paths": 8,
  "engines": ["live_coach"],
  "surfaces": ["session"],
  "ok": true,
  "errors": []
}
```

Exact `events.jsonl` lines for the fresh proof:

- Line 2: `event` row for `MANUAL` with full deck/source/audio context.
- Line 6: `llm_invoke` row for `MANUAL`, prompt path
  `invocations/0001_161250_MANUAL/prompt.txt`.
- Line 8: `citation_count` row for response `0001_161250`.
- Line 10: `ai_message` row for response `0001_161250`, message
  `"I'm listening."`, `engine="live_coach"`, `surface="session"`,
  `stop_reason="emit"`, `moves.deck_mixer.connected=true`, and session artifact
  paths under `ai_messages/artifacts/0001_161250/`.
- Line 11: `llm_to_tts_delta_ms` row for response `0001_161250`.

This fresh proof was intentionally a silent manual trigger, so
`moves.recent_moves=[]` and `move_rows=0`. Move-bearing proof is below.

## Current Bench Proof

Session:

```text
/Users/ozai/Library/Application Support/vibemix/recordings/20260531-154932/events.jsonl
```

Verifier command:

```bash
uv run python scripts/verify_ai_observability.py \
  --session-dir "$HOME/Library/Application Support/vibemix/recordings/20260531-154932" \
  --require-artifacts \
  --require-move-context \
  --require-deck-mixer \
  --require-engine live_coach \
  --require-surface session \
  --json
```

Verifier result:

```json
{
  "total_events": 175,
  "rows": 20,
  "artifact_pairs": 20,
  "move_rows": 3,
  "deck_mixer_rows": 20,
  "checked_artifact_paths": 160,
  "engines": ["live_coach"],
  "surfaces": ["session"],
  "ok": true,
  "errors": []
}
```

Global/non-session verifier result from the same refresh:

```json
{
  "rows": 1,
  "artifact_pairs": 1,
  "checked_artifact_paths": 3,
  "engines": ["codex"],
  "surfaces": ["viber_chat"],
  "ok": true
}
```

Fresh-session plus global verifier result:

```bash
uv run python scripts/verify_ai_observability.py \
  --latest-with-ai-message \
  --require-artifacts \
  --require-deck-mixer \
  --require-engine live_coach \
  --require-surface session \
  --require-global \
  --json
```

```json
{
  "session": {
    "session_dir": "/Users/ozai/Library/Application Support/vibemix/recordings/20260531-161228",
    "rows": 1,
    "artifact_pairs": 1,
    "deck_mixer_rows": 1,
    "checked_artifact_paths": 8,
    "engines": ["live_coach"],
    "surfaces": ["session"]
  },
  "global": {
    "rows": 1,
    "artifact_pairs": 1,
    "checked_artifact_paths": 3,
    "engines": ["codex"],
    "surfaces": ["viber_chat"]
  },
  "ok": true,
  "errors": []
}
```

Exact `events.jsonl` lines for the session rows:

- `ai_message`: 10, 18, 27, 35, 44, 52, 63, 71, 80, 88, 97, 107, 115, 122,
  129, 138, 146, 155, 165, 174.
- `llm_invoke`: 6, 16, 23, 33, 40, 50, 57, 69, 76, 86, 93, 103, 113, 120,
  127, 134, 144, 151, 160, 170.
- `citation_count`: 8, 17, 25, 34, 42, 51, 59, 70, 78, 87, 95, 105, 114,
  121, 128, 136, 145, 153, 162, 172.
- `deck_audio_parts_skipped`: 3, 13, 20, 30, 37, 47, 54, 66, 73, 83, 90, 100,
  110, 117, 124, 131, 141, 148, 157, 167. Every row has
  `reason="no_deck_audio_buffers"`.

Forensic examples from the recorded bench:

- Line 27 / response `0003_155029`: emitted 284 chars including a filter
  instruction, while `moves.recent_moves=[]`, `moves.deck_mixer.connected=true`,
  `xfader=64`, `deck_confidence=0.0`, and both deck mixers show closed volume,
  flat EQ/filter, `play=false`. This proves the observability layer can diagnose
  unsupported control talk after the fact.
- Lines 146, 155, and 165 / responses `0017_155821`, `0018_155843`, and
  `0019_155910`: preserve recent move evidence as `B_jog nudge back` with ages
  `5.7`, `5.9`, and `2.4` seconds, plus the same prompt-time deck mixer snapshot.
- Line 138 / response `0016_155751`: emitted 223 chars with an EQ instruction
  while recent moves were empty; again the row preserves the mismatch.
- All 20 `ai_message` rows preserve `extra.deck_audio_parts=0`; matching
  `deck_audio_parts_skipped` rows show the reason is `no_deck_audio_buffers`.

## Verified Commands

Focused source verification:

```bash
uv run pytest -q tests/scripts/test_verify_ai_observability.py tests/runtime/test_ai_observability.py tests/eval/test_judge_pro_rubric.py tests/agent/test_dj_cohost.py::test_llm_node_logs_ai_message_observability_with_moves tests/agent/test_dj_cohost.py::test_llm_node_ai_message_uses_prompt_time_mixer_snapshot tests/bench/test_run_fake.py::test_successful_cell_records_ai_message_observability tests/bench/test_run_fake.py::test_parked_cell_records_ai_message_observability tests/state/test_deck_vision.py::test_vision_read_records_ai_message_observability tests/state/test_deck_vision.py::test_vision_error_records_parked_ai_message tests/learn/test_runtime_evidence_grounding.py::test_runtime_logs_learn_milestones_to_session_event_sink tests/learn/test_observer_boot_wiring.py::test_observer_tutor_speak_is_logged_as_ai_message tests/debrief/test_tldr_length_60_to_90s.py::test_generate_tldr_text_raises_on_gemini_exception tests/debrief/test_drill_citations_resolve.py::test_generate_drills_raises_after_retries_exhausted
```

Observed result from this refresh after adding eval judge observability: `37 passed`.

Ruff:

```bash
uv run ruff check src/vibemix/runtime/ai_observability.py src/vibemix/agent/dj_cohost.py src/vibemix/bench/run.py src/vibemix/state/deck_vision.py src/vibemix/learn/observability.py src/vibemix/learn/runtime.py src/vibemix/__main__.py src/vibemix/debrief/tldr.py src/vibemix/debrief/drills.py scripts/eval/judge.py scripts/verify_ai_observability.py tests/runtime/test_ai_observability.py tests/agent/test_dj_cohost.py tests/eval/test_judge_pro_rubric.py tests/bench/test_run_fake.py tests/state/test_deck_vision.py tests/learn/test_runtime_evidence_grounding.py tests/learn/test_observer_boot_wiring.py tests/debrief/test_tldr_length_60_to_90s.py tests/debrief/test_drill_citations_resolve.py tests/scripts/test_verify_ai_observability.py
```

Diff check:

```bash
git diff --check -- .planning/handoffs/2026-05-31-ai-message-observability-handoff.md src/vibemix/runtime/ai_observability.py src/vibemix/agent/dj_cohost.py src/vibemix/bench/run.py src/vibemix/state/deck_vision.py src/vibemix/learn/observability.py src/vibemix/learn/runtime.py src/vibemix/__main__.py src/vibemix/debrief/tldr.py src/vibemix/debrief/drills.py scripts/eval/judge.py scripts/verify_ai_observability.py tests/runtime/test_ai_observability.py tests/agent/test_dj_cohost.py tests/eval/test_judge_pro_rubric.py tests/bench/test_run_fake.py tests/state/test_deck_vision.py tests/learn/test_runtime_evidence_grounding.py tests/learn/test_observer_boot_wiring.py tests/debrief/test_tldr_length_60_to_90s.py tests/debrief/test_drill_citations_resolve.py tests/scripts/test_verify_ai_observability.py
```

## Remaining Release Proof

Current source has now produced a fresh live-coach `ai_message` row with
artifacts and deck mixer context. The saved bench session also proves recent
move capture when controller moves are present. Before tagging a packaged
release, repeat the same verifier against the packaged app build, ideally during
an active controller move:

```bash
uv run python scripts/verify_ai_observability.py \
  --latest-with-ai-message \
  --require-artifacts \
  --require-move-context \
  --require-deck-mixer \
  --require-engine live_coach \
  --require-surface session
```

The verifier must report `OK`. It checks newest-session `events.jsonl`,
`kind="ai_message"`, existing artifact files, move context, and deck mixer
evidence. The required engine/surface flags are important: they prevent a parked
or unrelated row from satisfying the live-coach release proof.

For Viber/Codex/global rows, also run:

```bash
uv run python scripts/verify_ai_observability.py \
  --skip-session \
  --require-global \
  --require-artifacts \
  --require-engine codex \
  --require-surface viber_chat
```
