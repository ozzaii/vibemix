# SPDX-License-Identifier: Apache-2.0
"""Phase 33 / Plan 33-07 / P63 — Bundle ID lock gate.

The Tauri bundle identifier ``world.bravoh.vibemix`` is LOCKED Day 1.
Changing it on the user's machine resets every macOS TCC permission
(microphone, screen recording, accessibility) because TCC tracks
grants per-bundle-id. A silent bundle-id flip on upgrade = a forced
re-grant flow + a confused user = bad UX.

This test pins two facts:

1. ``tauri/src-tauri/tauri.conf.json5`` ``identifier`` field is the
   exact string ``world.bravoh.vibemix`` — no typo, no env-templating.
2. No OTHER ``identifier``-keyed JSON line in the repo (excluding
   lockfiles + the snapshot file mirror) carries a different bundle id.
   This guards against the slip where a copy-pasted manifest in a new
   phase silently introduces a divergent bundle id.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TAURI_CONF = REPO_ROOT / "tauri" / "src-tauri" / "tauri.conf.json5"
LOCKED_BUNDLE_ID = "world.bravoh.vibemix"


# Files we deliberately exclude from the cross-repo grep. These mirror
# the locked id (entitlements, info.plist) and are NOT a different id —
# they are the SAME id surfaced in a different file format. We also
# exclude lockfiles which can hold transitive package ids.
EXCLUDED_PATTERNS = (
    ".git/",
    ".venv/",
    "node_modules/",
    "target/",
    "dist/",
    ".pytest_cache/",
    "__pycache__/",
    "Cargo.lock",
    "package-lock.json",
    ".impeccable/",
)


def _strip_jsonc(body: str) -> str:
    """Strip // line comments + /* ... */ block comments from a JSON5
    body so we can json.loads() it. Tauri ships json5 with comments. """
    # Block comments first.
    body = re.sub(r"/\*.*?\*/", "", body, flags=re.DOTALL)
    # Line comments — keep // inside strings intact by checking quote
    # balance. Simple regex is fine here because the conf is
    # well-behaved and we already block-stripped.
    out_lines = []
    for line in body.splitlines():
        # Drop `// ...` from each line (very simple — no inline-string
        # /// false-positive risk in this config).
        idx = line.find("//")
        if idx != -1:
            line = line[:idx]
        out_lines.append(line)
    return "\n".join(out_lines)


def test_tauri_conf_identifier_is_world_bravoh_vibemix() -> None:
    """Pin the top-level ``identifier`` JSON5 key to the locked bundle
    id. Uses a regex anchored at the canonical line shape because
    tauri.conf.json5 contains comments + a CSP string with embedded
    control characters that defeat naive ``json.loads`` even after
    a strip pass."""
    raw = TAURI_CONF.read_text(encoding="utf-8")
    # Strip comments before grepping so a commented-out alt id can't
    # trip the gate.
    stripped = _strip_jsonc(raw)
    pattern = re.compile(
        r'^\s*"identifier"\s*:\s*"([^"]+)"',
        re.MULTILINE,
    )
    matches = pattern.findall(stripped)
    assert matches, "tauri.conf.json5 has no top-level identifier key"
    # First match in the file is the top-level identifier (no nested
    # "identifier" key exists at the conf root). Pin it exact.
    assert matches[0] == LOCKED_BUNDLE_ID, (
        f"tauri.conf.json5 identifier must be exactly '{LOCKED_BUNDLE_ID}'. "
        f"Got: {matches[0]!r}"
    )


def test_no_other_identifier_in_repo() -> None:
    """Grep every JSON / JSON5 / plist / TOML file for an ``identifier``
    line. Any value other than ``world.bravoh.vibemix`` (or a Tauri
    capability ``identifier`` which is a permission name, not a bundle
    id) fails the test."""
    suffixes = (".json", ".json5", ".plist", ".toml")
    pattern = re.compile(
        r'^[\s\t]*[\'"]?identifier[\'"]?\s*[:=]\s*[\'"]([^\'"]+)[\'"]',
        re.MULTILINE,
    )
    offenders: list[tuple[Path, str]] = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if not path.name.endswith(suffixes):
            continue
        rel = path.relative_to(REPO_ROOT).as_posix()
        if any(p in rel for p in EXCLUDED_PATTERNS):
            continue
        try:
            body = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for match in pattern.finditer(body):
            value = match.group(1)
            # Tauri capability files have identifier=<capability-name>,
            # NOT a bundle id. They live under tauri/src-tauri/capabilities/.
            if "capabilities/" in rel:
                continue
            # An "identifier" that looks like a bundle id has 2+ dots
            # AND is NOT the locked id. That's a P63 violation.
            if value.count(".") >= 2 and value != LOCKED_BUNDLE_ID:
                offenders.append((path, value))

    assert not offenders, (
        "Found a non-locked bundle identifier in: "
        + ", ".join(f"{p.relative_to(REPO_ROOT)}:{v}" for p, v in offenders)
    )
