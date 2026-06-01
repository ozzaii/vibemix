# CODEX_READY — Audio Vibe Contract Prompt Guard

Date: 2026-06-01
Package: Package 8E - Audio Vibe Contract Prompt Guard
Classification: LAND, prompt-side guard only

## Summary

This package keeps live audio magical but honest. The prompt now treats audio as
a grounded listener/vibe signal for texture, energy, motion, density, mood, and
silence/music presence. It explicitly forbids using audio alone as proof of
track identity, deck identity, hidden sources, or EQ/fader/filter/cue/knob
causality.

This is the prompt-side companion to Package 8D. Package 8D is still the hard
runtime backstop: unsafe live-claim guard hits must stay silent instead of
becoming spoken fallback text.

## Files

- `src/vibemix/prompts/matrix.py`
- `tests/prompts/test_matrix.py`

## Source Evidence

- `AUDIO_VIBE_CONTRACT_BLOCK` adds the live-mode contract in
  `src/vibemix/prompts/matrix.py`.
- `HYPE_INTERMEDIATE` now says ears are truth for listener read, not proof of
  identity/deck/control causality.
- `build_system_instruction()` appends the audio-vibe contract only on the
  default tag-DSL path, preserving the existing double-opt-out byte-identity
  behavior.
- `tests/prompts/test_matrix.py` asserts the default path includes the contract
  and the double-opt-out path excludes it.

## Verification

- `uv run pytest -q tests/prompts/test_matrix.py -k 'audio_vibe or double_opt_out or grammar'`
  passed: 20 passed, 76 deselected.
- `uv run ruff check src/vibemix/prompts/matrix.py tests/prompts/test_matrix.py`
  passed.

## Boundaries

- This does not prove a live model will never regress. It lowers prompt pressure
  toward fake causality; Package 8D and the runtime canaries remain the hard
  enforcement/proof layer.
- This does not claim current signed/package artifacts contain the change.
- No staging, commit, or product-release claim was made.
