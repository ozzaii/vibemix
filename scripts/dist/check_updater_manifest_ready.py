# SPDX-License-Identifier: Apache-2.0
"""Validate a signed Tauri updater ``latest.json`` before publish."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

REQUIRED_PLATFORMS = {
    "darwin-aarch64": ".app.tar.gz",
    "darwin-x86_64": ".app.tar.gz",
    "windows-x86_64": ".exe",
}
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")


@dataclass
class UpdaterManifestStatus:
    manifest: str
    ok: bool = True
    errors: list[str] = field(default_factory=list)
    platforms: list[str] = field(default_factory=list)
    version: str = ""

    def fail(self, message: str) -> None:
        self.ok = False
        self.errors.append(message)


def _read_manifest(path: Path, status: UpdaterManifestStatus) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        status.fail(f"manifest is not readable JSON: {exc}")
        return None
    if not isinstance(data, dict):
        status.fail("manifest root must be a JSON object")
        return None
    return data


def _is_https_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc) and bool(parsed.path)


def _validate_pub_date(value: object, status: UpdaterManifestStatus) -> None:
    if not isinstance(value, str) or not value:
        status.fail("pub_date must be a non-empty string")
        return
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        status.fail(f"pub_date is not ISO-8601: {value!r}")


def _validate_platform_entry(
    platform: str,
    entry: object,
    status: UpdaterManifestStatus,
) -> None:
    if not isinstance(entry, dict):
        status.fail(f"{platform}: entry must be an object")
        return
    url = entry.get("url")
    signature = entry.get("signature")
    if not isinstance(url, str) or not url:
        status.fail(f"{platform}: url must be non-empty")
    elif not _is_https_url(url):
        status.fail(f"{platform}: url must be an https URL with a path")
    else:
        expected_suffix = REQUIRED_PLATFORMS[platform]
        if not url.endswith(expected_suffix):
            status.fail(f"{platform}: url must end with {expected_suffix}: {url}")
        if platform.startswith("darwin-") and url.endswith(".dmg"):
            status.fail(f"{platform}: url points at first-install DMG, not updater archive")
        if platform == "windows-x86_64":
            name = Path(urlparse(url).path).name
            if name == "vibemix-installer.exe":
                status.fail("windows-x86_64: url points at Inno first-install installer")
            if "setup" not in name.lower():
                status.fail("windows-x86_64: url must point at Tauri NSIS *setup*.exe")
            if name.lower().endswith(".msi"):
                status.fail("windows-x86_64: url must not point at an MSI")
    if not isinstance(signature, str) or not signature.strip():
        status.fail(f"{platform}: signature must be non-empty")


def check_updater_manifest_ready(manifest: Path) -> UpdaterManifestStatus:
    status = UpdaterManifestStatus(manifest=str(manifest))
    data = _read_manifest(manifest, status)
    if data is None:
        return status

    version = data.get("version")
    if not isinstance(version, str) or not SEMVER_RE.match(version):
        status.fail(f"version must be semver-like x.y.z: {version!r}")
    else:
        status.version = version

    notes = data.get("notes")
    if not isinstance(notes, str):
        status.fail("notes must be a string")

    _validate_pub_date(data.get("pub_date"), status)

    platforms = data.get("platforms")
    if not isinstance(platforms, dict):
        status.fail("platforms must be an object")
        return status

    status.platforms = sorted(str(key) for key in platforms)
    actual = set(status.platforms)
    required = set(REQUIRED_PLATFORMS)
    missing = sorted(required - actual)
    extra = sorted(actual - required)
    if missing:
        status.fail(f"missing platform entries: {', '.join(missing)}")
    if extra:
        status.fail(f"unexpected platform entries: {', '.join(extra)}")

    for platform in sorted(required & actual):
        _validate_platform_entry(platform, platforms.get(platform), status)

    return status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail if latest.json is not a complete signed updater manifest."
    )
    parser.add_argument("manifest", type=Path, help="path to latest.json")
    parser.add_argument("--json", action="store_true", help="print machine-readable status")
    parser.add_argument("--quiet", action="store_true", help="print only failures")
    args = parser.parse_args(argv)

    status = check_updater_manifest_ready(args.manifest)
    if args.json:
        print(json.dumps(asdict(status), sort_keys=True))
    elif status.ok:
        if not args.quiet:
            print(
                "[updater-manifest] OK: "
                f"{status.version} ({', '.join(status.platforms)})"
            )
    else:
        for error in status.errors:
            print(f"[updater-manifest] FAIL: {error}", file=sys.stderr)
    return 0 if status.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
