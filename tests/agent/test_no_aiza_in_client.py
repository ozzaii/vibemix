# SPDX-License-Identifier: Apache-2.0
"""NO-AIZA-01 — phase-level invariant: no AIza pattern in client source.

This test passes regardless of mode and is the Phase 5 reason-to-exist gate.
"""

from __future__ import annotations

import re
from pathlib import Path

_AIZA = re.compile(r"AIza[0-9A-Za-z_-]{35}")
_SRC = Path(__file__).resolve().parent.parent.parent / "src" / "vibemix"


def test_no_aiza_pattern_in_client_source():
    violations: list[tuple[Path, list[str]]] = []
    for p in _SRC.rglob("*.py"):
        text = p.read_text(encoding="utf-8")
        matches = _AIZA.findall(text)
        if matches:
            violations.append((p, matches))
    assert not violations, f"AIza pattern leaked in client source: {violations}"
