# SPDX-License-Identifier: Apache-2.0
"""Plan 41-03 / Task 1 — thinking_gate validator unit tests (LAT-08).

Pins the live-coach config invariants:

- thinking_level on live coach MUST be MINIMAL (anything higher = 7s+ TTFT
  regression per CONTEXT D-LAT-08).
- service_tier on live coach MUST NOT be FLEX (Pitfall 3 — Flex SLA is
  1-15 min P99 60 min = live UX collapse).
- Pass cases cover: MINIMAL via enum / lowercase string / uppercase string,
  STANDARD / PRIORITY tier, no tier set, no thinking config set.
- Fail cases cover: LOW / MEDIUM / HIGH thinking, FLEX tier as enum or
  string, and the both-violations aggregated message.
"""

from __future__ import annotations

import pytest
from google.genai.types import (
    GenerateContentConfig,
    ServiceTier,
    ThinkingConfig,
    ThinkingLevel,
)

from vibemix.llm.thinking_gate import LiveCoachConfigError, validate_live_config


# ---------------------------------------------------------------------------
# Pass cases — validator returns None
# ---------------------------------------------------------------------------


def test_minimal_thinking_passes() -> None:
    cfg = GenerateContentConfig(
        thinking_config=ThinkingConfig(thinking_level=ThinkingLevel.MINIMAL),
    )
    assert validate_live_config(cfg) is None


def test_minimal_string_lowercase_passes() -> None:
    cfg = GenerateContentConfig(
        thinking_config=ThinkingConfig(thinking_level="minimal"),
    )
    assert validate_live_config(cfg) is None


def test_minimal_string_uppercase_passes() -> None:
    cfg = GenerateContentConfig(
        thinking_config=ThinkingConfig(thinking_level="MINIMAL"),
    )
    assert validate_live_config(cfg) is None


def test_standard_tier_passes() -> None:
    cfg = GenerateContentConfig(
        thinking_config=ThinkingConfig(thinking_level=ThinkingLevel.MINIMAL),
        service_tier=ServiceTier.STANDARD,
    )
    assert validate_live_config(cfg) is None


def test_priority_tier_passes() -> None:
    cfg = GenerateContentConfig(
        thinking_config=ThinkingConfig(thinking_level=ThinkingLevel.MINIMAL),
        service_tier=ServiceTier.PRIORITY,
    )
    assert validate_live_config(cfg) is None


def test_no_service_tier_passes() -> None:
    # SDK default tier is fine — validator must not raise on None.
    cfg = GenerateContentConfig(
        thinking_config=ThinkingConfig(thinking_level=ThinkingLevel.MINIMAL),
        service_tier=None,
    )
    assert validate_live_config(cfg) is None


def test_no_thinking_config_passes() -> None:
    # Defensive: when thinking_config is None Gemini's default behavior
    # applies. Production live coach explicitly sets MINIMAL; the validator
    # only rejects EXPLICIT non-MINIMAL overrides, not absence.
    cfg = GenerateContentConfig(thinking_config=None)
    assert validate_live_config(cfg) is None


# ---------------------------------------------------------------------------
# Fail cases — validator raises LiveCoachConfigError
# ---------------------------------------------------------------------------


def test_low_thinking_raises() -> None:
    cfg = GenerateContentConfig(
        thinking_config=ThinkingConfig(thinking_level=ThinkingLevel.LOW),
    )
    with pytest.raises(LiveCoachConfigError, match=r"thinking_level.*MINIMAL"):
        validate_live_config(cfg)


def test_medium_thinking_raises() -> None:
    cfg = GenerateContentConfig(
        thinking_config=ThinkingConfig(thinking_level=ThinkingLevel.MEDIUM),
    )
    with pytest.raises(LiveCoachConfigError, match=r"thinking_level.*MINIMAL"):
        validate_live_config(cfg)


def test_high_thinking_raises() -> None:
    cfg = GenerateContentConfig(
        thinking_config=ThinkingConfig(thinking_level=ThinkingLevel.HIGH),
    )
    with pytest.raises(LiveCoachConfigError, match=r"thinking_level.*MINIMAL"):
        validate_live_config(cfg)


def test_flex_tier_raises() -> None:
    cfg = GenerateContentConfig(
        thinking_config=ThinkingConfig(thinking_level=ThinkingLevel.MINIMAL),
        service_tier=ServiceTier.FLEX,
    )
    with pytest.raises(LiveCoachConfigError, match=r"service_tier.*Flex SLA"):
        validate_live_config(cfg)


def test_flex_tier_string_raises() -> None:
    # CaseInSensitiveEnum accepts the lowercase string too — validator
    # must normalize and still catch it.
    cfg = GenerateContentConfig(
        thinking_config=ThinkingConfig(thinking_level=ThinkingLevel.MINIMAL),
        service_tier="flex",
    )
    with pytest.raises(LiveCoachConfigError, match=r"service_tier.*Flex SLA"):
        validate_live_config(cfg)


def test_both_violations_reports_both() -> None:
    cfg = GenerateContentConfig(
        thinking_config=ThinkingConfig(thinking_level=ThinkingLevel.HIGH),
        service_tier=ServiceTier.FLEX,
    )
    with pytest.raises(LiveCoachConfigError) as exc:
        validate_live_config(cfg)
    msg = str(exc.value)
    assert "thinking_level" in msg
    assert "service_tier" in msg
