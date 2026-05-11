---
phase: 04-livekit-cascade-agent-pivot
plan: 01
type: summary
status: complete
completed_at: 2026-05-11
requirements_covered:
  - ARCH-03  # partial — model layer
  - ARCH-05  # TTS chain
wave_commit: 28f5f09
---

# Plan 04-01 — Agent persona + config + LLM factory + TTS chain (OpenRouter monkey-patch) — Summary

## What Shipped

The model layer of Phase 4's cascade agent — pure-string + pure-factory work
with no internal cross-deps:

- `src/vibemix/agent/persona.py` — `SYSTEM_INSTRUCTION` byte-identical to
  `cohost_v4.py:150-213` (8358 chars). Verified via AST extraction in test
  `PERSONA-02`.
- `src/vibemix/agent/config.py` — agent-layer constants (LLM_MODEL,
  TTS_MODEL, TTS_FALLBACK_MODEL, OPENROUTER_TTS_MODEL, VOICE, INPUT_DEVICE,
  OUTPUT_DEVICE, MIC_DEVICE) verbatim from v4:97-104.
- `src/vibemix/agent/llm_factory.py` — `build_llm(api_key) -> google_plugin.LLM`
  verbatim from v4:1983-1989.
- `src/vibemix/agent/tts_chain.py` — module-load OpenRouter monkey-patch
  (`_openai_tts_mod.AUDIO_STREAM_MODELS.add("google/gemini-3.1-flash-tts-preview")`)
  + `build_tts_chain(gemini_api_key, openrouter_api_key=None) -> FallbackAdapter`.
- `src/vibemix/agent/__init__.py` — package surface exporting all 10 names.
- `pyproject.toml` — `livekit-plugins-openai>=1.5.8` promoted from transitive
  to explicit. `websockets>=13.0` loosened (was `>=16.0`) because
  `livekit-plugins-openai 1.5.8` requires `openai[realtime]` with
  `websockets<16`; resolver-time conflict, runtime-fine. uv.lock refreshed.

## Files

Created (11):
- `src/vibemix/agent/__init__.py`
- `src/vibemix/agent/config.py`
- `src/vibemix/agent/persona.py`
- `src/vibemix/agent/llm_factory.py`
- `src/vibemix/agent/tts_chain.py`
- `tests/agent/__init__.py`
- `tests/agent/conftest.py`
- `tests/agent/test_persona.py`
- `tests/agent/test_config.py`
- `tests/agent/test_llm_factory.py`
- `tests/agent/test_tts_chain.py`

Modified (2):
- `pyproject.toml` — added `livekit-plugins-openai>=1.5.8`, loosened
  `websockets>=13.0`.
- `uv.lock` — refreshed (websockets pinned to 15.0.1 by resolver).

## Tests Added

16 tests under `tests/agent/`:
- PERSONA-01/02/03 (3 tests) — persona type, byte-equality vs v4 via AST,
  anti-hallucination substrings present.
- CONFIG-01 + PKG-01 (3 tests) — config constant values + package re-exports.
- LLM-01/02 (2 tests) — `build_llm` kwargs match v4:1983-1989; signature is
  `build_llm(api_key: str)`.
- TTS-01..06 (6 tests) — monkey-patch is module-load invariant, with-OR has
  3 chain entries, without-OR has 2 (None / empty str both treated the same),
  OpenRouter TTS kwargs match v4:1994-2001 (including the em-dash in
  instructions), gemini_native TTS kwargs match v4:2003-2014.
- PKG-02 + PYPROJECT-01 (2 tests) — `build_tts_chain` exported, pyproject
  contains the explicit `livekit-plugins-openai` dep.

Full suite: 286 pass (270 baseline + 16 new agent tests).

## Architectural Notes

- **OpenRouter monkey-patch ordering invariant.** The patch lives at
  `tts_chain.py:23` between `from livekit.plugins.openai import tts as
  _openai_tts_mod` (line 19) and `from livekit.plugins.google.beta import
  gemini_tts as gemini_native_tts` (line 25). It runs as a module-load side
  effect — no `build_tts_chain()` call is required for the patch to apply.
  Test TTS-01 pins this invariant and would fail if the patch ever drifted
  into a factory body.
- **Persona is byte-identical to v4.** Test `PERSONA-02` extracts the v4
  body via `ast` (not line-number slicing) so the test is robust against
  future v4 file growth above the SYSTEM_INSTRUCTION assignment. Length
  pin: 8358 chars.
- **`build_llm` and `build_tts_chain` accept api keys as parameters.** This
  is the Phase 5 seam — when the FastAPI proxy lands, `main()` will pass
  proxy-issued JWTs instead of raw env keys; the factory bodies don't change.
- **`livekit-plugins-openai` is now explicit.** Promoted from transitive dep
  (it was pulled in by `livekit-agents`) to a top-level requirement because
  the monkey-patch makes us load-bearing on its module structure
  (`livekit.plugins.openai.tts.AUDIO_STREAM_MODELS`). PYPROJECT-01 pins this.

## Deviation: websockets version constraint loosened

- v4 / Phase 2 pyproject declared `websockets>=16.0`. Adding
  `livekit-plugins-openai>=1.5.8` as an explicit dep triggers a resolver
  conflict because the plugin pulls `openai[realtime]>=2` which constrains
  `websockets>=13,<16`. The runtime venv already had `websockets 16.0`
  installed and working (openai 2.36.0 base package doesn't require
  websockets — only the `[realtime]` extra does).
- Fix: loosened to `websockets>=13.0`; resolver downgraded to 15.0.1.
  No code in vibemix actually uses websockets 16-specific APIs (Phase 4-03
  ws_bus uses only the `serve` + send/recv surface).
- Full suite still green at 15.0.1.

## Carry-Forward

- 04-02: `DJCoHostAgent(Agent)` + `PlaybackQueueAudioOutput(voice_io.AudioOutput)`.
  Imports `SYSTEM_INSTRUCTION` and `LLM_MODEL` from this package.
- 04-03: `coach_loop` / `diag_loop` / `ws_broadcast` runtime loops.
- 04-04: `__main__.py` consumes `build_llm` + `build_tts_chain` and assembles
  the AgentSession.
