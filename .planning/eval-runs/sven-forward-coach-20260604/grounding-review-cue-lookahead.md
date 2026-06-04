# Sven cue-lookahead grounding review

Date: 2026-06-04
Review target: cue-lookahead forward coaching for move-less `PHASE` / `TRACK_CHANGE`
Runtime commit under review: `bb708077` (`fix(sven): coach move-less cue lookahead`)
Current proof head: `57bebb35` (`test(sven): record heartbeat Respan census`)

## Surface

- `src/vibemix/runtime/suggestion_voice.py`
  - `build_next_suggestion_voice_line(None, ..., state=state)` delegates to the cue-lookahead receipt.
  - The receipt requires `state.next_phrase_cue_id`, `phrase_position_confidence >= 0.7`, and `0 < next_phrase_at - set_seconds <= 64`.
  - It writes `("cue", cue_id, next_phrase_at)` before exposing `[cue:<id>]`.
- `src/vibemix/runtime/coach.py`
  - `PHASE`, `TRACK_CHANGE`, and `TRANSITION_OPPORTUNITY` can attach a forward receipt.
  - Without a grounded suggestion/cue receipt, no forward payload is added.
- `src/vibemix/prompts/matrix.py`
  - The Sven persona has one positive cue-lookahead example.
- `src/vibemix/agent/dj_cohost.py`
  - Runtime speech still passes through the existing silence, slop, citation, and TTS cleanup gates.

## Invariant review

- Citation grounding: pass.
  - No new citation source was introduced. `cue` already exists in `EvidenceRegistry`, citation grammar, linter, and citation-strip allow-list.
  - The new receipt registers the exact cue id before emitting `[cue:<id>]`.
  - `tests/runtime/test_suggestion_voice.py` checks CitationLinter validity for the emitted cue receipt.
- Trust-the-audio / no speculative phrasing: pass.
  - The branch reads phrase/cue facts from `MusicState` fields produced upstream; it does not estimate phrases itself.
  - The branch abstains below confidence floor, outside the ETA window, without cue id, and without state.
- Rare + earned speak moat: pass for the scoped branch.
  - The gate remains `9/9` in the live-persona Respan sim.
  - Idle `HEARTBEAT` and `LAYER_ARRIVAL` stay silent in the sim.
  - Move-less `PHASE` / `TRACK_CHANGE` speak only with a grounded cue lookahead in the sim fixtures.
- One socket / live runtime: no new socket or sidecar code touched.
- Speech source: no TTS provider or cloud speech code touched; live speech remains on the existing local MOSS path.

## Evidence

- `uv run pytest -q tests/runtime/test_suggestion_voice.py tests/runtime/test_speak_gate.py tests/agent/test_dj_cohost_linter.py tests/state/test_evidence_registry.py tests/coach/test_citation_linter.py tests/prompts/test_negative_dict.py tests/state/test_hype_anti_slop.py tests/state/test_coach_anti_slop.py`
  - `129 passed`
- `uv run pytest -q tests/learn/test_no_speculative_phrase.py tests/state/test_event_detector.py tests/learn/test_no_new_ws_port.py`
  - `54 passed`
- `uv run ruff check src/vibemix/runtime/suggestion_voice.py src/vibemix/runtime/coach.py src/vibemix/runtime/speak_gate.py src/vibemix/agent/dj_cohost.py src/vibemix/prompts/matrix.py scripts/eval/respan_sven_sim.py scripts/eval/respan_sven_heartbeat_judge.py tests/runtime/test_suggestion_voice.py`
  - clean
- `.planning/eval-runs/sven-forward-coach-20260604/respan-sven-sim-live-persona.json`
  - `match_live_persona=true`, `include_citation_grammar=true`
  - gate `9/9`
  - cue `PHASE`: `3/3/3/3/3`
  - cue `TRACK_CHANGE`: `2/3/2/2/2`
  - generated-line means: friend `2.14`, grounded `3.0`, earned `2.0`, move `2.0`, voice `2.29`
- `.planning/eval-runs/sven-forward-coach-20260604/respan-sven-heartbeat-describe-bank-census.json`
  - recorded set `20260603-175859`
  - no-payload describe-bank census silenced `20/21`, kept `1`
  - kept row means: friend `2.0`, grounded `3.0`, earned `2.0`, move `3.0`, voice `2.0`

## Boundary

This review proves the cue-lookahead branch against static/unit invariants plus Respan sim and recorded-set census artifacts. It does not replace the final live driven-set proof: a sustained current-source set with real `invocations/` remains the outer validation gate for the full Sven voice lane.
