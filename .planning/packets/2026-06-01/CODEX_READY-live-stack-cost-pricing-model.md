# CODEX_READY: Live Stack Cost And Pricing Model

Date: 2026-06-01
Author: Codex
Package: 10 - Live Stack Cost And Pricing Model
Decision: LAND
Suggested commit: `feat(library-cost): add live stack budget model`

## Summary

This package is ready to land as an internal, reproducible live-stack cost model.

It adds a source-tagged pricing table, a composed per-reaction to per-session to
fleet cost model, and a `vibemix library budget --stack live` CLI that prints both
human and JSON reports. The important product result is not "this is external
pricing copy"; it is "we can now reproduce the bill, see assumptions, and keep
unverified rows visibly unverified."

The package is intentionally conservative around financial claims. Cartesia Sonic
is the live TTS pick in this scenario, but its public page is not a clean
per-character SKU. The row remains `verified=False`, the CLI marks it
`! UNVERIFIED`, and the docs say not to use the headline figures as external
pricing copy until account billing confirms the effective rate.

## Files In Package

- `src/vibemix/library/cost.py`
- `src/vibemix/library/pricing.py`
- `src/vibemix/library/budget.py`
- `src/vibemix/__main__.py`
- `src/vibemix/llm/_router_config.py`
- `tests/library/test_cost.py`
- `tests/library/test_pricing.py`
- `tests/e2e/test_phase_41_latency_stack_integration.py`
- `tests/llm/test_model_router.py`
- `docs/pricing/live-stack-economics.en.md`
- `docs/pricing/live-stack-economics.it.md`

Stage note: `src/vibemix/__main__.py` is a shared file with unrelated dirty
hunks. Stage only the `library budget --stack live` parser/handler hunks for this
package; keep live TTS shutdown and other runtime hunks in their own packages.

## LAND Criteria

- Pricing rows carry source URL, source date, verified flag, and concrete rates.
- Gemini rows resolve through `model_router`, keeping Gemini literals confined to
  `_router_config.py`.
- Candidate live-brain aliases are router-backed and remain Gemini-only.
- The live-stack cost model composes brain, listening, TTS, Viber, and LiveKit legs.
- The CLI prints human and JSON reports with echoed assumptions.
- The sensitivity table preserves unverified vendor status.
- Docs identify the model as internal and forbid external use of unverified Sonic
  headline figures.

## Source Evidence

### Source-tagged pricing table

- `src/vibemix/library/pricing.py:54-75` defines `PriceRow`, including
  `source_url`, `source_date`, `verified`, and separate fields for LLM, TTS, and
  STT billing shapes.
- `src/vibemix/library/pricing.py:77-82` builds Gemini rows by resolving router
  aliases, so Gemini model literals stay in the allowlisted router config.
- `src/vibemix/library/pricing.py:84-177` defines the live-brain, TTS, Viber, and
  STT rows consumed by the live budget model.
- `src/vibemix/library/pricing.py:166-176` keeps `sonic-3` as `verified=False`
  with `LEGACY_DERIVED` notes explaining that public billing still needs account
  confirmation.
- `src/vibemix/library/pricing.py:230-243` exposes model-id and router-path lookup
  helpers that fail explicitly on unknown rows.

### Cost composition and sensitivity

- `src/vibemix/library/cost.py:47-78` blends cached/fresh input rates and charges
  output separately.
- `src/vibemix/library/cost.py:81-126` handles both TTS billing shapes and the
  Gemini-audio-vs-dedicated-STT listening fork.
- `src/vibemix/library/cost.py:132-171` defines the live-stack, turn, and usage
  assumptions.
- `src/vibemix/library/cost.py:203-271` composes brain, listen, TTS, Viber, and
  LiveKit legs into per-session, per-DJ-month, and fleet totals.
- `src/vibemix/library/cost.py:274-355` builds the sensitivity rows and carries
  each candidate row's `verified` flag forward.
- `src/vibemix/library/cost.py:358-421` returns a JSON-serializable report with
  stack, assumptions, legs, totals, dominant leg, and sensitivity.

### CLI and router integration

- `src/vibemix/__main__.py:2969-3026` adds the `library budget` `--stack live`
  parser options.
- `src/vibemix/__main__.py:6415-6484` implements the live-stack budget CLI,
  including actionable error output, JSON mode, human table output, and
  `! UNVERIFIED` flags in the sensitivity table.
- `src/vibemix/__main__.py:6487-6490` routes `--stack live` to the new handler
  while preserving the legacy embedding-budget mode.
- `src/vibemix/llm/_router_config.py:46-59` adds the two candidate live-brain
  router aliases and keeps Viber/DeepSeek out of Gemini router paths.
- `tests/e2e/test_phase_41_latency_stack_integration.py:115-121` pins those
  candidate aliases in the integration router table and keeps the Gemini 3.1
  Flash Live model isolated under `spikes/`.

### Documentation boundary

- `docs/pricing/live-stack-economics.en.md:3-8` labels the document as an internal
  cost model and says it is not external pricing copy.
- `docs/pricing/live-stack-economics.en.md:45-51` shows the Cartesia row as
  legacy-derived/unverified.
