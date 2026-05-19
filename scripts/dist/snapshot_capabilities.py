# SPDX-License-Identifier: Apache-2.0
"""Phase 34 / SEC-09 — Tauri capability snapshot generator.

Produces a deterministic, canonical JSON representation of the current
Tauri capability set at ``tauri/src-tauri/capabilities-snapshot/SNAPSHOT.json``.

The snapshot lives in a SIBLING directory to ``capabilities/`` (NOT inside
``capabilities/`` itself) because Tauri's build-time loader scans
``capabilities/*.json`` and errors on duplicate identifiers — and the
snapshot is intentionally a derived copy of ``default.json`` (same
identifier "default"). The sibling location keeps the SEC-09 audit
invariant intact while letting ``cargo tauri build`` succeed locally.

The snapshot file is committed. The CI workflow
``.github/workflows/capabilities-lint.yml`` regenerates the snapshot
on every PR and ``git diff --exit-code`` fails the build if it differs
from the committed copy. To intentionally extend capabilities the
contributor must:

  1. Edit ``tauri/src-tauri/capabilities/default.json``.
  2. Run ``python scripts/dist/snapshot_capabilities.py --write``.
  3. Commit the regenerated ``SNAPSHOT.json``.
  4. Include a ``SECURITY_CAPABILITY_DELTA:`` block in the PR description
     justifying the change.

The snapshot is the *canonical* permission set; the description string
in ``default.json`` is for humans. We strip the description from the
snapshot to avoid prose drift triggering the gate.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CAP = REPO_ROOT / "tauri/src-tauri/capabilities/default.json"
SNAPSHOT = REPO_ROOT / "tauri/src-tauri/capabilities-snapshot/SNAPSHOT.json"


def canonicalise(data: dict[str, Any]) -> dict[str, Any]:
    """Strip prose + sort everything deterministically.

    We keep `identifier`, `windows`, `permissions` — these are the
    security-relevant fields. The `description` string drifts on doc
    edits and would generate false-positive diffs.
    """
    out: dict[str, Any] = {}
    if "identifier" in data:
        out["identifier"] = data["identifier"]
    if "windows" in data:
        out["windows"] = sorted(data["windows"])
    if "permissions" in data:
        out["permissions"] = _canonicalise_permissions(data["permissions"])
    return out


def _canonicalise_permissions(perms: list[Any]) -> list[Any]:
    """Sort + deep-canonicalise the permission entries."""
    out: list[Any] = []
    for entry in perms:
        if isinstance(entry, str):
            out.append(entry)
        elif isinstance(entry, dict):
            # Deep sort the dict keys (json.dumps with sort_keys handles inner).
            normalised = json.loads(json.dumps(entry, sort_keys=True))
            # `allow` lists should be sorted by their JSON representation
            # for determinism.
            if isinstance(normalised.get("allow"), list):
                normalised["allow"] = sorted(
                    normalised["allow"],
                    key=lambda e: json.dumps(e, sort_keys=True),
                )
            out.append(normalised)
        else:
            out.append(entry)
    # Sort the whole list by its JSON representation.
    out.sort(key=lambda e: json.dumps(e, sort_keys=True))
    return out


def render(data: dict[str, Any]) -> str:
    return json.dumps(canonicalise(data), indent=2, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--write", action="store_true",
                   help="write SNAPSHOT.json; otherwise just print")
    p.add_argument("--check", action="store_true",
                   help="exit 1 if SNAPSHOT.json differs from current default.json")
    args = p.parse_args(argv)

    raw = json.loads(DEFAULT_CAP.read_text(encoding="utf-8"))
    rendered = render(raw)

    if args.check:
        if not SNAPSHOT.exists():
            print(f"::error::SNAPSHOT.json missing at {SNAPSHOT}")
            print("Run: python scripts/dist/snapshot_capabilities.py --write")
            return 1
        committed = SNAPSHOT.read_text(encoding="utf-8")
        if committed != rendered:
            print("::error::Tauri capability drift detected.")
            print("default.json has been modified but SNAPSHOT.json is stale.")
            print("To proceed:")
            print("  1. Run: python scripts/dist/snapshot_capabilities.py --write")
            print("  2. Commit the regenerated SNAPSHOT.json in this PR.")
            print("  3. Add `SECURITY_CAPABILITY_DELTA: <reason>` to the PR description.")
            return 1
        print("::notice::Tauri capability snapshot matches default.json.")
        return 0

    if args.write:
        SNAPSHOT.write_text(rendered, encoding="utf-8")
        print(f"Wrote {SNAPSHOT}")
        return 0

    sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
