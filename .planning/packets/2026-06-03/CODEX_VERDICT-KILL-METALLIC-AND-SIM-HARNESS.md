# CODEX VERDICT — KILL-METALLIC-AND-SIM-HARNESS

- Item: FIX-B heartbeat prompt reframe.
- Code SHA: `0ed3cfdc fix(sven): steer heartbeat prompts forward`.
- User value: when a grounded HEARTBEAT payload reaches Sven, the prompt now asks for a forward DJ read Kaan can act on, not texture narration.

## By-Eye Artifact

Rendered real `AICoach.build_prompt(..., diet=True)` for `HEARTBEAT` with a grounded set-progress receipt:

```text
Steady stretch. Turn what you hear into where the set should go next — one forward read Kaan can act on: a move to set up, a layer to bring in, or an energy to hold or lift. Ground it in the audio you just heard. If you cite, copy an exact bracket from grounding_refs; never invent a timestamp from BPM/RMS values. If there is no grounded forward read worth interrupting for, output a single space to stay silent. Saved-set receipt: next up is Pressure Tool. If you mention it, copy these citations exactly: [track:track-next] [mix:set_progress=now->next]. These are grounded receipt contexts, not commands; do not force them if the live sound is more important.
```

The previous describe-bank phrase `ONE sharp observation about the SOUND ... groove, texture` is no longer present in the HEARTBEAT task, and grounded receipt payloads now thread into HEARTBEAT prompts through the existing `_with_grounded_receipts` helper.

## Gates

- `uv run pytest -q tests/state/test_coach.py::test_task_heartbeat_LOAD_BEARING_silence_escape_hatch tests/state/test_coach.py::test_task_heartbeat_includes_grounded_receipt_context tests/runtime/test_speak_gate.py` → 11 passed.
- `uv run ruff check src/vibemix/state/prompt_builder.py tests/state/test_coach.py` → pass.
- Prompt-side grounding review slice: `uv run pytest -q tests/state/test_coach.py tests/runtime/test_speak_gate.py tests/runtime/test_coach.py::test_coach_14_plain_heartbeat_stays_silent tests/agent/test_dj_cohost_linter.py tests/coach/test_citation_linter.py tests/state/test_evidence_registry.py` → 151 passed.
- Full Invariant #2 command from `.claude/skills/vibemix-grounding-review/references/invariant-checks.md` → 110 passed.
- `git diff --check` → pass.

## Notes

- This verdict covers FIX-B only. The scenario/sim harness described in the packet is still unbuilt.
- Plain HEARTBEAT silence remains owned by the existing `decide_speak_gate` path; this change improves the grounded-payload escape hatch when Sven is intentionally allowed to speak.
