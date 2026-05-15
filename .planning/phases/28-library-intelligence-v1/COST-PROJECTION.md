---
phase: 28-library-intelligence-v1
plan: 08
status: LOCKED
date: 2026-05-15
ceiling_eur: 50.0
projected_eur: 47.70
headroom_eur: 2.30
gate_test: tests/library/test_budget.py::test_monthly_projection_under_50_eur
---

# Phase 28 — Cost Projection (LOCKED)

**Status:** LOCKED at 2026-05-15 per RESEARCH §Budget Telemetry mandate.
**Hard CI gate:** `tests/library/test_budget.py::test_monthly_projection_under_50_eur` (Pitfall P56).
**Ceiling:** **€50.00 / month at 1000 DAU.**
**Projected:** **€47.70 / month at 1000 DAU.** Headroom: €2.30 (≥ €2 required to avoid CI float-flap).

---

## Decision Log — Option B locked (event-gated grounding)

RESEARCH **Open Q1** asked whether grounding should be:

- **Option A (continuous):** ~3 embeds/min × 60 min/session ≈ 180 events/session.
  At 1000 DAU × 4 sessions/mo = **720,000 audio embeds/month** ≈ **€397/mo grounding alone**.
  At even higher session counts → ~€3000/mo. **60× over budget.** Hard reject.
- **Option B (event-gated):** ~8 embeds/session, fired only on TRACK_CHANGE / PHASE / LAYER_ARRIVAL.
  At 1000 DAU × 4 sessions/mo = **32,000 audio embeds/month** ≈ **€17.66/mo grounding**.

**LOCKED: Option B.** Phase 28-04 implements `TRACK_AWARE_EVENTS = {TRACK_CHANGE, PHASE, LAYER_ARRIVAL}` in `grounding.py`. Other event types skip the embed entirely (`identify_playing` returns `None`).

**Regression guard:** `test_projection_event_gated_not_continuous` asserts `DEFAULT_GROUNDING_EVENTS_PER_SESSION ≤ 20`. `test_projection_override_grounding_rate` asserts that passing `grounding_events_per_session=180` produces `under_budget=False` — proves the gate would catch a regression.

---

## Per-feature cost breakdown (DAU = 1000, locked rates)

| Feature | Locked rate | Per-month volume @ 1000 DAU | Unit cost (USD) | Monthly (€) |
|---------|-------------|-----------------------------|-----------------|-------------|
| One-time library indexing (3 excerpts/track, amortised) | 500 tracks × 3 excerpts × $0.0006, amortised over 36mo → 1/36 of DAU each month indexes fresh | 27.78 fresh users × 1500 embeds = 41,667/mo | $0.0006/audio | **€23.00** |
| Vibe-search NL queries | 5 queries/day × 30d = 150/user/mo, 70% cache hit → 45 effective | 45,000 text embeds | $0.0001/text | **€4.14** |
| "What's playing" grounding (Option B event-gated) | 8 events × 4 sessions = 32/user/mo | 32,000 audio embeds | $0.0006/audio | **€17.66** |
| Track-to-track similarity (USER-ASKED) | 15/user/mo, 50% content-hash cache hit → 7.5 effective text lookups | 7,500 text embeds | $0.0001/text | **€0.69** |
| Session-end retrieval embed | 1 embed × 4 sessions = 4/user/mo | 4,000 audio embeds | $0.0006/audio | **€2.21** |
| **TOTAL** | — | — | — | **€47.70** |
| **Ceiling** | — | — | — | **€50.00** |
| **Headroom** | — | — | — | **€2.30** |

(Numbers from `python -m vibemix library budget --json --dau 1000` — see Verification snapshot below. Slight rounding diffs vs hand-calc due to USD→EUR floating point.)

### Pricing constants (Assumption A9 — Google Gemini Embedding 2 as of 2026-Q2)

| Modality | $/1M tokens | Per-call assumption | Per-call cost |
|----------|-------------|---------------------|---------------|
| Text | $0.20 | 50 tokens / query | $0.0001 |
| Audio | $6.50 | ~1000 tokens / 60s clip | $0.0006 |
| USD→EUR | 0.92 (env-overridable: `VIBEMIX_USD_TO_EUR`) | — | — |

