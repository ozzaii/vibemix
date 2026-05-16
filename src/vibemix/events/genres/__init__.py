# SPDX-License-Identifier: Apache-2.0
"""Per-genre detector chain builders + ``GENRE_REGISTRY``.

The ``GENRE_REGISTRY`` is the single dispatch table the GenreRouter uses
to resolve a chain at swap time. Keys MUST be a SUPERSET of
``vibemix.audio.constants.GENRE_BPM_BANDS.keys()`` — every genre the
state-refresh writer can emit MUST have a chain builder, otherwise
``GenreRouter.swap()`` would silently fall back to baseline for a
known-good genre (breaking the SENSE-15 contract).

Builders are pure functions — no I/O, no config lookups, no globals. They
instantiate fresh detector objects on every call. The router calls each
builder ONCE per session per genre (per the ``swap`` idempotency guarantee
in ``GenreRouter.swap``); construct cost is negligible.
"""

from __future__ import annotations

from collections.abc import Callable
from types import MappingProxyType

from vibemix.events.genres.baseline import build_baseline_chain
from vibemix.events.genres.hard_tek import build_hard_tek_chain
from vibemix.events.genres.house import build_house_chain
from vibemix.events.genres.techno import build_techno_chain

# Single dispatch table — GenreRouter consults this mapping on every swap.
# Keys MUST cover every genre in vibemix.audio.constants.GENRE_BPM_BANDS
# (test_genre_registry_keys_match_genre_bpm_bands pins the contract).
#
# Phase 30 SENSE-19 (Pitfall P49 mitigation): the public surface is a
# ``MappingProxyType`` so no caller can ``GENRE_REGISTRY[<x>] = builder``
# at runtime. Construct-time registration ONLY — re-registering a chain
# mid-session would break the atomic-swap contract (a swap mid-detect-call
# would observe a half-mutated registry). The raw dict
# ``_GENRE_REGISTRY_RAW`` is module-private; the only legitimate way to
# add a genre is to edit this file + ship a new release.
_GENRE_REGISTRY_RAW: dict[str, Callable[[], list]] = {
    "unknown": build_baseline_chain,
    "house": build_house_chain,
    "techno": build_techno_chain,
    "hard_tek": build_hard_tek_chain,
}
GENRE_REGISTRY: MappingProxyType = MappingProxyType(_GENRE_REGISTRY_RAW)

__all__ = [
    "GENRE_REGISTRY",
    "build_baseline_chain",
    "build_hard_tek_chain",
    "build_house_chain",
    "build_techno_chain",
]
