# Sven strict gate proof

Date: 2026-06-04

## Change

`scripts/eval/respan_sven_sim.py --strict-sven-gate` is now the standing Sven
regression command. It enables the live persona, live citation grammar, live
response linter parity, the KICK density target, and the quality gate together.

`--strict-sven-gate --gate-only` stays useful as a deterministic routing smoke:
it enables the same scenario set and live-parity flags, but does not require
judged scores because no model generation runs.

## Commands

Unit and lint:

```bash
uv run pytest -q tests/eval/test_respan_sven_sim_quality_gate.py
uv run ruff check scripts/eval/respan_sven_sim.py tests/eval/test_respan_sven_sim_quality_gate.py
```

Results:

```text
19 passed
All checks passed!
```

Deterministic routing smoke:

```bash
uv run python scripts/eval/respan_sven_sim.py --strict-sven-gate --gate-only --no-log
```

Result:

```text
persona: strict_sven_gate=True match_live_persona=True include_citation_grammar=True match_live_linter=True
gate routing: 10/10 matched expectation
```

Full strict Respan gate plus recorded heartbeat judge:

```bash
uv run python scripts/eval/respan_sven_sim.py \
  --strict-sven-gate \
  --out .planning/eval-runs/sven-strict-gate-20260604/respan-sven-sim-strict-gate.json \
  --heartbeat-session "$HOME/Library/Application Support/vibemix/recordings/20260603-175859" \
  --heartbeat-out .planning/eval-runs/sven-strict-gate-20260604/respan-sven-heartbeat-strict-gate.json
```

Results:

```text
sim quality gate: PASS
sim gate routing: 10/10
sim means: friend=3.0 grounded=3.0 earned=2.2 move=2.2 voice=2.6
heartbeat quality gate: PASS
heartbeat means: friend=2.0 grounded=3.0 earned=2.0 move=3.0 voice=2.0
describe-bank census: 20/21 silenced, 1 kept
```

## Artifacts

- `respan-sven-sim-strict-gate.json`
- `respan-sven-heartbeat-strict-gate.json`

## Boundary

This makes the Respan regression number hard to run in the wrong prompt/linter
mode. It does not replace the external sustained driven live-set proof.
