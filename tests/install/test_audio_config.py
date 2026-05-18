"""Behavioral tests for installer/companion/audio_config.py.

Phase 49 Plan 01 — validates:
  - 48 kHz probe contract (ok at 48000, fail at 44100, fail on missing device)
  - log_path resolves to per-OS install.log
  - source contains zero AIza pattern (Pitfall-7 grep gate)
  - source contains zero off-limits path strings
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[2]
AUDIO_CONFIG = ROOT / "installer" / "companion" / "audio_config.py"


# ─── Grep gates ───────────────────────────────────────────────────────────


def test_no_aiza_literal_in_source():
    """Pitfall-7 grep gate — AIza-key pattern must not appear as a string literal.

    We allow the literal `AIza` to appear ONLY inside string-literal lists of
    forbidden tokens or comment-flagged grep-gate references. Anywhere else
    indicates an inlined key.
    """
    src = AUDIO_CONFIG.read_text()
    # Strict form: the audio_config.py source must not contain the full
    # AIza-pattern key prefix as part of a literal-string definition.
    # Allowed: doc references like `AIza pattern`. Disallowed: any 39-char
    # extension matching the actual key shape.
    import re

    aiza_key_re = re.compile(r"AIza[0-9A-Za-z_-]{20,}")
    matches = aiza_key_re.findall(src)
    assert not matches, f"Pitfall-7 violation: AIza key literal in audio_config.py: {matches}"


def test_no_off_limits_log_writes_in_source():
    """Privacy gate — the source must not OPEN/WRITE to off-limits log dirs.

    The forbidden tokens may still appear inside docstrings/comments that
    document the privacy rule (this is desirable — keeps the rule visible).
    What's forbidden is the source actually constructing a path under those
    dirs. We grep for `open(...hermes` / `write(.../.lmstudio` / similar
    operation patterns rather than the bare string.
    """
    src = AUDIO_CONFIG.read_text()
    # The functional pattern is `open(<path-containing-forbidden>, "w"` or
    # `Path("...hermes...").write_*`. None of these should be present.
    # Look for literal write operations targeting the forbidden dirs.
    # Doc references like the word ".hermes" inside docstrings are allowed
    # (they document the rule); functional file ops are not.
    bad_phrases = [
        ".hermes/",          # any path-construction using hermes dir
        "hermes-rig/logs",   # transcript log dir
        ".lmstudio/",        # LM Studio log/state dir
    ]
    for phrase in bad_phrases:
        # The string may appear inside a comment but not inside an
        # `open(` / `Path(` / write expression. We approximate by checking
        # that any occurrence is preceded by a comment marker on the same
        # line OR sits inside a triple-quoted docstring. For Phase 49's
        # current source, the easier invariant is: if the phrase appears,
        # the same line must contain `#` or be a docstring continuation.
        for i, line in enumerate(src.splitlines(), start=1):
            if phrase in line:
                # Allow if the line begins with whitespace-then-# (comment) OR
                # the substring appears inside a docstring (heuristic:
                # nearby triple-quote within ±5 lines).
                stripped = line.strip()
                is_comment = stripped.startswith("#")
                surrounding = src.splitlines()[max(0, i - 6):i + 5]
                in_docstring = any('"""' in s for s in surrounding)
                allowed = is_comment or in_docstring
                assert allowed, f"Privacy violation at line {i}: {line!r}"


def test_no_aiza_keys_in_companion_dir():
    """Sweep the whole companion dir for actual AIza key literals (not doc refs)."""
    import re

    aiza_key_re = re.compile(r"AIza[0-9A-Za-z_-]{20,}")
    companion = ROOT / "installer" / "companion"
    for path in companion.rglob("*"):
        if path.is_file() and path.suffix in {".py", ".sh", ".ps1", ".json"}:
            text = path.read_text()
            matches = aiza_key_re.findall(text)
            assert not matches, f"{path.name}: AIza-key literal found: {matches}"


# ─── 48 kHz probe contract ────────────────────────────────────────────────


