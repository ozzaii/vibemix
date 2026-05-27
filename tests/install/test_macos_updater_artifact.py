# SPDX-License-Identifier: Apache-2.0
"""Guards for the macOS Tauri updater artifact helper."""

from __future__ import annotations

import stat
import subprocess
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "dist" / "create_macos_updater_artifact.sh"
PLIST_BUDDY = Path("/usr/libexec/PlistBuddy")


def test_macos_updater_artifact_script_contract() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert SCRIPT.is_file()
    assert SCRIPT.stat().st_mode & stat.S_IXUSR
    assert "arm64|x86_64" in text
    assert 'COPYFILE_DISABLE=1 tar -czf "$OUT" -C "$APP_PARENT" "$APP_BASENAME"' in text
    assert 'grep -q "^${APP_BASENAME}/Contents/"' in text
    assert "${TAURI_UPDATER_KEY_PASSWORD+x}" in text
    assert 'echo "$OUT"' in text


@pytest.mark.skipif(not PLIST_BUDDY.exists(), reason="PlistBuddy is macOS-only")
def test_macos_updater_artifact_script_creates_app_tarball(tmp_path: Path) -> None:
    app = tmp_path / "vibemix.app"
    contents = app / "Contents"
    contents.mkdir(parents=True)
    (contents / "Info.plist").write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleShortVersionString</key>
  <string>0.1.7</string>
</dict>
</plist>
""",
        encoding="utf-8",
    )

    out_dir = tmp_path / "out"
    result = subprocess.run(
        [str(SCRIPT), "--arch", "arm64", "--output-dir", str(out_dir), str(app)],
        check=True,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    artifact = Path(result.stdout.strip())
    assert artifact == out_dir / "vibemix-0.1.7-arm64.app.tar.gz"
    assert artifact.is_file()
    assert not Path(f"{artifact}.sig").exists()
    assert "skipping .sig sidecar" in result.stderr

    with tarfile.open(artifact, "r:gz") as archive:
        names = archive.getnames()
    assert "vibemix.app/Contents/Info.plist" in names