- `docs/pricing/live-stack-economics.en.md:99-101` explicitly forbids using the
  headline as external pricing copy until billing confirms the Sonic conversion.

## Current External Spot-Check

Checked official pages during this verification pass:

- Google Gemini pricing page currently lists `gemini-3.5-flash` Standard at
  $1.50 input, $9.00 output, and $0.15 cached input per 1M tokens, matching the
  `live_coach` row.
- The same page lists `gemini-3.1-flash-tts-preview` Standard TTS at $1.00 text
  input and $20.00 audio output per 1M tokens, with audio tokens equal to 25
  tokens/second, matching the TTS assumptions.
- DeepSeek's official pricing page lists V4 Pro at $0.003625 cache hit, $0.435
  cache miss, and $0.87 output per 1M tokens, matching the Viber row.
- Cartesia's public pricing page currently presents plans, credits, Sonic-3.5
  included minutes, and voice-agent minute rates rather than a clean Sonic
  per-character SKU. This supports keeping `sonic-3` unverified.

## Test Evidence

### Unit And Router Proof

Command:

```bash
uv run pytest -q tests/library/test_cost.py tests/library/test_pricing.py tests/llm/test_model_router.py
```

Result:

```text
37 passed in 0.67s
```

Coverage highlights:

- `tests/library/test_pricing.py:18-33` verifies the live-coach pricing row is
  resolved through `model_router` and carries source/date/verified fields.
- `tests/library/test_pricing.py:35-63` verifies all rows have sources/dates and
  verified rows carry concrete prices.
- `tests/library/test_pricing.py:65-74` verifies Cartesia Sonic is derived,
  unverified, and marked as such.
- `tests/library/test_pricing.py:89-97` verifies the cheaper Gemini candidate
  undercuts the current premium brain.
- `tests/library/test_cost.py:16-99` verifies cache blending, TTS billing shapes,
  and listening cost.
- `tests/library/test_cost.py:125-191` verifies leg totals, LiveKit direct-mode
  zero cost, fleet scaling, and the expected budget band.
- `tests/library/test_cost.py:213-255` verifies sensitivity axes, unverified flag
  carry-through, cache-hit sensitivity, and JSON serializability.

### Integration, Grep Gate, And Lint Proof

Command:

```bash
uv run pytest -q tests/e2e/test_phase_41_latency_stack_integration.py tests/repo/test_live_spike_scaffold.py tests/llm/test_model_router.py tests/library/test_pricing.py tests/library/test_cost.py
```

Result:

```text
62 passed in 1.04s
```

Command:

```bash
bash scripts/release/check_no_hardcoded_model.sh
```

Result:

```text
DEPS-04 / Plan 41-01 gate: clean - no hardcoded Gemini model literals in scanned paths (src/vibemix docs/AUDIT.md scripts/audit docs/dep-opportunities) outside src/vibemix/llm/_router_config.py.
```

Command:

```bash
uv run ruff check src/vibemix/library/pricing.py src/vibemix/library/cost.py tests/library/test_pricing.py tests/library/test_cost.py
```

Result:

```text
All checks passed!
```

Command:

```bash
git diff --check -- src/vibemix/library/cost.py src/vibemix/library/pricing.py src/vibemix/library/budget.py src/vibemix/__main__.py src/vibemix/llm/_router_config.py tests/library/test_cost.py tests/library/test_pricing.py tests/e2e/test_phase_41_latency_stack_integration.py tests/llm/test_model_router.py docs/pricing/live-stack-economics.en.md docs/pricing/live-stack-economics.it.md
```

Result: passed with no output.

### CLI Proof

Command:

```bash
uv run python -m vibemix library budget --stack live --dau 10000 --brain live_coach --tts sonic-3
```

Result:

```text
TOTAL     0.4857 EUR/session, 9.74 EUR/DJ-month, 97,374 fleet EUR/mo
Dominant leg: TTS
Cartesia Sonic 97,374 ! UNVERIFIED
```

Command:

```bash
uv run python -m vibemix library budget --stack live --dau 10000 --brain live_coach --tts sonic-3 --json > /tmp/vibemix-live-budget-p10-codex.json && uv run python -m json.tool /tmp/vibemix-live-budget-p10-codex.json
```

Result: JSON parsed successfully. Key fields:

```text
totals.per_dj_month_eur = 9.73740972
totals.fleet_month_eur = 97374.0972
dominant_leg = tts
Cartesia Sonic sensitivity verified = false
```

## Boundaries

- This package is an internal reproducible cost model, not launch pricing copy.
- Cartesia Sonic remains unverified until current account billing confirms the
  effective rate.
- The model assumes 90% input-cache hit, 1,900 input tokens, 40 output tokens,
  12s speech, 80 reactions/set, and 20 sessions/month; the CLI echoes these
  assumptions instead of hiding them.
- Gemini 3.1 Flash Live remains isolated under `spikes/` until its LAT-09 verdict
  is written; this package does not add it as a runtime router/pricing candidate.
- `src/vibemix/__main__.py` must be staged at hunk level if this lands while
  other packages still own neighboring hunks.

## Verdict

LAND as `feat(library-cost): add live stack budget model`.
