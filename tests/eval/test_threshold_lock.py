# SPDX-License-Identifier: Apache-2.0
"""Phase 27-04 — eval/THRESHOLD-LOCK.md parser + signature lifecycle tests."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from scripts.eval.threshold_lock import (
    DEFAULT_THRESHOLDS,
    autonomous_sign,
    is_signed,
    parse_threshold_lock_frontmatter,
)

PROJECT_ROOT = Path(__file__).parents[2]
LOCK_PATH = PROJECT_ROOT / "eval" / "THRESHOLD-LOCK.md"


def test_parse_returns_thresholds_dict() -> None:
    """The repo-shipped eval/THRESHOLD-LOCK.md parses to CONTEXT EVAL-06 values."""
    parsed = parse_threshold_lock_frontmatter(LOCK_PATH)
    assert parsed["thresholds"]["f1_min"] == 0.80
    assert parsed["thresholds"]["substance_min"] == 0.65
    assert parsed["thresholds"]["cited_cosine_min"] == 0.4
    assert parsed["thresholds"]["bypass_max"] == 0.15
    assert parsed["thresholds"]["per_genre_f1_min"] == 0.70
    assert parsed["phase"] == 27
    assert parsed["milestone"] == "v2.1"


def test_parse_uses_safe_load_not_load(monkeypatch: pytest.MonkeyPatch) -> None:
    """Confirm parser uses yaml.safe_load (V5 ASVS)."""
    import yaml

    safe_load_called = {"flag": False}
    original_safe_load = yaml.safe_load

    def fake_safe_load(s):
        safe_load_called["flag"] = True
        return original_safe_load(s)

    monkeypatch.setattr(yaml, "safe_load", fake_safe_load)
    # If parser uses yaml.load instead of yaml.safe_load, fake_safe_load
    # would never be called.
    parse_threshold_lock_frontmatter(LOCK_PATH)
    assert safe_load_called["flag"] is True


def test_is_signed_recognizes_autonomous_signature() -> None:
    """autonomous_phase27 → signed."""
    assert is_signed({"kaan_signed": "autonomous_phase27"}) is True


def test_is_signed_recognizes_real_signature() -> None:
    """Any non-empty non-false string → signed."""
    assert is_signed({"kaan_signed": "kaan-real-sig"}) is True


def test_is_signed_false_for_false_or_missing() -> None:
    assert is_signed({"kaan_signed": False}) is False
    assert is_signed({"kaan_signed": "false"}) is False
    assert is_signed({"kaan_signed": ""}) is False
    assert is_signed({}) is False


def test_autonomous_sign_writes_signature(tmp_path: Path) -> None:
    """Create a fake THRESHOLD-LOCK with kaan_signed: false; autonomous_sign flips it."""
    fake_lock = tmp_path / "THRESHOLD-LOCK.md"
    fake_lock.write_text(
        "---\n"
        "kaan_signed: false\n"
        "phase: 27\n"
        "milestone: v2.1\n"
        "thresholds:\n"
        "  f1_min: 0.80\n"
        "  substance_min: 0.65\n"
        "  cited_cosine_min: 0.4\n"
        "  bypass_max: 0.15\n"
        "  per_genre_f1_min: 0.70\n"
        "---\n\n"
        "# Test lock body\n",
        encoding="utf-8",
    )
    result = autonomous_sign(fake_lock)
    assert result["kaan_signed"] == "autonomous_phase27"
    assert "kaan_signed_at" in result
    # File now reflects the change.
    reparsed = parse_threshold_lock_frontmatter(fake_lock)
    assert reparsed["kaan_signed"] == "autonomous_phase27"


def test_autonomous_sign_is_idempotent(tmp_path: Path) -> None:
    """Calling autonomous_sign on already-signed lock is a no-op."""
    fake_lock = tmp_path / "THRESHOLD-LOCK.md"
    fake_lock.write_text(
        '---\n'
        'kaan_signed: autonomous_phase27\n'
        'kaan_signed_at: "2026-05-15T00:00:00+00:00"\n'
        'phase: 27\n'
        'thresholds:\n'
        '  f1_min: 0.80\n'
        '---\n\n'
        '# Already signed\n',
        encoding="utf-8",
    )
    before = fake_lock.read_text(encoding="utf-8")
    autonomous_sign(fake_lock)
    after = fake_lock.read_text(encoding="utf-8")
    assert before == after, "autonomous_sign mutated already-signed lock"


def test_default_thresholds_match_context_eval_06() -> None:
    assert DEFAULT_THRESHOLDS["f1_min"] == 0.80
    assert DEFAULT_THRESHOLDS["substance_min"] == 0.65
    assert DEFAULT_THRESHOLDS["cited_cosine_min"] == 0.4
    assert DEFAULT_THRESHOLDS["bypass_max"] == 0.15
    assert DEFAULT_THRESHOLDS["per_genre_f1_min"] == 0.70


def test_replay_harness_consumes_threshold_lock_via_cli(tmp_path: Path) -> None:
    """End-to-end: replay_harness with --threshold-lock argument exits 0 on happy path."""
    out = tmp_path / "eval-out"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.eval.replay_harness",
            "--corpus",
            str(PROJECT_ROOT / "tests" / "eval" / "fixtures"),
            "--judges",
            "noop",
            "--threshold-lock",
            str(LOCK_PATH),
            "--output",
            str(out),
        ],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stdout={result.stdout}\nstderr={result.stderr}"
    assert (out / "eval_report.json").exists()
    import json

    data = json.loads((out / "eval_report.json").read_text())
    # Confirm the lock thresholds (not defaults) are surfaced in the report.
    assert data["thresholds"]["f1_min"] == 0.80


def test_threshold_lock_md_documents_retuning_protocol() -> None:
    """The lock body documents the re-tuning protocol per RESEARCH §Open Questions #1."""
    text = LOCK_PATH.read_text(encoding="utf-8")
    assert "Re-tuning" in text or "re-tuning" in text
    assert "NEVER edit" in text or "re-run" in text.lower()


def test_threshold_lock_md_references_pitfalls() -> None:
    """The lock body cross-references the relevant Pitfalls."""
    text = LOCK_PATH.read_text(encoding="utf-8")
    for pitfall in ["P42", "P43", "P44", "P45", "P46"]:
        assert pitfall in text, f"THRESHOLD-LOCK missing {pitfall} reference"
