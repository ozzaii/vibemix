# SPDX-License-Identifier: Apache-2.0
"""Disco chain — sub arrival + phrase structure, no kick-wall overlays.

Disco / nu-disco / funk sets care about bassline entrances and phrase ends,
but should not inherit Hard Tek-only acid/distortion detectors. Keep the live
event chain structural and conservative: no genre-specific claims unless the
existing source detectors can ground them.
"""

from __future__ import annotations

from vibemix.state.detectors import PhraseBoundaryDetector, SubLayerArrivalDetector


def build_disco_chain() -> list:
    """Return the disco detector chain — SubLayerArrival + PhraseBoundary."""
    sub = SubLayerArrivalDetector()
    phrase = PhraseBoundaryDetector(kill_detector=None)
    return [sub, phrase]
