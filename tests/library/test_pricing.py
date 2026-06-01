# SPDX-License-Identifier: Apache-2.0
"""Source-audited live-stack pricing table (cost+capability study, 2026-05-31).

The table is the single source of per-model cost truth for the `library budget
--stack live` validator. Every row is keyed by a model id resolved through
`model_router` (no Gemini literal escapes `_router_config.py`) and carries a
source + date + verified flag so an UNVERIFIED price can never masquerade as
fact.
"""

from __future__ import annotations

import pytest

from vibemix.llm.model_router import resolve_model


def test_price_for_path_live_coach_is_verified_premium_tier() -> None:
    """The current live brain (`live_coach` → the premium Flash tier) prices at
    the verified 2026-05 USD/1M-token rates, keyed by the resolved model id."""
    from vibemix.library.pricing import price_for_path

    row = price_for_path("live_coach")
    assert row.model_id == resolve_model("live_coach")
    assert row.kind == "llm"
    assert row.input_per_mtok_usd == 1.50
    assert row.output_per_mtok_usd == 9.00
    assert row.cached_input_per_mtok_usd == 0.15
    # Every row is grounded — an unsourced/UNVERIFIED price can't pose as fact.
    assert row.verified is True
    assert row.source_url
    assert row.source_date


def test_every_row_is_grounded_with_a_source_and_date() -> None:
    """The anti-invented-price contract: NO row may exist without a source URL +
    date — that's how an UNVERIFIED price stays flagged instead of fabricated."""
    from vibemix.library.pricing import MODEL_PRICING

    for model_id, row in MODEL_PRICING.items():
        assert row.source_url, f"{model_id} has no source_url"
        assert row.source_date, f"{model_id} has no source_date"
        assert row.kind in ("llm", "tts", "stt"), f"{model_id} bad kind {row.kind!r}"


def test_verified_rows_carry_at_least_one_concrete_price() -> None:
    """A row claiming verified=True must actually carry a price (else it is an
    UNVERIFIED placeholder lying about being verified)."""
    from vibemix.library.pricing import MODEL_PRICING

    price_fields = (
        "input_per_mtok_usd",
        "output_per_mtok_usd",
        "tts_per_1m_char_usd",
        "tts_audio_out_per_mtok_usd",
        "stt_per_min_usd",
    )
    for model_id, row in MODEL_PRICING.items():
        if row.verified:
            assert any(getattr(row, f) is not None for f in price_fields), (
                f"verified row {model_id} carries no concrete price"
            )


def test_cartesia_sonic_price_is_derived_not_an_official_sku() -> None:
    """Cartesia's public page does not publish a stable per-character SKU, so this
    legacy-derived rate stays flagged instead of masquerading as verified."""
    from vibemix.library.pricing import price_for_model

    row = price_for_model("sonic-3")
    assert row.verified is False
    assert "LEGACY_DERIVED" in row.notes
    assert "unverified" in row.notes.lower()
    assert row.tts_per_1m_char_usd == 29.9


def test_deepseek_v4_pro_is_the_verified_standing_viber_price() -> None:
    """DeepSeek V4 Pro (the Viber/set-prep brain) at its official 1/4-price rate."""
    from vibemix.library.pricing import price_for_model

    row = price_for_model("deepseek-v4-pro")
    assert row.kind == "llm"
    assert row.input_per_mtok_usd == 0.435
    assert row.output_per_mtok_usd == 0.87
    assert row.cached_input_per_mtok_usd == 0.003625
    assert row.verified is True


def test_cheapest_gemini_tier_undercuts_the_current_premium_brain() -> None:
    """The whole thesis: a cheaper good-enough Gemini live-brain tier EXISTS —
    the cheapest candidate's output rate is well under the current premium one."""
    from vibemix.library.pricing import price_for_path

    premium = price_for_path("live_coach")  # gemini-3.5-flash today
    cheap = price_for_path("live_coach_cand_25flash")
    assert cheap.output_per_mtok_usd < premium.output_per_mtok_usd
    assert cheap.input_per_mtok_usd < premium.input_per_mtok_usd


def test_unknown_model_raises_unknown_model_error() -> None:
    from vibemix.library.pricing import UnknownModelError, price_for_model

    with pytest.raises(UnknownModelError):
        price_for_model("totally-not-a-model")
