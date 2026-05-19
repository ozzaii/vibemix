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
    # Post-DEPS-07 pinact discharge: refs are SHA-pinned with version comment.
    assert "anchore/sbom-action@d94f46e13c6c62f59525ac9a1e147a99dc0b9bf5" in txt
    assert "# v0.17.0" in txt


def test_sbom_workflow_uses_spdx_json_format():
    txt = WORKFLOW.read_text(encoding="utf-8")
    assert "format: spdx-json" in txt


def test_sbom_workflow_attaches_to_release():
    txt = WORKFLOW.read_text(encoding="utf-8")
    # Post-DEPS-07 pinact discharge: refs are SHA-pinned with version comment.
    assert "softprops/action-gh-release@3bb12739c298aeb8a4eeaf626c5b8d85266b0e65" in txt
    assert "sbom.spdx.json" in txt
    assert "fail_on_unmatched_files: true" in txt


def test_sbom_workflow_validates_json_shape():
    txt = WORKFLOW.read_text(encoding="utf-8")
    assert "spdxVersion" in txt


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
