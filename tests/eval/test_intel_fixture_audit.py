# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from pathlib import Path

from scripts.eval.intel_fixture_audit import (
    DEFAULT_FIXTURE_DIR,
    REQUIRED_FILES,
    validate_fixture_dir,
    validate_privacy_file,
)


def test_intel_fixture_audit_passes_committed_corpus() -> None:
    result = validate_fixture_dir(DEFAULT_FIXTURE_DIR)
    assert result.valid, result.errors
    assert result.files_checked == len(REQUIRED_FILES)
    assert result.manifest_hash


def test_intel_fixture_audit_rejects_privacy_bad_examples() -> None:
    bad_dir = DEFAULT_FIXTURE_DIR / "privacy_bad_examples"
    local_path_errors = validate_privacy_file(bad_dir / "local_path.json")
    raw_vector_errors = validate_privacy_file(bad_dir / "raw_vector_packet.json")

    assert any("local/private path" in error for error in local_path_errors)
    assert any("raw vector" in error for error in raw_vector_errors)


def test_intel_fixture_dir_constant_points_to_fixture_tree() -> None:
    assert isinstance(DEFAULT_FIXTURE_DIR, Path)
    assert DEFAULT_FIXTURE_DIR.parts[-3:] == ("tests", "intel", "fixtures")
