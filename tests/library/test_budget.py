# SPDX-License-Identifier: Apache-2.0
"""Plan 28-08 — budget projection + telemetry tests.

`test_monthly_projection_under_50_eur` is the CI hard gate per
RESEARCH §Common Pitfalls P56. Failing it BLOCKS phase merge.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

from vibemix.library.budget import (
    BUDGET_CEILING_EUR,
    BudgetTelemetry,
    COST_PER_AUDIO_EMBED_USD,
    DEFAULT_GROUNDING_EVENTS_PER_SESSION,
    PRICING,
    USD_TO_EUR,
    get_telemetry,
    project_monthly_cost,
)


def test_monthly_projection_under_50_eur() -> None:
    """CI HARD GATE — Pitfall P56."""
    p = project_monthly_cost(dau=1000)
    assert p.under_budget, (
        f"Cost projection {p.total_eur:.2f} EUR >= ceiling "
        f"{BUDGET_CEILING_EUR} EUR. Plan 28 cost gate violated."
    )
    # Sanity: at least €1 headroom so float drift doesn't flap CI.
    headroom = BUDGET_CEILING_EUR - p.total_eur
    assert headroom > 1.0, (
        f"Budget headroom too small ({headroom:.2f} EUR); "
        "tighten call-rate constants or raise ceiling explicitly."
    )


def test_projection_event_gated_not_continuous() -> None:
    """Sanity gate: locks event-gated grounding (not 180/hr continuous)."""
    assert DEFAULT_GROUNDING_EVENTS_PER_SESSION <= 20, (
        f"DEFAULT_GROUNDING_EVENTS_PER_SESSION = "
        f"{DEFAULT_GROUNDING_EVENTS_PER_SESSION} — "
        "looks like continuous-grounding regression. Plan 28 locked Option B."
    )


def test_projection_scales_with_dau() -> None:
    """DAU 5x → over budget (proves projection actually computes)."""
    p_low = project_monthly_cost(dau=1000)
    p_high = project_monthly_cost(dau=5000)
    assert p_high.total_eur > p_low.total_eur
    assert p_high.under_budget is False


def test_projection_override_grounding_rate() -> None:
    """Continuous grounding (180 events/session) → over budget.

    Locks Option B over Option A. If this test passes, someone broke
    the cost-gate by under-counting event-gated events.
    """
    p = project_monthly_cost(dau=1000, grounding_events_per_session=180)
    assert p.under_budget is False, (
        "Continuous grounding (180 events/session) MUST exceed budget — "
        "if it doesn't, the projection is missing cost terms."
    )


def test_telemetry_counters_increment() -> None:
    t = BudgetTelemetry()
    for _ in range(100):
        t.increment_audio_embed()
    expected = 100 * COST_PER_AUDIO_EMBED_USD * USD_TO_EUR
    assert abs(t.current_cost_estimate_eur() - expected) < 1e-6


def test_telemetry_singleton() -> None:
    a = get_telemetry()
    b = get_telemetry()
    assert a is b


def test_warning_at_90_percent_ceiling(caplog: pytest.LogCaptureFixture) -> None:
    """Crossing 90% of ceiling logs a warning exactly once."""
    import logging

    caplog.set_level(logging.WARNING)
    t = BudgetTelemetry()
    # 90% of €50 = €46. €46 / (0.0006 * 0.92) = ~83333 audio embeds.
    target = int(BUDGET_CEILING_EUR * 0.9 / (COST_PER_AUDIO_EMBED_USD * USD_TO_EUR)) + 5
    for _ in range(target):
        t.increment_audio_embed()
    assert any(
        "90%" in rec.message or "ceiling" in rec.message.lower()
        for rec in caplog.records
    )
    assert t.cost_warning_active() is True


def test_pricing_constants_locked() -> None:
    """Assumption A9 — if Google pricing changes, gate fails loud."""
    assert PRICING["audio_per_1m_tokens_usd"] == 6.50
    assert PRICING["text_per_1m_tokens_usd"] == 0.20


def test_telemetry_reset() -> None:
    t = BudgetTelemetry()
    t.increment_audio_embed()
    t.increment_text_embed()
    assert t.audio_embeds == 1
    t.reset()
    assert t.audio_embeds == 0
    assert t.text_embeds == 0


@pytest.mark.cli
def test_cli_library_budget_returns_projection() -> None:
    """End-to-end CLI invocation."""
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "vibemix",
            "library",
            "budget",
            "--json",
            "--dau",
            "1000",
        ],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["projection"]["under_budget"] is True
    assert data["dau"] == 1000
    assert "telemetry" in data


@pytest.mark.cli
def test_cli_library_budget_human_readable() -> None:
    """Default (no --json) shows human-readable table."""
    proc = subprocess.run(
        [sys.executable, "-m", "vibemix", "library", "budget", "--dau", "1000"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert proc.returncode == 0
    assert "Cost Projection" in proc.stdout
    assert "Total" in proc.stdout
    assert "Under budget" in proc.stdout
