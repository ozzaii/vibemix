# SPDX-License-Identifier: Apache-2.0
"""Phase 33 / Plan 33-09 — API-key entry surface assertion.

Original memory rule (project_one_click_install_hard_req): vibemix ships with
no UI surface that accepts a Gemini API key from the user.

Policy history: Kaan D2 briefly allowed exactly one BYO key surface (the
Settings BRAIN group). That drawer was deliberately deleted in `d056a391`
(2026-06-06 settings purge), and on 2026-06-09 Kaan locked the product as
PROXY-ONLY — users are served through the Bravoh proxy (altidus); direct mode
is a dev-only `.env` path with zero UI surface. This gate therefore enforces
the original zero-surface rule again. The backend `ipc.settings.set_brain`
handler and its IPC-log redaction rule stay as defensive depth — they are not
a license to rebuild the drawer.

This gate greps the Tauri UI source tree (and the install docs) for
any non-approved key-entry surface:

  - Literal Gemini key prefixes ("AIza...") in strings.
  - Label / placeholder text mentioning "api key" / "gemini key" /
    "api_token" (case-insensitive).
  - <input> elements whose surrounding label contains those tokens.

Any non-approved match fails the build with file:line for triage.
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
    # Read-only crash-banner error message (no <input>): mirrors the
    # Python exit-4 [FATAL] guidance (src/vibemix/__main__.py) for the
    # direct-mode "GEMINI_API_KEY not set" case. It surfaces *where to put*
    # a key, it does not *capture* one — so it's not the entry surface this
    # gate forbids. The actual entry-surface subtrees (wizard/settings) are
    # still fully covered by test_no_api_key_input_field_in_wizard_or_settings.
    "tauri/ui/src/crash-banner.ts",
)

# The deleted D2-era BYO surface. Its ABSENCE is now part of the gate.
DELETED_BYO_KEY_SURFACE = "tauri/ui/src/settings/components/brain-group.ts"
IPC_CLIENT = REPO_ROOT / "tauri" / "ui" / "src" / "ipc" / "client.ts"

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


def test_byo_key_drawer_stays_deleted_and_ipc_log_stays_redacted() -> None:
    """Proxy-only product (Kaan 2026-06-09): the D2-era BYO key drawer must
    NOT come back via a stray git add, and the defensive IPC-log redaction
    for `ipc.settings.set_brain` must survive as long as the message type
    exists in the schema."""
    assert not (REPO_ROOT / DELETED_BYO_KEY_SURFACE).exists(), (
        f"{DELETED_BYO_KEY_SURFACE} was deleted in d056a391 (proxy-only product); "
        "restoring a key-entry UI needs an explicit product decision, not a revert."
    )
    ipc_client = IPC_CLIENT.read_text(encoding="utf-8")
    assert '"ipc.settings.set_brain": ["gemini_api_key"]' in ipc_client, (
        "IPC log redaction for set_brain removed — if the message type still "
        "exists, the redaction must stay (defense in depth)."
    )


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