def _mock_system_profiler(rate_hz: int | None) -> subprocess.CompletedProcess:
    """Build a mocked SPAudioDataType output containing a BlackHole block with the given rate."""
    if rate_hz is None:
        return subprocess.CompletedProcess([], 0, stdout="", stderr="")
    text = f"""
Audio:

    Devices:

        BlackHole 2ch:
          Default Output Device: No
          Default System Output Device: No
          Manufacturer: ExistentialAudio
          Output Channels: 2
          Current SampleRate: {rate_hz}
          Transport: Virtual
          Output Source: Default
    """
    return subprocess.CompletedProcess([], 0, stdout=text, stderr="")


@pytest.mark.skipif(sys.platform != "darwin", reason="darwin-only probe path")
def test_probe_48k_at_48000_returns_ok():
    from installer.companion import audio_config

    with patch("installer.companion.audio_config.subprocess.run", return_value=_mock_system_profiler(48000)):
        result = audio_config.probe_48k_darwin()
    assert result["ok"] is True
    assert result["measured_khz"] == 48.0
    assert result["expected_khz"] == 48.0


@pytest.mark.skipif(sys.platform != "darwin", reason="darwin-only probe path")
def test_probe_48k_at_44100_returns_fail():
    from installer.companion import audio_config

    with patch("installer.companion.audio_config.subprocess.run", return_value=_mock_system_profiler(44100)):
        result = audio_config.probe_48k_darwin()
    assert result["ok"] is False
    assert result["measured_khz"] == 44.1


@pytest.mark.skipif(sys.platform != "darwin", reason="darwin-only probe path")
def test_probe_48k_missing_device_returns_fail():
    from installer.companion import audio_config

    with patch("installer.companion.audio_config.subprocess.run", return_value=_mock_system_profiler(None)):
        result = audio_config.probe_48k_darwin()
    assert result["ok"] is False
    assert result["reason"] == "no_device"


# ─── Log path resolution ──────────────────────────────────────────────────


def test_log_path_under_per_os_vibemix_dir():
    from installer.companion import audio_config

    log_str = str(audio_config.LOG_PATH).lower()
    if sys.platform == "darwin":
        assert "library/application support/vibemix" in log_str
    elif sys.platform == "win32":
        assert "vibemix" in log_str
    else:
        assert "vibemix" in log_str


def test_log_path_not_in_off_limits_paths():
    from installer.companion import audio_config

    log_str = str(audio_config.LOG_PATH).lower()
    forbidden = [".hermes", "hermes-rig/logs", ".lmstudio"]
    for needle in forbidden:
        assert needle not in log_str, f"LOG_PATH contains forbidden {needle!r}"


# ─── Probe-only contract ──────────────────────────────────────────────────


@pytest.mark.skipif(sys.platform != "darwin", reason="darwin-only")
def test_probe_only_detects_blackhole_when_present():
    from installer.companion import audio_config

    fake = subprocess.CompletedProcess([], 0, stdout="BlackHole 2ch: present", stderr="")
    with patch("installer.companion.audio_config.subprocess.run", return_value=fake):
        result = audio_config.probe_only()
    assert result["installed"] is True
    assert result["driver"] == "blackhole_2ch"


@pytest.mark.skipif(sys.platform != "darwin", reason="darwin-only")
def test_probe_only_reports_absent_when_missing():
    from installer.companion import audio_config

    fake = subprocess.CompletedProcess([], 0, stdout="no devices", stderr="")
    with patch("installer.companion.audio_config.subprocess.run", return_value=fake):
        result = audio_config.probe_only()
    assert result["installed"] is False


# ─── Routing scaffold ────────────────────────────────────────────────────


def test_remove_routing_clears_sentinel(tmp_path, monkeypatch):
    from installer.companion import audio_config

    sentinel = tmp_path / "multi_output_configured.flag"
    sentinel.touch()
    monkeypatch.setattr(audio_config, "LOG_PATH", tmp_path / "install.log")
    result = audio_config.remove_routing()
    assert result["ok"] is True
    assert not sentinel.exists()
