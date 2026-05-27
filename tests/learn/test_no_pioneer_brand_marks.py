# SPDX-License-Identifier: Apache-2.0
"""Phase 91 Plan 02 — Apache-clean grep gate for Pioneer wordmark in learn SVGs.

Pioneer trade-dress is a launch-suicide hazard (RESEARCH §Pitfall 4). Every
SVG in ``tauri/ui/src/learn/controllers/*.svg.ts`` is hand-authored from
manufacturer hardware-diagram PDFs only — NO ``Pioneer DJ`` wordmark, NO
``Pioneer ®`` glyphs. This grep gate catches the literal strings before they
land.

Trivially green day-one because ``tauri/ui/src/learn/`` does not yet exist
(Plans 05+06 land the controller SVGs). The moment any ``.svg.ts`` appears
under that path, every file is scanned case-insensitively; the first hit
fails the gate red.

REQ-ID: N/A — Brand safety (RESEARCH §Pitfall 4). Sibling test
``tauri/ui/tests/learn/test_no_pioneer_orange.spec.ts`` covers the colour
side; this one pins the wordmark side.

Sampling: per-task commit (~10 ms — file walk + case-insensitive scan).
"""
from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


_FORBIDDEN_STRINGS = (
    "pioneer dj",
    "pioneer®",
    "pioneer ®",
)


def test_no_pioneer_brand_marks_in_learn_svgs() -> None:
    """Walk ``tauri/ui/src/learn/**/*.svg.ts`` and assert zero Pioneer
    wordmark references (case-insensitive).

    The SVG source bodies must be wordmark-free. Trivially green when the
    directory does not yet exist (Plans 05+06 land it).
    """
    learn_svg_dir = _repo_root() / "tauri" / "ui" / "src" / "learn"
    if not learn_svg_dir.exists():
        # Plans 05+06 haven't landed yet — Apache-clean gate trivially holds.
        return

    offenders: list[tuple[Path, int, str, str]] = []
    for path in learn_svg_dir.rglob("*.svg.ts"):
        for lineno, raw in enumerate(path.read_text().splitlines(), start=1):
            lower = raw.lower()
            for needle in _FORBIDDEN_STRINGS:
                if needle in lower:
                    offenders.append((path, lineno, needle, raw))

    assert not offenders, (
        "Pioneer trade-dress leak (Pitfall 4) — every controller SVG must be "
        "hand-authored from manufacturer PDFs WITHOUT the ``Pioneer DJ`` "
        f"wordmark. Offenders ({len(offenders)}):\n"
        + "\n".join(
            f"  {p}:{n}: matched {needle!r} in {ln.strip()!r}"
            for p, n, needle, ln in offenders
        )
    )
