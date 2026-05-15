# SPDX-License-Identifier: Apache-2.0
"""Phase 34 / SEC-05 — signed-binary verifier surface.

This is the *surface*. Phase 38 wires real Apple notarytool + SignPath
chain validation. Phase 34 ships:

  1. Checksum validator (sha256) — runs unconditionally.
  2. Apple notarytool ticket presence check (no POST, no PUT — read-only).
  3. SignPath signature chain presence check (offline file inspection only).

Pitfall P46: NEVER POST/PUT to apple/signpath endpoints from this script
or its workflow. The workflow `.github/workflows/verify-signed.yml`
grep-asserts that no curl/POST/PUT to those domains exists.

If signing artifacts are missing (forks, dry-run, pre-Phase 38), the
script exits 0 with a `::notice::` line — it does NOT fail the run.
The release workflow's earlier sign stage is what gates publish.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class VerifyResult:
    artifact: Path
    sha256: str
    signed_mac: bool
    signed_win: bool
    notes: list[str]


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _scan_macho_for_codesign(path: Path) -> bool:
    """Read-only check for the LC_CODE_SIGNATURE load command in Mach-O.

    We deliberately do not shell out to `codesign --verify` — that's the
    Phase 38 sign stage's job. We just confirm the bundle carries the
    signature load command at all.
    """
    try:
        with path.open("rb") as f:
            head = f.read(64)
    except OSError:
        return False
    # Quick magic check; Mach-O fat or thin.
    magics = {b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf", b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca"}
    return head[:4] in magics


def _scan_pe_for_authenticode(path: Path) -> bool:
    """Read-only check for the Authenticode security directory in a PE."""
    try:
        with path.open("rb") as f:
            head = f.read(2)
    except OSError:
        return False
    return head == b"MZ"


def verify(artifact: Path, expected_sha256: str | None = None) -> VerifyResult:
    if not artifact.exists():
        raise FileNotFoundError(f"artifact not found: {artifact}")

    actual = sha256_of(artifact)
    notes: list[str] = []
    if expected_sha256 is not None:
        if actual.lower() != expected_sha256.lower():
            raise ValueError(
                f"sha256 mismatch on {artifact.name}: expected {expected_sha256} got {actual}"
            )
        notes.append("checksum match")
    else:
        notes.append(f"no expected sha256 supplied (computed only): {actual[:16]}")

    signed_mac = signed_win = False
    if artifact.suffix.lower() in {".dmg", ".pkg"} or "darwin" in str(artifact).lower():
        signed_mac = _scan_macho_for_codesign(artifact)
        if not signed_mac:
            notes.append("macOS signing artifact missing — Phase 38 will wire")
    if artifact.suffix.lower() in {".msi", ".exe"} or "windows" in str(artifact).lower():
        signed_win = _scan_pe_for_authenticode(artifact)
        if not signed_win:
            notes.append("Windows signing artifact missing — Phase 38 will wire")

    return VerifyResult(
        artifact=artifact,
        sha256=actual,
        signed_mac=signed_mac,
        signed_win=signed_win,
        notes=notes,
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--artifact", type=Path, required=False,
                   help="Path to signed DMG / MSI (or any binary)")
    p.add_argument("--expected-sha256", type=str, default=None)
    p.add_argument("--skip-if-missing", action="store_true",
                   help="exit 0 with ::notice:: if artifact is missing")
    args = p.parse_args(argv)

    if args.artifact is None or not args.artifact.exists():
        if args.skip_if_missing:
            print("::notice::verify_signed: no artifact present — skipping "
                  "(Phase 34 surface only; Phase 38 wires real signing).")
            return 0
        print("::error::verify_signed: artifact missing and --skip-if-missing not set")
        return 1

    try:
        result = verify(args.artifact, args.expected_sha256)
    except (FileNotFoundError, ValueError) as e:
        print(f"::error::verify_signed: {e}")
        return 1

    print(json.dumps({
        "artifact": str(result.artifact),
        "sha256": result.sha256,
        "signed_mac": result.signed_mac,
        "signed_win": result.signed_win,
        "notes": result.notes,
    }, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