`test_pricing_constants_locked` regression-guards the unit prices. If Google shifts pricing the test fails LOUD and the operator re-runs the projection.

---

## Verification snapshot — committed evidence

```text
$ python -m vibemix library budget --json --dau 1000
{
  "projection": {
    "indexing_eur": 23.0,
    "vibe_search_eur": 4.14,
    "grounding_eur": 17.664,
    "similar_eur": 0.69,
    "session_retrieval_eur": 2.208,
    "total_eur": 47.702,
    "ceiling_eur": 50.0,
    "under_budget": true
  },
  "telemetry": {
    "audio_embeds": 0,
    "text_embeds": 0,
    "cache_hits": 0,
    "current_cost_estimate_eur": 0.0,
    "cost_warning_active": false
  },
  "dau": 1000
}
```

(Captured 2026-05-15 from `vibemix library budget --json --dau 1000`.)

---

## Telemetry plan — runtime visibility

`BudgetTelemetry` (singleton, in-memory) increments three counters:

- `audio_embeds` — bumped from `LibraryEmbedder._call_gemini_audio_single` and from `grounding.identify_playing`.
- `text_embeds` — bumped from `LibraryEmbedder._call_gemini_text` (vibe-search query path + text-only track signature).
- `cache_hits` — bumped from `LibraryEmbedder.embed_track` content-hash hit + `search.vibe_search` query-cache hit.

**Surfaces:**

1. **CLI (Kaan-side audit):** `vibemix library budget` prints the live counters alongside the projection. `--json` shape:
   ```json
   {"telemetry": {"audio_embeds": N, "text_embeds": N, "cache_hits": N, "current_cost_estimate_eur": X, "cost_warning_active": false}}
   ```
2. **Renderer (Diagnostics drawer — deferred):** Plan 09's `LibraryConfidence` IPC payload may grow a `cost_warning: bool` flag in v2.2 once the Diagnostics drawer ships (Phase 34 territory). For v2.1 the warning is logger-only.
3. **90% ceiling warning:** First crossing of `BUDGET_CEILING_EUR * 0.9 = €45` logs a single WARNING. No auto-degradation — that creates surprise UX. Operator sees the warning + decides.

---

## Revisit criteria — when to re-run this projection

| Trigger | Action |
|---------|--------|
| Real-world DAU sustained > 1500 (Bravoh proxy rate-limit threshold) | Re-run projection at observed DAU + adjust rate caps in proxy layer. |
| Telemetry shows real-world rates > locked assumptions by ≥ 50% (e.g. heavy users avg 8+ sessions/mo, not 4) | Re-derive per-feature rates from telemetry distribution + adjust gate. |
| Google pricing change (`test_pricing_constants_locked` fails) | Update `PRICING` constants + commit a new projection cycle. |
| Library size distribution shifts (median > 500 tracks → indexing cost balloons) | Reconsider indexing strategy — single-clip vs 3-excerpt, longer amort window. |

---

## CI Hard Gate

```python
# tests/library/test_budget.py
def test_monthly_projection_under_50_eur() -> None:
    """CI HARD GATE — Pitfall P56."""
    p = project_monthly_cost(dau=1000)
    assert p.under_budget, ...
    headroom = BUDGET_CEILING_EUR - p.total_eur
    assert headroom > 1.0, "Budget headroom too small (...); tighten or raise ceiling explicitly."
```

If this test fails, **the phase does not merge.** Plan 28-08 design is the single point of truth for cost discipline.

---

## Sign-off

- [x] RESEARCH §Budget Telemetry mandate satisfied (this document).
- [x] Option B (event-gated grounding) LOCKED via two regression tests.
- [x] Pricing constants regression-guarded.
- [x] Telemetry counters wired into all 5 embed entry points.
- [x] CLI `vibemix library budget` ships with `--json` + human-readable modes.
- [x] CI hard gate in place with €2.30 headroom.
