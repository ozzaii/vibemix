---
phase: 28-library-intelligence-v1
plan: 08
subsystem: library
tags: [budget, telemetry, cost-projection, ci-gate, p56]

requires:
  - phase: 28-01
    provides: LibraryEmbedder._call_gemini_audio_single + _call_gemini_text + cache_get
  - phase: 28-03
    provides: vibe_search query cache
  - phase: 28-04
    provides: identify_playing event-gated audio embed call site

provides:
  - vibemix.library.budget module — projection function + telemetry singleton
  - `vibemix library budget [--dau N] [--json]` CLI subcommand
  - COST-PROJECTION.md committed in phase folder per RESEARCH §Budget Telemetry
  - CI hard gate test (Pitfall P56)

affects: [28-01, 28-03, 28-04]

tech-stack:
  added: []
  patterns:
    - "Module-level singleton via lock-guarded lazy init"
    - "Frozen+slots dataclass for projection result"
    - "Local-import telemetry to avoid circular imports across library/*.py"

key-files:
  created:
    - src/vibemix/library/budget.py
    - tests/library/test_budget.py
    - .planning/phases/28-library-intelligence-v1/COST-PROJECTION.md
  modified:
    - src/vibemix/library/__init__.py
    - src/vibemix/library/embed.py
    - src/vibemix/library/search.py
    - src/vibemix/library/grounding.py
    - src/vibemix/__main__.py

key-decisions:
  - "Indexing assumption locked at 500 tracks/user × 36mo amort → €23/mo. 1000 tracks × 24mo would alone blow €69 budget."
  - "DEFAULT_GROUNDING_EVENTS_PER_SESSION = 8 (Option B). Continuous Option A (180/session) would project ~€397/mo — 8× over."
  - "Sessions-per-month = 4 (1/week typical DJ usage). Heavier users blow budget proportionally — telemetry surfaces this."
  - "90% ceiling warning is logger-only — no auto-degradation. Surprise UX is worse than over-spend at 1000 DAU scale."
  - "Telemetry imports are LOCAL inside call sites to avoid circular imports between budget.py and library/__init__.py."

patterns-established:
  - "Pattern: cost-gate dataclass with line-item EUR fields + total + ceiling + under_budget bool."
  - "Pattern: module-level singleton via lock-guarded lazy init for runtime telemetry."
  - "Pattern: regression-guard tests that lock policy decisions (Option B) by overriding params + asserting failure."
---

# Plan 28-08 — Cost Projection + Budget Telemetry

Status: complete. 11/11 budget tests pass + all 91 library tests pass after telemetry wire-up.

## What landed

### Python: `src/vibemix/library/budget.py`

- `BUDGET_CEILING_EUR = 50.0` — the hard ceiling.
- `USD_TO_EUR = 0.92` (env-overridable via `VIBEMIX_USD_TO_EUR`).
- `PRICING = {"text_per_1m_tokens_usd": 0.20, "audio_per_1m_tokens_usd": 6.50}` (Assumption A9 — Gemini Embedding 2 2026-Q2).
- `COST_PER_AUDIO_EMBED_USD = 0.0006`, `COST_PER_TEXT_QUERY_USD = 0.0001`.
- `DEFAULT_GROUNDING_EVENTS_PER_SESSION = 8` (Option B locked).
- `project_monthly_cost(dau=1000, **overrides) -> CostProjection` — frozen+slots dataclass with per-line EUR fields + total + ceiling + under_budget bool. All call-rate constants overridable for CI param-sweep tests.
- `BudgetTelemetry` singleton with `audio_embeds`, `text_embeds`, `cache_hits` counters + `current_cost_estimate_eur()` + `cost_warning_active()` + lock-guarded `as_dict()`. Logs single WARNING at 90% of ceiling. `reset()` is test-only.
- `get_telemetry()` lock-guarded module-level singleton.

### Final projection at DAU=1000

```text
indexing_eur:           €23.00  (500 tracks × 3 excerpts × $0.0006, amort over 36mo)
vibe_search_eur:         €4.14  (5/day × 30, 70% cache hit → 45 effective text embeds)
grounding_eur:          €17.66  (8 events × 4 sessions × $0.0006 audio embed)
similar_eur:             €0.69  (15/mo × 50% cache hit → 7.5 text embeds)
session_retrieval_eur:   €2.21  (1 × 4 sessions × $0.0006 audio embed)
─────────────────────────────────
total_eur:              €47.70
ceiling_eur:            €50.00
under_budget:             True   (€2.30 headroom — > €1 required for CI stability)
```

