# Sven kick-density coach-first grounding review

Date: 2026-06-04
Review target: `KICK_DENSITY_SHIFT` prompt wording, scaffold suppression, and the opt-in Respan target.

## Surface

- `src/vibemix/state/prompt_builder.py`
  - `KICK_DENSITY_SHIFT` still grounds only on `prev_density`, `new_density`, and `delta`.
  - The prompt now asks for one forward DJ nudge from the measured density change instead of a sound-description reaction.
  - The silence escape remains: if the measured shift is not worth a call, the model can output a single space.
- `src/vibemix/agent/dj_cohost.py`
  - Existing meta/scaffold suppression now catches `word count` and `grounding refs` scratch fragments.
  - Unclosed quoted meta fragments are no longer repaired into spoken lines.
- `scripts/eval/respan_sven_sim.py`
  - Default 9-scenario routing remains unchanged.
  - `--include-kick-density-target` appends the recorded-set `KICK_DENSITY_SHIFT` weak spot as an explicit quality target.
  - Mean `earned_not_constant >= 2.0` is now part of the strict sim gate.

## Invariant review

- Citation grounding: pass. No citation source, grammar, linter source list, or citation chip allow-list changed.
- Trust-the-audio: pass. The prompt cites only measured kick-density fields already present on `Event.extra`; it does not infer deck identity, source identity, track transition, phrase geometry, or controller causality.
- Rare + earned speak moat: pass. The gate was not loosened. Default sim still has 9 scenarios; opt-in KICK target reports 10/10 routing only when requested.
- Speech source: pass. No TTS provider or cloud speech path changed.
- One socket: pass. No runtime socket code changed; no live sidecar was launched for this review.

## Evidence

- `uv run pytest -q tests/eval/test_respan_sven_sim_quality_gate.py tests/agent/test_dj_cohost_scaffold_repair.py tests/state/test_coach.py::test_task_kick_density_shift_grounds_on_density_delta tests/state/test_coach.py::test_task_kick_density_shift_sparser_density_points_to_space_move`
  - `46 passed`
- `uv run ruff check src/vibemix/agent/dj_cohost.py scripts/eval/respan_sven_sim.py src/vibemix/state/prompt_builder.py tests/agent/test_dj_cohost_scaffold_repair.py tests/state/test_coach.py tests/eval/test_respan_sven_sim_quality_gate.py`
  - clean
- `uv run python scripts/eval/respan_sven_sim.py --gate-only --include-kick-density-target --no-log`
  - gate routing `10/10`
- `uv run python scripts/eval/respan_sven_sim.py --match-live-persona --include-kick-density-target --require-quality --out .planning/eval-runs/sven-kick-density-coachfirst-20260604/respan-sven-sim-kick-density-coachfirst-live-persona-strict-quality.json`
  - quality gate PASS
  - gate routing `10/10`
  - generated means: friend `2.62`, grounded `3.0`, earned `2.5`, move `2.38`, voice `2.62`
  - KICK target: friend `2`, grounded `3`, earned `2`, move `2`, voice `2`
- `uv run python scripts/eval/respan_sven_heartbeat_judge.py --session "$HOME/Library/Application Support/vibemix/recordings/20260603-175859" --events ALL --describe-bank-census --concurrency 4 --require-quality --min-judged 1 --out .planning/eval-runs/sven-kick-density-coachfirst-20260604/respan-sven-heartbeat-kick-density-coachfirst-strict-quality.json`
  - quality gate PASS
  - friend `2.0`, grounded `3.0`, earned `2.0`, move `3.0`, voice `2.0`
  - describe-bank census: `20/21` silenced, `1` kept

## Boundary

This review proves the current-source prompt target and the recorded-set threshold. The heartbeat judge replays old `response.txt` lines, so it is a standing real-set threshold check, not proof that the historical KICK line would regenerate differently. A sustained driven live set remains the outer Sven validation gate.
