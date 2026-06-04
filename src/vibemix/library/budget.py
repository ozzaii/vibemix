# SPDX-License-Identifier: Apache-2.0
"""Embedding cost projection + runtime telemetry.

The production library embedding path is local CLAP ONNX, so normal
search/curate/indexing spend is zero API cost. This module is retained for
legacy Gemini-embedding projections, fallback what-if checks, and the shared
session token/cost meter used by live Gemini surfaces.

Two surfaces:
    1. ``project_monthly_cost(dau)`` — legacy design-time calculation. CLI
       exposed via ``vibemix library budget``.
    2. ``BudgetTelemetry`` (singleton) — runtime counters for legacy embedding
       tests and current live Gemini token/cost meters. Warning logged at 90%
       of ceiling for operators and telemetry.

Legacy Gemini pricing constants (Assumption A9 — Google pricing as of 2026-Q2):
    text:  $0.20 per 1M tokens
    audio: $6.50 per 1M tokens
"""

from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# ─── Locked constants ──────────────────────────────────────────────────────────

BUDGET_CEILING_EUR = 50.0
USD_TO_EUR = float(os.environ.get("VIBEMIX_USD_TO_EUR", "0.92"))

PRICING = {
    "text_per_1m_tokens_usd": 0.20,
    "audio_per_1m_tokens_usd": 6.50,
}

# Gemini tokenizes audio at a fixed 32 tokens/second (official docs:
# ai.google.dev/gemini-api/docs/tokens). The per-embed audio cost is therefore
# DERIVED from the real excerpt duration, never a guessed flat constant — a
# hardcoded value silently drifts when the clip length changes. (The prior
# 0.0006 was ~20× too low and internally inconsistent with its own comment.)
# For the fixed 60s excerpt: 60 × 32 = 1920 tokens × $6.50/1M = $0.01248.
AUDIO_TOKENS_PER_SECOND = 32
EXCERPT_SECONDS = 60.0  # mirrors embed.EXCERPT_DURATION
COST_PER_AUDIO_EMBED_USD = (
    EXCERPT_SECONDS
    * AUDIO_TOKENS_PER_SECOND
    * PRICING["audio_per_1m_tokens_usd"]
    / 1e6
)  # = 0.01248
# Text query: variable length; ~500-token worst case × $0.20/1M (explicit est.).
COST_PER_TEXT_QUERY_USD = 0.0001

# Default call-rate assumptions for the legacy Gemini embedding what-if. The
# production library path is local CLAP; these constants stay here so the old
# cloud-embedding model remains auditable instead of quietly posing as current
# product economics.
DEFAULT_GROUNDING_EVENTS_PER_SESSION = 8
DEFAULT_SESSIONS_PER_MONTH = 4
DEFAULT_VIBE_SEARCHES_PER_DAY = 5
DEFAULT_VIBE_SEARCH_CACHE_HIT_RATE = 0.70
DEFAULT_SIMILAR_QUERIES_PER_MONTH = 15
DEFAULT_SIMILAR_CACHE_HIT_RATE = 0.50
# Average DJ library size; power-users at 1000+ tracks override at runtime.
# At 1000 DAU × 500 tracks × 24mo amort, indexing alone = €34/mo.
# At 1000 DAU × 1000 tracks × 24mo amort, indexing alone = €69/mo (over).
# Phase 28 v1 locked the old cloud-embedding scenario at 500/36. Keep that
# history visible: at corrected 2026 audio-embed prices it is over the €50 gate,
# while the product path moved to local CLAP and is costed by ``--stack live``.
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
    """Project legacy monthly Gemini Embedding spend for ``dau`` users."""
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


# ─── Per-session token + cost meter (quick task 260525-fuv) ─────────────────────
#
# SessionMeter records per-call token usage keyed by ROUTER-PATH (never a raw
# Gemini model literal — CI grep gate forbids model names outside
# _router_config.py). It computes the fresh/cached/output billing split so a
# DJ set's true € cost and the € saved by the Gemini context cache are visible
# at session end.
#
# ROUTE_PRICING — USD per 1M tokens, May 2026 (see PLAN <pricing_facts>):
#   - cache-eligible paths carry a "cached_input" rate (90% discount on
#     live_coach: 0.15 vs 1.50);
#   - embedding paths have no cache → cached_input == input (the split
#     degenerates to "all fresh", savings 0). Production TTS is local Chatterbox and
#     no longer records a paid router path here.
ROUTE_PRICING: dict[str, dict[str, float]] = {
    # path:            input,  output, cached_input  (USD per 1M tokens)
    "live_coach":     {"input": 1.50, "output": 9.00, "cached_input": 0.15},
    "debrief":        {"input": 2.00, "output": 12.00, "cached_input": 0.20},
    "embedding":      {"input": 0.20, "output": 0.00, "cached_input": 0.20},
}

# Paths whose cached_input is a genuine discount feed the cache-hit-rate /
# savings numerator. tts/embedding carry no real cache → excluded so the rate
# reflects only paths where caching actually saves money.
_CACHE_ELIGIBLE_PATHS = frozenset(
    p for p, r in ROUTE_PRICING.items() if r["cached_input"] < r["input"]
)


