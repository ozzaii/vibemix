# SPDX-License-Identifier: Apache-2.0
"""Phase 34 / SEC-04 — SBOM workflow shape."""

from __future__ import annotations

from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github/workflows/sbom.yml"


def test_sbom_workflow_exists():
    assert WORKFLOW.exists()


def test_sbom_workflow_triggers_on_release_published():
    txt = WORKFLOW.read_text(encoding="utf-8")
    assert "release:" in txt
    assert "[published]" in txt


def test_sbom_workflow_uses_pinned_syft_action():
    txt = WORKFLOW.read_text(encoding="utf-8")
    assert "anchore/sbom-action@v0.17.0" in txt


def test_sbom_workflow_uses_spdx_json_format():
    txt = WORKFLOW.read_text(encoding="utf-8")
    assert "format: spdx-json" in txt


def test_sbom_workflow_attaches_to_release():
    txt = WORKFLOW.read_text(encoding="utf-8")
    assert "softprops/action-gh-release@v2" in txt
    assert "sbom.spdx.json" in txt
    assert "fail_on_unmatched_files: true" in txt


def test_sbom_workflow_validates_json_shape():
    txt = WORKFLOW.read_text(encoding="utf-8")
    assert "spdxVersion" in txt


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
