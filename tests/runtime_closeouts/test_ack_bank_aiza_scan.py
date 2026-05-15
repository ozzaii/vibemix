# SPDX-License-Identifier: Apache-2.0
"""Phase 27-08 — ack_bank AIza key scan (Pitfall LATENCY-15 critical).

Asserts ZERO matches of the Gemini API key pattern across all ack_bank
OPUS files. Re-uses the canonical AIZA_PATTERN from scripts/build_sidecar.py
so the eval-time gate matches the sidecar build-time gate.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[2]
ACK_BANK = PROJECT_ROOT / "src" / "vibemix" / "audio" / "ack_bank"
BUILD_SIDECAR = PROJECT_ROOT / "scripts" / "build_sidecar.py"


def _load_aiza_pattern() -> re.Pattern[bytes]:
    """Re-use the canonical AIZA_PATTERN from scripts/build_sidecar.py.

    Loading via importlib.util so the test does NOT depend on the script
    being importable as a package (it's not installed).
    """
    spec = importlib.util.spec_from_file_location("_build_sidecar_loader", BUILD_SIDECAR)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load scripts/build_sidecar.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.AIZA_PATTERN


def test_aiza_pattern_is_canonical_form() -> None:
    """AIZA_PATTERN matches the exact canonical regex (regression guard).

    Loosening the pattern (e.g. to `AIza\\w+`) would silently weaken the
    leak detection. The canonical form is `AIza[A-Za-z0-9_-]{35}`.
    """
    pattern = _load_aiza_pattern()
    assert pattern.pattern == rb"AIza[A-Za-z0-9_-]{35}"


def test_no_aiza_match_in_any_ack_bank_opus() -> None:
    """Pitfall LATENCY-15: zero AIza matches across all 40 ack_bank OPUS files."""
    pattern = _load_aiza_pattern()
    opus_paths = sorted(ACK_BANK.glob("*/*.opus"))
    # Don't assert on count here — see test_ack_bank_real_audio.py for the
    # 40/40 count gate. This test enforces the security invariant on
    # whatever files exist.
    for path in opus_paths:
        data = path.read_bytes()
        matches = pattern.findall(data)
        assert not matches, (
            f"Pitfall LATENCY-15 violation: AIza match in {path}: "
            f"{matches[:1]}... (only first match shown). The TTS render "
            f"leaked an API key into the OPUS bytes."
        )


def test_ack_bank_manifest_drives_generator() -> None:
    """assets/ack_bank/manifest.json exists and references the buckets."""
    import json

    manifest = PROJECT_ROOT / "assets" / "ack_bank" / "manifest.json"
    assert manifest.exists()
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    buckets = {e["bucket"] for e in data}
    assert buckets == {
        "drop_hit",
        "track_change",
        "mix_move",
        "silence_break",
        "generic_filler",
    }
    assert len(data) == 40


def test_voice_locked_to_achird_in_both_paths() -> None:
    """Achird voice consistency: live runtime config + offline render script."""
    config = (
        PROJECT_ROOT / "src" / "vibemix" / "agent" / "config.py"
    ).read_text(encoding="utf-8")
    assert 'VOICE: str = "Achird"' in config

    script = (
        PROJECT_ROOT / "scripts" / "generate_ack_audio.py"
    ).read_text(encoding="utf-8")
    assert 'VOICE = "Achird"' in script


def test_generate_ack_audio_script_help_works() -> None:
    """scripts/generate_ack_audio.py --help runs cleanly."""
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "scripts.generate_ack_audio", "--help"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Achird" in result.stdout or "ack" in result.stdout.lower()
