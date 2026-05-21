# SPDX-License-Identifier: Apache-2.0
"""Phase 58 / Plan 58-01 — v4.0 milestone audit structural pin (Gate 4 input).

REQ-ID: REL-01

`scripts/launch/cut_release.sh` Gate 4 greps the milestone audit's frontmatter
for `^(overall_verdict|status):\\s*(WIRED|passed)\\s*$` (cut_release.sh:127).
This test pins that the v4.0 audit:

- EXISTS at `.planning/v4.0-MILESTONE-AUDIT.md`.
- Reads WIRED on the exact regex Gate 4 greps (so a real cut can go green
  on a real artifact — not a simulated fixture).
- Carries the generator's `**Generated:** by ... --write-milestone-audit`
  marker line (integration_audit.py:656) AND `auditor: scripts/integration_audit.py`
  in frontmatter, so a HAND-WRITTEN audit cannot satisfy the pin
  (T-58-02 Tampering mitigation — Pitfall 2: a fabricated WIRED is rejected).
- Is labelled for the v4.0 SHIP milestone (the generator derives the
  milestone identity from the output filename, not a hardcoded v2.1 string).

The archived `.planning/v2.1-MILESTONE-AUDIT.md` is intentionally left
untouched (history); this test only asserts the v4.0 artifact.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT = REPO_ROOT / ".planning" / "v4.0-MILESTONE-AUDIT.md"

# The exact regex cut_release.sh:127 greps the frontmatter against.
GATE4_VERDICT_RE = re.compile(
    r"^(overall_verdict|status):\s*(WIRED|passed)\s*$",
    re.MULTILINE,
)

# The generator marker line — a hand-written audit will not carry it verbatim.
GENERATOR_MARKER = "**Generated:** by `python scripts/integration_audit.py --write-milestone-audit`"


def _frontmatter(text: str) -> str:
    """Return the YAML frontmatter block (between the first two `---` fences)."""
    parts = text.split("---", 2)
    assert len(parts) >= 3, "audit has no `---` frontmatter fence"
    return parts[1]


def test_v4_milestone_audit_exists() -> None:
    assert AUDIT.exists(), f"missing Gate 4 input: {AUDIT}"


def test_v4_milestone_audit_reads_wired_on_gate4_regex() -> None:
    text = AUDIT.read_text(encoding="utf-8")
    fm = _frontmatter(text)
    m = GATE4_VERDICT_RE.search(fm)
    assert m is not None, (
        "v4.0 audit frontmatter does not match Gate 4 verdict regex "
        f"`{GATE4_VERDICT_RE.pattern}` — found:\n{fm}"
    )
    assert m.group(2) == "WIRED", f"verdict is {m.group(2)!r}, expected WIRED"


def test_v4_milestone_audit_is_generator_produced() -> None:
    """Reject a hand-written substitute (T-58-02 / Pitfall 2)."""
    text = AUDIT.read_text(encoding="utf-8")
    assert GENERATOR_MARKER in text, (
        "v4.0 audit is missing the generator marker line — it must be produced "
        "by `scripts/integration_audit.py --write-milestone-audit`, never hand-written"
    )
    fm = _frontmatter(text)
    assert re.search(
        r"^auditor:\s*scripts/integration_audit\.py\s*$", fm, re.MULTILINE
    ), "frontmatter missing `auditor: scripts/integration_audit.py`"


def test_v4_milestone_audit_labelled_v4() -> None:
    """The generated audit carries v4.0 identity (not the stale v2.1 label)."""
    fm = _frontmatter(AUDIT.read_text(encoding="utf-8"))
    assert re.search(
        r"^milestone:\s*v4\.0\s*$", fm, re.MULTILINE
    ), "frontmatter `milestone:` is not v4.0"


def test_v2_1_audit_left_untouched() -> None:
    """The archived v2.1 audit is history — do not delete it."""
    v21 = REPO_ROOT / ".planning" / "v2.1-MILESTONE-AUDIT.md"
    if v21.exists():
        fm = _frontmatter(v21.read_text(encoding="utf-8"))
        assert re.search(
            r"^milestone:\s*v2\.1\s*$", fm, re.MULTILINE
        ), "v2.1 audit milestone label was clobbered"
    else:
        pytest.skip("v2.1 audit not present in this checkout")