class SessionMeter:
    """Token-level per-session cost meter, keyed by router-path.

    Mirrors ``BudgetTelemetry``'s lock-guarded, singleton-accessed style.
    ``record()`` is called from the LLM stream consumer hot path — it MUST
    NEVER raise (T-fuv-01); all arithmetic is defensive. Unknown router paths
    are tracked under their key with zero cost rather than crashing (T-fuv-02).
    """

    def __init__(self) -> None:
        # path -> {"input_tokens", "cached_tokens", "output_tokens",
        #          "cost_usd", "savings_usd", "known"}
        self._paths: dict[str, dict[str, float]] = {}
        self._untracked_calls = 0
        self._lock = threading.Lock()

    def record(
        self,
        path: str,
        *,
        prompt: int = 0,
        cached: int = 0,
        output: int = 0,
    ) -> None:
        """Record one call's token usage and bill it per the path's rates.

        ``prompt`` is the TOTAL input token count (cached tokens included),
        matching Gemini ``usage_metadata.prompt_token_count``. ``cached`` is
        ``cached_content_token_count``; ``output`` is
        ``candidates_token_count``. Never raises.
        """
        try:
            prompt = max(int(prompt or 0), 0)
            cached = max(int(cached or 0), 0)
            output = max(int(output or 0), 0)
            # cached can never legitimately exceed prompt; clamp so the
            # fresh-input split and the cache-hit-rate stay sane.
            cached = min(cached, prompt)
            fresh_input = prompt - cached

            rate = ROUTE_PRICING.get(path)
            known = rate is not None
            if rate is None:
                cost_usd = 0.0
                savings_usd = 0.0
            else:
                cost_usd = (
                    fresh_input * rate["input"] / 1e6
                    + cached * rate["cached_input"] / 1e6
                    + output * rate["output"] / 1e6
                )
                savings_usd = cached * (rate["input"] - rate["cached_input"]) / 1e6

            with self._lock:
                acc = self._paths.setdefault(
                    path,
                    {
                        "input_tokens": 0.0,
                        "cached_tokens": 0.0,
                        "output_tokens": 0.0,
                        "cost_usd": 0.0,
                        "savings_usd": 0.0,
                        "known": 1.0 if known else 0.0,
                    },
                )
                acc["input_tokens"] += prompt
                acc["cached_tokens"] += cached
                acc["output_tokens"] += output
                acc["cost_usd"] += cost_usd
                acc["savings_usd"] += savings_usd
                if known:
                    acc["known"] = 1.0
        except Exception:
            # Hot-path safety (T-fuv-01): a meter write must never wedge the
            # LLM stream consumer.
            pass

    def record_untracked(self) -> None:
        """Count a generation whose token usage is unavailable (OpenRouter
        brain path returns ``usage_metadata=None``). No cost is fabricated."""
        try:
            with self._lock:
                self._untracked_calls += 1
        except Exception:
            pass

    def summary(self) -> dict:
        """Return the per-path tokens + cost block written to session.json.

        Keys: ``per_path`` (per router-path {input_tokens, cached_tokens,
        output_tokens, cost_eur}), ``total_cost_eur``, ``total_savings_eur``,
        ``cache_hit_rate`` (cached/input over cache-eligible paths, 0.0 when no
        input, clamped to [0, 1]), ``untracked_calls``.
        """
        with self._lock:
            per_path: dict[str, dict[str, float]] = {}
            total_cost_usd = 0.0
            total_savings_usd = 0.0
            cache_input = 0
            cache_cached = 0
            for path, acc in self._paths.items():
                per_path[path] = {
                    "input_tokens": int(acc["input_tokens"]),
                    "cached_tokens": int(acc["cached_tokens"]),
                    "output_tokens": int(acc["output_tokens"]),
                    "cost_eur": acc["cost_usd"] * USD_TO_EUR,
                }
                total_cost_usd += acc["cost_usd"]
                total_savings_usd += acc["savings_usd"]
                if path in _CACHE_ELIGIBLE_PATHS:
                    cache_input += int(acc["input_tokens"])
                    cache_cached += int(acc["cached_tokens"])
            untracked = self._untracked_calls

        if cache_input > 0:
            cache_hit_rate = cache_cached / cache_input
            cache_hit_rate = max(0.0, min(1.0, cache_hit_rate))
        else:
            cache_hit_rate = 0.0

        return {
            "per_path": per_path,
            "total_cost_eur": total_cost_usd * USD_TO_EUR,
            "total_savings_eur": total_savings_usd * USD_TO_EUR,
            "cache_hit_rate": cache_hit_rate,
            "untracked_calls": untracked,
        }

    def reset(self) -> None:
        """Test-only reset — production code never resets."""
        with self._lock:
            self._paths.clear()
            self._untracked_calls = 0


_SESSION_METER: SessionMeter | None = None
_SESSION_METER_LOCK = threading.Lock()


def get_session_meter() -> SessionMeter:
    """Module-level SessionMeter singleton (mirrors ``get_telemetry()``)."""
    global _SESSION_METER
    with _SESSION_METER_LOCK:
        if _SESSION_METER is None:
            _SESSION_METER = SessionMeter()
        return _SESSION_METER


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
                "runtime telemetry warning is active.",
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
    "COST_PER_AUDIO_EMBED_USD",
    "COST_PER_TEXT_QUERY_USD",
    "DEFAULT_GROUNDING_EVENTS_PER_SESSION",
    "PRICING",
    "ROUTE_PRICING",
    "USD_TO_EUR",
    "BudgetTelemetry",
    "CostProjection",
    "SessionMeter",
    "get_session_meter",
    "get_telemetry",
    "project_monthly_cost",
]
