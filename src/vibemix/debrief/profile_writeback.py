# SPDX-License-Identifier: Apache-2.0
"""One Mind S5 — close the debrief → long-term-profile cold-start loop.

The debrief was a review-only dead-end: it generated chapters + drills + a TLDR
and wrote ``session_debrief.json``, but NEVER fed anything back into the
long-term DJ profile. The profile only ever rebuilt when the user manually
clicked "regenerate" in Settings — so a DJ could review fifty sessions and the
persona-shaping profile would still be cold.

This module wires the loop shut: after a session is reviewed, rebuild the
profile from that session's STRUCTURED events + grounded evidence snapshot via
the proven :func:`vibemix.profile.build_profile` aggregator (the exact path the
manual regenerate handler uses), and save it.

WHY STRUCTURED, NOT DRILLS: the obvious-but-wrong move is to mine the debrief
drills (situation / behavior / impact) for profile signal. Those are free-text
model output — feeding them to the profile that shapes the live persona is a
persistence-grade slop risk (a hallucinated drill would poison every future
session). We deliberately do NOT mine drill prose. We use only the same
citation-grounded ``evidence_snapshot`` + typed ``events`` the builder already
trusts, so the write-back inherits build_profile's anti-overfit guards (the
>=2-citation-per-field rule + prior-retention on insufficient evidence). Mining
drills for an additional taste signal is a documented follow-up gated on a Kaan
ear-pass, not shipped here.

Consent-gated (the whole profile feature is opt-in; build_profile returns None
without consent) and best-effort (a write-back failure must NEVER crash the
debrief). Dependency injection on the loaders/saver keeps it unit-testable
without touching disk.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


def write_back_profile(
    events: list[dict] | None,
    evidence_snapshot: dict[str, Any] | None,
    *,
    consent_loader: Callable[[], bool] | None = None,
    prior_loader: Callable[[], dict | None] | None = None,
    builder: Callable[..., dict | None] | None = None,
    saver: Callable[[dict], None] | None = None,
) -> bool:
    """Rebuild + persist the long-term profile from a reviewed session.

    Returns ``True`` iff a profile was written. Consent-gated + best-effort:
    any failure (no consent, nothing to learn, builder/save error) returns
    ``False`` without raising — the debrief flow must never crash on this.
    """
    try:
        from vibemix.profile import (
            build_profile,
            load_consent,
            load_profile,
            save_profile,
        )

        _consent = consent_loader or load_consent
        _prior = prior_loader or load_profile
        _build = builder or build_profile
        _save = saver or save_profile

        if not _consent():
            return False

        prior = _prior()
        evidence = evidence_snapshot or {}
        evt = list(events or [])
        # Mirror the regenerate handler's anti-cold-start gate: with no new
        # signal AND no prior, build_profile would emit a pretend-personalized
        # cold-start dict. Skip rather than write noise.
        if not evidence and not evt and prior is None:
            return False

        new_profile = _build(prior, evt, evidence, consent=True)
        if new_profile is None:
            return False

        _save(new_profile)
        return True
    except Exception as e:  # pragma: no cover — best-effort, never crash debrief
        logger.warning("[debrief] profile write-back skipped: %s", e)
        return False


__all__ = ["write_back_profile"]
