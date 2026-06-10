# SPDX-License-Identifier: Apache-2.0
"""Audit B-audio-firstrun — fetch_drivers.sh must not hard-require jq.

jq is not stock macOS; the fresh-Mac path reads the driver manifest via
plutil (stock, raw JSON keypath extraction since macOS 12).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "installer" / "companion" / "fetch_drivers.sh"
MANIFEST = REPO / "installer" / "companion" / "driver_manifest.json"


def test_fetch_drivers_does_not_hard_require_jq() -> None:
    text = SCRIPT.read_text()
    assert "require_cmd jq" not in text
    assert "plutil -extract" in text
    assert "read_manifest 'drivers.blackhole_2ch.url'" in text


@pytest.mark.skipif(sys.platform != "darwin", reason="plutil is macOS-only")
def test_plutil_reads_the_real_manifest_keypaths() -> None:
    expected = json.loads(MANIFEST.read_text())["drivers"]["blackhole_2ch"]
    for key, want in (("url", expected["url"]), ("version", expected["version"])):
        out = subprocess.run(
            ["plutil", "-extract", f"drivers.blackhole_2ch.{key}", "raw", "-o", "-", "--", str(MANIFEST)],
            capture_output=True, text=True, check=True,
        )
        assert out.stdout.strip() == want


def test_fetch_drivers_check_syntax_gate() -> None:
    # --check-syntax exits 0 before preflight; bash -n proves it still parses.
    out = subprocess.run(["bash", "-n", str(SCRIPT)], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
