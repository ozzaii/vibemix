# Sven persona / grounding unit gate proof

Date: 2026-06-04
Branch: `ux-redesign-impeccable`
Current HEAD before this proof artifact: `add11bdb test(eval): prove cue snap on persisted Rekordbox grid`

## Scope

This proves the five Sven persona/grounding unit tests called out as a RED gate
are green on current HEAD. No source changes were needed in this pass.

## Exact five-test gate

Command:

```bash
uv run pytest -q \
  tests/agent/test_persona.py::test_persona_02_has_required_section_markers \
  tests/agent/test_persona.py::test_persona_03_anti_hallucination_substrings_present \
  tests/agent/test_hype_prompt_grounding.py::test_intermediate_hype_cell_is_v4_grounded \
  tests/agent/test_dj_cohost.py::test_llm_node_attaches_configured_deck_audio_parts_on_mix_move \
  tests/agent/test_dj_cohost.py::test_llm_node_03b_places_deck_audio_map_next_to_audio_part
```

Result:

```text
.....                                                                    [100%]
5 passed in 1.60s
```

## Surrounding file gate

Command:

```bash
uv run pytest -q \
  tests/agent/test_persona.py \
  tests/agent/test_hype_prompt_grounding.py \
  tests/agent/test_dj_cohost.py
```

Result:

```text
...................................................................      [100%]
67 passed in 1.35s
```

## Boundary

This is unit-level proof for the persona/grounding gate only. It does not replace
the Respan sim, recorded-set heartbeat judge, or the external sustained live-set
ear proof required by the Sven goal.
