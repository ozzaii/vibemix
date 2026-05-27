# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LOG = REPO_ROOT / "eval" / "INTEL-THRESHOLD-RECALIBRATION-LOG.md"
LOCK = REPO_ROOT / "eval" / "INTEL-THRESHOLD-LOCK.md"
README = REPO_ROOT / "eval" / "README.md"


def test_intel_threshold_recalibration_log_exists() -> None:
    assert LOG.is_file()
    assert LOG.stat().st_size > 1000


def test_intel_recalibration_log_documents_private_split_contract() -> None:
    text = LOG.read_text(encoding="utf-8")

    assert "tier1_private_calibration" in text
    assert "tier2_private_holdout_canary" in text
    assert "calibration=N holdout=N canary=N" in text
    assert "label_kinds: section=N transition=N cue=N live_pill=N representation=N taste=N" in text
    assert "local_paths_redacted=true" in text
    assert "ids_hashed=true" in text
    assert "raw_audio_committed=false" in text
    assert "raw_vectors_committed=false" in text
    assert "free_form_notes_committed=false" in text
    assert "release_promoted" in text


def test_intel_threshold_lock_requires_recalibration_log_for_private_labels() -> None:
    text = LOCK.read_text(encoding="utf-8")

    assert "INTEL-THRESHOLD-RECALIBRATION-LOG.md" in text
    assert "private-label calibration" in text
    assert "release-gate promotion" in text
    for split in ("calibration", "holdout", "canary"):
        assert split in text


def test_eval_readme_cross_links_intel_recalibration_log() -> None:
    text = README.read_text(encoding="utf-8")

    assert "INTEL-THRESHOLD-RECALIBRATION-LOG.md" in text
    assert "Private-label recalibration" in text
    assert "redacted split counts" in text


def test_intel_recalibration_log_is_public_redacted() -> None:
    text = LOG.read_text(encoding="utf-8")
    forbidden_fragments = (
        "/Users/",
        "file://",
        ".wav",
        ".aiff",
        ".mp3",
        "session_id:",
        "deck_id:",
        "track_title:",
        "local_path:",
        "free_form:",
    )

    leaks = [fragment for fragment in forbidden_fragments if fragment in text]
    assert not leaks, f"private payload markers leaked into public INTEL log: {leaks}"
