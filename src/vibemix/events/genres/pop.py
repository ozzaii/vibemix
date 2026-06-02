# SPDX-License-Identifier: Apache-2.0
"""Pop chain — broad structural moments only.

Pop / mainstream / Top 40 material varies too much to justify hard-coded
scene overlays. Route it through conservative sub-arrival + phrase-boundary
detectors so Sven can stay aware of structure without hallucinating a club
subgenre grammar.
"""

from __future__ import annotations

from vibemix.state.detectors import PhraseBoundaryDetector, SubLayerArrivalDetector


def build_pop_chain() -> list:
    """Return the pop detector chain — SubLayerArrival + PhraseBoundary."""
    sub = SubLayerArrivalDetector()
    phrase = PhraseBoundaryDetector(kill_detector=None)
    return [sub, phrase]
