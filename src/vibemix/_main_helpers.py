# SPDX-License-Identifier: Apache-2.0
"""Helpers extracted from __main__.py for testability.

These would normally live inline in ``main()`` but extracting them lets tests
pin env-var handling without spinning up the full async orchestrator (Phase 6
Wave 4).
"""

from __future__ import annotations

import os
import sys

from vibemix.state import list_profiles, set_active_profile


def apply_genre_env() -> str | None:
    """Read ``VIBEMIX_GENRE_PROFILE`` and apply via ``set_active_profile``.

    Returns the applied profile name (e.g. ``'techno'``), or ``None`` when the
    env var is absent or requested ``'none'`` / ``'unknown'`` / empty (Phase 3
    absolute-threshold fallback — Critical Constraint 8).

    No absent-env genre is fabricated; live auto-detect earns the active profile.
    The env value is case-insensitive — ``TECHNO`` works.

    ``sys.exit`` with a clear error if the env var is set to an unknown
    profile name (anything not in ``list_profiles()`` and not in the explicit
    None aliases).
    """
    raw = os.environ.get("VIBEMIX_GENRE_PROFILE")
    if raw is None:
        set_active_profile(None)
        return None
    genre = raw.strip().lower()
    valid = list_profiles()
    if genre in ("none", "unknown", ""):
        set_active_profile(None)
        return None
    if genre in valid:
        set_active_profile(genre)
        return genre
    sys.exit(
        f"VIBEMIX_GENRE_PROFILE={genre!r} is not a known profile. "
        f"Valid choices: {[*valid, 'none']}. Default: auto-detect."
    )