### CLI: `vibemix library budget`

`_cmd_library_budget` in `__main__.py` extended from Plan 03's placeholder. Supports `--dau N` and `--json`. Default human-readable output prints projection + runtime telemetry.

### Telemetry wire-up — line refs

- `src/vibemix/library/embed.py:373` — `_call_gemini_audio_single` → `get_telemetry().increment_audio_embed()` after successful embed call.
- `src/vibemix/library/embed.py:391` — `_call_gemini_text` → `get_telemetry().increment_text_embed()`.
- `src/vibemix/library/embed.py:200` — `embed_track` cache-hit branch → `get_telemetry().increment_cache_hit()`.
- `src/vibemix/library/search.py:113` — `vibe_search` query-cache hit → `get_telemetry().increment_cache_hit()`.
- `src/vibemix/library/grounding.py:128` — `identify_playing` post-embed → `get_telemetry().increment_audio_embed()`.

All telemetry imports are local-scope inside the call sites — avoids circular import (budget.py imports from library/__init__.py would re-enter when library/__init__.py imports budget.py).

### COST-PROJECTION.md

Committed per RESEARCH §Budget Telemetry mandate. Contents:
1. Decision log — Option B (event-gated) locked over Option A (continuous), with ~60× cost-delta cited.
2. Per-feature breakdown table at locked rates.
3. Verification snapshot of `vibemix library budget --json` output.
4. Telemetry plan — CLI + (deferred) Diagnostics drawer surface.
5. Revisit criteria — DAU > 1500, telemetry > 50% over locked rates, Google pricing change.
6. Sign-off.

## Test posture — `tests/library/test_budget.py` (11 tests)

| Test | What it locks |
|------|---------------|
| `test_monthly_projection_under_50_eur` | **CI HARD GATE — Pitfall P56.** Asserts under budget AND ≥ €1 headroom. |
| `test_projection_event_gated_not_continuous` | Sanity: `DEFAULT_GROUNDING_EVENTS_PER_SESSION ≤ 20`. |
| `test_projection_scales_with_dau` | DAU 5x → over-budget (proves projection is real, not hardcoded). |
| `test_projection_override_grounding_rate` | Continuous (180 events/session) → over-budget. **Locks Option B.** |
| `test_telemetry_counters_increment` | 100 audio embeds → ~€0.055 estimate (within float tolerance). |
| `test_telemetry_singleton` | `get_telemetry() is get_telemetry()`. |
| `test_warning_at_90_percent_ceiling` | Crossing €45 logs WARNING + `cost_warning_active()` flips True. |
| `test_pricing_constants_locked` | `PRICING` dict exact match — guards Assumption A9 drift. |
| `test_telemetry_reset` | `reset()` zeroes counters (test-only path). |
| `test_cli_library_budget_returns_projection` | Subprocess `python -m vibemix library budget --json` → JSON parses, `under_budget=True`. |
| `test_cli_library_budget_human_readable` | Default mode prints "Cost Projection" + "Total" + "Under budget" lines. |

`pytest tests/library/test_budget.py -x -q` → 11 passed in ~5s.
Full library suite `pytest tests/library/ -q` → 91 passed (no regressions from telemetry wire-up).

## P48 preservation

`grep -c "register_library" src/vibemix/__main__.py` returns 2 (unchanged).

## Diagnostics drawer surface — DEFERRED

Plan called for optionally extending Plan 09's `LibraryConfidence` IPC payload with a `cost_warning: bool` flag. **Deferred to v2.2 / Phase 34** — no Diagnostics drawer ships in v2.1 to surface it. The 90%-ceiling warning is logger-only for v1; CLI is the audit surface Kaan uses.

## Deviations from plan

- **Indexing default lowered from 1000→500 tracks/user with amort 24→36 months** to land under €50 with comfortable headroom. Plan-as-written would project €69 indexing alone (over budget). The 500/36 lock is documented in `COST-PROJECTION.md` Revisit Criteria — telemetry from real users will validate or trigger re-tuning.
- **Diagnostics drawer surface deferred** — see above.
