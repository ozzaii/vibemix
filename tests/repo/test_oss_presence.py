# SPDX-License-Identifier: Apache-2.0
"""Phase 69 Plan 69-01 — OSS-01 repo-presence baseline gate.

v7.0 OSS-01 requires four OSS-canonical docs at repo root (MAINTAINERS.md,
CONTRIBUTING.md, CODE_OF_CONDUCT.md, SECURITY.md), each non-empty and
referenced from README.md, plus the exact-match Bravoh carveout sentinel
in CONTRIBUTING.md. Deletion, rename, or sentinel rewording fails CI here —
contributors must make a deliberate update rather than silently rotting the
OSS surface.

Pairs with the broader hygiene scan in tests/repo/test_oss_hygiene.py
(which predates OSS-01 and covers a different set of files); this gate is
the v7.0-specific contract.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

REQUIRED_OSS_FILES: list[str] = [
    "MAINTAINERS.md",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "SECURITY.md",
]

_MIN_BYTES: int = 200

_BRAVOH_CARVEOUT_SENTINEL: str = "the Bravoh proxy is closed-source by design"


@pytest.mark.parametrize("filename", REQUIRED_OSS_FILES)
def test_required_oss_files_exist(filename: str) -> None:
    """Each OSS-01 doc exists at repo root, is non-trivial, and is linked from README."""
    path = REPO_ROOT / filename
    assert path.exists(), (
        f"Missing required OSS file: {filename}. "
        "v7.0 OSS-01 requires all four at repo root."
    )
    size = path.stat().st_size
    assert size >= _MIN_BYTES, (
        f"OSS file {filename} is suspiciously small ({size} bytes < {_MIN_BYTES}); "
        "placeholder?"
    )
    readme_text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert filename in readme_text, (
        f"OSS file {filename} is not linked from README.md. "
        "Add it to the Community section (Plan 69-01 Task 3)."
    )


def test_contributing_has_bravoh_carveout() -> None:
    """CONTRIBUTING.md carries the exact-match Bravoh carveout sentinel exactly once.

    Pinning the literal string is deliberate — any rewording (even cosmetic prose
    tightening) trips this gate and forces a deliberate review, because the
    sentinel doubles as load-bearing privacy/IP language separating the
    Apache-2.0 client from the closed-source Bravoh proxy.
    """
    contributing_text = (REPO_ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    count = contributing_text.count(_BRAVOH_CARVEOUT_SENTINEL)
    assert count == 1, (
        f"CONTRIBUTING.md must contain the exact-match sentinel "
        f"{_BRAVOH_CARVEOUT_SENTINEL!r} exactly once; found {count}. "
        "See CONTRIBUTING.md '## Scope: vibemix vs Bravoh' section "
        "(Plan 69-01 Task 2)."
    )
