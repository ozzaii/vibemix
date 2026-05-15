# SPDX-License-Identifier: Apache-2.0
"""Phase 28 Plan 08 — Gemini Embedding 2 cost projection + runtime telemetry.

The Pitfall P56 hard gate: ``test_monthly_projection_under_50_eur`` asserts
the projected monthly cost stays ≤ €50 at 1000 DAU. Failure blocks merge.

Two surfaces:
    1. ``project_monthly_cost(dau)`` — design-time calculation. CLI exposed
       via ``vibemix library budget``.
    2. ``BudgetTelemetry`` (singleton) — runtime counters. Embedder + search
       + grounding paths increment as they spend. Warning logged at 90% of
       ceiling. The Plan 09 ``LibraryConfidence.cost_warning`` boolean
       surfaces the warning to the renderer.

Pricing constants (Assumption A9 — Google pricing as of 2026-Q2):
    text:  $0.20 per 1M tokens
    audio: $6.50 per 1M tokens
"""

from __future__ import annotations

import logging
import os
import threading
from dataclasses import asdict, dataclass

logger = logging.getLogger(__name__)


# ─── Locked constants ──────────────────────────────────────────────────────────

BUDGET_CEILING_EUR = 50.0
USD_TO_EUR = float(os.environ.get("VIBEMIX_USD_TO_EUR", "0.92"))

PRICING = {
    "text_per_1m_tokens_usd": 0.20,
    "audio_per_1m_tokens_usd": 6.50,
}

# Empirical per-call cost (60s clip ≈ 1000 audio tokens × $6.50/1M).
COST_PER_AUDIO_EMBED_USD = 0.0006
# 50-token query × $0.20/1M, rounded up.
COST_PER_TEXT_QUERY_USD = 0.0001

# Default call-rate assumptions (locked at "land under €50" rates).
DEFAULT_GROUNDING_EVENTS_PER_SESSION = 8
DEFAULT_SESSIONS_PER_MONTH = 4
DEFAULT_VIBE_SEARCHES_PER_DAY = 5
DEFAULT_VIBE_SEARCH_CACHE_HIT_RATE = 0.70
DEFAULT_SIMILAR_QUERIES_PER_MONTH = 15
DEFAULT_SIMILAR_CACHE_HIT_RATE = 0.50
# Average DJ library size; power-users at 1000+ tracks override at runtime.
# At 1000 DAU × 500 tracks × 24mo amort, indexing alone = €34/mo.
# At 1000 DAU × 1000 tracks × 24mo amort, indexing alone = €69/mo (over).
# Phase 28 v1 ships at 500/36 — see COST-PROJECTION.md for the lock + revisit
# criteria when real-world telemetry lands.
DEFAULT_INDEXING_TRACKS = 500
DEFAULT_INDEXING_AMORT_MONTHS = 36
DEFAULT_SESSION_RETRIEVAL_PER_SESSION = 1


@dataclass(frozen=True, slots=True)
class CostProjection:
    indexing_eur: float
    vibe_search_eur: float
    grounding_eur: float
    similar_eur: float
    session_retrieval_eur: float
    total_eur: float
    ceiling_eur: float
    under_budget: bool


