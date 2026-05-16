# SPDX-License-Identifier: Apache-2.0
"""Phase 35 Plan 35-02 — Demo film cut driver tests.

Pitfall P57: cut count <= 8. Manual editing only.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CUT_SH = REPO_ROOT / "scripts" / "demo_film" / "cut.sh"
CUTS_JSON = REPO_ROOT / "scripts" / "demo_film" / "cuts.json"
HARD_CEILING = 8


def test_cut_script_exists_executable() -> None:
    assert CUT_SH.is_file(), f"missing {CUT_SH}"
    assert os.access(CUT_SH, os.X_OK), f"{CUT_SH} not executable"


def test_template_cuts_json_well_formed() -> None:
    """cuts.json template must parse + have expected schema keys."""
    data = json.loads(CUTS_JSON.read_text())
    for key in ("source", "vo_track", "max_cuts", "output", "cuts"):
        assert key in data, f"missing {key} in cuts.json"
    assert isinstance(data["cuts"], list)
    assert data["max_cuts"] <= HARD_CEILING, (
        f"max_cuts {data['max_cuts']} > hard ceiling {HARD_CEILING} (P57)"
    )


def test_cuts_under_8_in_template() -> None:
    """Current template has <= 8 cuts."""
    data = json.loads(CUTS_JSON.read_text())
    assert len(data["cuts"]) <= HARD_CEILING


def _run_cut(cuts_override: Path | None = None, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if cuts_override is not None:
        env["CUTS_JSON_OVERRIDE"] = str(cuts_override)
    return subprocess.run(
        ["bash", str(CUT_SH), *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


@pytest.mark.skipif(shutil.which("jq") is None, reason="jq not on PATH")
def test_template_dry_run_passes() -> None:
    """Template (0 cuts) dry-runs cleanly — exit 0 with the no-op note."""
    result = _run_cut(None, "--dry-run")
    assert result.returncode == 0, (
        f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
    )
    # 0-cut template is a no-op.
    assert "0 cuts" in result.stdout or "nothing to do" in result.stdout


@pytest.mark.skipif(shutil.which("jq") is None, reason="jq not on PATH")
def test_cuts_over_8_rejected(tmp_path: Path) -> None:
    """9 cuts -> exit 1 with Pitfall P57 message."""
    overflow = {
        "source": "raw/dummy.mov",
        "vo_track": None,
        "max_cuts": 8,
        "output": "docs/assets/demo.mp4",
        "cuts": [
            {"id": f"cut_{i}", "start": f"00:00:{i:02d}.000", "end": f"00:00:{i+1:02d}.000"}
            for i in range(9)
        ],
    }
    overflow_json = tmp_path / "cuts.json"
    overflow_json.write_text(json.dumps(overflow))

    result = _run_cut(overflow_json, "--dry-run")
    assert result.returncode == 1
    assert "P57" in result.stderr
    assert "9" in result.stderr


@pytest.mark.skipif(shutil.which("jq") is None, reason="jq not on PATH")
def test_vo_track_pointing_at_ai_service_rejected(tmp_path: Path) -> None:
    """AI-VO URL in vo_track -> exit 1 with Pitfall P58 message."""
    bad = {
        "source": "raw/dummy.mov",
        "vo_track": "https://api.elevenlabs.io/v1/text-to-speech/abc",
        "max_cuts": 8,
        "output": "docs/assets/demo.mp4",
        "cuts": [
            {"id": "x", "start": "00:00:00.000", "end": "00:00:01.000"}
        ],
    }
    bad_json = tmp_path / "cuts.json"
    bad_json.write_text(json.dumps(bad))

    result = _run_cut(bad_json, "--dry-run")
    assert result.returncode == 1
    assert "P58" in result.stderr
    assert "elevenlabs" in result.stderr.lower()
