# SPDX-License-Identifier: Apache-2.0
"""Phase 33 / Plan 33-09 — API-key entry surface assertion.

Memory rule (project_one_click_install_hard_req): vibemix NEVER ships
a UI surface that accepts a Gemini API key from the user. The proxy
sits at Bravoh and rate-limits per client; there is no key entry,
no settings field, no env-var prompt.

This gate greps the Tauri UI source tree (and the install docs) for
ANY indication of a key-entry surface:

  - Literal Gemini key prefixes ("AIza...") in strings.
  - Label / placeholder text mentioning "api key" / "gemini key" /
    "api_token" (case-insensitive).
  - <input> elements whose surrounding label contains those tokens.

Any match fails the build with file:line for triage.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Globs we scan. Vue / TSX are listed for forward-compat — vibemix is
# currently vanilla TS + HTML.
SCAN_GLOBS = (
    "tauri/ui/src/**/*.ts",
    "tauri/ui/src/**/*.tsx",
    "tauri/ui/src/**/*.html",
    "tauri/ui/src/**/*.vue",
    "tauri/ui/index.html",
    "tauri/ui/mascot.html",
    "tauri/ui/overlay.html",
    "tauri/ui/debrief.html",
)

# Files allowed to mention the forbidden tokens — typically test files
# that assert the absence of the very surface this gate is enforcing,
# or comments that document why the surface does not exist.
EXCLUDED_PATHS = (
    "tauri/ui/src/wizard/__tests__/",
    "tauri/ui/tests/",
    "tauri/ui/src/ipc/validator.spec.ts",  # tests the schema
)

# Regex catalogue.
FORBIDDEN_PATTERNS = (
    # Literal Gemini key (AIza...) in source. NEVER ship these.
    re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
    # api key / API_KEY / api-key / api_key as a label/placeholder token.
    re.compile(r"\bapi[ _-]?key\b", re.IGNORECASE),
    # gemini key variants.
    re.compile(r"\bgemini[ _-]?key\b", re.IGNORECASE),
    # api_token / api-token / API Token.
    re.compile(r"\bapi[ _-]?token\b", re.IGNORECASE),
)


def _scan_files() -> list[Path]:
    files: list[Path] = []
    for pattern in SCAN_GLOBS:
        for path in REPO_ROOT.glob(pattern):
            if not path.is_file():
                continue
            rel = path.relative_to(REPO_ROOT).as_posix()
            if any(rel.startswith(ex) or ex in rel for ex in EXCLUDED_PATHS):
                continue
            files.append(path)
    return files


def _match_in_file(path: Path) -> list[tuple[int, str, str]]:
    """Returns list of (line_number, pattern_repr, line_text) for any
    forbidden token match."""
    matches: list[tuple[int, str, str]] = []
    try:
        body = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return matches
    for line_no, line in enumerate(body.splitlines(), start=1):
        for pat in FORBIDDEN_PATTERNS:
            if pat.search(line):
                matches.append((line_no, pat.pattern, line.strip()))
                break
    return matches


def test_no_api_key_input_field_in_wizard_or_settings() -> None:
    """Grep every wizard + settings TS file for API-key entry surfaces."""
    offenders: list[tuple[Path, list[tuple[int, str, str]]]] = []
    for path in _scan_files():
        # Restrict this test to the wizard + settings subtrees.
        rel = path.relative_to(REPO_ROOT).as_posix()
        if "wizard/" not in rel and "settings/" not in rel:
            continue
        matches = _match_in_file(path)
        if matches:
            offenders.append((path, matches))
    assert not offenders, _format_offenders(offenders)


def test_no_api_key_label_text_anywhere_in_ui() -> None:
    """Grep ALL UI source for label / placeholder / id text that
    captures an API key."""
    offenders: list[tuple[Path, list[tuple[int, str, str]]]] = []
    for path in _scan_files():
        matches = _match_in_file(path)
        if matches:
            offenders.append((path, matches))
    assert not offenders, _format_offenders(offenders)


def _format_offenders(
    offenders: list[tuple[Path, list[tuple[int, str, str]]]],
) -> str:
    rows: list[str] = ["API-key entry surface detected — see project_one_click_install_hard_req memory."]
    for path, matches in offenders:
        rel = path.relative_to(REPO_ROOT)
        for line_no, pat, text in matches:
            rows.append(f"  {rel}:{line_no}  /{pat}/  {text!r}")
    return "\n".join(rows)


def test_scan_globs_actually_match_files() -> None:
    """Sanity check — if we accidentally globbed nothing, the absence
    test passes vacuously. Assert the wizard tree is in scope."""
    files = _scan_files()
    assert files, "scan globs matched no files"
    wizard_files = [
        p for p in files
        if "wizard/" in p.relative_to(REPO_ROOT).as_posix()
    ]
    assert wizard_files, "no wizard source files in scan scope"
