# SPDX-License-Identifier: Apache-2.0
"""Phase 34 / SEC-05 — signed-binary verifier surface.

This is the *surface*. Phase 38 wires real Apple notarytool + SignPath
chain validation. Phase 34 ships:

  1. Checksum validator (sha256) — runs unconditionally.
  2. macOS codesign surface check (no POST, no PUT — read-only).
  3. Authenticode certificate-table presence check (offline PE inspection only).

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
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

_WIN_CERT_REVISION_1_0 = 0x0100
_WIN_CERT_REVISION_2_0 = 0x0200
_WIN_CERT_TYPE_PKCS_SIGNED_DATA = 0x0002
_PE32_DATA_DIRECTORY_OFFSET = 96
_PE32_PLUS_DATA_DIRECTORY_OFFSET = 112
_IMAGE_DIRECTORY_ENTRY_SECURITY = 4


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
    """Read-only check for a macOS signing surface.

    DMG/PKG signatures are verified with macOS `codesign` when the release
    publish gate runs on a macOS runner. For Mach-O files, fall back to the
    historical offline magic check used by the older Phase 34 surface.
    """
    if path.suffix.lower() in {".dmg", ".pkg"} and sys.platform == "darwin":
        try:
            result = subprocess.run(
                ["codesign", "--verify", "--strict", "--verbose=2", str(path)],
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError:
            return False
        return result.returncode == 0

    try:
        with path.open("rb") as f:
            head = f.read(64)
    except OSError:
        return False
    # Quick magic check; Mach-O fat or thin.
    magics = {b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf", b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca"}
    return head[:4] in magics


def _scan_pe_for_authenticode(path: Path) -> bool:
    """Read-only check for a PE Authenticode certificate table."""
    try:
        size = path.stat().st_size
        with path.open("rb") as f:
            if f.read(2) != b"MZ":
                return False
            f.seek(0x3C)
            e_lfanew = int.from_bytes(f.read(4), "little")
            if e_lfanew <= 0 or e_lfanew + 24 >= size:
                return False

            f.seek(e_lfanew)
            if f.read(4) != b"PE\0\0":
                return False

            f.seek(e_lfanew + 20)
            optional_header_size = int.from_bytes(f.read(2), "little")
            optional_header_offset = e_lfanew + 24
            if optional_header_size <= 0 or optional_header_offset + optional_header_size > size:
                return False

            f.seek(optional_header_offset)
            optional = f.read(optional_header_size)
    except OSError:
        return False

    magic = int.from_bytes(optional[:2], "little")
    if magic == 0x10B:
        directory_offset = _PE32_DATA_DIRECTORY_OFFSET
    elif magic == 0x20B:
        directory_offset = _PE32_PLUS_DATA_DIRECTORY_OFFSET
    else:
        return False

    security_entry_offset = directory_offset + (_IMAGE_DIRECTORY_ENTRY_SECURITY * 8)
    if security_entry_offset + 8 > len(optional):
        return False

    cert_offset = int.from_bytes(
        optional[security_entry_offset : security_entry_offset + 4], "little"
    )
    cert_size = int.from_bytes(
        optional[security_entry_offset + 4 : security_entry_offset + 8], "little"
    )
    if cert_offset <= 0 or cert_size < 8 or cert_offset + cert_size > size:
        return False

    try:
        with path.open("rb") as f:
            f.seek(cert_offset)
            header = f.read(8)
    except OSError:
        return False
    if len(header) != 8:
        return False

    cert_length = int.from_bytes(header[:4], "little")
    revision = int.from_bytes(header[4:6], "little")
    cert_type = int.from_bytes(header[6:8], "little")
    return (
        8 <= cert_length <= cert_size
        and cert_offset + cert_length <= size
        and revision in {_WIN_CERT_REVISION_1_0, _WIN_CERT_REVISION_2_0}
        and cert_type == _WIN_CERT_TYPE_PKCS_SIGNED_DATA
    )


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
    is_mac_artifact = (
        artifact.suffix.lower() in {".dmg", ".pkg"} or "darwin" in str(artifact).lower()
    )
    is_win_artifact = (
        artifact.suffix.lower() in {".msi", ".exe"} or "windows" in str(artifact).lower()
    )
    if is_mac_artifact:
        signed_mac = _scan_macho_for_codesign(artifact)
        if not signed_mac:
            notes.append("macOS signing artifact missing — Phase 38 will wire")
    if is_win_artifact:
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


def is_signed_for_platform(result: VerifyResult) -> bool:
    """Return True iff the artifact carries the expected signing surface.

    Phase 38 DIST-17 — used by the release-publish gate. A `.dmg`/`.pkg` MUST
    return signed_mac=True; a `.msi`/`.exe` MUST return signed_win=True. For
    artifacts of unknown type we pass (avoids false positives on .json reports).
    """
    suffix = result.artifact.suffix.lower()
    path_str = str(result.artifact).lower()
    if suffix in {".dmg", ".pkg"} or "darwin" in path_str:
        return result.signed_mac
    if suffix in {".msi", ".exe"} or "windows" in path_str:
        return result.signed_win
    return True


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--artifact",
        type=Path,
        required=False,
        help="Path to signed DMG / Windows installer (or any binary)",
    )
    p.add_argument("--expected-sha256", type=str, default=None)
    p.add_argument(
        "--skip-if-missing",
        action="store_true",
        help="exit 0 with ::notice:: if artifact is missing",
    )
    p.add_argument(
        "--require-signed",
        action="store_true",
        help="Phase 38 DIST-17 — exit 1 if signing surface missing "
        "for the artifact's platform (release-publish gate).",
    )
    args = p.parse_args(argv)

    if args.artifact is None or not args.artifact.exists():
        if args.skip_if_missing:
            print(
                "::notice::verify_signed: no artifact present — skipping "
                "(Phase 34 surface only; Phase 38 wires real signing)."
            )
            return 0
        print("::error::verify_signed: artifact missing and --skip-if-missing not set")
        return 1

    try:
        result = verify(args.artifact, args.expected_sha256)
    except (FileNotFoundError, ValueError) as e:
        print(f"::error::verify_signed: {e}")
        return 1

    print(
        json.dumps(
            {
                "artifact": str(result.artifact),
                "sha256": result.sha256,
                "signed_mac": result.signed_mac,
                "signed_win": result.signed_win,
                "notes": result.notes,
            },
            indent=2,
        )
    )

    if args.require_signed and not is_signed_for_platform(result):
        print(
            "::error::verify_signed: --require-signed set but artifact lacks "
            f"signing surface (signed_mac={result.signed_mac}, "
            f"signed_win={result.signed_win}). Publish blocked (DIST-17)."
        )
        return 1

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
