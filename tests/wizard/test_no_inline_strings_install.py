"""Test wizard step files (Phase 49) contain zero inline user-facing strings.

Phase 49 Plan 03 — invariant: every user-facing string in the new wizard
step files MUST flow from `copy.ts` (which reads `copy.json`). Inline string
literals indicate a copy contract violation.

We approximate "user-facing string" as: a string-literal of length ≥ 6
characters containing at least one space, appearing in a `.textContent =`
assignment, `.setAttribute("aria-label", ...)`, or similar render-time
context. Templates / class names / data-attribute values are excluded.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WIZARD = ROOT / "tauri" / "ui" / "src" / "wizard"

NEW_STEPS = [
    WIZARD / "step-forewarning.ts",
    WIZARD / "step-driver-fetch.ts",
    WIZARD / "step-48k-probe.ts",
]

# Match string literals of length >= 6 with at least one space that appear
# directly after `.textContent =` or `setAttribute("aria-label", `.
# We do NOT flag comments, log messages, or class names.
USER_FACING_PATTERNS = [
    re.compile(r'\.textContent\s*=\s*"([^"]{6,})"'),
    re.compile(r'setAttribute\("aria-label",\s*"([^"]{6,})"'),
    re.compile(r"label:\s*\"([^\"]{6,}\s[^\"]+)\""),
]


@pytest.mark.parametrize("path", NEW_STEPS, ids=lambda p: p.name)
def test_no_inline_user_facing_string_literals(path: Path):
    if not path.exists():
        pytest.skip(f"{path} not yet created")
    text = path.read_text()
    hits: list[tuple[int, str]] = []
    for line_no, line in enumerate(text.splitlines(), 1):
        for pat in USER_FACING_PATTERNS:
            for match in pat.finditer(line):
                literal = match.group(1)
                # Whitelist: short non-spaced strings or technical jargon
                if (
                    "Checking BlackHole format" in literal
                    or literal.startswith("data-")
                    or literal == ""
                ):
                    continue
                hits.append((line_no, literal))
    assert not hits, (
        f"{path.name}: inline user-facing string(s) found:\n"
        + "\n".join(f"  line {ln}: {lit!r}" for ln, lit in hits)
        + "\nMove to installer/companion/onboarding_copy.json + import via copy.ts."
    )


def test_step_files_import_from_copy_module():
    """Every new step file must import from ./copy.js."""
    for path in NEW_STEPS:
        if not path.exists():
            continue
        text = path.read_text()
        assert "from \"./copy.js\"" in text or "from './copy.js'" in text, (
            f"{path.name} must import from ./copy.js"
        )


def test_no_hex_literals_in_step_files():
    """CDJ Whisper invariant — components MUST read tokens, not inline hex."""
    HEX_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")
    for path in NEW_STEPS:
        if not path.exists():
            continue
        text = path.read_text()
        # Strip comment lines (// or /* ... */) to allow doc references
        stripped_lines = []
        in_block_comment = False
        for line in text.splitlines():
            s = line.strip()
            if in_block_comment:
                if "*/" in s:
                    in_block_comment = False
                continue
            if s.startswith("//") or s.startswith("*"):
                continue
            if "/*" in s and "*/" not in s:
                in_block_comment = True
                continue
            stripped_lines.append(line)
        body = "\n".join(stripped_lines)
        hits = HEX_RE.findall(body)
        assert not hits, f"{path.name}: hex literal(s) found: {hits}. Use var(--token) instead."