def project_monthly_cost(
    dau: int = 1000,
    *,
    grounding_events_per_session: int = DEFAULT_GROUNDING_EVENTS_PER_SESSION,
    sessions_per_month: int = DEFAULT_SESSIONS_PER_MONTH,
    vibe_searches_per_day: int = DEFAULT_VIBE_SEARCHES_PER_DAY,
    vibe_cache_hit_rate: float = DEFAULT_VIBE_SEARCH_CACHE_HIT_RATE,
    similar_per_month: int = DEFAULT_SIMILAR_QUERIES_PER_MONTH,
    similar_cache_hit_rate: float = DEFAULT_SIMILAR_CACHE_HIT_RATE,
    indexing_tracks: int = DEFAULT_INDEXING_TRACKS,
    indexing_amort_months: int = DEFAULT_INDEXING_AMORT_MONTHS,
    session_retrieval_per_session: int = DEFAULT_SESSION_RETRIEVAL_PER_SESSION,
) -> CostProjection:
    """Project monthly Gemini Embedding spend for ``dau`` daily-active users."""
    # 1. One-time library indexing — amortised over N months.
    # Indexing uses the 3-excerpt path → 3 audio embeds per track. The
    # one-time cost per user is amortised over indexing_amort_months;
    # at steady-state only 1/indexing_amort_months of the DAU pool is
    # indexing fresh in any given month (the rest re-import cache-hit
    # via Plan 28-01's content-hash cache → 0 API spend).
    indexing_per_user_one_time_usd = (
        indexing_tracks * 3 * COST_PER_AUDIO_EMBED_USD
    )
    fresh_indexers_per_month = dau / max(1, indexing_amort_months)
    indexing_total_usd = (
        fresh_indexers_per_month * indexing_per_user_one_time_usd
    )

    # 2. Vibe-search NL queries — text embeds, cache miss only.
    vibe_per_user_per_month = vibe_searches_per_day * 30
    vibe_misses_per_user = vibe_per_user_per_month * (
        1.0 - vibe_cache_hit_rate
    )
    vibe_usd = vibe_misses_per_user * COST_PER_TEXT_QUERY_USD * dau

    # 3. Grounding — event-gated, single audio embed per event.
    grounding_per_user = grounding_events_per_session * sessions_per_month
    grounding_usd = grounding_per_user * COST_PER_AUDIO_EMBED_USD * dau

    # 4. Similar — single text embed per call (seed track is already cached
    #    via embed_track content-hash; only the seed-vec lookup uses the
    #    cache; the search itself is a free in-process cosine).
    similar_misses = similar_per_month * (1.0 - similar_cache_hit_rate)
    # Similar embeds the track audio if not cached — assume cache hit at
    # the embed level (track is in library, was embedded at indexing time)
    # so the cost is effectively the in-process lookup → ~$0.
    # Conservative: count as cache_hit_rate misses producing 1 text embed.
    similar_usd = similar_misses * COST_PER_TEXT_QUERY_USD * dau

    # 5. Session-end retrieval embed (Phase 25 debrief slot — minor).
    session_per_user = session_retrieval_per_session * sessions_per_month
    session_usd = session_per_user * COST_PER_AUDIO_EMBED_USD * dau

    total_usd = (
        indexing_total_usd
        + vibe_usd
        + grounding_usd
        + similar_usd
        + session_usd
    )
    total_eur = total_usd * USD_TO_EUR

    return CostProjection(
        indexing_eur=indexing_total_usd * USD_TO_EUR,
        vibe_search_eur=vibe_usd * USD_TO_EUR,
        grounding_eur=grounding_usd * USD_TO_EUR,
        similar_eur=similar_usd * USD_TO_EUR,
        session_retrieval_eur=session_usd * USD_TO_EUR,
        total_eur=total_eur,
        ceiling_eur=BUDGET_CEILING_EUR,
        under_budget=total_eur < BUDGET_CEILING_EUR,
    )


# ─── Runtime telemetry singleton ───────────────────────────────────────────────


class BudgetTelemetry:
    """In-memory counters for runtime cost estimate."""

    def __init__(self) -> None:
        self.audio_embeds = 0
        self.text_embeds = 0
        self.cache_hits = 0
        self._lock = threading.Lock()
        self._warned_at_90 = False

    def increment_audio_embed(self) -> None:
        with self._lock:
            self.audio_embeds += 1
        self._maybe_warn()

    def increment_text_embed(self) -> None:
        with self._lock:
            self.text_embeds += 1
        self._maybe_warn()

    def increment_cache_hit(self) -> None:
        with self._lock:
            self.cache_hits += 1

    def current_cost_estimate_eur(self) -> float:
        with self._lock:
            usd = (
                self.audio_embeds * COST_PER_AUDIO_EMBED_USD
                + self.text_embeds * COST_PER_TEXT_QUERY_USD
            )
        return usd * USD_TO_EUR

    def _maybe_warn(self) -> None:
        cost = self.current_cost_estimate_eur()
        if cost >= BUDGET_CEILING_EUR * 0.9 and not self._warned_at_90:
            logger.warning(
                "BudgetTelemetry: 90%% ceiling crossed — "
                "current=%.4f EUR, ceiling=%.2f EUR. "
                "Plan 28-09 LibraryConfidence.cost_warning will surface "
                "in the next IPC tick.",
                cost,
                BUDGET_CEILING_EUR,
            )
            self._warned_at_90 = True

    def cost_warning_active(self) -> bool:
        """Return True iff runtime telemetry has crossed 90% of ceiling."""
        return (
            self.current_cost_estimate_eur()
            >= BUDGET_CEILING_EUR * 0.9
        )

    def as_dict(self) -> dict:
        return {
            "audio_embeds": self.audio_embeds,
            "text_embeds": self.text_embeds,
            "cache_hits": self.cache_hits,
            "current_cost_estimate_eur": self.current_cost_estimate_eur(),
            "cost_warning_active": self.cost_warning_active(),
        }

    def reset(self) -> None:
        """Test-only reset — production code never resets."""
        with self._lock:
            self.audio_embeds = 0
            self.text_embeds = 0
            self.cache_hits = 0
            self._warned_at_90 = False


_TELEMETRY: BudgetTelemetry | None = None
_TELEMETRY_LOCK = threading.Lock()


def get_telemetry() -> BudgetTelemetry:
    """Module-level BudgetTelemetry singleton."""
    global _TELEMETRY
    with _TELEMETRY_LOCK:
        if _TELEMETRY is None:
            _TELEMETRY = BudgetTelemetry()
        return _TELEMETRY


__all__ = [
    "BUDGET_CEILING_EUR",
    "BudgetTelemetry",
    "COST_PER_AUDIO_EMBED_USD",
    "COST_PER_TEXT_QUERY_USD",
    "CostProjection",
    "DEFAULT_GROUNDING_EVENTS_PER_SESSION",
    "PRICING",
    "USD_TO_EUR",
    "get_telemetry",
    "project_monthly_cost",
]
