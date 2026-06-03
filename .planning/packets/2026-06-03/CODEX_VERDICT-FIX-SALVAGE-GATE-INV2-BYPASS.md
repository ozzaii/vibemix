# CODEX VERDICT — FIX-SALVAGE-GATE-INV2-BYPASS

- Item: salvage-gate Invariant #2 bypass.
- Code SHA: `f0c5a15f fix(sven): recheck salvaged live claims`.
- User value: Sven no longer lets a fake mixer/control clause reach the mouth just because a separate unsupported harmonic clause was stripped.

## By-Eye Artifact

Direct guard proof for:

```text
You just killed the lows on deck B and brought it under the incoming track. Keep the next blend strictly in key so the breakdown lands clean.
```

with deck lows actually boosted:

```text
{'text': "I can't tell from this live proof whether the control caused that.", 'corrected': True, 'emit_corrected': False, 'policy': 'mixer_contradiction', 'reason': 'low_kill_not_in_mixer_state', ... 'mixer_lows=A:boost+B:boost'}
```

The regression test was RED before the fix: harmonic/no-move combined text left `strictly in key` behind, and the cohost stream yielded the fake low-kill head before the post-stream guard. After the fix, salvaged text falls through the remaining guards and stream output defers once risky claim text appears.

## Gates

- RED proof before code change: new salvage regression tests failed on HEAD.
- `uv run pytest -q tests/state/test_deck_context.py::test_live_claim_guard_harmonic_salvage_falls_through_mixer_low_guard tests/state/test_deck_context.py::test_live_claim_guard_harmonic_salvage_falls_through_no_move_control_guard tests/agent/test_dj_cohost_linter.py::test_live_claim_guard_blocks_mixer_claim_surviving_harmonic_salvage` → 3 passed.
- `uv run pytest -q tests/state/test_deck_context.py::test_live_claim_guard_corrects_mixer_low_kill_contradiction tests/state/test_deck_context.py::test_live_claim_guard_allows_low_kill_when_mixer_agrees tests/state/test_deck_context.py::test_live_claim_guard_salvages_audio_read_before_unsupported_harmonic_advice tests/state/test_deck_context.py::test_live_claim_guard_harmonic_salvage_falls_through_mixer_low_guard tests/state/test_deck_context.py::test_live_claim_guard_harmonic_salvage_falls_through_no_move_control_guard tests/agent/test_dj_cohost_linter.py::test_live_claim_guard_emits_salvaged_audio_read_before_harmonic_advice tests/agent/test_dj_cohost_linter.py::test_live_claim_guard_blocks_mixer_claim_surviving_harmonic_salvage` → 7 passed.
- `uv run pytest -q tests/state/test_deck_context.py tests/agent/test_dj_cohost_linter.py` → 168 passed.
- Full Invariant #2 command from `.claude/skills/vibemix-grounding-review/references/invariant-checks.md` → 111 passed.
- `uv run ruff check src/vibemix/state/deck_context.py src/vibemix/agent/dj_cohost.py tests/state/test_deck_context.py tests/agent/test_dj_cohost_linter.py` → pass.
- `git diff --check` → pass.

## Notes

- The fix does not force `VIBEMIX_CITATION_LINT=on`.
- Harmonic and no-move salvage now rewrite the working text and continue the guard ladder; if no later guard blocks it, the salvaged line still emits as corrected.
- `DJCoHostAgent.llm_node` now defers streaming once accumulated text matches live-claim guard risk, so post-stream strip is not too late for the audience path.
