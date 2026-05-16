# SPDX-License-Identifier: Apache-2.0
"""Live-coach config validator — enforces low-latency invariants at agent init.

Per Phase 41 LAT-08 + Pitfall 3:

- ``thinking_level`` on the live coach path MUST be MINIMAL — anything higher
  adds 7s+ of TTFT regression (Gemini 3 Flash with LOW/MEDIUM/HIGH thinking
  costs the live UX its real-time feel).
- ``service_tier`` on the live coach path MUST NOT be FLEX — Flex SLA is
  1-15 min P99 60 min (per Google's tier docs), which collapses live TTFT
  to unusable. STANDARD (the SDK default) or PRIORITY are both acceptable.

Validation runs ONCE at DJCoHostAgent init / llm_factory construction. Zero
per-turn overhead. The validator is a pure callable — no side effects, no
I/O — so it is safe to call from constructors and unit tests alike.

Bypass surface: anyone with code-edit access can monkey-patch this away;
that threat is out of scope (see T-41-03-04 in 41-03-PLAN.md). The Plan
41-01 CI grep gate catches accidental model-literal regressions; this
gate catches accidental config regressions.
"""

from __future__ import annotations

from google.genai.types import GenerateContentConfig, ServiceTier, ThinkingLevel

__all__ = ["LiveCoachConfigError", "validate_live_config"]


class LiveCoachConfigError(ValueError):
    """Raised when a ``GenerateContentConfig`` violates live-coach invariants.

    Inherits from ``ValueError`` so callers that ``except ValueError`` keep
    working. The error message aggregates every violation (not just the
    first) so a single boot-time crash surfaces the full problem.
    """


# Allow-list / deny-list — name-form (uppercase) after normalization.
_ALLOWED_THINKING: frozenset[str] = frozenset({"MINIMAL"})
# Absence (None), STANDARD, PRIORITY are all acceptable for the live path.
# Only FLEX is explicitly disallowed per Pitfall 3.
_DISALLOWED_TIER: frozenset[str] = frozenset({"FLEX"})


def _normalize_thinking(level: object) -> str | None:
    """Return the uppercase name form of a ``ThinkingLevel`` value, or None.

    Accepts ``ThinkingLevel`` enum members and free-form strings; the SDK
    accepts both at config-construction time so the validator must too.
    """
    if level is None:
        return None
    if isinstance(level, ThinkingLevel):
        return level.name
    return str(level).upper()


def _normalize_tier(tier: object) -> str | None:
    """Return the uppercase name form of a ``ServiceTier`` value, or None.

    The SDK's enum values are lowercase (``'flex'``) but the enum
    ``.name`` attribute is uppercase (``'FLEX'``) — we compare against the
    name form so the allow-list reads naturally.
    """
    if tier is None:
        return None
    if isinstance(tier, ServiceTier):
        return tier.name
    return str(tier).upper()


def validate_live_config(cfg: GenerateContentConfig) -> None:
    """Raise :class:`LiveCoachConfigError` if ``cfg`` violates live-coach invariants.

    Returns ``None`` on pass. Aggregates violations — error message names
    every offending field, not just the first found, so a single boot
    surfaces the full set of problems.

    Args:
        cfg: The ``GenerateContentConfig`` about to be used on the live
            coach path. The validator never mutates it.
    """
    violations: list[str] = []

    # ----- thinking_level check ------------------------------------------------
    thinking_cfg = getattr(cfg, "thinking_config", None)
    if thinking_cfg is not None:
        level = _normalize_thinking(getattr(thinking_cfg, "thinking_level", None))
        if level is not None and level not in _ALLOWED_THINKING:
            violations.append(
                f"thinking_level={level!r} not allowed on live coach path "
                f"(must be MINIMAL — anything higher adds 7s+ TTFT regression). "
                f"Override blocked by Phase 41 LAT-08 gate."
            )

    # ----- service_tier check --------------------------------------------------
    tier = _normalize_tier(getattr(cfg, "service_tier", None))
    if tier is not None and tier in _DISALLOWED_TIER:
        violations.append(
            f"service_tier={tier!r} not allowed on live coach path "
            f"(Flex SLA 1-15 min P99 60 min = live UX collapse — Pitfall 3). "
            f"Use STANDARD or PRIORITY."
        )

    if violations:
        raise LiveCoachConfigError(" | ".join(violations))
