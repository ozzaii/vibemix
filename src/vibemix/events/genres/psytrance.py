# SPDX-License-Identifier: Apache-2.0
"""Psytrance chain — kick/phrase structure without Hard Tek overlays.

Psytrance shares the useful kick-side and phrase-structure moments with the
techno chain: kick character shifts, density changes, breakdown kick kills,
re-entry lands, and phrase boundaries. It intentionally does NOT include the
Hard Tek-only distortion/acid overlays; a detected psytrance set should not
prime Sven to hear acidcore walls just because the BPM is fast.
"""

from __future__ import annotations

from vibemix.events.genres.techno import build_techno_chain


def build_psytrance_chain() -> list:
    """Return a fresh psytrance detector chain.

    Reuse the techno kick/phrase builder so the pair contracts stay identical:
    one BreakdownKickKillDetector instance is shared by re-entry and phrase.
    """
    return build_techno_chain()
