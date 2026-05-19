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
    """Post-DEPS-07: ref is SHA-pinned to any 40-char hex, version in comment."""
    txt = WORKFLOW.read_text(encoding="utf-8")
    import re
    m = re.search(
        r"anchore/sbom-action@([0-9a-f]{40})\s+#\s+v(\d+\.\d+(?:\.\d+)?)",
        txt,
    )
    assert m is not None, (
        "expected `anchore/sbom-action@<40-char SHA> # v<version>` "
        "(SHA-pinned + version-comment form post-DEPS-07)"
    )


def test_sbom_workflow_uses_spdx_json_format():
    txt = WORKFLOW.read_text(encoding="utf-8")
    assert "format: spdx-json" in txt


def test_sbom_workflow_attaches_to_release():
    """Post-DEPS-07: gh-release action is SHA-pinned to any 40-char hex."""
    txt = WORKFLOW.read_text(encoding="utf-8")
    import re
    assert re.search(
        r"softprops/action-gh-release@[0-9a-f]{40}\s+#\s+v\d",
        txt,
    ), (
        "expected `softprops/action-gh-release@<40-char SHA> # v<version>` "
        "(SHA-pinned + version-comment form post-DEPS-07)"
    )
    assert "sbom.spdx.json" in txt
    assert "fail_on_unmatched_files: true" in txt


def test_sbom_workflow_validates_json_shape():
    txt = WORKFLOW.read_text(encoding="utf-8")
    assert "spdxVersion" in txt


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
